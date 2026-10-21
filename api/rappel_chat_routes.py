"""Demandes de rappel faites dans le chat public « Premier avis sur votre piano ».

Le serveur du chat (ptm-chat-api) relaie ici, de serveur à serveur, la demande
d'un client qui veut être rappelé : prénom, téléphone, meilleur moment et résumé
de la conversation. L'assistant l'envoie par courriel à info@piano-tek.com,
donc dans Front, où la coordonnatrice la traite.
"""
from __future__ import annotations

import hashlib
import hmac
import html
import os
import re
import time
from collections import deque
from typing import List, Optional

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from core.email_notifier import get_email_notifier

router = APIRouter(prefix="/chat-public", tags=["chat-public"])

DESTINATAIRE = "info@piano-tek.com"

# Empreinte SHA-256 du jeton partagé avec le serveur du chat.
# Le dépôt est public : seule l'empreinte est ici, jamais le jeton lui-même.
_EMPREINTE_JETON = os.environ.get(
    "CHAT_RELAY_SECRET_SHA256",
    "ec5625bdc4c09eabc93603ba7ceee961eed39f04b273192d6ffbcb9c8acc40c2",
)
_PLAFOND_HEURE = 20
_recents: deque[float] = deque()


def _verifier_jeton(jeton: Optional[str]) -> None:
    if not jeton or not hmac.compare_digest(hashlib.sha256(jeton.encode()).hexdigest(), _EMPREINTE_JETON):
        raise HTTPException(403, "Accès refusé")
    maintenant = time.time()
    while _recents and maintenant - _recents[0] > 3600:
        _recents.popleft()
    if len(_recents) >= _PLAFOND_HEURE:
        raise HTTPException(429, "Trop de demandes")
    _recents.append(maintenant)


class Echange(BaseModel):
    role: str = Field(..., max_length=20)
    texte: str = Field(..., max_length=3000)


class DemandeRappel(BaseModel):
    prenom: str = Field(..., min_length=1, max_length=80)
    telephone: str = Field(..., min_length=7, max_length=40)
    moment: Optional[str] = Field(None, max_length=200)
    langue: str = Field("fr", max_length=5)
    conversation: List[Echange] = Field(default_factory=list, max_length=30)


@router.post("/rappel")
def demande_rappel(d: DemandeRappel, x_chat_secret: Optional[str] = Header(None)):
    _verifier_jeton(x_chat_secret)
    chiffres = re.sub(r"\D", "", d.telephone)
    if len(chiffres) < 10:
        raise HTTPException(422, "Numéro de téléphone incomplet")

    e = lambda s: html.escape(s or "—")
    lignes = "".join(
        f"<p style='margin:4px 0'><b>{'Client' if x.role == 'user' else 'Chat'} :</b> "
        f"{e(x.texte).replace(chr(10), '<br>')}</p>"
        for x in d.conversation[-12:]
    )
    corps = (
        f"<p><b>À rappeler :</b> {e(d.prenom)} — <a href='tel:+1{chiffres[-10:]}'>{e(d.telephone)}</a><br>"
        f"<b>Meilleur moment :</b> {e(d.moment)}<br>"
        f"<b>Langue :</b> {'anglais' if d.langue == 'en' else 'français'}</p>"
        "<p>Le client a demandé dans le chat du site qu'on le rappelle. "
        "On lui a dit que l'équipe le rappellerait d'ici deux jours ouvrables.</p>"
        f"<hr><p><b>Conversation :</b></p>{lignes}"
        "<p style='color:#777'>Envoyé automatiquement par le chat « Premier avis sur votre piano ».</p>"
    )
    ok = get_email_notifier().send_email(
        to_emails=[DESTINATAIRE],
        subject=f"Chat — à rappeler : {d.prenom} ({d.telephone})",
        html_content=corps,
    )
    if not ok:
        raise HTTPException(502, "Envoi impossible pour le moment.")
    return {"ok": True}
