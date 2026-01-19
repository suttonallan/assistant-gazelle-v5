#!/usr/bin/env python3
"""
Test de l'extraction intelligente des mesures de température et humidité.

Valide que tous les formats utilisés par les techniciens sont correctement détectés:
- 20C, 33%
- 20c, 33%
- 20°, 33%
- 20°C, 33%
- 21C,39% (sans espace)
- Accord 440Hz, 21C, 39%
"""

import sys
from pathlib import Path

# Ajouter le répertoire parent au PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.reports.service_reports import ServiceReports

# Cas de test
TEST_CASES = [
    # Format: (input, expected_output, description)
    ("20C, 33%", "20°, 33%", "Format compact avec C majuscule"),
    ("20c, 33%", "20°, 33%", "Format compact avec c minuscule"),
    ("20°, 33%", "20°, 33%", "Format avec symbole degré"),
    ("20°C, 33%", "20°, 33%", "Format avec °C"),
    ("21C,39%", "21°, 39%", "Format sans espaces"),
    ("Accord 440Hz, 21C, 39%", "21°, 39%", "Note de service avec mesures"),
    ("Service Accord 440Hz, 21C, 39%.", "21°, 39%", "Note de service complète"),
    ("20 C, 33%", "20°, 33%", "Avec espace avant C"),
    ("Température: 23°, humidité: 35%", "23°, 35%", "Format verbeux"),
    ("Température ambiante 23° Celsius, humidité relative 35%", "23°, 35%", "Format très verbeux"),
    ("68F, 40%", "68°, 40%", "Format Fahrenheit"),
    ("38%", "38%", "Humidité seule"),
    ("Humidité 38%", "38%", "Humidité seule avec mot-clé"),
    ("", "", "Texte vide"),
    ("Accord sans mesure", "", "Pas de mesure détectée"),
    ("Accord 440Hz", "", "Pas de mesure de température/humidité"),
]

def run_tests():
    """Exécute tous les tests d'extraction."""
    print("=" * 80)
    print("🧪 TEST EXTRACTION MESURES TEMPÉRATURE/HUMIDITÉ")
    print("=" * 80)
    print()

    passed = 0
    failed = 0

    for input_text, expected, description in TEST_CASES:
        result = ServiceReports._extract_measurements_from_text(input_text)

        if result == expected:
            status = "✅ PASS"
            passed += 1
        else:
            status = "❌ FAIL"
            failed += 1

        print(f"{status} | {description}")
        print(f"  Input:    '{input_text}'")
        print(f"  Expected: '{expected}'")
        print(f"  Got:      '{result}'")
        print()

    print("=" * 80)
    print(f"📊 RÉSULTATS: {passed} réussis, {failed} échoués sur {len(TEST_CASES)} tests")
    print("=" * 80)

    if failed == 0:
        print("🎉 Tous les tests sont passés!")
        return 0
    else:
        print(f"⚠️  {failed} test(s) ont échoué")
        return 1

if __name__ == "__main__":
    exit_code = run_tests()
    sys.exit(exit_code)
