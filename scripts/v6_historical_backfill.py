#!/usr/bin/env python3
"""
v6 HISTORICAL BACKFILL - Récupération rapide des données historiques

Stratégie:
- Commence au 28 octobre 2025 et remonte dans le temps
- Utilise des batchs pour la vitesse (100 entrées par requête)
- Pas de vérification de doublons (on sait qu'il n'y a rien avant le 29 octobre)
- Objectif: Octobre, Septembre, Août 2025 en moins de 2 minutes
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import time
from datetime import datetime, timezone, timedelta
from core.gazelle_api_client import GazelleAPIClient
from core.supabase_storage import SupabaseStorage
from supabase import create_client
import requests


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
        print(f"⚠️  Erreur comptage: {e}")
        return None


def backfill_month_range(start_date: datetime, end_date: datetime, api_client, storage):
    """
    Backfill rapide pour une plage de dates (remonte dans le temps).
    
    Args:
        start_date: Date de début (la plus récente, ex: 28 oct 2025)
        end_date: Date de fin (la plus ancienne, ex: 1 août 2025)
    """
    print(f"\n{'='*70}")
    print(f"📅 BACKFILL HISTORIQUE v6 - REMONTÉE DANS LE TEMPS")
    print(f"{'='*70}")
    print(f"📍 De: {start_date.strftime('%Y-%m-%d')} (récent)")
    print(f"📍 À: {end_date.strftime('%Y-%m-%d')} (ancien)")
    print(f"⚡ Mode: Batch rapide (pas de vérification doublons)")
    print(f"{'='*70}\n")
    
    initial_count = count_timeline_entries(storage)
    print(f"📊 Entrées initiales: {initial_count:,}\n")
    
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
    
    # Traiter par mois en remontant (octobre -> septembre -> août)
    current_date = start_date
    total_synced = 0
    total_errors = 0
    
    while current_date >= end_date:
        month_start = current_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        # Fin du mois
        if current_date.month == 12:
            month_end = current_date.replace(year=current_date.year + 1, month=1, day=1) - timedelta(seconds=1)
        else:
            month_end = current_date.replace(month=current_date.month + 1, day=1) - timedelta(seconds=1)
        
        # S'assurer qu'on ne dépasse pas end_date
        if month_start < end_date:
            month_start = end_date
        
        month_name = current_date.strftime('%B %Y')
        print(f"📅 Traitement: {month_name} ({month_start.strftime('%Y-%m-%d')} à {month_end.strftime('%Y-%m-%d')})")
        
        month_synced = 0
        month_errors = 0
        cursor = None
        page = 0
        batch = []
        batch_size = 100  # Batch de 100 entrées
        
        while True:
            page += 1
            try:
                variables = {
                    "first": 100,
                    "after": cursor,
                    "occurredAtGet": month_start.strftime("%Y-%m-%dT%H:%M:%SZ")
                }
                
                result = api_client._execute_query(query, variables)
                connection = result.get('data', {}).get('allTimelineEntries', {})
                nodes = connection.get('nodes', [])
                page_info = connection.get('pageInfo', {})
                
                if not nodes:
                    break
                
                # Filtrer les entrées dans la plage du mois
                for entry in nodes:
                    occurred_at_raw = entry.get('occurredAt')
                    if not occurred_at_raw:
                        continue
                    
                    try:
                        dt = datetime.fromisoformat(occurred_at_raw.replace('Z', '+00:00'))
                        if dt.tzinfo is None:
                            dt = dt.replace(tzinfo=timezone.utc)
                        
                        # Vérifier que c'est dans la plage du mois
                        if dt < month_start or dt > month_end:
                            continue
                        
                        # Préparer l'enregistrement
                        record = {
                            'external_id': entry.get('id'),
                            'entry_type': entry.get('type'),
                            'description': entry.get('comment'),
                            'title': entry.get('summary'),
                            'occurred_at': dt.isoformat(),
                            'entity_id': entry.get('client', {}).get('id') if entry.get('client') else None,
                            'piano_id': entry.get('piano', {}).get('id') if entry.get('piano') else None,
                            'user_id': entry.get('user', {}).get('id') if entry.get('user') else None,
                            'invoice_id': entry.get('invoice', {}).get('id') if entry.get('invoice') else None,
                            'estimate_id': entry.get('estimate', {}).get('id') if entry.get('estimate') else None
                        }
                        
                        batch.append(record)
                        
                        # Insérer par batch de 100
                        if len(batch) >= batch_size:
                            success = _insert_batch(storage, batch)
                            if success:
                                month_synced += len(batch)
                                total_synced += len(batch)
                            else:
                                month_errors += len(batch)
                                total_errors += len(batch)
                            batch = []
                    
                    except Exception as e:
                        month_errors += 1
                        total_errors += 1
                        if total_errors <= 3:
                            print(f"  ⚠️  Erreur parsing: {e}")
                
                # Insérer le reste du batch
                if batch:
                    success = _insert_batch(storage, batch)
                    if success:
                        month_synced += len(batch)
                        total_synced += len(batch)
                    else:
                        month_errors += len(batch)
                        total_errors += len(batch)
                    batch = []
                
                has_next = page_info.get('hasNextPage', False)
                if not has_next:
                    break
                
                cursor = page_info.get('endCursor')
            
            except Exception as e:
                print(f"  ❌ Erreur page {page}: {e}")
                break
        
        print(f"  ✅ {month_name}: {month_synced:,} entrées synchronisées")
        if month_errors > 0:
            print(f"  ⚠️  {month_errors} erreurs")
        
        # Passer au mois précédent
        if current_date.month == 1:
            current_date = current_date.replace(year=current_date.year - 1, month=12)
        else:
            current_date = current_date.replace(month=current_date.month - 1)
    
    final_count = count_timeline_entries(storage)
    print(f"\n{'='*70}")
    print(f"✅ BACKFILL TERMINÉ")
    print(f"{'='*70}")
    print(f"📊 Total synchronisées: {total_synced:,}")
    print(f"📊 Total erreurs: {total_errors}")
    print(f"📈 Avant: {initial_count:,} | Après: {final_count:,} | Ajouté: {final_count - initial_count:,}")
    print(f"{'='*70}\n")
    
    return {'synced': total_synced, 'errors': total_errors}


def _insert_batch(storage, batch):
    """Insère un batch d'entrées en une seule requête (rapide)."""
    if not batch:
        return True
    
    try:
        url = f"{storage.api_url}/gazelle_timeline_entries"
        headers = storage._get_headers()
        # Pas de Prefer pour éviter les vérifications de doublons (on sait qu'il n'y en a pas)
        
        resp = requests.post(url, headers=headers, json=batch, timeout=30)
        
        if resp.status_code in [200, 201]:
            return True
        else:
            # En cas d'erreur, essayer une par une (fallback)
            print(f"  ⚠️  Erreur batch ({resp.status_code}), fallback individuel...")
            success_count = 0
            for record in batch:
                try:
                    resp_single = requests.post(url, headers=headers, json=record, timeout=10)
                    if resp_single.status_code in [200, 201, 409]:
                        success_count += 1
                except:
                    pass
            return success_count == len(batch)
    
    except Exception as e:
        print(f"  ❌ Erreur batch: {e}")
        return False


def main():
    print("\n" + "="*70)
    print("🚀 v6 HISTORICAL BACKFILL - REMONTÉE DANS LE TEMPS")
    print("="*70)
    print("📅 Cible: Octobre, Septembre, Août 2025")
    print("⚡ Mode: Batch rapide (100 entrées/requête)")
    print("🎯 Objectif: < 2 minutes")
    print("="*70)
    
    api_client = GazelleAPIClient()
    storage = SupabaseStorage(silent=True)
    
    # Dates: 28 octobre 2025 -> 1er août 2025
    start_date = datetime(2025, 10, 28, tzinfo=timezone.utc)
    end_date = datetime(2025, 8, 1, tzinfo=timezone.utc)
    
    start_time = time.time()
    result = backfill_month_range(start_date, end_date, api_client, storage)
    elapsed = time.time() - start_time
    
    print(f"⏱️  Durée totale: {elapsed:.1f} secondes ({elapsed/60:.2f} minutes)")
    
    if elapsed < 120:
        print("🎯 Objectif atteint: < 2 minutes!")
    else:
        print(f"⚠️  Objectif non atteint: {elapsed/60:.2f} minutes (objectif: < 2 min)")


if __name__ == '__main__':
    main()
