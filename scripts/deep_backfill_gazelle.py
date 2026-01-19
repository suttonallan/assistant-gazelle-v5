#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════════════╗
║             RESTAURATION HISTORIQUE PROFONDE GAZELLE (2016-2026)           ║
║                     Backfill complet avec sécurité anti-effacement         ║
╚═══════════════════════════════════════════════════════════════════════════╝

Ce script récupère TOUT l'historique Gazelle depuis 2016 et le synchronise
vers Supabase en mode UPSERT sécurisé (jamais de suppression).

Stratégie:
- Pagination Relay avec curseur (first: 100, after)
- UPSERT strict avec on_conflict (jamais de DELETE)
- Progression année par année avec résumés
- Gestion d'erreurs robuste

Usage:
    python3 scripts/deep_backfill_gazelle.py [--start-year 2016] [--end-year 2026]
"""

import sys
from pathlib import Path

# Ajouter le projet au path
sys.path.insert(0, str(Path(__file__).parent.parent))

import argparse
import requests
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from core.gazelle_api_client import GazelleAPIClient
from core.supabase_storage import SupabaseStorage


class DeepBackfillService:
    """Service de restauration historique profonde avec sécurité anti-effacement."""

    def __init__(self):
        self.api_client = GazelleAPIClient()
        self.storage = SupabaseStorage()

        # Compteurs globaux
        self.total_timeline_synced = 0
        self.total_timeline_errors = 0
        self.total_pianos_synced = 0
        self.total_clients_synced = 0

    def get_existing_timeline_ids(self) -> set:
        """
        Récupère tous les external_id déjà présents dans Supabase.
        Permet la reprise intelligente.

        Returns:
            Set d'external_id déjà synchronisés
        """
        print("🔍 Vérification des entrées déjà synchronisées...")

        try:
            url = f"{self.storage.api_url}/gazelle_timeline_entries?select=external_id"
            headers = self.storage._get_headers()

            existing_ids = set()
            offset = 0
            limit = 1000

            while True:
                paginated_url = f"{url}&offset={offset}&limit={limit}"
                resp = requests.get(paginated_url, headers=headers)

                if resp.status_code != 200:
                    print(f"⚠️  Erreur récupération IDs existants: {resp.status_code}")
                    return set()

                data = resp.json()
                if not data:
                    break

                for item in data:
                    if item.get('external_id'):
                        existing_ids.add(item['external_id'])

                if len(data) < limit:
                    break

                offset += limit

            print(f"✅ Trouvé {len(existing_ids)} entrées déjà synchronisées")
            return existing_ids

        except Exception as e:
            print(f"⚠️  Erreur lors de la vérification: {e}")
            return set()

    def backfill_timeline_year(self, year: int, existing_ids: set) -> Dict[str, int]:
        """
        Récupère toutes les timeline entries pour une année donnée.

        Args:
            year: Année à synchroniser (ex: 2024)
            existing_ids: Set des external_id déjà dans Supabase (reprise intelligente)

        Returns:
            Dict avec 'synced' et 'errors'
        """
        print(f"\n{'='*70}")
        print(f"📅 ANNÉE {year} - Timeline Entries")
        print(f"{'='*70}")

        # Dates de début et fin pour l'année
        start_date = f"{year}-01-01T00:00:00Z"
        end_date = f"{year}-12-31T23:59:59Z"

        print(f"📍 Période: {start_date} → {end_date}")

        synced = 0
        errors = 0
        skipped = 0
        cursor = None
        page = 0

        # GraphQL Query avec pagination Relay
        # CORRECTION CRITIQUE: Utiliser occurredAtGte (Greater Than or Equal), pas occurredAtGet
        query = """
        query GetTimelineYear($cursor: String, $occurredAtGte: CoreDateTime, $occurredAtLte: CoreDateTime) {
            allTimelineEntries(
                first: 100,
                after: $cursor,
                occurredAtGte: $occurredAtGte,
                occurredAtLte: $occurredAtLte
            ) {
                edges {
                    node {
                        id
                        occurredAt
                        type
                        summary
                        comment
                        client { id }
                        piano { id }
                        invoice { id }
                        estimate { id }
                        user { id }
                    }
                }
                pageInfo {
                    hasNextPage
                    endCursor
                }
            }
        }
        """

        while True:
            page += 1

            try:
                # Exécuter la query
                variables = {
                    "cursor": cursor,
                    "occurredAtGte": start_date,
                    "occurredAtLte": end_date
                }

                result = self.api_client._execute_query(query, variables)
                entries_data = result.get('allTimelineEntries', {})
                edges = entries_data.get('edges', [])
                page_info = entries_data.get('pageInfo', {})

                if not edges:
                    print(f"   📄 Page {page}: 0 entrées (fin)")
                    break

                print(f"   📄 Page {page}: {len(edges)} entrées récupérées")

                # Synchroniser chaque entrée avec UPSERT
                for edge in edges:
                    entry = edge.get('node', {})
                    entry_id = entry.get('id')

                    # REPRISE INTELLIGENTE: Skip si déjà dans Supabase
                    if entry_id in existing_ids:
                        skipped += 1
                        continue

                    try:
                        # Préparer le record Supabase
                        # CORRECTION TIMEZONE: S'assurer que occurred_at est offset-aware
                        occurred_at_raw = entry.get('occurredAt')
                        occurred_at_aware = None
                        if occurred_at_raw:
                            try:
                                # Parser la date ISO et s'assurer qu'elle est timezone-aware
                                dt = datetime.fromisoformat(occurred_at_raw.replace('Z', '+00:00'))
                                if dt.tzinfo is None:
                                    dt = dt.replace(tzinfo=timezone.utc)
                                occurred_at_aware = dt.isoformat()
                            except Exception as e_date:
                                print(f"   ⚠️  Erreur parsing date {occurred_at_raw}: {e_date}")
                                occurred_at_aware = occurred_at_raw  # Fallback

                        record = {
                            'external_id': entry_id,
                            'entry_type': entry.get('type'),
                            'description': entry.get('comment'),
                            'title': entry.get('summary'),
                            'occurred_at': occurred_at_aware,
                            'entity_id': entry.get('client', {}).get('id') if entry.get('client') else None,
                            'piano_id': entry.get('piano', {}).get('id') if entry.get('piano') else None,
                            'user_id': entry.get('user', {}).get('id') if entry.get('user') else None,
                            'invoice_id': entry.get('invoice', {}).get('id') if entry.get('invoice') else None,
                            'estimate_id': entry.get('estimate', {}).get('id') if entry.get('estimate') else None
                        }

                        # UPSERT SÉCURISÉ - on_conflict évite les doublons
                        url = f"{self.storage.api_url}/gazelle_timeline_entries?on_conflict=external_id"
                        headers = self.storage._get_headers()
                        headers['Prefer'] = 'resolution=merge-duplicates'

                        resp = requests.post(url, headers=headers, json=record)

                        if resp.status_code in [200, 201]:
                            synced += 1
                            existing_ids.add(entry_id)  # Ajouter au set pour éviter duplicata
                        else:
                            errors += 1
                            if errors <= 5:  # Afficher seulement les 5 premières erreurs
                                print(f"   ⚠️  Erreur entry {entry_id}: {resp.status_code}")

                    except Exception as e:
                        errors += 1
                        if errors <= 5:
                            print(f"   ❌ Exception entry {entry_id}: {str(e)[:50]}")

                # Vérifier si on doit continuer
                has_next = page_info.get('hasNextPage', False)
                if not has_next:
                    print(f"   ✅ Fin de l'année (dernière page)")
                    break

                cursor = page_info.get('endCursor')

            except Exception as e:
                print(f"   ❌ Erreur page {page}: {e}")
                errors += len(edges) if edges else 0
                break

        print(f"\n📊 Année {year} - Résumé:")
        print(f"   ✅ Synchronisées: {synced}")
        print(f"   ⏭️  Sautées (déjà présentes): {skipped}")
        print(f"   ❌ Erreurs: {errors}")

        self.total_timeline_synced += synced
        self.total_timeline_errors += errors

        return {'synced': synced, 'errors': errors, 'skipped': skipped}

    def backfill_pianos(self) -> int:
        """
        Récupère TOUS les pianos (historique complet).

        Returns:
            Nombre de pianos synchronisés
        """
        print(f"\n{'='*70}")
        print(f"🎹 SYNCHRONISATION COMPLÈTE DES PIANOS")
        print(f"{'='*70}")

        try:
            # Utiliser la méthode existante du syncer
            from modules.sync_gazelle.sync_to_supabase import GazelleToSupabaseSync
            syncer = GazelleToSupabaseSync()

            count = syncer.sync_pianos()
            self.total_pianos_synced = count

            print(f"✅ Pianos synchronisés: {count}")
            return count

        except Exception as e:
            print(f"❌ Erreur sync pianos: {e}")
            return 0

    def backfill_clients(self) -> int:
        """
        Récupère TOUS les clients (historique complet).

        Returns:
            Nombre de clients synchronisés
        """
        print(f"\n{'='*70}")
        print(f"🏢 SYNCHRONISATION COMPLÈTE DES CLIENTS")
        print(f"{'='*70}")

        try:
            # Utiliser la méthode existante du syncer
            from modules.sync_gazelle.sync_to_supabase import GazelleToSupabaseSync
            syncer = GazelleToSupabaseSync()

            count = syncer.sync_clients()
            self.total_clients_synced = count

            print(f"✅ Clients synchronisés: {count}")
            return count

        except Exception as e:
            print(f"❌ Erreur sync clients: {e}")
            return 0

    def run_full_backfill(self, start_year: int = 2016, end_year: int = 2026):
        """
        Exécute la restauration historique complète.

        Args:
            start_year: Première année à synchroniser
            end_year: Dernière année à synchroniser
        """
        print("\n" + "="*70)
        print("🚀 RESTAURATION HISTORIQUE PROFONDE GAZELLE")
        print("="*70)
        print(f"Période: {start_year} - {end_year}")
        print(f"Mode: UPSERT sécurisé (pas de suppression)")
        print(f"Démarrage: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print("="*70)

        start_time = datetime.now(timezone.utc)

        # 1. Synchroniser les clients (requis pour les relations)
        print("\n📍 ÉTAPE 1/3: Clients")
        self.backfill_clients()

        # 2. Synchroniser les pianos (requis pour les relations)
        print("\n📍 ÉTAPE 2/3: Pianos")
        self.backfill_pianos()

        # 3. Récupérer les IDs déjà synchronisés (REPRISE INTELLIGENTE)
        print("\n📍 ÉTAPE 3a/3: Reprise intelligente")
        existing_ids = self.get_existing_timeline_ids()

        # 4. Synchroniser les timeline entries année par année
        print("\n📍 ÉTAPE 3b/3: Timeline Entries (année par année)")

        for year in range(start_year, end_year + 1):
            self.backfill_timeline_year(year, existing_ids)

        # Résumé final
        end_time = datetime.now(timezone.utc)
        duration = (end_time - start_time).total_seconds()

        print("\n" + "="*70)
        print("✅ RESTAURATION HISTORIQUE TERMINÉE")
        print("="*70)
        print(f"📊 Résumé global:")
        print(f"   Clients synchronisés: {self.total_clients_synced}")
        print(f"   Pianos synchronisés: {self.total_pianos_synced}")
        print(f"   Timeline synchronisées: {self.total_timeline_synced}")
        print(f"   Timeline erreurs: {self.total_timeline_errors}")
        print(f"\n⏱️  Durée totale: {duration:.1f} secondes")
        print(f"🕐 Fin: {end_time.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print("="*70)


def main():
    """Point d'entrée du script."""
    parser = argparse.ArgumentParser(
        description="Restauration historique profonde Gazelle (2016-2026)"
    )
    parser.add_argument(
        '--start-year',
        type=int,
        default=2016,
        help='Première année à synchroniser (défaut: 2016)'
    )
    parser.add_argument(
        '--end-year',
        type=int,
        default=2026,
        help='Dernière année à synchroniser (défaut: 2026)'
    )

    args = parser.parse_args()

    # Validation
    if args.start_year > args.end_year:
        print("❌ Erreur: start-year doit être <= end-year")
        sys.exit(1)

    if args.start_year < 2016 or args.end_year > 2026:
        print("❌ Erreur: Les années doivent être entre 2016 et 2026")
        sys.exit(1)

    # Exécution
    service = DeepBackfillService()
    service.run_full_backfill(
        start_year=args.start_year,
        end_year=args.end_year
    )


if __name__ == '__main__':
    main()
