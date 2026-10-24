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
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel

from core.supabase_storage import SupabaseStorage
from core.timezone_utils import aujourdhui_montreal

# Membres privés d'accès au module (réglable sans déploiement : system_settings
# « taches_membres_bloques » = ["margot", …] ; [] pour rouvrir à tous).
BLOQUES_PAR_DEFAUT: List[str] = []


def _membres_bloques() -> set:
    try:
        import json as _json
        v = SupabaseStorage(silent=True).get_system_setting("taches_membres_bloques")
        if isinstance(v, str):
            v = _json.loads(v)
        if isinstance(v, list):
            return set(v)
    except Exception:
        pass
    return set(BLOQUES_PAR_DEFAUT)


_APERCU_POSSIBLE = {"nicolas", "louise", "margot", "jp"}


def _apercu(qui: Optional[str], request: Request) -> Optional[str]:
    """Allan peut « voir comme » un membre (sélecteur de rôle) : le serveur applique alors
    exactement le filtre de ce membre. Accepté UNIQUEMENT depuis le jeton d'Allan."""
    voir = (request.headers.get("x-voir-comme") or "").strip().lower()
    if qui == "allan" and voir in _APERCU_POSSIBLE:
        return voir
    return qui


def _qui_du_jeton(request: Request) -> Optional[str]:
    from core import verrou_api
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        d = verrou_api.verifier_jeton(auth[7:])
        if d:
            q = d.get("qui")
            return _apercu({"nick": "nicolas"}.get(q, q), request)
    return None


# Ce qu'un membre hors direction (Margot, JP…) peut appeler : ses tâches et leur fil.
# Tout le reste (outils Gazelle, factures, campagnes, timeline…) est réservé à la direction.
import re as _re
_ROUTES_MEMBRE = _re.compile(r"/taches(/actif|/campagnes|/ordre|/[0-9a-f-]{36}(/etape|/commentaires)?)?/?$")


def _pas_bloque(request: Request) -> None:
    """Appliqué à TOUTES les routes /taches (sauf /actif, qui répond « inactif »)."""
    chemin = request.url.path.rstrip("/")
    if chemin.endswith("/taches/actif"):
        return
    q = _qui_du_jeton(request)
    if q and q in _membres_bloques():
        raise HTTPException(403, "Accès au module Tâches suspendu")
    if q and q not in ("allan", "nicolas", "louise") and not _ROUTES_MEMBRE.search(chemin):
        raise HTTPException(403, "Réservé à la direction")


router = APIRouter(prefix="/taches", tags=["taches"], dependencies=[Depends(_pas_bloque)])
_log = logging.getLogger(__name__)

STATUTS = ("a_faire", "en_cours", "fait")
EQUIPE = ["allan", "nicolas", "louise", "margot", "jp"]

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

# Visibilité : la direction (Allan, Nicolas, Louise) voit tout ; les autres
# (Margot, JP…) ne voient que les tâches qui les concernent — assignées à eux,
# ou contenant une étape qui leur est assignée. Appliqué par le SERVEUR.
QUI_VERS_MEMBRE = {"allan": "allan", "nick": "nicolas", "nicolas": "nicolas", "louise": "louise",
                   "margot": "margot", "jp": "jp"}
VOIT_TOUT = {"allan", "nicolas", "louise"}


def _membre(request: Request) -> Optional[str]:
    """Membre connecté d'après le jeton signé (None = clé service / tâche automatique)."""
    from core import verrou_api
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        d = verrou_api.verifier_jeton(auth[7:])
        if d:
            return _apercu(QUI_VERS_MEMBRE.get(d.get("qui"), d.get("qui") or "inconnu"), request)
    if verrou_api.cle_service_valide(request.headers.get("x-cle-service")):
        return None
    raise HTTPException(401, "Connexion requise")


def _concerne(t: Dict[str, Any], membre: str) -> bool:
    return t.get("assigne") == membre or any((e or {}).get("assigne") == membre for e in (t.get("etapes") or []))


def _restreint(request: Request) -> Optional[str]:
    """Membre à qui appliquer le filtre, ou None si la personne voit tout."""
    m = _membre(request)
    return None if (m is None or m in VOIT_TOUT) else m


def _verifier_acces(request: Request, tache_id: str) -> None:
    m = _restreint(request)
    if m and not _concerne(_tache(tache_id, "id,assigne,etapes"), m):
        raise HTTPException(404, "Tâche introuvable")


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
    urgent: Optional[bool] = None
    client: Optional[str] = None  # pda, vdi, orford, prive… (couleur dans l'échéancier)
    front_discussion: Optional[str] = None  # cnv_… : fil Front de la tâche


def _nettoyer(data: Dict[str, Any]) -> Dict[str, Any]:
    if "statut" in data and data["statut"] not in STATUTS:
        raise HTTPException(400, f"statut invalide (attendu : {', '.join(STATUTS)})")
    for champ in ("echeance", "campagne", "assigne", "contexte", "note", "client"):
        if champ in data and data[champ] == "":
            data[champ] = None
    if "titre" in data and not (data["titre"] or "").strip():
        raise HTTPException(400, "Le titre est requis")
    if "statut" in data:
        data["fait_le"] = datetime.now(timezone.utc).isoformat() if data["statut"] == "fait" else None
    return data


@router.get("/actif")
def module_actif(request: Request):
    """Interrupteurs (system_settings) :
    - flag_taches = false          → module caché pour tout le monde (coupe-circuit)
    - flag_taches_equipe = true    → visible pour toute l'équipe (sinon : Allan seulement)
    """
    from core.feature_flags import is_enabled
    q = _qui_du_jeton(request)
    if q and q in _membres_bloques():
        return {"actif": False, "equipe": False}
    return {"actif": is_enabled("taches", default=True), "equipe": is_enabled("taches_equipe", default=False)}


@router.get("/campagnes")
def lister_campagnes():
    return {"campagnes": CAMPAGNES, "equipe": EQUIPE}


@router.get("")
def lister_taches(
    request: Request,
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
    m = _restreint(request)
    if m:
        taches = [t for t in taches if _concerne(t, m)]
    return {"taches": taches, "voit_tout": m is None}


@router.post("")
def creer_tache(tache: TacheIn, request: Request):
    data = _nettoyer({k: v for k, v in tache.model_dump().items() if v is not None})
    m = _restreint(request)
    if m:
        data["assigne"] = m
    if "titre" not in data:
        raise HTTPException(400, "Le titre est requis")
    data.setdefault("statut", "a_faire")
    rows = _check(requests.post(_url(), headers=_db()._get_headers(), json=data, timeout=15))
    return rows[0] if rows else data


class OrdreIn(BaseModel):
    ids: List[str]


@router.post("/ordre")
def reordonner(o: OrdreIn, request: Request):
    for tid in o.ids:
        _verifier_acces(request, tid)
    """Enregistre l'ordre manuel d'une liste : 1re = 10, 2e = 20, …"""
    if not o.ids or len(o.ids) > 200:
        raise HTTPException(400, "Liste vide ou trop longue")
    for i, tid in enumerate(o.ids):
        _check(requests.patch(_url(f"?id=eq.{requests.utils.quote(tid)}"), headers=_db()._get_headers(),
                              json={"ordre": (i + 1) * 10}, timeout=15))
    return {"ok": True, "n": len(o.ids)}


@router.patch("/{tache_id}")
def modifier_tache(tache_id: str, tache: TacheIn, request: Request):
    _verifier_acces(request, tache_id)
    data = _nettoyer(tache.model_dump(exclude_unset=True))
    if not data:
        raise HTTPException(400, "Rien à modifier")
    data["updated_at"] = datetime.now(timezone.utc).isoformat()
    rows = _check(requests.patch(_url(f"?id=eq.{tache_id}"), headers=_db()._get_headers(), json=data, timeout=15))
    if not rows:
        raise HTTPException(404, "Tâche introuvable")
    return rows[0]


class EtapeIn(BaseModel):
    index: int
    texte: Optional[str] = None       # sert à retrouver la bonne étape si l'ordre a changé entre-temps
    fait: Optional[bool] = None       # None = basculer
    assigne: Optional[str] = None     # membre responsable de l'étape ("" = personne)


@router.post("/{tache_id}/etape")
def modifier_etape(tache_id: str, e: EtapeIn, request: Request):
    _verifier_acces(request, tache_id)
    """Modifie UNE étape à partir de la version à jour en base. Cocher une étape
    n'envoie plus toute la liste (qui pouvait être périmée sur l'écran d'un
    collègue et écraser les cases cochées par les autres)."""
    t = _tache(tache_id, "id,etapes")
    etapes = list(t.get("etapes") or [])
    i = e.index
    if e.texte is not None and not (0 <= i < len(etapes) and etapes[i].get("texte") == e.texte):
        i = next((k for k, x in enumerate(etapes) if x.get("texte") == e.texte), -1)
    if not (0 <= i < len(etapes)):
        raise HTTPException(409, "Étape introuvable (modifiée par quelqu'un d'autre ?) — rechargez la page")
    et = dict(etapes[i])
    if "assigne" in e.model_fields_set:
        et["assigne"] = e.assigne or None
    if e.fait is not None or "assigne" not in e.model_fields_set:
        fait = (not et.get("fait")) if e.fait is None else e.fait
        et["fait"] = fait
        et["date"] = aujourdhui_montreal().isoformat() if fait else None
    etapes[i] = et
    rows = _check(requests.patch(_url(f"?id=eq.{tache_id}"), headers=_db()._get_headers(),
                                 json={"etapes": etapes, "updated_at": datetime.now(timezone.utc).isoformat()}, timeout=15))
    if not rows:
        raise HTTPException(404, "Tâche introuvable")
    return rows[0]


class AviserIn(BaseModel):
    de: str        # membre qui envoie (allan, nicolas, louise, margot)
    a: str         # membre avisé
    message: str


class CommentaireTacheIn(BaseModel):
    auteur: str                       # membre qui écrit (allan, nicolas, louise, margot)
    texte: str
    aviser: List[str] = []            # membres à prévenir (JP : par courriel, pas de compte Front)


PAR_COURRIEL = {"jp": "jpreny@gmail.com"}  # techniciens sans compte Front


def _tache(tache_id: str, champs: str) -> Dict[str, Any]:
    rows = _check(requests.get(_url(f"?id=eq.{tache_id}&select={champs}"), headers=_db()._get_headers(), timeout=15))
    if not rows:
        raise HTTPException(404, "Tâche introuvable")
    return rows[0]


@router.get("/{tache_id}/commentaires")
def lire_commentaires(tache_id: str, request: Request):
    _verifier_acces(request, tache_id)
    """Le fil de la tâche = les commentaires de SA discussion Front (source unique)."""
    t = _tache(tache_id, "front_discussion")
    cid = t.get("front_discussion")
    if not cid:
        return {"discussion": None, "commentaires": []}
    from core.front_client import get_front_client
    try:
        coms = get_front_client().list_comments(cid, limit=100)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(502, f"Front : {e}")
    from api.front_routes import EQUIPE_FRONT
    par_email = {v: k for k, v in EQUIPE_FRONT.items()}
    sortie = []
    for c in sorted(coms, key=lambda x: x.get("posted_at") or 0):
        email = ((c.get("author") or {}).get("email") or "").lower()
        sortie.append({"id": c.get("id"), "auteur": par_email.get(email, (c.get("author") or {}).get("first_name") or email),
                       "texte": c.get("body") or "",
                       "quand": datetime.fromtimestamp(c.get("posted_at") or 0, timezone.utc).isoformat()})
    return {"discussion": cid, "url": f"https://app.frontapp.com/open/{cid}", "commentaires": sortie}


@router.post("/{tache_id}/commentaires")
def commenter(tache_id: str, c: CommentaireTacheIn, request: Request):
    _verifier_acces(request, tache_id)
    """Ajoute un commentaire au fil Front de la tâche (le crée au premier commentaire)
    et prévient les membres cochés : abonnés à la discussion (notification Front),
    ou courriel envoyé depuis Front pour JP."""
    from api.front_routes import EQUIPE_FRONT
    from core.front_client import get_front_client
    if c.auteur not in EQUIPE_FRONT:
        raise HTTPException(400, "Seuls les membres ayant un compte Front peuvent commenter")
    if not c.texte.strip():
        raise HTTPException(400, "Commentaire vide")
    inconnus = [m for m in c.aviser if m not in EQUIPE_FRONT and m not in PAR_COURRIEL]
    if inconnus:
        raise HTTPException(400, f"Destinataires inconnus : {', '.join(inconnus)}")
    t = _tache(tache_id, "titre,front_discussion,assigne")
    client = get_front_client()
    auteur_email = EQUIPE_FRONT[c.auteur]
    avises_front = sorted({EQUIPE_FRONT[m] for m in c.aviser if m in EQUIPE_FRONT} - {auteur_email})
    cid = t.get("front_discussion")
    try:
        if not cid:
            conv = client.create_discussion(f"Tâche : {t['titre']}", c.texte.strip(), auteur_email,
                                            sorted(set(avises_front) | {auteur_email}))
            cid = conv.get("id")
            _check(requests.patch(_url(f"?id=eq.{tache_id}"), headers=_db()._get_headers(),
                                  json={"front_discussion": cid}, timeout=15))
        else:
            client.add_comment(cid, c.texte.strip(), auteur_email)
        if avises_front:
            try:
                client.ajouter_abonnes(cid, avises_front)
            except Exception as e:  # noqa: BLE001 — le commentaire est posé ; la notification est un plus
                _log.warning("Abonnement Front impossible (%s) : %s", cid, e)
        for m in c.aviser:
            if m in PAR_COURRIEL:
                canal = client.channel_pour("info@piano-tek.com")
                signature = c.auteur.capitalize()
                client.send_new_message(canal, PAR_COURRIEL[m], f"Tâche : {t['titre']}",
                                        f"{c.texte.strip()}\n\n{signature}", auteur_email)
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001
        raise HTTPException(502, f"Front : {e}")
    return lire_commentaires(tache_id)


@router.delete("/{tache_id}")
def supprimer_tache(tache_id: str, request: Request):
    _verifier_acces(request, tache_id)
    _check(requests.delete(_url(f"?id=eq.{tache_id}"), headers=_db()._get_headers(), timeout=15))
    return {"ok": True}


# --- Commentaires équipe Front par campagne (mémoire 10 min : Front est lent) ---
_cache_front: Dict[str, Any] = {}
_CACHE_TTL = 600


@router.get("/campagnes/{slug}/commentaires")
def commentaires_campagne(request: Request, slug: str, limite: int = Query(5, ge=1, le=20)):
    if _restreint(request):
        raise HTTPException(403, "Réservé à la direction")
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
    masques = _ids_masques()
    visibles = [c for c in ctx.get("recent_team_comments", [])
                if c.get("id") not in masques and not _est_du_bruit(c.get("text") or "")]
    return {
        "disponible": True,
        "commentaires": visibles[:limite],
        "conversations": convs[:6],
    }


def _est_du_bruit(texte: str) -> bool:
    """Commentaire vide ou qui ne contient qu'une mention (« @asutton »)."""
    import re
    reste = re.sub(r"@\w+", "", texte or "").strip(" \n\t.,:;!-")
    return len(reste) < 3


def _ids_masques() -> set:
    try:
        r = requests.get(f"{_db().api_url}/commentaires_masques?select=comment_id",
                         headers=_db()._get_headers(), timeout=10)
        return {x["comment_id"] for x in r.json()} if r.status_code == 200 else set()
    except Exception:
        return set()  # table absente ou Supabase lent : on n'empêche pas l'affichage


class MasquerIn(BaseModel):
    par: Optional[str] = None


@router.post("/commentaires/{comment_id}/masquer")
def masquer_commentaire(comment_id: str, m: MasquerIn = MasquerIn()):
    """Retire un commentaire Front des cartes campagne (il reste intact dans Front)."""
    h = {**_db()._get_headers(), "Prefer": "resolution=merge-duplicates,return=minimal"}
    _check(requests.post(f"{_db().api_url}/commentaires_masques", headers=h,
                         json={"comment_id": comment_id, "masque_par": m.par}, timeout=10))
    return {"ok": True}


@router.get("/campagnes/{slug}/factures")
def factures_campagne(request: Request, slug: str, depuis: str = Query("2025-01-01"), limite: int = Query(50, ge=1, le=200)):
    """Factures Gazelle du client de la campagne (avec leurs lignes), les plus récentes d'abord."""
    if _restreint(request):
        raise HTTPException(403, "Réservé à la direction")
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


# --- Factures en direct de Gazelle (la copie Supabase s'est arrêtée en mars 2026) ---
_cache_gz: Dict[str, Any] = {}
_Q_FACTURES = """
query F($cursor: String%(decl)s) {
  allInvoices(first: 100, after: $cursor%(arg)s) {
    edges { node { id number status subTotal total createdAt client { id }
      allInvoiceItems { nodes { description quantity amount subTotal sequenceNumber } } } }
    pageInfo { hasNextPage endCursor }
  }
}"""


def _factures_gazelle(client_id: str) -> List[Dict]:
    from core.gazelle_api_client import GazelleAPIClient
    api = GazelleAPIClient()
    variantes = [
        ({"decl": ", $c: String", "arg": ", clientId: $c"}, True),
        ({"decl": "", "arg": ""}, False),  # repli : tout parcourir et filtrer ici
    ]
    for gabarit, filtre_serveur in variantes:
        q = _Q_FACTURES % gabarit
        out, cursor, ok = [], None, True
        for _ in range(200):
            v = {"cursor": cursor} if cursor else {}
            if filtre_serveur:
                v["c"] = client_id
            try:
                res = api._execute_query(q, v)
            except Exception as e:
                _log.warning("Gazelle factures (%s) : %s", "filtre" if filtre_serveur else "complet", e)
                ok = False
                break
            if res.get("errors"):
                ok = False
                break
            conn = (res.get("data") or {}).get("allInvoices") or {}
            for e in conn.get("edges", []):
                n = e["node"]
                if (n.get("client") or {}).get("id") == client_id:
                    out.append(n)
            if not (conn.get("pageInfo") or {}).get("hasNextPage"):
                break
            cursor = conn["pageInfo"]["endCursor"]
        if ok:
            return out
    raise HTTPException(502, "Gazelle n'a pas répondu pour les factures")


def _dollars(v):
    return round(v / 100, 2) if isinstance(v, int) else v


@router.get("/campagnes/{slug}/factures-gazelle")
def factures_gazelle_campagne(request: Request, slug: str, depuis: str = Query("2025-01-01")):
    """Factures du client de la campagne, lues en direct dans Gazelle (mémoire 1 h)."""
    if _restreint(request):
        raise HTTPException(403, "Réservé à la direction")
    camp = next((c for c in CAMPAGNES if c["slug"] == slug), None)
    if not camp or not camp.get("client_gazelle"):
        raise HTTPException(404, "Campagne inconnue")
    cache = _cache_gz.get(slug)
    if cache and time.time() - cache[0] < 3600:
        brutes = cache[1]
    else:
        brutes = _factures_gazelle(camp["client_gazelle"])
        _cache_gz[slug] = (time.time(), brutes)
    factures = []
    for n in brutes:
        date = (n.get("createdAt") or "")[:10]
        if date < depuis:
            continue
        items = sorted((n.get("allInvoiceItems") or {}).get("nodes", []), key=lambda i: i.get("sequenceNumber") or 0)
        factures.append({
            "numero": str(n.get("number", "")), "date": date, "statut": n.get("status"),
            "sous_total": _dollars(n.get("subTotal")), "total": _dollars(n.get("total")),
            "lignes": [{"description": i.get("description"), "quantite": i.get("quantity"),
                        "montant": _dollars(i.get("amount")), "sous_total": _dollars(i.get("subTotal"))} for i in items],
        })
    factures.sort(key=lambda f: f["date"], reverse=True)
    return {"client": camp["nom"], "count": len(factures), "factures": factures}


# --- Timeline Gazelle des pianos de campagne ---
UTILISATEURS_GAZELLE = {"allan": "usr_ofYggsCDt2JAVeNP", "nicolas": "usr_HcCiFk7o0vZ9xAI0"}


def _clients_campagnes() -> Dict[str, str]:
    return {c["client_gazelle"]: c["slug"] for c in CAMPAGNES if c.get("client_gazelle")}


@router.get("/pianos")
def pianos_campagne(campagne: str = Query(...), q: Optional[str] = Query(None)):
    """Pianos du client d'une campagne (copie Supabase de Gazelle), filtrables par marque, modèle, série ou lieu."""
    camp = next((c for c in CAMPAGNES if c["slug"] == campagne), None)
    if not camp or not camp.get("client_gazelle"):
        raise HTTPException(404, "Campagne inconnue")
    rows = _check(requests.get(
        f"{_db().api_url}/gazelle_pianos?select=external_id,make,model,serial_number,type,location"
        f"&client_external_id=eq.{camp['client_gazelle']}", headers=_db()._get_headers(), timeout=15)) or []
    if q:
        ql = q.lower()
        rows = [r for r in rows if ql in " ".join(str(r.get(k) or "") for k in ("make", "model", "serial_number", "location")).lower()]
    return {"pianos": rows}


class TimelineIn(BaseModel):
    piano_id: str
    resume: str
    commentaire: Optional[str] = None
    auteur: str = "allan"
    date: Optional[str] = None  # ISO ; défaut : maintenant (heure de Montréal)


@router.post("/timeline")
def ajouter_timeline(t: TimelineIn):
    """Ajoute une note dans la timeline Gazelle d'un piano de campagne."""
    if t.auteur not in UTILISATEURS_GAZELLE:
        raise HTTPException(400, "auteur inconnu")
    piano = _check(requests.get(
        f"{_db().api_url}/gazelle_pianos?select=external_id,client_external_id&external_id=eq.{t.piano_id}",
        headers=_db()._get_headers(), timeout=15)) or []
    if not piano or piano[0].get("client_external_id") not in _clients_campagnes():
        raise HTTPException(403, "Piano hors campagne : écriture refusée")
    from core.gazelle_api_client import GazelleAPIClient
    try:
        # Note simple (createClientLog) marquée 📝 : jamais comptée comme service
        # (sync → type NOTE ; rapport Timeline l'ignore).
        note = "📝 " + t.resume + (("\n\n" + t.commentaire) if t.commentaire else "")
        GazelleAPIClient().create_client_log(piano[0]["client_external_id"], note, piano_id=t.piano_id,
                                             created_at=t.date)
        return {"ok": True, "note": note[:120]}
    except Exception as e:
        raise HTTPException(502, f"Gazelle : {e}")


@router.get("/gazelle/schema-mutation")
def schema_mutation(nom: str = Query(...)):
    """Lecture seule : signature d'une mutation Gazelle et champs de ses types d'entrée."""
    from core.gazelle_api_client import GazelleAPIClient
    api = GazelleAPIClient()
    res = api._execute_query("""{ __schema { mutationType { fields { name args { name type { name kind ofType { name kind ofType { name } } } } } } } }""", {})
    champs = ((res.get("data") or {}).get("__schema") or {}).get("mutationType", {}).get("fields", [])
    f = next((x for x in champs if x["name"] == nom), None)
    if not f:
        return {"trouve": False}
    types = {}
    def _nom_type(t):
        while t and not t.get("name"):
            t = t.get("ofType")
        return (t or {}).get("name")
    for a in f["args"]:
        tn = _nom_type(a["type"])
        if tn and tn.startswith("Private"):
            r = api._execute_query("""query($n:String!){ __type(name:$n){ inputFields { name type { name kind ofType { name kind } } } } }""", {"n": tn})
            types[tn] = ((r.get("data") or {}).get("__type") or {}).get("inputFields")
    return {"trouve": True, "mutation": f, "types": types}


@router.get("/gazelle/schema-type")
def schema_type(nom: str = Query(...)):
    """Lecture seule : champs d'un type d'entrée Gazelle (ex. PrivateContactPhoneInput)."""
    from core.gazelle_api_client import GazelleAPIClient
    r = GazelleAPIClient()._execute_query("""query($n:String!){ __type(name:$n){ name kind inputFields { name type { name kind ofType { name kind ofType { name } } } } enumValues { name } fields { name type { name kind ofType { name } } } } }""", {"n": nom})
    return (r.get("data") or {}).get("__type") or {"trouve": False}


@router.get("/gazelle/schema-notes")
def schema_notes():
    """Lecture seule : mutations et types Gazelle liés aux notes/timeline (diagnostic)."""
    from core.gazelle_api_client import GazelleAPIClient
    api = GazelleAPIClient()
    q = """{ __schema { mutationType { fields { name args { name type { name kind ofType { name } } } } } } }"""
    res = api._execute_query(q, {})
    champs = ((res.get("data") or {}).get("__schema") or {}).get("mutationType", {}).get("fields", [])
    mots = ("note", "timeline", "comment", "history", "delete", "event")
    garder = [f for f in champs if any(m in f["name"].lower() for m in mots)]
    types = {}
    for nom in ("PrivatePianoNoteInput", "PrivateTimelineEntryInput", "PrivateNoteInput", "PrivateCreateNoteInput"):
        r = api._execute_query("""query($n:String!){ __type(name:$n){ name inputFields { name type { name kind ofType { name } } } } }""", {"n": nom})
        t = (r.get("data") or {}).get("__type")
        if t:
            types[nom] = t
    return {"mutations": garder, "types": types, "total_mutations": len(champs)}


# --- Soumissions Gazelle (brouillon : rien n'est envoyé au client) ---

@router.get("/gazelle/clients")
def chercher_clients(q: str = Query(..., min_length=2)):
    """Clients (copie Supabase de Gazelle) dont le nom contient q, avec leurs pianos."""
    h = _db()._get_headers()
    base = _db().api_url
    motif = requests.utils.quote(f"*{q}*")
    clients = _check(requests.get(
        f"{base}/gazelle_clients?select=external_id,company_name&company_name=ilike.{motif}&limit=10",
        headers=h, timeout=15)) or []
    for c in clients:
        c["pianos"] = _check(requests.get(
            f"{base}/gazelle_pianos?select=external_id,make,model,serial_number,type,location"
            f"&client_external_id=eq.{c['external_id']}", headers=h, timeout=15)) or []
    return {"clients": clients}


def _nom_i18n(n):
    if isinstance(n, dict):
        return n.get("fr_CA") or n.get("fr") or n.get("en_US") or ""
    return n or ""


@router.get("/gazelle/services")
def chercher_services(q: str = Query("", max_length=80)):
    """Catalogue Gazelle (prix courants), filtré par nom."""
    from core.gazelle_api_client import GazelleAPIClient
    res = GazelleAPIClient()._execute_query(
        "query { allMasterServiceItems { id name amount isArchived isTaxable type } }")
    items = ((res or {}).get("data") or {}).get("allMasterServiceItems") or []
    ql = q.lower()
    out = [{"id": i["id"], "nom": _nom_i18n(i.get("name")), "prix": (i.get("amount") or 0) / 100,
            "type": i.get("type")}
           for i in items if not i.get("isArchived") and ql in _nom_i18n(i.get("name")).lower()]
    return {"services": out}


class LigneSoumission(BaseModel):
    nom: str
    montant: float  # dollars
    description: Optional[str] = None
    service_id: Optional[str] = None  # MasterServiceItem : reprend son nom officiel


class SoumissionIn(BaseModel):
    client_id: str
    piano_id: str
    lignes: List[LigneSoumission]
    notes: Optional[str] = None
    locale: str = "fr"
    completer_id: Optional[str] = None  # remplir une soumission existante (vide) au lieu d'en créer une


@router.post("/gazelle/soumission")
def creer_soumission(s: SoumissionIn):
    """Crée une soumission dans Gazelle (2 étapes éprouvées : createEstimate minimal
    puis updateEstimate avec taxes). Rien n'est envoyé : Louise/Allan l'envoient depuis Gazelle."""
    from datetime import timedelta
    from core.gazelle_api_client import GazelleAPIClient
    from core.timezone_utils import aujourdhui_montreal
    from api.assistant_duplication import _CREATE_ESTIMATE, _build_taxes, _mutation_error_detail
    gz = GazelleAPIClient()
    noms_msl = {}
    if any(l.service_id for l in s.lignes):
        res = gz._execute_query("query { allMasterServiceItems { id name } }")
        noms_msl = {i["id"]: i.get("name") for i in ((res or {}).get("data") or {}).get("allMasterServiceItems") or []}
    items = []
    for i, l in enumerate(s.lignes):
        cents = int(round(l.montant * 100))
        # Les lignes de soumission prennent un nom texte (pas I18n) — cf. updateEstimate
        nom = _nom_i18n(noms_msl.get(l.service_id)) if l.service_id else ""
        nom = nom or l.nom
        item = {"name": nom, "quantity": 100, "amount": cents, "duration": 0, "type": "LABOR_FIXED_RATE",
                "isTaxable": True, "isTuning": False, "sequenceNumber": i, "photos": [],
                "taxes": _build_taxes(cents, True)}
        if l.description:
            item["description"] = l.description
        if l.service_id:
            item["masterServiceItemId"] = l.service_id
        items.append(item)
    tiers = [{"sequenceNumber": 0, "isPrimary": True, "estimateTierGroups": [], "ungroupedEstimateTierItems": items}]
    if s.completer_id:
        try:
            r = gz.update_estimate(s.completer_id, {"estimateTiers": tiers})
        except Exception as e:
            raise HTTPException(502, f"updateEstimate : {e}")
        return {"numero": (r or {}).get("number"), "id": s.completer_id, "total_avant_taxes": sum(l.montant for l in s.lignes)}
    today = aujourdhui_montreal()
    create_input = {"clientId": s.client_id, "pianoId": s.piano_id, "locale": s.locale,
                    "estimatedOn": today.isoformat(), "expiresOn": (today + timedelta(days=30)).isoformat()}
    if s.notes:
        create_input["notes"] = s.notes
    try:
        res = gz._execute_query(_CREATE_ESTIMATE, {"input": create_input})
    except Exception as e:
        raise HTTPException(502, f"createEstimate : {e}")
    payload = ((res or {}).get("data") or {}).get("createEstimate") or {}
    est = payload.get("estimate")
    if not est:
        raise HTTPException(502, f"Gazelle a refusé la création ({_mutation_error_detail(payload)}) {res.get('errors') if isinstance(res, dict) else ''}")
    try:
        gz.update_estimate(est["id"], {"estimateTiers": tiers})
    except Exception as e:
        raise HTTPException(502, f"Soumission #{est.get('number')} créée VIDE, lignes refusées : {e}")
    return {"numero": est.get("number"), "id": est.get("id"),
            "total_avant_taxes": sum(l.montant for l in s.lignes)}



@router.get("/gazelle/soumissions")
def soumissions_client(client_id: str = Query(...)):
    """Soumissions Gazelle récentes d'un client, avec leur contenu complet :
    notes, options (tiers), lignes groupées et non groupées (nom, description, montant)."""
    from core.gazelle_api_client import GazelleAPIClient
    q = """query($c: String) { allEstimates(first: 20, filters: {clientId: $c}) {
      nodes { id number estimatedOn isArchived recommendedTierTotal notes
        allEstimateTiers { sequenceNumber isPrimary subtotal taxTotal total
          allUngroupedEstimateTierItems { name description amount quantity }
          allEstimateTierGroups { name
            allEstimateTierItems { name description amount quantity } } } } } }"""
    try:
        res = GazelleAPIClient()._execute_query(q, {"c": client_id})
    except Exception as e:
        raise HTTPException(502, str(e))
    return res


# --- Factures : lecture d'un client + création en BROUILLON (jamais envoyée) ---
_Q_FACTURES_CLIENT = """query($c: String) { allInvoices(first: 10, filters: {clientId: $c}) {
  nodes { id number status createdAt dueOn subTotal total notes topNotes taxPricingMode
    contact { id } assignedTo { id }
    allInvoiceItems { nodes { description type quantity amount taxable billable sequenceNumber
      masterServiceItem { id } piano { id } taxes { taxId name rate total } } } } } }"""


@router.get("/gazelle/factures")
def factures_client(client_id: str = Query(...)):
    """LECTURE — 10 dernières factures Gazelle d'un client, avec lignes et taxes (en direct)."""
    from core.gazelle_api_client import GazelleAPIClient
    try:
        res = GazelleAPIClient()._execute_query(_Q_FACTURES_CLIENT, {"c": client_id})
    except Exception as e:
        raise HTTPException(502, str(e))
    return res


class LigneFacture(BaseModel):
    description: str
    montant: float  # dollars, quantité 1
    taxable: bool = True
    service_id: Optional[str] = None  # MasterServiceItem
    piano_id: Optional[str] = None


class FactureIn(BaseModel):
    client_id: str
    lignes: List[LigneFacture]
    echeance: Optional[str] = None  # ISO AAAA-MM-JJ
    notes: Optional[str] = None
    top_notes: Optional[str] = None
    contact_id: Optional[str] = None
    assigne_a: Optional[str] = None


@router.post("/gazelle/facture")
def creer_facture(f: FactureIn):
    """Crée une facture Gazelle en BROUILLON (DRAFT), TPS/TVQ cochées.
    Rien n'est envoyé au client : l'envoi reste un geste humain dans Gazelle."""
    from core.gazelle_api_client import GazelleAPIClient
    from api.assistant_duplication import _CREATE_INVOICE, _build_taxes, _mutation_error_detail
    if not f.lignes:
        raise HTTPException(400, "Aucune ligne")
    items = []
    for i, l in enumerate(f.lignes):
        cents = int(round(l.montant * 100))
        item = {"description": l.description, "type": "LABOR_FIXED_RATE", "quantity": 100,
                "amount": cents, "taxable": l.taxable, "billable": True, "sequenceNumber": i,
                "taxes": _build_taxes(cents, l.taxable)}
        if l.service_id:
            item["masterServiceItemId"] = l.service_id
        if l.piano_id:
            item["pianoId"] = l.piano_id
        items.append(item)
    inp = {"clientId": f.client_id, "status": "DRAFT", "taxPricingMode": "EXCLUSIVE", "invoiceItems": items}
    for cle, val in (("dueOn", f.echeance), ("notes", f.notes), ("topNotes", f.top_notes),
                     ("contactId", f.contact_id), ("assignedToId", f.assigne_a)):
        if val:
            inp[cle] = val
    try:
        res = GazelleAPIClient()._execute_query(_CREATE_INVOICE, {"input": inp})
    except Exception as e:
        raise HTTPException(502, f"createInvoice : {e}")
    payload = ((res or {}).get("data") or {}).get("createInvoice") or {}
    inv = payload.get("invoice")
    if not inv:
        raise HTTPException(502, f"Gazelle a refusé la création ({_mutation_error_detail(payload)}) "
                                 f"{res.get('errors') if isinstance(res, dict) else ''}")
    return {"numero": inv.get("number"), "id": inv.get("id"), "statut": inv.get("status"),
            "echeance": inv.get("dueOn"), "sous_total": _dollars(inv.get("subTotal")),
            "total": _dollars(inv.get("total"))}


# --- Rendez-vous Gazelle (créé à la demande d'Allan depuis une conversation Claude) ---
class RendezVousIn(BaseModel):
    client_id: str
    user_id: str                       # technicien (1 event = 1 technicien)
    debut_montreal: str                # "2026-12-20T12:00" — heure de Montréal
    duree_min: int = 120
    titre: Optional[str] = None        # défaut : nom du client (format natif PTM)
    notes: Optional[str] = None
    piano_ids: List[str] = []
    accord: bool = True                # isTuning sur les pianos


@router.post("/gazelle/rendez-vous")
def creer_rendez_vous(r: RendezVousIn):
    """Crée un APPOINTMENT dans Gazelle au format natif PTM (durée en minutes, start en UTC,
    travelMode DRIVING, pas de location : l'adresse vient de la fiche client)."""
    from core.gazelle_api_client import GazelleAPIClient
    from core.timezone_utils import MONTREAL_TZ
    try:
        local = datetime.fromisoformat(r.debut_montreal)
    except ValueError:
        raise HTTPException(400, "debut_montreal invalide (attendu AAAA-MM-JJTHH:MM)")
    if local.tzinfo is None:
        local = local.replace(tzinfo=MONTREAL_TZ)
    start = local.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    gz = GazelleAPIClient()
    titre = r.titre
    if not titre:
        res = gz._execute_query("query($id: String!) { client(id: $id) { id companyName "
                                "defaultContact { firstName lastName } } }", {"id": r.client_id})
        c = (res.get("data") or {}).get("client") or {}
        dc = c.get("defaultContact") or {}
        titre = c.get("companyName") or f"{dc.get('firstName', '')} {dc.get('lastName', '')}".strip()
    inp = {"title": titre, "start": start, "duration": r.duree_min, "type": "APPOINTMENT",
           "travelMode": "DRIVING", "userId": r.user_id, "clientId": r.client_id}
    if r.notes:
        inp["notes"] = r.notes
    if r.piano_ids:
        inp["pianos"] = [{"pianoId": p, "isTuning": r.accord} for p in r.piano_ids]
    mut = """mutation($input: PrivateEventInput!) { createEvent(input: $input) {
      event { id title start duration type status user { id firstName } client { id }
              allEventPianos(first: 5) { nodes { piano { id make model } } } }
      mutationErrors { fieldName messages } } }"""
    try:
        res = gz._execute_query(mut, {"input": inp})
    except Exception as e:
        raise HTTPException(502, f"createEvent : {e}")
    payload = ((res or {}).get("data") or {}).get("createEvent") or {}
    ev = payload.get("event")
    if not ev:
        raise HTTPException(502, f"Gazelle a refusé le rendez-vous : {payload.get('mutationErrors')} "
                                 f"{res.get('errors') if isinstance(res, dict) else ''}")
    return {"evenement": ev, "start_utc": start}


# --- Ménage : supprimer un rendez-vous « Service: NOTE » créé par erreur par l'IA ---
_Q_EVENEMENT = """query($id: String!) { event(eventId: $id) { id title start type status notes
  client { id } allEventPianos(first: 5) { nodes { piano { id } } } } }"""


def _evenement(gz, eid: str) -> Dict[str, Any]:
    try:
        res = gz._execute_query(_Q_EVENEMENT, {"id": eid})
    except Exception as e:
        raise HTTPException(502, f"Gazelle : {e}")
    if res.get("errors"):
        raise HTTPException(502, str(res["errors"]))
    return (res.get("data") or {}).get("event") or {}


@router.get("/gazelle/evenement/{eid}")
def lire_evenement(eid: str):
    from core.gazelle_api_client import GazelleAPIClient
    return _evenement(GazelleAPIClient(), eid)


@router.delete("/gazelle/evenement/{eid}")
def supprimer_note_evenement(eid: str):
    """Supprime UNIQUEMENT un rendez-vous-note créé par l'IA (titre « Service: NOTE »,
    notes commençant par « NOTE: »). Tout autre rendez-vous est refusé."""
    from core.gazelle_api_client import GazelleAPIClient
    gz = GazelleAPIClient()
    ev = _evenement(gz, eid)
    if ev.get("title") != "Service: NOTE" or not (ev.get("notes") or "").startswith("NOTE: "):
        raise HTTPException(403, f"Refusé : ce rendez-vous n'est pas une note créée par l'IA ({ev.get('title')!r})")
    res = gz._execute_query("""mutation($id: String!) { deleteEvent(id: $id) { mutationErrors { fieldName messages } } }""", {"id": eid})
    if res.get("errors"):
        raise HTTPException(502, str(res["errors"]))
    err = ((res.get("data") or {}).get("deleteEvent") or {}).get("mutationErrors") or []
    if err:
        raise HTTPException(502, str(err))
    return {"supprime": eid, "titre": ev.get("title")}


@router.get("/gazelle/charge")
def charge_techniciens(debut: str = Query(...), fin: str = Query(...)):
    """LECTURE SEULE — charge par technicien et par jour (RV, blocs perso, source de la prise de RV).
    Sert à comprendre un déséquilibre (ex. Nicolas plein, JP vide)."""
    from core.gazelle_api_client import GazelleAPIClient
    from core.timezone_utils import MONTREAL_TZ
    noms = {"usr_HcCiFk7o0vZ9xAI0": "Nicolas", "usr_ofYggsCDt2JAVeNP": "Allan", "usr_ReUSmIJmBF86ilY1": "JP",
            "usr_QmEpdeM2xMgZVkDS": "JP", "usr_bbt59aCUqUaDWA8n": "Margot", "usr_HihJsEgkmpTEziJo": "À attribuer"}
    evs = GazelleAPIClient().get_appointments(start_date_override=debut, end_date_override=fin) or []
    sortie = []
    for e in evs:
        if (e.get("status") or "").upper() in ("CANCELLED", "CANCELED"):
            continue
        try:
            d = datetime.fromisoformat(e["start"].replace("Z", "+00:00")).astimezone(MONTREAL_TZ)
        except Exception:
            continue
        uid = (e.get("user") or {}).get("id")
        cb = (e.get("createdBy") or {}).get("id")
        sortie.append({"jour": d.strftime("%Y-%m-%d"), "heure": d.strftime("%H:%M"), "tech": noms.get(uid, uid),
                       "type": e.get("type"), "titre": (e.get("title") or "")[:60], "duree_min": e.get("duration"),
                       "journee": e.get("isAllDay"), "source": e.get("source"), "cree_par": noms.get(cb, cb),
                       "cree_le": (e.get("createdAt") or "")[:10]})
    sortie.sort(key=lambda x: (x["jour"], x["tech"] or "", x["heure"]))
    return {"evenements": sortie}


@router.get("/gazelle/timeline-piano")
def timeline_piano_gazelle(client_id: str = Query(...), piano_id: str = Query(...), limite: int = Query(15, le=50)):
    """Entrées timeline EN DIRECT de Gazelle pour un piano (vérification après ménage)."""
    from core.gazelle_api_client import GazelleAPIClient
    gz = GazelleAPIClient()
    try:
        res = gz._execute_query("""query($c: String!, $n: Int!) { allTimelineEntries(clientId: $c, first: $n) {
          edges { node { id occurredAt type summary comment relatedId relatedType piano { id } } } } }""", {"c": client_id, "n": 100})
    except Exception as e:
        raise HTTPException(502, str(e))
    edges = (((res.get("data") or {}).get("allTimelineEntries") or {}).get("edges")) or []
    out = [e["node"] for e in edges if (e["node"].get("piano") or {}).get("id") == piano_id]
    return {"entrees": out[:limite]}


@router.post("/gazelle/test-note-piano")
def test_note_piano(client_id: str = Query(...), piano_id: str = Query(...),
                    date: Optional[str] = Query(None)):
    """DIAGNOSTIC (direction) — écrit une note de test createClientLog sur un piano et
    compare le piano avant/après (statut, dernier service). La note porte la signature
    « Saisi par Claude IA » : elle se retire avec DELETE /taches/gazelle/timeline/{id}."""
    from core.gazelle_api_client import GazelleAPIClient
    gz = GazelleAPIClient()
    q = """query($p: String!) { piano(id: $p) { id status calculatedLastService manualLastService } }"""

    def lire():
        return ((gz._execute_query(q, {"p": piano_id}).get("data") or {}).get("piano")) or {}
    try:
        avant = lire()
        gz.create_client_log(client_id, "TEST de l'assistant — note à supprimer.\n\nSaisi par Claude IA",
                             piano_id=piano_id, created_at=date)
        apres = lire()
    except Exception as e:
        raise HTTPException(502, f"Gazelle : {e}")
    return {"avant": avant, "apres": apres}


@router.delete("/copie/timeline/{external_id}")
def retirer_copie_timeline(external_id: str):
    """Retire de la COPIE Supabase une entrée qui n'existe plus dans Gazelle
    (la synchro n'efface jamais). Refuse si l'entrée existe encore dans Gazelle."""
    h = _db()._get_headers()
    rows = _check(requests.get(f"{_db().api_url}/gazelle_timeline_entries?select=external_id,client_id,piano_id,title,description,entry_type&external_id=eq.{external_id}",
                               headers=h, timeout=15)) or []
    if not rows:
        raise HTTPException(404, "Absente de la copie")
    r = rows[0]
    encore = timeline_piano_gazelle(client_id=r["client_id"], piano_id=r["piano_id"], limite=50)["entrees"]
    if any(e["id"] == external_id for e in encore):
        raise HTTPException(409, "Elle existe encore dans Gazelle : rien retiré")
    _check(requests.delete(f"{_db().api_url}/gazelle_timeline_entries?external_id=eq.{external_id}", headers=h, timeout=15))
    return {"retire": external_id, "titre": r.get("title"), "type": r.get("entry_type")}


@router.delete("/gazelle/timeline/{entry_id}")
def supprimer_entree_ia(entry_id: str, client_id: str = Query(...), piano_id: str = Query(...)):
    """Supprime une entrée de timeline Gazelle SEULEMENT si elle a été écrite par l'IA
    (signature « Saisi par Claude IA »). Puis la retire de la copie Supabase."""
    from core.gazelle_api_client import GazelleAPIClient
    entrees = timeline_piano_gazelle(client_id=client_id, piano_id=piano_id, limite=50)["entrees"]
    e = next((x for x in entrees if x["id"] == entry_id), None)
    if not e:
        raise HTTPException(404, "Entrée introuvable pour ce piano")
    if "Saisi par Claude IA" not in (e.get("comment") or ""):
        raise HTTPException(403, "Refusé : cette entrée n'a pas été écrite par l'IA")
    gz = GazelleAPIClient()
    try:
        # L'identifiant à supprimer est celui de l'objet lié (relatedId), pas celui de l'entrée
        res = gz._execute_query("""mutation($id: String!) { deleteClientLog(id: $id) { mutationErrors { fieldName messages } } }""", {"id": e.get("relatedId") or entry_id})
    except Exception as ex:
        raise HTTPException(502, f"Gazelle : {ex}")
    err = ((res.get("data") or {}).get("deleteClientLog") or {}).get("mutationErrors") or []
    if err:
        raise HTTPException(502, str(err))
    requests.delete(f"{_db().api_url}/gazelle_timeline_entries?external_id=eq.{entry_id}", headers=_db()._get_headers(), timeout=15)
    return {"supprime": entry_id}


@router.get("/gazelle/schema-type")
def schema_type(nom: str = Query(...)):
    """Lecture seule : champs d'un type Gazelle (diagnostic)."""
    from core.gazelle_api_client import GazelleAPIClient
    r = GazelleAPIClient()._execute_query("""query($n:String!){ __type(name:$n){ name fields { name type { name kind ofType { name } } } } }""", {"n": nom})
    return (r.get("data") or {}).get("__type")


@router.get("/gazelle/usage-services")
def usage_services(depuis: str = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$"),
                   jusqu: Optional[str] = Query(None, pattern=r"^\d{4}-\d{2}-\d{2}$")):
    """LECTURE — Nombre de factures par service du catalogue (MasterServiceItem) sur une période.

    Sert à décider des services offerts (ex. fusionner deux services peu distincts)."""
    from core.gazelle_api_client import GazelleAPIClient
    api = GazelleAPIClient()
    q = """query U($cursor: String, $f: PrivateAllInvoicesFilter) {
      allInvoices(first: 100, after: $cursor, filters: $f) {
        edges { node { id allInvoiceItems { nodes { masterServiceItem { id name } } } } }
        pageInfo { hasNextPage endCursor } } }"""
    filtre: Dict[str, Any] = {"invoiceDateGet": depuis}
    if jusqu:
        filtre["invoiceDateLet"] = jusqu
    compte: Dict[str, Dict[str, Any]] = {}
    total, cursor = 0, None
    for _ in range(300):
        v: Dict[str, Any] = {"f": filtre}
        if cursor:
            v["cursor"] = cursor
        try:
            res = api._execute_query(q, v)
        except Exception as e:
            raise HTTPException(502, f"Gazelle : {e}")
        if res.get("errors"):
            raise HTTPException(502, f"Gazelle : {res['errors']}")
        bloc = (res.get("data") or {}).get("allInvoices") or {}
        for e in bloc.get("edges") or []:
            total += 1
            vus = set()
            for it in ((e["node"].get("allInvoiceItems") or {}).get("nodes") or []):
                m = it.get("masterServiceItem")
                if m and m["id"] not in vus:
                    vus.add(m["id"])
                    c = compte.setdefault(m["id"], {"id": m["id"], "service": _nom_i18n(m.get("name")), "factures": 0})
                    c["factures"] += 1
        pi = bloc.get("pageInfo") or {}
        if not pi.get("hasNextPage"):
            break
        cursor = pi.get("endCursor")
    return {"depuis": depuis, "jusqu": jusqu, "factures": total,
            "services": sorted(compte.values(), key=lambda c: -c["factures"])}
