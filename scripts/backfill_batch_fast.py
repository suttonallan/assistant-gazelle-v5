#!/usr/bin/env python3
"""
BACKFILL BATCH RAPIDE
100 entrées par page = 1 seul POST
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import argparse
import requests
import time
from datetime import datetime, timezone
from core.gazelle_api_client import GazelleAPIClient
from core.supabase_storage import SupabaseStorage


def main():
    parser = argparse.ArgumentParser(description="Backfill batch rapide")
    parser.add_argument('--start-year', type=int, default=2016)
    parser.add_argument('--max-pages', type=int, default=0, help="Limiter à N pages (0=illimité)")
    args = parser.parse_args()

    print("\n" + "="*70)
    print("🚀 BACKFILL BATCH RAPIDE")
    print("="*70)
    print(f"Année de départ: {args.start_year}")
    print(f"Mode: BATCH INSERT (100 entrées/POST)")
    if args.max_pages:
        print(f"⚡ LIMITE: {args.max_pages} pages")
    print("="*70 + "\n")

    api_client = GazelleAPIClient()
    storage = SupabaseStorage()

    start_date = f"{args.start_year}-01-01T00:00:00Z"
    synced = 0
    errors = 0
    cursor = None
    page = 0
    start_time = time.time()

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

        # Limite de pages pour test
        if args.max_pages > 0 and page > args.max_pages:
            print(f"\n⚠️  Limite de {args.max_pages} pages atteinte\n", flush=True)
            break

        try:
            # Récupérer la page
            variables = {"first": 100, "after": cursor, "occurredAtGet": start_date}
            result = api_client._execute_query(query, variables)
            connection = result.get('data', {}).get('allTimelineEntries', {})
            nodes = connection.get('nodes', [])
            page_info = connection.get('pageInfo', {})
            total_count = connection.get('totalCount', 'N/A')

            if page == 1:
                print(f"ℹ️  Total disponible: {total_count:,}\n", flush=True)

            if not nodes:
                print(f"\n✅ FIN - Aucune entrée à la page {page}", flush=True)
                break

            # Préparer batch
            batch_records = []
            year_months = set()
            skipped = 0

            # Types valides seulement
            VALID_TYPES = {'NOTE', 'APPOINTMENT', 'APPOINTMENT_COMPLETION'}

            for entry in nodes:
                # Filtrer types invalides
                entry_type = entry.get('type')
                if entry_type not in VALID_TYPES:
                    skipped += 1
                    continue

                occurred_at_raw = entry.get('occurredAt', '')
                occurred_at_aware = None

                if occurred_at_raw:
                    try:
                        dt = datetime.fromisoformat(occurred_at_raw.replace('Z', '+00:00'))
                        if dt.tzinfo is None:
                            dt = dt.replace(tzinfo=timezone.utc)
                        occurred_at_aware = dt.isoformat()
                        year_months.add(occurred_at_raw[:7])  # "2024-03"
                    except:
                        occurred_at_aware = occurred_at_raw

                # Ignorer les foreign keys pour éviter erreurs de contraintes
                batch_records.append({
                    'external_id': entry.get('id'),
                    'entry_type': entry_type,
                    'description': entry.get('comment'),
                    'title': entry.get('summary'),
                    'occurred_at': occurred_at_aware,
                    'entity_id': None,  # Ignorer pour éviter FK errors
                    'piano_id': None,
                    'user_id': None,
                    'invoice_id': None,
                    'estimate_id': None
                })

            # BATCH UPSERT avec on_conflict
            url = f"{storage.api_url}/gazelle_timeline_entries?on_conflict=external_id"
            headers = storage._get_headers()
            headers['Prefer'] = 'resolution=merge-duplicates,return=minimal'

            resp = requests.post(url, headers=headers, json=batch_records, timeout=30)

            if resp.status_code in [200, 201]:
                synced += len(batch_records)
                year_month_str = ", ".join(sorted(year_months))
                elapsed = time.time() - start_time
                rate = synced / elapsed if elapsed > 0 else 0

                print(f"📊 Page {page:4d} | {len(batch_records):3d} items | {year_month_str:20s} | Total: {synced:6,} | {rate:5.0f}/s", flush=True)
            else:
                errors += len(batch_records)
                print(f"❌ Page {page}: HTTP {resp.status_code} - {resp.text[:100]}", flush=True)

            # Pagination
            if not page_info.get('hasNextPage'):
                print(f"\n✅ Fin de la pagination", flush=True)
                break

            cursor = page_info.get('endCursor')

        except Exception as e:
            print(f"❌ Erreur page {page}: {str(e)[:150]}", flush=True)
            errors += 100

            # Retry après pause
            print(f"⏸️  Pause 5s et retry...", flush=True)
            time.sleep(5)
            continue

    elapsed = time.time() - start_time

    print("\n" + "="*70)
    print("✅ TERMINÉ")
    print("="*70)
    print(f"📊 Pages traitées: {page}")
    print(f"📊 Entrées synchronisées: {synced:,}")
    print(f"📊 Erreurs: {errors}")
    print(f"⏱️  Durée: {elapsed:.1f}s ({elapsed/60:.1f}min)")
    if synced > 0 and elapsed > 0:
        print(f"⚡ Vitesse: {synced/elapsed:.0f} entrées/seconde")
        print(f"⚡ Estimation 150K entrées: {150000/(synced/elapsed)/60:.0f} minutes")
    print("="*70 + "\n")


if __name__ == '__main__':
    main()
