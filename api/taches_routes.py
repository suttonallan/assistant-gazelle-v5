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
    urgent: Optional[bool] = None
    client: Optional[str] = None  # pda, vdi, orford, prive… (couleur dans l'échéancier)


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
def factures_gazelle_campagne(slug: str, depuis: str = Query("2025-01-01")):
    """Factures du client de la campagne, lues en direct dans Gazelle (mémoire 1 h)."""
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
    """Soumissions Gazelle récentes d'un client (numéro, date, total, archivée)."""
    from core.gazelle_api_client import GazelleAPIClient
    q = """query($c: String) { allEstimates(first: 20, filters: {clientId: $c}) {
      nodes { id number estimatedOn isArchived recommendedTierTotal
        allEstimateTiers { allUngroupedEstimateTierItems { name amount } } } } }"""
    try:
        res = GazelleAPIClient()._execute_query(q, {"c": client_id})
    except Exception as e:
        raise HTTPException(502, str(e))
    return res


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
