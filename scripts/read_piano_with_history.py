#!/usr/bin/env python3
"""
Lecture complète du piano test d'Allan avec historique des services.

Objectif:
1. Lire le piano ins_9H7Mh59SXwEs2JxL avec tous ses champs
2. Récupérer les timeline entries liées (query séparée)
3. Récupérer les événements liés (query séparée)
4. Analyser la structure pour comprendre comment ajouter des services

Date: 2026-01-01
"""

import sys
import json
from pathlib import Path

# Ajouter le projet au path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.gazelle_api_client import GazelleAPIClient


def read_piano_details(client, piano_id: str):
    """
    Lit les détails du piano.

    Args:
        client: Instance du GazelleAPIClient
        piano_id: ID du piano à lire

    Returns:
        Dictionnaire avec les données du piano
    """
    print(f"\n{'='*70}")
    print(f"📖 LECTURE DU PIANO - Détails")
    print(f"   Piano ID: {piano_id}")
    print(f"{'='*70}\n")

    query = """
    query GetPianoDetails($pianoId: String!) {
        piano(id: $pianoId) {
            id
            make
            model
            serialNumber
            type
            year
            location
            notes
            status
            lifecycleState

            # Client propriétaire
            client {
                id
                companyName
                defaultContact {
                    firstName
                    lastName
                    defaultEmail {
                        email
                    }
                }
            }

            # Dates critiques
            createdAt
            updatedAt
            calculatedLastService
            manualLastService
            eventLastService
            calculatedNextService
            nextServiceOverride

            # Dampp Chaser
            damppChaserInstalled
            damppChaserHumidistatModel
            damppChaserMfgDate

            # Autres infos
            caseColor
            caseFinish
            hasIvory
            serviceIntervalMonths
            rental
            consignment
            useType

            # Prochain accord planifié
            nextTuningScheduled {
                id
                title
                start
                type
                status
            }

            # Tags
            tags
        }
    }
    """

    variables = {"pianoId": piano_id}

    try:
        result = client._execute_query(query, variables)

        if not result:
            print("❌ Aucune réponse reçue")
            return None

        piano = result.get("data", {}).get("piano")

        if not piano:
            print("❌ Piano non trouvé")
            return None

        print("✅ Piano trouvé avec succès!\n")
        print(f"{'='*70}")
        print(f"INFORMATIONS GÉNÉRALES")
        print(f"{'='*70}")
        print(f"ID:              {piano.get('id')}")
        print(f"Marque:          {piano.get('make')}")
        print(f"Modèle:          {piano.get('model')}")
        print(f"Numéro de série: {piano.get('serialNumber')}")
        print(f"Type:            {piano.get('type')}")
        print(f"Année:           {piano.get('year')}")
        print(f"Statut:          {piano.get('status')}")
        print(f"État lifecycle:  {piano.get('lifecycleState')}")
        print(f"Localisation:    {piano.get('location')}")

        # Client propriétaire
        client_data = piano.get('client', {})
        if client_data:
            contact = client_data.get('defaultContact', {})
            email = contact.get('defaultEmail', {}).get('email') if contact.get('defaultEmail') else 'N/A'
            print(f"\nPropriétaire:    {contact.get('firstName', '')} {contact.get('lastName', '')}")
            print(f"Email:           {email}")
            print(f"Client ID:       {client_data.get('id')}")
            print(f"Compagnie:       {client_data.get('companyName')}")

        # Dates critiques
        print(f"\n{'='*70}")
        print(f"⭐ DATES DE SERVICE (CRITIQUES)")
        print(f"{'='*70}")
        print(f"calculatedLastService:  {piano.get('calculatedLastService')}")
        print(f"manualLastService:      {piano.get('manualLastService')}")
        print(f"eventLastService:       {piano.get('eventLastService')}")
        print(f"calculatedNextService:  {piano.get('calculatedNextService')}")
        print(f"nextServiceOverride:    {piano.get('nextServiceOverride')}")
        print(f"serviceIntervalMonths:  {piano.get('serviceIntervalMonths')}")

        # Prochaine session planifiée
        next_tuning = piano.get('nextTuningScheduled')
        if next_tuning:
            print(f"\nProchaine session planifiée:")
            print(f"  ID:     {next_tuning.get('id')}")
            print(f"  Titre:  {next_tuning.get('title')}")
            print(f"  Date:   {next_tuning.get('start')}")
            print(f"  Statut: {next_tuning.get('status')}")

        return piano

    except Exception as e:
        print(f"\n❌ Erreur lors de la lecture du piano: {e}")
        import traceback
        traceback.print_exc()
        return None


def read_piano_timeline_entries(client, piano_id: str):
    """
    Récupère les timeline entries pour un piano.

    Args:
        client: Instance du GazelleAPIClient
        piano_id: ID du piano

    Returns:
        Liste des timeline entries
    """
    print(f"\n{'='*70}")
    print(f"📅 HISTORIQUE DES SERVICES (Timeline Entries)")
    print(f"{'='*70}\n")

    query = """
    query GetPianoTimelineEntries($pianoId: ID) {
        allTimelineEntries(first: 20, pianoId: $pianoId, orderBy: OCCURRED_AT_DESC) {
            edges {
                node {
                    id
                    occurredAt
                    type
                    summary
                    comment
                    user {
                        id
                        firstName
                        lastName
                    }
                    invoice {
                        id
                        number
                    }
                }
            }
        }
    }
    """

    variables = {"pianoId": piano_id}

    try:
        result = client._execute_query(query, variables)

        if not result:
            print("❌ Aucune réponse reçue")
            return []

        edges = result.get("data", {}).get("allTimelineEntries", {}).get("edges", [])
        entries = [edge.get("node") for edge in edges if edge.get("node")]

        if entries:
            print(f"✅ {len(entries)} timeline entries trouvées:\n")
            for idx, entry in enumerate(entries, 1):
                print(f"{idx}. Timeline Entry ID: {entry.get('id')}")
                print(f"   Date:     {entry.get('occurredAt')}")
                print(f"   Type:     {entry.get('type')}")
                print(f"   Résumé:   {entry.get('summary')}")
                if entry.get('comment'):
                    print(f"   Notes:    {entry.get('comment')[:100]}...")

                user = entry.get('user', {})
                if user:
                    print(f"   Technicien: {user.get('firstName', '')} {user.get('lastName', '')}")

                invoice = entry.get('invoice', {})
                if invoice:
                    print(f"   Facture: {invoice.get('number')}")

                print()
        else:
            print("❌ Aucune timeline entry trouvée pour ce piano")

        return entries

    except Exception as e:
        print(f"\n❌ Erreur lors de la lecture des timeline entries: {e}")
        import traceback
        traceback.print_exc()
        return []


def read_piano_events(client, piano_id: str):
    """
    Récupère les événements (RV/Services) pour un piano.

    Args:
        client: Instance du GazelleAPIClient
        piano_id: ID du piano

    Returns:
        Liste des événements
    """
    print(f"\n{'='*70}")
    print(f"📆 ÉVÉNEMENTS (RV/Services)")
    print(f"{'='*70}\n")

    query = """
    query GetPianoEvents($pianoId: ID) {
        allEventsBatched(first: 20, filters: {pianoId: $pianoId}) {
            nodes {
                id
                title
                start
                type
                status
                notes
                user {
                    id
                    firstName
                    lastName
                }
                client {
                    id
                    companyName
                }
                # ⭐ CRUCIAL: Services cochés dans le RV ⭐
                allEventServices(first: 10) {
                    nodes {
                        id
                        masterServiceItem {
                            id
                            name
                            isTuning
                            type
                        }
                        status
                        completedAt
                        notes
                    }
                }
            }
        }
    }
    """

    variables = {"pianoId": piano_id}

    try:
        result = client._execute_query(query, variables)

        if not result:
            print("❌ Aucune réponse reçue")
            return []

        events = result.get("data", {}).get("allEventsBatched", {}).get("nodes", [])

        if events:
            print(f"✅ {len(events)} événements trouvés:\n")
            for idx, event in enumerate(events, 1):
                print(f"{idx}. Événement ID: {event.get('id')}")
                print(f"   Titre:    {event.get('title')}")
                print(f"   Date:     {event.get('start')}")
                print(f"   Type:     {event.get('type')}")
                print(f"   Statut:   {event.get('status')}")
                if event.get('notes'):
                    print(f"   Notes:    {event.get('notes')[:100]}...")

                user = event.get('user', {})
                if user:
                    print(f"   Technicien: {user.get('firstName', '')} {user.get('lastName', '')}")

                # ⭐ SERVICES COCHÉS ⭐
                event_services = event.get('allEventServices', {}).get('nodes', [])
                if event_services:
                    print(f"\n   ⭐ SERVICES COCHÉS DANS CE RV ({len(event_services)}):")
                    for service_idx, service in enumerate(event_services, 1):
                        master_item = service.get('masterServiceItem', {})
                        print(f"      {service_idx}. Service ID: {service.get('id')}")
                        print(f"         Master Service: {master_item.get('id')}")
                        print(f"         Nom: {master_item.get('name')}")
                        print(f"         Type: {master_item.get('type')}")
                        print(f"         Est un Accord (isTuning): {master_item.get('isTuning')}")
                        print(f"         Statut: {service.get('status')}")
                        print(f"         Complété le: {service.get('completedAt')}")
                        if service.get('notes'):
                            print(f"         Notes: {service.get('notes')[:60]}...")

                        # Analyser si c'est un accord complété
                        if master_item.get('isTuning') and service.get('completedAt'):
                            print(f"\n         ✅ C'EST UN ACCORD COMPLÉTÉ!")
                            print(f"         → Ce service devrait avoir mis à jour eventLastService")
                else:
                    print(f"\n   ❌ Aucun service coché dans ce RV")

                print()
        else:
            print("❌ Aucun événement trouvé pour ce piano")

        return events

    except Exception as e:
        print(f"\n❌ Erreur lors de la lecture des événements: {e}")
        import traceback
        traceback.print_exc()
        return []


def main():
    """Fonction principale."""
    print("\n" + "="*70)
    print("TEST: Lecture Complète du Piano Test d'Allan")
    print("="*70)

    # ID du piano test d'Allan
    piano_id = "ins_9H7Mh59SXwEs2JxL"

    # Initialiser le client
    client = GazelleAPIClient()

    # 1. Lire les détails du piano
    piano_data = read_piano_details(client, piano_id)

    if not piano_data:
        print("\n❌ Impossible de continuer sans les données du piano")
        return

    # 2. Lire les timeline entries
    timeline_entries = read_piano_timeline_entries(client, piano_id)

    # 3. Lire les événements avec services
    events = read_piano_events(client, piano_id)

    # 4. Sauvegarder tout dans un fichier JSON
    output_data = {
        "piano": piano_data,
        "timeline_entries": timeline_entries,
        "events": events
    }

    output_file = Path(__file__).parent.parent / 'data' / f'piano_{piano_id}_complete.json'
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    print(f"\n{'='*70}")
    print(f"💾 Données complètes sauvegardées dans:")
    print(f"   {output_file}")
    print(f"{'='*70}\n")

    # 5. Analyser et résumer
    print(f"\n{'='*70}")
    print(f"📊 RÉSUMÉ DE L'ANALYSE")
    print(f"{'='*70}\n")

    print(f"Piano:              {piano_data.get('make')} {piano_data.get('model')}")
    print(f"Propriétaire:       Allan Test Sutton")
    print(f"Statut:             {piano_data.get('status')}")
    print(f"Timeline entries:   {len(timeline_entries)}")
    print(f"Événements:         {len(events)}")

    # Analyser les services
    total_services = 0
    accords_completes = 0

    for event in events:
        event_services = event.get('allEventServices', {}).get('nodes', [])
        total_services += len(event_services)

        for service in event_services:
            master_item = service.get('masterServiceItem', {})
            if master_item.get('isTuning') and service.get('completedAt'):
                accords_completes += 1

    print(f"Services cochés:    {total_services}")
    print(f"Accords complétés:  {accords_completes}")

    # Recommandations
    print(f"\n{'='*70}")
    print(f"💡 RECOMMANDATIONS")
    print(f"{'='*70}\n")

    if accords_completes > 0:
        print("✅ Ce piano a des accords complétés dans son historique!")
        print("   → Examinez le fichier JSON pour voir la structure exacte")
        print("   → Les services sont dans event.allEventServices.nodes")
        print("   → Un accord complété a isTuning=true et completedAt non null")
    else:
        print("⚠️  Ce piano n'a aucun accord complété dans son historique.")
        print("   → Il faut tester avec un autre piano qui a des RV complétés")
        print("   → Ou créer un événement de test avec un service d'accord")

    print(f"\n{'='*70}")
    print(f"✅ Test terminé")
    print(f"{'='*70}\n")


if __name__ == '__main__':
    main()
