#!/usr/bin/env python3
"""
Explorer comment associer des services (Master Service Items) à un événement
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.gazelle_api_client import GazelleAPIClient

def explore_event_structure():
    """Explorer la structure d'un événement pour voir les services"""
    print("="*60)
    print("🔍 EXPLORATION: Structure d'un événement avec services")
    print("="*60)
    
    api_client = GazelleAPIClient()
    
    # Récupérer des événements existants via get_appointments
    try:
        events = api_client.get_appointments(limit=5)
        
        print(f"\n✅ {len(events)} événement(s) récupéré(s)\n")
        
        for event in events[:3]:  # Limiter à 3 pour l'affichage
            print(f"📅 Événement: {event.get('title')} ({event.get('id')})")
            print(f"   Type: {event.get('type')}, Statut: {event.get('status')}")
            
            # Services associés - explorer la structure
            all_event_services = event.get('allEventServices')
            if all_event_services:
                if isinstance(all_event_services, dict):
                    services = all_event_services.get('nodes', [])
                elif isinstance(all_event_services, list):
                    services = all_event_services
                else:
                    services = []
                
                if services:
                    print(f"   Services associés ({len(services)}):")
                    for service in services[:3]:  # Limiter à 3 services
                        if isinstance(service, dict):
                            service_item = service.get('masterServiceItem', {})
                            if service_item:
                                name = service_item.get('name', {})
                                if isinstance(name, dict):
                                    name_fr = name.get('fr_CA', name.get('fr', 'N/A'))
                                else:
                                    name_fr = str(name)
                                is_tuning = service_item.get('isTuning', False)
                                status = service.get('status', 'N/A')
                                completed = service.get('completedAt', 'N/A')
                                print(f"      - {name_fr} (isTuning: {is_tuning}, Status: {status}, Completed: {completed})")
                            else:
                                print(f"      - Service: {service}")
                        else:
                            print(f"      - {service}")
                else:
                    print(f"   ⚠️  Aucun service dans allEventServices")
            else:
                print(f"   ⚠️  Champ allEventServices absent ou vide")
                # Afficher toutes les clés pour debug
                print(f"   Clés disponibles: {list(event.keys())[:10]}")
            
            print()
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()

def explore_event_input_services():
    """Explorer PrivateEventInput pour voir comment ajouter des services"""
    print("\n" + "="*60)
    print("🔍 EXPLORATION: PrivateEventInput - Services")
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
        
        # Chercher les champs liés aux services
        service_fields = [f for f in input_fields if 'service' in f.get('name', '').lower()]
        
        if service_fields:
            print("\n✅ Champs liés aux services trouvés:")
            for field in service_fields:
                print(f"   - {field.get('name')}: {field.get('type', {}).get('name', 'Unknown')}")
                if field.get('description'):
                    print(f"     {field.get('description')}")
        else:
            print("\n⚠️  Aucun champ 'service' trouvé dans PrivateEventInput")
            print("   Les services sont peut-être ajoutés via une mutation séparée")
        
        # Chercher allEventServices
        all_event_services_fields = [f for f in input_fields if 'allEventServices' in f.get('name', '')]
        if all_event_services_fields:
            print("\n✅ Champs allEventServices trouvés:")
            for field in all_event_services_fields:
                print(f"   - {field.get('name')}: {field.get('type', {}).get('name', 'Unknown')}")
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()

def find_tuning_service(api_client):
    """Trouver le service 'Accord' (isTuning: true)"""
    print("\n" + "="*60)
    print("🔍 RECHERCHE: Service 'Accord' (isTuning)")
    print("="*60)
    
    try:
        products = api_client.get_products(limit=100)
        
        tuning_services = [p for p in products if p.get('isTuning', False)]
        
        if tuning_services:
            print(f"\n✅ {len(tuning_services)} service(s) d'accord trouvé(s):\n")
            for service in tuning_services[:5]:  # Afficher les 5 premiers
                name_fr = service.get('name_fr', 'N/A')
                service_id = service.get('id')
                print(f"   - {name_fr} (ID: {service_id})")
            
            return tuning_services[0] if tuning_services else None
        else:
            print("\n⚠️  Aucun service d'accord trouvé")
            return None
            
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return None

def main():
    print("🧪 EXPLORATION: Services dans les événements")
    print("="*60)
    
    api_client = GazelleAPIClient()
    
    # Étape 1: Explorer la structure d'un événement avec services
    explore_event_structure()
    
    # Étape 2: Explorer PrivateEventInput pour les services
    explore_event_input_services()
    
    # Étape 3: Trouver le service 'Accord'
    tuning_service = find_tuning_service(api_client)
    
    if tuning_service:
        print(f"\n💡 Service 'Accord' trouvé: {tuning_service.get('id')}")
        print("   Ce service devra être associé à l'événement et marqué comme complété")

if __name__ == "__main__":
    main()

