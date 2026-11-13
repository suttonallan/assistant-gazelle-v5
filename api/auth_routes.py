"""Connexion par PIN vérifiée côté serveur (voir core/verrou_api.py)."""
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from core import verrou_api

router = APIRouter(prefix="/auth", tags=["auth"])


class ConnexionIn(BaseModel):
    pin: str = Field(..., min_length=4, max_length=8)


class ChangerPinIn(BaseModel):
    nouveau_pin: str = Field(..., min_length=4, max_length=8)


def _ip(request: Request) -> str:
    return (request.headers.get("x-forwarded-for") or (request.client.host if request.client else "?")).split(",")[0].strip()


@router.post("/connexion")
def connexion(c: ConnexionIn, request: Request):
    try:
        res = verrou_api.connexion(c.pin, _ip(request))
    except PermissionError as e:
        raise HTTPException(429, str(e))
    if not res:
        raise HTTPException(401, "PIN incorrect")
    return res


def _qui(request: Request) -> str:
    auth = request.headers.get("authorization", "")
    donnees = verrou_api.verifier_jeton(auth[7:]) if auth.lower().startswith("bearer ") else None
    if not donnees:
        raise HTTPException(401, "Connexion requise")
    return donnees["qui"]


@router.get("/moi")
def moi(request: Request):
    return {"qui": _qui(request)}


@router.post("/changer-pin")
def changer_pin(c: ChangerPinIn, request: Request):
    try:
        verrou_api.changer_pin(_qui(request), c.nouveau_pin)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"ok": True}


def _allan_ou_claude(request: Request) -> str:
    """Allan (jeton de personne) ou Claude (sa clé réservée)."""
    if verrou_api.est_cle_claude(request.headers.get("x-cle-service")):
        return "claude"
    if _qui(request) != "allan":
        raise HTTPException(403, "Réservé à Allan")
    return "allan"


@router.post("/verrou")
def basculer_verrou(request: Request, actif: bool):
    """Active (ou désactive, en cas de pépin) le verrou : sans jeton ni clé, l'API répond 401.
    Réservé à Allan ou à Claude."""
    qui = _allan_ou_claude(request)
    verrou_api._storage().save_system_setting("flag_api_verrou", "true" if actif else "false")
    from core import feature_flags
    feature_flags._cache_time = 0  # relire tout de suite
    return {"verrou_actif": feature_flags.is_enabled("api_verrou", default=False), "par": qui}


@router.get("/journal")
def journal(request: Request):
    """Appels reçus sans jeton valide (mode observation), cumulés même après un redémarrage."""
    _allan_ou_claude(request)
    from core.feature_flags import is_enabled
    routes = verrou_api.journal()
    return {"verrou_actif": is_enabled("api_verrou", default=False),
            "depuis": verrou_api._journal_etat.get("depuis"), "sans_jeton": routes,
            "cle_claude_derniere_utilisation": verrou_api.DERNIER_USAGE_CLE_CLAUDE}



@router.get("/activite")
def activite(request: Request):
    """Qui utilise l'app, et comment (Google ou PIN). Réservé à Allan."""
    if _qui(request) != "allan":
        raise HTTPException(403, "Réservé à Allan")
    return {"activite": verrou_api.activite_equipe()}


class GoogleIn(BaseModel):
    credential: str = Field(..., min_length=20)


@router.get("/config")
def config():
    """Public : identifiant de l'app Google (vide = connexion Google pas encore active)."""
    return {"google_client_id": verrou_api.google_client_id()}


@router.post("/google")
def connexion_google(g: GoogleIn):
    try:
        res = verrou_api.connexion_google(g.credential)
    except PermissionError as e:
        raise HTTPException(403, str(e))
    if not res:
        raise HTTPException(401, "Connexion Google refusée")
    return res
