#!/usr/bin/env python3
"""
Script d'exploration du schéma GraphQL de Gazelle pour les pianos.
Objectif: Identifier tous les champs disponibles et leurs types exacts.
"""

import sys
import os
from pathlib import Path

# Ajouter le répertoire racine au path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.gazelle_api_client import GazelleAPIClient

def explore_piano_schema():
    """Explore le schéma des pianos dans Gazelle."""

    client = GazelleAPIClient()

    # Requête pour récupérer quelques pianos avec TOUS les champs possibles
    query = """
    query ExplorePianoSchema {
        allPianos(first: 100) {
            nodes {
                id
                client {
                    id
                }
                make
                model
                serialNumber
                type
                year
                location
                notes
                damppChaserInstalled
                damppChaserHumidistatModel
                damppChaserMfgDate
                referenceId
                tags
            }
        }
    }
    """

    print("🔍 Exploration du schéma GraphQL des pianos Gazelle...\n")

    try:
        result = client._execute_query(query)

        if 'errors' in result:
            print("⚠️ Erreurs GraphQL détectées:")
            for error in result['errors']:
                print(f"   - {error.get('message', 'Unknown error')}")
            print()

        pianos = result.get('data', {}).get('allPianos', {}).get('nodes', [])

        if not pianos:
            print("❌ Aucun piano récupéré")
            return

        print(f"✅ {len(pianos)} pianos récupérés\n")
        print("📊 RAPPORT DE STRUCTURE:\n")

        # Analyser les champs disponibles
        first_piano = pianos[0]

        print("=" * 60)
        print("CHAMPS DISPONIBLES SUR LE TYPE PIANO:")
        print("=" * 60)

        for key, value in sorted(first_piano.items()):
            value_type = type(value).__name__
            value_preview = str(value)[:50] if value else "null"
            print(f"  • {key:30} | {value_type:10} | {value_preview}")

        print("\n" + "=" * 60)
        print("ANALYSE DES IDENTIFIANTS:")
        print("=" * 60)

        # Compter les pianos avec/sans serialNumber
        pianos_with_serial = sum(1 for p in pianos if p.get('serialNumber'))
        pianos_without_serial = len(pianos) - pianos_with_serial

        print(f"\n  Pianos avec serialNumber:    {pianos_with_serial}/{len(pianos)}")
        print(f"  Pianos sans serialNumber:    {pianos_without_serial}/{len(pianos)}")

        # Vérifier les autres identifiants potentiels
        other_ids = ['referenceId', 'tags']
        print("\n  Autres identifiants potentiels:")
        for field in other_ids:
            if field in first_piano:
                count = sum(1 for p in pianos if p.get(field))
                print(f"    - {field:20} : {count}/{len(pianos)} pianos")

        print("\n" + "=" * 60)
        print("EXEMPLES DE DONNÉES:")
        print("=" * 60)

        for i, piano in enumerate(pianos[:3], 1):
            print(f"\nPiano {i}:")
            print(f"  ID:            {piano.get('id')}")
            print(f"  Serial Number: {piano.get('serialNumber', 'N/A')}")
            print(f"  Make:          {piano.get('make', 'N/A')}")
            print(f"  Model:         {piano.get('model', 'N/A')}")
            print(f"  Location:      {piano.get('location', 'N/A')}")

        print("\n" + "=" * 60)
        print("CONCLUSION:")
        print("=" * 60)

        id_type = type(first_piano.get('id')).__name__
        serial_field = 'serialNumber'

        print(f"\n  ✓ Le champ exact pour le numéro de série est: '{serial_field}'")
        print(f"  ✓ Le type de l'ID est: {id_type}")
        print(f"  ✓ Format de l'ID: {first_piano.get('id', 'N/A')}")

        if pianos_without_serial > 0:
            print(f"\n  ⚠️ ATTENTION: {pianos_without_serial}/{len(pianos)} pianos n'ont PAS de serialNumber")
            print("     → Un mécanisme de fallback sera nécessaire")

    except Exception as e:
        print(f"❌ Erreur lors de l'exploration: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    explore_piano_schema()
