#!/usr/bin/env python3
"""
Charge TOUS les pianos Vincent d'Indy directement depuis Gazelle.

Client ID confirmé: cli_9UMLkteep8EsISbG (École Vincent-d'Indy)
"""

import sys
import os

# Ajouter le répertoire parent au PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.gazelle_api_client import GazelleAPIClient


# ID du client Vincent d'Indy trouvé via introspection
VINCENT_DINDY_CLIENT_ID = "cli_9UMLkteep8EsISbG"


def load_pianos_from_gazelle():
    """Charge tous les pianos Vincent d'Indy depuis Gazelle."""

    client = GazelleAPIClient()

    print("🎹 Chargement des pianos Vincent d'Indy depuis Gazelle...")
    print(f"   Client ID: {VINCENT_DINDY_CLIENT_ID}")
    print("=" * 80)

    query = """
    query GetVincentDIndyPianos($clientId: String!) {
      allPianos(first: 200, filters: { clientId: $clientId }) {
        nodes {
          id
          serialNumber
          make
          model
          location
          type
          status
          notes
          calculatedLastService
          calculatedNextService
          serviceIntervalMonths
        }
      }
    }
    """

    variables = {
        "clientId": VINCENT_DINDY_CLIENT_ID
    }

    try:
        result = client._execute_query(query, variables)
        pianos = result.get("data", {}).get("allPianos", {}).get("nodes", [])

        print(f"✅ {len(pianos)} pianos chargés!\n")

        # Grouper par status
        active_pianos = [p for p in pianos if p.get("status") == "ACTIVE"]
        other_pianos = [p for p in pianos if p.get("status") != "ACTIVE"]

        print(f"📊 Statistiques:")
        print(f"   - Actifs: {len(active_pianos)}")
        print(f"   - Autres statuts: {len(other_pianos)}")

        print(f"\n🎹 Premiers 10 pianos actifs:")
        for i, p in enumerate(active_pianos[:10], 1):
            location = p.get("location", "N/A")
            serial = p.get("serialNumber", "N/A")
            make = p.get("make", "?")
            model = p.get("model", "")
            last_service = p.get("calculatedLastService", "Jamais")

            print(f"{i:2d}. {make} {model}")
            print(f"    ID: {p['id']}")
            print(f"    Serial: {serial}")
            print(f"    Local: {location}")
            print(f"    Dernier accord: {last_service}")
            print()

        # Comparaison avec CSV
        print("\n📋 Comparaison avec le CSV...")
        csv_path = "/Users/allansutton/Documents/assistant-gazelle-v5/api/data/pianos_vincent_dindy.csv"

        try:
            import csv
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                csv_pianos = list(reader)

            print(f"   - Pianos dans CSV: {len(csv_pianos)}")
            print(f"   - Pianos dans Gazelle (actifs): {len(active_pianos)}")
            print(f"   - Pianos dans Gazelle (tous): {len(pianos)}")

            if len(active_pianos) >= len(csv_pianos):
                print(f"\n✅ Gazelle a PLUS de pianos que le CSV!")
                print(f"   → Le CSV peut maintenant être ÉLIMINÉ")
                print(f"   → Utiliser Gazelle comme source unique de vérité")
            else:
                print(f"\n⚠️  Gazelle a MOINS de pianos actifs que le CSV")
                print(f"   → Investiguer pourquoi certains pianos manquent")

        except Exception as e:
            print(f"   ⚠️  Impossible de lire le CSV: {e}")

        return pianos

    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return []


if __name__ == "__main__":
    pianos = load_pianos_from_gazelle()

    if pianos:
        print(f"\n" + "=" * 80)
        print(f"✅ CONCLUSION: Méthode de chargement trouvée!")
        print(f"   Query: allPianos")
        print(f"   Filter: {{ clientId: \"{VINCENT_DINDY_CLIENT_ID}\" }}")
        print(f"   Résultat: {len(pianos)} pianos")
        sys.exit(0)
    else:
        print(f"\n❌ Échec du chargement")
        sys.exit(1)
