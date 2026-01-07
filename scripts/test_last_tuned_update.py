#!/usr/bin/env python3
"""
Test: Vérifier si calculatedLastService est mis à jour après un événement COMPLETE
"""

import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.gazelle_api_client import GazelleAPIClient

TEST_PIANO_ID = "ins_9H7Mh59SXwEs2JxL"
NICK_TECHNICIAN_ID = "usr_HcCiFk7o0vZ9xAI0"

def get_piano_last_service(api_client, piano_id):
    """Récupérer le calculatedLastService du piano"""
    query = """
    query GetPianoLastService($pianoId: String!) {
        piano(id: $pianoId) {
            id
            make
            model
            calculatedLastService
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
            last_service = piano.get("calculatedLastService")
            return last_service, piano
        else:
            return None, None
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return None, None

def test_last_tuned_update(api_client):
    """Test: Créer un événement COMPLETE et vérifier si calculatedLastService est mis à jour"""
    print("="*60)
    print("🧪 TEST: Mise à jour de calculatedLastService")
    print("="*60)
    
    # Étape 1: Récupérer le calculatedLastService AVANT
    print("\n📊 ÉTAPE 1: Récupérer calculatedLastService AVANT")
    last_service_before, piano_before = get_piano_last_service(api_client, TEST_PIANO_ID)
    
    if not piano_before:
        print("❌ Impossible de récupérer le piano")
        return
    
    print(f"✅ Piano trouvé:")
    print(f"   ID: {piano_before.get('id')}")
    print(f"   calculatedLastService AVANT: {last_service_before}")
    
    # Étape 2: Créer un événement et le marquer comme COMPLETE
    print("\n📊 ÉTAPE 2: Créer un événement et le marquer COMPLETE")
    
    technician_note = f"Test mise à jour dernier accord - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    client_id = piano_before.get("client", {}).get("id")
    
    # Créer l'événement
    create_mutation = """
    mutation CreateEvent($input: PrivateEventInput!) {
        createEvent(input: $input) {
            event {
                id
                title
                start
                type
                status
                notes
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
    
    event_input = {
        "title": "Service: TUNING",
        "start": datetime.now().isoformat(),
        "type": "APPOINTMENT",
        "duration": 60,
        "notes": f"TUNING: {technician_note}",
        "userId": NICK_TECHNICIAN_ID,
        "clientId": client_id,
        "pianos": [{"pianoId": TEST_PIANO_ID}]
    }
    
    try:
        result = api_client._execute_query(create_mutation, {"input": event_input})
        create_result = result.get("data", {}).get("createEvent", {})
        mutation_errors = create_result.get("mutationErrors", [])
        
        if mutation_errors:
            error_msgs = []
            for e in mutation_errors:
                field = e.get('fieldName', '')
                messages = e.get('messages', [])
                error_msgs.append(f"{field}: {', '.join(messages)}")
            print(f"❌ Erreurs de mutation: {', '.join(error_msgs)}")
            return
        
        event = create_result.get("event")
        if not event:
            print("❌ Événement None retourné")
            return
        
        event_id = event.get('id')
        print(f"✅ Événement créé: {event_id}")
        
        # Marquer comme COMPLETE
        update_mutation = """
        mutation UpdateEventStatus($eventId: String!, $input: PrivateEventInput!) {
            updateEvent(id: $eventId, input: $input) {
                event {
                    id
                    status
                }
                mutationErrors {
                    fieldName
                    messages
                }
            }
        }
        """
        
        update_result = api_client._execute_query(update_mutation, {
            "eventId": event_id,
            "input": {"status": "COMPLETE"}
        })
        
        update_data = update_result.get("data", {}).get("updateEvent", {})
        if update_data.get("event", {}).get("status") == "COMPLETE":
            print(f"✅ Événement marqué comme COMPLETE")
        else:
            print(f"⚠️  Statut de l'événement: {update_data.get('event', {}).get('status')}")
        
        # Attendre un peu pour que Gazelle mette à jour
        import time
        print("\n⏳ Attente de 2 secondes pour que Gazelle mette à jour...")
        time.sleep(2)
        
        # Étape 3: Vérifier calculatedLastService APRÈS
        print("\n📊 ÉTAPE 3: Vérifier calculatedLastService APRÈS")
        last_service_after, piano_after = get_piano_last_service(api_client, TEST_PIANO_ID)
        
        print(f"   calculatedLastService APRÈS: {last_service_after}")
        
        # Comparer
        print("\n" + "="*60)
        print("📊 RÉSULTAT:")
        print("="*60)
        print(f"   AVANT:  {last_service_before}")
        print(f"   APRÈS: {last_service_after}")
        
        if last_service_after and last_service_after != last_service_before:
            print("\n✅ SUCCÈS: calculatedLastService a été mis à jour!")
            print("   Gazelle met automatiquement à jour ce champ quand un événement est complété.")
        elif last_service_after == last_service_before:
            print("\n⚠️  calculatedLastService n'a pas changé")
            print("   Cela peut signifier:")
            print("   - Le champ est mis à jour de manière asynchrone (attendre plus longtemps)")
            print("   - Le champ nécessite un type d'événement spécifique")
            print("   - Le champ nécessite que l'événement soit 'cédulé' (scheduled) avant d'être complété")
        else:
            print("\n❌ Impossible de récupérer calculatedLastService après")
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()

def main():
    print("🧪 TEST: Mise à jour automatique de calculatedLastService")
    print("="*60)
    
    api_client = GazelleAPIClient()
    
    test_last_tuned_update(api_client)
    
    print("\n" + "="*60)
    print("💡 NOTE: Si calculatedLastService n'est pas mis à jour automatiquement,")
    print("   il faudra peut-être utiliser une mutation updatePiano explicite.")
    print("="*60)

if __name__ == "__main__":
    main()




