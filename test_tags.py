#!/usr/bin/env python3
"""
Test pour vérifier si les tags sont disponibles dans l'API Gazelle.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.gazelle_api_client import GazelleAPIClient

VINCENT_DINDY_CLIENT_ID = "cli_9UMLkteep8EsISbG"

def test_tags():
    """Teste si les tags sont disponibles dans l'API Gazelle."""
    client = GazelleAPIClient()

    # Query avec tags (tags est un String)
    query = """
    query GetPianoWithTags($clientId: String!) {
      allPianos(first: 200, filters: { clientId: $clientId }) {
        nodes {
          id
          serialNumber
          make
          location
          tags
        }
      }
    }
    """

    variables = {"clientId": VINCENT_DINDY_CLIENT_ID}

    try:
        result = client._execute_query(query, variables)
        pianos = result.get("data", {}).get("allPianos", {}).get("nodes", [])

        print(f"✅ {len(pianos)} pianos récupérés\n")

        # Chercher spécifiquement les pianos avec tags
        print("=" * 60)
        print("Pianos avec tags:")
        print("=" * 60)

        pianos_avec_tags = []
        for piano in pianos:
            tags = piano.get('tags', '')
            if tags:
                serial = piano.get('serialNumber', 'N/A')
                location = piano.get('location', 'N/A')
                print(f"✓ {serial} @ {location}")
                print(f"  Tags: {tags}")
                print()
                pianos_avec_tags.append(piano)

        if not pianos_avec_tags:
            print("(aucun piano avec tags trouvé)")
        else:
            print(f"\n📊 Total: {len(pianos_avec_tags)} pianos ont des tags")

        # Chercher spécifiquement le piano avec tag "NON"
        print("\n" + "=" * 60)
        print("Recherche des pianos avec le tag 'NON':")
        print("=" * 60)

        found_non = False
        for piano in pianos:
            tags = piano.get('tags', '')

            if tags and 'NON' in tags:
                serial = piano.get('serialNumber', 'N/A')
                location = piano.get('location', 'N/A')
                print(f"✓ Trouvé: {serial} @ {location}")
                print(f"  Tags: {tags}")
                found_non = True

        if not found_non:
            print("(aucun piano avec tag 'NON' trouvé)")

    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return False

    return True

if __name__ == "__main__":
    success = test_tags()
    sys.exit(0 if success else 1)
