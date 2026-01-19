#!/usr/bin/env python3
"""
BACKFILL HISTORIQUE RÉSILIENT 2016-2026
Avec retry automatique et logging détaillé tous les 2,000 items
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


def backfill_all(start_year: int, end_year: int, api_client, storage):
    """Backfill complet avec gestion d'erreurs et logging détaillé."""

    start_date = f"{start_year}-01-01T00:00:00Z"

    print(f"\n{'='*70}")
    print(f"📅 BACKFILL COMPLET {start_year}-{end_year}")
    print(f"{'='*70}")
    print(f"📍 Start: {start_date}")
    print(f"📊 Journal de bord: tous les 2,000 items")
    print(f"🔄 Retry automatique: 3 tentatives avec pause 5s")
    print(f"{'='*70}\n")

    synced = 0
    errors = 0
    cursor = None
    page = 0
    last_year_month = None

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
        retry_count = 0
        max_retries = 3
        page_success = False

        # RETRY LOGIC pour chaque page
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

                                # Extraire année/mois pour le journal de bord
                                year_month = occurred_at_raw[:7]  # "2024-03"

                            except Exception:
                                occurred_at_aware = occurred_at_raw
                                year_month = None

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

                        # UPSERT SÉCURISÉ avec retry
                        upsert_success = False
                        upsert_retry = 0

                        while upsert_retry < 3 and not upsert_success:
                            try:
                                url = f"{storage.api_url}/gazelle_timeline_entries?on_conflict=external_id"
                                headers = storage._get_headers()
                                headers['Prefer'] = 'resolution=merge-duplicates'

                                resp = requests.post(url, headers=headers, json=record, timeout=10)

                                if resp.status_code in [200, 201, 409]:  # 409 = déjà existant (OK)
                                    synced += 1
                                    upsert_success = True

                                    # JOURNAL DE BORD tous les 2,000 items
                                    if synced % 2000 == 0:
                                        print(f"📊 [{synced:,} items] Traitement: {year_month} | Page {page}", flush=True)

                                else:
                                    upsert_retry += 1
                                    if upsert_retry < 3:
                                        time.sleep(1)

                            except requests.exceptions.RequestException as req_err:
                                upsert_retry += 1
                                if upsert_retry < 3:
                                    time.sleep(2)

                        if not upsert_success:
                            errors += 1
                            if errors <= 5:
                                print(f"⚠️  Erreur persistante {entry_id}", flush=True)

                    except Exception as e:
                        errors += 1
                        if errors <= 5:
                            print(f"❌ Exception {entry_id}: {str(e)[:80]}", flush=True)

                # Vérifier pagination
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
                    errors += 100  # Pénalité pour page échouée
                    return {'synced': synced, 'errors': errors}

        if not page_success:
            print(f"❌ Impossible de récupérer la page {page} - Arrêt", flush=True)
            break

        if not nodes:
            break

    return {'synced': synced, 'errors': errors}


def main():
    parser = argparse.ArgumentParser(description="Backfill résilient timeline 2016-2026")
    parser.add_argument('--start-year', type=int, default=2016)
    parser.add_argument('--end-year', type=int, default=2026)
    args = parser.parse_args()

    print("\n" + "="*70)
    print("🚀 RESTAURATION HISTORIQUE TIMELINE GAZELLE (RÉSILIENT)")
    print("="*70)
    print(f"Période: {args.start_year} - {args.end_year}")
    print(f"Mode: UPSERT sécurisé (pas de suppression)")
    print(f"Retry: Automatique avec pause 5s")
    print(f"Logging: Journal de bord tous les 2,000 items")
    print("="*70)

    api_client = GazelleAPIClient()
    storage = SupabaseStorage()

    start_time = time.time()
    result = backfill_all(args.start_year, args.end_year, api_client, storage)
    elapsed = time.time() - start_time

    print("\n" + "="*70)
    print("✅ RESTAURATION TERMINÉE")
    print("="*70)
    print(f"📊 Total synchronisées: {result['synced']:,}")
    print(f"📊 Total erreurs: {result['errors']}")
    print(f"⏱️  Durée: {elapsed/60:.1f} minutes")
    print("="*70 + "\n")


if __name__ == '__main__':
    main()
