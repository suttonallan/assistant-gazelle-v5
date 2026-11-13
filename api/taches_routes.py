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


class NoteClientIn(BaseModel):
    client_id: str
    texte: str
    piano_id: Optional[str] = None
    date: Optional[str] = None  # ISO ; défaut : maintenant


@router.post("/gazelle/note-client")
def note_client(n: NoteClientIn):
    """Note simple (📝) dans la chronologie d'un client Gazelle — jamais comptée comme service."""
    if not n.client_id.startswith("cli_") or not n.texte.strip():
        raise HTTPException(400, "client_id ou texte invalide")
    from core.gazelle_api_client import GazelleAPIClient
    try:
        GazelleAPIClient().create_client_log(n.client_id, "📝 " + n.texte.strip(), piano_id=n.piano_id,
                                             created_at=n.date)
    except Exception as e:
        raise HTTPException(502, f"Gazelle : {e}")
    return {"ok": True}


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
    mots = ("note", "timeline", "comment", "history", "delete", "event", "log")
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


@router.post("/gazelle/service-prix")
def changer_prix_service(service_id: str = Query(..., pattern=r"^mit_[A-Za-z0-9]+$"),
                         prix: float = Query(..., gt=0, lt=100000)):
    """Change SEULEMENT le prix d'un article de la Master Service List de Gazelle.
    Les factures et soumissions existantes gardent leur montant : seules les nouvelles lignes prennent le nouveau prix."""
    from core.gazelle_api_client import GazelleAPIClient
    gz = GazelleAPIClient()
    lire = "query { allMasterServiceItems { id name amount isArchived } }"
    avant = next((i for i in ((gz._execute_query(lire).get("data") or {}).get("allMasterServiceItems") or [])
                  if i["id"] == service_id), None)
    if not avant:
        raise HTTPException(404, "Article introuvable dans la Master Service List")
    res = gz._execute_query("""mutation($id: String!, $i: PrivateMasterServiceItemInput!) {
      updateMasterServiceItem(id: $id, input: $i) { masterServiceItem { id amount } mutationErrors { fieldName messages } } }""",
                            {"id": service_id, "i": {"amount": int(round(prix * 100))}})
    m = (res.get("data") or {}).get("updateMasterServiceItem") or {}
    if res.get("errors") or m.get("mutationErrors"):
        raise HTTPException(502, str(res.get("errors") or m.get("mutationErrors")))
    return {"article": _nom_i18n(avant.get("name")), "avant": (avant.get("amount") or 0) / 100,
            "apres": ((m.get("masterServiceItem") or {}).get("amount") or 0) / 100}


@router.post("/gazelle/service-accord")
def cocher_service_accord(service_id: str = Query(..., pattern=r"^mit_[A-Za-z0-9]+$"),
                          accord: bool = Query(True)):
    """Coche (ou décoche) « accord » (isTuning) sur un article de la Master Service List.
    Un RV avec un service coché « accord » retient les rappels « piano dû » et met à jour
    la date du dernier accord quand il est complété. Rien d'autre n'est modifié."""
    from core.gazelle_api_client import GazelleAPIClient
    gz = GazelleAPIClient()
    lire = "query { allMasterServiceItems { id name isTuning isArchived } }"
    avant = next((i for i in ((gz._execute_query(lire).get("data") or {}).get("allMasterServiceItems") or [])
                  if i["id"] == service_id), None)
    if not avant:
        raise HTTPException(404, "Article introuvable dans la Master Service List")
    res = gz._execute_query("""mutation($id: String!, $i: PrivateMasterServiceItemInput!) {
      updateMasterServiceItem(id: $id, input: $i) { masterServiceItem { id isTuning } mutationErrors { fieldName messages } } }""",
                            {"id": service_id, "i": {"isTuning": accord}})
    m = (res.get("data") or {}).get("updateMasterServiceItem") or {}
    if res.get("errors") or m.get("mutationErrors"):
        raise HTTPException(502, str(res.get("errors") or m.get("mutationErrors")))
    return {"article": _nom_i18n(avant.get("name")), "avant": bool(avant.get("isTuning")),
            "apres": bool((m.get("masterServiceItem") or {}).get("isTuning"))}


@router.get("/gazelle/accords-non-comptes")
def accords_non_comptes(jours_avant: int = Query(30, ge=0, le=365), jours_apres: int = Query(90, ge=0, le=365)):
    """LECTURE — services d'accord non cochés « accord » dans la Master Service List, et RV
    contenant un accord où rien n'est coché « accord » (le rappel « piano dû » partirait)."""
    from core.gazelle_api_client import GazelleAPIClient
    from modules.data_quality.accords_non_comptes import services_accord_non_coches, rv_accord_non_compte
    gz = GazelleAPIClient()
    return {"services": services_accord_non_coches(gz),
            "rendez_vous": rv_accord_non_compte(gz, jours_avant, jours_apres)}


@router.get("/gazelle/rappels-a-risque")
def rappels_a_risque_route(jours_avant: int = Query(7, ge=0, le=120), jours_apres: int = Query(21, ge=0, le=120)):
    """LECTURE — pianos qui peuvent recevoir « piano dû » malgré un RV prévu, et RV d'accord
    complétés dont la date du dernier accord n'a pas avancé."""
    from core.gazelle_api_client import GazelleAPIClient
    from modules.data_quality.accords_non_comptes import rappels_a_risque
    return {"cas": rappels_a_risque(GazelleAPIClient(), jours_avant, jours_apres)}


_CHAMPS_DISPO = ("id name startTime endTime startOfDayType preferredSlotPolicy preferredSlotTimes "
                 "adjustPreferredSlots roundingMinutes recurrenceRule startDate endDate")


@router.get("/gazelle/disponibilites")
def disponibilites(user_id: str = Query(..., pattern=r"^usr_[A-Za-z0-9]+$")):
    """LECTURE — disponibilités du planificateur Gazelle d'un technicien (heures préférées,
    ajustement selon le déplacement, arrondi)."""
    from core.gazelle_api_client import GazelleAPIClient
    res = GazelleAPIClient()._execute_query(
        "query($u: String!) { allSchedulerAvailabilities(userId: $u) { %s } }" % _CHAMPS_DISPO, {"u": user_id})
    if res.get("errors"):
        raise HTTPException(502, str(res["errors"]))
    return {"disponibilites": (res.get("data") or {}).get("allSchedulerAvailabilities") or []}


_LIEU = "type addressLine manualLat manualLng coordinates { latitude longitude } what3words { what3words }"
_DISPO_COMPLETE = (_CHAMPS_DISPO + " endOfDayType isExclusive maxAppointmentsPerDay includeDates excludeDates "
                   "serviceArea { id } floatingDowntimeRules { startTime endTime duration } "
                   "startOfDayLocation { %s } endOfDayLocation { %s }" % (_LIEU, _LIEU))


def _lieu_input(l: Dict[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Any] = {"type": l.get("type")}
    if l.get("addressLine"):
        out["addressLine"] = l["addressLine"]
    if (l.get("coordinates") or {}).get("latitude"):
        out["coordinates"] = {"latitude": l["coordinates"]["latitude"], "longitude": l["coordinates"]["longitude"]}
    if (l.get("what3words") or {}).get("what3words"):
        out["what3words"] = {"what3words": l["what3words"]["what3words"]}
    return out


@router.post("/gazelle/disponibilite/{dispo_id}/ajuster-selon-deplacement")
def dispo_ajuster(dispo_id: str, user_id: str = Query(..., pattern=r"^usr_[A-Za-z0-9]+$"), actif: bool = Query(True)):
    """Coche (ou décoche) « Allow preferred time slots to be adjusted based on travel time » sur une
    disponibilité. Gazelle exige la disponibilité complète : on renvoie tous les réglages existants
    tels quels, puis on relit et compare champ par champ (rien d'autre ne doit changer)."""
    from core.gazelle_api_client import GazelleAPIClient
    gz = GazelleAPIClient()
    q = "query($i: String!, $u: String!) { schedulerAvailability(id: $i, userId: $u) { %s } }" % _DISPO_COMPLETE
    r0 = gz._execute_query(q, {"i": dispo_id, "u": user_id})
    avant = (r0.get("data") or {}).get("schedulerAvailability")
    if not avant:
        raise HTTPException(404, f"Disponibilité introuvable : {r0.get('errors')}")
    for cle in ("startOfDayLocation", "endOfDayLocation"):
        if (avant.get(cle) or {}).get("manualLat") or (avant.get(cle) or {}).get("manualLng"):
            raise HTTPException(409, "Lieu avec position manuelle : non modifiable sans risque par l'API, à faire dans Gazelle")
    if bool(avant.get("adjustPreferredSlots")) == actif:
        return {"nom": avant.get("name"), "change": False, "apres": actif}
    entree = {k: avant.get(k) for k in ("name", "startDate", "endDate", "startOfDayType", "startTime", "endOfDayType",
                                         "endTime", "recurrenceRule", "includeDates", "excludeDates",
                                         "preferredSlotPolicy", "preferredSlotTimes", "isExclusive",
                                         "maxAppointmentsPerDay", "roundingMinutes")}
    entree.update({"adjustPreferredSlots": actif, "serviceAreaId": (avant.get("serviceArea") or {}).get("id"),
                   "startOfDayLocation": _lieu_input(avant.get("startOfDayLocation") or {}),
                   "endOfDayLocation": _lieu_input(avant.get("endOfDayLocation") or {}),
                   "floatingDowntimeRules": avant.get("floatingDowntimeRules") or []})
    res = gz._execute_query("""mutation($i: String!, $in: PrivateSchedulerAvailabilityInput!) {
      updateSchedulerAvailability(id: $i, input: $in) { availability { id } mutationErrors { fieldName messages } } }""",
                            {"i": dispo_id, "in": entree})
    m = (res.get("data") or {}).get("updateSchedulerAvailability") or {}
    if res.get("errors") or m.get("mutationErrors"):
        raise HTTPException(502, str(res.get("errors") or m.get("mutationErrors")))
    apres = ((gz._execute_query(q, {"i": dispo_id, "u": user_id}).get("data") or {}).get("schedulerAvailability")) or {}
    autres = [k for k in avant if k != "adjustPreferredSlots" and avant.get(k) != apres.get(k)]
    return {"nom": avant.get("name"), "change": True, "avant": avant.get("adjustPreferredSlots"),
            "apres": apres.get("adjustPreferredSlots"), "autres_champs_modifies": autres,
            "detail_ecarts": {k: [avant.get(k), apres.get(k)] for k in autres}}


@router.get("/gazelle/piano/{piano_id}/accord")
def piano_accord(piano_id: str):
    """LECTURE — dates de dernier service (calculée, manuelle, par RV) et prochain accord prévu d'un piano."""
    from core.gazelle_api_client import GazelleAPIClient
    res = GazelleAPIClient()._execute_query("""query($p: String!) { piano(id: $p) { id make model status
      serviceIntervalMonths calculatedLastService manualLastService eventLastService calculatedNextService
      nextTuningScheduled { id start } client { id } } }""", {"p": piano_id})
    if res.get("errors"):
        res = GazelleAPIClient()._execute_query("""query($p: String!) { piano(id: $p) { id make model status
          serviceIntervalMonths calculatedLastService manualLastService eventLastService calculatedNextService client { id } } }""",
                                                {"p": piano_id})
    return {"piano": (res.get("data") or {}).get("piano"), "erreurs": res.get("errors")}


@router.post("/gazelle/service-copie")
def copier_service(source_id: str = Query(..., pattern=r"^mit_[A-Za-z0-9]+$"),
                   nom_fr: str = Query(..., min_length=2, max_length=120),
                   nom_en: str = Query(..., min_length=2, max_length=120),
                   prix: float = Query(..., gt=0, lt=100000)):
    """Crée un article de la Master Service List en copiant les réglages d'un article existant
    (groupe, type, taxes, réservation en ligne, techniciens) ; seuls le nom et le prix changent."""
    from core.gazelle_api_client import GazelleAPIClient
    gz = GazelleAPIClient()
    champs = "id name description type isTaxable isAnyUser isSelfSchedulable isTuning duration masterServiceGroup { id }"
    items = (gz._execute_query("query { allMasterServiceItems { %s isArchived } }" % champs).get("data") or {}).get("allMasterServiceItems") or []
    src = next((i for i in items if i["id"] == source_id), None)
    if not src:
        raise HTTPException(404, "Article source introuvable")
    if any(_nom_i18n(i.get("name")).strip().lower() == nom_fr.strip().lower() and not i.get("isArchived") for i in items):
        raise HTTPException(409, "Un article actif porte déjà ce nom")
    entree = {"name": {"fr_CA": nom_fr, "en_US": nom_en}, "amount": int(round(prix * 100)),
              "type": src.get("type"), "isTaxable": src.get("isTaxable"), "isAnyUser": src.get("isAnyUser"),
              "isSelfSchedulable": src.get("isSelfSchedulable"), "isTuning": src.get("isTuning"),
              "duration": src.get("duration"), "masterServiceGroupId": (src.get("masterServiceGroup") or {}).get("id")}
    entree = {k: v for k, v in entree.items() if v is not None}
    res = gz._execute_query("""mutation($i: PrivateMasterServiceItemInput!) { createMasterServiceItem(input: $i) {
      masterServiceItem { id name amount isTaxable isSelfSchedulable } mutationErrors { fieldName messages } } }""", {"i": entree})
    m = (res.get("data") or {}).get("createMasterServiceItem") or {}
    if res.get("errors") or m.get("mutationErrors"):
        raise HTTPException(502, str(res.get("errors") or m.get("mutationErrors")))
    return {"cree": m.get("masterServiceItem"), "copie_de": _nom_i18n(src.get("name"))}


@router.get("/boutique/catalogue")
def boutique_catalogue():
    """LECTURE — articles de la boutique « avec l'accord », prix en direct de la Master Service List."""
    from core.boutique_accord import catalogue
    from core.gazelle_api_client import GazelleAPIClient
    items = ((GazelleAPIClient()._execute_query("query { allMasterServiceItems { id amount isArchived } }")
              .get("data") or {}).get("allMasterServiceItems") or [])
    prix = {i["id"]: (i.get("amount") or 0) / 100 for i in items if not i.get("isArchived")}
    return {"articles": catalogue(prix)}


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
            maj = {"estimateTiers": tiers}
            if s.notes:
                maj["notes"] = s.notes
            r = gz.update_estimate(s.completer_id, maj)
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



# Cycles de vie visés par les rappels personnalisés (lecture seule pour l'instant)
CYCLES_RAPPEL_PERSO = {
    "lcy_VEOrJHKlyLhGaNa4": "fr",   # Français
    "lcy_JnzQO9dhl9AeY5MQ": "fr",   # Français 1x/an
    "lcy_bWUWxo81RTbyQc7x": "en",   # English
}


@router.get("/gazelle/rappels-a-venir")
def rappels_a_venir(jours: int = Query(35, ge=1, le=90)):
    """LECTURE — pianos actifs dont le prochain service calculé par Gazelle tombe d'ici `jours` jours,
    pour les clients des cycles Français, Français 1x/an et English. Sert à préparer les rappels personnalisés."""
    from datetime import timedelta
    from core.gazelle_api_client import GazelleAPIClient
    gz = GazelleAPIClient()
    debut = aujourdhui_montreal()
    fin = debut + timedelta(days=jours)
    req = """query($a: String) { allPianos(first: 100, after: $a) {
      nodes { id status make model type location calculatedNextService calculatedLastService
        client { id companyName lifecycle { id } } }
      pageInfo { hasNextPage endCursor } } }"""
    out, apres, pages, erreurs = [], None, 0, None
    while pages < 200:
        res = gz._execute_query(req, {"a": apres})
        if res.get("errors"):
            erreurs = res["errors"]
            break
        bloc = (res.get("data") or {}).get("allPianos") or {}
        for p in bloc.get("nodes") or []:
            c = p.get("client") or {}
            lc = (c.get("lifecycle") or {}).get("id")
            nxt = (p.get("calculatedNextService") or "")[:10]
            if p.get("status") not in (None, "ACTIVE") or lc not in CYCLES_RAPPEL_PERSO or not nxt:
                continue
            if debut.isoformat() <= nxt <= fin.isoformat():
                out.append({"client_id": c.get("id"), "client": c.get("companyName"), "langue": CYCLES_RAPPEL_PERSO[lc],
                            "piano_id": p["id"], "piano": " ".join(x for x in (p.get("make"), p.get("model")) if x),
                            "lieu": p.get("location"), "prochain": nxt, "dernier": (p.get("calculatedLastService") or "")[:10]})
        pages += 1
        info = bloc.get("pageInfo") or {}
        if not info.get("hasNextPage"):
            break
        apres = info.get("endCursor")
    out.sort(key=lambda r: r["prochain"])
    return {"de": debut.isoformat(), "a": fin.isoformat(), "pages": pages, "nombre": len(out), "pianos": out, "erreurs": erreurs}


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


_Q_FACTURES_ECHUES = """query($f: PrivateAllInvoicesFilter, $after: String) {
  allInvoices(first: 100, after: $after, filters: $f) {
    pageInfo { hasNextPage endCursor }
    nodes { id number status createdAt dueOn total
      client { id companyName defaultContact { firstName lastName } }
      altBillingCompanyName assignedTo { id firstName }
      allInvoicePayments { nodes { id type amount paidAt notes } } } } }"""


@router.get("/gazelle/factures-echues")
def factures_echues():
    """LECTURE — toutes les factures Gazelle au statut OVERDUE (échues), avec paiements déjà inscrits."""
    from core.gazelle_api_client import GazelleAPIClient
    gz = GazelleAPIClient()
    out, after = [], None
    for _ in range(20):
        res = gz._execute_query(_Q_FACTURES_ECHUES, {"f": {"status": "OVERDUE"}, "after": after})
        if res.get("errors"):
            raise HTTPException(502, str(res["errors"]))
        page = (res.get("data") or {}).get("allInvoices") or {}
        out.extend(page.get("nodes") or [])
        if not (page.get("pageInfo") or {}).get("hasNextPage"):
            break
        after = page["pageInfo"]["endCursor"]
    return {"nombre": len(out), "factures": out}


@router.get("/gazelle/schema/type")
def schema_type(nom: str = Query(...)):
    """LECTURE — introspection GraphQL d'un type Gazelle (champs, arguments). Aucune donnée client."""
    from core.gazelle_api_client import GazelleAPIClient
    q = """query($n: String!) { __type(name: $n) { name kind
      fields { name args { name type { name kind ofType { name kind ofType { name } } } }
        type { name kind ofType { name } } }
      inputFields { name type { name kind ofType { name kind ofType { name } } } }
      enumValues { name } } }"""
    return GazelleAPIClient()._execute_query(q, {"n": nom})


_Q_FACTURE_SOLDE = """query($id: String!) { invoice(id: $id) { id number status total
  allInvoicePayments { nodes { id type amount paidAt notes } } } }"""

_ADD_PAYMENT = """mutation($inv: String!, $amt: Int!, $type: InvoicePaymentType, $notes: String, $paid: CoreDateTime) {
  addInvoicePayment(invoiceId: $inv, paymentAmount: $amt, paymentType: $type, paymentNotes: $notes, paymentPaidAt: $paid) {
    invoice { id number status total allInvoicePayments { nodes { id type amount paidAt notes } } }
    mutationErrors { fieldName messages } } }"""


class PaiementIn(BaseModel):
    montant: float                     # dollars
    date_paiement: str                 # AAAA-MM-JJ (date du virement, heure de Montréal)
    type: str = "ELECTRONIC_FUNDS_TRANSFER"
    notes: Optional[str] = None


@router.post("/gazelle/facture/{invoice_id}/paiement")
def inscrire_paiement(invoice_id: str, p: PaiementIn):
    """Inscrit un paiement reçu (ex. virement Interac) sur une facture Gazelle OUVERTE ou ÉCHUE.
    Gazelle le transmet ensuite à QuickBooks. Garde-fous : jamais plus que le solde, refus si un
    paiement du même montant à la même date existe déjà (anti-doublon). Rien n'est envoyé au client."""
    from core.gazelle_api_client import GazelleAPIClient
    gz = GazelleAPIClient()
    inv = ((gz._execute_query(_Q_FACTURE_SOLDE, {"id": invoice_id}) or {}).get("data") or {}).get("invoice")
    if not inv:
        raise HTTPException(404, "Facture introuvable")
    if inv.get("status") not in ("OPEN", "OVERDUE"):
        raise HTTPException(409, f"Statut {inv.get('status')} — rien inscrit")
    cents = int(round(p.montant * 100))
    deja = inv["allInvoicePayments"]["nodes"]
    solde = (inv.get("total") or 0) - sum(x.get("amount") or 0 for x in deja)
    if cents <= 0 or cents > solde:
        raise HTTPException(409, f"Montant {cents/100:.2f} $ refusé : solde de la facture {solde/100:.2f} $")
    if any(x.get("amount") == cents and (x.get("paidAt") or "")[:10] == p.date_paiement for x in deja):
        raise HTTPException(409, "Un paiement identique (montant et date) existe déjà — rien inscrit")
    # Midi heure de Montréal : la date reste la bonne quel que soit le fuseau de lecture.
    paye_le = f"{p.date_paiement}T17:00:00Z"
    res = gz._execute_query(_ADD_PAYMENT, {"inv": invoice_id, "amt": cents, "type": p.type,
                                           "notes": p.notes, "paid": paye_le})
    payload = ((res or {}).get("data") or {}).get("addInvoicePayment") or {}
    if res.get("errors") or payload.get("mutationErrors") or not payload.get("invoice"):
        raise HTTPException(502, f"Gazelle a refusé : {payload.get('mutationErrors') or res.get('errors')}")
    i = payload["invoice"]
    return {"numero": i.get("number"), "statut": i.get("status"), "total": _dollars(i.get("total")),
            "paiements": i["allInvoicePayments"]["nodes"]}


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


_Q_FACTURE_UNE = """query($id: String!) { invoice(id: $id) { id number status
  client { id }
  allInvoiceItems { nodes { description type quantity amount taxable billable sequenceNumber
    masterServiceItem { id } piano { id } } } } }"""

_Q_CLIENT_FACTURATION = """query($id: String!) { client(id: $id) { id companyName
  defaultContact { firstName lastName defaultEmail { email } defaultPhone { phoneNumber }
    defaultLocation { street1 street2 municipality postalCode region countryCode } } } }"""

_UPDATE_INVOICE = """mutation($id: String!, $input: PrivateUpdateInvoiceInput!) {
  updateInvoice(id: $id, input: $input) {
    invoice { id number status subTotal total altBillingCompanyName altBillingFirstName altBillingLastName assignedTo { id } }
    mutationErrors { fieldName messages } } }"""


class LigneTexte(BaseModel):
    sequence: int          # sequenceNumber de la ligne (0 = première)
    description: str


class FactureMajIn(BaseModel):
    descriptions: List[LigneTexte] = []
    facturer_a_client_id: Optional[str] = None   # facturation alternative (ex. Piano Vertu)
    assigne_a: Optional[str] = None              # technicien Gazelle (usr_…) — ex. commission


@router.patch("/gazelle/facture/{invoice_id}")
def maj_facture(invoice_id: str, m: FactureMajIn):
    """Modifie une facture Gazelle NON PAYÉE (brouillon ou ouverte) : texte des lignes et/ou
    facturation alternative vers un autre client Gazelle. Montants et taxes inchangés.
    Rien n'est envoyé."""
    from core.gazelle_api_client import GazelleAPIClient
    from api.assistant_duplication import _build_taxes
    gz = GazelleAPIClient()
    inv = ((gz._execute_query(_Q_FACTURE_UNE, {"id": invoice_id}) or {}).get("data") or {}).get("invoice")
    if not inv:
        raise HTTPException(404, "Facture introuvable")
    # Brouillon, ou facture ouverte non payée (pas encore réglée) : on peut encore en corriger le texte.
    if inv.get("status") not in ("DRAFT", "OPEN", "OVERDUE"):
        raise HTTPException(409, f"Statut {inv.get('status')} — seules les factures non payées peuvent être modifiées ici")
    inp: Dict[str, Any] = {}
    if m.descriptions:
        nouv = {d.sequence: d.description for d in m.descriptions}
        items = []
        for it in sorted(inv["allInvoiceItems"]["nodes"], key=lambda x: x.get("sequenceNumber") or 0):
            seq = it.get("sequenceNumber") or 0
            item = {"description": nouv.get(seq, it.get("description")), "type": it.get("type"),
                    "quantity": it.get("quantity"), "amount": it.get("amount"),
                    "taxable": it.get("taxable"), "billable": it.get("billable"), "sequenceNumber": seq,
                    "taxes": _build_taxes(int((it.get("amount") or 0) * (it.get("quantity") or 100) / 100),
                                          it.get("taxable"))}
            if (it.get("masterServiceItem") or {}).get("id"):
                item["masterServiceItemId"] = it["masterServiceItem"]["id"]
            if (it.get("piano") or {}).get("id"):
                item["pianoId"] = it["piano"]["id"]
            items.append(item)
        inp["invoiceItems"] = items
    if m.facturer_a_client_id:
        c = ((gz._execute_query(_Q_CLIENT_FACTURATION, {"id": m.facturer_a_client_id}) or {})
             .get("data") or {}).get("client")
        if not c:
            raise HTTPException(404, "Client de facturation introuvable")
        dc = c.get("defaultContact") or {}
        loc = dc.get("defaultLocation") or {}
        for cle, val in (("altBillingCompanyName", c.get("companyName")),
                         ("altBillingFirstName", dc.get("firstName")), ("altBillingLastName", dc.get("lastName")),
                         ("altBillingEmail", (dc.get("defaultEmail") or {}).get("email")),
                         ("altBillingPhone", (dc.get("defaultPhone") or {}).get("phoneNumber")),
                         ("altBillingStreet1", loc.get("street1")), ("altBillingStreet2", loc.get("street2")),
                         ("altBillingMunicipality", loc.get("municipality")),
                         ("altBillingPostalCode", loc.get("postalCode")),
                         ("altBillingCountryCode", loc.get("countryCode")),
                         # Gazelle n'accepte que les provinces/États CA/US comme région
                         ("altBillingRegion", loc.get("region") if (loc.get("countryCode") or "CA") in ("CA", "US") else None)):
            if val:
                inp[cle] = val
    if m.assigne_a:
        inp["assignedToId"] = m.assigne_a
    if not inp:
        raise HTTPException(400, "Rien à modifier")
    res = gz._execute_query(_UPDATE_INVOICE, {"id": invoice_id, "input": inp})
    payload = ((res or {}).get("data") or {}).get("updateInvoice") or {}
    if payload.get("mutationErrors") or not payload.get("invoice"):
        raise HTTPException(502, f"Gazelle a refusé : {payload.get('mutationErrors')} {res.get('errors') if isinstance(res, dict) else ''}")
    i = payload["invoice"]
    return {"numero": i.get("number"), "statut": i.get("status"), "sous_total": _dollars(i.get("subTotal")),
            "total": _dollars(i.get("total")),
            "facture_a": i.get("altBillingCompanyName") or " ".join(
                x for x in (i.get("altBillingFirstName"), i.get("altBillingLastName")) if x) or None,
            "assigne_a": (i.get("assignedTo") or {}).get("id")}


_Q_FACTURE_DETAILS = """query($id: String!) { invoice(id: $id) { id number status subTotal taxTotal total
  clientUrl acceptElectronicPayment acceptedElectronicPaymentMethods
  altBillingCompanyName altBillingEmail altBillingCountryCode
  client { id companyName localization { id locale } defaultClientLocalization { id locale } }
  allInvoiceItems { nodes { sequenceNumber description amount taxable } } } }"""


@router.get("/gazelle/facture/{invoice_id}/details")
def details_facture(invoice_id: str):
    """LECTURE — une facture Gazelle : statut, lien client (paiement), facturation alt., langue."""
    from core.gazelle_api_client import GazelleAPIClient
    res = GazelleAPIClient()._execute_query(_Q_FACTURE_DETAILS, {"id": invoice_id})
    if res.get("errors"):
        raise HTTPException(502, str(res["errors"]))
    inv = (res.get("data") or {}).get("invoice")
    if not inv:
        raise HTTPException(404, "Facture introuvable")
    return inv


class NotesFactureIn(BaseModel):
    notes: Optional[str] = None
    top_notes: Optional[str] = None


@router.patch("/gazelle/facture/{invoice_id}/notes")
def maj_notes_facture(invoice_id: str, n: NotesFactureIn):
    """Modifie SEULEMENT le texte des notes (bas/haut) d'une facture non payée, même déjà
    envoyée. Montants, lignes et taxes inchangés. Rien n'est renvoyé au client."""
    from core.gazelle_api_client import GazelleAPIClient
    inv = details_facture(invoice_id)
    if inv.get("status") not in ("DRAFT", "OPEN", "OVERDUE"):
        raise HTTPException(409, f"Statut {inv.get('status')} — rien modifié")
    inp = {k: v for k, v in (("notes", n.notes), ("topNotes", n.top_notes)) if v is not None}
    if not inp:
        raise HTTPException(400, "Rien à modifier")
    res = GazelleAPIClient()._execute_query(_UPDATE_INVOICE, {"id": invoice_id, "input": inp})
    payload = ((res or {}).get("data") or {}).get("updateInvoice") or {}
    if res.get("errors") or payload.get("mutationErrors") or not payload.get("invoice"):
        raise HTTPException(502, f"Gazelle a refusé : {payload.get('mutationErrors') or res.get('errors')}")
    return {"numero": payload["invoice"].get("number"), "statut": payload["invoice"].get("status"), **inp}


class EnvoiFactureIn(BaseModel):
    sujet: str
    message: str
    paiement_carte: bool = True


@router.post("/gazelle/facture/{invoice_id}/envoyer-facturation-alt")
def envoyer_facture_alt(invoice_id: str, e: EnvoiFactureIn):
    """Envoie la facture (PDF joint + lien de paiement Gazelle) au courriel de FACTURATION
    ALTERNATIVE, à la demande d'Allan. Passe le brouillon à OPEN. Refuse si la facture n'a pas
    de facturation alternative ou est déjà payée/annulée."""
    from core.gazelle_api_client import GazelleAPIClient
    gz = GazelleAPIClient()
    inv = details_facture(invoice_id)
    if inv.get("status") not in ("DRAFT", "OPEN", "OVERDUE"):
        raise HTTPException(409, f"Statut {inv.get('status')} — rien envoyé")
    if not inv.get("altBillingEmail"):
        raise HTTPException(409, "Aucun courriel de facturation alternative — rien envoyé")
    inp = {"status": "OPEN", "emailToAltBilling": True, "attachPdf": True,
           "emailSubject": e.sujet, "emailMessage": e.message}
    if e.paiement_carte:
        inp["acceptElectronicPayment"] = True
        inp["acceptedElectronicPaymentMethods"] = ["CARD"]
    res = gz._execute_query(_UPDATE_INVOICE, {"id": invoice_id, "input": inp})
    payload = ((res or {}).get("data") or {}).get("updateInvoice") or {}
    if res.get("errors") or payload.get("mutationErrors") or not payload.get("invoice"):
        raise HTTPException(502, f"Gazelle a refusé : {payload.get('mutationErrors') or res.get('errors')}")
    apres = details_facture(invoice_id)
    return {"numero": apres.get("number"), "statut": apres.get("status"), "envoye_a": apres.get("altBillingEmail"),
            "lien": apres.get("clientUrl"), "paiement_carte": apres.get("acceptElectronicPayment")}


# --- Rendez-vous Gazelle (créé à la demande d'Allan depuis une conversation Claude) ---
class RendezVousIn(BaseModel):
    client_id: Optional[str] = None    # facultatif pour un bloc PERSONAL (ex. déjeuner d'affaires, retour maison)
    user_id: str                       # technicien (1 event = 1 technicien)
    debut_montreal: str                # "2026-12-20T12:00" — heure de Montréal
    duree_min: int = 120
    titre: Optional[str] = None        # défaut : nom du client (format natif PTM)
    notes: Optional[str] = None
    piano_ids: List[str] = []
    accord: bool = True                # isTuning sur les pianos
    type: str = "APPOINTMENT"          # PERSONAL = bloc perso (aucun avis au client)
    lieu: Optional[str] = None         # adresse sur une ligne si différente de la fiche client
    # Courriel de confirmation Gazelle au client : PAS par défaut (décision d'Allan, 4 nov. 2026) —
    # l'équipe relit le RV puis l'envoie (POST /gazelle/rendez-vous/{eid}/confirmation).
    confirmation_client: bool = False
    par: Optional[str] = "Ivo (assistant IA) à la demande d'Allan"  # mention en tête des notes du RV


from core.provenance_client import (RAPPEL_PROVENANCE as RAPPEL_NOUVEAU_CLIENT, RAPPEL_PROVENANCE_EXISTANT,
                                   faut_demander, provenance_connue, est_institution)


def client_recent(client_id: str, jours: int = 365) -> bool:
    """Fiche Gazelle créée depuis moins d'un an. En cas de doute → False (pas de rappel)."""
    from datetime import timedelta
    try:
        db = _db()
        r = requests.get(f"{db.api_url}/gazelle_clients?select=created_at&external_id=eq.{client_id}",
                         headers=db._get_headers(), timeout=10)
        lignes = r.json() if r.status_code == 200 else []
        if not lignes or not lignes[0].get("created_at"):
            return False
        cree = datetime.fromisoformat(lignes[0]["created_at"].replace("Z", "+00:00"))
        if cree.tzinfo is None:
            cree = cree.replace(tzinfo=timezone.utc)
        return cree >= datetime.now(timezone.utc) - timedelta(days=jours)
    except Exception:
        return False


def est_nouveau_client(client_id: str) -> bool:
    """Fiche créée depuis moins de 90 jours ET aucun RV passé. En cas de doute → False."""
    from datetime import timedelta
    from core.timezone_utils import MONTREAL_TZ
    try:
        db = _db()
        h = db._get_headers()
        r = requests.get(f"{db.api_url}/gazelle_clients?select=created_at&external_id=eq.{client_id}",
                         headers=h, timeout=10)
        lignes = r.json() if r.status_code == 200 else []
        if not lignes or not lignes[0].get("created_at"):
            return False
        cree = datetime.fromisoformat(lignes[0]["created_at"].replace("Z", "+00:00"))
        if cree.tzinfo is None:
            cree = cree.replace(tzinfo=timezone.utc)
        if cree < datetime.now(timezone.utc) - timedelta(days=90):
            return False
        aujourdhui = datetime.now(MONTREAL_TZ).date().isoformat()
        r = requests.get(f"{db.api_url}/gazelle_appointments?select=external_id"
                         f"&client_external_id=eq.{client_id}&appointment_date=lt.{aujourdhui}&limit=1",
                         headers=h, timeout=10)
        return r.status_code == 200 and not r.json()
    except Exception:
        return False


@router.get("/gazelle/nouveau-client")
def nouveau_client(client_id: str = Query(...)):
    """LECTURE SEULE — ce client recevra-t-il le rappel « comment nous a-t-il trouvés » ?"""
    db = _db()
    h = db._get_headers()
    fiche = requests.get(f"{db.api_url}/gazelle_clients?select=created_at&external_id=eq.{client_id}",
                         headers=h, timeout=10)
    rv = requests.get(f"{db.api_url}/gazelle_appointments?select=appointment_date"
                      f"&client_external_id=eq.{client_id}&order=appointment_date.asc&limit=3", headers=h, timeout=10)
    return {"client_id": client_id, "nouveau": est_nouveau_client(client_id),
            "provenance_connue": provenance_connue(client_id),
            "fiche": fiche.json() if fiche.status_code == 200 else fiche.text[:200],
            "premiers_rv": rv.json() if rv.status_code == 200 else rv.text[:200]}


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
    if r.type not in ("APPOINTMENT", "PERSONAL"):
        raise HTTPException(400, "type : APPOINTMENT ou PERSONAL")
    if not r.client_id and (r.type != "PERSONAL" or not r.titre):
        raise HTTPException(400, "client_id requis (sauf bloc PERSONAL avec un titre)")
    titre = r.titre
    if not titre:
        res = gz._execute_query("query($id: String!) { client(id: $id) { id companyName "
                                "defaultContact { firstName lastName } } }", {"id": r.client_id})
        c = (res.get("data") or {}).get("client") or {}
        dc = c.get("defaultContact") or {}
        titre = c.get("companyName") or f"{dc.get('firstName', '')} {dc.get('lastName', '')}".strip()
    inp = {"title": titre, "start": start, "duration": r.duree_min, "type": r.type,
           "travelMode": "DRIVING", "userId": r.user_id}
    if r.client_id:
        inp["clientId"] = r.client_id
    if r.lieu:
        inp["location"] = {"locationType": "SINGLE_LINE_ADDRESS", "singleLineAddress": r.lieu}
    notes = r.notes or ""
    if r.type == "APPOINTMENT" and r.par:
        notes = f"Planifié par {r.par}." + ("\n\n" + notes if notes else "")
    if (r.type == "APPOINTMENT" and r.client_id and "« Référé par »" not in notes and client_recent(r.client_id)
            and not est_institution(r.client_id) and faut_demander(r.client_id)):
        rappel = RAPPEL_NOUVEAU_CLIENT if est_nouveau_client(r.client_id) else RAPPEL_PROVENANCE_EXISTANT
        notes = (notes + "\n\n" if notes else "") + rappel
    if r.type == "APPOINTMENT" and r.client_id and r.piano_ids and est_institution(r.client_id):
        # Institutions : code de porte, salle, entrée recopiés du mémo du piano dans Gazelle
        from core.acces_piano import note_acces_pianos, ajouter_acces
        notes = ajouter_acces(notes, note_acces_pianos(gz, r.piano_ids))
    if notes:
        inp["notes"] = notes
    if r.piano_ids:
        inp["pianos"] = [{"pianoId": p, "isTuning": r.accord} for p in r.piano_ids]
    if r.type == "APPOINTMENT" and r.confirmation_client:
        inp["isConfirmationEmailWanted"] = True
    mut = """mutation($input: PrivateEventInput!) { createEvent(input: $input) {
      event { id title start duration type status user { id firstName } client { id }
              location { singleLineAddress street1 municipality }
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


class PianoClientIn(BaseModel):
    marque: str
    modele: Optional[str] = None
    type_piano: str = "UPRIGHT"          # UPRIGHT, GRAND, ...
    numero_serie: Optional[str] = None
    emplacement: Optional[str] = None
    notes: Optional[str] = None


@router.post("/gazelle/client/{client_id}/piano")
def ajouter_piano_client(client_id: str, p: PianoClientIn):
    """Ajoute un piano à une fiche client. Garde-fou contre les doublons :
    - avec un numéro de série : doublon si un piano de la fiche porte ce numéro,
      ou si un piano actif de même marque n'a encore aucun numéro (sans doute le même) ;
    - sans numéro : doublon si la fiche a déjà un piano actif de la même marque.
    (Une institution peut ainsi recevoir un 2e Yamaha dont le numéro est connu.)"""
    from core.gazelle_api_client import GazelleAPIClient
    gz = GazelleAPIClient()
    ex = gz._execute_query("query($id: String!) { client(id: $id) { id allPianos { nodes { id make model type status serialNumber } } } }",
                           {"id": client_id})
    c = ((ex or {}).get("data") or {}).get("client")
    if not c:
        raise HTTPException(404, f"Client introuvable : {client_id}")
    serie = (p.numero_serie or "").replace(" ", "").upper()
    for n in (c.get("allPianos") or {}).get("nodes") or []:
        meme_marque = (n.get("make") or "").strip().lower() == p.marque.strip().lower()
        actif = n.get("status") != "INACTIVE"
        serie_n = (n.get("serialNumber") or "").replace(" ", "").upper()
        if serie:
            if serie_n == serie or (meme_marque and actif and not serie_n):
                return {"deja": True, "piano": n}
        elif meme_marque and actif:
            return {"deja": True, "piano": n}
    entree = {"clientId": client_id, "type": p.type_piano, "make": p.marque, "status": "ACTIVE"}
    for cle, val in (("model", p.modele), ("serialNumber", p.numero_serie),
                     ("location", p.emplacement), ("notes", p.notes)):
        if val:
            entree[cle] = val
    r = gz._execute_query("""mutation($i: PrivatePianoInput!) { createPiano(input: $i) {
      piano { id make model type status } mutationErrors { fieldName messages } } }""", {"i": entree})
    pp = ((r or {}).get("data") or {}).get("createPiano") or {}
    if (isinstance(r, dict) and r.get("errors")) or pp.get("mutationErrors") or not pp.get("piano"):
        raise HTTPException(502, f"createPiano : {r.get('errors') if isinstance(r, dict) else ''} {pp.get('mutationErrors')}")
    return {"deja": False, "piano": pp["piano"]}


class PianoModifIn(BaseModel):
    marque: Optional[str] = None
    modele: Optional[str] = None
    type_piano: Optional[str] = None
    numero_serie: Optional[str] = None
    emplacement: Optional[str] = None
    ajout_notes: Optional[str] = None     # ajouté À LA SUITE des notes existantes, jamais en remplacement


@router.post("/gazelle/piano/{piano_id}/modifier")
def modifier_piano(piano_id: str, m: PianoModifIn):
    """Corrige un piano existant. Seuls les champs fournis changent ; les notes
    existantes sont conservées (le texte fourni s'ajoute à la suite)."""
    from core.gazelle_api_client import GazelleAPIClient
    gz = GazelleAPIClient()
    ex = gz._execute_query("query($id: String!) { piano(id: $id) { id make model type serialNumber location notes } }",
                           {"id": piano_id})
    avant = ((ex or {}).get("data") or {}).get("piano")
    if not avant:
        raise HTTPException(404, f"Piano introuvable : {piano_id}")
    entree = {}
    for cle, val in (("make", m.marque), ("model", m.modele), ("type", m.type_piano),
                     ("serialNumber", m.numero_serie), ("location", m.emplacement)):
        if val:
            entree[cle] = val
    if m.ajout_notes:
        existantes = (avant.get("notes") or "").strip()
        if m.ajout_notes.strip() not in existantes:
            entree["notes"] = (existantes + "\n\n" if existantes else "") + m.ajout_notes.strip()
    if not entree:
        return {"modifie": False, "piano": avant}
    r = gz._execute_query("""mutation($id: String!, $i: PrivatePianoInput!) { updatePiano(id: $id, input: $i) {
      piano { id make model type serialNumber location notes } mutationErrors { fieldName messages } } }""",
                          {"id": piano_id, "i": entree})
    pp = ((r or {}).get("data") or {}).get("updatePiano") or {}
    if (isinstance(r, dict) and r.get("errors")) or pp.get("mutationErrors") or not pp.get("piano"):
        raise HTTPException(502, f"updatePiano : {r.get('errors') if isinstance(r, dict) else ''} {pp.get('mutationErrors')}")
    return {"modifie": True, "avant": avant, "piano": pp["piano"]}


class AdresseClientIn(BaseModel):
    rue: str                              # ex. « 192, 80e Avenue »
    ville: str
    code_postal: Optional[str] = None
    province: str = "QC"


@router.post("/gazelle/client/{client_id}/adresse")
def ajouter_adresse_client(client_id: str, a: AdresseClientIn):
    """Ajoute l'adresse au contact principal SEULEMENT si la fiche n'en a aucune
    (jamais d'écrasement d'une adresse existante)."""
    from core.gazelle_api_client import GazelleAPIClient
    gz = GazelleAPIClient()
    res = gz._execute_query("""query($id: String!) { client(id: $id) { id defaultContact { id
      defaultLocation { street1 municipality postalCode } } } }""", {"id": client_id})
    c = ((res or {}).get("data") or {}).get("client")
    if not c or not (c.get("defaultContact") or {}).get("id"):
        raise HTTPException(404, f"Client ou contact principal introuvable : {client_id}")
    loc = c["defaultContact"].get("defaultLocation") or {}
    if (loc.get("street1") or "").strip():
        raise HTTPException(409, f"La fiche a déjà une adresse ({loc.get('street1')}, {loc.get('municipality')}) : rien modifié")
    entree = {"locationType": "ADDRESS", "usageType": "STREET", "street1": a.rue.strip(),
              "municipality": a.ville.strip(), "region": a.province, "countryCode": "CA"}
    if a.code_postal:
        entree["postalCode"] = a.code_postal.strip().upper()
    r = gz._execute_query("""mutation($c: String!, $i: PrivateContactLocationInput!) {
      createContactLocation(contactId: $c, input: $i) { mutationErrors { fieldName messages } } }""",
                          {"c": c["defaultContact"]["id"], "i": entree})
    p = ((r or {}).get("data") or {}).get("createContactLocation") or {}
    if (isinstance(r, dict) and r.get("errors")) or p.get("mutationErrors"):
        raise HTTPException(502, f"createContactLocation : {(r or {}).get('errors') or p.get('mutationErrors')}")
    return {"ok": True, "client_id": client_id, "adresse": entree}


class CorrectionAdresseIn(BaseModel):
    ancienne_rue: str                     # garde-fou : doit correspondre à la rue actuelle
    nouvelle_rue: str
    ville: Optional[str] = None
    code_postal: Optional[str] = None


@router.post("/gazelle/client/{client_id}/adresse/corriger")
def corriger_adresse_client(client_id: str, a: CorrectionAdresseIn):
    """Corrige la rue de l'adresse principale. Refuse si la rue actuelle n'est pas celle
    qu'on croit corriger (évite d'écraser une adresse mise à jour entre-temps)."""
    from core.gazelle_api_client import GazelleAPIClient
    norm = lambda t: _re.sub(r"[^0-9a-z]", "", (t or "").lower())
    gz = GazelleAPIClient()
    res = gz._execute_query("""query($id: String!) { client(id: $id) { id defaultContact { id
      defaultLocation { id street1 municipality postalCode } } } }""", {"id": client_id})
    c = ((res or {}).get("data") or {}).get("client") or {}
    loc = (c.get("defaultContact") or {}).get("defaultLocation") or {}
    if not loc.get("id"):
        raise HTTPException(404, "Aucune adresse principale sur la fiche : utiliser l'ajout d'adresse")
    if norm(loc.get("street1")) != norm(a.ancienne_rue):
        raise HTTPException(409, f"La rue actuelle est « {loc.get('street1')} », pas « {a.ancienne_rue} » : rien modifié")
    entree = {"street1": a.nouvelle_rue.strip()}
    if a.ville:
        entree["municipality"] = a.ville.strip()
    if a.code_postal:
        entree["postalCode"] = a.code_postal.strip().upper()
    r = gz._execute_query("""mutation($id: String!, $i: PrivateContactLocationInput!) {
      updateContactLocation(id: $id, input: $i) { mutationErrors { fieldName messages } } }""",
                          {"id": loc["id"], "i": entree})
    p = ((r or {}).get("data") or {}).get("updateContactLocation") or {}
    if (isinstance(r, dict) and r.get("errors")) or p.get("mutationErrors"):
        raise HTTPException(502, f"updateContactLocation : {(r or {}).get('errors') or p.get('mutationErrors')}")
    return {"ok": True, "client_id": client_id, "avant": loc.get("street1"), "apres": entree["street1"]}


class CourrielClientIn(BaseModel):
    courriel: str


def ajouter_courriel(client_id: str, courriel: str) -> Dict[str, Any]:
    """Ajoute un courriel au contact principal d'une fiche Gazelle.
    Garde-fous : format valide ; rien si le courriel y est déjà ; refus si un AUTRE
    client a ce courriel (doublon possible) ; ne remplace jamais le courriel principal
    existant (le nouveau devient principal seulement s'il n'y en a aucun)."""
    from core.gazelle_api_client import GazelleAPIClient
    courriel = (courriel or "").strip().lower()
    if not _re.fullmatch(r"[^@\s]+@[^@\s]+\.[a-z]{2,}", courriel):
        raise HTTPException(400, f"Courriel invalide : {courriel!r}")
    gz = GazelleAPIClient()
    res = gz._execute_query("""query($id: String!) { client(id: $id) { id
      defaultContact { id firstName lastName allEmails { nodes { id email isDefault } } } } }""", {"id": client_id})
    c = ((res or {}).get("data") or {}).get("client")
    if not c:
        raise HTTPException(404, f"Client introuvable : {client_id}")
    contact = c.get("defaultContact") or {}
    if not contact.get("id"):
        raise HTTPException(409, "La fiche n'a pas de contact principal : rien modifié")
    actuels = (contact.get("allEmails") or {}).get("nodes") or []
    if any((e.get("email") or "").strip().lower() == courriel for e in actuels):
        return {"deja": True, "client_id": client_id, "courriel": courriel}
    autre = gz.trouver_client_existant(courriel=courriel)
    if autre and autre != client_id:
        raise HTTPException(409, f"Ce courriel est déjà sur une autre fiche ({autre}) : doublon possible, rien modifié")
    principal = not any(e.get("isDefault") for e in actuels)
    r = gz._execute_query("""mutation($c: String!, $i: PrivateContactEmailInput!) { createContactEmail(contactId: $c, input: $i) {
      email { id email isDefault } mutationErrors { fieldName messages } } }""",
                          {"c": contact["id"], "i": {"email": courriel, "isDefault": principal}})
    p = ((r or {}).get("data") or {}).get("createContactEmail") or {}
    if (isinstance(r, dict) and r.get("errors")) or p.get("mutationErrors") or not p.get("email"):
        raise HTTPException(502, f"createContactEmail : {(r or {}).get('errors') or p.get('mutationErrors')}")
    return {"deja": False, "client_id": client_id, "courriel": courriel, "principal": principal,
            "contact": f"{contact.get('firstName') or ''} {contact.get('lastName') or ''}".strip()}


@router.post("/gazelle/client/{client_id}/courriel")
def ajouter_courriel_client(client_id: str, c: CourrielClientIn):
    return ajouter_courriel(client_id, c.courriel)


class ReferenceClientIn(BaseModel):
    refere_par: str
    notes: Optional[str] = None


class NomContactIn(BaseModel):
    ancien_nom: str        # garde-fou : nom de famille actuel du contact principal
    prenom: Optional[str] = None
    nom: str


@router.post("/gazelle/client/{client_id}/nom")
def corriger_nom_contact(client_id: str, n: NomContactIn):
    """Corrige le prénom/nom du contact principal (ex. « White » → « Esmonde-White »), seulement si
    le nom actuel correspond à ancien_nom. Rien d'autre n'est modifié, aucun courriel."""
    from core.gazelle_api_client import GazelleAPIClient
    gz = GazelleAPIClient()
    res = gz._execute_query("query($id: String!) { client(id: $id) { id defaultContact { id firstName lastName } } }",
                            {"id": client_id})
    dc = ((((res or {}).get("data") or {}).get("client") or {}).get("defaultContact")) or {}
    if not dc.get("id"):
        raise HTTPException(404, "Client ou contact principal introuvable")
    if (dc.get("lastName") or "").strip().lower() != n.ancien_nom.strip().lower():
        raise HTTPException(409, f"Le nom actuel est « {dc.get('firstName')} {dc.get('lastName')} » : rien modifié")
    inp = {"lastName": n.nom.strip()}
    if n.prenom:
        inp["firstName"] = n.prenom.strip()
    r = gz._execute_query("""mutation($id: String!, $i: PrivateContactInputWithoutNestedCollections!) {
      updateContact(id: $id, input: $i) { contact { id firstName lastName } mutationErrors { fieldName messages } } }""",
                          {"id": dc["id"], "i": inp})
    p = ((r or {}).get("data") or {}).get("updateContact") or {}
    if (r or {}).get("errors") or p.get("mutationErrors") or not p.get("contact"):
        raise HTTPException(502, f"updateContact : {(r or {}).get('errors') or p.get('mutationErrors')}")
    return {"avant": f"{dc.get('firstName')} {dc.get('lastName')}",
            "apres": f"{p['contact'].get('firstName')} {p['contact'].get('lastName')}"}


@router.post("/gazelle/client/{client_id}/reference")
def inscrire_reference(client_id: str, r: ReferenceClientIn):
    """Inscrit « Référé par » dans la fiche Gazelle, SEULEMENT s'il est vide (jamais d'écrasement)."""
    from core.gazelle_api_client import GazelleAPIClient
    gz = GazelleAPIClient()
    actuel = gz._execute_query("query($id: String!) { client(id: $id) { referredBy referredByNotes } }",
                               {"id": client_id})
    c = ((actuel or {}).get("data") or {}).get("client") or {}
    if (c.get("referredBy") or "").strip():
        raise HTTPException(409, f"« Référé par » déjà rempli : {c['referredBy']!r} — rien modifié")
    entree = {"referredBy": r.refere_par}
    if r.notes and not (c.get("referredByNotes") or "").strip():
        entree["referredByNotes"] = r.notes
    res = gz._execute_query("""mutation($id: String!, $input: PrivateClientInput!) { updateClient(id: $id, input: $input) {
      client { id referredBy referredByNotes } mutationErrors { fieldName messages } } }""",
                            {"id": client_id, "input": entree})
    p = ((res or {}).get("data") or {}).get("updateClient") or {}
    if (isinstance(res, dict) and res.get("errors")) or p.get("mutationErrors"):
        raise HTTPException(502, str(p.get("mutationErrors") or res.get("errors")))
    return p.get("client")


class NotesRvIn(BaseModel):
    notes: str


@router.post("/gazelle/rendez-vous/{eid}/notes")
def modifier_notes_rv(eid: str, n: NotesRvIn):
    """Remplace les notes d'un RV (rien d'autre n'est modifié, aucun courriel au client)."""
    from core.gazelle_api_client import GazelleAPIClient
    mut = """mutation($id: String!, $input: PrivateEventInput!) { updateEvent(id: $id, input: $input) {
      event { id title notes } mutationErrors { fieldName messages } } }"""
    res = GazelleAPIClient()._execute_query(mut, {"id": eid, "input": {"notes": n.notes}})
    payload = ((res or {}).get("data") or {}).get("updateEvent") or {}
    if (isinstance(res, dict) and res.get("errors")) or payload.get("mutationErrors"):
        raise HTTPException(502, str(payload.get("mutationErrors") or res.get("errors")))
    return payload.get("event")


@router.post("/gazelle/rendez-vous/{eid}/confirmation")
def envoyer_confirmation(eid: str):
    """Envoie au client le courriel de confirmation Gazelle d'un RV déjà créé
    (même courriel que la case « Envoyer une confirmation » de l'appli)."""
    from core.gazelle_api_client import GazelleAPIClient
    mut = """mutation($id: String!, $input: PrivateEventInput!) { updateEvent(id: $id, input: $input) {
      event { id title start } mutationErrors { fieldName messages } } }"""
    try:
        res = GazelleAPIClient()._execute_query(mut, {"id": eid, "input": {"isConfirmationEmailWanted": True}})
    except Exception as e:
        raise HTTPException(502, f"updateEvent : {e}")
    if isinstance(res, dict) and res.get("errors"):
        raise HTTPException(502, str(res["errors"]))
    payload = ((res or {}).get("data") or {}).get("updateEvent") or {}
    if payload.get("mutationErrors"):
        raise HTTPException(502, str(payload["mutationErrors"]))
    return {"envoye": True, "evenement": payload.get("event")}


class ModifRvIn(BaseModel):
    user_id: Optional[str] = None      # réassigner à un technicien
    notes_ajout: Optional[str] = None  # ajouté EN TÊTE des notes existantes (rien n'est effacé)
    debut_montreal: Optional[str] = None  # « AAAA-MM-JJTHH:MM » heure de Montréal ; retire le « toute la journée »
    duree_min: Optional[int] = None


@router.post("/gazelle/rendez-vous/{eid}/modifier")
def modifier_rendez_vous(eid: str, m: ModifRvIn):
    """Réassigne un RV, ajoute une précision aux notes et/ou fixe une heure précise
    (debut_montreal + duree_min ; un RV « toute la journée » devient un RV à heure fixe).
    Ne touche ni au client ni au titre ; aucun courriel n'est envoyé au client."""
    from core.gazelle_api_client import GazelleAPIClient
    from core.timezone_utils import MONTREAL_TZ
    gz = GazelleAPIClient()
    inp: Dict[str, Any] = {}
    if m.debut_montreal:
        try:
            local = datetime.fromisoformat(m.debut_montreal)
        except ValueError:
            raise HTTPException(400, "debut_montreal invalide (attendu AAAA-MM-JJTHH:MM)")
        if local.tzinfo is None:
            local = local.replace(tzinfo=MONTREAL_TZ)
        inp["start"] = local.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        inp["isAllDay"] = False
    if m.duree_min:
        inp["duration"] = m.duree_min
    if m.user_id:
        inp["userId"] = m.user_id
    if m.notes_ajout:
        actuelles = (_evenement(gz, eid).get("notes") or "").strip()
        if m.notes_ajout.strip() not in actuelles:
            inp["notes"] = m.notes_ajout.strip() + ("\n\n" + actuelles if actuelles else "")
    if not inp:
        raise HTTPException(400, "Rien à modifier")
    mut = """mutation($id: String!, $input: PrivateEventInput!) { updateEvent(id: $id, input: $input) {
      event { id title start duration isAllDay notes user { id firstName } } mutationErrors { fieldName messages } } }"""
    res = gz._execute_query(mut, {"id": eid, "input": inp})
    payload = ((res or {}).get("data") or {}).get("updateEvent") or {}
    if (isinstance(res, dict) and res.get("errors")) or payload.get("mutationErrors"):
        raise HTTPException(502, str(payload.get("mutationErrors") or res.get("errors")))
    return payload.get("event")


class PianosRvIn(BaseModel):
    retirer: List[str] = []   # ins_… à enlever du RV
    ajouter: List[str] = []   # ins_… à mettre sur le RV


_Q_RV_PIANOS = """query($id: String!) { event(eventId: $id) { id title start duration status notes type
  client { id } user { id } allEventPianos(first: 20) { nodes { isTuning piano { id } } } } }"""


def _rv_pianos(gz, eid: str) -> Dict[str, Any]:
    res = gz._execute_query(_Q_RV_PIANOS, {"id": eid}) or {}
    if res.get("errors"):
        raise HTTPException(502, f"Gazelle : {res['errors']}")
    ev = (res.get("data") or {}).get("event")
    if not ev:
        raise HTTPException(404, f"RV {eid} introuvable dans Gazelle")
    return ev


@router.post("/gazelle/rendez-vous/{eid}/accord")
def cocher_accord_rv(eid: str):
    """Coche « accord » sur tous les pianos d'un RV (rien d'autre ne change, aucun courriel au client).
    Sert quand un RV d'accord ne compte pas comme accord : sinon Gazelle envoie « piano dû »
    et ne met pas à jour la date du dernier accord à la fin du RV."""
    from core.gazelle_api_client import GazelleAPIClient
    if not eid.startswith("evt_"):
        raise HTTPException(400, "Identifiant de RV invalide (evt_…)")
    gz = GazelleAPIClient()
    avant = _rv_pianos(gz, eid)
    noeuds = (avant.get("allEventPianos") or {}).get("nodes") or []
    ids = [((n.get("piano") or {}).get("id")) for n in noeuds if (n.get("piano") or {}).get("id")]
    if not ids:
        raise HTTPException(400, "Ce RV n'a aucun piano attaché")
    if all(n.get("isTuning") for n in noeuds):
        return {"change": False, "message": "Déjà coché accord"}
    mut = """mutation($id: String!, $input: PrivateEventInput!) { updateEvent(id: $id, input: $input) {
      event { id } mutationErrors { fieldName messages } } }"""
    res = gz._execute_query(mut, {"id": eid, "input": {"pianos": [{"pianoId": i, "isTuning": True} for i in ids]}})
    payload = ((res or {}).get("data") or {}).get("updateEvent") or {}
    if (isinstance(res, dict) and res.get("errors")) or payload.get("mutationErrors"):
        raise HTTPException(502, str(res.get("errors") or payload.get("mutationErrors")))
    apres = _rv_pianos(gz, eid)
    return {"change": True, "pianos": [{"id": (n.get("piano") or {}).get("id"), "accord": bool(n.get("isTuning"))}
                                       for n in (apres.get("allEventPianos") or {}).get("nodes") or []],
            "heure_inchangee": apres.get("start") == avant.get("start"), "duree_inchangee": apres.get("duration") == avant.get("duration")}


@router.post("/gazelle/rendez-vous/{eid}/pianos")
def changer_pianos_rv(eid: str, b: PianosRvIn):
    """Remplace un ou des pianos d'un RV existant (ex. Steinway B → Steinway D). Les autres pianos
    du RV et leur case « accord » sont gardés ; rien d'autre n'est modifié (heure, technicien,
    titre, notes, client) et aucun courriel n'est envoyé au client. Vérifie le résultat après coup."""
    from core.gazelle_api_client import GazelleAPIClient
    if not eid.startswith("evt_"):
        raise HTTPException(400, "Identifiant de RV invalide (evt_…)")
    if not (b.retirer or b.ajouter) or any(not x.startswith("ins_") for x in b.retirer + b.ajouter):
        raise HTTPException(400, "Donne des pianos ins_… à retirer et/ou à ajouter")
    gz = GazelleAPIClient()
    avant = _rv_pianos(gz, eid)
    noeuds = (avant.get("allEventPianos") or {}).get("nodes") or []
    actuels = [(((n.get("piano") or {}).get("id")), bool(n.get("isTuning"))) for n in noeuds]
    ids_actuels = [i for i, _ in actuels]
    accord_defaut = any(t for _, t in actuels) or not actuels
    voulus = [(i, t) for i, t in actuels if i not in b.retirer]
    voulus += [(i, accord_defaut) for i in b.ajouter if i not in [v[0] for v in voulus]]
    if [i for i, _ in voulus] == ids_actuels:
        return {"change": False, "pianos": ids_actuels, "message": "Le RV avait déjà ces pianos : rien modifié."}
    if not voulus:
        raise HTTPException(400, "Un RV ne peut pas rester sans piano")
    mut = """mutation($id: String!, $input: PrivateEventInput!) { updateEvent(id: $id, input: $input) {
      event { id } mutationErrors { fieldName messages } } }"""
    res = gz._execute_query(mut, {"id": eid, "input": {"pianos": [{"pianoId": i, "isTuning": t} for i, t in voulus]}})
    payload = ((res or {}).get("data") or {}).get("updateEvent") or {}
    if (isinstance(res, dict) and res.get("errors")) or payload.get("mutationErrors") or not payload.get("event"):
        raise HTTPException(502, f"Gazelle a refusé : {payload.get('mutationErrors') or res.get('errors')}")
    apres = _rv_pianos(gz, eid)
    ids_apres = [((n.get("piano") or {}).get("id")) for n in ((apres.get("allEventPianos") or {}).get("nodes") or [])]
    avert = []
    if sorted(ids_apres) != sorted(i for i, _ in voulus):
        avert.append(f"Pianos dans Gazelle après le changement : {ids_apres} (attendu : {[i for i, _ in voulus]})")
    for c in ("title", "start", "duration", "notes", "status", "type"):
        if apres.get(c) != avant.get(c):
            avert.append(f"« {c} » a changé : {avant.get(c)!r} → {apres.get(c)!r}")
    for c in ("client", "user"):
        if (apres.get(c) or {}).get("id") != (avant.get(c) or {}).get("id"):
            avert.append(f"« {c} » a changé")
    return {"change": True, "avant": ids_actuels, "pianos": ids_apres, "avertissements": avert}


class NoteServicePiano(BaseModel):
    piano_id: str
    notes: str


class CompleterRvIn(BaseModel):
    notes: List[NoteServicePiano]


@router.post("/gazelle/rendez-vous/{eid}/completer")
def completer_rv(eid: str, b: CompleterRvIn):
    """Complète un RV passé resté « actif » et crée son entrée de service (historique du piano),
    comme le technicien le fait dans l'appli Gazelle. Ex. : « Accord 440Hz … stat 11 » — le
    « stat » est ensuite repris par l'assistant pour le stationnement de Place des Arts.
    Refuse un RV futur, déjà complété, ou un piano qui n'est pas sur le RV."""
    from core.gazelle_api_client import GazelleAPIClient
    if not eid.startswith("evt_"):
        raise HTTPException(400, "Identifiant de RV invalide (evt_…)")
    if not b.notes or any(not n.piano_id.startswith("ins_") or not n.notes.strip() for n in b.notes):
        raise HTTPException(400, "Donne au moins une note de service non vide par piano ins_…")
    gz = GazelleAPIClient()
    ev = _evenement(gz, eid)
    if not ev:
        raise HTTPException(404, f"RV {eid} introuvable dans Gazelle")
    if ev.get("type") != "APPOINTMENT":
        raise HTTPException(400, f"Ce n'est pas un RV client (type {ev.get('type')})")
    if ev.get("status") != "ACTIVE":
        raise HTTPException(409, f"RV déjà traité (statut {ev.get('status')}) : rien modifié")
    debut = datetime.fromisoformat((ev.get("start") or "").replace("Z", "+00:00"))
    if debut > datetime.now(timezone.utc):
        raise HTTPException(400, "Ce RV n'a pas encore eu lieu : rien modifié")
    sur_rv = {((n.get("piano") or {}).get("id")) for n in ((ev.get("allEventPianos") or {}).get("nodes") or [])}
    hors = [n.piano_id for n in b.notes if n.piano_id not in sur_rv]
    if hors:
        raise HTTPException(400, f"Pianos absents du RV : {hors} (pianos du RV : {sorted(sur_rv)})")
    mut = """mutation($eventId: String!, $input: PrivateCompleteEventInput!) {
      completeEvent(eventId: $eventId, input: $input) { event { id status } mutationErrors { fieldName messages } } }"""
    res = gz._execute_query(mut, {"eventId": eid, "input": {
        "resultType": "COMPLETE",
        "serviceHistoryNotes": [{"pianoId": n.piano_id, "notes": n.notes.strip()} for n in b.notes]}}) or {}
    payload = (res.get("data") or {}).get("completeEvent") or {}
    if res.get("errors") or payload.get("mutationErrors") or not payload.get("event"):
        raise HTTPException(502, f"Gazelle a refusé : {payload.get('mutationErrors') or res.get('errors')}")
    apres = _evenement(gz, eid)
    return {"complete": apres.get("status") == "COMPLETE", "statut": apres.get("status"),
            "pianos": [n.piano_id for n in b.notes]}


# --- Ménage : supprimer un rendez-vous « Service: NOTE » créé par erreur par l'IA ---
_Q_EVENEMENT = """query($id: String!) { event(eventId: $id) { id title start duration type status notes user { id }
  client { id } allEventPianos(first: 5) { nodes { piano { id } } } } }"""


def _evenement(gz, eid: str) -> Dict[str, Any]:
    try:
        res = gz._execute_query(_Q_EVENEMENT, {"id": eid})
    except Exception as e:
        raise HTTPException(502, f"Gazelle : {e}")
    if res.get("errors"):
        raise HTTPException(502, str(res["errors"]))
    return (res.get("data") or {}).get("event") or {}


class ConversionBlocIn(BaseModel):
    client_id: str
    piano_ids: List[str] = []
    accord: bool = True
    notes: Optional[str] = None
    par: Optional[str] = "Ivo (assistant IA) à la demande d'Allan"


@router.post("/gazelle/evenement/{eid}/convertir-en-rv")
def convertir_bloc_en_rv(eid: str, c: ConversionBlocIn):
    """Transforme un bloc PERSONNEL futur (ex. « accorder fazioli à la maison trestler ») en vrai RV
    client : même technicien, même jour, même heure, même durée. Le RV est créé d'abord ; le bloc
    n'est supprimé qu'une fois le RV confirmé par Gazelle. Aucun courriel au client."""
    from datetime import timedelta
    from core.gazelle_api_client import GazelleAPIClient
    from core.timezone_utils import MONTREAL_TZ
    gz = GazelleAPIClient()
    ev = _evenement(gz, eid)
    if not ev:
        raise HTTPException(404, f"Bloc {eid} introuvable")
    if ev.get("type") != "PERSONAL":
        raise HTTPException(409, f"« {ev.get('title')} » n'est pas un bloc personnel : rien modifié")
    debut = datetime.fromisoformat(ev["start"].replace("Z", "+00:00")).astimezone(MONTREAL_TZ)
    if debut < datetime.now(MONTREAL_TZ):
        raise HTTPException(409, "Bloc passé : rien modifié")
    duree = int(ev.get("duration") or 0)
    uid = (ev.get("user") or {}).get("id")
    if not uid or duree <= 0 or duree >= 24 * 60:
        raise HTTPException(409, "Bloc sans technicien, sans durée ou d'une journée entière : rien modifié")
    notes = "\n\n".join(x for x in ((c.notes or "").strip(), f"(Remplace le bloc « {ev.get('title') or ''} ».)") if x)
    res = creer_rendez_vous(RendezVousIn(client_id=c.client_id, user_id=uid,
                                         debut_montreal=debut.strftime("%Y-%m-%dT%H:%M"), duree_min=duree,
                                         notes=notes, piano_ids=c.piano_ids, accord=c.accord, par=c.par))
    nouveau = (res.get("evenement") or {}).get("id")
    if not nouveau:
        raise HTTPException(502, "Gazelle n'a pas confirmé le RV : bloc laissé en place")
    r = gz._execute_query("""mutation($id: String!) { deleteEvent(id: $id) { mutationErrors { fieldName messages } } }""", {"id": eid})
    err = (r or {}).get("errors") or (((r or {}).get("data") or {}).get("deleteEvent") or {}).get("mutationErrors")
    return {"rv": res.get("evenement"), "bloc_supprime": not err,
            "avertissement": f"RV créé, mais le bloc {eid} n'a pas pu être retiré : {err}" if err else None,
            "fin": (debut + timedelta(minutes=duree)).strftime("%H:%M")}


@router.get("/gazelle/evenement/{eid}")
def lire_evenement(eid: str):
    from core.gazelle_api_client import GazelleAPIClient
    return _evenement(GazelleAPIClient(), eid)


@router.delete("/gazelle/evenement/{eid}")
def supprimer_note_evenement(eid: str):
    """Supprime UNIQUEMENT un rendez-vous-note créé par l'IA (titre « Service: NOTE »,
    notes commençant par « NOTE: ») ou un bloc perso temporaire « RÉSERVÉ (à confirmer) ».
    Tout autre rendez-vous est refusé."""
    from core.gazelle_api_client import GazelleAPIClient
    gz = GazelleAPIClient()
    ev = _evenement(gz, eid)
    note_ia = ev.get("title") == "Service: NOTE" and (ev.get("notes") or "").startswith("NOTE: ")
    bloc_reserve = (ev.get("type") == "PERSONAL" and (ev.get("title") or "").startswith("RÉSERVÉ (à confirmer)"))
    if not (note_ia or bloc_reserve):
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
        sortie.append({"id": e.get("id"), "jour": d.strftime("%Y-%m-%d"), "heure": d.strftime("%H:%M"), "tech": noms.get(uid, uid),
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


@router.get("/gazelle/pianos-statut")
def pianos_statut(client_id: str = Query(...)):
    """LECTURE — statut Gazelle (ACTIVE/INACTIVE…) des pianos d'un client."""
    from core.gazelle_api_client import GazelleAPIClient
    res = GazelleAPIClient()._execute_query("""query($c: String!, $s: [PianoStatus!]) {
      allPianos(clientId: $c, filters: { status: $s }) { nodes { id status location make calculatedLastService } } }""",
                                            {"c": client_id, "s": ["ACTIVE", "INACTIVE"]})
    if res.get("errors"):
        res = GazelleAPIClient()._execute_query("""query($c: String!) { allPianos(clientId: $c) {
          nodes { id status location make calculatedLastService } } }""", {"c": client_id})
    return {"pianos": ((res.get("data") or {}).get("allPianos") or {}).get("nodes") or [], "erreurs": res.get("errors")}


@router.post("/gazelle/piano-maj")
def piano_maj(piano_id: str = Query(...), statut: Optional[str] = Query(None, pattern="^(ACTIVE|INACTIVE)$"),
              dernier_service: Optional[str] = Query(None, pattern=r"^\d{4}-\d{2}-\d{2}$"),
              numero_serie: Optional[str] = Query(None, min_length=1, max_length=40),
              emplacement: Optional[str] = Query(None, min_length=1, max_length=200)):
    """Met à jour le statut, la date de dernier service (manuelle), le numéro de série
    et/ou l'emplacement (champ « location ») d'un piano Gazelle."""
    from core.gazelle_api_client import GazelleAPIClient
    entree: Dict[str, Any] = {}
    if statut:
        entree["status"] = statut
    if dernier_service:
        entree["manualLastService"] = dernier_service
    if numero_serie:
        entree["serialNumber"] = numero_serie.strip()
    if emplacement:
        entree["location"] = emplacement.strip()
    if not entree:
        raise HTTPException(400, "Rien à modifier")
    res = GazelleAPIClient()._execute_query(
        'mutation($id:String!,$input:PrivatePianoInput!){updatePiano(id:$id,input:$input){piano{id status serialNumber location calculatedLastService manualLastService} mutationErrors{fieldName messages}}}',
        {"id": piano_id, "input": entree})
    data = (res.get("data") or {}).get("updatePiano") or {}
    if res.get("errors") or data.get("mutationErrors"):
        raise HTTPException(502, str(res.get("errors") or data.get("mutationErrors")))
    return data.get("piano")


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


class StatMontantIn(BaseModel):
    client_id: str
    piano_id: str
    montant: float   # montant du reçu de stationnement


@router.post("/gazelle/timeline/{entry_id}/montant-stat")
def completer_montant_stat(entry_id: str, m: StatMontantIn):
    """Ajoute le montant à une note de service qui dit « stat » SANS montant
    (ex. « Accord pour adisq stat » → « Accord pour adisq stat 20 »). Ne touche rien
    d'autre dans la note, garde sa date, et refuse si la note a déjà un montant."""
    import re as _re
    from core.gazelle_api_client import GazelleAPIClient
    from modules.place_des_arts.services.gazelle_sync import extract_parking_amount
    if not (0 < m.montant < 200):
        raise HTTPException(400, "Montant invalide")
    entrees = timeline_piano_gazelle(client_id=m.client_id, piano_id=m.piano_id, limite=50)["entrees"]
    e = next((x for x in entrees if x["id"] == entry_id), None)
    if not e:
        raise HTTPException(404, "Entrée introuvable pour ce piano")
    texte = e.get("comment") or ""
    if extract_parking_amount(texte):
        raise HTTPException(409, "Cette note a déjà un montant de stationnement : rien n'a été changé")
    mot = _re.search(r"(?<![a-zà-ÿ])stat(?![a-zà-ÿ])", texte, _re.IGNORECASE)
    if not mot:
        raise HTTPException(409, "Pas de « stat » dans cette note : rien n'a été changé")
    montant = f"{m.montant:g}"
    nouveau = texte[:mot.end()] + f" {montant}" + texte[mot.end():]
    gz = GazelleAPIClient()
    entree = {"comment": nouveau}
    if e.get("occurredAt"):
        entree["createdAt"] = e["occurredAt"]
    try:
        res = gz._execute_query("""mutation($id: String!, $c: String!, $input: PrivateClientLogInput!) {
          updateClientLog(id: $id, clientId: $c, input: $input) { mutationErrors { fieldName messages } } }""",
                                {"id": e.get("relatedId") or entry_id, "c": m.client_id, "input": entree})
    except Exception as ex:
        raise HTTPException(502, f"Gazelle : {ex}")
    err = ((res.get("data") or {}).get("updateClientLog") or {}).get("mutationErrors") or res.get("errors")
    if err:
        raise HTTPException(502, str(err))
    # Copie locale : le vérificateur du matin lit Supabase
    requests.patch(f"{_db().api_url}/gazelle_timeline_entries?external_id=eq.{entry_id}",
                   headers=_db()._get_headers(), json={"description": nouveau}, timeout=15)
    return {"entree": entry_id, "avant": texte, "apres": nouveau}


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


# --- Rapport des fiches clients en double (lecture seule) ---
_dernier_rapport_doublons = [0.0]


@router.post("/gazelle/rapport-doublons")
def rapport_doublons(tous: bool = Query(False)):
    """Envoie à asutton@ les fiches en double (rien n'est modifié dans Gazelle).
    tous=true : y compris les groupes déjà revus. La réponse ne contient aucune
    donnée personnelle : seulement le nombre de groupes."""
    if time.time() - _dernier_rapport_doublons[0] < 600:
        raise HTTPException(429, "Rapport déjà envoyé il y a moins de 10 minutes")
    _dernier_rapport_doublons[0] = time.time()
    from core.email_notifier import get_email_notifier
    from modules.alerts.clients_doublons import trouver_doublons, corps_rapport
    groupes = trouver_doublons(tous=tous)
    ok = get_email_notifier().send_email(to_emails=["asutton@piano-tek.com"],
                                         subject=f"Fiches clients en double — {len(groupes)} groupe(s)",
                                         html_content=corps_rapport(groupes))
    if not ok:
        raise HTTPException(502, "Courriel non envoyé")
    return {"ok": True, "groupes": len(groupes)}


@router.post("/gazelle/fusionner-doublons-approuves")
def fusionner_doublons_approuves(limite: int = Query(0, ge=0, le=50),
                                 seulement: str = Query("", pattern=r"^(cli_[A-Za-z0-9]+>cli_[A-Za-z0-9]+)?$")):
    """Exécute UNIQUEMENT la liste de fusions décidée par Allan (FUSIONS_APPROUVEES,
    dans le code). Idempotent : une fusion déjà faite est passée.
    `seulement="source>cible"` : une seule fusion de la liste (aucune hors liste)."""
    from modules.alerts.clients_doublons import fusionner_approuves
    return fusionner_approuves(limite, seulement)


@router.post("/gazelle/supprimer-fiches-approuvees")
def supprimer_fiches_approuvees():
    """Supprime UNIQUEMENT les fiches de SUPPRESSIONS_APPROUVEES (dans le code, décidées par
    Allan), et seulement si la fiche est vide : aucun piano, rendez-vous ni facture."""
    from modules.alerts.clients_doublons import supprimer_approuvees
    return supprimer_approuvees()


class FicheTestEquipe(BaseModel):
    prenom: str
    nom: str
    courriel: str
    rue: str
    ville: str = "Montréal"
    code_postal: str
    marque: str
    modele: str
    type_piano: str = "UPRIGHT"


@router.post("/gazelle/fiche-test-equipe")
def fiche_test_equipe(f: FicheTestEquipe):
    """Crée une fiche client TEST pour un membre de l'équipe (essai de la réservation en ligne) :
    sans cycle de rappels, étiquetée « test-equipe », avec un piano. Retourne le lien personnel."""
    from core.gazelle_api_client import GazelleAPIClient
    gz = GazelleAPIClient()
    nom_complet = f"{f.prenom} {f.nom}"
    # Garde-fou : pas de doublon si la fiche test existe déjà
    try:
        deja = gz._execute_query("""query($s: String) { allClients(first: 20, search: $s) {
            nodes { id tags } } }""", {"s": nom_complet})
    except Exception as e:
        logging.getLogger(__name__).warning("fiche-test-equipe : recherche de doublon impossible : %s", e)
        deja = {}
    for c in ((deja.get("data") or {}).get("allClients") or {}).get("nodes") or []:
        if "test-equipe" in (c.get("tags") or []):
            return {"deja": True, "client_id": c["id"], "lien": f"https://reserver.pianotechniquemontreal.com/?client={c['id']}"}
    contact = {"isDefault": True, "isBillingDefault": True, "firstName": f.prenom, "lastName": f.nom,
               "emails": [{"isDefault": True, "email": f.courriel}],
               "locations": [{"locationType": "ADDRESS", "usageType": "STREET", "street1": f.rue,
                              "municipality": f.ville, "region": "QC", "postalCode": f.code_postal, "countryCode": "CA"}]}
    entree = {"status": "ACTIVE", "contacts": [contact], "tags": ["test-equipe"], "lifecycleId": None,
              "personalNotes": "FICHE TEST de l'équipe PTM pour essayer la réservation en ligne. "
                               "Adresse et piano fictifs. Ne pas planifier, ne pas facturer."}
    try:
        r = gz._execute_query("""mutation($i: PrivateClientInput!) { createClient(input: $i) {
            client { id } mutationErrors { fieldName messages } } }""", {"i": entree})
    except Exception as e:
        raise HTTPException(502, f"createClient : {e}")
    p = (r.get("data") or {}).get("createClient") or {}
    if r.get("errors") or p.get("mutationErrors") or not (p.get("client") or {}).get("id"):
        raise HTTPException(502, f"createClient : {r.get('errors') or p.get('mutationErrors')}")
    cid = p["client"]["id"]
    try:
        rp = gz._execute_query("""mutation($i: PrivatePianoInput!) { createPiano(input: $i) {
        piano { id make model type } mutationErrors { fieldName messages } } }""",
                           {"i": {"clientId": cid, "type": f.type_piano, "make": f.marque, "model": f.modele,
                                  "location": "Salon", "status": "ACTIVE", "tags": ["test-equipe"]}})
    except Exception as e:
        rp = {"errors": str(e)}
    pp = (rp.get("data") or {}).get("createPiano") or {}
    return {"deja": False, "client_id": cid, 
            "piano": pp.get("piano"), "erreurs_piano": rp.get("errors") or pp.get("mutationErrors"),
            "lien": f"https://reserver.pianotechniquemontreal.com/?client={cid}"}


class ClientEntrepriseIn(BaseModel):
    entreprise: str
    prenom: str
    nom: str
    courriel: str
    telephone: Optional[str] = None
    rue: str
    ville: str
    region: Optional[str] = None
    code_postal: str
    pays: str = "CA"          # code ISO à 2 lettres
    notes: Optional[str] = None


@router.post("/gazelle/client-entreprise")
def creer_client_entreprise(c: ClientEntrepriseIn):
    """Crée une fiche Gazelle d'entreprise (ex. fabricant, partenaire à facturer), SANS cycle de
    rappels. Refuse s'il existe déjà une fiche au même nom d'entreprise (jamais de doublon)."""
    from core.gazelle_api_client import GazelleAPIClient
    gz = GazelleAPIClient()
    deja = gz._execute_query("""query($s: String) { allClients(first: 20, search: $s) {
        nodes { id companyName } } }""", {"s": c.entreprise})
    if deja.get("errors"):
        raise HTTPException(502, f"Recherche de doublon impossible : {deja['errors']}")
    for n in ((deja.get("data") or {}).get("allClients") or {}).get("nodes") or []:
        if (n.get("companyName") or "").strip().lower() == c.entreprise.strip().lower():
            raise HTTPException(409, f"Fiche déjà existante : {n['id']} — rien créé")
    contact = {"isDefault": True, "isBillingDefault": True, "firstName": c.prenom, "lastName": c.nom,
               "emails": [{"isDefault": True, "email": c.courriel}],
               "locations": [{"locationType": "ADDRESS", "usageType": "STREET", "street1": c.rue,
                              "municipality": c.ville, "region": c.region, "postalCode": c.code_postal,
                              "countryCode": c.pays}]}
    if c.telephone:
        contact["phones"] = [{"isDefault": True, "type": "WORK", "phoneNumber": c.telephone}]
    entree = {"status": "ACTIVE", "companyName": c.entreprise, "contacts": [contact], "lifecycleId": None}
    if c.notes:
        entree["personalNotes"] = c.notes
    r = gz._execute_query("""mutation($i: PrivateClientInput!) { createClient(input: $i) {
        client { id companyName } mutationErrors { fieldName messages } } }""", {"i": entree})
    p = (r.get("data") or {}).get("createClient") or {}
    if r.get("errors") or p.get("mutationErrors") or not (p.get("client") or {}).get("id"):
        raise HTTPException(502, f"createClient : {r.get('errors') or p.get('mutationErrors')}")
    return p["client"]


# --- Rapport LECTURE SEULE : rétention des clients d'accords de courtoisie (Nantel vs Archambault) ---
# Rien n'est écrit dans Gazelle. Parcourt toutes les factures en direct (la copie Supabase s'arrête en mars 2026).
_rapport_courtoisie: Dict[str, Any] = {"statut": "jamais_lance"}
_EXCLUS = {"VOIDED", "VOID", "DRAFT", "CANCELED", "CANCELLED"}


def _marchand(texte: str) -> Optional[str]:
    t = texte.lower()
    if "nantel" in t:
        return "Nantel"
    if "archambault" in t:
        return "Archambault"
    if _re.search(r"piano[s]?[ -]?vertu", t):
        return "Piano Vertu"
    return None


_MOTS_MARCHAND = _re.compile(r"nantel|archambault|pianos?[ -]?vertu", _re.IGNORECASE)


def _resumer(clients: List[Dict[str, Any]], cle: str) -> Dict[str, Any]:
    resume: Dict[str, Any] = {}
    for c in clients:
        r = resume.setdefault(c.get(cle) or "Non précisé",
                              {"clients": 0, "revenus": 0, "par_annee": {}, "eligibles_12": 0, "revenus_12": 0})
        r["clients"] += 1
        r["revenus"] += 1 if c["visites_payees_apres"] else 0
        r["paye_courtoisie"] = round(r.get("paye_courtoisie", 0) + c.get("paye_courtoisie", 0), 2)
        r["ventes_apres"] = round(r.get("ventes_apres", 0) + c.get("revenus_apres_dollars", 0), 2)
        r["visites_apres"] = r.get("visites_apres", 0) + c["visites_payees_apres"]
        if c["eligible_12_mois"]:
            r["eligibles_12"] += 1
            r["revenus_12"] += 1 if c["revenu_12_mois"] else 0
        a = r["par_annee"].setdefault(c["date_courtoisie"][:4], {"clients": 0, "revenus": 0})
        a["clients"] += 1
        a["revenus"] += 1 if c["visites_payees_apres"] else 0
    for r in resume.values():
        r["taux"] = round(100 * r["revenus"] / r["clients"], 1) if r["clients"] else None
        r["taux_12"] = round(100 * r["revenus_12"] / r["eligibles_12"], 1) if r["eligibles_12"] else None
    return resume


def _rattacher_non_precises(clients: List[Dict[str, Any]], par_client: Dict[str, List[Dict[str, Any]]]) -> None:
    """Cherche le marchand des courtoisies « non précisé » : autres factures, fiche Gazelle, courriels Front.
    LECTURE SEULE. Résultat dans c["marchand_final"] et c["preuve"]."""
    from core.gazelle_api_client import GazelleAPIClient
    gz = GazelleAPIClient()
    front = None
    try:
        from core.front_client import get_front_client
        from api.ivo_routes import _texte
        front = get_front_client()
    except Exception as e:
        _log.warning("Front indisponible : %s", e)
    for c in clients:
        c["marchand_final"], c["preuve"] = c["marchand"], None
        if c["marchand"] != "Non précisé":
            continue
        # 1. Autres factures du client
        for f in par_client.get(c["client_id"], []):
            m = _marchand(f["texte"])
            if m:
                c["marchand_final"], c["preuve"] = m, f"Facture {f['date']}"
                break
        courriels: List[str] = []
        # 2. Fiche Gazelle
        try:
            r = gz._execute_query("""query($id: String!) { client(id: $id) { referredBy referredByNotes personalNotes
                preferenceNotes allContacts { nodes { allEmails { nodes { email } } } } } }""", {"id": c["client_id"]})
            fiche = ((r or {}).get("data") or {}).get("client") or {}
            for n in ((fiche.get("allContacts") or {}).get("nodes") or []):
                courriels += [e["email"].lower() for e in ((n.get("allEmails") or {}).get("nodes") or []) if e.get("email")]
            if c["preuve"] is None:
                for champ in ("referredBy", "referredByNotes", "personalNotes", "preferenceNotes"):
                    m = _marchand(str(fiche.get(champ) or ""))
                    if m:
                        c["marchand_final"], c["preuve"] = m, f"Fiche Gazelle ({champ})"
                        break
        except Exception as e:
            _log.warning("fiche %s : %s", c["client_id"], e)
        c["courriels"] = courriels
        # 3. Courriels Front (tous messages, entrants et sortants)
        if c["preuve"] is None and front and courriels:
            for adr in courriels[:2]:
                try:
                    convs = front.search_conversations(adr, limit=25)
                except Exception:
                    continue
                trouve = False
                for conv in convs:
                    if _MOTS_MARCHAND.search(conv.get("subject") or ""):
                        m = _marchand(conv["subject"])
                        c["marchand_final"], c["preuve"] = m, f"Front (objet) : {conv['subject'][:120]}"
                        trouve = True
                        break
                    try:
                        msgs = front.list_messages(conv["id"], limit=30)
                    except Exception:
                        continue
                    time.sleep(0.4)
                    for msg in msgs:
                        texte = _texte(msg.get("text") or msg.get("body") or "")
                        hit = _MOTS_MARCHAND.search(texte)
                        if hit:
                            date = datetime.fromtimestamp(msg.get("created_at") or 0, timezone.utc).strftime("%Y-%m-%d")
                            c["marchand_final"] = _marchand(hit.group(0))
                            c["preuve"] = f"Front {date} : …{texte[max(0, hit.start() - 100):hit.start() + 120]}…"
                            trouve = True
                            break
                    if trouve:
                        break
                if trouve:
                    break
                time.sleep(0.4)
        # 4. Règle d'Allan : avant 2025 (avant Nantel et Piano Vertu), toutes les courtoisies venaient d'Archambault
        if c["preuve"] is None and c["date_courtoisie"] < "2025-01-01":
            c["marchand_final"], c["preuve"] = "Archambault", "Déduit : avant 2025, seul Archambault"


def _calculer_courtoisie() -> None:
    from core.gazelle_api_client import GazelleAPIClient
    api = GazelleAPIClient()
    q = """query R($cursor: String) { allInvoices(first: 100, after: $cursor) {
      edges { node { id number status createdAt total notes topNotes
        client { id companyName defaultContact { firstName lastName } }
        allInvoiceItems { nodes { description } } } }
      pageInfo { hasNextPage endCursor } } }"""
    _rapport_courtoisie.clear()
    _rapport_courtoisie.update({"statut": "en_cours", "debut": datetime.now(timezone.utc).isoformat(), "pages": 0})
    factures: List[Dict[str, Any]] = []
    cursor = None
    try:
        for _ in range(1000):
            res = api._execute_query(q, {"cursor": cursor} if cursor else {})
            if res.get("errors"):
                raise RuntimeError(str(res["errors"])[:500])
            bloc = (res.get("data") or {}).get("allInvoices") or {}
            for e in bloc.get("edges") or []:
                n = e["node"]
                cl = n.get("client") or {}
                dc = cl.get("defaultContact") or {}
                desc = " | ".join((it.get("description") or "") for it in ((n.get("allInvoiceItems") or {}).get("nodes") or []))
                factures.append({
                    "id": n["id"], "numero": n.get("number"), "statut": (n.get("status") or "").upper(),
                    "date": (n.get("createdAt") or "")[:10],
                    "total": n.get("total") or 0, "client_id": cl.get("id"),
                    "client": cl.get("companyName") or f"{dc.get('firstName') or ''} {dc.get('lastName') or ''}".strip(),
                    "texte": f"{desc} | {n.get('notes') or ''} | {n.get('topNotes') or ''}",
                })
            _rapport_courtoisie["pages"] += 1
            pi = bloc.get("pageInfo") or {}
            if not pi.get("hasNextPage"):
                break
            cursor = pi.get("endCursor")

        valides = [f for f in factures if f["statut"] not in _EXCLUS and f["client_id"]]
        par_client: Dict[str, List[Dict[str, Any]]] = {}
        for f in valides:
            par_client.setdefault(f["client_id"], []).append(f)

        clients: List[Dict[str, Any]] = []
        for cid, fs in par_client.items():
            fs.sort(key=lambda f: f["date"])
            court = [f for f in fs if "courtoisie" in f["texte"].lower()]
            if not court:
                continue
            premiere = court[0]
            marchand = next((m for m in (_marchand(f["texte"]) for f in court) if m), None) or "Non précisé"
            apres = [f for f in fs if f["date"] > premiere["date"] and f not in court and (f["total"] or 0) > 0]
            d0 = datetime.fromisoformat(premiere["date"])
            dans_12 = [f for f in apres if (datetime.fromisoformat(f["date"]) - d0).days <= 365]
            clients.append({
                "revenu_12_mois": bool(dans_12), "eligible_12_mois": (datetime.now() - d0).days >= 365,
                "paye_courtoisie": round(sum((f["total"] or 0) for f in court) / 100, 2),
                "revenus_apres_dollars": round(sum((f["total"] or 0) for f in apres) / 100, 2),
                "client_id": cid, "client": premiere["client"], "marchand": marchand,
                "date_courtoisie": premiere["date"], "visites_payees_apres": len(apres),
                "derniere_visite": apres[-1]["date"] if apres else None,
                "extrait": premiere["texte"][:160],
            })

        _rattacher_non_precises(clients, par_client)

        # Diagnostic : courtoisies facturées au marchand lui-même (client final absent de la facture)
        au_marchand: Dict[str, int] = {}
        for f in valides:
            m = _marchand(f["client"] or "")
            if m:
                au_marchand[m] = au_marchand.get(m, 0) + 1

        resume = _resumer(clients, "marchand")
        resume_rattache = _resumer(clients, "marchand_final")

        _rapport_courtoisie.update({
            "statut": "termine", "fin": datetime.now(timezone.utc).isoformat(),
            "factures_lues": len(factures), "resume": resume, "resume_rattache": resume_rattache,
            "factures_au_nom_du_marchand": au_marchand,
            "clients": sorted(clients, key=lambda c: (c["marchand"], c["date_courtoisie"])),
        })
    except Exception as e:
        _log.exception("rapport courtoisie")
        _rapport_courtoisie.update({"statut": "erreur", "erreur": str(e)[:500]})


@router.post("/rapports/courtoisie")
def lancer_rapport_courtoisie(request: Request):
    """LECTURE SEULE — lance en arrière-plan l'analyse des accords de courtoisie."""
    if _restreint(request):
        raise HTTPException(403, "Réservé à la direction")
    if _rapport_courtoisie.get("statut") == "en_cours":
        return {"statut": "en_cours"}
    import threading
    threading.Thread(target=_calculer_courtoisie, daemon=True).start()
    return {"statut": "lance"}


@router.get("/rapports/courtoisie")
def lire_rapport_courtoisie(request: Request):
    if _restreint(request):
        raise HTTPException(403, "Réservé à la direction")
    return _rapport_courtoisie




@router.get("/gazelle/messages")
def messages_gazelle(q: Optional[str] = Query(None, max_length=80), client_id: Optional[str] = Query(None),
                     limite: int = Query(25, ge=1, le=100)):
    """LECTURE — messages envoyés/planifiés par Gazelle (section « Messages ») avec leur statut de suivi :
    ouvert, cliqué, livré, rejeté… `q` = recherche Gazelle (ex. numéro de soumission ou de facture, nom);
    `client_id` filtre sur un client (sans `q`, on cherche par le nom du client). Heures de Montréal."""
    if not q and not client_id:
        raise HTTPException(400, "Fournir q (recherche) ou client_id")
    from core import historique_client as hc
    try:
        if q:
            return {"messages": hc.messages_gazelle(q=q, client_id=client_id, limite=limite, pages=5 if client_id else 1)}
        return {"messages": hc.messages_du_client(client_id, limite=limite)}
    except Exception as e:
        raise HTTPException(502, str(e))


@router.get("/gazelle/historique")
def historique_gazelle(client_id: str = Query(...)):
    """LECTURE — dossier complet d'un client : fiche, chronologie, factures, soumissions (avec suivi
    d'ouverture du courriel) et messages Gazelle avec leur statut."""
    from core.historique_client import dossier_client
    return {"client_id": client_id, "dossier": dossier_client(client_id)}
