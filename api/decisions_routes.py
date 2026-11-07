"""Volet « Décisions » — points à trancher par Allan et Nicolas.

Remplace les panneaux de décisions publiés à part (dont les votes de Nicolas ne
s'enregistraient pas). Chaque point porte un vote par personne : ok (Approuver),
talk (À discuter) ou no (Refuser), avec une note.

Règle de décision (calculée par le serveur, jamais par la page) :
  - quelqu'un a choisi « À discuter »          → a_discuter
  - tous les votants ont voté, tous ok         → approuvee
  - tous les votants ont voté, tous no         → refusee
  - tous les votants ont voté, votes différents → a_discuter
  - sinon                                      → en_attente (de la personne qui n'a pas voté)

Stockage : table Supabase `decisions` (sql/auto/013_decisions.sql).
Accès : Allan et Nicolas (jeton signé). Claude dépose les points et lit les
résultats par l'API ; seul un jeton de personne peut voter (on vote en son nom).
"""
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import requests
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from core.supabase_storage import SupabaseStorage

_log = logging.getLogger(__name__)

PERSONNES = {"allan": "Allan", "nicolas": "Nicolas"}
_QUI = {"allan": "allan", "nick": "nicolas", "nicolas": "nicolas"}
VOTES = ("ok", "talk", "no")
STATUTS = ("en_attente", "a_discuter", "approuvee", "refusee")


def _qui(request: Request) -> Optional[str]:
    """Personne connectée d'après son jeton (identité réelle : on ignore « voir comme »)."""
    from core import verrou_api
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        d = verrou_api.verifier_jeton(auth[7:])
        if d:
            return _QUI.get(d.get("qui"), d.get("qui") or "inconnu")
    return None


def _acces(request: Request) -> Optional[str]:
    """Allan et Nicolas seulement. Sans jeton : tâche automatique ou Claude (comme le
    reste de l'API tant que le verrou est en mode observation)."""
    q = _qui(request)
    if q is not None and q not in PERSONNES:
        raise HTTPException(403, "Réservé à Allan et Nicolas")
    return q


router = APIRouter(prefix="/decisions", tags=["decisions"], dependencies=[Depends(_acces)])

_storage: Optional[SupabaseStorage] = None


def _db() -> SupabaseStorage:
    global _storage
    if _storage is None:
        _storage = SupabaseStorage(silent=True)
    return _storage


def _url(query: str = "") -> str:
    return f"{_db().api_url}/decisions{query}"


def _h(extra: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    h = dict(_db()._get_headers())
    h.update(extra or {})
    return h


def _check(resp: requests.Response) -> Any:
    if resp.status_code >= 400:
        detail = resp.text[:300]
        if "decisions" in detail and ("does not exist" in detail or "schema cache" in detail):
            raise HTTPException(503, "Table « decisions » absente : la migration sql/auto/013_decisions.sql n'a pas encore été appliquée.")
        raise HTTPException(502, f"Supabase {resp.status_code}: {detail}")
    return resp.json() if resp.text else None


def statut_de(votes: Dict[str, Any], votants: List[str]) -> str:
    """La règle de décision (voir l'en-tête)."""
    choix = {p: ((votes or {}).get(p) or {}).get("s") for p in votants}
    if any(s == "talk" for s in choix.values()):
        return "a_discuter"
    if any(s not in ("ok", "no") for s in choix.values()):
        return "en_attente"
    valeurs = set(choix.values())
    if valeurs == {"ok"}:
        return "approuvee"
    if valeurs == {"no"}:
        return "refusee"
    return "a_discuter"


def _maintenant() -> str:
    return datetime.now(timezone.utc).isoformat()


def _lire(did: str) -> Dict[str, Any]:
    rows = _check(requests.get(_url(f"?id=eq.{did}&select=*"), headers=_h(), timeout=15)) or []
    if not rows:
        raise HTTPException(404, "Décision introuvable")
    return rows[0]


# ─── Lecture ─────────────────────────────────────────────────────

@router.get("")
def lister(archives: bool = False, statut: Optional[str] = None, sujet: Optional[str] = None):
    q = "?select=*&order=sujet.asc,ordre.asc,created_at.asc"
    if not archives:
        q += "&archive=eq.false"
    if statut:
        if statut not in STATUTS:
            raise HTTPException(400, f"Statut inconnu : {statut}")
        q += f"&statut=eq.{statut}"
    if sujet:
        from urllib.parse import quote
        q += f"&sujet=eq.{quote(sujet)}"
    return {"decisions": _check(requests.get(_url(q), headers=_h(), timeout=20)) or [],
            "personnes": PERSONNES}


@router.get("/a-voter")
def a_voter(request: Request):
    """Nombre de points qui attendent le vote de la personne connectée (pastille du menu)."""
    q = _qui(request)
    rows = _check(requests.get(_url("?select=votes,votants,statut&archive=eq.false&statut=in.(en_attente,a_discuter)"),
                               headers=_h(), timeout=15)) or []
    if not q:
        return {"n": 0}
    n = sum(1 for r in rows if q in (r.get("votants") or []) and not ((r.get("votes") or {}).get(q) or {}).get("s"))
    return {"n": n}


# ─── Dépôt des points (Claude, ou Allan) ─────────────────────────

class PointIn(BaseModel):
    titre: str
    sujet: Optional[str] = None
    groupe: Optional[str] = None
    type: Optional[str] = None
    avant: Optional[str] = None
    apres: Optional[str] = None
    changements: Optional[List[List[str]]] = None
    info: Optional[str] = None
    consigne: Optional[str] = None
    question: Optional[str] = None
    recommandation: Optional[str] = None
    page: Optional[str] = None
    lien: Optional[str] = None
    lien_wp: Optional[str] = None
    rid: Optional[int] = None
    ordre: Optional[int] = None
    votants: Optional[List[str]] = None
    votes: Optional[Dict[str, Dict[str, Any]]] = None  # import des votes déjà donnés
    source: Optional[str] = None
    cle_source: Optional[str] = None
    depuis: Optional[str] = None  # AAAA-MM-JJ


def _ligne(p: PointIn, qui: Optional[str]) -> Dict[str, Any]:
    votants = [v for v in (p.votants or ["allan", "nicolas"]) if v in PERSONNES] or ["allan", "nicolas"]
    votes = {k: {"s": v.get("s"), "note": v.get("note") or "", "at": v.get("at") or _maintenant()}
             for k, v in (p.votes or {}).items() if k in PERSONNES and v.get("s") in VOTES + ("",)}
    statut = statut_de(votes, votants)
    ligne = {k: v for k, v in p.model_dump().items() if v is not None and k not in ("votes", "votants")}
    ligne.update(votes=votes, votants=votants, statut=statut, cree_par=qui or "claude",
                 type=p.type if p.type in ("point", "revision_wp") else "point",
                 sujet=(p.sujet or "Général").strip() or "Général")
    if statut in ("approuvee", "refusee"):
        ligne["decidee_le"] = max((v.get("at") or "") for v in votes.values()) or _maintenant()
    return ligne


@router.post("")
def creer(points: List[PointIn], request: Request):
    """Dépose un ou plusieurs points. Un point dont la cle_source existe déjà est ignoré
    (on peut rejouer un import sans créer de doublons)."""
    if not points:
        return {"crees": 0, "ignores": 0, "decisions": []}
    qui = _qui(request)
    if qui == "nicolas":
        raise HTTPException(403, "Seul Allan (ou Claude) dépose des points")
    lignes = [_ligne(p, qui) for p in points]
    cles = [l["cle_source"] for l in lignes if l.get("cle_source")]
    existantes = set()
    if cles:
        from urllib.parse import quote
        lot = ",".join(f'"{quote(c)}"' for c in cles)
        existantes = {r["cle_source"] for r in (_check(requests.get(
            _url(f"?select=cle_source&cle_source=in.({lot})"), headers=_h(), timeout=20)) or [])}
    nouvelles = [l for l in lignes if not l.get("cle_source") or l["cle_source"] not in existantes]
    crees = []
    # Insertions une par une : PostgREST exige les mêmes colonnes dans un lot.
    for l in nouvelles:
        crees += _check(requests.post(_url(), headers=_h({"Prefer": "return=representation"}), json=l, timeout=20)) or []
    return {"crees": len(crees), "ignores": len(lignes) - len(nouvelles), "decisions": crees}


# ─── Vote ────────────────────────────────────────────────────────

class VoteIn(BaseModel):
    s: Optional[str] = None      # ok | talk | no | "" (retirer le vote) ; absent = note seule
    note: Optional[str] = None


@router.post("/{did}/vote")
def voter(did: str, v: VoteIn, request: Request):
    qui = _qui(request)
    if qui not in PERSONNES:
        raise HTTPException(401, "Connexion requise")  # on ne vote qu'en son propre nom
    d = _lire(did)
    if qui not in (d.get("votants") or []):
        raise HTTPException(403, "Ce point ne demande pas ton vote")
    if v.s is not None and v.s not in VOTES + ("",):
        raise HTTPException(400, "Vote inconnu")
    votes = dict(d.get("votes") or {})
    mien = dict(votes.get(qui) or {})
    if v.s is not None:
        mien["s"] = v.s
    if v.note is not None:
        mien["note"] = v.note[:4000]
    mien["at"] = _maintenant()
    votes[qui] = mien
    statut = statut_de(votes, d.get("votants") or [])
    maj = {"votes": votes, "statut": statut, "updated_at": _maintenant()}
    if statut in ("approuvee", "refusee"):
        if d.get("statut") != statut:
            maj["decidee_le"] = _maintenant()
    else:
        maj["decidee_le"] = None
    rows = _check(requests.patch(_url(f"?id=eq.{did}"), headers=_h({"Prefer": "return=representation"}),
                                 json=maj, timeout=15)) or []
    return rows[0] if rows else {**d, **maj}


# ─── Suite (Claude note ce qui a été fait) et archivage ─────────

class MajIn(BaseModel):
    suite: Optional[str] = None
    realisee: Optional[bool] = None
    archive: Optional[bool] = None
    votants: Optional[List[str]] = None
    titre: Optional[str] = None
    info: Optional[str] = None
    consigne: Optional[str] = None
    question: Optional[str] = None
    apres: Optional[str] = None


@router.patch("/{did}")
def modifier(did: str, m: MajIn, request: Request):
    if _qui(request) == "nicolas" and (m.votants is not None or m.titre is not None or m.apres is not None):
        raise HTTPException(403, "Seul Allan modifie le contenu d'un point")
    d = _lire(did)
    maj: Dict[str, Any] = {k: v for k, v in m.model_dump().items() if v is not None and k not in ("realisee", "votants")}
    if m.realisee is not None:
        maj["realisee_le"] = _maintenant() if m.realisee else None
    if m.votants is not None:
        votants = [p for p in m.votants if p in PERSONNES]
        if not votants:
            raise HTTPException(400, "Au moins un votant")
        maj["votants"] = votants
        maj["statut"] = statut_de(d.get("votes") or {}, votants)
        if maj["statut"] in ("approuvee", "refusee") and not d.get("decidee_le"):
            maj["decidee_le"] = _maintenant()
    maj["updated_at"] = _maintenant()
    rows = _check(requests.patch(_url(f"?id=eq.{did}"), headers=_h({"Prefer": "return=representation"}),
                                 json=maj, timeout=15)) or []
    return rows[0] if rows else {**d, **maj}
