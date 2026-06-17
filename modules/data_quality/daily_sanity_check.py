#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Vérificateur quotidien des données PTM.

But : détecter des anomalies AVANT qu'Allan les vive en production, et lui envoyer
un courriel récapitulatif — uniquement s'il y a quelque chose à signaler (zéro bruit
les jours propres).

Aucune dépendance à l'IA Anthropic : ce sont des vérifications déterministes sur les
données. Reste donc fonctionnel même si les crédits API sont à plat.

Ajouter un check = écrire une fonction `check_xxx(storage) -> list[dict]` et l'ajouter
à CHECKS. Chaque anomalie : {check, severity, title, detail}.

Exécution : quotidienne (cron / GitHub Actions). DRY_RUN=1 pour ne pas envoyer.
"""
import os
import sys
import re
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from core.supabase_storage import SupabaseStorage  # noqa: E402

RECIPIENT = "asutton@piano-tek.com"
WINDOW_DAYS = 30  # fenêtre de scan (jours en arrière)


def _norm_amount(val):
    """Normalise un montant de stationnement ('20', '20.00', '20,00$', '') -> '20.00' ou ''."""
    if not val:
        return ""
    m = re.search(r"(\d+(?:[.,]\d{1,2})?)", str(val))
    if not m:
        return ""
    return f"{float(m.group(1).replace(',', '.')):.2f}"


# ════════════════════════════════════════════════════════════════════
# CHECK 1 — Stationnement PdA mal attribué / doublé
# ════════════════════════════════════════════════════════════════════

def check_pda_parking(storage) -> list:
    """Pour chaque demande PdA récente AVEC stationnement, on revalide via la logique
    corrigée (note « stat » sur LE piano du RV). Si le montant stocké ne correspond
    pas à ce que la note du piano justifie -> anomalie (mauvaise attribution / double)."""
    anomalies = []
    H = storage._get_headers()
    api = storage.api_url
    import requests as http
    since = (datetime.now() - timedelta(days=WINDOW_DAYS)).strftime("%Y-%m-%d")

    reqs = http.get(
        f"{api}/place_des_arts_requests?parking=not.is.null"
        f"&appointment_date=gte.{since}"
        f"&select=id,appointment_id,appointment_date,room,for_who,technician_id,parking",
        headers=H, timeout=20).json()
    reqs = [r for r in reqs if isinstance(r, dict) and _norm_amount(r.get("parking"))]
    if not reqs:
        return anomalies

    apt_ids = [r["appointment_id"] for r in reqs if r.get("appointment_id")]
    appts = {}
    if apt_ids:
        ids_csv = ",".join(apt_ids)
        rows = http.get(f"{api}/gazelle_appointments?external_id=in.({ids_csv})"
                        f"&select=external_id,piano_external_id,technicien,appointment_date",
                        headers=H, timeout=20).json()
        appts = {a["external_id"]: a for a in rows if isinstance(a, dict)}

    from modules.place_des_arts.services.gazelle_sync import GazelleSyncService
    svc = GazelleSyncService(storage)

    for r in reqs:
        stored = _norm_amount(r.get("parking"))
        apt = appts.get(r.get("appointment_id"))
        expected = _norm_amount(svc._extract_parking_from_appointment(apt)) if apt else ""
        if expected != stored:
            anomalies.append({
                "check": "pda_parking",
                "severity": "warning",
                "title": f"Stationnement à vérifier — {r.get('appointment_date', '')[:10]} {r.get('room', '')}",
                "detail": (f"{r.get('for_who', '')} : {stored} $ rapporté, mais la note « stat » du "
                           f"piano de ce RV justifie {expected or 'aucun montant'}. "
                           f"Possible double comptage ou mauvaise attribution."),
            })
    return anomalies


# ════════════════════════════════════════════════════════════════════
# CHECK 2 — Note de piano qui contredit le statut PLS
# ════════════════════════════════════════════════════════════════════

# RETIRE = vrai retrait (contredit « installé »). On exclut « débranché » : un PLS
# débranché reste INSTALLÉ (juste pas en usage) — ce n'est pas une contradiction.
_PLS_REMOVED = re.compile(r"pls\s+(?:retir|enlev|absent)|(?:retir[ée]s?|enlev[ée]s?)\s+(?:le\s+)?pls", re.I)
_PLS_PRESENT_NOTE = re.compile(r"(nouveau|neuf|install[ée]).{0,20}(pls|piano life saver|life saver)", re.I)


def check_pls_note_contradiction(storage) -> list:
    """Pianos dont les NOTES contredisent le drapeau dampp_chaser_installed :
       - notes disent le PLS retiré/absent MAIS le drapeau dit installé, ou
       - notes disent un PLS neuf/installé MAIS le drapeau dit non installé.
    Faible taux de faux positifs (on exige une formulation explicite)."""
    anomalies = []
    H = storage._get_headers()
    api = storage.api_url
    import requests as http
    rows = http.get(f"{api}/gazelle_pianos?notes=not.is.null"
                    f"&select=external_id,make,model,notes,dampp_chaser_installed,location",
                    headers=H, timeout=30).json()
    for p in (rows if isinstance(rows, list) else []):
        notes = p.get("notes") or ""
        installed = bool(p.get("dampp_chaser_installed"))
        label = f"{p.get('make', '')} {p.get('model', '')}".strip() + (f" — {p.get('location')}" if p.get('location') else "")
        if _PLS_REMOVED.search(notes) and installed:
            anomalies.append({
                "check": "pls_contradiction", "severity": "info",
                "title": f"PLS contradictoire — {label}",
                "detail": "La note indique un PLS retiré/absent, mais le piano est marqué « PLS installé ». À réconcilier.",
            })
        elif _PLS_PRESENT_NOTE.search(notes) and not installed:
            anomalies.append({
                "check": "pls_contradiction", "severity": "info",
                "title": f"PLS contradictoire — {label}",
                "detail": "La note parle d'un PLS neuf/installé, mais le piano n'est PAS marqué « PLS installé ». À réconcilier.",
            })
    return anomalies


CHECKS = [check_pda_parking, check_pls_note_contradiction]


# ════════════════════════════════════════════════════════════════════
# Orchestration + courriel
# ════════════════════════════════════════════════════════════════════

def run_checks(storage) -> list:
    found = []
    for check in CHECKS:
        try:
            found.extend(check(storage) or [])
        except Exception as e:
            found.append({"check": check.__name__, "severity": "error",
                          "title": f"Le check {check.__name__} a échoué",
                          "detail": str(e)[:300]})
    return found


def build_email(anomalies: list):
    n = len(anomalies)
    by = {}
    for a in anomalies:
        by.setdefault(a["check"], []).append(a)
    plain = [f"Vérificateur quotidien PTM — {n} anomalie(s) à vérifier", ""]
    html = [f"<h2>Vérificateur quotidien — {n} anomalie(s)</h2>"]
    for check, items in by.items():
        plain.append(f"[{check}] ({len(items)})")
        html.append(f"<h3>{check} ({len(items)})</h3><ul>")
        for a in items:
            plain.append(f"  - {a['title']} : {a['detail']}")
            html.append(f"<li><strong>{a['title']}</strong><br>{a['detail']}</li>")
        html.append("</ul>")
        plain.append("")
    return f"[PTM] Vérificateur quotidien — {n} anomalie(s)", "".join(html), "\n".join(plain)


def main() -> int:
    dry_run = os.getenv("DRY_RUN", "").lower() in ("1", "true", "yes")
    storage = SupabaseStorage(silent=True)
    anomalies = run_checks(storage)

    print(f"Verificateur quotidien : {len(anomalies)} anomalie(s)")
    for a in anomalies:
        print(f"  [{a['severity']}] {a['title']} :: {a['detail']}")

    if not anomalies:
        print("Rien a signaler — aucun courriel envoye.")
        return 0

    subject, html, plain = build_email(anomalies)
    if dry_run:
        print("\n--- DRY RUN (aucun courriel) ---")
        print(plain)
        return 0

    from core.email_notifier import get_email_notifier
    ok = get_email_notifier().send_email(
        to_emails=[RECIPIENT], subject=subject, html_content=html, plain_content=plain)
    print("Courriel envoye." if ok else "Echec envoi courriel.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
