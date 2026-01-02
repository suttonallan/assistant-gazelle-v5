#!/usr/bin/env python3
"""
Test: Créer un événement en utilisant le client du piano
"""

import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.gazelle_api_client import GazelleAPIClient

TEST_PIANO_ID = "ins_9H7Mh59SXwEs2JxL"
NICK_TECHNICIAN_ID = "usr_HcCiFk7o0vZ9xAI0"

def get_piano_client(api_client, piano_id):
    """Récupérer le client associé au piano"""
    query = """
    query GetPianoClient($pianoId: String!) {
        piano(id: $pianoId) {
            id
            make
            model
            client {
                id
                companyName
            }
        }
    }
    """
    
    try:
        result = api_client._execute_query(query, {"pianoId": piano_id})
        piano = result.get("data", {}).get("piano", {})
        
        if piano:
            client = piano.get("client", {})
            client_id = client.get("id")
            client_name = client.get("companyName", "N/A")
            
            print(f"✅ Piano trouvé:")
            print(f"   ID: {piano.get('id')}")
            print(f"   Marque: {piano.get('make', 'N/A')}")
            print(f"   Client ID: {client_id}")
            print(f"   Client: {client_name}")
            
            return client_id, client_name
        else:
            print("❌ Piano non trouvé")
            return None, None
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return None, None

def test_event_with_piano_client(api_client, piano_id, client_id):
    """Test: Créer un événement avec le client du piano"""
    print("\n" + "="*60)
    print("🧪 TEST: Créer événement avec client du piano")
    print("="*60)
    
    technician_note = f"Test avec client du piano - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    
    mutation = """
    mutation CreateEventWithPianoClient($input: PrivateEventInput!) {
        createEvent(input: $input) {
            event {
                id
                title
                start
                type
                status
                notes
                client {
                    id
                    companyName
                }
                user {
                    id
                    firstName
                    lastName
                }
                allEventPianos(first: 10) {
                    nodes {
                        piano {
                            id
                            make
                            model
                        }
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
    
    # Essayer avec le champ pianos
    # Note: Ne pas mettre status lors de la création (il sera ACTIVE par défaut)
    # Note: Duration est requis (en minutes)
    event_input = {
        "title": "Service: TUNING",
        "start": datetime.now().isoformat(),
        "type": "APPOINTMENT",
        "duration": 60,  # 1 heure en minutes
        "notes": f"TUNING: {technician_note}",
        "userId": NICK_TECHNICIAN_ID,
        "clientId": client_id,
        "pianos": [{"pianoId": piano_id}]
    }
    
    print(f"\n📝 Paramètres:")
    print(f"   Piano ID: {piano_id}")
    print(f"   Client ID: {client_id}")
    print(f"   Technicien: Nick ({NICK_TECHNICIAN_ID})")
    print(f"   Note: {technician_note}")
    
    try:
        result = api_client._execute_query(mutation, {"input": event_input})
        
        if not result:
            print("❌ Aucune réponse")
            return None
        
        errors = result.get("errors", [])
        if errors:
            print(f"❌ Erreurs GraphQL: {[e.get('message') for e in errors]}")
            return None
        
        create_result = result.get("data", {}).get("createEvent", {})
        mutation_errors = create_result.get("mutationErrors", [])
        
        if mutation_errors:
            error_msgs = []
            for e in mutation_errors:
                field = e.get('fieldName', '')
                messages = e.get('messages', [])
                error_msgs.append(f"{field}: {', '.join(messages)}")
            print(f"❌ Erreurs de mutation: {', '.join(error_msgs)}")
            
            # Si pianos cause une erreur, essayer sans
            if "pianos" in str(error_msgs).lower():
                print("\n   🔄 Tentative sans champ pianos...")
                event_input_no_pianos = {k: v for k, v in event_input.items() if k != "pianos"}
                result = api_client._execute_query(mutation, {"input": event_input_no_pianos})
                create_result = result.get("data", {}).get("createEvent", {})
                mutation_errors = create_result.get("mutationErrors", [])
                
                if mutation_errors:
                    error_msgs = []
                    for e in mutation_errors:
                        field = e.get('fieldName', '')
                        messages = e.get('messages', [])
                        error_msgs.append(f"{field}: {', '.join(messages)}")
                    print(f"❌ Erreurs de mutation (sans pianos): {', '.join(error_msgs)}")
                    return None
        
        event = create_result.get("event")
        if not event:
            print("❌ Événement None retourné")
            return None
        
        print(f"\n✅ Événement créé: {event.get('id')}")
        print(f"   Titre: {event.get('title')}")
        print(f"   Client: {event.get('client', {}).get('companyName', 'N/A')}")
        print(f"   Statut: {event.get('status')}")
        
        # Vérifier les pianos associés
        event_pianos = event.get('allEventPianos', {}).get('nodes', [])
        if event_pianos:
            piano_ids = [p.get('piano', {}).get('id') for p in event_pianos if p.get('piano')]
            print(f"   Pianos associés: {piano_ids}")
            if piano_id in piano_ids:
                print(f"   ✅ Piano correctement associé!")
            else:
                print(f"   ⚠️  Piano non trouvé, tentative d'ajout après création...")
                # Essayer d'ajouter le piano après création
                try:
                    update_mutation = """
                    mutation UpdateEventWithPiano($eventId: String!, $input: PrivateEventInput!) {
                        updateEvent(id: $eventId, input: $input) {
                            event {
                                id
                                allEventPianos(first: 10) {
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
                    
                    # Explorer la structure pour updateEvent
                    # On va utiliser allEventPianos avec create
                    update_input = {
                        "allEventPianos": {
                            "create": [{"pianoId": piano_id}]
                        }
                    }
                    
                    update_result = api_client._execute_query(update_mutation, {
                        "eventId": event.get('id'),
                        "input": update_input
                    })
                    
                    update_data = update_result.get("data", {}).get("updateEvent", {})
                    if update_data.get("event"):
                        print(f"   ✅ Piano ajouté avec succès après création!")
                except Exception as e:
                    print(f"   ⚠️  Erreur lors de l'ajout du piano: {e}")
        else:
            print(f"   ⚠️  Aucun piano associé")
        
        return event
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return None

def main():
    print("🧪 TEST: Événement avec client du piano")
    print("="*60)
    
    api_client = GazelleAPIClient()
    
    # Étape 1: Récupérer le client du piano
    client_id, client_name = get_piano_client(api_client, TEST_PIANO_ID)
    
    if not client_id:
        print("\n❌ Impossible de récupérer le client du piano")
        return
    
    # Étape 2: Créer l'événement avec le client du piano
    event = test_event_with_piano_client(api_client, TEST_PIANO_ID, client_id)
    
    print("\n" + "="*60)
    if event:
        print("✅ SUCCÈS: On peut créer un événement avec le client du piano!")
        print("   Le client est automatiquement récupéré depuis le piano.")
        print("   L'événement peut être associé au piano via allEventPianos.")
    else:
        print("❌ ÉCHEC: Impossible de créer un événement")
    print("="*60)

if __name__ == "__main__":
    main()

