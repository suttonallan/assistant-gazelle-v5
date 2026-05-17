#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test manuel du module modules/briefing/push_digest.py.

Exerce la logique pure (groupement par institution, calcul age_days,
escalation, rendu HTML/plain, abbreviation tech) avec des donnees mockees.
Ne touche pas a Supabase ni a l'email.

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
    _format_date,
    _group_by_institution,
    _tech_abbreviation,
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


def test_format_date():
    print("\n[2] _format_date")
    assert _format_date(None) == "date inconnue"
    _ok("None -> 'date inconnue'")
    formatted = _format_date("2026-04-18T14:30:00")
    assert "2026" in formatted and ("Apr" in formatted or "avr" in formatted.lower()), formatted
    _ok(f"ISO -> '{formatted}'")


def test_tech_abbreviation():
    print("\n[3] _tech_abbreviation")
    assert _tech_abbreviation(None) == "?"
    _ok("None -> '?'")
    assert _tech_abbreviation("") == "?"
    _ok("'' -> '?'")
    # Avec un email connu (nlessard@piano-tek.com -> Nick)
    result = _tech_abbreviation("nlessard@piano-tek.com")
    assert result == "Nick", f"Expected 'Nick', got '{result}'"
    _ok("nlessard@piano-tek.com -> 'Nick'")
    # Avec un email inconnu
    result = _tech_abbreviation("unknown@example.com")
    assert result == "Unknown", f"Expected 'Unknown', got '{result}'"
    _ok("unknown@example.com -> fallback 'Unknown'")


def test_group_empty():
    print("\n[4] _group_by_institution (empty)")
    grouped = _group_by_institution([])
    assert grouped == {}
    _ok("[] -> {}")


def test_group_single_institution():
    print("\n[5] _group_by_institution (une institution, pas d'escalation)")
    records = [
        {
            "id": "r1",
            "piano_id": "pno_1",
            "piano_local": "240",
            "piano_name": "Yamaha U1",
            "institution_slug": "vincent-dindy",
            "started_at": _iso_days_ago(1),
            "updated_at": _iso_days_ago(0),
            "technician_email": "nlessard@piano-tek.com",
            "tech_abbrev": "Nick",
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
    print("\n[6] _group_by_institution (escalation declenchee)")
    records = [
        {
            "id": "r1",
            "piano_id": "pno_1",
            "piano_local": "103",
            "piano_name": "",
            "institution_slug": "orford",
            "started_at": _iso_days_ago(ESCALATION_DAYS),
            "updated_at": _iso_days_ago(ESCALATION_DAYS),
            "technician_email": "jp@piano-tek.com",
            "tech_abbrev": "JP",
            "travail": "Accord",
        },
        {
            "id": "r2",
            "piano_id": "pno_2",
            "piano_local": "305",
            "piano_name": "",
            "institution_slug": "orford",
            "started_at": _iso_days_ago(ESCALATION_DAYS + 2),
            "updated_at": _iso_days_ago(ESCALATION_DAYS + 2),
            "technician_email": "jp@piano-tek.com",
            "tech_abbrev": "JP",
            "travail": "Accord + reparation pedale",
        },
    ]
    grouped = _group_by_institution(records)
    assert all(r["escalate"] for r in grouped["orford"]), \
        f"Les deux fiches >= {ESCALATION_DAYS} jours devraient escalader"
    _ok(f"2 fiches >= {ESCALATION_DAYS} jours -> escalate=True")


def test_group_multi_institutions():
    print("\n[7] _group_by_institution (3 institutions)")
    records = [
        {"id": "r1", "piano_id": "p1", "piano_local": "240",
         "piano_name": "", "tech_abbrev": "Nick",
         "institution_slug": "vincent-dindy",
         "started_at": _iso_days_ago(0), "updated_at": _iso_days_ago(0)},
        {"id": "r2", "piano_id": "p2", "piano_local": "12",
         "piano_name": "", "tech_abbrev": "JP",
         "institution_slug": "place-des-arts",
         "started_at": _iso_days_ago(1), "updated_at": _iso_days_ago(1)},
        {"id": "r3", "piano_id": "p3", "piano_local": "A",
         "piano_name": "", "tech_abbrev": "Allan",
         "institution_slug": "orford",
         "started_at": _iso_days_ago(5), "updated_at": _iso_days_ago(5)},
    ]
    grouped = _group_by_institution(records)
    assert set(grouped.keys()) == {"vincent-dindy", "place-des-arts", "orford"}
    assert all(len(v) == 1 for v in grouped.values())
    assert grouped["orford"][0]["escalate"] is True
    assert grouped["vincent-dindy"][0]["escalate"] is False
    _ok("3 institutions, 1 seule escalade (Orford 5j)")


def test_build_html_no_escalation():
    print("\n[8] _build_html (sans escalation)")
    records = [
        {"id": "r1", "piano_id": "p1", "piano_local": "240",
         "piano_name": "Yamaha U1",
         "institution_slug": "vincent-dindy",
         "started_at": _iso_days_ago(0), "updated_at": _iso_days_ago(0),
         "tech_abbrev": "Nick",
         "travail": "Accord complet"},
    ]
    grouped = _group_by_institution(records)
    html = _build_html(grouped, total=1, has_escalation=False, today_str="2026-04-18")
    assert "1 fiche(s)" in html
    assert "Vincent d'Indy" in html
    assert "Local <strong>240</strong>" in html
    assert "Yamaha U1" in html
    assert "Nick" in html
    assert "Saisi par" in html
    assert "Allan est en copie" not in html
    _ok("HTML contient piano, institution, tech, pas de banniere escalation")


def test_build_html_with_escalation():
    print("\n[9] _build_html (avec escalation)")
    records = [
        {"id": "r1", "piano_id": "p1", "piano_local": "305",
         "piano_name": "",
         "institution_slug": "orford",
         "started_at": _iso_days_ago(5), "updated_at": _iso_days_ago(5),
         "tech_abbrev": "JP",
         "travail": "Accord"},
    ]
    grouped = _group_by_institution(records)
    html = _build_html(grouped, total=1, has_escalation=True, today_str="2026-04-18")
    assert "Allan est en copie" in html
    assert "il y a 5 jours" in html
    assert "JP" in html
    _ok("HTML contient banniere escalation + age + tech")


def test_build_plain():
    print("\n[10] _build_plain")
    records = [
        {"id": "r1", "piano_id": "p1", "piano_local": "240",
         "piano_name": "", "tech_abbrev": "Nick",
         "institution_slug": "vincent-dindy",
         "started_at": _iso_days_ago(1), "updated_at": _iso_days_ago(1)},
        {"id": "r2", "piano_id": "p2", "piano_local": "305",
         "piano_name": "", "tech_abbrev": "JP",
         "institution_slug": "orford",
         "started_at": _iso_days_ago(5), "updated_at": _iso_days_ago(5)},
    ]
    grouped = _group_by_institution(records)
    plain = _build_plain(grouped, total=2)
    assert "2 fiche(s)" in plain
    assert "Vincent d'Indy" in plain
    assert "Orford" in plain
    assert "Local 240" in plain
    assert "Nick" in plain
    assert "JP" in plain
    assert "[!]" in plain  # escalation marker
    _ok("Plain text contient institutions, locaux, techs, marker escalation")


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
        if plain_content:
            print(f"             plain preview:\n{plain_content[:500]}")
        return True

    en_mod.EmailNotifier.send_email = fake_send
    try:
        from modules.briefing.push_digest import run_push_digest
        import asyncio
        result = asyncio.run(run_push_digest())
        print(f"  Rapport : {result}")
        if result.get("draft_count", 0) == 0:
            print(f"  {YELLOW}Aucune fiche draft en attente -> rien envoye (comportement attendu).{RESET}")
        else:
            print(f"  {GREEN}Email aurait ete envoye a : {captured.get('to')}{RESET}")
    finally:
        en_mod.EmailNotifier.send_email = original_send


def main():
    live = "--live" in sys.argv
    print("=" * 60)
    print("Tests push_digest.py (fiches a valider)")
    print("=" * 60)

    test_days_since()
    test_format_date()
    test_tech_abbreviation()
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
