"""Commentaires des clients sur la nouvelle réservation en ligne.

Le service de réservation (dépôt privé ptm-reservation) relaie ici, de serveur
à serveur, la note (1 à 5) et le commentaire laissés après une réservation.
L'assistant les envoie par courriel à info@piano-tek.com, donc dans Front.
"""
from __future__ import annotations

import html
import time
from collections import deque
from typing import Optional

from fastapi import APIRouter, HTTPException
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
