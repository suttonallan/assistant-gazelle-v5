#!/usr/bin/env python3
"""
Test: Créer une note de service pour le piano Yamatest via push_technician_service.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.gazelle_api_client import GazelleAPIClient


def main():
    """Créer une note de service pour Yamatest."""
    client = GazelleAPIClient()

    piano_id = "ins_hUTnjvtZc6I6cXxA"
    client_id = "cli_PmqPUBTbPFeCMGmz"  # Orford Musique
    technician_id = "usr_HcCiFk7o0vZ9xAI0"  # Nick
    service_note = "test de entrée de service pour ce piano Yamatest G 24c. 34%"

    print("\n" + "="*70)
    print("TEST: Création de note de service pour Yamatest")
    print("="*70)
    print(f"\nPiano:      {piano_id}")
    print(f"Client:     {client_id}")
    print(f"Technicien: {technician_id}")
    print(f"Note:       {service_note}")
    print("\n" + "="*70 + "\n")

    try:
        event = client.push_technician_service(
            piano_id=piano_id,
            technician_note=service_note,
            service_type="TUNING",
            technician_id=technician_id,
            client_id=client_id
        )

        print(f"\n{'='*70}")
        print("✅ NOTE DE SERVICE CRÉÉE AVEC SUCCÈS")
        print(f"{'='*70}")
        print(f"Événement ID: {event.get('id')}")
        print(f"Titre:        {event.get('title')}")
        print(f"Statut:       {event.get('status')}")
        print(f"Type:         {event.get('type')}")
        print(f"{'='*70}\n")

    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
