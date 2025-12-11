#!/usr/bin/env python3
"""
Script de migration: Copie les données du CSV vers Supabase.

Ce script lit le CSV des pianos Vincent-d'Indy et met à jour Supabase
avec les champs manquants (local, piano, usage, etc.).

Exécution:
    python3 scripts/migrate_csv_to_supabase.py
"""

import os
import sys
import csv
from pathlib import Path

# Ajouter le répertoire parent au path pour importer les modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.supabase_storage import SupabaseStorage


def get_csv_path():
    """Retourne le chemin du CSV des pianos."""
    # Chercher dans data_csv_test/ ou api/data/
    possible_paths = [
        "data_csv_test/pianos_vincent_dindy.csv",
        "api/data/pianos_vincent_dindy.csv"
    ]

    for path in possible_paths:
        if os.path.exists(path):
            return path

    raise FileNotFoundError(f"CSV non trouvé dans: {possible_paths}")


def migrate_csv_to_supabase():
    """Migre les données du CSV vers Supabase."""
    print("=" * 60)
    print("🔄 Migration CSV → Supabase")
    print("=" * 60)

    # Initialiser Supabase
    try:
        storage = SupabaseStorage()
        print("✅ Connexion à Supabase réussie")
    except Exception as e:
        print(f"❌ Erreur de connexion à Supabase: {e}")
        return

    # Lire le CSV
    csv_path = get_csv_path()
    print(f"📄 Lecture du CSV: {csv_path}")

    pianos_to_update = []

    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)

        for idx, row in enumerate(reader, start=1):
            # Extraire les données du CSV
            serie = row.get("# série", "").strip() or row.get("série", "").strip()
            piano_id = serie if serie else f"piano_{idx}"

            local = row.get("local", "").strip()
            piano_name = row.get("Piano", "").strip()
            type_piano = row.get("Type", "").strip()
            usage = row.get("Usage", "").strip()

            # Préparer les données pour Supabase
            piano_data = {
                "piano_id": piano_id,
                "local": local if local and local != "?" else "",
                "piano": piano_name,
                "type": type_piano.upper() if type_piano else "D",
                "usage": usage
            }

            pianos_to_update.append(piano_data)

    print(f"📊 {len(pianos_to_update)} pianos à migrer")

    # Migrer par batch de 50 pour éviter les timeouts
    batch_size = 50
    total_updated = 0

    for i in range(0, len(pianos_to_update), batch_size):
        batch = pianos_to_update[i:i+batch_size]
        print(f"\n🔄 Migration batch {i//batch_size + 1}/{(len(pianos_to_update)-1)//batch_size + 1} ({len(batch)} pianos)...")

        success = storage.batch_update_pianos(batch)

        if success:
            total_updated += len(batch)
            print(f"   ✅ {len(batch)} pianos migrés")
        else:
            print(f"   ❌ Échec de la migration du batch")

    print("\n" + "=" * 60)
    print(f"✅ Migration terminée: {total_updated}/{len(pianos_to_update)} pianos")
    print("=" * 60)


if __name__ == "__main__":
    migrate_csv_to_supabase()
