#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de test pour vérifier la structure de la mutation GraphQL Gazelle
Avant de pousser des données, ce script teste différentes structures de mutation
pour trouver celle qui fonctionne.
"""

import os
import sys
import json
import requests
from pathlib import Path

# Ajouter le répertoire parent au path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Configuration
API_URL = "https://gazelleapp.io/graphql/private/"
TOKEN_FILE = "data/gazelle_token.json"

# OAuth2 credentials
CLIENT_ID = os.getenv("GAZELLE_CLIENT_ID", "")
CLIENT_SECRET = os.getenv("GAZELLE_CLIENT_SECRET", "")

current_tokens = {}


def load_tokens():
    """Charge les tokens OAuth"""
    token_path = Path(TOKEN_FILE)
    if not token_path.exists():
        print(f"❌ Fichier token introuvable: {TOKEN_FILE}")
        return None

    try:
        with open(token_path, 'r') as f:
            tokens = json.load(f)
            global current_tokens
            current_tokens = tokens
            return tokens
    except Exception as e:
        print(f"❌ Erreur chargement tokens: {e}")
        return None


def refresh_access_token(refresh_token):
    """Rafraîchit le token"""
    data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token"
    }
    try:
        response = requests.post("https://gazelleapp.io/developer/oauth/token", data=data)
        response.raise_for_status()
        new_token_data = response.json()
        if "refresh_token" not in new_token_data:
            new_token_data["refresh_token"] = refresh_token
        global current_tokens
        current_tokens = new_token_data
        return new_token_data
    except Exception as e:
        print(f"❌ Erreur rafraîchissement: {e}")
        return None


def make_api_call(payload):
    """Effectue un appel GraphQL"""
    global current_tokens

    headers = {"Authorization": f"Bearer {current_tokens.get('access_token')}"}

    try:
        response = requests.post(API_URL, json=payload, headers=headers, timeout=60)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            refreshed = refresh_access_token(current_tokens.get('refresh_token'))
            if refreshed:
                return make_api_call(payload)
        return {"error": f"HTTP {e.response.status_code}", "details": e.response.text}
    except Exception as e:
        return {"error": str(e)}


def test_introspection():
    """Teste l'introspection GraphQL pour découvrir les mutations disponibles"""
    print("\n" + "="*60)
    print("🔍 TEST 1: Introspection GraphQL")
    print("="*60)

    query = """
    query IntrospectMutations {
      __schema {
        mutationType {
          name
          fields {
            name
            description
            args {
              name
              type {
                name
                kind
              }
            }
          }
        }
      }
    }
    """

    payload = {"query": query}
    result = make_api_call(payload)

    if "data" in result:
        mutations = result["data"]["__schema"]["mutationType"]["fields"]
        print(f"\n✅ {len(mutations)} mutation(s) trouvée(s):")

        # Chercher les mutations liées à timeline
        timeline_mutations = [m for m in mutations if "timeline" in m["name"].lower() or "entry" in m["name"].lower()]

        if timeline_mutations:
            print("\n📋 Mutations liées à timeline:")
            for mut in timeline_mutations:
                print(f"   - {mut['name']}")
                if mut.get('description'):
                    print(f"     {mut['description']}")
        else:
            print("\n⚠️  Aucune mutation 'timeline' trouvée")
            print("   Mutations disponibles (premières 10):")
            for mut in mutations[:10]:
                print(f"   - {mut['name']}")
    else:
        print("❌ Erreur lors de l'introspection")
        print(json.dumps(result, indent=2))

    return result


def test_timeline_entry_structure():
    """Teste différentes structures pour créer une entrée timeline"""
    print("\n" + "="*60)
    print("🔍 TEST 2: Structure de la mutation createTimelineEntry")
    print("="*60)

    # Essayer différentes variantes de la mutation
    mutations_to_try = [
        # Variante 1: createTimelineEntry
        """
        mutation Test1 {
          __type(name: "CreateTimelineEntryInput") {
            name
            inputFields {
              name
              type {
                name
                kind
              }
            }
          }
        }
        """,
        # Variante 2: addTimelineEntry
        """
        mutation Test2 {
          __type(name: "AddTimelineEntryInput") {
            name
            inputFields {
              name
              type {
                name
                kind
              }
            }
          }
        }
        """,
        # Variante 3: timelineEntry
        """
        mutation Test3 {
          __type(name: "TimelineEntryInput") {
            name
            inputFields {
              name
              type {
                name
                kind
              }
            }
          }
        }
        """
    ]

    for i, mutation in enumerate(mutations_to_try, 1):
        print(f"\n🧪 Test {i}...")
        payload = {"query": mutation}
        result = make_api_call(payload)

        if "data" in result and result["data"].get("__type"):
            type_info = result["data"]["__type"]
            print(f"✅ Type trouvé: {type_info['name']}")
            print("   Champs requis:")
            for field in type_info.get("inputFields", []):
                field_type = field["type"]
                type_name = field_type.get("name") or field_type.get("kind")
                print(f"   - {field['name']}: {type_name}")
        else:
            print("   ❌ Type non trouvé")


def test_existing_timeline_entry():
    """Récupère une entrée timeline existante pour voir sa structure"""
    print("\n" + "="*60)
    print("🔍 TEST 3: Structure d'une TimelineEntry existante")
    print("="*60)

    # D'abord, trouver un piano pour tester
    query = """
    query GetPiano {
      allPianosBatched(first: 1) {
        nodes {
          id
          make
          model
        }
      }
    }
    """

    payload = {"query": query}
    result = make_api_call(payload)

    if "data" in result and result["data"].get("allPianosBatched"):
        pianos = result["data"]["allPianosBatched"].get("nodes", [])
        if pianos:
            piano_id = pianos[0]["id"]
            print(f"✅ Piano trouvé: {piano_id}")

            # Essayer de récupérer les timeline entries de ce piano
            timeline_query = """
            query GetTimelineEntries($pianoId: String!) {
              piano(id: $pianoId) {
                id
                timelineEntries {
                  nodes {
                    id
                    occurredAt
                    entryType
                    title
                    details
                  }
                }
              }
            }
            """

            payload = {
                "query": timeline_query,
                "variables": {"pianoId": piano_id}
            }

            result = make_api_call(payload)

            if "data" in result:
                piano_data = result["data"].get("piano")
                if piano_data:
                    entries = piano_data.get("timelineEntries", {}).get("nodes", [])
                    if entries:
                        print(f"\n✅ {len(entries)} entrée(s) timeline trouvée(s)")
                        print("\n📋 Structure d'une entrée:")
                        entry = entries[0]
                        for key, value in entry.items():
                            print(f"   {key}: {value}")
                    else:
                        print("⚠️  Aucune entrée timeline pour ce piano")
                else:
                    print("❌ Impossible de récupérer les données du piano")
            else:
                print("❌ Erreur lors de la récupération")
                print(json.dumps(result, indent=2))
        else:
            print("❌ Aucun piano trouvé")
    else:
        print("❌ Erreur lors de la recherche de piano")
        print(json.dumps(result, indent=2))


def main():
    """Fonction principale"""
    print("\n" + "="*60)
    print("🧪 TEST STRUCTURE MUTATION GAZELLE")
    print("="*60)

    # Charger les tokens
    if not load_tokens():
        print("\n❌ Impossible de charger les tokens")
        return

    # Test 1: Introspection
    test_introspection()

    # Test 2: Structure de la mutation
    test_timeline_entry_structure()

    # Test 3: Structure existante
    test_existing_timeline_entry()

    print("\n" + "="*60)
    print("✅ Tests terminés")
    print("="*60)
    print("\n💡 Utilisez ces informations pour ajuster le script")
    print("   push_service_history_to_gazelle.py")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Interrompu par l'utilisateur")
    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
