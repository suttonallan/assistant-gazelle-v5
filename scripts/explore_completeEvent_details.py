#!/usr/bin/env python3
"""
Explorer en détail les champs de PrivateCompleteEventInput, surtout serviceHistoryNotes
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.gazelle_api_client import GazelleAPIClient

def explore_serviceHistoryNotes():
    """Explorer le type de serviceHistoryNotes"""
    print("="*60)
    print("🔍 EXPLORATION: serviceHistoryNotes")
    print("="*60)
    
    api_client = GazelleAPIClient()
    
    # Essayer de trouver le type
    query = """
    query {
        __type(name: "PrivateCompleteEventInput") {
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
                                ofType {
                                    name
                                    kind
                                }
                            }
                            description
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
        input_fields = input_type.get("inputFields", [])
        
        # Trouver serviceHistoryNotes
        service_history_field = next((f for f in input_fields if f.get('name') == 'serviceHistoryNotes'), None)
        
        if service_history_field:
            print(f"\n✅ Champ serviceHistoryNotes trouvé")
            field_type = service_history_field.get('type', {})
            of_type = field_type.get('ofType', {})
            
            if of_type:
                type_name = of_type.get('name', 'Unknown')
                kind = of_type.get('kind', 'Unknown')
                print(f"   Type: {type_name} ({kind})")
                
                # Explorer les inputFields
                nested_fields = of_type.get('inputFields', [])
                if nested_fields:
                    print(f"\n   Champs disponibles ({len(nested_fields)}):")
                    for field in nested_fields:
                        field_name = field.get('name')
                        field_type_nested = field.get('type', {})
                        type_name_nested = field_type_nested.get('name') or field_type_nested.get('ofType', {}).get('name', 'Unknown')
                        field_desc = field.get('description', '')
                        print(f"      - {field_name}: {type_name_nested}")
                        if field_desc:
                            print(f"        {field_desc[:100]}...")
                else:
                    print(f"   ⚠️  Aucun champ imbriqué (peut-être une liste simple)")
        else:
            print("\n❌ Champ serviceHistoryNotes non trouvé")
            
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()

def explore_scheduledMessages():
    """Explorer scheduledMessages"""
    print("\n" + "="*60)
    print("🔍 EXPLORATION: scheduledMessages")
    print("="*60)
    
    api_client = GazelleAPIClient()
    
    query = """
    query {
        __type(name: "PrivateCompleteEventInput") {
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
                            description
                        }
                    }
                }
            }
        }
    }
    """
    
    try:
        result = api_client._execute_query(query, {})
        input_type = result.get("data", {}).get("__type", {})
        input_fields = input_type.get("inputFields", [])
        
        scheduled_messages_field = next((f for f in input_fields if f.get('name') == 'scheduledMessages'), None)
        
        if scheduled_messages_field:
            print(f"\n✅ Champ scheduledMessages trouvé")
            field_type = scheduled_messages_field.get('type', {})
            of_type = field_type.get('ofType', {})
            
            if of_type:
                type_name = of_type.get('name', 'Unknown')
                print(f"   Type: {type_name}")
                
                nested_fields = of_type.get('inputFields', [])
                if nested_fields:
                    print(f"\n   Champs disponibles:")
                    for field in nested_fields:
                        print(f"      - {field.get('name')}: {field.get('type', {}).get('name', 'Unknown')}")
        else:
            print("\n❌ Champ scheduledMessages non trouvé")
            
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()

def main():
    print("🧪 EXPLORATION: Détails de PrivateCompleteEventInput")
    print("="*60)
    
    api_client = GazelleAPIClient()
    
    explore_serviceHistoryNotes()
    explore_scheduledMessages()
    
    print("\n" + "="*60)
    print("💡 HYPOTHÈSE:")
    print("   Les services sont peut-être gérés via scheduledMessages ou")
    print("   serviceHistoryNotes. Il faut peut-être créer l'événement avec")
    print("   les services dans scheduledMessages, puis les compléter via")
    print("   completeEvent avec serviceHistoryNotes.")
    print("="*60)

if __name__ == "__main__":
    main()

