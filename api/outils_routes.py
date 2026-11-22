"""Suivi des outils et de l'équipement partagés — qui a pris quoi.

Chaque outil suivi porte une étiquette QR (gravée au laser ou collée). Le QR
contient une adresse courte de l'API (/o/<numéro>) qui renvoie vers l'appli :
on pourra changer la destination plus tard sans regraver les étiquettes.
Dans l'appli, le technicien (déjà connecté) touche « Je le prends » ou
« Je le rapporte à l'atelier ».

Stockage : tables Supabase `outils` et `outils_mouvements` (sql/auto/016_outils.sql).
Identité : le jeton de connexion de la personne. Sans jeton (Claude, Ivo, tâche
automatique, tant que le verrou est en mode observation), le champ `qui` est requis.
"""
import io
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from xml.sax.saxutils import escape

import requests
import segno
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse, Response
from pydantic import BaseModel, Field

from core.supabase_storage import SupabaseStorage

_log = logging.getLogger(__name__)

URL_API = "https://assistant-gazelle-v5-api.onrender.com"
URL_APP = "https://suttonallan.github.io/assistant-gazelle-v5/"

# Clé stockée → nom affiché
PERSONNES = {
    "allan": "Allan",
    "nicolas": "Nicolas",
    "jean-philippe": "Jean-Philippe",
    "margot": "Margot",
    "louise": "Louise",
}
ATELIER = "atelier"
# Identifiants du jeton (core/verrou_api.PROFILS) → clé stockée
_DU_JETON = {"allan": "allan", "nick": "nicolas", "nicolas": "nicolas", "jp": "jean-philippe",
             "jean-philippe": "jean-philippe", "margot": "margot", "louise": "louise"}
GESTION = {"allan", "nicolas", "louise"}  # peuvent ajouter / modifier des outils


def _qui_jeton(request: Request) -> Optional[str]:
    from core import verrou_api
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        d = verrou_api.verifier_jeton(auth[7:])
        if d:
            return _DU_JETON.get(d.get("qui"), d.get("qui") or None)
    return None


def _normaliser(nom: Optional[str]) -> Optional[str]:
    if not nom:
        return None
    n = nom.strip().lower().replace("é", "e").replace(" ", "-")
    n = {"nick": "nicolas", "jp": "jean-philippe", "jeanphilippe": "jean-philippe"}.get(n, n)
    return n if n in PERSONNES else None


def _qui(request: Request, fourni: Optional[str]) -> str:
    q = _qui_jeton(request) or _normaliser(fourni)
    if not q:
        raise HTTPException(400, "Qui ? (connexion requise ou champ « qui » : " + ", ".join(PERSONNES) + ")")
    return q


def _gestion(request: Request) -> None:
    q = _qui_jeton(request)
    if q is not None and q not in GESTION:
        raise HTTPException(403, "Réservé à Allan, Nicolas et Louise")


router = APIRouter(prefix="/outils", tags=["outils"])
router_court = APIRouter(tags=["outils"])  # /o/<numéro> : adresse des étiquettes QR

_storage: Optional[SupabaseStorage] = None


def _db() -> SupabaseStorage:
    global _storage
    if _storage is None:
        _storage = SupabaseStorage(silent=True)
    return _storage


def _url(table: str, query: str = "") -> str:
    return f"{_db().api_url}/{table}{query}"


def _h(extra: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    h = dict(_db()._get_headers())
    h.update(extra or {})
    return h


def _check(resp: requests.Response) -> Any:
    if resp.status_code >= 400:
        detail = resp.text[:300]
        if "outils" in detail and ("does not exist" in detail or "schema cache" in detail):
            raise HTTPException(503, "Table « outils » absente : la migration sql/auto/016_outils.sql n'a pas encore été appliquée.")
        raise HTTPException(502, f"Supabase {resp.status_code}: {detail}")
    return resp.json() if resp.text else None


def _maintenant() -> str:
    return datetime.now(timezone.utc).isoformat()


def _affiche(o: Dict[str, Any]) -> Dict[str, Any]:
    d = o.get("detenteur") or ATELIER
    o["detenteur_nom"] = "Atelier" if d == ATELIER else PERSONNES.get(d, d)
    o["lien_qr"] = f"{URL_API}/o/{o['id']}"
    return o


def _lire(oid: int) -> Dict[str, Any]:
    rows = _check(requests.get(_url("outils", f"?id=eq.{oid}&select=*"), headers=_h(), timeout=15)) or []
    if not rows:
        raise HTTPException(404, "Outil introuvable")
    return rows[0]


def _mouvement(oid: int, action: str, qui: Optional[str], avant: Optional[str], apres: Optional[str], note: Optional[str]) -> None:
    try:
        _check(requests.post(_url("outils_mouvements"), headers=_h(), timeout=15, json={
            "outil_id": oid, "action": action, "qui": qui,
            "detenteur_avant": avant, "detenteur_apres": apres, "note": note,
        }))
    except HTTPException as e:
        _log.warning("Mouvement d'outil non journalisé (%s) : %s", oid, e.detail)


# ─── Lecture ─────────────────────────────────────────────────────

@router.get("")
def lister(inactifs: bool = False, detenteur: Optional[str] = None):
    q = "?select=*&order=categorie.asc,nom.asc"
    if not inactifs:
        q += "&actif=eq.true"
    if detenteur:
        d = ATELIER if detenteur.lower() == ATELIER else _normaliser(detenteur)
        if not d:
            raise HTTPException(400, "Détenteur inconnu")
        q += f"&detenteur=eq.{d}"
    rows = _check(requests.get(_url("outils", q), headers=_h(), timeout=15)) or []
    return {"outils": [_affiche(o) for o in rows], "personnes": PERSONNES}


@router.get("/{oid}")
def lire(oid: int):
    o = _affiche(_lire(oid))
    hist = _check(requests.get(_url("outils_mouvements", f"?outil_id=eq.{oid}&select=*&order=le.desc&limit=20"),
                               headers=_h(), timeout=15)) or []
    for m in hist:
        m["qui_nom"] = PERSONNES.get(m.get("qui"), m.get("qui") or "?")
    o["historique"] = hist
    return o


# ─── Prendre / rapporter ────────────────────────────────────────

class MouvementIn(BaseModel):
    qui: Optional[str] = Field(None, max_length=40, description="Seulement sans jeton (Claude, Ivo)")
    note: Optional[str] = Field(None, max_length=300)


@router.post("/{oid}/prendre")
def prendre(oid: int, m: MouvementIn, request: Request):
    qui = _qui(request, m.qui)
    o = _lire(oid)
    if not o.get("actif"):
        raise HTTPException(409, "Outil retiré")
    avant = o.get("detenteur") or ATELIER
    if avant != qui:
        _check(requests.patch(_url("outils", f"?id=eq.{oid}"), headers=_h(), timeout=15,
                              json={"detenteur": qui, "depuis": _maintenant()}))
        _mouvement(oid, "prendre", qui, avant, qui, m.note)
    return lire(oid)


@router.post("/{oid}/rapporter")
def rapporter(oid: int, m: MouvementIn, request: Request):
    qui = _qui(request, m.qui)
    o = _lire(oid)
    avant = o.get("detenteur") or ATELIER
    if avant != ATELIER:
        _check(requests.patch(_url("outils", f"?id=eq.{oid}"), headers=_h(), timeout=15,
                              json={"detenteur": ATELIER, "depuis": _maintenant()}))
        _mouvement(oid, "rapporter", qui, avant, ATELIER, m.note)
    return lire(oid)


# ─── Gestion (Allan, Nicolas, Louise) ───────────────────────────

class OutilIn(BaseModel):
    nom: str = Field(..., min_length=1, max_length=120)
    categorie: Optional[str] = Field(None, max_length=60)
    description: Optional[str] = Field(None, max_length=500)
    valeur: Optional[float] = None
    detenteur: Optional[str] = Field(None, max_length=40)


class OutilMaj(BaseModel):
    nom: Optional[str] = Field(None, min_length=1, max_length=120)
    categorie: Optional[str] = Field(None, max_length=60)
    description: Optional[str] = Field(None, max_length=500)
    valeur: Optional[float] = None
    actif: Optional[bool] = None


@router.post("")
def creer(outils: List[OutilIn], request: Request):
    """Ajoute un ou plusieurs outils (liste). Un nom déjà actif est ignoré."""
    _gestion(request)
    qui = _qui_jeton(request)
    existants = {(o["nom"] or "").strip().lower() for o in
                 (_check(requests.get(_url("outils", "?select=nom&actif=eq.true"), headers=_h(), timeout=15)) or [])}
    lignes = []
    for o in outils:
        cle = o.nom.strip().lower()
        if cle in existants:
            continue
        existants.add(cle)
        det = ATELIER
        if o.detenteur and o.detenteur.lower() != ATELIER:
            det = _normaliser(o.detenteur) or ATELIER
        lignes.append({"nom": o.nom.strip(), "categorie": (o.categorie or "Général").strip() or "Général",
                       "description": o.description, "valeur": o.valeur, "detenteur": det})
    crees = []
    if lignes:
        crees = _check(requests.post(_url("outils"), headers=_h({"Prefer": "return=representation"}),
                                     timeout=20, json=lignes)) or []
        for c in crees:
            _mouvement(c["id"], "creer", qui, None, c["detenteur"], None)
    return {"crees": [_affiche(c) for c in crees], "ignores": len(outils) - len(crees)}


@router.put("/{oid}")
def modifier(oid: int, m: OutilMaj, request: Request):
    _gestion(request)
    _lire(oid)
    maj = {k: v for k, v in m.model_dump().items() if v is not None}
    if maj:
        _check(requests.patch(_url("outils", f"?id=eq.{oid}"), headers=_h(), timeout=15, json=maj))
        if "actif" in maj:
            _mouvement(oid, "reactiver" if maj["actif"] else "retirer", _qui_jeton(request), None, None, None)
    return lire(oid)


# ─── Étiquettes QR (SVG vectoriel, pour le graveur laser) ───────

def _chemin_qr(texte: str) -> tuple:
    """Chemin SVG des modules foncés (1 unité = 1 module), sans marge."""
    qr = segno.make(texte, error="m", micro=False)
    lignes = [list(r) for r in qr.matrix]
    n = len(lignes)
    morceaux = []
    for y, rangee in enumerate(lignes):
        x = 0
        while x < n:
            if rangee[x]:
                debut = x
                while x < n and rangee[x]:
                    x += 1
                morceaux.append(f"M{debut} {y}h{x - debut}v1h{debut - x}z")
            else:
                x += 1
    return "".join(morceaux), n


def _etiquette(o: Dict[str, Any], taille_mm: float, x: float, y: float, texte: bool) -> str:
    chemin, n = _chemin_qr(f"{URL_API}/o/{o['id']}")
    echelle = taille_mm / n
    g = [f'<g transform="translate({x:.3f} {y:.3f})">',
         f'<path transform="scale({echelle:.5f})" d="{chemin}" fill="#000"/>']
    if texte:
        g.append(f'<text x="{taille_mm / 2:.3f}" y="{taille_mm + 3.2:.3f}" font-family="Helvetica, Arial, sans-serif" '
                 f'font-size="2.6" text-anchor="middle" fill="#000">PTM-{o["id"]}</text>')
    g.append("</g>")
    return "".join(g)


def _svg(largeur: float, hauteur: float, corps: str) -> Response:
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{largeur:.2f}mm" height="{hauteur:.2f}mm" '
           f'viewBox="0 0 {largeur:.3f} {hauteur:.3f}">{corps}</svg>')
    return Response(svg, media_type="image/svg+xml")


@router.get("/{oid}/qr.svg")
def qr_svg(oid: int, taille_mm: float = 15, texte: bool = True):
    o = _lire(oid)
    t = max(6.0, min(taille_mm, 80.0))
    return _svg(t, t + (4.5 if texte else 0), _etiquette(o, t, 0, 0, texte))


@router.get("/etiquettes/planche.svg")
def planche(ids: Optional[str] = None, taille_mm: float = 15, texte: bool = True, colonnes: int = 8):
    """Planche de plusieurs étiquettes (une case par outil, nom en commentaire pour s'y retrouver)."""
    if ids:
        liste = [int(i) for i in ids.split(",") if i.strip().isdigit()]
        if not liste:
            raise HTTPException(400, "ids invalides")
        rows = _check(requests.get(_url("outils", f"?id=in.({','.join(map(str, liste))})&select=*&order=id.asc"),
                                   headers=_h(), timeout=15)) or []
    else:
        rows = _check(requests.get(_url("outils", "?actif=eq.true&select=*&order=id.asc"), headers=_h(), timeout=15)) or []
    if not rows:
        raise HTTPException(404, "Aucun outil")
    t = max(6.0, min(taille_mm, 80.0))
    colonnes = max(1, min(colonnes, 20))
    pas_x, pas_y = t + 5, t + (9 if texte else 5)
    corps = []
    for i, o in enumerate(rows):
        cx, cy = 3 + (i % colonnes) * pas_x, 3 + (i // colonnes) * pas_y
        corps.append(f"<!-- PTM-{o['id']} : {escape(o['nom']).replace('--', '-')} -->")
        corps.append(_etiquette(o, t, cx, cy, texte))
    largeur = 6 + min(len(rows), colonnes) * pas_x - 5
    hauteur = 6 + ((len(rows) - 1) // colonnes + 1) * pas_y - (4 if texte else 5)
    return _svg(largeur, hauteur, "".join(corps))


# ─── Adresse courte des étiquettes ──────────────────────────────

@router_court.get("/o/{oid}")
def ouvrir(oid: int):
    """Le QR pointe ici ; on renvoie vers l'appli, sur l'outil. Aucune donnée exposée."""
    return RedirectResponse(f"{URL_APP}?o={oid}", status_code=302)
