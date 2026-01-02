#!/usr/bin/env python3
"""
Créer une note d'historique de service pour un piano via completeEvent.

Ce script:
1. Crée un événement APPOINTMENT pour le piano
2. Associe le piano à l'événement
3. Complète l'événement avec serviceHistoryNotes
"""

import sys
import json
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.gazelle_api_client import GazelleAPIClient


def create_service_note_for_piano(
    piano_id: str,
    client_id: str,
    service_note: str,
    technician_id: str = "usr_HcCiFk7o0vZ9xAI0",  # Nick par défaut
    service_date: str = None
):
    """
    Crée une note d'historique de service pour un piano.

    Args:
        piano_id: ID du piano
        client_id: ID du client propriétaire
        service_note: Note de service à enregistrer
        technician_id: ID du technicien
        service_date: Date ISO ou None pour maintenant
    """
    client = GazelleAPIClient()

    if not service_date:
        service_date = datetime.now().isoformat()

    print(f"\n{'='*70}")
    print(f"CRÉATION DE NOTE D'HISTORIQUE DE SERVICE")
    print(f"{'='*70}")
    print(f"Piano:      {piano_id}")
    print(f"Client:     {client_id}")
    print(f"Technicien: {technician_id}")
    print(f"Date:       {service_date}")
    print(f"Note:       {service_note}")
    print(f"{'='*70}\n")

    # Étape 1: Créer l'événement
    print("📝 Étape 1/3: Création de l'événement...")

    create_mutation = """
    mutation CreateServiceEvent($input: PrivateEventInput!) {
        createEvent(input: $input) {
            event {
                id
                title
                start
                type
                status
            }
            mutationErrors {
                fieldName
                messages
            }
        }
    }
    """

    event_input = {
        "title": "Service Piano",
        "start": service_date,
        "duration": 60,
        "type": "APPOINTMENT",
        "userId": technician_id,
        "clientId": client_id
    }

    create_result = client._execute_query(create_mutation, {"input": event_input})
    create_data = create_result.get("data", {}).get("createEvent", {})
    mutation_errors = create_data.get("mutationErrors", [])

    if mutation_errors:
        print("❌ Erreurs lors de la création:")
        for error in mutation_errors:
            print(f"   • {error.get('fieldName')}: {error.get('messages')}")
        return False

    event = create_data.get("event")
    if not event:
        print("❌ Aucun événement créé")
        return False

    event_id = event.get("id")
    print(f"✅ Événement créé: {event_id}")

    # Étape 2: Associer le piano à l'événement via updateEvent
    print(f"\n📝 Étape 2/3: Association du piano à l'événement...")

    update_mutation = """
    mutation UpdateEventWithPiano(
        $eventId: String!
        $input: PrivateEventInput!
    ) {
        updateEvent(id: $eventId, input: $input) {
            event {
                id
                allEventPianos(first: 10) {
                    nodes {
                        piano {
                            id
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

    update_input = {
        "allEventPianos": {
            "create": [{"pianoId": piano_id}]
        }
    }

    update_result = client._execute_query(update_mutation, {
        "eventId": event_id,
        "input": update_input
    })

    update_data = update_result.get("data", {}).get("updateEvent", {})
    mutation_errors = update_data.get("mutationErrors", [])

    if mutation_errors:
        print("⚠️  Erreurs lors de l'association du piano:")
        for error in mutation_errors:
            print(f"   • {error.get('fieldName')}: {error.get('messages')}")
        # Continuer quand même
    else:
        print(f"✅ Piano associé à l'événement")

    # Étape 3: Compléter l'événement avec serviceHistoryNotes
    print(f"\n📝 Étape 3/3: Complétion avec note d'historique de service...")

    complete_mutation = """
    mutation CompleteEventWithServiceNote(
        $eventId: String!
        $input: PrivateCompleteEventInput!
    ) {
        completeEvent(id: $eventId, input: $input) {
            event {
                id
                status
                notes
            }
            mutationErrors {
                fieldName
                messages
            }
        }
    }
    """

    complete_input = {
        "serviceHistoryNotes": [
            {
                "pianoId": piano_id,
                "notes": service_note
            }
        ]
    }

    try:
        complete_result = client._execute_query(complete_mutation, {
            "eventId": event_id,
            "input": complete_input
        })

        complete_data = complete_result.get("data", {}).get("completeEvent", {})
        mutation_errors = complete_data.get("mutationErrors", [])

        if mutation_errors:
            print("❌ Erreurs lors de la complétion:")
            for error in mutation_errors:
                print(f"   • {error.get('fieldName')}: {error.get('messages')}")
            return False

        completed_event = complete_data.get("event")
        if completed_event:
            print(f"✅ Événement complété avec succès!")
            print(f"   ID: {completed_event.get('id')}")
            print(f"   Statut: {completed_event.get('status')}")

            print(f"\n{'='*70}")
            print(f"✅ NOTE D'HISTORIQUE DE SERVICE CRÉÉE")
            print(f"{'='*70}")
            print(f"Événement: {event_id}")
            print(f"Piano:     {piano_id}")
            print(f"Note:      {service_note}")
            print(f"{'='*70}\n")

            return True
        else:
            print("❌ Aucun événement retourné après complétion")
            return False

    except Exception as e:
        print(f"❌ Erreur lors de la complétion: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Fonction principale."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Créer une note d'historique de service pour un piano"
    )
    parser.add_argument(
        '--piano-id',
        required=True,
        help="ID du piano"
    )
    parser.add_argument(
        '--client-id',
        required=True,
        help="ID du client propriétaire"
    )
    parser.add_argument(
        '--note',
        required=True,
        help="Note de service à enregistrer"
    )
    parser.add_argument(
        '--technician-id',
        default="usr_HcCiFk7o0vZ9xAI0",
        help="ID du technicien (défaut: Nick)"
    )
    parser.add_argument(
        '--date',
        default=None,
        help="Date du service (YYYY-MM-DD) (défaut: maintenant)"
    )
    parser.add_argument(
        '--yes',
        action='store_true',
        help="Skip la confirmation"
    )

    args = parser.parse_args()

    print("\n" + "="*70)
    print("CRÉATION DE NOTE D'HISTORIQUE DE SERVICE")
    print("="*70)

    if not args.yes:
        print(f"\nPiano:      {args.piano_id}")
        print(f"Client:     {args.client_id}")
        print(f"Note:       {args.note}")
        response = input("\nContinuer? (oui/non): ")
        if response.lower() not in ['oui', 'yes', 'y', 'o']:
            print("\n❌ Annulé")
            return

    result = create_service_note_for_piano(
        piano_id=args.piano_id,
        client_id=args.client_id,
        service_note=args.note,
        technician_id=args.technician_id,
        service_date=args.date
    )

    print("\n" + "="*70)
    if result:
        print("✅ Note créée avec succès")
    else:
        print("❌ Échec de la création")
    print("="*70 + "\n")


if __name__ == '__main__':
    main()
