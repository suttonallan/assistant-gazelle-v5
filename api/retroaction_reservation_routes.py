"""Commentaires des clients sur la nouvelle réservation en ligne.

Le service de réservation (dépôt privé ptm-reservation) relaie ici, de serveur
à serveur, la note (1 à 5) et le commentaire laissés après une réservation.
L'assistant les envoie par courriel à info@piano-tek.com, donc dans Front.
"""
from __future__ import annotations

import hmac
import html
import logging
import os
import re
import time
from collections import deque
from typing import Optional

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from core.email_notifier import get_email_notifier

router = APIRouter(prefix="/reservation-en-ligne", tags=["reservation-en-ligne"])

DESTINATAIRE = "info@piano-tek.com"
_PLAFOND_HEURE = 30
_recents: deque[float] = deque()


class Retroaction(BaseModel):
    note: int = Field(..., ge=1, le=5)
    commentaire: Optional[str] = Field(None, max_length=2000)
    client: Optional[str] = Field(None, max_length=120)
    courriel: Optional[str] = Field(None, max_length=200)
    rendez_vous: Optional[str] = Field(None, max_length=120)


@router.post("/retroaction")
def recevoir_retroaction(r: Retroaction):
    maintenant = time.time()
    while _recents and maintenant - _recents[0] > 3600:
        _recents.popleft()
    if len(_recents) >= _PLAFOND_HEURE:
        raise HTTPException(429, "Trop de commentaires reçus, réessayez plus tard.")
    _recents.append(maintenant)

    etoiles = "★" * r.note + "☆" * (5 - r.note)
    e = lambda s: html.escape(s or "—")
    corps = (
        f"<p><b>Note :</b> {etoiles} ({r.note}/5)</p>"
        f"<p><b>Client :</b> {e(r.client)} &lt;{e(r.courriel)}&gt;<br>"
        f"<b>Rendez-vous demandé :</b> {e(r.rendez_vous)}</p>"
        f"<p><b>Commentaire :</b><br>{e(r.commentaire).replace(chr(10), '<br>')}</p>"
        "<p style='color:#777'>Envoyé automatiquement par la nouvelle page de réservation en ligne.</p>"
    )
    ok = get_email_notifier().send_email(
        to_emails=[DESTINATAIRE],
        subject=f"Réservation en ligne — commentaire client ({r.note}/5)",
        html_content=corps,
    )
    if not ok:
        raise HTTPException(502, "Envoi impossible pour le moment.")
    return {"ok": True}


# ---------------------------------------------------------------------------
# Client créé (ou retrouvé) AVANT la réservation : si le technicien refuse la
# demande, la fiche et ses informations restent dans Gazelle (contrairement à
# une réservation refusée dans le Self-Scheduler, qui ne laisse rien).
# Appel de serveur à serveur seulement : jeton partagé RESERVATION_SECRET.
# ---------------------------------------------------------------------------
_log = logging.getLogger(__name__)
_appels_client: deque[float] = deque()


# Empreinte SHA-256 du jeton partagé avec le service de réservation (dépôt privé).
# Le dépôt est public : seule l'empreinte est ici, jamais le jeton lui-même.
_EMPREINTE_JETON = os.environ.get("RESERVATION_SECRET_SHA256", "4461ac5784a4515f3a5f32958285117c2ef4d42f29db0db85f9b739003f51be8")


def _verifier_jeton(jeton: Optional[str]) -> None:
    import hashlib
    if not jeton or not hmac.compare_digest(hashlib.sha256(jeton.encode()).hexdigest(), _EMPREINTE_JETON):
        raise HTTPException(403, "Accès refusé")
    maintenant = time.time()
    while _appels_client and maintenant - _appels_client[0] > 3600:
        _appels_client.popleft()
    if len(_appels_client) >= 60:
        raise HTTPException(429, "Trop de demandes")
    _appels_client.append(maintenant)


class ClientReservation(BaseModel):
    prenom: str = Field(..., max_length=80)
    nom: str = Field(..., max_length=80)
    courriel: str = Field(..., max_length=200)
    telephone: str = Field(..., max_length=40)
    rue: str = Field(..., max_length=200)
    ville: str = Field(..., max_length=100)
    province: str = Field("QC", max_length=10)
    code_postal: str = Field(..., max_length=12)
    langue: str = "fr"


def _chiffres(t: str) -> str:
    return re.sub(r"\D", "", t or "")[-10:]


@router.post("/client")
def client_pour_reservation(c: ClientReservation, x_reservation_secret: Optional[str] = Header(None)):
    """Retrouve le client par courriel ou téléphone, sinon le crée (client potentiel)."""
    _verifier_jeton(x_reservation_secret)
    from core.gazelle_api_client import GazelleAPIClient
    gz = GazelleAPIClient()
    q = """query($s: String) { allClients(first: 10, filters: {search: $s}) { nodes { id
      defaultContact { defaultEmail { email } defaultPhone { phoneNumber } } } } }"""
    for terme, egal in ((c.courriel.strip(), lambda n: ((n.get("defaultContact") or {}).get("defaultEmail") or {}).get("email", "").strip().lower() == c.courriel.strip().lower()),
                        (_chiffres(c.telephone), lambda n: _chiffres(((n.get("defaultContact") or {}).get("defaultPhone") or {}).get("phoneNumber", "")) == _chiffres(c.telephone))):
        if not terme or len(terme) < 6:
            continue
        try:
            res = gz._execute_query(q, {"s": terme})
            for n in (((res.get("data") or {}).get("allClients") or {}).get("nodes") or []):
                if egal(n):
                    return {"client_id": n["id"], "existant": True}
        except Exception as e:
            _log.warning("Recherche client (réservation en ligne) : %s", e)
    loc = None
    if c.langue == "en":
        try:
            r = gz._execute_query("{ allLocalizations { id locale } }")
            loc = next((l["id"] for l in (r.get("data") or {}).get("allLocalizations") or []
                        if str(l.get("locale", "")).lower().startswith("en")), None)
        except Exception as e:
            _log.warning("Langues Gazelle : %s", e)
    try:
        cid = gz.create_client(c.prenom, c.nom, telephone=c.telephone, courriel=c.courriel,
                               adresse={"rue": c.rue, "ville": c.ville, "province": c.province,
                                        "code_postal": c.code_postal},
                               reference="Réservation en ligne (reserver.pianotechniquemontreal.com)",
                               localization_id=loc)
    except Exception as e:
        raise HTTPException(502, f"Création du client impossible : {e}")
    return {"client_id": cid, "existant": False}


class NoteReservation(BaseModel):
    client_id: str = Field(..., pattern=r"^cli_[A-Za-z0-9]{6,40}$")
    texte: str = Field(..., max_length=3000)


@router.post("/journal")
def note_reservation(n: NoteReservation, x_reservation_secret: Optional[str] = Header(None)):
    """Note dans la chronologie du client : la demande reste visible même si elle est refusée."""
    _verifier_jeton(x_reservation_secret)
    from core.gazelle_api_client import GazelleAPIClient
    try:
        GazelleAPIClient().create_client_log(n.client_id, n.texte)
    except Exception as e:
        raise HTTPException(502, f"Note impossible : {e}")
    return {"ok": True}
