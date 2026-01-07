#!/usr/bin/env python3
"""
Explorer la structure de allEventServices et comment l'ajouter à un événement
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.gazelle_api_client import GazelleAPIClient

def explore_allEventServices_type():
    """Explorer le type allEventServices"""
    print("="*60)
    print("🔍 EXPLORATION: Type allEventServices")
    print("="*60)
    
    api_client = GazelleAPIClient()
    
    query = """
    query {
        __type(name: "PrivateEvent") {
            name
            fields {
                name
                type {
                    name
                    kind
                    ofType {
                        name
                        kind
                    }
                }
            }
        }
    }
    """
    
    try:
        result = api_client._execute_query(query, {})
        event_type = result.get("data", {}).get("__type", {})
        fields = event_type.get("fields", [])
        
        # Chercher allEventServices
        all_event_services_field = next((f for f in fields if f.get('name') == 'allEventServices'), None)
        
        if all_event_services_field:
            print(f"\n✅ Champ allEventServices trouvé:")
            field_type = all_event_services_field.get('type', {})
            print(f"   Type: {field_type.get('name') or field_type.get('ofType', {}).get('name', 'Unknown')}")
            print(f"   Kind: {field_type.get('kind') or field_type.get('ofType', {}).get('kind', 'Unknown')}")
            
            # Explorer le type de connexion
            connection_type_name = field_type.get('ofType', {}).get('name') or field_type.get('name')
            if connection_type_name:
                explore_connection_type(api_client, connection_type_name)
        else:
            print("\n❌ Champ allEventServices non trouvé")
            
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()

def explore_connection_type(api_client, type_name):
    """Explorer le type de connexion (ex: PrivateEventServicesConnection)"""
    print(f"\n🔍 Exploration du type: {type_name}")
    
    query = """
    query ExploreConnectionType($typeName: String!) {
        __type(name: $typeName) {
            name
            kind
            fields {
                name
                type {
                    name
                    kind
                    ofType {
                        name
                        kind
                    }
                }
            }
        }
    }
    """
    
    try:
        result = api_client._execute_query(query, {"typeName": type_name})
        connection_type = result.get("data", {}).get("__type", {})
        
        if connection_type:
            print(f"   Type: {connection_type.get('name')}")
            print(f"   Kind: {connection_type.get('kind')}")
            fields = connection_type.get("fields", [])
            print(f"   Champs ({len(fields)}):")
            for field in fields:
                print(f"      - {field.get('name')}: {field.get('type', {}).get('name', 'Unknown')}")
        else:
            print(f"   ⚠️  Type {type_name} non trouvé")
            
    except Exception as e:
        print(f"   ⚠️  Erreur: {e}")

def explore_PrivateEventServiceInput():
    """Explorer PrivateEventInput pour voir s'il y a un champ allEventServices"""
    print("\n" + "="*60)
    print("🔍 EXPLORATION: PrivateEventInput - allEventServices")
    print("="*60)
    
    api_client = GazelleAPIClient()
    
    query = """
    query {
        __type(name: "PrivateEventInput") {
            name
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
        event_input_type = result.get("data", {}).get("__type", {})
        input_fields = event_input_type.get("inputFields", [])
        
        # Chercher allEventServices
        all_event_services_field = next((f for f in input_fields if 'service' in f.get('name', '').lower() or 'allEventServices' in f.get('name', '')), None)
        
        if all_event_services_field:
            print(f"\n✅ Champ trouvé: {all_event_services_field.get('name')}")
            field_type = all_event_services_field.get('type', {})
            print(f"   Type: {field_type.get('name') or field_type.get('ofType', {}).get('name', 'Unknown')}")
            
            # Explorer les inputFields du type
            of_type = field_type.get('ofType', {})
            if of_type:
                input_fields_nested = of_type.get('inputFields', [])
                if input_fields_nested:
                    print(f"   Champs disponibles:")
                    for field in input_fields_nested:
                        print(f"      - {field.get('name')}: {field.get('type', {}).get('name', 'Unknown')}")
        else:
            print("\n⚠️  Aucun champ 'service' ou 'allEventServices' trouvé dans PrivateEventInput")
            print("   Les services sont peut-être ajoutés via une mutation séparée")
            
            # Lister tous les champs pour debug
            print("\n   Tous les champs de PrivateEventInput:")
            for field in input_fields:
                name = field.get('name', '')
                if 'piano' in name.lower() or 'service' in name.lower() or 'event' in name.lower():
                    print(f"      - {name}: {field.get('type', {}).get('name', 'Unknown')}")
            
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()

def explore_createEventService_mutation():
    """Chercher une mutation pour créer un EventService"""
    print("\n" + "="*60)
    print("🔍 EXPLORATION: Mutation createEventService")
    print("="*60)
    
    api_client = GazelleAPIClient()
    
    query = """
    query {
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
        result = api_client._execute_query(query, {})
        mutation_type = result.get("data", {}).get("__type", {})
        fields = mutation_type.get("fields", [])
        
        # Chercher les mutations liées aux services d'événement
        service_mutations = [f for f in fields if 'service' in f.get('name', '').lower() and 'event' in f.get('name', '').lower()]
        
        if service_mutations:
            print(f"\n✅ {len(service_mutations)} mutation(s) trouvée(s):\n")
            for mut in service_mutations:
                print(f"   - {mut.get('name')}")
                if mut.get('description'):
                    print(f"     {mut.get('description')[:100]}...")
                args = mut.get('args', [])
                if args:
                    print(f"     Arguments:")
                    for arg in args:
                        print(f"        - {arg.get('name')}: {arg.get('type', {}).get('name', 'Unknown')}")
        else:
            print("\n⚠️  Aucune mutation createEventService trouvée")
            
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()

def main():
    print("🧪 EXPLORATION: Structure allEventServices")
    print("="*60)
    
    api_client = GazelleAPIClient()
    
    # Étape 1: Explorer le type allEventServices
    explore_allEventServices_type()
    
    # Étape 2: Explorer PrivateEventInput pour allEventServices
    explore_PrivateEventServiceInput()
    
    # Étape 3: Chercher une mutation createEventService
    explore_createEventService_mutation()

if __name__ == "__main__":
    main()




