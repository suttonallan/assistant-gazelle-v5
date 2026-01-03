#!/usr/bin/env python3
"""
Test: Créer un événement avec un service 'Accord' et le marquer comme complété
"""

import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.gazelle_api_client import GazelleAPIClient

TEST_PIANO_ID = "ins_9H7Mh59SXwEs2JxL"
NICK_TECHNICIAN_ID = "usr_HcCiFk7o0vZ9xAI0"

def get_tuning_service(api_client):
    """Trouver le service 'Accord' (isTuning: true)"""
    try:
        products = api_client.get_products(limit=100)
        tuning_services = [p for p in products if p.get('isTuning', False)]
        
        if tuning_services:
            # Prendre le premier service d'accord simple
            for service in tuning_services:
                name_fr = service.get('name_fr', '').lower()
                if 'accord' in name_fr and 'entretien' not in name_fr:
                    return service
            
            # Sinon, prendre le premier
            return tuning_services[0]
        return None
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return None

def get_piano_client(api_client, piano_id):
    """Récupérer le client du piano"""
    query = """
    query GetPianoClient($pianoId: String!) {
        piano(id: $pianoId) {
            id
            client {
                id
            }
        }
    }
    """
    
    try:
        result = api_client._execute_query(query, {"pianoId": piano_id})
        piano = result.get("data", {}).get("piano", {})
        return piano.get("client", {}).get("id") if piano else None
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return None

def explore_event_service_mutations():
    """Explorer les mutations disponibles pour les services d'événement"""
    print("="*60)
    print("🔍 EXPLORATION: Mutations pour Event Services")
    print("="*60)
    
    api_client = GazelleAPIClient()
    
    query = """
    query {
        __schema {
            mutationType {
                fields {
                    name
                    description
                }
            }
        }
    }
    """
    
    try:
        result = api_client._execute_query(query, {})
        mutations = result.get("data", {}).get("__schema", {}).get("mutationType", {}).get("fields", [])
        
        # Chercher les mutations liées aux services d'événement
        service_mutations = [m for m in mutations if 'service' in m.get('name', '').lower() or 'event' in m.get('name', '').lower()]
        
        print(f"\n✅ {len(service_mutations)} mutation(s) liée(s) aux services/événements:\n")
        for mut in service_mutations[:20]:  # Limiter à 20
            print(f"   - {mut.get('name')}")
            if mut.get('description'):
                print(f"     {mut.get('description')[:80]}...")
        
        return service_mutations
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return []

def test_create_event_with_service(api_client, piano_id, client_id, service_id):
    """Test: Créer un événement avec un service"""
    print("\n" + "="*60)
    print("🧪 TEST: Créer événement avec service 'Accord'")
    print("="*60)
    
    # Étape 1: Créer l'événement
    create_mutation = """
    mutation CreateEvent($input: PrivateEventInput!) {
        createEvent(input: $input) {
            event {
                id
                title
                status
                allEventPianos(first: 5) {
                    nodes {
                        piano { id }
                    }
                }
            }
            mutationErrors {
                fieldName
                messages
            }
        }
    }
    """
    
    event_input = {
        "title": "Service: Accord",
        "start": datetime.now().isoformat(),
        "type": "APPOINTMENT",
        "duration": 60,
        "notes": "Test avec service Accord",
        "userId": NICK_TECHNICIAN_ID,
        "clientId": client_id,
        "pianos": [{"pianoId": piano_id}]
    }
    
    try:
        result = api_client._execute_query(create_mutation, {"input": event_input})
        create_result = result.get("data", {}).get("createEvent", {})
        mutation_errors = create_result.get("mutationErrors", [])
        
        if mutation_errors:
            error_msgs = [f"{e.get('fieldName')}: {', '.join(e.get('messages', []))}" for e in mutation_errors]
            print(f"❌ Erreurs: {', '.join(error_msgs)}")
            return None
        
        event = create_result.get("event")
        if not event:
            print("❌ Événement None")
            return None
        
        event_id = event.get('id')
        print(f"✅ Événement créé: {event_id}")
        
        # Étape 2: Explorer comment ajouter le service
        print(f"\n🔍 Exploration: Comment ajouter le service {service_id} à l'événement?")
        
        # Chercher une mutation createEventService ou similaire
        explore_event_service_mutations()
        
        return event_id
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return None

def main():
    print("🧪 TEST: Événement avec service 'Accord'")
    print("="*60)
    
    api_client = GazelleAPIClient()
    
    # Étape 1: Trouver le service 'Accord'
    print("\n📋 ÉTAPE 1: Trouver le service 'Accord'")
    tuning_service = get_tuning_service(api_client)
    
    if not tuning_service:
        print("❌ Service 'Accord' non trouvé")
        return
    
    service_id = tuning_service.get('id')
    service_name = tuning_service.get('name_fr', 'N/A')
    print(f"✅ Service trouvé: {service_name} (ID: {service_id})")
    
    # Étape 2: Récupérer le client du piano
    print("\n📋 ÉTAPE 2: Récupérer le client du piano")
    client_id = get_piano_client(api_client, TEST_PIANO_ID)
    
    if not client_id:
        print("❌ Client non trouvé")
        return
    
    print(f"✅ Client trouvé: {client_id}")
    
    # Étape 3: Créer l'événement et explorer comment ajouter le service
    event_id = test_create_event_with_service(api_client, TEST_PIANO_ID, client_id, service_id)
    
    if event_id:
        print(f"\n💡 Prochaines étapes:")
        print(f"   1. Trouver la mutation pour ajouter le service {service_id} à l'événement {event_id}")
        print(f"   2. Marquer le service comme complété")
        print(f"   3. Vérifier si calculatedLastService est mis à jour")

if __name__ == "__main__":
    main()



