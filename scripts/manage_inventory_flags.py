#!/usr/bin/env python3
"""
Script interactif pour gérer les flags is_in_csv des pianos Vincent d'Indy.
Permet de marquer des pianos comme "hors inventaire" en batch.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.gazelle_api_client import GazelleAPIClient
from core.supabase_storage import SupabaseStorage
import requests


VINCENT_DINDY_CLIENT_ID = "cli_9UMLkteep8EsISbG"


def load_pianos():
    """Charge tous les pianos Vincent d'Indy depuis Gazelle."""
    print("🔄 Chargement des pianos depuis Gazelle...")

    client = GazelleAPIClient()

    query = """
    query GetVincentDIndyPianos($clientId: String!) {
      allPianos(first: 200, filters: { clientId: $clientId }) {
        nodes {
          id
          serialNumber
          make
          model
          location
          status
          calculatedLastService
        }
      }
    }
    """

    variables = {"clientId": VINCENT_DINDY_CLIENT_ID}
    result = client._execute_query(query, variables)
    pianos = result.get("data", {}).get("allPianos", {}).get("nodes", [])

    return pianos


def load_supabase_flags():
    """Charge les flags is_in_csv depuis Supabase."""
    storage = SupabaseStorage()

    try:
        url = f"{storage.api_url}/vincent_dindy_piano_updates?select=piano_id,gazelle_id,is_in_csv"
        headers = storage._get_headers()

        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            data = response.json()
            # Créer un dict pour lookup rapide
            flags = {}
            for entry in data:
                piano_id = entry.get('piano_id')
                gazelle_id = entry.get('gazelle_id')
                is_in_csv = entry.get('is_in_csv', True)

                if piano_id:
                    flags[piano_id] = is_in_csv
                if gazelle_id:
                    flags[gazelle_id] = is_in_csv

            return flags
        else:
            print(f"⚠️  Erreur lors du chargement des flags: HTTP {response.status_code}")
            return {}
    except Exception as e:
        print(f"⚠️  Erreur: {e}")
        return {}


def display_pianos(pianos, flags):
    """Affiche la liste des pianos avec leurs flags."""
    print("\n" + "=" * 120)
    print(f"{'#':<4} {'ID':<25} {'Série':<15} {'Marque':<15} {'Modèle':<15} {'Local':<20} {'Status':<10} {'CSV':<5}")
    print("=" * 120)

    for idx, piano in enumerate(pianos, start=1):
        gz_id = piano.get('id', '')
        serial = piano.get('serialNumber') or ''
        make = (piano.get('make') or '')[:14]
        model = (piano.get('model') or '')[:14]
        location = (piano.get('location') or '')[:19]
        status = (piano.get('status') or '')[:9]

        # Déterminer le flag is_in_csv
        is_in_csv = flags.get(serial, flags.get(gz_id, True))
        csv_flag = "✓" if is_in_csv else "✗"

        print(f"{idx:<4} {gz_id:<25} {serial:<15} {make:<15} {model:<15} {location:<20} {status:<10} {csv_flag:<5}")

    print("=" * 120)


def select_pianos(pianos):
    """Permet à l'utilisateur de sélectionner des pianos."""
    print("\n📋 Sélection des pianos à marquer comme HORS INVENTAIRE")
    print("\nOptions:")
    print("  - Entrez les numéros séparés par des virgules (ex: 1,3,5-10,15)")
    print("  - Tapez 'all' pour sélectionner tous")
    print("  - Tapez 'inactive' pour sélectionner tous les inactifs")
    print("  - Tapez 'q' pour quitter")
    print()

    selection = input("Votre sélection: ").strip().lower()

    if selection == 'q':
        return None

    selected_indices = set()

    if selection == 'all':
        selected_indices = set(range(1, len(pianos) + 1))
    elif selection == 'inactive':
        for idx, piano in enumerate(pianos, start=1):
            if piano.get('status') == 'INACTIVE':
                selected_indices.add(idx)
        print(f"✓ {len(selected_indices)} pianos inactifs sélectionnés")
    else:
        # Parser la sélection (ex: "1,3,5-10,15")
        parts = selection.split(',')
        for part in parts:
            part = part.strip()
            if '-' in part:
                # Range (ex: "5-10")
                try:
                    start, end = part.split('-')
                    start = int(start.strip())
                    end = int(end.strip())
                    selected_indices.update(range(start, end + 1))
                except ValueError:
                    print(f"⚠️  Format invalide: {part}")
            else:
                # Nombre unique
                try:
                    selected_indices.add(int(part))
                except ValueError:
                    print(f"⚠️  Format invalide: {part}")

    # Filtrer les indices valides
    valid_indices = [i for i in selected_indices if 1 <= i <= len(pianos)]

    if not valid_indices:
        print("❌ Aucun piano sélectionné")
        return []

    # Récupérer les pianos sélectionnés
    selected_pianos = [pianos[i - 1] for i in sorted(valid_indices)]

    print(f"\n✓ {len(selected_pianos)} piano(s) sélectionné(s):")
    for piano in selected_pianos:
        serial = piano.get('serialNumber', 'N/A')
        make = piano.get('make', '')
        location = piano.get('location', '')
        print(f"  - {serial} - {make} @ {location}")

    return selected_pianos


def update_flags(selected_pianos, set_to_value):
    """Met à jour les flags is_in_csv dans Supabase."""
    storage = SupabaseStorage()

    print(f"\n🔧 Mise à jour de {len(selected_pianos)} piano(s)...")
    print(f"   Valeur: is_in_csv = {set_to_value}")
    print()

    success_count = 0

    for piano in selected_pianos:
        gz_id = piano.get('id')
        serial = piano.get('serialNumber', '')

        try:
            # Chercher par gazelle_id
            url = f"{storage.api_url}/vincent_dindy_piano_updates?gazelle_id=eq.{gz_id}"
            headers = storage._get_headers()

            response = requests.get(url, headers=headers)

            if response.status_code == 200 and response.json():
                # Entrée existe - mettre à jour
                update_data = {'is_in_csv': set_to_value}
                response = requests.patch(url, json=update_data, headers=headers)

                if response.status_code == 200:
                    print(f"  ✓ {serial or gz_id} - Mis à jour")
                    success_count += 1
                else:
                    print(f"  ✗ {serial or gz_id} - Erreur HTTP {response.status_code}")
            else:
                # Entrée n'existe pas - créer
                insert_data = {
                    'piano_id': serial if serial else None,
                    'gazelle_id': gz_id,
                    'is_in_csv': set_to_value
                }
                response = requests.post(
                    f"{storage.api_url}/vincent_dindy_piano_updates",
                    json=insert_data,
                    headers=headers
                )

                if response.status_code == 201:
                    print(f"  ✓ {serial or gz_id} - Créé")
                    success_count += 1
                else:
                    print(f"  ✗ {serial or gz_id} - Erreur HTTP {response.status_code}")

        except Exception as e:
            print(f"  ✗ {serial or gz_id} - Erreur: {e}")

    print()
    print(f"✅ {success_count}/{len(selected_pianos)} piano(s) mis à jour avec succès")

    return success_count


def main():
    """Fonction principale."""
    print("=" * 80)
    print("GESTION DES FLAGS D'INVENTAIRE - Vincent d'Indy")
    print("=" * 80)
    print()

    try:
        # Charger les pianos
        pianos = load_pianos()
        print(f"✅ {len(pianos)} pianos chargés depuis Gazelle")

        # Charger les flags actuels
        flags = load_supabase_flags()
        print(f"✅ Flags chargés depuis Supabase")

        while True:
            # Afficher la liste
            display_pianos(pianos, flags)

            # Menu principal
            print("\n📋 Actions disponibles:")
            print("  1. Marquer des pianos comme HORS INVENTAIRE (is_in_csv=FALSE)")
            print("  2. Marquer des pianos comme DANS INVENTAIRE (is_in_csv=TRUE)")
            print("  3. Afficher les statistiques")
            print("  q. Quitter")
            print()

            choice = input("Votre choix: ").strip().lower()

            if choice == 'q':
                print("\n👋 Au revoir!")
                break
            elif choice == '1':
                selected = select_pianos(pianos)
                if selected:
                    confirm = input(f"\n⚠️  Confirmer: marquer {len(selected)} piano(s) comme HORS INVENTAIRE? (oui/non): ").strip().lower()
                    if confirm == 'oui':
                        update_flags(selected, False)
                        # Recharger les flags
                        flags = load_supabase_flags()
            elif choice == '2':
                selected = select_pianos(pianos)
                if selected:
                    confirm = input(f"\n⚠️  Confirmer: marquer {len(selected)} piano(s) comme DANS INVENTAIRE? (oui/non): ").strip().lower()
                    if confirm == 'oui':
                        update_flags(selected, True)
                        # Recharger les flags
                        flags = load_supabase_flags()
            elif choice == '3':
                # Statistiques
                in_csv = sum(1 for p in pianos if flags.get(p.get('serialNumber', ''), flags.get(p.get('id', ''), True)))
                out_csv = len(pianos) - in_csv
                active = sum(1 for p in pianos if p.get('status') == 'ACTIVE')
                inactive = len(pianos) - active

                print("\n📊 Statistiques:")
                print(f"  Total pianos: {len(pianos)}")
                print(f"  Dans inventaire (is_in_csv=TRUE): {in_csv}")
                print(f"  Hors inventaire (is_in_csv=FALSE): {out_csv}")
                print(f"  Actifs: {active}")
                print(f"  Inactifs: {inactive}")
                print()
                input("Appuyez sur Entrée pour continuer...")
            else:
                print("❌ Choix invalide")

    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
