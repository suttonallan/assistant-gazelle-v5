#!/usr/bin/env python3
"""Briefing quotidien par technicien — version nuage (pilote transferabilite).

Migration de C:\\Allan Python projets\\Gazelle import v2\\send_briefing_allan.py
(qui lisait le SQL Server local PIANOTEK\\SQLEXPRESS via pyodbc et postait sur
Slack). Cette version lit Supabase (gazelle_appointments + gazelle_clients) et
poste le meme briefing Slack, mais tourne dans le nuage via GitHub Actions.

Objectif pilote : prouver le mecanisme cron-nuage sans deranger l'equipe. Par
defaut, cible le technicien "allan" et poste UNIQUEMENT sur son webhook Slack
(variable d'environnement BRIEFING_SLACK_WEBHOOK_ALLAN). Ni JP ni Nicolas ne
recoivent quoi que ce soit tant que le pilote n'est pas valide.

Le webhook Slack n'est jamais code en dur : il vient d'un secret GitHub injecte
comme variable d'environnement (voir .github/workflows/briefing_slack_pilot.yml).

Execution : tous les jours a 12h Montreal via GitHub Actions
(cron 16+17 UTC, gate par heure locale pour gerer EST/EDT).

Usage local :
    python scripts/briefing_slack_pilot.py --dry-run          # affiche, n'envoie pas
    python scripts/briefing_slack_pilot.py --force            # envoie hors fenetre horaire
    python scripts/briefing_slack_pilot.py --technician allan
"""
import argparse
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.techniciens_config import get_technicien_by_username  # noqa: E402
from core.supabase_storage import SupabaseStorage                 # noqa: E402
from core.timezone_utils import (                                 # noqa: E402
    MONTREAL_TZ,
    montreal_to_utc,
    utc_to_montreal,
)

# Heure d'envoi (heure Montreal), fidele a l'ancienne tache Windows (12h).
SEND_HOUR = 12
# Variable d'env par defaut contenant le webhook Slack du technicien pilote.
DEFAULT_WEBHOOK_ENV = "BRIEFING_SLACK_WEBHOOK_ALLAN"


def get_tomorrow_appointments(storage: SupabaseStorage, gazelle_id: str):
    """RV ACTIVE du technicien pour demain (fenetre journee Montreal -> UTC)."""
    now_mtl = datetime.now(MONTREAL_TZ)
    start_mtl = (now_mtl + timedelta(days=1)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    end_mtl = start_mtl + timedelta(days=1)

    start_utc = montreal_to_utc(start_mtl).strftime("%Y-%m-%dT%H:%M:%SZ")
    end_utc = montreal_to_utc(end_mtl).strftime("%Y-%m-%dT%H:%M:%SZ")

    result = (
        storage.client.table("gazelle_appointments")
        .select("*")
        .eq("technicien", gazelle_id)
        .eq("status", "ACTIVE")
        .gte("start_datetime", start_utc)
        .lt("start_datetime", end_utc)
        .order("start_datetime")
        .execute()
    )
    return result.data or [], start_mtl.date()


def _client_name(storage: SupabaseStorage, apt: dict) -> str:
    name = apt.get("client_name")
    if name:
        return name
    client_id = apt.get("client_external_id")
    if client_id:
        try:
            res = (
                storage.client.table("gazelle_clients")
                .select("company_name")
                .eq("external_id", client_id)
                .limit(1)
                .execute()
            )
            if res.data:
                return res.data[0].get("company_name") or "N/A"
        except Exception:
            pass
    return "N/A"


def _appt_time(apt: dict) -> str:
    raw = apt.get("start_datetime")
    if not raw:
        return apt.get("appointment_time") or "N/A"
    try:
        return utc_to_montreal(raw).strftime("%H:%M")
    except Exception:
        return apt.get("appointment_time") or "N/A"


def _piano_label(apt: dict) -> str:
    piano = apt.get("piano_description")
    if piano:
        return piano
    make = (apt.get("piano_make") or "").strip()
    model = (apt.get("piano_model") or "").strip()
    return f"{make} {model}".strip()


def format_blocks(storage: SupabaseStorage, tech_name: str, rows: list) -> list:
    header = {
        "type": "header",
        "text": {"type": "plain_text", "text": f"Briefing - {tech_name}"},
    }
    intro = {
        "type": "section",
        "text": {"type": "mrkdwn", "text": f"*{len(rows)} rendez-vous* pour demain"},
    }
    blocks = [header, intro, {"type": "divider"}]

    for i, r in enumerate(rows[:10], 1):
        client = _client_name(storage, r)
        time_str = _appt_time(r)
        piano = _piano_label(r)
        service = r.get("title") or "N/A"
        notes = (r.get("description") or "").strip()
        location = (r.get("location") or "").strip()

        text = f"*RDV #{i} - {time_str}*\n- {client}\n- {service}"
        if piano:
            text += f"\n- Piano : {piano}"
        if location:
            text += f"\n- Lieu : {location}"
        if notes:
            text += f"\n- Note : {notes[:160]}"
        blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": text}})

    generated = datetime.now(MONTREAL_TZ).strftime("%Y-%m-%d %H:%M")
    blocks.append(
        {
            "type": "context",
            "elements": [
                {"type": "mrkdwn", "text": f"Genere le {generated} (nuage / GitHub Actions)"}
            ],
        }
    )
    return blocks


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--technician", default="allan", help="username (defaut: allan)")
    parser.add_argument(
        "--webhook-env",
        default=DEFAULT_WEBHOOK_ENV,
        help=f"nom de la var d'env contenant le webhook Slack (defaut: {DEFAULT_WEBHOOK_ENV})",
    )
    parser.add_argument("--dry-run", action="store_true", help="affiche le payload sans envoyer")
    parser.add_argument("--force", action="store_true", help="ignore la fenetre horaire")
    args = parser.parse_args()

    tech = get_technicien_by_username(args.technician)
    if not tech:
        print(f"ERREUR : technicien inconnu '{args.technician}'")
        return 1
    tech_name = tech["prenom"]
    gazelle_id = tech["gazelle_id"]

    # Gate horaire : le cron tombe a 16h ET 17h UTC (EST/EDT) -> on ne garde
    # que l'execution ou il est 12h a Montreal. Contourne par --force / FORCE_RUN
    # (dispatch manuel) et par --dry-run.
    force = args.force or os.getenv("FORCE_RUN", "").lower() in ("1", "true", "yes")
    if not args.dry_run and not force:
        current_hour = datetime.now(MONTREAL_TZ).hour
        if current_hour != SEND_HOUR:
            print(
                f"Hors fenetre : il est {current_hour}h a Montreal (envoi prevu a "
                f"{SEND_HOUR}h). Sortie silencieuse."
            )
            return 0

    storage = SupabaseStorage(silent=True)
    rows, target_date = get_tomorrow_appointments(storage, gazelle_id)

    if not rows:
        payload = {
            "text": f"Briefing technicien - {tech_name} ({target_date.isoformat()}) : "
            f"aucun rendez-vous pour demain."
        }
    else:
        payload = {
            "text": f"Briefing technicien - {tech_name} ({target_date.isoformat()})",
            "blocks": format_blocks(storage, tech_name, rows),
        }

    if args.dry_run:
        import json

        print("--- DRY RUN : payload Slack (non envoye) ---")
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        print(f"--- {len(rows)} RV pour {tech_name} le {target_date.isoformat()} ---")
        return 0

    webhook = os.getenv(args.webhook_env)
    if not webhook:
        print(f"ERREUR : variable d'environnement {args.webhook_env} absente.")
        return 1

    resp = requests.post(webhook, json=payload, timeout=10)
    resp.raise_for_status()
    print(
        f"OK - Briefing envoye pour {tech_name} : {len(rows)} RV le "
        f"{target_date.isoformat()} (via {args.webhook_env})"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
