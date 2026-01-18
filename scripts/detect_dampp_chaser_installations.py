#!/usr/bin/env python3
"""
🔍 Détection des installations Dampp-Chaser / Piano Life Saver

Scanne la timeline pour trouver les pianos avec système d'humidité installé
et met à jour la colonne dampp_chaser_installed dans gazelle_pianos.

Recherche les mots-clés:
- "Dampp-Chaser"
- "Life Saver"
- "PLS"
- "Piano Life Saver"
- "humidité système"
- "humidificateur"
- "déshumidificateur"
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.supabase_storage import SupabaseStorage
from typing import Set


def find_pianos_with_dampp_chaser(storage: SupabaseStorage) -> Set[str]:
    """
    Scanne la timeline pour trouver les pianos avec Dampp-Chaser.

    Returns:
        Set de piano_id (internal UUID) avec système détecté
    """
    print("\n" + "=" * 80)
    print("🔍 DÉTECTION DAMPP-CHASER / PIANO LIFE SAVER")
    print("=" * 80 + "\n")

    # Mots-clés à rechercher (case-insensitive)
    keywords = [
        'dampp-chaser',
        'dampp chaser',
        'life saver',
        'piano life saver',
        'pls system',
        'humidificateur system',
        'déshumidificateur system',
        'système humidité',
        'humidity control system',
    ]

    pianos_with_dc = set()

    # Rechercher dans la timeline
    print("🔎 Recherche dans la timeline...\n")

    for keyword in keywords:
        print(f"  Recherche: '{keyword}'...", end=' ')

        try:
            # Rechercher dans title
            result_title = storage.client.table('gazelle_timeline_entries')\
                .select('piano_id,title,description,occurred_at')\
                .ilike('title', f'%{keyword}%')\
                .not_.is_('piano_id', 'null')\
                .execute()

            # Rechercher dans description
            result_desc = storage.client.table('gazelle_timeline_entries')\
                .select('piano_id,title,description,occurred_at')\
                .ilike('description', f'%{keyword}%')\
                .not_.is_('piano_id', 'null')\
                .execute()

            found_title = len(result_title.data) if result_title.data else 0
            found_desc = len(result_desc.data) if result_desc.data else 0
            total_found = found_title + found_desc

            print(f"✅ {total_found} entrées")

            # Ajouter les piano_id trouvés
            if result_title.data:
                for entry in result_title.data:
                    piano_id = entry.get('piano_id')
                    if piano_id:
                        pianos_with_dc.add(piano_id)

            if result_desc.data:
                for entry in result_desc.data:
                    piano_id = entry.get('piano_id')
                    if piano_id:
                        pianos_with_dc.add(piano_id)

        except Exception as e:
            print(f"❌ Erreur: {str(e)[:50]}")

    print(f"\n📊 RÉSULTAT: {len(pianos_with_dc)} pianos uniques avec Dampp-Chaser détectés\n")

    return pianos_with_dc


def update_pianos_dampp_chaser(storage: SupabaseStorage, piano_ids: Set[str], dry_run: bool = True):
    """
    Met à jour la colonne dampp_chaser_installed pour les pianos détectés.

    Args:
        storage: Instance SupabaseStorage
        piano_ids: Set de piano_id (UUID) à mettre à jour
        dry_run: Si True, affiche seulement ce qui serait fait (ne modifie pas)
    """
    if not piano_ids:
        print("⚠️  Aucun piano à mettre à jour.\n")
        return

    print("=" * 80)
    if dry_run:
        print("🔍 MODE TEST (DRY RUN) - Aucune modification")
    else:
        print("✏️  MODE ÉCRITURE - Mise à jour des pianos")
    print("=" * 80 + "\n")

    success_count = 0
    error_count = 0

    for i, piano_id in enumerate(piano_ids, 1):
        try:
            # Récupérer infos piano (piano_id est external_id de Gazelle)
            piano = storage.client.table('gazelle_pianos')\
                .select('id,external_id,make,model,type')\
                .eq('external_id', piano_id)\
                .maybe_single()\
                .execute()

            if not piano.data:
                # Piano n'existe pas dans Supabase (probablement supprimé)
                if i <= 5:  # Montrer seulement les 5 premiers
                    print(f"  {i:3d}. ⚠️  Piano {piano_id[:20]} introuvable (supprimé?)")
                error_count += 1
                continue

            piano_info = piano.data
            make = piano_info.get('make', 'N/A')
            model = piano_info.get('model', 'N/A')
            external_id = piano_info.get('external_id', 'N/A')

            if dry_run:
                print(f"  {i:3d}. SERAIT MARQUÉ: {make} {model} ({external_id[:20]})")
            else:
                # Mettre à jour (par external_id)
                storage.client.table('gazelle_pianos')\
                    .update({'dampp_chaser_installed': True})\
                    .eq('external_id', piano_id)\
                    .execute()

                print(f"  {i:3d}. ✅ MARQUÉ: {make} {model} ({external_id[:20]})")
                success_count += 1

        except Exception as e:
            print(f"  {i:3d}. ❌ ERREUR {piano_id}: {str(e)[:50]}")
            error_count += 1

    print("\n" + "=" * 80)
    if dry_run:
        print(f"📊 TEST: {len(piano_ids)} pianos seraient marqués")
    else:
        print(f"✅ Succès: {success_count}")
        print(f"❌ Erreurs: {error_count}")
    print("=" * 80 + "\n")


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Détecte et marque les pianos avec Dampp-Chaser')
    parser.add_argument('--write', action='store_true', help='Effectuer les modifications (sinon mode test)')
    args = parser.parse_args()

    storage = SupabaseStorage()

    # 1. Détecter
    pianos_with_dc = find_pianos_with_dampp_chaser(storage)

    # 2. Mettre à jour
    if pianos_with_dc:
        update_pianos_dampp_chaser(storage, pianos_with_dc, dry_run=not args.write)

        if not args.write:
            print("\n💡 Pour appliquer les modifications, relancez avec: --write\n")
    else:
        print("⚠️  Aucun piano avec Dampp-Chaser détecté dans la timeline.\n")


if __name__ == '__main__':
    main()
