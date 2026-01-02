#!/usr/bin/env python3
"""
Script pour explorer la structure de PrivateEventInput dans Gazelle
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.gazelle_api_client import GazelleAPIClient

def explore_event_input():
    """Explorer la structure de PrivateEventInput"""
    print("="*60)
    print("🔍 EXPLORATION: Structure de PrivateEventInput")
    print("="*60)
    
    api_client = GazelleAPIClient()
    
    # Requête pour obtenir le schéma de PrivateEventInput
    query = """
    query {
        __type(name: "PrivateEventInput") {
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
    """
    
    try:
        result = api_client._execute_query(query, {})
        event_input_type = result.get("data", {}).get("__type", {})
        
        if not event_input_type:
            print("❌ Type PrivateEventInput non trouvé")
            return
        
        print(f"\n✅ Type trouvé: {event_input_type.get('name')}")
        print(f"   Kind: {event_input_type.get('kind')}")
        
        input_fields = event_input_type.get("inputFields", [])
        print(f"\n📋 {len(input_fields)} champs disponibles:\n")
        
        required_fields = []
        optional_fields = []
        
        for field in input_fields:
            field_name = field.get("name")
            field_type = field.get("type", {})
            type_name = field_type.get("name") or field_type.get("ofType", {}).get("name", "Unknown")
            kind = field_type.get("kind") or field_type.get("ofType", {}).get("kind", "Unknown")
            is_required = "!" in str(field_type) or kind == "NON_NULL"
            description = field.get("description", "")
            
            field_info = {
                "name": field_name,
                "type": type_name,
                "kind": kind,
                "required": is_required,
                "description": description
            }
            
            if is_required:
                required_fields.append(field_info)
            else:
                optional_fields.append(field_info)
        
        print("🔴 CHAMPS REQUIS:")
        for field in required_fields:
            print(f"   - {field['name']}: {field['type']} ({field['kind']})")
            if field['description']:
                print(f"     {field['description']}")
        
        print("\n🟢 CHAMPS OPTIONNELS:")
        for field in optional_fields:
            print(f"   - {field['name']}: {field['type']} ({field['kind']})")
            if field['description']:
                print(f"     {field['description']}")
        
        # Vérifier spécifiquement si clientId est requis
        print("\n" + "="*60)
        print("🔍 VÉRIFICATION: clientId")
        print("="*60)
        
        client_field = next((f for f in input_fields if f.get("name") == "clientId"), None)
        if client_field:
            client_type = client_field.get("type", {})
            is_required = "!" in str(client_type) or client_type.get("kind") == "NON_NULL"
            print(f"   clientId trouvé: {'REQUIS' if is_required else 'OPTIONNEL'}")
            print(f"   Type: {client_type.get('name') or client_type.get('ofType', {}).get('name', 'Unknown')}")
        else:
            print("   ⚠️  clientId non trouvé dans les champs")
        
        # Vérifier allEventPianos
        print("\n🔍 VÉRIFICATION: allEventPianos")
        print("="*60)
        
        pianos_field = next((f for f in input_fields if f.get("name") == "allEventPianos"), None)
        if pianos_field:
            pianos_type = pianos_field.get("type", {})
            is_required = "!" in str(pianos_type) or pianos_type.get("kind") == "NON_NULL"
            print(f"   allEventPianos trouvé: {'REQUIS' if is_required else 'OPTIONNEL'}")
            print(f"   Type: {pianos_type.get('name') or pianos_type.get('ofType', {}).get('name', 'Unknown')}")
        else:
            print("   ⚠️  allEventPianos non trouvé dans les champs")
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    explore_event_input()

