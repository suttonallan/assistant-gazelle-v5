#!/usr/bin/env python3
"""
BACKFILL HISTORIQUE COMPLET 2016-2026
Basé sur scripts/import_timeline_entries.py (syntaxe nodes validée)
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import argparse
import requests
from datetime import datetime, timezone
from core.gazelle_api_client import GazelleAPIClient
from core.supabase_storage import SupabaseStorage


def backfill_year(year: int, api_client, storage):
    """Backfill une année complète."""

    start_date = f"{year}-01-01T00:00:00Z"
    print(f"\n{'='*70}")
    print(f"📅 BACKFILL {year}")
    print(f"{'='*70}")
    print(f"📍 Start: {start_date}\n")

    synced = 0
    errors = 0
    cursor = None
    page = 0

    # SYNTAXE VALIDÉE (avec nodes, pas edges)
    query = """
    query($first: Int, $after: String, $occurredAtGet: CoreDateTime) {
        allTimelineEntries(first: $first, after: $after, occurredAtGet: $occurredAtGet) {
            totalCount
            nodes {
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
            variables = {
                "first": 100,
                "after": cursor,
                "occurredAtGet": start_date
            }

            print(f"   📄 Page {page}: Récupération...", flush=True)

            result = api_client._execute_query(query, variables)
            connection = result.get('data', {}).get('allTimelineEntries', {})
            nodes = connection.get('nodes', [])
            page_info = connection.get('pageInfo', {})
            total_count = connection.get('totalCount', 'N/A')

            if page == 1:
                print(f"   ℹ️  Total disponible: {total_count}")

            if not nodes:
                print(f"   ✅ Page {page}: 0 entrées (fin)")
                break

            print(f"   ✅ Page {page}: {len(nodes)} entrées récupérées", flush=True)

            # Synchroniser chaque entrée
            for entry in nodes:
                entry_id = entry.get('id')

                try:
                    # Préparer occurred_at avec timezone
                    occurred_at_raw = entry.get('occurredAt')
                    occurred_at_aware = None
                    if occurred_at_raw:
                        try:
                            dt = datetime.fromisoformat(occurred_at_raw.replace('Z', '+00:00'))
                            if dt.tzinfo is None:
                                dt = dt.replace(tzinfo=timezone.utc)
                            occurred_at_aware = dt.isoformat()
                        except Exception:
                            occurred_at_aware = occurred_at_raw

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

                    # UPSERT SÉCURISÉ
                    url = f"{storage.api_url}/gazelle_timeline_entries?on_conflict=external_id"
                    headers = storage._get_headers()
                    headers['Prefer'] = 'resolution=merge-duplicates'

                    resp = requests.post(url, headers=headers, json=record)

                    if resp.status_code in [200, 201]:
                        synced += 1
                        if synced % 100 == 0:
                            print(f"      → {synced} entrées synchronisées...", flush=True)
                    else:
                        errors += 1
                        if errors <= 3:
                            print(f"   ⚠️  Erreur {entry_id}: {resp.status_code}")

                except Exception as e:
                    errors += 1
                    if errors <= 3:
                        print(f"   ❌ Exception {entry_id}: {str(e)[:100]}")

            # Vérifier pagination
            has_next = page_info.get('hasNextPage', False)
            if not has_next:
                print(f"   ✅ Fin de l'année (dernière page)\n")
                break

            cursor = page_info.get('endCursor')

        except Exception as e:
            print(f"   ❌ Erreur page {page}: {e}")
            errors += len(nodes) if nodes else 0
            break

    print(f"{'='*70}")
    print(f"📊 RÉSUMÉ {year}:")
    print(f"   ✅ Synchronisées: {synced}")
    print(f"   ❌ Erreurs: {errors}")
    print(f"{'='*70}\n")

    return {'synced': synced, 'errors': errors}


def main():
    parser = argparse.ArgumentParser(description="Backfill timeline 2016-2026")
    parser.add_argument('--start-year', type=int, default=2016)
    parser.add_argument('--end-year', type=int, default=2026)
    args = parser.parse_args()

    print("\n" + "="*70)
    print("🚀 RESTAURATION HISTORIQUE TIMELINE GAZELLE")
    print("="*70)
    print(f"Période: {args.start_year} - {args.end_year}")
    print(f"Mode: UPSERT sécurisé (pas de suppression)")
    print("="*70)

    api_client = GazelleAPIClient()
    storage = SupabaseStorage()

    total_synced = 0
    total_errors = 0

    for year in range(args.start_year, args.end_year + 1):
        result = backfill_year(year, api_client, storage)
        total_synced += result['synced']
        total_errors += result['errors']

    print("\n" + "="*70)
    print("✅ RESTAURATION TERMINÉE")
    print("="*70)
    print(f"📊 Total synchronisées: {total_synced:,}")
    print(f"📊 Total erreurs: {total_errors}")
    print("="*70 + "\n")


if __name__ == '__main__':
    main()
