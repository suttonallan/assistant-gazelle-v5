#!/usr/bin/env python3
"""
BACKFILL TIMELINE UNIQUEMENT (sans sync clients/pianos)

Usage:
    python3 scripts/backfill_timeline_only.py --year 2017
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import argparse
import requests
from datetime import datetime, timezone
from core.gazelle_api_client import GazelleAPIClient
from core.supabase_storage import SupabaseStorage


def backfill_timeline_year(year: int):
    """Récupère toutes les timeline entries pour une année."""

    api_client = GazelleAPIClient()
    storage = SupabaseStorage()

    print(f"\n{'='*70}")
    print(f"📅 BACKFILL TIMELINE {year}")
    print(f"{'='*70}\n")

    start_date = f"{year}-01-01T00:00:00Z"
    end_date = f"{year}-12-31T23:59:59Z"

    print(f"📍 Période: {start_date} → {end_date}\n")

    synced = 0
    errors = 0
    cursor = None
    page = 0

    query = """
    query GetTimelineYear($cursor: String, $occurredAtGet: CoreDateTime) {
        allTimelineEntries(
            first: 100,
            after: $cursor,
            occurredAtGet: $occurredAtGet
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
            variables = {
                "cursor": cursor,
                "occurredAtGet": start_date
            }

            print(f"   📄 Page {page}: Récupération...")

            result = api_client._execute_query(query, variables)
            entries_data = result.get('allTimelineEntries', {})
            edges = entries_data.get('edges', [])
            page_info = entries_data.get('pageInfo', {})

            if not edges:
                print(f"   ✅ Page {page}: 0 entrées (fin)")
                break

            print(f"   ✅ Page {page}: {len(edges)} entrées récupérées")

            # Synchroniser chaque entrée
            for edge in edges:
                entry = edge.get('node', {})
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
                            print(f"      → {synced} entrées synchronisées...")
                    else:
                        errors += 1
                        if errors <= 3:
                            print(f"   ⚠️  Erreur {entry_id}: {resp.status_code} - {resp.text[:100]}")

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
            errors += len(edges) if edges else 0
            break

    print(f"{'='*70}")
    print(f"📊 RÉSUMÉ {year}:")
    print(f"   ✅ Synchronisées: {synced}")
    print(f"   ❌ Erreurs: {errors}")
    print(f"{'='*70}\n")

    return {'synced': synced, 'errors': errors}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Backfill timeline pour une année")
    parser.add_argument('--year', type=int, required=True, help='Année à synchroniser')

    args = parser.parse_args()

    if args.year < 2016 or args.year > 2026:
        print("❌ Année doit être entre 2016 et 2026")
        sys.exit(1)

    backfill_timeline_year(args.year)
