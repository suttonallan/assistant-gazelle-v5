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


# ---------------------------------------------------------------------------
# Demande hors zone (plus de 45 km du métro Outremont) : pas de plage en ligne,
# la coordonnatrice fixe le rendez-vous. Le service de réservation relaie la
# demande ici. Elle devient une TÂCHE assignée à Louise (volet Tâches : elle ne
# peut pas être oubliée) et part aussi par courriel à info@ (Front). La demande
# est acceptée dès que l'un des deux réussit.
# ---------------------------------------------------------------------------
class DemandeHorsZone(BaseModel):
    prenom: str = Field(..., max_length=80)
    nom: str = Field(..., max_length=80)
    courriel: str = Field(..., max_length=200)
    telephone: str = Field(..., max_length=40)
    adresse: str = Field(..., max_length=300)
    distance_km: Optional[float] = None
    frais_estimes: Optional[float] = None
    service: Optional[str] = Field(None, max_length=200)
    piano: Optional[str] = Field(None, max_length=300)
    preferences: Optional[str] = Field(None, max_length=1000)
    indisponibilites: Optional[str] = Field(None, max_length=1000)
    notes: Optional[str] = Field(None, max_length=2000)
    client_id: Optional[str] = Field(None, max_length=60)
    langue: str = "fr"


@router.post("/demande-hors-zone")
def demande_hors_zone(d: DemandeHorsZone, x_reservation_secret: Optional[str] = Header(None)):
    _verifier_jeton(x_reservation_secret)
    e = lambda s: html.escape(str(s) if s not in (None, "") else "—")
    tel = re.sub(r"\D", "", d.telephone)[-10:]
    corps = (
        "<p><b>Demande de rendez-vous hors zone à fixer</b> (plus de 45 km du métro Outremont).</p>"
        f"<p><b>Client :</b> {e(d.prenom)} {e(d.nom)} — <a href='tel:+1{tel}'>{e(d.telephone)}</a> — {e(d.courriel)}<br>"
        f"<b>Adresse du piano :</b> {e(d.adresse)}<br>"
        f"<b>Distance :</b> {e(round(d.distance_km) if d.distance_km else None)} km (aller) — "
        f"<b>frais de déplacement estimés affichés au client :</b> {e(round(d.frais_estimes) if d.frais_estimes else None)} $ + taxes<br>"
        f"<b>Service :</b> {e(d.service)}<br><b>Piano :</b> {e(d.piano)}<br>"
        f"<b>Langue :</b> {'anglais' if d.langue == 'en' else 'français'}</p>"
        f"<p><b>Préférences (jours et moments) :</b><br>{e(d.preferences)}</p>"
        f"<p><b>Indisponibilités :</b><br>{e(d.indisponibilites).replace(chr(10), '<br>')}</p>"
        f"<p><b>Note du client :</b><br>{e(d.notes).replace(chr(10), '<br>')}</p>"
        f"<p>Fiche Gazelle : {e(d.client_id)}</p>"
        "<p>On a dit au client que l'équipe le contacterait d'ici deux jours ouvrables pour fixer le rendez-vous.</p>"
        "<p style='color:#777'>Envoyé automatiquement par la page de réservation en ligne.</p>"
    )
    tache_ok = _tache_hors_zone(d)
    try:
        courriel_ok = get_email_notifier().send_email(
            to_emails=[DESTINATAIRE],
            subject=f"Réservation hors zone — à fixer : {d.prenom} {d.nom} ({d.adresse[:60]})",
            html_content=corps + ("" if tache_ok else
                                  "<p><b>⚠️ La tâche n'a pas pu être créée dans le volet Tâches : à ajouter à la main.</b></p>"),
        )
    except Exception as ex:  # noqa: BLE001
        logging.getLogger(__name__).error("Courriel hors zone : %s", ex)
        courriel_ok = False
    if not (tache_ok or courriel_ok):
        raise HTTPException(502, "Envoi impossible pour le moment.")
    return {"ok": True, "tache": tache_ok, "courriel": courriel_ok}


def _echeance_ouvrable(jours: int = 2) -> str:
    """Date AAAA-MM-JJ à N jours ouvrables (heure de Montréal) : ce qu'on promet au client."""
    from datetime import timedelta
    from core.timezone_utils import aujourdhui_montreal
    d = aujourdhui_montreal()
    restant = jours
    while restant:
        d += timedelta(days=1)
        if d.weekday() < 5:
            restant -= 1
    return d.isoformat()


def _tache_hors_zone(d: "DemandeHorsZone") -> bool:
    """Tâche « RV hors zone à fixer » pour Louise, échéance à deux jours ouvrables."""
    import requests
    from api.taches_routes import _db, _url
    km = f"{round(d.distance_km)} km" if d.distance_km else "distance inconnue"
    frais = f"{round(d.frais_estimes)} $ + taxes" if d.frais_estimes else "à calculer"
    lignes = [
        f"Client : {d.prenom} {d.nom} — {d.telephone} — {d.courriel}",
        f"Adresse : {d.adresse} ({km} du métro Outremont)",
        f"Frais de déplacement estimés affichés au client : {frais}",
        f"Service : {d.service or '—'}",
        f"Piano : {d.piano or '—'}",
        f"Préférences : {d.preferences or '—'}",
        f"Indisponibilités : {d.indisponibilites or '—'}",
        f"Note du client : {d.notes or '—'}",
        f"Langue : {'anglais' if d.langue == 'en' else 'français'}",
        f"Fiche Gazelle : {d.client_id or '—'}",
        "Promis au client : un appel d'ici deux jours ouvrables pour fixer le rendez-vous.",
    ]
    ville = d.adresse.split(",")[1].strip() if "," in d.adresse else d.adresse[:40]
    data = {
        "titre": f"RV hors zone à fixer : {d.prenom} {d.nom} ({ville})",
        "contexte": "\n".join(lignes),
        "statut": "a_faire",
        "assigne": "louise",
        "echeance": _echeance_ouvrable(2),
        "source": "reservation-en-ligne",
        "cree_par": "reservation-en-ligne",
        "client": "prive",
        "etapes": [{"texte": "Appeler le client et fixer le RV", "fait": False},
                   {"texte": "Créer le RV dans Gazelle (frais de déplacement inclus)", "fait": False}],
    }
    try:
        r = requests.post(_url(), headers=_db()._get_headers(), json=data, timeout=15)
        if r.status_code >= 400:
            logging.getLogger(__name__).error("Tâche hors zone refusée : %s %s", r.status_code, r.text[:300])
            return False
        return True
    except Exception as ex:  # noqa: BLE001
        logging.getLogger(__name__).error("Tâche hors zone : %s", ex)
        return False


# ---------------------------------------------------------------------------
# Journal des événements de la page (étapes anonymes, réservations, abandons…)
# conservé dans Supabase : survit aux redémarrages du service de réservation.
# Bilan quotidien : modules/alerts/bilan_reservation_en_ligne.py.
# Plafond séparé de _verifier_jeton : un afflux d'étapes ne doit jamais bloquer
# la création des fiches clients.
# ---------------------------------------------------------------------------
# Plafonds séparés : un afflux d'étapes (anonymes, publiques) ne peut pas
# empêcher l'enregistrement des vraies demandes et abandons.
_appels_evenements: dict[str, deque] = {"etape": deque(), "autre": deque()}
_PLAFONDS_EVENEMENTS = {"etape": 2000, "autre": 300}
_TYPES_EVENEMENTS = {"etape", "reservation", "abandon", "hors_zone", "refus"}


class EvenementReservation(BaseModel):
    type: str = Field(..., max_length=20)
    cle: Optional[str] = Field(None, max_length=60)
    client_id: Optional[str] = Field(None, max_length=60)
    details: dict = Field(default_factory=dict)


@router.post("/evenement")
def evenement_reservation(ev: EvenementReservation, x_reservation_secret: Optional[str] = Header(None)):
    import hashlib
    import json
    if not x_reservation_secret or not hmac.compare_digest(
            hashlib.sha256(x_reservation_secret.encode()).hexdigest(), _EMPREINTE_JETON):
        raise HTTPException(403, "Accès refusé")
    if ev.type not in _TYPES_EVENEMENTS:
        raise HTTPException(422, "Type inconnu")
    if len(json.dumps(ev.details, default=str)) > 2000:
        raise HTTPException(422, "Détails trop longs")
    maintenant = time.time()
    groupe = "etape" if ev.type == "etape" else "autre"
    file = _appels_evenements[groupe]
    while file and maintenant - file[0] > 3600:
        file.popleft()
    if len(file) >= _PLAFONDS_EVENEMENTS[groupe]:
        raise HTTPException(429, "Trop d'événements")
    file.append(maintenant)
    from datetime import datetime
    from core.supabase_storage import SupabaseStorage
    from core.timezone_utils import MONTREAL_TZ
    try:
        SupabaseStorage(silent=True).client.table("reservation_en_ligne_evenements").insert({
            "jour": datetime.now(MONTREAL_TZ).date().isoformat(),
            "type": ev.type, "cle": ev.cle, "client_id": ev.client_id, "details": ev.details,
        }).execute()
    except Exception as e:
        _log.warning("Événement réservation en ligne non enregistré : %s", e)
        raise HTTPException(502, "Enregistrement impossible")
    return {"ok": True}
