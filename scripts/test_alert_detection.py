#!/usr/bin/env python3
"""
Test de la détection d'alertes pour valider qu'elle ne déclenche PAS
de fausses alertes sur les notes de service normales avec mesures.
"""

import sys
from pathlib import Path

# Ajouter le répertoire parent au PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.alerts.humidity_scanner import HumidityScanner
import json

# Charger la config
CONFIG_PATH = Path(__file__).parent.parent / "config" / "alerts" / "config.json"

def load_config():
    """Charge la configuration des alertes."""
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)

# Cas de test
TEST_CASES = [
    # Format: (description, should_trigger_alert, reason)
    (
        "Accord 440Hz, 21C, 39%",
        False,
        "Note de service normale avec mesures - NE DOIT PAS alerter"
    ),
    (
        "Service Accord 440Hz, 21C, 39%",
        False,
        "Note de service normale - NE DOIT PAS alerter"
    ),
    (
        "20C, 33%",
        False,
        "Mesures seules - NE DOIT PAS alerter"
    ),
    (
        "Température: 20°, humidité: 35%",
        False,
        "Rapport de mesures - NE DOIT PAS alerter"
    ),
    (
        "PLS débranché",
        True,
        "Problème d'alimentation - DOIT alerter"
    ),
    (
        "Dampp Chaser débranché",
        True,
        "Système débranché - DOIT alerter"
    ),
    (
        "housse enlevée",
        True,
        "Housse retirée - DOIT alerter"
    ),
    (
        "réservoir vide",
        True,
        "Réservoir vide - DOIT alerter"
    ),
    (
        "humidité trop basse",
        True,
        "Problème d'humidité avec contexte - DOIT alerter"
    ),
    (
        "température anormale",
        True,
        "Problème de température avec contexte - DOIT alerter"
    ),
    (
        "fenêtre ouverte",
        True,
        "Problème environnement - DOIT alerter"
    ),
]

def run_tests():
    """Exécute tous les tests de détection d'alertes."""
    print("=" * 80)
    print("🧪 TEST DÉTECTION ALERTES (sans faux positifs)")
    print("=" * 80)
    print()

    config = load_config()
    scanner = HumidityScanner()

    passed = 0
    failed = 0

    for description, should_alert, reason in TEST_CASES:
        result = scanner.detect_issue(
            description,
            config["alert_keywords"],
            config["resolution_keywords"]
        )

        has_alert = result is not None

        if has_alert == should_alert:
            status = "✅ PASS"
            passed += 1
        else:
            status = "❌ FAIL"
            failed += 1

        print(f"{status} | {reason}")
        print(f"  Description:  '{description}'")
        print(f"  Should alert: {should_alert}")
        print(f"  Has alert:    {has_alert}")
        if result:
            print(f"  Alert type:   {result[0]}")
            print(f"  Alert desc:   {result[1]}")
        print()

    print("=" * 80)
    print(f"📊 RÉSULTATS: {passed} réussis, {failed} échoués sur {len(TEST_CASES)} tests")
    print("=" * 80)

    if failed == 0:
        print("🎉 Tous les tests sont passés!")
        print("✅ Aucun faux positif détecté sur les notes de service normales")
        return 0
    else:
        print(f"⚠️  {failed} test(s) ont échoué")
        return 1

if __name__ == "__main__":
    exit_code = run_tests()
    sys.exit(exit_code)
