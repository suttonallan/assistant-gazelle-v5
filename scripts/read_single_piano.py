#!/usr/bin/env python3
"""
Lit un piano spécifique depuis Gazelle.
"""

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.gazelle_api_client import GazelleAPIClient


def read_piano(piano_id: str):
    """Lit les détails d'un piano."""
    client = GazelleAPIClient()

    query = """
    query GetPiano($pianoId: String!) {
        piano(id: $pianoId) {
            id
            make
            model
            serialNumber
            type
            year
            status
            location
            notes

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

            manualLastService
            calculatedLastService
            eventLastService
            calculatedNextService
            serviceIntervalMonths
        }
    }
    """

    result = client._execute_query(query, {"pianoId": piano_id})
    piano = result.get("data", {}).get("piano")

    if piano:
        print(f"\n{'='*70}")
        print(f"PIANO: {piano.get('id')}")
        print(f"{'='*70}")
        print(f"Marque:          {piano.get('make')}")
        print(f"Modèle:          {piano.get('model')}")
        print(f"Série:           {piano.get('serialNumber')}")
        print(f"Type:            {piano.get('type')}")
        print(f"Année:           {piano.get('year')}")
        print(f"Statut:          {piano.get('status')}")
        print(f"Localisation:    {piano.get('location')}")

        client_data = piano.get('client', {})
        if client_data:
            contact = client_data.get('defaultContact', {})
            email = contact.get('defaultEmail', {}).get('email') if contact.get('defaultEmail') else 'N/A'
            print(f"\nClient ID:       {client_data.get('id')}")
            print(f"Compagnie:       {client_data.get('companyName')}")
            print(f"Contact:         {contact.get('firstName', '')} {contact.get('lastName', '')}")
            print(f"Email:           {email}")

        print(f"\n{'='*70}")
        print(f"DATES DE SERVICE")
        print(f"{'='*70}")
        print(f"manualLastService:     {piano.get('manualLastService')}")
        print(f"calculatedLastService: {piano.get('calculatedLastService')}")
        print(f"eventLastService:      {piano.get('eventLastService')}")
        print(f"calculatedNextService: {piano.get('calculatedNextService')}")
        print(f"serviceIntervalMonths: {piano.get('serviceIntervalMonths')}")
        print()

    return piano


if __name__ == '__main__':
    import sys
    piano_id = sys.argv[1] if len(sys.argv) > 1 else "ins_9H7Mh59SXwEs2JxL"
    read_piano(piano_id)
