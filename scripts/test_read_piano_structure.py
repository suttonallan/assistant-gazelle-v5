#!/usr/bin/env python3
"""
Test de lecture du piano test d'Allan pour analyser la structure complète.

Objectif:
1. Récupérer le piano ins_9H7Mh59SXwEs2JxL
2. Analyser où se trouve l'historique des services
3. Identifier les champs pour ajouter des entrées
4. Valider la connexion

Date: 2026-01-01
"""

import sys
import json
from pathlib import Path

# Ajouter le projet au path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.gazelle_api_client import GazelleAPIClient


def read_piano_full_structure(piano_id: str):
    """
    Lit la structure complète d'un piano avec tous les champs possibles.

    Args:
        piano_id: ID du piano à lire
    """
    client = GazelleAPIClient()

    print(f"\n{'='*70}")
    print(f"📖 LECTURE DU PIANO - Structure Complète")
    print(f"   Piano ID: {piano_id}")
    print(f"{'='*70}\n")

    # Query exhaustive pour récupérer TOUS les champs possibles
    query = """
    query GetPianoFullStructure($pianoId: String!) {
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

            # Client propriétaire
            client {
                id
                companyName
                defaultContact {
                    firstName
                    lastName
                }
            }

            # Dates
            createdAt
            updatedAt

            # Dampp Chaser
            damppChaserInstalled
            damppChaserHumidistatModel
            damppChaserMfgDate

            # ⭐ Champs critiques pour les services ⭐
            calculatedLastService

            # ⭐ Historique des services (Timeline Entries) ⭐
            allTimelineEntries(first: 10, orderBy: OCCURRED_AT_DESC) {
                nodes {
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

            # ⭐ Événements associés (RV/Services) ⭐
            allEventPianos(first: 10) {
                nodes {
                    event {
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
                        # ⭐ CRITIQUE: Services cochés dans le RV ⭐
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

            # Mesures
            allPianoMeasurements(first: 5, orderBy: CREATED_AT_DESC) {
                nodes {
                    id
                    createdAt
                    temperature
                    humidity
                    notes
                }
            }

            # Photos
            allPianoPhotos(first: 5) {
                nodes {
                    id
                    url
                    createdAt
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
            return None

        piano = result.get("data", {}).get("piano")

        if not piano:
            print("❌ Piano non trouvé")
            print(f"Réponse complète: {json.dumps(result, indent=2)}")
            return None

        # Afficher les informations principales
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
        print(f"Localisation:    {piano.get('location')}")

        # Client propriétaire
        client_data = piano.get('client', {})
        if client_data:
            contact = client_data.get('defaultContact', {})
            print(f"\nPropriétaire:    {contact.get('firstName', '')} {contact.get('lastName', '')}")
            print(f"Client ID:       {client_data.get('id')}")
            print(f"Compagnie:       {client_data.get('companyName')}")

        # Dates
        print(f"\nCréé le:         {piano.get('createdAt')}")
        print(f"Modifié le:      {piano.get('updatedAt')}")

        # ⭐ CHAMP CRITIQUE ⭐
        print(f"\n{'='*70}")
        print(f"⭐ DERNIER SERVICE (calculatedLastService)")
        print(f"{'='*70}")
        print(f"calculatedLastService: {piano.get('calculatedLastService')}")

        # Timeline Entries (historique)
        print(f"\n{'='*70}")
        print(f"📅 HISTORIQUE DES SERVICES (Timeline Entries)")
        print(f"{'='*70}")
        timeline_entries = piano.get('allTimelineEntries', {}).get('nodes', [])
        if timeline_entries:
            for idx, entry in enumerate(timeline_entries, 1):
                print(f"\n{idx}. Timeline Entry ID: {entry.get('id')}")
                print(f"   Date:     {entry.get('occurredAt')}")
                print(f"   Type:     {entry.get('type')}")
                print(f"   Résumé:   {entry.get('summary')}")
                print(f"   Notes:    {entry.get('comment', 'N/A')}")
                user = entry.get('user', {})
                if user:
                    print(f"   Technicien: {user.get('firstName', '')} {user.get('lastName', '')}")
        else:
            print("Aucune timeline entry trouvée")

        # Événements (RV/Services)
        print(f"\n{'='*70}")
        print(f"📆 ÉVÉNEMENTS ASSOCIÉS (RV/Services)")
        print(f"{'='*70}")
        event_pianos = piano.get('allEventPianos', {}).get('nodes', [])
        if event_pianos:
            for idx, event_piano in enumerate(event_pianos, 1):
                event = event_piano.get('event', {})
                print(f"\n{idx}. Événement ID: {event.get('id')}")
                print(f"   Titre:    {event.get('title')}")
                print(f"   Date:     {event.get('start')}")
                print(f"   Type:     {event.get('type')}")
                print(f"   Statut:   {event.get('status')}")
                print(f"   Notes:    {event.get('notes', 'N/A')[:100]}...")

                user = event.get('user', {})
                if user:
                    print(f"   Technicien: {user.get('firstName', '')} {user.get('lastName', '')}")

                # ⭐ SERVICES COCHÉS DANS LE RV ⭐
                event_services = event.get('allEventServices', {}).get('nodes', [])
                if event_services:
                    print(f"\n   ⭐ Services cochés dans ce RV:")
                    for service_idx, service in enumerate(event_services, 1):
                        master_item = service.get('masterServiceItem', {})
                        print(f"      {service_idx}. Service ID: {service.get('id')}")
                        print(f"         Master Service: {master_item.get('name')}")
                        print(f"         Type: {master_item.get('type')}")
                        print(f"         Est un Accord (isTuning): {master_item.get('isTuning')}")
                        print(f"         Statut: {service.get('status')}")
                        print(f"         Complété le: {service.get('completedAt')}")
                        print(f"         Notes: {service.get('notes', 'N/A')}")
                else:
                    print(f"   ❌ Aucun service coché dans ce RV")
        else:
            print("Aucun événement trouvé")

        # Mesures
        print(f"\n{'='*70}")
        print(f"🌡️  MESURES (Température/Humidité)")
        print(f"{'='*70}")
        measurements = piano.get('allPianoMeasurements', {}).get('nodes', [])
        if measurements:
            for idx, measurement in enumerate(measurements, 1):
                print(f"\n{idx}. Mesure ID: {measurement.get('id')}")
                print(f"   Date:        {measurement.get('createdAt')}")
                print(f"   Température: {measurement.get('temperature')}°C")
                print(f"   Humidité:    {measurement.get('humidity')}%")
                print(f"   Notes:       {measurement.get('notes', 'N/A')}")
        else:
            print("Aucune mesure trouvée")

        # Sauvegarder la structure complète en JSON
        output_file = Path(__file__).parent.parent / 'data' / f'piano_{piano_id}_structure.json'
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(piano, f, indent=2, ensure_ascii=False)

        print(f"\n{'='*70}")
        print(f"💾 Structure complète sauvegardée dans:")
        print(f"   {output_file}")
        print(f"{'='*70}\n")

        # Retourner le piano pour analyse ultérieure
        return piano

    except Exception as e:
        print(f"\n❌ Erreur lors de la lecture du piano: {e}")
        import traceback
        traceback.print_exc()
        return None


def analyze_service_structure(piano_data: dict):
    """
    Analyse la structure pour identifier comment ajouter des services.

    Args:
        piano_data: Données du piano récupérées
    """
    if not piano_data:
        print("❌ Aucune donnée piano à analyser")
        return

    print(f"\n{'='*70}")
    print(f"🔍 ANALYSE - Comment ajouter des services")
    print(f"{'='*70}\n")

    # Vérifier si le piano a des événements avec services
    event_pianos = piano_data.get('allEventPianos', {}).get('nodes', [])

    if not event_pianos:
        print("⚠️  Ce piano n'a aucun événement avec services.")
        print("   Impossible d'analyser la structure des services.")
        print("\n📝 RECOMMANDATIONS:")
        print("   1. Trouver un piano avec des événements complétés (services cochés)")
        print("   2. Lire ce piano pour voir la structure des allEventServices")
        print("   3. Comprendre comment les services sont stockés et marqués comme complétés")
        return

    # Analyser les événements avec services
    services_found = False

    for event_piano in event_pianos:
        event = event_piano.get('event', {})
        event_services = event.get('allEventServices', {}).get('nodes', [])

        if event_services:
            services_found = True
            print(f"✅ Événement trouvé avec services: {event.get('id')}")
            print(f"   Titre: {event.get('title')}")
            print(f"   Statut: {event.get('status')}")
            print(f"   Nombre de services: {len(event_services)}")

            for service in event_services:
                master_item = service.get('masterServiceItem', {})
                print(f"\n   📋 Service:")
                print(f"      ID: {service.get('id')}")
                print(f"      Master Service ID: {master_item.get('id')}")
                print(f"      Nom: {master_item.get('name')}")
                print(f"      Type: {master_item.get('type')}")
                print(f"      isTuning: {master_item.get('isTuning')}")
                print(f"      Statut: {service.get('status')}")
                print(f"      Complété le: {service.get('completedAt')}")

                # Analyser si c'est un accord complété
                if master_item.get('isTuning') and service.get('completedAt'):
                    print(f"\n      ⭐ C'EST UN ACCORD COMPLÉTÉ!")
                    print(f"      → Cet événement devrait avoir mis à jour calculatedLastService")

    if not services_found:
        print("⚠️  Aucun service trouvé dans les événements de ce piano.")
        print("\n📝 Pour comprendre comment ajouter des services:")
        print("   1. Chercher un piano avec un RV complété qui a un accord coché")
        print("   2. Analyser la structure de ses allEventServices")
        print("   3. Identifier la mutation pour créer/ajouter des services à un événement")


def main():
    """Fonction principale."""
    print("\n" + "="*70)
    print("TEST: Lecture du Piano Test d'Allan - Analyse de Structure")
    print("="*70)

    # ID du piano test d'Allan
    piano_id = "ins_9H7Mh59SXwEs2JxL"

    # Lire la structure complète
    piano_data = read_piano_full_structure(piano_id)

    # Analyser la structure pour comprendre comment ajouter des services
    analyze_service_structure(piano_data)

    print("\n" + "="*70)
    print("✅ Test terminé")
    print("="*70 + "\n")


if __name__ == '__main__':
    main()
