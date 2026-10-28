"""Outils serveur à serveur pour gérer un rendez-vous client depuis Claude
(ex. : un client demande de déplacer son RV → on l'annule et on lui propose
des plages équivalentes).

Protégé par le même jeton que la réservation en ligne (X-Reservation-Secret) ;
le dépôt public ne contient que l'empreinte du jeton.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

import httpx
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from api.retroaction_reservation_routes import _verifier_jeton

router = APIRouter(prefix="/reservation-en-ligne/outils", tags=["outils-rv"])

RESERVATION_URL = "https://reserver.pianotechniquemontreal.com"


def _gz():
    from core.gazelle_api_client import GazelleAPIClient
    return GazelleAPIClient()


class TypeSchema(BaseModel):
    type_name: Optional[str] = Field(None, max_length=80)
    motif_mutation: Optional[str] = Field(None, max_length=40)


@router.post("/schema")
def schema(t: TypeSchema, x_reservation_secret: Optional[str] = Header(None)):
    """Lecture seule : champs d'un type Gazelle, ou mutations dont le nom contient un motif."""
    _verifier_jeton(x_reservation_secret)
    gz = _gz()
    out = {}
    if t.type_name:
        q = """query($n: String!) { __type(name: $n) { name kind
          fields { name args { name type { name kind ofType { name kind } } } type { name kind ofType { name kind ofType { name } } } }
          inputFields { name type { name kind ofType { name kind } } }
          enumValues { name } } }"""
        out["type"] = (gz._execute_query(q, {"n": t.type_name}).get("data") or {}).get("__type")
    if t.motif_mutation:
        q = """{ __schema { mutationType { fields { name
          args { name type { name kind ofType { name kind ofType { name } } } } } } } }"""
        champs = ((gz._execute_query(q).get("data") or {}).get("__schema") or {}).get("mutationType", {}).get("fields") or []
        out["mutations"] = [f for f in champs if t.motif_mutation.lower() in f["name"].lower()]
    return out


class RvClient(BaseModel):
    client_id: str = Field(..., pattern=r"^cli_[A-Za-z0-9]{6,40}$")
    jours: int = Field(60, ge=1, le=180)


@router.post("/rv-client")
def rv_client(c: RvClient, x_reservation_secret: Optional[str] = Header(None)):
    """Rendez-vous à venir d'un client (id, date, durée, technicien, adresse, pianos)."""
    _verifier_jeton(x_reservation_secret)
    gz = _gz()
    q = """query($after: String, $filters: PrivateAllEventsFilter) {
      allEventsBatched(first: 100, after: $after, filters: $filters) {
        nodes { id title start duration status type notes confirmedByClient
          client { id } user { id firstName lastName }
          location { singleLineAddress }
          allEventPianos(first: 10) { nodes { piano { id make model type } } } }
        pageInfo { hasNextPage endCursor } } }"""
    debut = datetime.now().strftime("%Y-%m-%d")
    fin = (datetime.now() + timedelta(days=c.jours)).strftime("%Y-%m-%d")
    filtres = {"startOn": debut, "endOn": fin, "type": ["APPOINTMENT"]}
    trouves, apres = [], None
    for _ in range(30):
        res = gz._execute_query(q, {"after": apres, "filters": filtres})
        if res.get("errors"):
            raise HTTPException(502, str(res["errors"])[:500])
        conn = (res.get("data") or {}).get("allEventsBatched") or {}
        trouves += [n for n in conn.get("nodes") or [] if (n.get("client") or {}).get("id") == c.client_id]
        if not (conn.get("pageInfo") or {}).get("hasNextPage"):
            break
        apres = conn["pageInfo"]["endCursor"]
    return {"rendez_vous": trouves}


class Annulation(BaseModel):
    event_id: str = Field(..., pattern=r"^evt_[A-Za-z0-9]{6,40}$")
    client_id: str = Field(..., pattern=r"^cli_[A-Za-z0-9]{6,40}$")
    note: Optional[str] = Field(None, max_length=1000)


@router.post("/annuler-rv")
def annuler_rv(a: Annulation, x_reservation_secret: Optional[str] = Header(None)):
    """Annule (sans supprimer) un rendez-vous du client : il reste une trace dans sa chronologie."""
    _verifier_jeton(x_reservation_secret)
    gz = _gz()
    ev = gz._execute_query("query($id: String!) { event(id: $id) { id status client { id } } }", {"id": a.event_id})
    e = (ev.get("data") or {}).get("event")
    if not e or (e.get("client") or {}).get("id") != a.client_id:
        raise HTTPException(404, "Rendez-vous introuvable pour ce client")
    res = gz._execute_query(
        "mutation($id: String!) { cancelEvent(eventId: $id) { event { id status } mutationErrors { fieldName messages } } }",
        {"id": a.event_id})
    if res.get("errors"):
        raise HTTPException(502, str(res["errors"])[:800])
    sortie = (res.get("data") or {}).get("cancelEvent") or {}
    if sortie.get("mutationErrors"):
        raise HTTPException(502, str(sortie["mutationErrors"])[:800])
    if a.note:
        try:
            gz.create_client_log(a.client_id, a.note)
        except Exception:
            pass
    return sortie


class Recherche(BaseModel):
    adresse: str = Field(..., min_length=5, max_length=300)
    date_visee: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    services: list[str] = Field(..., min_length=1, max_length=10)
    client_id: Optional[str] = None


@router.post("/disponibilites")
def disponibilites(r: Recherche, x_reservation_secret: Optional[str] = Header(None)):
    """Plages libres selon les règles de la réservation en ligne (relais vers reserver.pianotechniquemontreal.com)."""
    _verifier_jeton(x_reservation_secret)
    try:
        res = httpx.post(f"{RESERVATION_URL}/disponibilites", json=r.model_dump(), timeout=90)
        return {"code": res.status_code, "reponse": res.json()}
    except (httpx.HTTPError, ValueError) as e:
        raise HTTPException(502, str(e))


@router.post("/services")
def services(x_reservation_secret: Optional[str] = Header(None)):
    _verifier_jeton(x_reservation_secret)
    try:
        return httpx.get(f"{RESERVATION_URL}/services", timeout=30).json()
    except (httpx.HTTPError, ValueError) as e:
        raise HTTPException(502, str(e))
