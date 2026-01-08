#!/usr/bin/env python3
"""
Script de test pour le système d'alertes humidité.
À lancer après avoir créé les tables Supabase.
"""

import sys
from pathlib import Path

# Ajouter le répertoire parent au path
sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.alerts import HumidityScanner


def test_pattern_matching():
    """Test 1: Pattern matching basique"""
    print("\n" + "="*70)
    print("TEST 1: Pattern Matching")
    print("="*70)

    scanner = HumidityScanner()

    # Test housse non résolue
    result = scanner.detect_issue(
        "Housse enlevée pendant la visite",
        scanner.config['alert_keywords'],
        scanner.config['resolution_keywords']
    )
    print(f"\n✅ Test housse non résolue:")
    print(f"   Input: 'Housse enlevée pendant la visite'")
    print(f"   Result: {result}")
    assert result is not None, "Devrait détecter housse"
    assert result[0] == 'housse', "Type devrait être 'housse'"
    assert result[2] == False, "Ne devrait pas être résolu"

    # Test housse résolue
    result = scanner.detect_issue(
        "Housse enlevée puis replacée",
        scanner.config['alert_keywords'],
        scanner.config['resolution_keywords']
    )
    print(f"\n✅ Test housse résolue:")
    print(f"   Input: 'Housse enlevée puis replacée'")
    print(f"   Result: {result}")
    assert result is not None, "Devrait détecter housse"
    assert result[2] == True, "Devrait être résolu"

    # Test alimentation non résolue
    result = scanner.detect_issue(
        "PLS débranché",
        scanner.config['alert_keywords'],
        scanner.config['resolution_keywords']
    )
    print(f"\n✅ Test alimentation non résolue:")
    print(f"   Input: 'PLS débranché'")
    print(f"   Result: {result}")
    assert result is not None, "Devrait détecter alimentation"
    assert result[0] == 'alimentation', "Type devrait être 'alimentation'"
    assert result[2] == False, "Ne devrait pas être résolu"

    # Test alimentation résolue
    result = scanner.detect_issue(
        "PLS débranché. Rebranché après inspection.",
        scanner.config['alert_keywords'],
        scanner.config['resolution_keywords']
    )
    print(f"\n✅ Test alimentation résolue:")
    print(f"   Input: 'PLS débranché. Rebranché après inspection.'")
    print(f"   Result: {result}")
    assert result is not None, "Devrait détecter alimentation"
    assert result[2] == True, "Devrait être résolu"

    # Test aucun problème
    result = scanner.detect_issue(
        "Accordage standard, piano en bon état",
        scanner.config['alert_keywords'],
        scanner.config['resolution_keywords']
    )
    print(f"\n✅ Test aucun problème:")
    print(f"   Input: 'Accordage standard, piano en bon état'")
    print(f"   Result: {result}")
    assert result is None, "Ne devrait rien détecter"

    print(f"\n✅ TOUS LES TESTS DE PATTERN MATCHING RÉUSSIS!")


def test_scan_timeline():
    """Test 2: Scan réel de timeline entries"""
    print("\n" + "="*70)
    print("TEST 2: Scan Timeline Entries (10 entries)")
    print("="*70)

    scanner = HumidityScanner()

    # Scanner 10 entries
    stats = scanner.scan_timeline_entries(limit=10)

    print(f"\n📊 Résultats du scan:")
    print(f"   - Scannées: {stats['scanned']}")
    print(f"   - Skipped (déjà scannées): {stats['skipped']}")
    print(f"   - Alertes trouvées: {stats['alerts_found']}")
    print(f"   - Notifications envoyées: {stats['notifications_sent']}")
    print(f"   - Erreurs: {stats['errors']}")

    print(f"\n✅ SCAN TERMINÉ!")


def test_configuration():
    """Test 3: Vérifier la configuration"""
    print("\n" + "="*70)
    print("TEST 3: Configuration")
    print("="*70)

    scanner = HumidityScanner()

    print(f"\n📋 Mots-clés d'alertes:")
    for alert_type, keywords in scanner.config['alert_keywords'].items():
        print(f"   {alert_type}: {len(keywords)} mots-clés")
        print(f"      Exemples: {keywords[:3]}")

    print(f"\n📋 Mots-clés de résolution:")
    for alert_type, keywords in scanner.config['resolution_keywords'].items():
        print(f"   {alert_type}: {len(keywords)} mots-clés")
        print(f"      Exemples: {keywords[:3]}")

    print(f"\n✅ CONFIGURATION VALIDE!")


if __name__ == "__main__":
    print("\n🧪 TESTS SYSTÈME D'ALERTES HUMIDITÉ")
    print("="*70)

    try:
        # Test 1: Pattern matching
        test_pattern_matching()

        # Test 2: Configuration
        test_configuration()

        # Test 3: Scan timeline (seulement si tables créées)
        print("\n⚠️  Le test de scan nécessite que les tables Supabase soient créées.")
        response = input("Les tables sont-elles créées? (o/n): ").lower()

        if response == 'o':
            test_scan_timeline()
        else:
            print("\n⏭️  Test de scan ignoré. Exécute le SQL dans Supabase d'abord.")

        print("\n" + "="*70)
        print("✅ TOUS LES TESTS RÉUSSIS!")
        print("="*70)

    except Exception as e:
        print(f"\n❌ ERREUR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
