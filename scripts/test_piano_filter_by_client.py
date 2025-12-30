#!/usr/bin/env python3
"""
Test du filtrage des pianos par clientId avec le vrai schéma.

Utilise: filters { clientId: "..." }
"""

import sys
import os

# Ajouter le répertoire parent au PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.gazelle_api_client import GazelleAPIClient


def test_piano_filter():
    """Test de filtrage des pianos par client."""

    client = GazelleAPIClient()

    # On va tester avec différents clientId possibles
    # D'abord, essayons de trouver un client "Vincent"

    print("🔍 Étape 1: Rechercher le client Vincent d'Indy dans Gazelle...")
    print("=" * 80)

    # Requête pour chercher tous les clients
    query_search_client = """
    query SearchClient {
      allClients(first: 1000) {
        nodes {
          id
          searchString
          companyName
        }
      }
    }
    """

    try:
        result = client._execute_query(query_search_client)
        clients = result.get("data", {}).get("allClients", {}).get("nodes", [])

        print(f"✅ {len(clients)} clients trouvés")

        # Chercher "Vincent" ou "Indy"
        vincent_clients = [c for c in clients if c.get("searchString") and ("vincent" in c["searchString"].lower() or "indy" in c["searchString"].lower())]

        if vincent_clients:
            print(f"\n✅ Clients correspondants trouvés:")
            for c in vincent_clients:
                print(f"   - {c.get('searchString', 'N/A')} (ID: {c['id']})")

            # Utiliser le premier client trouvé
            vincent_client_id = vincent_clients[0]["id"]
            vincent_client_name = vincent_clients[0].get("searchString", "N/A")

        else:
            print("❌ Aucun client 'Vincent d'Indy' trouvé")
            print("\nPremiers 10 clients:")
            for c in clients[:10]:
                print(f"   - {c.get('searchString', 'N/A')} (ID: {c['id']})")
            return

    except Exception as e:
        print(f"❌ Erreur recherche client: {e}")
        import traceback
        traceback.print_exc()
        return

    # Étape 2: Utiliser le bon filtre
    print(f"\n🔍 Étape 2: Filtrer les pianos pour '{vincent_client_name}' (ID: {vincent_client_id})...")
    print("=" * 80)

    query_pianos = """
    query GetPianosByClient($clientId: String!) {
      allPianos(first: 100, filters: { clientId: $clientId }) {
        nodes {
          id
          serialNumber
          make
          model
          location
          client {
            id
            searchString
          }
        }
      }
    }
    """

    variables = {
        "clientId": vincent_client_id
    }

    try:
        result = client._execute_query(query_pianos, variables)
        pianos = result.get("data", {}).get("allPianos", {}).get("nodes", [])

        print(f"✅ {len(pianos)} pianos trouvés pour ce client!")

        if pianos:
            print(f"\nPremiers 5 pianos:")
            for p in pianos[:5]:
                loc_name = p.get("location", "N/A")
                print(f"   - {p['make']} {p.get('model', '')} (Serial: {p.get('serialNumber', 'N/A')}) @ {loc_name}")

            print(f"\n✅ SUCCESS! La méthode de filtrage est:")
            print(f"   filters: {{ clientId: \"{vincent_client_id}\" }}")

    except Exception as e:
        print(f"❌ Erreur filtrage pianos: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_piano_filter()
