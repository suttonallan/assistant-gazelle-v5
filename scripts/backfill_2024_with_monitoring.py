#!/usr/bin/env python3
"""
BACKFILL 2024 AVEC MONITORING
- Importe l'année 2024 complète
- Monitoring toutes les 500 insertions avec comptage Supabase
- Relance automatique du rapport Google Sheets à la fin
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
from supabase import create_client


def count_timeline_entries(storage):
    """Compte le nombre total d'entrées dans Supabase."""
    try:
        supabase = create_client(storage.supabase_url, storage.supabase_key)
        result = supabase.table('gazelle_timeline_entries')\
            .select('external_id', count='exact')\
            .in_('entry_type', ['SERVICE_ENTRY_MANUAL', 'PIANO_MEASUREMENT'])\
            .execute()
        return result.count or 0
    except Exception as e:
        print(f"⚠️  Erreur comptage Supabase: {e}")
        return None


def backfill_2024(api_client, storage, monitor_interval=500):
    """Backfill 2024 avec monitoring toutes les 500 insertions."""
    
    start_date = "2024-01-01T00:00:00Z"
    
    print(f"\n{'='*70}")
    print(f"📅 BACKFILL 2024 - ANNÉE COMPLÈTE")
    print(f"{'='*70}")
    print(f"📍 Start: {start_date}")
    print(f"📊 Monitoring: toutes les {monitor_interval} insertions")
    print(f"🔄 Retry automatique: 3 tentatives avec pause 5s")
    print(f"{'='*70}\n")
    
    # Comptage initial
    initial_count = count_timeline_entries(storage)
    print(f"📊 Entrées initiales dans Supabase: {initial_count:,}\n")
    
    synced = 0
    errors = 0
    cursor = None
    page = 0
    
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
                    print(f"ℹ️  Total disponible pour 2024+: {total_count:,}\n", flush=True)
                
                if not nodes:
                    print(f"\n✅ FIN - Page {page}: 0 entrées", flush=True)
                    page_success = True
                    break
                
                # Synchroniser chaque entrée
                for entry in nodes:
                    entry_id = entry.get('id')
                    
                    try:
                        occurred_at_raw = entry.get('occurredAt')
                        occurred_at_aware = None
                        
                        if occurred_at_raw:
                            try:
                                dt = datetime.fromisoformat(occurred_at_raw.replace('Z', '+00:00'))
                                if dt.tzinfo is None:
                                    dt = dt.replace(tzinfo=timezone.utc)
                                occurred_at_aware = dt.isoformat()
                                
                                # Filtrer uniquement 2024
                                if dt.year != 2024:
                                    continue  # Ignorer les entrées hors 2024
                                    
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
                        
                        # UPSERT avec retry
                        upsert_success = False
                        upsert_retry = 0
                        
                        while upsert_retry < 3 and not upsert_success:
                            try:
                                url = f"{storage.api_url}/gazelle_timeline_entries?on_conflict=external_id"
                                headers = storage._get_headers()
                                headers['Prefer'] = 'resolution=merge-duplicates'
                                
                                resp = requests.post(url, headers=headers, json=record, timeout=10)
                                
                                if resp.status_code in [200, 201, 409]:
                                    synced += 1
                                    upsert_success = True
                                    
                                    # MONITORING toutes les 500 insertions
                                    if synced % monitor_interval == 0:
                                        current_count = count_timeline_entries(storage)
                                        if current_count is not None:
                                            print(f"📊 [{synced:,} insertions] Total Supabase: {current_count:,} entrées | Page {page}", flush=True)
                                        else:
                                            print(f"📊 [{synced:,} insertions] Traitement en cours... | Page {page}", flush=True)
                                
                                else:
                                    # Afficher l'erreur détaillée pour les 10 premières erreurs
                                    if errors < 10:
                                        error_detail = resp.text[:300] if resp.text else "Pas de détails"
                                        print(f"❌ Erreur HTTP {resp.status_code} pour {entry_id}: {error_detail}", flush=True)
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
                    errors += 100
                    return {'synced': synced, 'errors': errors}
        
        if not page_success:
            print(f"❌ Impossible de récupérer la page {page} - Arrêt", flush=True)
            break
        
        if not nodes:
            break
    
    # Comptage final
    final_count = count_timeline_entries(storage)
    print(f"\n📊 Entrées finales dans Supabase: {final_count:,}")
    if initial_count is not None and final_count is not None:
        added = final_count - initial_count
        print(f"📊 Nouvelles entrées ajoutées: {added:,}")
    
    return {'synced': synced, 'errors': errors, 'initial_count': initial_count, 'final_count': final_count}


def generate_sheets_report():
    """Génère le rapport Google Sheets après le backfill."""
    print("\n" + "="*70)
    print("📊 GÉNÉRATION RAPPORT GOOGLE SHEETS")
    print("="*70)
    
    try:
        from modules.reports.service_reports import run_reports
        result = run_reports(append=False)
        print(f"✅ Rapport généré: {result}")
        return result
    except Exception as e:
        print(f"❌ Erreur lors de la génération du rapport: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    parser = argparse.ArgumentParser(description="Backfill 2024 avec monitoring et rapport automatique")
    parser.add_argument('--monitor-interval', type=int, default=500, help='Monitoring toutes les N insertions')
    parser.add_argument('--skip-report', action='store_true', help='Ne pas générer le rapport à la fin')
    args = parser.parse_args()
    
    print("\n" + "="*70)
    print("🚀 BACKFILL 2024 - AVEC MONITORING ET RAPPORT AUTO")
    print("="*70)
    print(f"📅 Année: 2024")
    print(f"📊 Monitoring: toutes les {args.monitor_interval} insertions")
    print(f"🔄 Retry: Automatique avec pause 5s")
    print(f"📝 Rapport Google Sheets: {'Activé' if not args.skip_report else 'Désactivé'}")
    print("="*70)
    
    api_client = GazelleAPIClient()
    storage = SupabaseStorage(silent=True)
    
    start_time = time.time()
    result = backfill_2024(api_client, storage, monitor_interval=args.monitor_interval)
    elapsed = time.time() - start_time
    
    print("\n" + "="*70)
    print("✅ BACKFILL 2024 TERMINÉ")
    print("="*70)
    print(f"📊 Total synchronisées: {result['synced']:,}")
    print(f"📊 Total erreurs: {result['errors']}")
    print(f"⏱️  Durée: {elapsed/60:.1f} minutes")
    if result.get('initial_count') and result.get('final_count'):
        print(f"📈 Avant: {result['initial_count']:,} | Après: {result['final_count']:,} | Ajouté: {result['final_count'] - result['initial_count']:,}")
    print("="*70)
    
    # Générer le rapport Google Sheets si demandé
    if not args.skip_report:
        generate_sheets_report()
    else:
        print("\n⏭️  Rapport Google Sheets ignoré (--skip-report)")


if __name__ == '__main__':
    main()
