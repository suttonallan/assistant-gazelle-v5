#!/usr/bin/env python3
"""
Script d'exploration pour trouver les bonnes mutations GraphQL Gazelle
pour créer des timeline entries et mettre à jour les pianos.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.gazelle_api_client import GazelleAPIClient

TEST_PIANO_ID = "ins_9H7Mh59SXwEs2JxL"
TECHNICIAN_ID = "usr_ofYggsCDt2JAVeNP"

def test_introspection():
    """Test: Introspection GraphQL pour voir les mutations disponibles"""
    print("\n" + "="*60)
    print("🔍 EXPLORATION: Mutations disponibles")
    print("="*60)
    
    api_client = GazelleAPIClient()
    
    # Introspection query pour voir les mutations
    introspection_query = """
    query IntrospectMutations {
        __type(name: "PrivateMutation") {
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
    """
    
    try:
        result = api_client._execute_query(introspection_query)
        mutation_type = result.get("data", {}).get("__type", {})
        fields = mutation_type.get("fields", [])
        
        print(f"\n✅ Mutations disponibles ({len(fields)}):")
        for field in fields:
            print(f"   - {field.get('name')}")
            if 'timeline' in field.get('name', '').lower() or 'piano' in field.get('name', '').lower():
                print(f"     ⭐ {field.get('description', 'Pas de description')}")
                args = field.get('args', [])
                if args:
                    print(f"     Arguments:")
                    for arg in args:
                        print(f"       - {arg.get('name')}: {arg.get('type', {}).get('name', 'N/A')}")
    except Exception as e:
        print(f"❌ Erreur introspection: {e}")

def test_timeline_variants():
    """Test différentes variantes de mutations timeline"""
    print("\n" + "="*60)
    print("🧪 TEST: Variantes de mutations timeline")
    print("="*60)
    
    api_client = GazelleAPIClient()
    
    variants = [
        # Variante 1: createTimelineEntry (actuelle)
        {
            "name": "createTimelineEntry",
            "mutation": """
            mutation CreateTimelineEntry($pianoId: ID!, $summary: String!) {
                createTimelineEntry(pianoId: $pianoId, summary: $summary) {
                    id
                }
            }
            """,
            "variables": {"pianoId": TEST_PIANO_ID, "summary": "Test"}
        },
        # Variante 2: addTimelineEntry
        {
            "name": "addTimelineEntry",
            "mutation": """
            mutation AddTimelineEntry($pianoId: ID!, $summary: String!) {
                addTimelineEntry(pianoId: $pianoId, summary: $summary) {
                    id
                }
            }
            """,
            "variables": {"pianoId": TEST_PIANO_ID, "summary": "Test"}
        },
        # Variante 3: createServiceNote
        {
            "name": "createServiceNote",
            "mutation": """
            mutation CreateServiceNote($pianoId: ID!, $note: String!) {
                createServiceNote(pianoId: $pianoId, note: $note) {
                    id
                }
            }
            """,
            "variables": {"pianoId": TEST_PIANO_ID, "note": "Test"}
        },
    ]
    
    for variant in variants:
        print(f"\n📝 Test: {variant['name']}")
        try:
            result = api_client._execute_query(variant['mutation'], variant['variables'])
            print(f"   ✅ SUCCÈS! Résultat: {result}")
            return variant
        except Exception as e:
            error_msg = str(e)
            if "doesn't exist" in error_msg:
                print(f"   ❌ Mutation n'existe pas")
            else:
                print(f"   ⚠️  Erreur: {error_msg[:100]}")
    
    return None

def test_update_piano_variants():
    """Test différentes variantes de mutations updatePiano"""
    print("\n" + "="*60)
    print("🧪 TEST: Variantes de mutations updatePiano")
    print("="*60)
    
    api_client = GazelleAPIClient()
    
    # D'abord, voir la structure de updatePiano
    introspection = """
    query IntrospectUpdatePiano {
        __type(name: "PrivateMutation") {
            fields(includeDeprecated: true) {
                name
                args {
                    name
                    type {
                        name
                        kind
                        inputFields {
                            name
                            type {
                                name
                            }
                        }
                    }
                }
            }
        }
    }
    """
    
    try:
        result = api_client._execute_query(introspection)
        mutations = result.get("data", {}).get("__type", {}).get("fields", [])
        
        update_piano = None
        for mut in mutations:
            if mut.get('name') == 'updatePiano':
                update_piano = mut
                break
        
        if update_piano:
            print(f"\n✅ Structure de updatePiano trouvée:")
            args = update_piano.get('args', [])
            for arg in args:
                print(f"   Argument: {arg.get('name')}")
                arg_type = arg.get('type', {})
                if arg_type.get('kind') == 'INPUT_OBJECT':
                    input_fields = arg_type.get('inputFields', [])
                    print(f"   Champs disponibles:")
                    for field in input_fields:
                        print(f"     - {field.get('name')}: {field.get('type', {}).get('name', 'N/A')}")
    except Exception as e:
        print(f"❌ Erreur introspection: {e}")

def main():
    print("🔍 EXPLORATION DES MUTATIONS GAZELLE")
    print("="*60)
    
    api_client = GazelleAPIClient()
    
    # Test 1: Introspection
    test_introspection()
    
    # Test 2: Variantes timeline
    test_timeline_variants()
    
    # Test 3: Variantes updatePiano
    test_update_piano_variants()
    
    print("\n" + "="*60)
    print("✅ EXPLORATION TERMINÉE")
    print("="*60)
    print("\n💡 PROCHAINES ÉTAPES:")
    print("   1. Identifier la bonne mutation depuis l'introspection")
    print("   2. Tester avec la structure correcte")
    print("   3. Vérifier si ça fonctionne avec piano inactif")

if __name__ == "__main__":
    main()



