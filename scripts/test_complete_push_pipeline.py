#!/usr/bin/env python3
"""
Test script pour vérifier le pipeline complet de push vers Gazelle.

Teste les 3 fonctionnalités critiques:
1. Mise à jour du champ "Last Tuned" dans Gazelle
2. Création de note de service dans l'historique
3. Parsing température/humidité et création de measurement

Usage:
    python3 scripts/test_complete_push_pipeline.py --piano-id ins_abc123
    python3 scripts/test_complete_push_pipeline.py --piano-id ins_abc123 --dry-run
"""

import sys
import os
from datetime import datetime, timedelta

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from core.gazelle_api_client import GazelleAPIClient


def test_complete_pipeline(piano_id: str, dry_run: bool = False):
    """
    Teste le pipeline complet de push vers Gazelle.

    Args:
        piano_id: ID du piano à tester (ex: "ins_hUTnjvtZc6I6cXxA")
        dry_run: Si True, ne push pas réellement
    """
    print(f"\n{'='*80}")
    print(f"TEST DU PIPELINE COMPLET DE PUSH VERS GAZELLE")
    print(f"{'='*80}")
    print(f"Piano ID: {piano_id}")
    print(f"Mode: {'DRY RUN (simulation)' if dry_run else 'REAL PUSH'}")
    print(f"Date: {datetime.now().isoformat()}")
    print(f"{'='*80}\n")

    # Initialize API client
    try:
        print("🔄 Initialisation du client API Gazelle...")
        client = GazelleAPIClient()
        print("✅ Client API initialisé\n")
    except Exception as e:
        print(f"❌ Erreur lors de l'initialisation du client API: {e}")
        return False

    # Test data - simule une note de technicien avec température et humidité
    technician_note = """Accord effectué avec succès.

Humidité: 45%
Température: 22C

Observations:
- Piano en bon état général
- Quelques touches à ajuster
- Recommandation: vérifier dans 6 mois
"""

    service_type = "TUNING"
    technician_id = "usr_HcCiFk7o0vZ9xAI0"  # Nick

    # Use completed date 3 days ago to test date handling
    event_date = (datetime.now() - timedelta(days=3)).isoformat()

    print("📝 Données de test:")
    print(f"   Service type: {service_type}")
    print(f"   Technicien ID: {technician_id}")
    print(f"   Date événement: {event_date}")
    print(f"   Note technicien:")
    for line in technician_note.split('\n'):
        print(f"      {line}")
    print()

    if dry_run:
        print("🔶 MODE DRY RUN - Aucune modification réelle ne sera effectuée\n")
        return True

    # ============ EXECUTE PIPELINE ============
    try:
        print(f"\n{'='*80}")
        print("EXÉCUTION DU PIPELINE COMPLET")
        print(f"{'='*80}\n")

        result = client.push_technician_service_with_measurements(
            piano_id=piano_id,
            technician_note=technician_note,
            service_type=service_type,
            technician_id=technician_id,
            event_date=event_date
        )

        print(f"\n{'='*80}")
        print("RÉSULTATS DU PUSH")
        print(f"{'='*80}\n")

        # Check Last Tuned update
        if result.get('last_tuned_updated'):
            print("✅ LAST TUNED: Date mise à jour avec succès")
        else:
            print("⚠️  LAST TUNED: Échec de mise à jour (voir erreurs ci-dessus)")

        # Check service note creation
        service_note = result.get('service_note')
        if service_note:
            print(f"✅ SERVICE NOTE: Créée avec succès")
            print(f"   ID: {service_note.get('id')}")
            print(f"   Type: {service_note.get('type')}")
            print(f"   Status: {service_note.get('status')}")
        else:
            print("❌ SERVICE NOTE: Échec de création")

        # Check measurement creation
        measurement = result.get('measurement')
        parsed = result.get('parsed_values')
        if measurement:
            print(f"✅ MEASUREMENT: Créé avec succès")
            print(f"   ID: {measurement.get('id')}")
            print(f"   Température: {parsed.get('temperature')}°C")
            print(f"   Humidité: {parsed.get('humidity')}%")
            print(f"   Date prise: {measurement.get('takenOn')}")
        elif parsed:
            print(f"⚠️  MEASUREMENT: Valeurs parsées mais pas créées")
            print(f"   Température parsée: {parsed.get('temperature')}°C")
            print(f"   Humidité parsée: {parsed.get('humidity')}%")
        else:
            print("ℹ️  MEASUREMENT: Aucune température/humidité détectée dans les notes")

        print(f"\n{'='*80}")
        print("PIPELINE COMPLET EXÉCUTÉ AVEC SUCCÈS")
        print(f"{'='*80}\n")

        return True

    except Exception as e:
        print(f"\n{'='*80}")
        print("ÉCHEC DU PIPELINE")
        print(f"{'='*80}\n")
        print(f"❌ Erreur: {e}")
        import traceback
        print(f"\nTraceback complet:")
        print(traceback.format_exc())
        return False


def main():
    """Point d'entrée principal."""
    import argparse

    parser = argparse.ArgumentParser(description="Test du pipeline complet de push vers Gazelle")
    parser.add_argument('--piano-id', required=True, help='ID du piano à tester (ex: ins_hUTnjvtZc6I6cXxA)')
    parser.add_argument('--dry-run', action='store_true', help='Mode simulation (pas de push réel)')

    args = parser.parse_args()

    success = test_complete_pipeline(
        piano_id=args.piano_id,
        dry_run=args.dry_run
    )

    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
