#!/usr/bin/env python3
"""
Test: Créer un événement pour un piano SANS client
"""

import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.gazelle_api_client import GazelleAPIClient

TEST_PIANO_ID = "ins_9H7Mh59SXwEs2JxL"
NICK_TECHNICIAN_ID = "usr_HcCiFk7o0vZ9xAI0"

def test_event_without_client(api_client):
    """Test: Créer un événement sans clientId, seulement avec piano"""
    print("="*60)
    print("🧪 TEST: Créer événement SANS clientId")
    print("="*60)
    
    technician_note = f"Test événement sans client - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    
    mutation = """
    mutation CreateEventWithoutClient($input: PrivateEventInput!) {
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
    
    # Essayer différentes structures pour le champ pianos
    test_cases = [
        {
            "name": "pianos avec pianoId",
            "input": {
                "title": "Service: TUNING",
                "start": datetime.now().isoformat(),
                "type": "APPOINTMENT",
                "status": "ACTIVE",
                "notes": f"TUNING: {technician_note}",
                "userId": NICK_TECHNICIAN_ID,
                "pianos": [{"pianoId": TEST_PIANO_ID}]
            }
        },
        {
            "name": "pianos avec id",
            "input": {
                "title": "Service: TUNING",
                "start": datetime.now().isoformat(),
                "type": "APPOINTMENT",
                "status": "ACTIVE",
                "notes": f"TUNING: {technician_note}",
                "userId": NICK_TECHNICIAN_ID,
                "pianos": [{"id": TEST_PIANO_ID}]
            }
        },
        {
            "name": "pianos avec create",
            "input": {
                "title": "Service: TUNING",
                "start": datetime.now().isoformat(),
                "type": "APPOINTMENT",
                "status": "ACTIVE",
                "notes": f"TUNING: {technician_note}",
                "userId": NICK_TECHNICIAN_ID,
                "pianos": {
                    "create": [{"pianoId": TEST_PIANO_ID}]
                }
            }
        },
        {
            "name": "sans pianos (ajout après)",
            "input": {
                "title": "Service: TUNING",
                "start": datetime.now().isoformat(),
                "type": "APPOINTMENT",
                "status": "ACTIVE",
                "notes": f"TUNING: {technician_note}",
                "userId": NICK_TECHNICIAN_ID
            }
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{'='*60}")
        print(f"Test {i}: {test_case['name']}")
        print(f"{'='*60}")
        
        try:
            result = api_client._execute_query(mutation, {"input": test_case["input"]})
            
            if not result:
                print("❌ Aucune réponse")
                continue
            
            errors = result.get("errors", [])
            if errors:
                print(f"❌ Erreurs GraphQL: {[e.get('message') for e in errors]}")
                continue
            
            create_result = result.get("data", {}).get("createEvent", {})
            mutation_errors = create_result.get("mutationErrors", [])
            
            if mutation_errors:
                error_msgs = []
                for e in mutation_errors:
                    field = e.get('fieldName', '')
                    messages = e.get('messages', [])
                    error_msgs.append(f"{field}: {', '.join(messages)}")
                print(f"❌ Erreurs de mutation: {', '.join(error_msgs)}")
                continue
            
            event = create_result.get("event")
            if not event:
                print("❌ Événement None retourné")
                continue
            
            print(f"✅ Événement créé: {event.get('id')}")
            print(f"   Titre: {event.get('title')}")
            print(f"   Client: {event.get('client', {}).get('companyName', 'AUCUN')}")
            print(f"   Statut: {event.get('status')}")
            
            # Vérifier les pianos associés
            event_pianos = event.get('allEventPianos', {}).get('nodes', [])
            if event_pianos:
                piano_ids = [p.get('piano', {}).get('id') for p in event_pianos if p.get('piano')]
                print(f"   Pianos associés: {piano_ids}")
                if TEST_PIANO_ID in piano_ids:
                    print(f"   ✅ Piano correctement associé!")
                else:
                    print(f"   ⚠️  Piano non trouvé")
            else:
                print(f"   ⚠️  Aucun piano associé")
            
            # Si le test 4 (sans pianos) a réussi, essayer d'ajouter le piano après
            if i == 4 and event:
                print(f"\n   🔄 Tentative d'ajout du piano après création...")
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
                    
                    # Essayer différentes structures pour updateEvent
                    update_inputs = [
                        {"pianos": [{"pianoId": TEST_PIANO_ID}]},
                        {"pianos": [{"id": TEST_PIANO_ID}]},
                        {"pianos": {"create": [{"pianoId": TEST_PIANO_ID}]}},
                    ]
                    
                    for update_input in update_inputs:
                        try:
                            update_result = api_client._execute_query(update_mutation, {
                                "eventId": event.get('id'),
                                "input": update_input
                            })
                            update_data = update_result.get("data", {}).get("updateEvent", {})
                            if update_data.get("event"):
                                print(f"   ✅ Piano ajouté avec succès!")
                                break
                        except Exception as e:
                            print(f"   ⚠️  Erreur: {e}")
                            continue
                except Exception as e:
                    print(f"   ❌ Erreur lors de l'ajout: {e}")
            
            return event  # Retourner le premier événement créé avec succès
            
        except Exception as e:
            print(f"❌ Erreur: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    return None

def main():
    print("🧪 TEST: Événement SANS clientId")
    print("="*60)
    
    api_client = GazelleAPIClient()
    
    event = test_event_without_client(api_client)
    
    print("\n" + "="*60)
    if event:
        print("✅ SUCCÈS: On peut créer un événement sans clientId!")
        print("   L'événement peut être associé directement au piano.")
    else:
        print("❌ ÉCHEC: Impossible de créer un événement sans clientId")
    print("="*60)

if __name__ == "__main__":
    main()




