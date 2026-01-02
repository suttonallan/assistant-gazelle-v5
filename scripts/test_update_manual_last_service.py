#!/usr/bin/env python3
"""
Script de test - Mise à jour manuelle de la date de dernier service.

⚠️ NE PAS EXÉCUTER SANS AUTORISATION

Ce script propose une mise à jour de manualLastService pour le piano test d'Allan.

Option: SIMPLE (Option A)
- Met à jour uniquement manualLastService
- N'affecte PAS calculatedLastService automatiquement
- Ne crée PAS de timeline entry
- Ne crée PAS d'événement dans l'historique

Avantages:
- Très simple à implémenter
- Fonctionne immédiatement
- Pas besoin de comprendre les services

Limites:
- Ne respecte pas le workflow Gazelle complet
- calculatedLastService reste à null

Date: 2026-01-01
"""

import sys
import json
from pathlib import Path
from datetime import date

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.gazelle_api_client import GazelleAPIClient


def update_manual_last_service(piano_id: str, service_date: str = None, execute: bool = False):
    """
    Met à jour manualLastService pour un piano.

    Args:
        piano_id: ID du piano
        service_date: Date ISO (YYYY-MM-DD) ou None pour aujourd'hui
        execute: Si True, exécute la mutation. Sinon, affiche seulement.
    """
    client = GazelleAPIClient()

    if not service_date:
        service_date = date.today().isoformat()

    mutation = """
    mutation UpdatePianoManualLastService(
        $pianoId: String!
        $manualLastService: CoreDate!
    ) {
        updatePiano(
            id: $pianoId
            input: {
                manualLastService: $manualLastService
            }
        ) {
            piano {
                id
                manualLastService
                calculatedLastService
                eventLastService
                calculatedNextService
            }
            mutationErrors {
                fieldName
                messages
            }
        }
    }
    """

    variables = {
        "pianoId": piano_id,
        "manualLastService": service_date
    }

    print(f"\n{'='*70}")
    print(f"⚠️  TEST: Mise à jour manuelle de la date de dernier service")
    print(f"   Piano ID: {piano_id}")
    print(f"   Date: {service_date}")
    print(f"{'='*70}\n")

    print("📋 Mutation GraphQL:")
    print("-" * 70)
    print(mutation)
    print("-" * 70)

    print("\n📋 Variables:")
    print("-" * 70)
    print(json.dumps(variables, indent=2))
    print("-" * 70)

    if execute:
        print(f"\n⚠️  EXÉCUTION DE LA MUTATION...")

        try:
            result = client._execute_query(mutation, variables)

            print(f"\n✅ Résultat:")
            print("=" * 70)
            print(json.dumps(result, indent=2))
            print("=" * 70)

            # Vérifier les erreurs
            update_result = result.get("data", {}).get("updatePiano", {})
            mutation_errors = update_result.get("mutationErrors", [])

            if mutation_errors:
                print(f"\n❌ Erreurs lors de la mise à jour:")
                for error in mutation_errors:
                    field = error.get('fieldName', 'Unknown')
                    messages = error.get('messages', [])
                    print(f"   • {field}: {', '.join(messages)}")
                return False

            piano = update_result.get("piano")
            if piano:
                print(f"\n✅ Piano mis à jour avec succès!")
                print(f"\n📊 Dates de service mises à jour:")
                print(f"   manualLastService:     {piano.get('manualLastService')}")
                print(f"   calculatedLastService: {piano.get('calculatedLastService')}")
                print(f"   eventLastService:      {piano.get('eventLastService')}")
                print(f"   calculatedNextService: {piano.get('calculatedNextService')}")

                if piano.get('calculatedLastService') == service_date:
                    print(f"\n🎉 calculatedLastService a été mis à jour automatiquement!")
                else:
                    print(f"\n⚠️  calculatedLastService n'a PAS été mis à jour automatiquement")
                    print(f"   Ceci est attendu avec l'approche manualLastService")

                return True
            else:
                print(f"\n❌ Aucun piano retourné dans la réponse")
                return False

        except Exception as e:
            print(f"\n❌ Erreur lors de l'exécution de la mutation: {e}")
            import traceback
            traceback.print_exc()
            return False

    else:
        print(f"\n{'='*70}")
        print(f"⚠️  MUTATION NON EXÉCUTÉE (Mode Dry-Run)")
        print(f"{'='*70}")
        print(f"\n📝 Pour exécuter cette mutation:")
        print(f"   python3 scripts/test_update_manual_last_service.py --execute")
        print(f"\nOu modifier le code pour passer execute=True")
        return None


def main():
    """Fonction principale."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Teste la mise à jour manuelle de la date de dernier service"
    )
    parser.add_argument(
        '--execute',
        action='store_true',
        help="Exécute réellement la mutation (par défaut: dry-run seulement)"
    )
    parser.add_argument(
        '--piano-id',
        default="ins_9H7Mh59SXwEs2JxL",
        help="ID du piano à mettre à jour (défaut: piano test d'Allan)"
    )
    parser.add_argument(
        '--date',
        default=None,
        help="Date du service (YYYY-MM-DD) (défaut: aujourd'hui)"
    )
    parser.add_argument(
        '--yes',
        action='store_true',
        help="Skip la confirmation (pour scripts automatisés)"
    )

    args = parser.parse_args()

    print("\n" + "="*70)
    print("TEST: Mise à jour manuelle de la date de dernier service")
    print("="*70)

    if args.execute:
        print("\n⚠️  MODE EXÉCUTION ACTIVÉ")
        print("La mutation SERA exécutée sur l'API Gazelle")

        if not args.yes:
            response = input("\nContinuer? (oui/non): ")
            if response.lower() not in ['oui', 'yes', 'y', 'o']:
                print("\n❌ Annulé par l'utilisateur")
                return
        else:
            print("✅ Confirmation automatique (--yes)")

    else:
        print("\n📋 MODE DRY-RUN (Affichage seulement)")
        print("Aucune modification ne sera apportée à Gazelle")

    # Exécuter le test
    result = update_manual_last_service(
        piano_id=args.piano_id,
        service_date=args.date,
        execute=args.execute
    )

    print("\n" + "="*70)
    if result is True:
        print("✅ Test terminé avec succès")
    elif result is False:
        print("❌ Test échoué")
    else:
        print("📋 Dry-run terminé")
    print("="*70 + "\n")


if __name__ == '__main__':
    main()
