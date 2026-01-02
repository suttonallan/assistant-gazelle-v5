#!/usr/bin/env python3
"""
Explorer la mutation completeEvent pour voir si on peut spécifier un service
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.gazelle_api_client import GazelleAPIClient

def explore_completeEvent():
    """Explorer la mutation completeEvent"""
    print("="*60)
    print("🔍 EXPLORATION: Mutation completeEvent")
    print("="*60)
    
    api_client = GazelleAPIClient()
    
    query = """
    query {
        __type(name: "PrivateMutation") {
            fields(includeDeprecated: true) {
                name
                description
                args {
                    name
                    type {
                        name
                        kind
                        ofType {
                            name
                            kind
                            inputFields {
                                name
                                type {
                                    name
                                    kind
                                }
                                description
                            }
                        }
                    }
                    description
                }
            }
        }
    }
    """
    
    try:
        result = api_client._execute_query(query, {})
        mutation_type = result.get("data", {}).get("__type", {})
        fields = mutation_type.get("fields", [])
        
        # Chercher completeEvent
        complete_event = next((f for f in fields if f.get('name') == 'completeEvent'), None)
        
        if complete_event:
            print(f"\n✅ Mutation completeEvent trouvée")
            if complete_event.get('description'):
                print(f"   Description: {complete_event.get('description')}")
            
            args = complete_event.get('args', [])
            if args:
                print(f"\n   Arguments ({len(args)}):")
                for arg in args:
                    arg_name = arg.get('name')
                    arg_type = arg.get('type', {})
                    type_name = arg_type.get('name') or arg_type.get('ofType', {}).get('name', 'Unknown')
                    print(f"      - {arg_name}: {type_name}")
                    
                    # Explorer les inputFields si c'est un INPUT_OBJECT
                    of_type = arg_type.get('ofType', {})
                    if of_type and of_type.get('kind') == 'INPUT_OBJECT':
                        input_fields = of_type.get('inputFields', [])
                        if input_fields:
                            print(f"        Champs disponibles:")
                            for field in input_fields:
                                field_name = field.get('name')
                                field_type_name = field.get('type', {}).get('name', 'Unknown')
                                field_desc = field.get('description', '')
                                print(f"          - {field_name}: {field_type_name}")
                                if field_desc:
                                    print(f"            {field_desc[:80]}...")
        else:
            print("\n❌ Mutation completeEvent non trouvée")
            
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()

def explore_PrivateCompleteEventInput():
    """Explorer PrivateCompleteEventInput"""
    print("\n" + "="*60)
    print("🔍 EXPLORATION: PrivateCompleteEventInput")
    print("="*60)
    
    api_client = GazelleAPIClient()
    
    query = """
    query {
        __type(name: "PrivateCompleteEventInput") {
            name
            kind
            inputFields {
                name
                type {
                    name
                    kind
                    ofType {
                        name
                        kind
                        inputFields {
                            name
                            type {
                                name
                                kind
                            }
                        }
                    }
                }
                description
            }
        }
    }
    """
    
    try:
        result = api_client._execute_query(query, {})
        input_type = result.get("data", {}).get("__type", {})
        
        if input_type:
            print(f"\n✅ Type trouvé: {input_type.get('name')}")
            input_fields = input_type.get("inputFields", [])
            
            if input_fields:
                print(f"\n   Champs disponibles ({len(input_fields)}):")
                for field in input_fields:
                    field_name = field.get('name')
                    field_type = field.get('type', {})
                    type_name = field_type.get('name') or field_type.get('ofType', {}).get('name', 'Unknown')
                    field_desc = field.get('description', '')
                    print(f"      - {field_name}: {type_name}")
                    if field_desc:
                        print(f"        {field_desc[:100]}...")
                    
                    # Explorer les inputFields imbriqués
                    of_type = field_type.get('ofType', {})
                    if of_type and of_type.get('kind') == 'INPUT_OBJECT':
                        nested_fields = of_type.get('inputFields', [])
                        if nested_fields:
                            print(f"        Champs imbriqués:")
                            for nested in nested_fields:
                                print(f"          - {nested.get('name')}: {nested.get('type', {}).get('name', 'Unknown')}")
            else:
                print("\n   ⚠️  Aucun champ trouvé")
        else:
            print("\n❌ Type PrivateCompleteEventInput non trouvé")
            
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()

def main():
    print("🧪 EXPLORATION: completeEvent")
    print("="*60)
    
    api_client = GazelleAPIClient()
    
    explore_completeEvent()
    explore_PrivateCompleteEventInput()

if __name__ == "__main__":
    main()

