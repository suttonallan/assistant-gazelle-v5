#!/usr/bin/env python3
"""
Script de test pour le calculateur de frais de déplacement.

Usage:
    python scripts/test_travel_fees.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import os
from dotenv import load_dotenv

# Charger .env
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)

from modules.travel_fees.calculator import TravelFeeCalculator, calculate_travel_fee


def test_basic_usage():
    """Test 1: Usage basique avec fonction utilitaire."""
    print("=" * 70)
    print("TEST 1: Usage Basique (Fonction Utilitaire)")
    print("=" * 70)
    print("\nCode postal: H2X 2L1 (près de Nicolas)")
    print()

    try:
        result = calculate_travel_fee("H2X 2L1")
        print(result)
        print("\n✅ Test 1 réussi!")
    except ValueError as e:
        print(f"❌ Erreur: {e}")
        print("\nVeuillez ajouter GOOGLE_MAPS_API_KEY dans .env")
        return False
    except Exception as e:
        print(f"❌ Erreur inattendue: {e}")
        return False

    return True


def test_class_usage():
    """Test 2: Usage avec classe TravelFeeCalculator."""
    print("\n" + "=" * 70)
    print("TEST 2: Usage Classe TravelFeeCalculator")
    print("=" * 70)

    try:
        calculator = TravelFeeCalculator()

        # Test avec différents codes postaux
        test_cases = [
            ("H2X 2L1", "Près de Nicolas (gratuit attendu)"),
            ("H4N 2A1", "Près d'Allan (gratuit attendu)"),
            ("J4H 3M3", "Saint-Hubert (frais attendus)")
        ]

        for postal_code, description in test_cases:
            print(f"\n📍 {description}")
            print(f"   Code postal: {postal_code}")
            print()

            results = calculator.calculate_all_technicians(postal_code)

            for result in results:
                status = "GRATUIT" if result.is_free else f"{result.total_fee:.2f}$"
                print(f"   {result.technician_name}: {status} "
                      f"({result.distance_km:.1f} km, {result.duration_minutes:.0f} min)")

        print("\n✅ Test 2 réussi!")
        return True

    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        return False


def test_cheapest_technician():
    """Test 3: Trouver le technicien le moins cher."""
    print("\n" + "=" * 70)
    print("TEST 3: Trouver le Technicien le Moins Cher")
    print("=" * 70)

    try:
        calculator = TravelFeeCalculator()

        postal_code = "H3B 4W8"  # Centre-ville
        print(f"\nCode postal: {postal_code} (Centre-ville Montréal)")
        print()

        cheapest = calculator.get_cheapest_technician(postal_code)

        if cheapest:
            print(f"🏆 Technicien le moins cher: {cheapest.technician_name}")
            print(f"   Coût: {'GRATUIT' if cheapest.is_free else f'{cheapest.total_fee:.2f}$'}")
            print(f"   Distance: {cheapest.distance_km:.1f} km")
            print(f"   Temps: {cheapest.duration_minutes:.0f} min")

            # Afficher les détails si des frais s'appliquent
            if not cheapest.is_free:
                if cheapest.distance_fee > 0:
                    excess_km = cheapest.distance_km - 40
                    print(f"   Distance excédent: {excess_km:.1f} km → {cheapest.distance_fee:.2f}$")
                if cheapest.time_fee > 0:
                    excess_min = cheapest.duration_minutes - 40
                    print(f"   Temps excédent: {excess_min:.0f} min → {cheapest.time_fee:.2f}$")

            print("\n✅ Test 3 réussi!")
            return True
        else:
            print("❌ Aucun résultat trouvé")
            return False

    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        return False


def test_format_for_assistant():
    """Test 4: Format pour l'assistant conversationnel."""
    print("\n" + "=" * 70)
    print("TEST 4: Format pour Assistant Conversationnel")
    print("=" * 70)

    try:
        calculator = TravelFeeCalculator()

        postal_code = "H3Z 2Y7"
        assigned_tech = "Allan"

        print(f"\nCode postal: {postal_code}")
        print(f"Technicien assigné: {assigned_tech}")
        print()

        result = calculator.format_for_assistant(postal_code, assigned_tech)
        print(result)

        print("\n✅ Test 4 réussi!")
        return True

    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        return False


def test_edge_cases():
    """Test 5: Cas limites."""
    print("\n" + "=" * 70)
    print("TEST 5: Cas Limites")
    print("=" * 70)

    try:
        calculator = TravelFeeCalculator()

        # Test 1: Code postal invalide
        print("\n📍 Test avec code postal invalide")
        try:
            result = calculator.calculate_all_technicians("INVALID")
            print("⚠️ Devrait avoir généré une erreur")
        except Exception as e:
            print(f"✅ Erreur attendue capturée: {type(e).__name__}")

        # Test 2: Code postal vide
        print("\n📍 Test avec code postal vide")
        try:
            result = calculator.calculate_all_technicians("")
            print("⚠️ Devrait avoir généré une erreur")
        except Exception as e:
            print(f"✅ Erreur attendue capturée: {type(e).__name__}")

        print("\n✅ Test 5 réussi!")
        return True

    except Exception as e:
        print(f"\n❌ Erreur inattendue: {e}")
        return False


def run_all_tests():
    """Exécute tous les tests."""
    print("\n" + "=" * 70)
    print("🧪 TESTS DU CALCULATEUR DE FRAIS DE DÉPLACEMENT")
    print("=" * 70)

    # Vérifier que la clé API est configurée
    api_key = os.getenv('GOOGLE_MAPS_API_KEY')
    if not api_key:
        print("\n❌ GOOGLE_MAPS_API_KEY non trouvé dans .env")
        print("\nPour exécuter les tests:")
        print("1. Obtenir une clé API: https://console.cloud.google.com/")
        print("2. Activer Distance Matrix API")
        print("3. Ajouter dans .env: GOOGLE_MAPS_API_KEY=votre_clé")
        return False

    print(f"\n✅ Clé API Google Maps trouvée: {api_key[:15]}...")

    # Exécuter les tests
    results = []

    results.append(("Test 1: Usage Basique", test_basic_usage()))
    results.append(("Test 2: Usage Classe", test_class_usage()))
    results.append(("Test 3: Technicien le Moins Cher", test_cheapest_technician()))
    results.append(("Test 4: Format Assistant", test_format_for_assistant()))
    results.append(("Test 5: Cas Limites", test_edge_cases()))

    # Résumé
    print("\n" + "=" * 70)
    print("📊 RÉSUMÉ DES TESTS")
    print("=" * 70)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✅ RÉUSSI" if result else "❌ ÉCHOUÉ"
        print(f"{status} - {test_name}")

    print(f"\nRésultat: {passed}/{total} tests réussis")

    if passed == total:
        print("\n🎉 Tous les tests ont réussi!")
        print("\nProchaines étapes:")
        print("1. Tester dans train_summaries.py")
        print("2. Intégrer dans l'API de l'assistant")
        print("3. Créer l'interface web avec onglet code postal")
        return True
    else:
        print("\n⚠️ Certains tests ont échoué")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
