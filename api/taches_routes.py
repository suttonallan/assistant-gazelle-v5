"""Module Tâches — gestion des tâches d'équipe et des campagnes clients.

Deux étages (maquette « Tâches Gazelle v7 ») :
  - Campagnes : gros dossiers clients (Place des Arts, Orford…). Chaque
    campagne affiche ses éléments (= tâches rattachées via `campagne`) et
    les derniers commentaires équipe tirés de Front.
  - Tâches : tableau À faire / En cours / Fait pour tout le reste.

Stockage : table Supabase `taches` (sql/auto/002_taches.sql), accès via la
clé service uniquement.
"""
import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import requests
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from core.supabase_storage import SupabaseStorage

router = APIRouter(prefix="/taches", tags=["taches"])
_log = logging.getLogger(__name__)

STATUTS = ("a_faire", "en_cours", "fait")
EQUIPE = ["allan", "nicolas", "louise", "margot", "jp", "ilyan"]

# Campagnes actives. Pour en ajouter une : une entrée ici (slug stable).
CAMPAGNES: List[Dict[str, Any]] = [
    {
        "slug": "place-des-arts",
        "client_gazelle": "cli_HbEwl9rN11pSuDEU",
        "nom": "Place des Arts",
        "sous_titre": "PO DS23391 · 6 pianos · 14 000 $ · avr–déc 2026",
        "contacts": "Guy Levesque · Isabelle Clairoux (cc)",
        "recherche_front": "Place des Arts",
        "liens": [],
    },
    {
        "slug": "orford",
        "client_gazelle": "cli_PmqPUBTbPFeCMGmz",
        "nom": "Orford Musique",
        "sous_titre": "48 pianos · 2 ans · ~345 000 $ · en attente subvention",
        "contacts": "Wonny Song",
        "recherche_front": "Orford",
        "liens": [],
    },
]

_storage: Optional[SupabaseStorage] = None


def _db() -> SupabaseStorage:
    global _storage
    if _storage is None:
        _storage = SupabaseStorage(silent=True)
    return _storage


def _url(query: str = "") -> str:
    return f"{_db().api_url}/taches{query}"


def _check(resp: requests.Response) -> Any:
    if resp.status_code >= 400:
        detail = resp.text[:300]
        if "taches" in detail and ("does not exist" in detail or "schema cache" in detail):
            raise HTTPException(503, "Table « taches » absente : la migration sql/auto/002_taches.sql n'a pas encore été appliquée.")
        raise HTTPException(502, f"Supabase {resp.status_code}: {detail}")
    return resp.json() if resp.text else None


class TacheIn(BaseModel):
    titre: Optional[str] = None
    contexte: Optional[str] = None
    statut: Optional[str] = None
    assigne: Optional[str] = None
    echeance: Optional[str] = None  # AAAA-MM-JJ ou vide
    campagne: Optional[str] = None
    note: Optional[str] = None
    etapes: Optional[List[Dict[str, Any]]] = None  # [{texte, fait, date}]
    liens: Optional[List[Dict[str, Any]]] = None   # [{label, url, source}]
    source: Optional[str] = None
    cree_par: Optional[str] = None


def _nettoyer(data: Dict[str, Any]) -> Dict[str, Any]:
    if "statut" in data and data["statut"] not in STATUTS:
        raise HTTPException(400, f"statut invalide (attendu : {', '.join(STATUTS)})")
    for champ in ("echeance", "campagne", "assigne", "contexte", "note"):
        if champ in data and data[champ] == "":
            data[champ] = None
    if "titre" in data and not (data["titre"] or "").strip():
        raise HTTPException(400, "Le titre est requis")
    if "statut" in data:
        data["fait_le"] = datetime.now(timezone.utc).isoformat() if data["statut"] == "fait" else None
    return data


@router.get("/actif")
def module_actif():
    """Interrupteurs (system_settings) :
    - flag_taches = false          → module caché pour tout le monde (coupe-circuit)
    - flag_taches_equipe = true    → visible pour toute l'équipe (sinon : Allan seulement)
    """
    from core.feature_flags import is_enabled
    return {"actif": is_enabled("taches", default=True), "equipe": is_enabled("taches_equipe", default=False)}


@router.get("/campagnes")
def lister_campagnes():
    return {"campagnes": CAMPAGNES, "equipe": EQUIPE}


@router.get("")
def lister_taches(
    campagne: Optional[str] = Query(None),
    assigne: Optional[str] = Query(None),
    inclure_faites_depuis_jours: int = Query(30, ge=0, le=3650),
):
    """Toutes les tâches ouvertes + celles faites depuis N jours."""
    q = "?select=*&order=created_at.asc"
    if campagne:
        q += f"&campagne=eq.{requests.utils.quote(campagne)}"
    if assigne:
        q += f"&assigne=eq.{requests.utils.quote(assigne)}"
    taches = _check(requests.get(_url(q), headers=_db()._get_headers(), timeout=15)) or []
    if inclure_faites_depuis_jours is not None:
        limite = time.time() - inclure_faites_depuis_jours * 86400
        garder = []
        for t in taches:
            if t.get("statut") == "fait" and t.get("fait_le"):
                try:
                    ts = datetime.fromisoformat(t["fait_le"].replace("Z", "+00:00")).timestamp()
                    if ts < limite:
                        continue
                except ValueError:
                    pass
            garder.append(t)
        taches = garder
    return {"taches": taches}


@router.post("")
def creer_tache(tache: TacheIn):
    data = _nettoyer({k: v for k, v in tache.model_dump().items() if v is not None})
    if "titre" not in data:
        raise HTTPException(400, "Le titre est requis")
    data.setdefault("statut", "a_faire")
    rows = _check(requests.post(_url(), headers=_db()._get_headers(), json=data, timeout=15))
    return rows[0] if rows else data


@router.patch("/{tache_id}")
def modifier_tache(tache_id: str, tache: TacheIn):
    data = _nettoyer(tache.model_dump(exclude_unset=True))
    if not data:
        raise HTTPException(400, "Rien à modifier")
    data["updated_at"] = datetime.now(timezone.utc).isoformat()
    rows = _check(requests.patch(_url(f"?id=eq.{tache_id}"), headers=_db()._get_headers(), json=data, timeout=15))
    if not rows:
        raise HTTPException(404, "Tâche introuvable")
    return rows[0]


@router.delete("/{tache_id}")
def supprimer_tache(tache_id: str):
    _check(requests.delete(_url(f"?id=eq.{tache_id}"), headers=_db()._get_headers(), timeout=15))
    return {"ok": True}


# --- Commentaires équipe Front par campagne (mémoire 10 min : Front est lent) ---
_cache_front: Dict[str, Any] = {}
_CACHE_TTL = 600


@router.get("/campagnes/{slug}/commentaires")
def commentaires_campagne(slug: str, limite: int = Query(5, ge=1, le=20)):
    camp = next((c for c in CAMPAGNES if c["slug"] == slug), None)
    if not camp:
        raise HTTPException(404, "Campagne inconnue")
    cache = _cache_front.get(slug)
    if cache and time.time() - cache[0] < _CACHE_TTL:
        ctx = cache[1]
    else:
        try:
            from modules.campaigns.campaign_service import get_campaign_context
            ctx = get_campaign_context(camp["recherche_front"], max_conversations=10, max_recent_comments_feed=20)
        except ValueError as e:  # FRONT_API_KEY absent
            return {"disponible": False, "raison": str(e), "commentaires": [], "conversations": []}
        except Exception as e:
            _log.exception("Front indisponible pour %s", slug)
            return {"disponible": False, "raison": f"Front indisponible : {e}", "commentaires": [], "conversations": []}
        _cache_front[slug] = (time.time(), ctx)
    convs = [
        {"id": c["id"], "sujet": c["subject"], "commentaires": c.get("comment_count", 0),
         "url": f"https://app.frontapp.com/open/{c['id']}"}
        for c in ctx.get("conversations", [])
    ]
    return {
        "disponible": True,
        "commentaires": ctx.get("recent_team_comments", [])[:limite],
        "conversations": convs[:6],
    }


@router.get("/campagnes/{slug}/factures")
def factures_campagne(slug: str, depuis: str = Query("2025-01-01"), limite: int = Query(50, ge=1, le=200)):
    """Factures Gazelle du client de la campagne (avec leurs lignes), les plus récentes d'abord."""
    camp = next((c for c in CAMPAGNES if c["slug"] == slug), None)
    if not camp or not camp.get("client_gazelle"):
        raise HTTPException(404, "Campagne inconnue")
    h = _db()._get_headers()
    base = _db().api_url
    factures = _check(requests.get(
        f"{base}/gazelle_invoices?select=external_id,invoice_number,invoice_date,status,sub_total,total,notes"
        f"&client_id=eq.{camp['client_gazelle']}&invoice_date=gte.{depuis}&order=invoice_date.desc&limit={limite}",
        headers=h, timeout=20)) or []
    ids = [f["external_id"] for f in factures]
    lignes: Dict[str, List[Dict]] = {}
    for i in range(0, len(ids), 40):
        lot = ",".join(f'"{x}"' for x in ids[i:i + 40])
        rows = _check(requests.get(
            f"{base}/gazelle_invoice_items?select=invoice_external_id,description,quantity,amount,sub_total"
            f"&invoice_external_id=in.({lot})&order=sequence_number.asc", headers=h, timeout=20)) or []
        for r in rows:
            lignes.setdefault(r["invoice_external_id"], []).append(
                {k: r[k] for k in ("description", "quantity", "amount", "sub_total")})
    for f in factures:
        f["lignes"] = lignes.get(f.pop("external_id"), [])
    return {"client": camp["nom"], "count": len(factures), "factures": factures}
