#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Rappel « préférence de diapason 440/442 » envoyé SIX JOURS avant chaque accord
à Orford.

Contexte (2026-07-31, demandé par Allan) : en période chaude (canicule), les pianos
d'Orford dérivent naturellement vers 442 Hz même s'ils sont habituellement accordés
à 440. Avant chaque accord, il faut demander à l'artiste sa préférence : faut-il
absolument revenir à 440, ou est-ce que 442 convient ? Descendre un piano chaud de
442 à 440 est un travail supplémentaire qui ne tient pas forcément — d'où l'intérêt
de valider la préférence AVANT le rendez-vous.

Déclencheur : TOUS les accords Orford (pas seulement les concerts), six jours avant.
Un accord = un RV actif chez Orford qui touche au moins un piano. On envoie un seul
courriel récapitulatif à info@ (visibilité centrale + coordination Telya) et au(x)
technicien(s) assigné(s).

Pas de table de déduplication : la cible est exactement J+6 et le job tourne une fois
par jour, donc chaque RV n'est notifié qu'une seule fois (comme le rappel d'accès PdA
la veille). Un RV déplacé sera re-notifié pour sa nouvelle date — comportement voulu.

Désactivation : poser la clé system_settings 'orford_pitch_reminder_enabled' à 'false'
(aucun redéploiement).
"""
from datetime import datetime, timedelta

import requests

from core.supabase_storage import SupabaseStorage
from core.email_notifier import EmailNotifier
from core.timezone_utils import MONTREAL_TZ

ORFORD_CLIENT = 'cli_PmqPUBTbPFeCMGmz'
LEAD_DAYS = 6
INFO_EMAIL = 'info@piano-tek.com'

PITCH_BLOCK = (
    "Rappel diapason Orford (440 vs 442) :\n"
    "- En période chaude, les pianos d'Orford dérivent vers 442 Hz même s'ils sont "
    "habituellement accordés à 440.\n"
    "- Avant l'accord, demander à l'artiste sa préférence : faut-il absolument revenir "
    "à 440, ou est-ce que 442 convient ?\n"
    "- Descendre un piano chaud de 442 à 440 est un travail supplémentaire qui ne tient "
    "pas forcément : mieux vaut valider la préférence avant le rendez-vous."
)


def is_enabled(storage) -> bool:
    """Activé par défaut ; désactivable via system_settings sans redéploiement."""
    try:
        r = requests.get(
            f"{storage.api_url}/system_settings?key=eq.orford_pitch_reminder_enabled&select=value",
            headers=storage._get_headers(), timeout=10)
        if r.status_code == 200 and r.json():
            return str(r.json()[0].get('value')).strip().lower() not in ('false', '0', 'off', 'no')
    except Exception:
        pass
    return True


def _piano_label(piano: dict) -> str:
    """Étiquette lisible d'un piano : make/model, sinon local."""
    piano = piano or {}
    ident = f"{(piano.get('make') or '').strip()} {(piano.get('model') or '').strip()}".strip()
    return ident or (piano.get('location') or 'piano')


def run_orford_pitch_reminder(dry_run: bool = False) -> dict:
    """Envoie le rappel diapason 440/442 pour les accords Orford dans six jours.

    dry_run=True : compose et affiche le courriel sans l'envoyer.
    """
    storage = SupabaseStorage(silent=True)
    if not is_enabled(storage):
        print("Rappel diapason Orford : désactivé (system_settings)")
        return {"enabled": False, "sent": 0}

    from core.gazelle_api_client import GazelleAPIClient
    gz = GazelleAPIClient()
    target = (datetime.now(MONTREAL_TZ).date() + timedelta(days=LEAD_DAYS)).isoformat()

    q = ('query($f: PrivateAllEventsFilter){ allEventsBatched(first:100, filters:$f){ '
         'nodes{ id title notes status start user{ id } '
         'allEventPianos(first:20){ nodes{ piano{ make model location } } } } } }')
    try:
        res = gz._execute_query(q, {'f': {'clientId': ORFORD_CLIENT, 'dateGet': target, 'dateLet': target}})
    except Exception as exc:
        print(f"Rappel diapason Orford : requête échouée : {exc}")
        return {"sent": 0, "error": str(exc)}
    nodes = ((res.get('data') or {}).get('allEventsBatched') or {}).get('nodes') or []

    # Un accord = RV actif touchant au moins un piano (exclut les événements admin).
    accords = []
    for nd in nodes:
        if (nd.get('status') or '').upper() != 'ACTIVE':
            continue
        pianos = (nd.get('allEventPianos') or {}).get('nodes') or []
        if not pianos:
            continue
        accords.append(nd)

    if not accords:
        print(f"Rappel diapason Orford : aucun accord le {target}")
        return {"date": target, "sent": 0, "accords": 0}

    # Destinataires : info@ + technicien(s) assigné(s), dédupliqués.
    try:
        from config.techniciens_config import get_technicien_by_id
    except Exception:
        get_technicien_by_id = lambda _x: None

    recipients = [INFO_EMAIL]
    for nd in accords:
        tech_id = (nd.get('user') or {}).get('id')
        tech = get_technicien_by_id(tech_id) if tech_id else None
        if tech and tech.get('email') and tech['email'] not in recipients:
            recipients.append(tech['email'])

    # Corps : liste des accords du jour cible.
    lignes = []
    for nd in accords:
        heure = ''
        if nd.get('start'):
            try:
                dt = datetime.fromisoformat(str(nd['start']).replace('Z', '+00:00')).astimezone(MONTREAL_TZ)
                heure = dt.strftime('%H:%M')
            except Exception:
                pass
        titre = nd.get('title') or 'Accord Orford'
        pianos = (nd.get('allEventPianos') or {}).get('nodes') or []
        piano_txt = ', '.join(_piano_label(p.get('piano')) for p in pianos) or '—'
        heure_txt = f" à {heure}" if heure else ""
        lignes.append(f"- {titre}{heure_txt} : {piano_txt}")

    liste = "\n".join(lignes)
    plain = (
        f"Bonjour,\n\n"
        f"Dans six jours (le {target}), il y a {len(accords)} accord(s) prévu(s) à Orford :\n"
        f"{liste}\n\n"
        f"{PITCH_BLOCK}\n\n"
        f"Cordialement,\n"
        f"Assistant Gazelle"
    )
    subject = f"Rappel diapason Orford (440/442) — {len(accords)} accord(s) le {target}"

    if dry_run:
        print("=" * 70)
        print("APERÇU (dry-run) — rien envoyé")
        print(f"Destinataires : {recipients}")
        print(f"Sujet : {subject}")
        print("-" * 70)
        print(plain)
        print("=" * 70)
        return {"date": target, "accords": len(accords), "sent": 0, "dry_run": True,
                "recipients": recipients}

    notifier = EmailNotifier()
    ok = notifier.send_email(
        to_emails=recipients,
        subject=subject,
        html_content=plain.replace('\n', '<br>'),
        plain_content=plain,
    )
    sent = 1 if ok else 0
    print(f"Rappel diapason Orford : {'envoyé' if ok else 'échec'} pour le {target} "
          f"({len(accords)} accord(s), destinataires : {recipients})")
    return {"date": target, "accords": len(accords), "sent": sent, "recipients": recipients}


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="Aperçu sans envoi")
    args = ap.parse_args()
    return run_orford_pitch_reminder(dry_run=args.dry_run)


if __name__ == '__main__':
    main()
