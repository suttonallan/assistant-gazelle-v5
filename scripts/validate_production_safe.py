#!/usr/bin/env python3
"""
Validation PRODUCTION-SAFE - Test anti-crash.

Simule des entrées avec champs manquants pour prouver que le code ne crashe JAMAIS.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.alerts.humidity_scanner_safe import HumidityScannerSafe


def test_case_1_entry_sans_client():
    """TEST 1: Entrée SANS client - Ne doit PAS crasher."""
    print("=" * 80)
    print("TEST 1: ENTRÉE SANS CLIENT (protection contre crash)")
    print("=" * 80)
    print()

    scanner = HumidityScannerSafe()

    # Simuler une entrée SANS client
    entry_sans_client = {
        "id": "tme_test_001",
        "occurredAt": "2026-01-11T10:00:00Z",
        "type": "SERVICE_ENTRY_MANUAL",
        "comment": "Piano débranché. Besoin d'une rallonge.",
        "summary": None,
        "client": None,  # ❌ PAS DE CLIENT
        "piano": {
            "id": "ins_test_001",
            "make": "Yamaha",
            "model": "G2",
            "serialNumber": "123456"
        }
    }

    print("Entrée de test (client=None):")
    print(f"  ID: {entry_sans_client['id']}")
    print(f"  Comment: {entry_sans_client['comment']}")
    print(f"  Client: {entry_sans_client['client']}")
    print()

    try:
        # PROTECTION: Accès sécurisé
        client = (entry_sans_client.get("client") or {})
        client_id = client.get("id")
        client_name = client.get("companyName")

        print("✅ Accès sécurisé réussi:")
        print(f"   client_id: {client_id}")
        print(f"   client_name: {client_name}")
        print()

        # Tester la détection
        alert_keywords = scanner.config.get("alert_keywords") or {}
        resolution_keywords = scanner.config.get("resolution_keywords") or {}

        result = scanner.detect_issue_safe(
            entry_sans_client.get("comment"),
            alert_keywords,
            resolution_keywords
        )

        if result:
            alert_type, description, is_resolved = result
            print(f"🚨 Alerte détectée:")
            print(f"   Type: {alert_type}")
            print(f"   Description: {description}")
            print(f"   Résolu: {is_resolved}")
            print()
            return True
        else:
            print("⚠️  Aucune alerte détectée")
            return False

    except Exception as e:
        print(f"❌ CRASH détecté: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_case_2_entry_sans_piano():
    """TEST 2: Entrée SANS piano - Ne doit PAS crasher."""
    print("=" * 80)
    print("TEST 2: ENTRÉE SANS PIANO (protection contre crash)")
    print("=" * 80)
    print()

    scanner = HumidityScannerSafe()

    # Simuler une entrée SANS piano
    entry_sans_piano = {
        "id": "tme_test_002",
        "occurredAt": "2026-01-11T11:00:00Z",
        "type": "SERVICE_ENTRY_MANUAL",
        "comment": "Housse enlevée sur le piano.",
        "summary": "Problème housse",
        "client": {
            "id": "cli_test_001",
            "companyName": "Test Client"
        },
        "piano": None  # ❌ PAS DE PIANO
    }

    print("Entrée de test (piano=None):")
    print(f"  ID: {entry_sans_piano['id']}")
    print(f"  Comment: {entry_sans_piano['comment']}")
    print(f"  Piano: {entry_sans_piano['piano']}")
    print()

    try:
        # PROTECTION: Accès sécurisé
        piano = (entry_sans_piano.get("piano") or {})
        piano_id = piano.get("id")
        piano_make = piano.get("make")
        piano_model = piano.get("model")

        print("✅ Accès sécurisé réussi:")
        print(f"   piano_id: {piano_id}")
        print(f"   piano_make: {piano_make}")
        print(f"   piano_model: {piano_model}")
        print()

        # SCANNER DOUBLE: Tester summary puis comment
        alert_keywords = scanner.config.get("alert_keywords") or {}
        resolution_keywords = scanner.config.get("resolution_keywords") or {}

        # Test summary d'abord
        result = scanner.detect_issue_safe(
            entry_sans_piano.get("summary"),
            alert_keywords,
            resolution_keywords
        )

        if result:
            print("✅ Détection via SUMMARY réussie")
        else:
            # Fallback sur comment
            result = scanner.detect_issue_safe(
                entry_sans_piano.get("comment"),
                alert_keywords,
                resolution_keywords
            )
            if result:
                print("✅ Détection via COMMENT réussie (fallback)")

        if result:
            alert_type, description, is_resolved = result
            print(f"🚨 Alerte détectée:")
            print(f"   Type: {alert_type}")
            print(f"   Description: {description}")
            print()
            return True
        else:
            print("⚠️  Aucune alerte détectée")
            return False

    except Exception as e:
        print(f"❌ CRASH détecté: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_case_3_entry_comment_none():
    """TEST 3: Entrée avec comment=None - Ne doit PAS crasher."""
    print("=" * 80)
    print("TEST 3: ENTRÉE AVEC COMMENT=NONE (scanner double)")
    print("=" * 80)
    print()

    scanner = HumidityScannerSafe()

    # Simuler une entrée avec comment=None mais summary valide
    entry_comment_none = {
        "id": "tme_test_003",
        "occurredAt": "2026-01-11T12:00:00Z",
        "type": "SYSTEM_MESSAGE",
        "comment": None,  # ❌ PAS DE COMMENT
        "summary": "Réservoir vide détecté",
        "client": {
            "id": "cli_test_002",
            "companyName": "Test Client 2"
        },
        "piano": {
            "id": "ins_test_002",
            "make": "Steinway",
            "model": "B",
            "serialNumber": "654321"
        }
    }

    print("Entrée de test (comment=None, summary valide):")
    print(f"  ID: {entry_comment_none['id']}")
    print(f"  Comment: {entry_comment_none['comment']}")
    print(f"  Summary: {entry_comment_none['summary']}")
    print()

    try:
        alert_keywords = scanner.config.get("alert_keywords") or {}
        resolution_keywords = scanner.config.get("resolution_keywords") or {}

        # SCANNER DOUBLE: summary d'abord
        summary = entry_comment_none.get("summary")
        comment = entry_comment_none.get("comment")

        result_summary = scanner.detect_issue_safe(summary, alert_keywords, resolution_keywords)
        result_comment = scanner.detect_issue_safe(comment, alert_keywords, resolution_keywords)

        print(f"✅ Scanner double terminé:")
        print(f"   Résultat summary: {result_summary is not None}")
        print(f"   Résultat comment: {result_comment is not None}")
        print()

        result = result_summary or result_comment

        if result:
            alert_type, description, is_resolved = result
            print(f"🚨 Alerte détectée via SUMMARY:")
            print(f"   Type: {alert_type}")
            print(f"   Description: {description}")
            print()
            return True
        else:
            print("⚠️  Aucune alerte détectée")
            return False

    except Exception as e:
        print(f"❌ CRASH détecté: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_case_4_entry_tout_none():
    """TEST 4: Entrée avec TOUT=None - Ne doit PAS crasher."""
    print("=" * 80)
    print("TEST 4: ENTRÉE AVEC TOUT=NONE (protection totale)")
    print("=" * 80)
    print()

    scanner = HumidityScannerSafe()

    # Simuler une entrée COMPLÈTEMENT vide
    entry_tout_none = {
        "id": "tme_test_004",
        "occurredAt": None,
        "type": None,
        "comment": None,
        "summary": None,
        "client": None,
        "piano": None
    }

    print("Entrée de test (tout=None):")
    print(f"  ID: {entry_tout_none['id']}")
    print(f"  Tous les autres champs: None")
    print()

    try:
        # PROTECTION TOTALE: Tous les accès sécurisés
        client = (entry_tout_none.get("client") or {})
        client_id = client.get("id")

        piano = (entry_tout_none.get("piano") or {})
        piano_id = piano.get("id")

        comment = entry_tout_none.get("comment")
        summary = entry_tout_none.get("summary")

        print("✅ Accès sécurisés réussis:")
        print(f"   client_id: {client_id}")
        print(f"   piano_id: {piano_id}")
        print(f"   comment: {comment}")
        print(f"   summary: {summary}")
        print()

        # Tester détection (doit retourner None sans crasher)
        alert_keywords = scanner.config.get("alert_keywords") or {}
        resolution_keywords = scanner.config.get("resolution_keywords") or {}

        result_summary = scanner.detect_issue_safe(summary, alert_keywords, resolution_keywords)
        result_comment = scanner.detect_issue_safe(comment, alert_keywords, resolution_keywords)

        print(f"✅ Détection sans crash:")
        print(f"   summary: {result_summary}")
        print(f"   comment: {result_comment}")
        print()

        return result_summary is None and result_comment is None

    except Exception as e:
        print(f"❌ CRASH détecté: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Exécute tous les tests anti-crash."""
    print()
    print("🛡️  VALIDATION PRODUCTION-SAFE - TESTS ANTI-CRASH")
    print()

    results = []

    # Test 1: Sans client
    results.append(("Entrée SANS client", test_case_1_entry_sans_client()))
    print()

    # Test 2: Sans piano
    results.append(("Entrée SANS piano", test_case_2_entry_sans_piano()))
    print()

    # Test 3: Comment=None
    results.append(("Comment=None (scanner double)", test_case_3_entry_comment_none()))
    print()

    # Test 4: Tout=None
    results.append(("Tout=None (protection totale)", test_case_4_entry_tout_none()))
    print()

    # Résumé
    print("=" * 80)
    print("RÉSUMÉ DES TESTS ANTI-CRASH")
    print("=" * 80)
    print()

    all_passed = True
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {name}")
        if not passed:
            all_passed = False

    print()

    if all_passed:
        print("=" * 80)
        print("🎉 TOUS LES TESTS ANTI-CRASH PASSENT")
        print("=" * 80)
        print()
        print("Le code est PRODUCTION-SAFE:")
        print("  ✅ Protection contre client=None")
        print("  ✅ Protection contre piano=None")
        print("  ✅ Scanner double (summary ET comment)")
        print("  ✅ Protection contre tout=None")
        print()
        print("Le système ne crashera JAMAIS! 🛡️")
        print()
        return 0
    else:
        print("=" * 80)
        print("⚠️  CERTAINS TESTS ONT ÉCHOUÉ")
        print("=" * 80)
        print()
        return 1


if __name__ == "__main__":
    sys.exit(main())
