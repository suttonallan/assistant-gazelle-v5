#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════════════╗
║          RESTAURATION HISTORIQUE FINALE 2016-2026 (SCHÉMA VALIDÉ)         ║
║                 Basé sur le schéma PrivateQuery Gazelle                    ║
╚═══════════════════════════════════════════════════════════════════════════╝

CORRECTIONS CRITIQUES appliquées:
1. occurredAtGet (pas occurredAtGte/Lte) - seul filtre valide
2. Format UTC avec Z: "2016-01-01T05:00:00Z" (timezone Montréal = UTC-5)
3. Syntaxe nodes (validée par scripts/import_timeline_entries.py)
4. Filtrage Python: NOTE et APPOINTMENT_COMPLETION (comptes-rendus techniques)
5. UPSERT strict avec .get() sécurisés (pas de NoneType crashes)

Usage:
    python3 scripts/backfill_final_2016_2026.py --start-year 2016 --end-year 2026
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import argparse
import requests
from datetime import datetime, timezone
from core.gazelle_api_client import GazelleAPIClient
from core.supabase_storage import SupabaseStorage


# Types timeline pertinents (comptes-rendus techniques + notes)
RELEVANT_TYPES = {'NOTE', 'APPOINTMENT_COMPLETION'}


def backfill_year(year: int, api_client, storage):
    """
    Backfill une année complète avec occurredAtGet (SCHÉMA GAZELLE VALIDÉ).

    IMPORTANT: occurredAtGet signifie "Greater or Equal To" mais NÉCESSITE
    le format UTC avec Z (ex: 2016-01-01T05:00:00Z pour Montréal).
    """

    # Montréal = UTC-5 en hiver, UTC-4 en été
    # Pour capturer TOUT 2016 à Montréal, commencer à 05:00:00 UTC le 1er janvier
    start_date = f"{year}-01-01T05:00:00Z"

    print(f"\n{'='*70}")
    print(f"📅 BACKFILL {year}")
    print(f"{'='*70}")
    print(f"📍 occurredAtGet: {start_date} (Montréal timezone-aware)")
    print(f"📍 Types recherchés: {', '.join(RELEVANT_TYPES)}\n")

    synced = 0
    errors = 0
    skipped_types = 0
    cursor = None
    page = 0

    # SCHÉMA GAZELLE VALIDÉ (PrivateQuery)
    query = """
    query GetTimelineYear($first: Int, $after: String, $occurredAtGet: CoreDateTime) {
        allTimelineEntries(
            first: $first,
            after: $after,
            occurredAtGet: $occurredAtGet
        ) {
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

            print(f"   📄 Page {page}: Récupération...")

            result = api_client._execute_query(query, variables)
            connection = result.get('allTimelineEntries', {})
            nodes = connection.get('nodes', [])
            page_info = connection.get('pageInfo', {})
            total_count = connection.get('totalCount')

            if page == 1 and total_count is not None:
                print(f"   ℹ️  Total disponible depuis {year}: {total_count}")

            if not nodes:
                print(f"   ✅ Page {page}: 0 entrées (fin)")
                break

            print(f"   ✅ Page {page}: {len(nodes)} entrées récupérées")

            # Filtrer et synchroniser
            for entry in nodes:
                entry_id = entry.get('id')
                entry_type = entry.get('type')

                # FILTRAGE PYTHON: Seulement NOTE et APPOINTMENT_COMPLETION
                if entry_type not in RELEVANT_TYPES:
                    skipped_types += 1
                    continue

                try:
                    # Parser occurred_at avec timezone awareness
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

                    # SÉCURISÉ: .get() partout pour éviter NoneType
                    record = {
                        'external_id': entry_id,
                        'entry_type': entry_type,
                        'description': entry.get('comment'),
                        'title': entry.get('summary'),
                        'occurred_at': occurred_at_aware,
                        'entity_id': (entry.get('client') or {}).get('id'),
                        'piano_id': (entry.get('piano') or {}).get('id'),
                        'user_id': (entry.get('user') or {}).get('id'),
                        'invoice_id': (entry.get('invoice') or {}).get('id'),
                        'estimate_id': (entry.get('estimate') or {}).get('id')
                    }

                    # UPSERT STRICT (on_conflict = jamais de suppression)
                    url = f"{storage.api_url}/gazelle_timeline_entries?on_conflict=external_id"
                    headers = storage._get_headers()
                    headers['Prefer'] = 'resolution=merge-duplicates'

                    resp = requests.post(url, headers=headers, json=record)

                    if resp.status_code in [200, 201]:
                        synced += 1
                        if synced % 50 == 0:
                            print(f"      → {synced} entrées synchronisées...")
                    else:
                        errors += 1
                        if errors <= 3:
                            print(f"   ⚠️  Erreur {entry_id}: {resp.status_code}")

                except Exception as e:
                    errors += 1
                    if errors <= 3:
                        print(f"   ❌ Exception {entry_id}: {str(e)[:100]}")

            # Vérifier si on continue (occurredAtGet = toutes les années suivantes)
            # Il faut s'arrêter quand on dépasse l'année cible
            if nodes:
                # Vérifier la date de la dernière entrée
                last_entry = nodes[-1]
                last_date_raw = last_entry.get('occurredAt', '')

                if last_date_raw:
                    try:
                        last_year = int(last_date_raw[:4])
                        if last_year > year:
                            print(f"   ⏹️  Arrêt: entrées de {last_year} détectées (hors plage {year})")
                            break
                    except Exception:
                        pass

            # Vérifier pagination
            has_next = page_info.get('hasNextPage', False)
            if not has_next:
                print(f"   ✅ Fin de pagination\n")
                break

            cursor = page_info.get('endCursor')

        except Exception as e:
            print(f"   ❌ Erreur page {page}: {e}")
            errors += len(nodes) if 'nodes' in locals() and nodes else 0
            break

    print(f"{'='*70}")
    print(f"📊 RÉSUMÉ {year}:")
    print(f"   ✅ Synchronisées (NOTE + APPOINTMENT_COMPLETION): {synced}")
    print(f"   ⏭️  Ignorées (autres types): {skipped_types}")
    print(f"   ❌ Erreurs: {errors}")
    print(f"{'='*70}\n")

    return {'synced': synced, 'errors': errors, 'skipped': skipped_types}


def main():
    parser = argparse.ArgumentParser(
        description="Backfill timeline 2016-2026 (schéma Gazelle validé)"
    )
    parser.add_argument('--start-year', type=int, default=2016)
    parser.add_argument('--end-year', type=int, default=2026)
    args = parser.parse_args()

    print("\n" + "="*70)
    print("🚀 RESTAURATION HISTORIQUE GAZELLE (SCHÉMA VALIDÉ)")
    print("="*70)
    print(f"Période: {args.start_year} - {args.end_year}")
    print(f"Filtre: occurredAtGet avec format UTC Z")
    print(f"Types: NOTE + APPOINTMENT_COMPLETION (comptes-rendus)")
    print(f"Mode: UPSERT sécurisé (jamais de suppression)")
    print("="*70)

    api_client = GazelleAPIClient()
    storage = SupabaseStorage()

    total_synced = 0
    total_errors = 0
    total_skipped = 0

    for year in range(args.start_year, args.end_year + 1):
        result = backfill_year(year, api_client, storage)
        total_synced += result['synced']
        total_errors += result['errors']
        total_skipped += result['skipped']

    print("\n" + "="*70)
    print("✅ RESTAURATION TERMINÉE")
    print("="*70)
    print(f"📊 Total synchronisées: {total_synced:,}")
    print(f"📊 Total ignorées (autres types): {total_skipped:,}")
    print(f"📊 Total erreurs: {total_errors}")
    print("="*70 + "\n")


if __name__ == '__main__':
    main()
