#!/usr/bin/env python3
"""
BACKFILL OPTIMISÉ AVEC BATCH INSERTS
100 entrées par page = 1 seul UPSERT massif
Journal de bord: Année/Mois pour suivre la progression
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


def backfill_batch(start_year: int, end_year: int, api_client, storage):
    """Backfill avec batch inserts pour performance maximale."""

    start_date = f"{start_year}-01-01T00:00:00Z"

    print(f"\n{'='*70}")
    print(f"🚀 BACKFILL BATCH OPTIMISÉ {start_year}-{end_year}")
    print(f"{'='*70}")
    print(f"📍 Start: {start_date}")
    print(f"⚡ Mode: Batch insert (100 entrées/requête)")
    print(f"📊 Journal: Année/Mois en cours de traitement")
    print(f"{'='*70}\n")

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
        retry_count = 0
        max_retries = 3
        page_success = False

        while retry_count < max_retries and not page_success:
            try:
                variables = {
                    "first": 100,
                    "after": cursor,
                    "occurredAtGet": start_date
                }

                result = api_client._execute_query(query, variables)
                connection = result.get('data', {}).get('allTimelineEntries', {})
                nodes = connection.get('nodes', [])
                page_info = connection.get('pageInfo', {})
                total_count = connection.get('totalCount', 'N/A')

                if page == 1:
                    print(f"ℹ️  Total disponible: {total_count:,}\n", flush=True)

                if not nodes:
                    print(f"\n✅ FIN - Page {page}: 0 entrées", flush=True)
                    page_success = True
                    break

                # BATCH: Préparer toutes les entrées de la page
                batch_records = []
                year_months = set()

                for entry in nodes:
                    try:
                        occurred_at_raw = entry.get('occurredAt')
                        occurred_at_aware = None

                        if occurred_at_raw:
                            try:
                                dt = datetime.fromisoformat(occurred_at_raw.replace('Z', '+00:00'))
                                if dt.tzinfo is None:
                                    dt = dt.replace(tzinfo=timezone.utc)
                                occurred_at_aware = dt.isoformat()

                                # Collecter année/mois pour le journal
                                year_month = occurred_at_raw[:7]  # "2024-03"
                                year_months.add(year_month)

                            except Exception:
                                occurred_at_aware = occurred_at_raw

                        record = {
                            'external_id': entry.get('id'),
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

                        batch_records.append(record)

                    except Exception as e:
                        errors += 1
                        if errors <= 5:
                            print(f"⚠️  Erreur préparation: {str(e)[:80]}", flush=True)

                # BATCH UPSERT: Un seul POST avec toutes les entrées
                if batch_records:
                    batch_retry = 0
                    batch_success = False

                    while batch_retry < 3 and not batch_success:
                        try:
                            url = f"{storage.api_url}/gazelle_timeline_entries"
                            headers = storage._get_headers()
                            headers['Prefer'] = 'resolution=merge-duplicates'

                            # POST avec toutes les entrées en une fois
                            resp = requests.post(url, headers=headers, json=batch_records, timeout=30)

                            if resp.status_code in [200, 201]:
                                synced += len(batch_records)
                                batch_success = True

                                # Afficher année/mois en cours
                                year_month_str = ", ".join(sorted(year_months))
                                elapsed = time.time() - start_time
                                rate = synced / elapsed if elapsed > 0 else 0

                                print(f"📊 Page {page:4d} | {len(batch_records):3d} items | {year_month_str:20s} | Total: {synced:6,} | {rate:.0f} items/s", flush=True)

                            else:
                                batch_retry += 1
                                if batch_retry < 3:
                                    print(f"⚠️  Retry batch (HTTP {resp.status_code})...", flush=True)
                                    time.sleep(2)
                                else:
                                    errors += len(batch_records)
                                    print(f"❌ Échec batch page {page}: {resp.status_code}", flush=True)

                        except requests.exceptions.RequestException as req_err:
                            batch_retry += 1
                            if batch_retry < 3:
                                print(f"⚠️  Retry connexion (tentative {batch_retry})...", flush=True)
                                time.sleep(5)
                            else:
                                errors += len(batch_records)
                                print(f"❌ Échec connexion page {page}", flush=True)

                    if not batch_success:
                        print(f"❌ Page {page} non insérée après 3 tentatives", flush=True)

                # Pagination
                has_next = page_info.get('hasNextPage', False)
                if not has_next:
                    print(f"\n✅ Fin de la pagination à la page {page}", flush=True)
                    page_success = True
                    break

                cursor = page_info.get('endCursor')
                page_success = True

            except Exception as e:
                retry_count += 1
                print(f"⚠️  Erreur API page {page} (tentative {retry_count}/{max_retries}): {str(e)[:100]}", flush=True)

                if retry_count < max_retries:
                    print(f"⏸️  Pause 5 secondes avant retry...", flush=True)
                    time.sleep(5)
                else:
                    print(f"❌ Échec après {max_retries} tentatives - Arrêt", flush=True)
                    return {'synced': synced, 'errors': errors}

        if not page_success or not nodes:
            break

    return {'synced': synced, 'errors': errors}


def main():
    parser = argparse.ArgumentParser(description="Backfill batch optimisé")
    parser.add_argument('--start-year', type=int, default=2016)
    parser.add_argument('--end-year', type=int, default=2026)
    parser.add_argument('--test-pages', type=int, default=0, help="Test avec N pages seulement")
    args = parser.parse_args()

    print("\n" + "="*70)
    print("🚀 RESTAURATION BATCH OPTIMISÉE")
    print("="*70)
    print(f"Période: {args.start_year} - {args.end_year}")
    print(f"Mode: BATCH UPSERT (100 entrées/requête)")
    if args.test_pages:
        print(f"⚡ MODE TEST: {args.test_pages} pages seulement")
    print("="*70)

    api_client = GazelleAPIClient()
    storage = SupabaseStorage()

    start_time = time.time()

    # Modification pour mode test
    if args.test_pages > 0:
        # Mode test: on intercepte après N pages
        original_backfill = backfill_batch

        def test_backfill(start_year, end_year, api, stor):
            result = {'synced': 0, 'errors': 0}
            start_date = f"{start_year}-01-01T00:00:00Z"
            cursor = None

            query = """
            query($first: Int, $after: String, $occurredAtGet: CoreDateTime) {
                allTimelineEntries(first: $first, after: $after, occurredAtGet: $occurredAtGet) {
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

            for page in range(1, args.test_pages + 1):
                variables = {"first": 100, "after": cursor, "occurredAtGet": start_date}
                res = api._execute_query(query, variables)
                connection = res.get('data', {}).get('allTimelineEntries', {})
                nodes = connection.get('nodes', [])
                page_info = connection.get('pageInfo', {})

                if not nodes:
                    break

                # Batch insert
                batch_records = []
                year_months = set()

                for entry in nodes:
                    occurred_at_raw = entry.get('occurredAt')
                    occurred_at_aware = None

                    if occurred_at_raw:
                        dt = datetime.fromisoformat(occurred_at_raw.replace('Z', '+00:00'))
                        if dt.tzinfo is None:
                            dt = dt.replace(tzinfo=timezone.utc)
                        occurred_at_aware = dt.isoformat()
                        year_months.add(occurred_at_raw[:7])

                    batch_records.append({
                        'external_id': entry.get('id'),
                        'entry_type': entry.get('type'),
                        'description': entry.get('comment'),
                        'title': entry.get('summary'),
                        'occurred_at': occurred_at_aware,
                        'entity_id': entry.get('client', {}).get('id') if entry.get('client') else None,
                        'piano_id': entry.get('piano', {}).get('id') if entry.get('piano') else None,
                        'user_id': entry.get('user', {}).get('id') if entry.get('user') else None,
                        'invoice_id': entry.get('invoice', {}).get('id') if entry.get('invoice') else None,
                        'estimate_id': entry.get('estimate', {}).get('id') if entry.get('estimate') else None
                    })

                # Batch insert
                url = f"{stor.api_url}/gazelle_timeline_entries"
                headers = stor._get_headers()
                headers['Prefer'] = 'resolution=merge-duplicates'
                resp = requests.post(url, headers=headers, json=batch_records, timeout=30)

                if resp.status_code in [200, 201]:
                    result['synced'] += len(batch_records)
                    year_month_str = ", ".join(sorted(year_months))
                    elapsed = time.time() - start_time
                    rate = result['synced'] / elapsed if elapsed > 0 else 0
                    print(f"📊 Page {page:4d} | {len(batch_records):3d} items | {year_month_str:20s} | Total: {result['synced']:6,} | {rate:.0f} items/s", flush=True)

                cursor = page_info.get('endCursor')
                if not page_info.get('hasNextPage'):
                    break

            return result

        result = test_backfill(args.start_year, args.end_year, api_client, storage)
    else:
        result = backfill_batch(args.start_year, args.end_year, api_client, storage)

    elapsed = time.time() - start_time

    print("\n" + "="*70)
    print("✅ TERMINÉ")
    print("="*70)
    print(f"📊 Total synchronisées: {result['synced']:,}")
    print(f"📊 Total erreurs: {result['errors']}")
    print(f"⏱️  Durée: {elapsed:.1f} secondes ({elapsed/60:.1f} minutes)")
    if result['synced'] > 0:
        print(f"⚡ Vitesse moyenne: {result['synced']/elapsed:.0f} entrées/seconde")
    print("="*70 + "\n")


if __name__ == '__main__':
    main()
