#!/usr/bin/env python3
"""
Migration: Convertir les IDs de techniciens Place des Arts → IDs Gazelle

PROBLÈME:
- Place des Arts utilise: usr_U9E5bLxrFiXqTbE8 (Nicolas), usr_allan (Allan)
- Gazelle utilise: usr_HcCiFk7o0vZ9xAI0 (Nicolas), usr_ofYggsCDt2JAVeNP (Allan)

SOLUTION:
- Mettre à jour les 14 demandes existantes pour utiliser les IDs Gazelle
- Afficher un rapport détaillé avant/après
"""

import sys
import os
from typing import Dict, List, Any
import requests
from dotenv import load_dotenv

# Charger .env
load_dotenv()

# Ajouter le parent au path pour importer SupabaseStorage
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
from modules.storage.supabase import SupabaseStorage


# Mapping Place des Arts ID → Gazelle ID
TECH_ID_MAPPING = {
    'usr_U9E5bLxrFiXqTbE8': 'usr_HcCiFk7o0vZ9xAI0',  # Nicolas/Patrick
    'usr_allan': 'usr_ofYggsCDt2JAVeNP',              # Allan
}


class PdaTechnicianMigrator:
    """Migration des IDs de techniciens PDA → Gazelle"""

    def __init__(self):
        """Initialise avec connexion Supabase"""
        self.storage = SupabaseStorage()
        print("✅ PdaTechnicianMigrator initialisé")

    def get_requests_with_old_ids(self) -> List[Dict[str, Any]]:
        """Récupère toutes les demandes PDA avec anciens IDs"""
        try:
            old_ids = list(TECH_ID_MAPPING.keys())

            # Construire la requête OR pour tous les anciens IDs
            url = f"{self.storage.api_url}/place_des_arts_requests"
            url += "?select=*"
            url += "&or=(" + ",".join([f"technician_id.eq.{id}" for id in old_ids]) + ")"

            response = requests.get(url, headers=self.storage._get_headers())

            if response.status_code == 200:
                return response.json()
            else:
                print(f"  ❌ Erreur {response.status_code}: {response.text}")
                return []

        except Exception as e:
            print(f"⚠️ Erreur get_requests_with_old_ids: {e}")
            import traceback
            traceback.print_exc()
            return []

    def migrate_request(self, request_id: str, old_id: str, new_id: str, dry_run: bool = True) -> bool:
        """Migre une seule demande vers le nouvel ID"""
        try:
            if dry_run:
                print(f"  [DRY RUN] Migrerait {request_id}: {old_id} → {new_id}")
                return True

            url = f"{self.storage.api_url}/place_des_arts_requests"
            url += f"?id=eq.{request_id}"

            response = requests.patch(
                url,
                headers=self.storage._get_headers(),
                json={'technician_id': new_id}
            )

            if response.status_code in (200, 204):
                print(f"  ✅ Migré {request_id}: {old_id} → {new_id}")
                return True
            else:
                print(f"  ❌ Erreur {response.status_code}: {response.text}")
                return False

        except Exception as e:
            print(f"⚠️ Erreur migrate_request: {e}")
            return False

    def run_migration(self, dry_run: bool = True):
        """Exécute la migration complète"""
        print(f"\n{'='*80}")
        print(f"🔄 Migration IDs Techniciens: Place des Arts → Gazelle")
        if dry_run:
            print("   [MODE DRY RUN - Aucune modification ne sera faite]")
        else:
            print("   [MODE LIVE - Les modifications seront appliquées!]")
        print(f"{'='*80}")

        # Récupérer les demandes avec anciens IDs
        requests_to_migrate = self.get_requests_with_old_ids()

        print(f"\n📊 {len(requests_to_migrate)} demandes à migrer")

        if not requests_to_migrate:
            print("\n✅ Aucune demande à migrer - tous les IDs sont déjà corrects!")
            return

        # Grouper par ancien ID
        by_old_id = {}
        for req in requests_to_migrate:
            old_id = req.get('technician_id')
            if old_id not in by_old_id:
                by_old_id[old_id] = []
            by_old_id[old_id].append(req)

        # Afficher le plan de migration
        print("\n📋 Plan de migration:")
        for old_id, reqs in by_old_id.items():
            new_id = TECH_ID_MAPPING.get(old_id, '???')
            print(f"\n  {old_id} → {new_id}")
            print(f"  {len(reqs)} demandes:")
            for req in reqs[:3]:  # Montrer les 3 premières
                print(f"    - {req['id']}: {req.get('room', 'N/A')} ({req.get('appointment_date', 'N/A')})")
            if len(reqs) > 3:
                print(f"    ... et {len(reqs) - 3} autres")

        # Exécuter la migration
        print(f"\n{'='*80}")
        print("🚀 Exécution de la migration...")
        print(f"{'='*80}")

        success_count = 0
        fail_count = 0

        for req in requests_to_migrate:
            old_id = req.get('technician_id')
            new_id = TECH_ID_MAPPING.get(old_id)

            if not new_id:
                print(f"  ⚠️ Pas de mapping pour {old_id} - ignoré")
                fail_count += 1
                continue

            if self.migrate_request(req['id'], old_id, new_id, dry_run=dry_run):
                success_count += 1
            else:
                fail_count += 1

        # Résumé
        print(f"\n{'='*80}")
        print("📊 RÉSUMÉ DE MIGRATION")
        print(f"{'='*80}")
        print(f"✅ Succès: {success_count}")
        print(f"❌ Échecs: {fail_count}")

        if dry_run:
            print("\n💡 Pour appliquer réellement les changements, relancez avec dry_run=False")

        return success_count, fail_count


# ============================================================================
# Exécution
# ============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Migrer les IDs de techniciens PDA → Gazelle')
    parser.add_argument('--live', action='store_true', help='Appliquer réellement les changements (sinon dry-run)')
    args = parser.parse_args()

    migrator = PdaTechnicianMigrator()

    # Par défaut, dry run
    dry_run = not args.live

    migrator.run_migration(dry_run=dry_run)
