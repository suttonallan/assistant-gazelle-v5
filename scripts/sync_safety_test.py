#!/usr/bin/env python3
"""
Script de test de sécurité pour la synchronisation.

OBJECTIF: Vérifier que les modifications de sécurité fonctionnent
SANS RISQUE pour les données existantes.

Usage:
    python3 scripts/sync_safety_test.py --dry-run
    python3 scripts/sync_safety_test.py --backup
    python3 scripts/sync_safety_test.py --restore <backup_file>
"""

import sys
import os
import json
import argparse
from datetime import datetime
from pathlib import Path

# Ajouter le projet au path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from core.supabase_storage import SupabaseStorage


def backup_timeline_entries(storage: SupabaseStorage, output_dir: str = "backups") -> str:
    """
    Sauvegarde toutes les timeline entries dans un fichier JSON.

    Returns:
        Chemin du fichier de backup
    """
    print("=" * 70)
    print("🔒 BACKUP DES TIMELINE ENTRIES")
    print("=" * 70)

    # Créer le dossier backups s'il n'existe pas
    backup_dir = Path(output_dir)
    backup_dir.mkdir(exist_ok=True)

    # Récupérer toutes les timeline entries
    print("📥 Récupération des timeline entries depuis Supabase...")

    try:
        import requests
        url = f"{storage.api_url}/gazelle_timeline_entries?select=*"
        response = requests.get(url, headers=storage._get_headers())

        if response.status_code != 200:
            print(f"❌ Erreur: {response.status_code}")
            return None

        entries = response.json()
        print(f"   ✅ {len(entries)} entrées récupérées")

        # Sauvegarder dans un fichier
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = backup_dir / f"timeline_backup_{timestamp}.json"

        with open(backup_file, 'w', encoding='utf-8') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'count': len(entries),
                'entries': entries
            }, f, ensure_ascii=False, indent=2)

        print(f"   💾 Backup sauvegardé: {backup_file}")
        print(f"   📊 Taille: {backup_file.stat().st_size / 1024:.1f} KB")

        return str(backup_file)

    except Exception as e:
        print(f"❌ Erreur backup: {e}")
        return None


def restore_timeline_entries(storage: SupabaseStorage, backup_file: str) -> bool:
    """
    Restaure les timeline entries depuis un fichier de backup.

    ⚠️ ATTENTION: Ceci va écraser les données actuelles!
    """
    print("=" * 70)
    print("🔄 RESTAURATION DES TIMELINE ENTRIES")
    print("=" * 70)

    backup_path = Path(backup_file)
    if not backup_path.exists():
        print(f"❌ Fichier de backup non trouvé: {backup_file}")
        return False

    print(f"📂 Lecture du backup: {backup_file}")

    try:
        with open(backup_path, 'r', encoding='utf-8') as f:
            backup_data = json.load(f)

        entries = backup_data.get('entries', [])
        print(f"   📊 {len(entries)} entrées dans le backup")
        print(f"   📅 Backup créé le: {backup_data.get('timestamp', 'inconnu')}")

        # Confirmation
        confirm = input("\n⚠️  ATTENTION: Ceci va restaurer les données.\n   Continuer? (oui/non): ")
        if confirm.lower() != 'oui':
            print("❌ Restauration annulée")
            return False

        import requests

        restored = 0
        errors = 0

        for entry in entries:
            try:
                # UPSERT pour restaurer
                url = f"{storage.api_url}/gazelle_timeline_entries?on_conflict=external_id"
                headers = storage._get_headers()
                headers["Prefer"] = "resolution=merge-duplicates"

                response = requests.post(url, headers=headers, json=entry)

                if response.status_code in [200, 201]:
                    restored += 1
                else:
                    errors += 1
                    if errors <= 5:  # Limiter les logs d'erreur
                        print(f"   ⚠️ Erreur {entry.get('external_id')}: {response.status_code}")
            except Exception as e:
                errors += 1

        print(f"\n✅ Restauration terminée:")
        print(f"   - {restored} entrées restaurées")
        print(f"   - {errors} erreurs")

        return errors == 0

    except Exception as e:
        print(f"❌ Erreur restauration: {e}")
        return False


def dry_run_sync(storage: SupabaseStorage):
    """
    Simule une synchronisation SANS modifier les données.
    Vérifie que les verrous de sécurité sont actifs.
    """
    print("=" * 70)
    print("🔍 DRY RUN - TEST DES VERROUS DE SÉCURITÉ")
    print("=" * 70)

    print("\n1️⃣ Vérification du code sync_to_supabase.py...")

    sync_file = Path(__file__).parent.parent / "modules/sync_gazelle/sync_to_supabase.py"

    if not sync_file.exists():
        print(f"   ❌ Fichier non trouvé: {sync_file}")
        return False

    with open(sync_file, 'r', encoding='utf-8') as f:
        code = f.read()

    # Vérifier les verrous de sécurité
    checks = [
        ("VERROU #1: Mapping multi-champs", "VERROU SÉCURITÉ #1"),
        ("VERROU #2: Protection écrasement vide", "VERROU SÉCURITÉ #2"),
        ("VERROU #3: DELETE désactivé", "ENABLE_APPOINTMENT_CLEANUP = False"),
        ("VERROU #4: Fenêtre 30 jours", "TIMELINE_SYNC_DAYS = 30"),
    ]

    all_ok = True
    for name, pattern in checks:
        if pattern in code:
            print(f"   ✅ {name}")
        else:
            print(f"   ❌ {name} - MANQUANT!")
            all_ok = False

    print("\n2️⃣ Vérification de la base de données...")

    import requests

    # Compter les timeline entries
    url = f"{storage.api_url}/gazelle_timeline_entries?select=count"
    headers = storage._get_headers()
    headers["Prefer"] = "count=exact"

    response = requests.head(url, headers=headers)
    count = response.headers.get('content-range', '0').split('/')[-1]
    print(f"   📊 Timeline entries actuelles: {count}")

    # Vérifier les entrées avec description vide
    url = f"{storage.api_url}/gazelle_timeline_entries?description=is.null&select=count"
    response = requests.head(url, headers=headers)
    empty_count = response.headers.get('content-range', '0').split('/')[-1]
    print(f"   ⚠️  Entrées avec description vide: {empty_count}")

    print("\n" + "=" * 70)
    if all_ok:
        print("✅ TOUS LES VERROUS DE SÉCURITÉ SONT ACTIFS")
        print("   La synchronisation peut être lancée en toute sécurité.")
    else:
        print("❌ CERTAINS VERROUS SONT MANQUANTS")
        print("   Ne PAS lancer la synchronisation avant correction!")
    print("=" * 70)

    return all_ok


def main():
    parser = argparse.ArgumentParser(description="Test de sécurité sync")
    parser.add_argument('--dry-run', action='store_true', help='Vérifier les verrous sans modifier')
    parser.add_argument('--backup', action='store_true', help='Sauvegarder les timeline entries')
    parser.add_argument('--restore', type=str, help='Restaurer depuis un fichier de backup')

    args = parser.parse_args()

    storage = SupabaseStorage()

    if args.backup:
        backup_timeline_entries(storage)
    elif args.restore:
        restore_timeline_entries(storage, args.restore)
    elif args.dry_run:
        dry_run_sync(storage)
    else:
        # Par défaut: dry-run
        dry_run_sync(storage)


if __name__ == "__main__":
    main()
