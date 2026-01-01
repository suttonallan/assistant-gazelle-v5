#!/usr/bin/env python3
"""
Script pour supprimer le piano de test dans Gazelle.

Piano à supprimer:
- ID: ins_iEoxy3WdsYMBU9q1
- Nom: "Test Créé"
- Client: Vincent d'Indy
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.gazelle_api_client import GazelleAPIClient


def delete_test_piano():
    """Supprime le piano de test."""

    TEST_PIANO_ID = "ins_iEoxy3WdsYMBU9q1"

    print("=" * 80)
    print("SUPPRESSION DU PIANO DE TEST")
    print("=" * 80)
    print()
    print(f"Piano ID: {TEST_PIANO_ID}")
    print(f"Nom: Test Créé")
    print()

    # Demander confirmation
    confirmation = input("⚠️  Êtes-vous sûr de vouloir supprimer ce piano? (oui/non): ").strip().lower()

    if confirmation != 'oui':
        print("❌ Suppression annulée")
        return False

    print()
    print("🔧 Connexion à l'API Gazelle...")

    try:
        client = GazelleAPIClient()

        # Mutation pour supprimer le piano
        mutation = """
        mutation DeleteTestPiano($id: String!) {
          deletePiano(id: $id) {
            isDeleted
            mutationErrors {
              fieldName
              messages
            }
          }
        }
        """

        variables = {"id": TEST_PIANO_ID}

        print(f"🗑️  Suppression du piano {TEST_PIANO_ID}...")

        result = client._execute_query(mutation, variables)

        # Vérifier le résultat
        delete_result = result.get("data", {}).get("deletePiano", {})
        is_deleted = delete_result.get("isDeleted")
        mutation_errors = delete_result.get("mutationErrors", [])

        if is_deleted:
            print("✅ Piano supprimé avec succès!")
            print()
            print("📋 Prochaines étapes:")
            print("1. Le piano n'apparaîtra plus dans l'API Gazelle")
            print("2. Il disparaîtra automatiquement du dashboard Vincent d'Indy")
            print("3. Aucune action supplémentaire nécessaire")
            return True
        else:
            print(f"❌ Échec de la suppression")
            if mutation_errors:
                print("Erreurs:")
                for err in mutation_errors:
                    field = err.get('fieldName', 'N/A')
                    msgs = err.get('messages', [])
                    print(f"  - Champ '{field}': {', '.join(msgs)}")
            return False

    except Exception as e:
        print(f"❌ Erreur lors de la suppression: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = delete_test_piano()
    sys.exit(0 if success else 1)
