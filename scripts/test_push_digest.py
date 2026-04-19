#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test manuel du module modules/briefing/push_digest.py.

Exerce la logique pure (groupement par institution, calcul age_days,
escalation, rendu HTML/plain) avec des donnees mockees. Ne touche pas
a Supabase ni a l'email.

Usage :
    python3 scripts/test_push_digest.py           # tous les tests
    python3 scripts/test_push_digest.py --live    # teste run_push_digest()
                                                  # contre la vraie Supabase
                                                  # SANS envoyer d'email
"""

import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.briefing.push_digest import (
    _build_html,
    _build_plain,
    _days_since,
    _format_validated_on,
    _group_by_institution,
    ESCALATION_DAYS,
)


GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"


def _ok(msg: str):
    print(f"  {GREEN}OK{RESET} {msg}")


def _fail(msg: str):
    print(f"  {RED}FAIL{RESET} {msg}")
    raise SystemExit(1)


def _iso_days_ago(n: int) -> str:
    dt = datetime.now(timezone.utc) - timedelta(days=n)
    # format sans timezone, comme datetime.utcnow().isoformat() dans service_records.py
    return dt.replace(tzinfo=None).isoformat()


def test_days_since():
    print("\n[1] _days_since")
    assert _days_since(None) is None, "None devrait retourner None"
    _ok("None -> None")
    assert _days_since("") is None, "string vide -> None"
    _ok("'' -> None")
    assert _days_since(_iso_days_ago(0)) == 0
    _ok("aujourd'hui -> 0")
    assert _days_since(_iso_days_ago(1)) == 1
    _ok("hier -> 1")
    assert _days_since(_iso_days_ago(5)) == 5
    _ok("il y a 5 jours -> 5")


def test_format_validated_on():
    print("\n[2] _format_validated_on")
    assert _format_validated_on(None) == "date inconnue"
    _ok("None -> 'date inconnue'")
    formatted = _format_validated_on("2026-04-18T14:30:00")
    assert "2026" in formatted and ("Apr" in formatted or "avr" in formatted.lower()), formatted
    _ok(f"ISO -> '{formatted}'")


def test_group_empty():
    print("\n[3] _group_by_institution (empty)")
    grouped = _group_by_institution([])
    assert grouped == {}
    _ok("[] -> {}")


def test_group_single_institution():
    print("\n[4] _group_by_institution (une institution, pas d'escalation)")
    records = [
        {
            "id": "r1",
            "piano_id": "pno_1",
            "piano_local": "240",
            "piano_name": "Yamaha U1",
            "institution_slug": "vincent-dindy",
            "validated_at": _iso_days_ago(1),
            "validated_by": "Nicolas",
            "travail": "Accord complet",
        },
    ]
    grouped = _group_by_institution(records)
    assert list(grouped.keys()) == ["vincent-dindy"]
    rec = grouped["vincent-dindy"][0]
    assert rec["age_days"] == 1
    assert rec["escalate"] is False, "1 jour < 3, pas d'escalation"
    _ok("1 fiche, 1 institution, age=1j, escalate=False")


def test_group_escalation():
    print("\n[5] _group_by_institution (escalation declenchee)")
    records = [
        {
            "id": "r1",
            "piano_id": "pno_1",
            "piano_local": "103",
            "institution_slug": "orford",
            "validated_at": _iso_days_ago(ESCALATION_DAYS),
            "validated_by": "Marie",
            "travail": "Accord",
        },
        {
            "id": "r2",
            "piano_id": "pno_2",
            "piano_local": "305",
            "institution_slug": "orford",
            "validated_at": _iso_days_ago(ESCALATION_DAYS + 2),
            "validated_by": "Marie",
            "travail": "Accord + reparation pedale",
        },
    ]
    grouped = _group_by_institution(records)
    assert all(r["escalate"] for r in grouped["orford"]), \
        f"Les deux fiches >= {ESCALATION_DAYS} jours devraient escalader"
    _ok(f"2 fiches >= {ESCALATION_DAYS} jours -> escalate=True")


def test_group_multi_institutions():
    print("\n[6] _group_by_institution (3 institutions)")
    records = [
        {"id": "r1", "piano_id": "p1", "piano_local": "240",
         "institution_slug": "vincent-dindy",
         "validated_at": _iso_days_ago(0), "validated_by": "Nicolas"},
        {"id": "r2", "piano_id": "p2", "piano_local": "12",
         "institution_slug": "place-des-arts",
         "validated_at": _iso_days_ago(1), "validated_by": "Marie"},
        {"id": "r3", "piano_id": "p3", "piano_local": "A",
         "institution_slug": "orford",
         "validated_at": _iso_days_ago(5), "validated_by": "JP"},
    ]
    grouped = _group_by_institution(records)
    assert set(grouped.keys()) == {"vincent-dindy", "place-des-arts", "orford"}
    assert all(len(v) == 1 for v in grouped.values())
    assert grouped["orford"][0]["escalate"] is True
    assert grouped["vincent-dindy"][0]["escalate"] is False
    _ok("3 institutions, 1 seule escalade (Orford 5j)")


def test_build_html_no_escalation():
    print("\n[7] _build_html (sans escalation)")
    records = [
        {"id": "r1", "piano_id": "p1", "piano_local": "240",
         "piano_name": "Yamaha U1",
         "institution_slug": "vincent-dindy",
         "validated_at": _iso_days_ago(0), "validated_by": "Nicolas",
         "travail": "Accord complet"},
    ]
    grouped = _group_by_institution(records)
    html = _build_html(grouped, total=1, has_escalation=False, today_str="2026-04-18")
    assert "1 fiche(s)" in html
    assert "Vincent d'Indy" in html
    assert "Local <strong>240</strong>" in html
    assert "Yamaha U1" in html
    assert "Nicolas" in html
    assert "Allan est en copie" not in html  # pas de banniere
    _ok("HTML contient piano, institution, validator, pas de banniere escalation")


def test_build_html_with_escalation():
    print("\n[8] _build_html (avec escalation)")
    records = [
        {"id": "r1", "piano_id": "p1", "piano_local": "305",
         "institution_slug": "orford",
         "validated_at": _iso_days_ago(5), "validated_by": "Marie",
         "travail": "Accord"},
    ]
    grouped = _group_by_institution(records)
    html = _build_html(grouped, total=1, has_escalation=True, today_str="2026-04-18")
    assert "Allan est en copie" in html
    assert "il y a 5 jours" in html
    _ok("HTML contient banniere escalation + age en texte")


def test_build_plain():
    print("\n[9] _build_plain")
    records = [
        {"id": "r1", "piano_id": "p1", "piano_local": "240",
         "institution_slug": "vincent-dindy",
         "validated_at": _iso_days_ago(1), "validated_by": "Nicolas"},
        {"id": "r2", "piano_id": "p2", "piano_local": "305",
         "institution_slug": "orford",
         "validated_at": _iso_days_ago(5), "validated_by": "Marie"},
    ]
    grouped = _group_by_institution(records)
    plain = _build_plain(grouped, total=2)
    assert "2 fiche(s)" in plain
    assert "Vincent d'Indy" in plain
    assert "Orford" in plain
    assert "Local 240" in plain
    assert "[!]" in plain  # escalation marker
    _ok("Plain text contient institutions, locaux, marker escalation")


def test_live_run():
    """Optionnel : execute run_push_digest() contre la vraie Supabase.
    Monkey-patch EmailNotifier.send_email pour ne PAS envoyer."""
    print("\n[LIVE] run_push_digest() -- sans envoi reel d'email")
    from core import email_notifier as en_mod
    original_send = en_mod.EmailNotifier.send_email
    captured = {}

    def fake_send(self, to_emails, subject, html_content, plain_content=None, **kwargs):
        captured["to"] = to_emails
        captured["subject"] = subject
        captured["html_len"] = len(html_content or "")
        captured["plain"] = plain_content
        print(f"  [FAKE SEND] to={to_emails}")
        print(f"             subject={subject}")
        print(f"             html={len(html_content or '')} chars")
        return True

    en_mod.EmailNotifier.send_email = fake_send
    try:
        from modules.briefing.push_digest import run_push_digest
        import asyncio
        result = asyncio.run(run_push_digest())
        print(f"  Rapport : {result}")
        if result.get("validated_count", 0) == 0:
            print(f"  {YELLOW}Aucune fiche validee en attente -> rien envoye (comportement attendu).{RESET}")
        else:
            print(f"  {GREEN}Email aurait ete envoye a : {captured.get('to')}{RESET}")
    finally:
        en_mod.EmailNotifier.send_email = original_send


def main():
    live = "--live" in sys.argv
    print("=" * 60)
    print("Tests push_digest.py")
    print("=" * 60)

    test_days_since()
    test_format_validated_on()
    test_group_empty()
    test_group_single_institution()
    test_group_escalation()
    test_group_multi_institutions()
    test_build_html_no_escalation()
    test_build_html_with_escalation()
    test_build_plain()

    print(f"\n{GREEN}Tous les tests unitaires passent.{RESET}")

    if live:
        test_live_run()


if __name__ == "__main__":
    main()
