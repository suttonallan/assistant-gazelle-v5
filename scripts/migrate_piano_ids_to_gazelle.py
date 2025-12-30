#!/usr/bin/env python3
"""
Script de migration des IDs de pianos vers IDs Gazelle.

Objectif: Ajouter le champ `gazelle_id` à la table `vincent_dindy_piano_updates`
en matchant les pianos CSV avec les pianos Gazelle via:
  1. serialNumber (clé primaire - 87% des cas)
  2. make + location (fallback - 13% des cas)

Usage:
  python scripts/migrate_piano_ids_to_gazelle.py --limit 10    # Test rapide
  python scripts/migrate_piano_ids_to_gazelle.py --limit 100   # Pilote
  python scripts/migrate_piano_ids_to_gazelle.py --all         # Production complète

Sécurités:
  - Aperçu avant écriture avec confirmation utilisateur
  - Continue malgré échecs individuels
  - Rapport d'erreurs détaillé dans rapport_erreurs.md
  - N'efface jamais la colonne `id` existante
"""

import sys
import os
import csv
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime

# Ajouter le répertoire racine au path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.gazelle_api_client import GazelleAPIClient
from core.supabase_storage import SupabaseStorage
from supabase import create_client


class PianoIDMigrator:
    """Migre les IDs de pianos CSV vers IDs Gazelle."""

    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.gazelle_client = GazelleAPIClient()
        self.storage = SupabaseStorage()
        self.supabase = create_client(self.storage.supabase_url, self.storage.supabase_key)

        # Statistiques
        self.stats = {
            'total': 0,
            'matched_by_serial': 0,
            'matched_by_make_location': 0,
            'unmatched': 0,
            'supabase_updated': 0,
            'supabase_errors': 0
        }

        # Erreurs à rapporter
        self.errors = []

    def fetch_gazelle_pianos(self, limit: Optional[int] = None) -> List[Dict]:
        """
        Récupère tous les pianos depuis Gazelle API.

        Args:
            limit: Nombre maximum de pianos à récupérer (None = tous)

        Returns:
            Liste de dictionnaires avec les données Gazelle
        """
        print("🔄 Récupération des pianos depuis Gazelle API...")

        # GraphQL query pour tous les pianos
        query = """
        query GetAllPianos {
            allPianos {
                nodes {
                    id
                    serialNumber
                    make
                    model
                    type
                    location
                }
            }
        }
        """

        result = self.gazelle_client._execute_query(query)
        pianos = result.get('data', {}).get('allPianos', {}).get('nodes', [])

        if limit and len(pianos) > limit:
            pianos = pianos[:limit]

        print(f"✅ {len(pianos)} pianos récupérés depuis Gazelle")
        return pianos

    def load_csv_pianos(self, csv_path: str, limit: Optional[int] = None) -> List[Dict]:
        """
        Charge les pianos depuis le CSV Vincent d'Indy.

        Args:
            csv_path: Chemin vers le fichier CSV
            limit: Nombre maximum de pianos à charger (None = tous)

        Returns:
            Liste de dictionnaires avec les données CSV
        """
        print(f"📖 Lecture du CSV: {csv_path}")

        pianos = []
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                pianos.append(row)
                if limit and len(pianos) >= limit:
                    break

        print(f"✅ {len(pianos)} pianos chargés depuis le CSV")
        return pianos

    def match_by_serial(self, csv_piano: Dict, gazelle_pianos: List[Dict]) -> Optional[str]:
        """
        Matching primaire par numéro de série.

        Args:
            csv_piano: Piano depuis CSV
            gazelle_pianos: Liste des pianos Gazelle

        Returns:
            ID Gazelle si match trouvé, None sinon
        """
        # Essayer plusieurs noms de colonnes possibles
        csv_serial = csv_piano.get('# série', '') or csv_piano.get('serie', '')
        csv_serial = csv_serial.strip()

        if not csv_serial:
            return None

        for gz_piano in gazelle_pianos:
            gz_serial = gz_piano.get('serialNumber') or ''
            gz_serial = gz_serial.strip() if gz_serial else ''
            if csv_serial == gz_serial and csv_serial:  # Éviter de matcher des chaînes vides
                return gz_piano['id']

        return None

    def match_by_make_location(self, csv_piano: Dict, gazelle_pianos: List[Dict]) -> Optional[str]:
        """
        Matching secondaire par marque + localisation.

        Args:
            csv_piano: Piano depuis CSV
            gazelle_pianos: Liste des pianos Gazelle

        Returns:
            ID Gazelle si match trouvé, None sinon
        """
        # Essayer plusieurs noms de colonnes possibles
        csv_make = csv_piano.get('Piano', '') or csv_piano.get('marque', '')
        csv_location = csv_piano.get('local', '')

        # Extraire seulement la marque (avant le premier espace)
        csv_make = csv_make.strip().split()[0] if csv_make.strip() else ''
        csv_location = csv_location.strip().lower()

        if not csv_make or not csv_location:
            return None

        csv_make_lower = csv_make.lower()

        for gz_piano in gazelle_pianos:
            gz_make = gz_piano.get('make') or ''
            gz_location = gz_piano.get('location') or ''

            gz_make = gz_make.strip().lower() if gz_make else ''
            gz_location = gz_location.strip().lower() if gz_location else ''

            if csv_make_lower == gz_make and csv_location == gz_location and csv_location:
                return gz_piano['id']

        return None

    def match_piano(self, csv_piano: Dict, gazelle_pianos: List[Dict]) -> Tuple[Optional[str], str]:
        """
        Tente de matcher un piano CSV avec Gazelle.

        Args:
            csv_piano: Piano depuis CSV
            gazelle_pianos: Liste des pianos Gazelle

        Returns:
            Tuple (gazelle_id, method) où method est 'serial', 'make_location' ou 'none'
        """
        # Tentative 1: Matching par serial
        gazelle_id = self.match_by_serial(csv_piano, gazelle_pianos)
        if gazelle_id:
            return (gazelle_id, 'serial')

        # Tentative 2: Matching par make + location
        gazelle_id = self.match_by_make_location(csv_piano, gazelle_pianos)
        if gazelle_id:
            return (gazelle_id, 'make_location')

        # Aucun match trouvé
        return (None, 'none')

    def process_pianos(self, csv_pianos: List[Dict], gazelle_pianos: List[Dict]) -> List[Dict]:
        """
        Traite tous les pianos et prépare les mises à jour.

        Args:
            csv_pianos: Pianos depuis CSV
            gazelle_pianos: Pianos depuis Gazelle

        Returns:
            Liste des updates à appliquer
        """
        print("\n🔍 Matching des pianos CSV ↔ Gazelle...")

        updates = []
        self.stats['total'] = len(csv_pianos)

        for csv_piano in csv_pianos:
            # Extraire les champs avec noms de colonnes flexibles
            serie = csv_piano.get('# série', '') or csv_piano.get('serie', '')
            piano_id = serie or f"piano_{csv_pianos.index(csv_piano)}"
            local = csv_piano.get('local', 'N/A')
            marque = csv_piano.get('Piano', '') or csv_piano.get('marque', 'N/A')
            # Extraire seulement le premier mot de la marque
            marque = marque.split()[0] if marque and marque != 'N/A' else 'N/A'

            gazelle_id, method = self.match_piano(csv_piano, gazelle_pianos)

            if gazelle_id:
                if method == 'serial':
                    self.stats['matched_by_serial'] += 1
                elif method == 'make_location':
                    self.stats['matched_by_make_location'] += 1

                updates.append({
                    'id': piano_id,
                    'gazelle_id': gazelle_id,
                    'local': local,
                    'method': method
                })
            else:
                self.stats['unmatched'] += 1
                self.errors.append({
                    'local': local,
                    'marque': marque,
                    'serie': serie,
                    'raison': 'Aucun match trouvé dans Gazelle (ni serial ni make+location)'
                })

        return updates

    def print_summary(self, updates: List[Dict]):
        """Affiche un résumé de l'aperçu."""
        print("\n" + "=" * 60)
        print("📊 APERÇU MIGRATION")
        print("=" * 60)
        print(f"\n  Total pianos CSV:              {self.stats['total']}")
        print(f"  ✅ Matchés par serial:          {self.stats['matched_by_serial']} ({self.stats['matched_by_serial']/max(self.stats['total'], 1)*100:.1f}%)")
        print(f"  ✅ Matchés par make+location:   {self.stats['matched_by_make_location']} ({self.stats['matched_by_make_location']/max(self.stats['total'], 1)*100:.1f}%)")
        print(f"  ❌ Non matchés:                  {self.stats['unmatched']} ({self.stats['unmatched']/max(self.stats['total'], 1)*100:.1f}%)")

        if updates:
            print("\n  📋 Exemples de pianos matchés:")
            for update in updates[:5]:
                print(f"     • {update['local']:30} → {update['gazelle_id']} (via {update['method']})")

        if self.errors:
            print(f"\n  ⚠️  {len(self.errors)} pianos non matchés (voir rapport_erreurs.md)")

    def write_error_report(self):
        """Génère le rapport d'erreurs en Markdown."""
        if not self.errors:
            print("\n✅ Aucune erreur à rapporter")
            return

        report_path = project_root / "rapport_erreurs_migration_pianos.md"

        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("# Rapport d'Erreurs - Migration IDs Pianos\n\n")
            f.write(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"**Total pianos non matchés:** {len(self.errors)}\n\n")
            f.write("---\n\n")
            f.write("## Pianos Non Matchés\n\n")
            f.write("| Local | Marque | Série | Raison |\n")
            f.write("|-------|--------|-------|--------|\n")

            for error in self.errors:
                local = error.get('local', 'N/A')
                marque = error.get('marque', 'N/A')
                serie = error.get('serie', 'N/A')
                raison = error.get('raison', 'Inconnue')
                f.write(f"| {local} | {marque} | {serie} | {raison} |\n")

        print(f"\n📄 Rapport d'erreurs généré: {report_path}")

    def apply_updates(self, updates: List[Dict]):
        """
        Applique les mises à jour dans Supabase.

        Args:
            updates: Liste des updates à appliquer
        """
        if not updates:
            print("\n⚠️  Aucune mise à jour à appliquer")
            return

        print(f"\n🔧 Application de {len(updates)} mises à jour dans Supabase...")

        for update in updates:
            piano_serial = update['id']  # Le numéro de série du piano
            gazelle_id = update['gazelle_id']
            local = update['local']

            try:
                # Mise à jour du champ gazelle_id en matchant par piano_id (le numéro de série)
                result = self.supabase.table('vincent_dindy_piano_updates')\
                    .update({'gazelle_id': gazelle_id})\
                    .eq('piano_id', piano_serial)\
                    .execute()

                if result.data:
                    self.stats['supabase_updated'] += 1
                    print(f"  ✅ {local:30} → gazelle_id: {gazelle_id}")
                else:
                    # Piano n'existe pas encore dans Supabase, créer l'entrée
                    result = self.supabase.table('vincent_dindy_piano_updates')\
                        .insert({'piano_id': piano_serial, 'gazelle_id': gazelle_id})\
                        .execute()

                    if result.data:
                        self.stats['supabase_updated'] += 1
                        print(f"  ✅ {local:30} → gazelle_id: {gazelle_id} (créé)")
                    else:
                        raise Exception("Insert failed")

            except Exception as e:
                self.stats['supabase_errors'] += 1
                print(f"  ❌ {local:30} → Erreur: {e}")
                self.errors.append({
                    'local': local,
                    'marque': 'N/A',
                    'serie': piano_serial,
                    'raison': f'Erreur Supabase: {str(e)}'
                })

    def run(self, csv_path: str, limit: Optional[int] = None, skip_confirmation: bool = False):
        """
        Exécute la migration complète.

        Args:
            csv_path: Chemin vers le fichier CSV
            limit: Nombre maximum de pianos à traiter (None = tous)
            skip_confirmation: Si True, ne demande pas de confirmation
        """
        print("\n" + "=" * 60)
        print("🎹 MIGRATION IDS PIANOS → GAZELLE")
        print("=" * 60)

        # 1. Charger les données
        csv_pianos = self.load_csv_pianos(csv_path, limit)
        gazelle_pianos = self.fetch_gazelle_pianos()

        # 2. Traiter les pianos
        updates = self.process_pianos(csv_pianos, gazelle_pianos)

        # 3. Afficher l'aperçu
        self.print_summary(updates)

        # 4. Demander confirmation
        if not skip_confirmation:
            print("\n" + "=" * 60)
            response = input("\n⚠️  Voulez-vous appliquer ces modifications dans Supabase? (y/n): ")
            if response.lower() != 'y':
                print("\n❌ Migration annulée par l'utilisateur")
                return

        # 5. Appliquer les mises à jour
        if not self.dry_run:
            self.apply_updates(updates)
        else:
            print("\n🔍 Mode DRY-RUN: Aucune modification appliquée")

        # 6. Générer le rapport d'erreurs
        self.write_error_report()

        # 7. Résumé final
        print("\n" + "=" * 60)
        print("📊 RÉSUMÉ FINAL")
        print("=" * 60)
        print(f"\n  Total traités:          {self.stats['total']}")
        print(f"  ✅ Matchés (serial):     {self.stats['matched_by_serial']}")
        print(f"  ✅ Matchés (make+loc):   {self.stats['matched_by_make_location']}")
        print(f"  ✅ Supabase mis à jour:  {self.stats['supabase_updated']}")
        print(f"  ❌ Non matchés:          {self.stats['unmatched']}")
        print(f"  ❌ Erreurs Supabase:     {self.stats['supabase_errors']}")
        print()


def main():
    parser = argparse.ArgumentParser(
        description="Migre les IDs de pianos Vincent d'Indy vers IDs Gazelle",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples:
  # Test rapide avec 10 pianos
  python scripts/migrate_piano_ids_to_gazelle.py --limit 10

  # Pilote avec 100 pianos
  python scripts/migrate_piano_ids_to_gazelle.py --limit 100

  # Migration complète
  python scripts/migrate_piano_ids_to_gazelle.py --all

  # Mode dry-run (aperçu sans modification)
  python scripts/migrate_piano_ids_to_gazelle.py --limit 10 --dry-run
        """
    )

    parser.add_argument(
        '--limit',
        type=int,
        default=None,
        help='Nombre maximum de pianos à traiter (défaut: tous)'
    )

    parser.add_argument(
        '--all',
        action='store_true',
        help='Traiter TOUS les pianos (ignore --limit)'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Aperçu sans modification (mode test)'
    )

    parser.add_argument(
        '--yes',
        action='store_true',
        help='Ne pas demander de confirmation (automatique)'
    )

    parser.add_argument(
        '--csv',
        type=str,
        default='api/data/pianos_vincent_dindy.csv',
        help='Chemin vers le fichier CSV (défaut: api/data/pianos_vincent_dindy.csv)'
    )

    args = parser.parse_args()

    # Déterminer la limite
    limit = None if args.all else args.limit

    # Vérifier que le CSV existe
    csv_path = project_root / args.csv
    if not csv_path.exists():
        print(f"❌ Erreur: Fichier CSV introuvable: {csv_path}")
        sys.exit(1)

    # Exécuter la migration
    migrator = PianoIDMigrator(dry_run=args.dry_run)
    migrator.run(str(csv_path), limit=limit, skip_confirmation=args.yes)


if __name__ == "__main__":
    main()
