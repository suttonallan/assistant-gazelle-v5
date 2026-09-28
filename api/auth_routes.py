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


@router.get("/journal")
def journal(request: Request):
    """Appels reçus sans jeton depuis le dernier démarrage (mode observation)."""
    if _qui(request) != "allan":
        raise HTTPException(403, "Réservé à Allan")
    from core.feature_flags import is_enabled
    return {"verrou_actif": is_enabled("api_verrou", default=False), "sans_jeton": verrou_api.journal()}
