#!/usr/bin/env python3
"""
Explorer comment créer des notes d'historique de service dans Gazelle.

Objectif: Trouver comment créer une note visible dans l'historique du piano,
différente de 'notes' du piano et de timeline entries.
"""

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.gazelle_api_client import GazelleAPIClient


def explore_piano_service_history():
    """Explore les champs liés à l'historique de service."""
    client = GazelleAPIClient()

    # Introspection pour trouver les types liés aux services
    query = """
    query {
        __schema {
            types {
                name
                kind
            }
        }
    }
    """

    result = client._execute_query(query)
    types = result.get("data", {}).get("__schema", {}).get("types", [])

    print(f"\n{'='*70}")
    print("TYPES LIÉS AUX SERVICES/NOTES")
    print(f"{'='*70}\n")

    service_types = [
        t for t in types
        if any(keyword in t.get("name", "").lower()
               for keyword in ["service", "note", "history", "event"])
        and t.get("kind") in ["OBJECT", "INPUT_OBJECT"]
    ]

    for t in sorted(service_types, key=lambda x: x.get("name", "")):
        print(f"  • {t.get('name')} ({t.get('kind')})")

    print()


def explore_completeEvent_input():
    """Explore PrivateCompleteEventInput pour voir si on peut y mettre des notes."""
    client = GazelleAPIClient()

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
                    }
                }
                description
            }
        }
    }
    """

    result = client._execute_query(query)
    type_info = result.get("data", {}).get("__type")

    if not type_info:
        print("❌ PrivateCompleteEventInput non trouvé")
        return

    print(f"\n{'='*70}")
    print("STRUCTURE DE PrivateCompleteEventInput")
    print(f"{'='*70}\n")

    input_fields = type_info.get("inputFields", [])

    for field in input_fields:
        field_name = field.get("name")
        field_type = field.get("type", {})
        type_name = field_type.get("name") or field_type.get("ofType", {}).get("name")
        description = field.get("description", "")

        marker = "⭐" if any(kw in field_name.lower() for kw in ["note", "service", "history"]) else " "
        print(f"{marker} {field_name:30} : {type_name}")
        if description:
            print(f"  {'':30}   {description[:100]}")

    print()


def explore_event_fields():
    """Explore les champs disponibles sur PrivateEvent."""
    client = GazelleAPIClient()

    query = """
    query {
        __type(name: "PrivateEvent") {
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

    result = client._execute_query(query)
    type_info = result.get("data", {}).get("__type")

    if not type_info:
        print("❌ PrivateEvent non trouvé")
        return

    print(f"\n{'='*70}")
    print("CHAMPS SUR PrivateEvent LIÉS AUX NOTES/SERVICES")
    print(f"{'='*70}\n")

    fields = type_info.get("fields", [])

    for field in fields:
        field_name = field.get("name")
        if any(kw in field_name.lower() for kw in ["note", "service", "history", "message"]):
            field_type = field.get("type", {})
            type_name = field_type.get("name") or field_type.get("ofType", {}).get("name")
            print(f"  ⭐ {field_name:30} : {type_name}")

    print()


def test_complete_event_with_notes():
    """Teste la mutation completeEvent avec serviceHistoryNotes."""
    client = GazelleAPIClient()

    # D'abord, créer un événement simple
    print(f"\n{'='*70}")
    print("TEST: Créer un événement puis le compléter avec des notes")
    print(f"{'='*70}\n")

    # Créer l'événement
    create_mutation = """
    mutation CreateTestEvent($input: PrivateEventInput!) {
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

    from datetime import datetime

    event_input = {
        "title": "Test Service Note - Yamatest",
        "start": datetime.now().isoformat(),
        "duration": 60,
        "type": "APPOINTMENT",
        "userId": "usr_HcCiFk7o0vZ9xAI0",  # Nick
        "clientId": "cli_PmqPUBTbPFeCMGmz"  # Orford Musique
    }

    print("📝 Création de l'événement...")
    create_result = client._execute_query(create_mutation, {"input": event_input})

    create_data = create_result.get("data", {}).get("createEvent", {})
    mutation_errors = create_data.get("mutationErrors", [])

    if mutation_errors:
        print("❌ Erreurs lors de la création:")
        for error in mutation_errors:
            print(f"   • {error.get('fieldName')}: {error.get('messages')}")
        return None

    event = create_data.get("event")
    if not event:
        print("❌ Aucun événement créé")
        return None

    event_id = event.get("id")
    print(f"✅ Événement créé: {event_id}")

    # Maintenant essayer de le compléter avec des notes
    print(f"\n📝 Tentative de complétion avec serviceHistoryNotes...")

    complete_mutation = """
    mutation CompleteEventWithNotes(
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
        "serviceHistoryNotes": "test de entrée de service pour ce piano Yamatest G 24c. 34%"
    }

    try:
        complete_result = client._execute_query(complete_mutation, {
            "eventId": event_id,
            "input": complete_input
        })

        print("✅ Mutation completeEvent exécutée")
        print(json.dumps(complete_result, indent=2))

        return event_id

    except Exception as e:
        print(f"❌ Erreur: {e}")
        return event_id


def main():
    """Fonction principale."""
    print("\n" + "="*70)
    print("EXPLORATION: Notes d'Historique de Service")
    print("="*70)

    # 1. Explorer les types disponibles
    explore_piano_service_history()

    # 2. Explorer PrivateCompleteEventInput
    explore_completeEvent_input()

    # 3. Explorer les champs sur PrivateEvent
    explore_event_fields()

    # 4. Tester completeEvent avec serviceHistoryNotes
    print("\n" + "="*70)
    print("VOULEZ-VOUS TESTER completeEvent AVEC serviceHistoryNotes?")
    print("="*70)
    print("\nCeci va créer un événement de test pour le piano Yamatest.")
    response = input("\nContinuer? (oui/non): ")

    if response.lower() in ['oui', 'yes', 'y', 'o']:
        event_id = test_complete_event_with_notes()
        if event_id:
            print(f"\n✅ Test terminé. Événement créé: {event_id}")
            print("Vérifiez dans Gazelle si la note apparaît dans l'historique du service.")
    else:
        print("\n❌ Test annulé")

    print("\n" + "="*70)
    print("✅ Exploration terminée")
    print("="*70 + "\n")


if __name__ == '__main__':
    main()
