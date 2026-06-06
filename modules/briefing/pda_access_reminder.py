#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Rappel d'accès Place des Arts envoyé LA VEILLE des RV au Théâtre Maisonneuve
et au Théâtre Jean-Duceppe.

Contexte (juin 2026) : l'entrée des artistes du 1400 est fermée pour travaux.
Les équipes doivent passer par l'entrée de la sécurité principale ; un agent
accueille sur place. Tant que les travaux durent, on prévient le technicien la
veille de chaque RV dans ces deux salles précises.

Détection de la salle : un RV PdA ne porte pas la salle dans un champ dédié.
On la repère de deux façons combinées :
  - le nom de la salle (« Maisonneuve » / « Duceppe ») dans le titre ou les notes ;
  - le local du/des piano(s) rattaché(s) au RV.
Le Jean-Duceppe n'a pas de piano dans l'inventaire, mais son nom apparaît dans
les notes du RV — d'où la détection par texte aussi.

Désactivation (quand les travaux du 1400 sont finis) : poser la clé
system_settings 'pda_access_reminder_enabled' à 'false' (aucun redéploiement).
"""
from datetime import datetime, timedelta

import requests

from core.supabase_storage import SupabaseStorage
from core.email_notifier import EmailNotifier
from core.timezone_utils import MONTREAL_TZ
from config.techniciens_config import get_technicien_by_id, GAZELLE_IDS

PDA_CLIENT = 'cli_HbEwl9rN11pSuDEU'
SALLE_KEYWORDS = ('maisonneuve', 'duceppe')

ACCESS_BLOCK = (
    "Accès Place des Arts — travaux en cours :\n"
    "- L'entrée des artistes du 1400 est FERMÉE (travaux en cours).\n"
    "- Utilisez l'entrée de la sécurité principale de la PdA (entrée des artistes "
    "pour le Théâtre Maisonneuve et le Théâtre Jean-Duceppe).\n"
    "- Un agent accueille et dirige les équipes sur place."
)


def _enabled(storage) -> bool:
    """Activé par défaut ; désactivable via system_settings sans redéploiement."""
    try:
        r = requests.get(
            f"{storage.api_url}/system_settings?key=eq.pda_access_reminder_enabled&select=value",
            headers=storage._get_headers(), timeout=10)
        if r.status_code == 200 and r.json():
            return str(r.json()[0].get('value')).strip().lower() not in ('false', '0', 'off', 'no')
    except Exception:
        pass
    return True


def run_pda_access_reminder() -> dict:
    """Envoie le rappel d'accès aux techniciens ayant un RV TM/JD demain."""
    storage = SupabaseStorage(silent=True)
    if not _enabled(storage):
        print("Rappel accès PdA : désactivé (system_settings)")
        return {"enabled": False, "sent": 0}

    from core.gazelle_api_client import GazelleAPIClient
    gz = GazelleAPIClient()
    tomorrow = (datetime.now(MONTREAL_TZ).date() + timedelta(days=1)).isoformat()

    q = ('query($f: PrivateAllEventsFilter){ allEventsBatched(first:50, filters:$f){ '
         'nodes{ id title notes status start user{ id } '
         'allEventPianos(first:10){ nodes{ piano{ location } } } } } }')
    try:
        res = gz._execute_query(q, {'f': {'clientId': PDA_CLIENT, 'dateGet': tomorrow, 'dateLet': tomorrow}})
    except Exception as exc:
        print(f"Rappel accès PdA : requête échouée : {exc}")
        return {"sent": 0, "error": str(exc)}
    nodes = ((res.get('data') or {}).get('allEventsBatched') or {}).get('nodes') or []

    notifier = EmailNotifier()
    sent = 0
    for nd in nodes:
        if (nd.get('status') or '').upper() != 'ACTIVE':
            continue
        piano_locs = ' '.join(
            ((p.get('piano') or {}).get('location') or '')
            for p in ((nd.get('allEventPianos') or {}).get('nodes') or []))
        text = f"{nd.get('title') or ''} {nd.get('notes') or ''} {piano_locs}".lower()
        if not any(k in text for k in SALLE_KEYWORDS):
            continue

        tech_id = (nd.get('user') or {}).get('id')
        if tech_id not in GAZELLE_IDS:
            continue
        tech = get_technicien_by_id(tech_id)
        if not tech or not tech.get('email'):
            continue

        heure = ''
        if nd.get('start'):
            try:
                dt = datetime.fromisoformat(str(nd['start']).replace('Z', '+00:00')).astimezone(MONTREAL_TZ)
                heure = dt.strftime('%H:%M')
            except Exception:
                pass
        has_m, has_d = 'maisonneuve' in text, 'duceppe' in text
        if has_m and has_d:
            salle = "Théâtre Maisonneuve / Jean-Duceppe"
        elif has_m:
            salle = "Théâtre Maisonneuve"
        else:
            salle = "Théâtre Jean-Duceppe"
        time_txt = f" à {heure}" if heure else ""
        plain = (
            f"Bonjour {tech['prenom']},\n\n"
            f"Tu as un rendez-vous demain le {tomorrow}{time_txt} à la Place des Arts "
            f"({salle}).\n\n"
            f"{ACCESS_BLOCK}\n\n"
            f"Cordialement,\n"
            f"Assistant Gazelle"
        )
        ok = notifier.send_email(
            to_emails=[tech['email']],
            subject="Rappel — accès Place des Arts (1400 fermé), RV demain",
            html_content=plain.replace('\n', '<br>'),
            plain_content=plain,
        )
        if ok:
            sent += 1
            print(f"  Rappel accès PdA -> {tech['email']} ({salle}, {tomorrow})")

    print(f"Rappel accès PdA : {sent} email(s) pour le {tomorrow}")
    return {"date": tomorrow, "sent": sent}


def main():
    return run_pda_access_reminder()


if __name__ == '__main__':
    main()
