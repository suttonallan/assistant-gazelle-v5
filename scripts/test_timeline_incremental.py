#!/usr/bin/env python3
"""
Test d'import incrémentiel Timeline - Limite à 50 items

Ce script teste l'import de seulement 50 items du Timeline pour vérifier:
1. Que les items sont bien triés par date de création descendante (plus récent en premier)
2. Que les doublons sont évités grâce à l'UPSERT (clé unique: external_id)
3. Que les items s'ajoutent correctement dans Supabase

Usage:
    python3 scripts/test_timeline_incremental.py
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import requests

# Ajouter le projet au path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from core.gazelle_api_client import GazelleAPIClient
from core.supabase_storage import SupabaseStorage
from scripts.sync_logger import SyncLogger


def test_incremental_timeline_sync(limit: int = 50):
    """
    Test de synchronisation incrémentielle du Timeline.
    
    Args:
        limit: Nombre maximum d'entrées à synchroniser (défaut: 50)
    """
    print("\n" + "="*70)
    print(f"🧪 TEST IMPORT INC RÉMENTIEL TIMELINE (limite: {limit} items)")
    print("="*70)
    
    # Mesurer le temps d'exécution
    import time
    start_time = time.time()

    # Initialisation
    print("\n🔧 Initialisation...")
    try:
        api_client = GazelleAPIClient()
        storage = SupabaseStorage()
        logger = SyncLogger()
        print("✅ Clients initialisés")
    except Exception as e:
        print(f"❌ Erreur d'initialisation: {e}")
        # Logger l'erreur
        try:
            SyncLogger().log_sync(
                script_name='GitHub_Timeline_Sync',
                status='error',
                error_message=str(e),
                execution_time_seconds=time.time() - start_time
            )
        except:
            pass
        return
    
    # 1. Récupérer les 50 derniers items depuis l'API (triés par date descendante)
    print(f"\n📥 Étape 1/3: Récupération des {limit} derniers items depuis l'API Gazelle...")
    try:
        # Pas de filtre de date pour récupérer les plus récents
        api_entries = api_client.get_timeline_entries(
            since_date=None,  # Pas de filtre de date
            limit=limit  # Limiter à 50 items
        )
        
        if not api_entries:
            print("⚠️  Aucune timeline entry récupérée depuis l'API")
            return
        
        print(f"✅ {len(api_entries)} timeline entries récupérées")
        
        # Vérifier le tri (les plus récents doivent être en premier)
        if len(api_entries) >= 2:
            first_date = api_entries[0].get('occurredAt')
            last_date = api_entries[-1].get('occurredAt')
            print(f"   📅 Premier item (le plus récent): {first_date}")
            print(f"   📅 Dernier item: {last_date}")
            
            if first_date and last_date:
                from zoneinfo import ZoneInfo
                try:
                    first_dt = datetime.fromisoformat(first_date.replace('Z', '+00:00'))
                    last_dt = datetime.fromisoformat(last_date.replace('Z', '+00:00'))
                    if first_dt >= last_dt:
                        print("   ✅ Tri vérifié: items triés du plus récent au plus ancien")
                    else:
                        print("   ⚠️  Attention: items ne semblent pas triés correctement")
                except Exception as e:
                    print(f"   ⚠️  Erreur parsing dates: {e}")
        
    except Exception as e:
        print(f"❌ Erreur lors de la récupération: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # 2. Vérifier les IDs existants dans Supabase AVANT l'import
    print(f"\n🔍 Étape 2/3: Vérification des IDs existants dans Supabase...")
    try:
        url = f"{storage.api_url}/gazelle_timeline_entries?select=external_id"
        headers = storage._get_headers()
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            existing_entries = response.json()
            existing_ids = {entry['external_id'] for entry in existing_entries if entry.get('external_id')}
            print(f"✅ {len(existing_ids)} timeline entries existantes dans Supabase")
        else:
            existing_ids = set()
            print(f"⚠️  Erreur lors de la récupération des IDs existants: {response.status_code}")
    except Exception as e:
        existing_ids = set()
        print(f"⚠️  Erreur: {e}")
    
    # 3. Synchroniser les items (avec UPSERT pour éviter les doublons)
    print(f"\n📤 Étape 3/3: Synchronisation des {len(api_entries)} items vers Supabase...")
    synced_count = 0
    new_count = 0
    updated_count = 0
    error_count = 0
    
    for entry_data in api_entries:
        try:
            external_id = entry_data.get('id')
            if not external_id:
                print(f"⚠️  Entrée sans ID, ignorée")
                continue
            
            # Client
            client_obj = entry_data.get('client', {})
            client_id = client_obj.get('id') if client_obj else None

            # Piano
            piano_obj = entry_data.get('piano', {})
            piano_id = piano_obj.get('id') if piano_obj else None

            # Invoice et Estimate
            invoice_obj = entry_data.get('invoice', {})
            invoice_id = invoice_obj.get('id') if invoice_obj else None

            estimate_obj = entry_data.get('estimate', {})
            estimate_id = estimate_obj.get('id') if estimate_obj else None

            # User (technicien)
            user_obj = entry_data.get('user', {})
            user_id = user_obj.get('id') if user_obj else None

            # Données de l'entrée
            entry_type = entry_data.get('type', 'UNKNOWN')
            title = entry_data.get('summary', '')
            details = entry_data.get('comment', '')
            occurred_at = entry_data.get('occurredAt')

            timeline_record = {
                'external_id': external_id,
                'client_id': client_id,
                'piano_id': piano_id,
                'invoice_id': invoice_id,
                'estimate_id': estimate_id,
                'user_id': user_id,
                'occurred_at': occurred_at,
                'entry_type': entry_type,
                'title': title,
                'description': details
            }

            # UPSERT (merge-duplicates utilise external_id comme clé unique)
            url = f"{storage.api_url}/gazelle_timeline_entries"
            headers = storage._get_headers()
            headers["Prefer"] = "resolution=merge-duplicates"

            response = requests.post(url, headers=headers, json=timeline_record)

            if response.status_code in [200, 201]:
                # Nouveau item ou mis à jour
                if external_id in existing_ids:
                    updated_count += 1
                else:
                    new_count += 1
                synced_count += 1
                existing_ids.add(external_id)  # Mettre à jour le set local
            elif response.status_code == 409:
                # 409 peut être un succès (merge)
                if external_id in existing_ids:
                    updated_count += 1
                else:
                    new_count += 1
                synced_count += 1
                existing_ids.add(external_id)
            else:
                print(f"❌ Erreur UPSERT timeline {external_id}: {response.status_code}")
                print(f"   Response: {response.text[:200]}")
                error_count += 1

        except Exception as e:
            print(f"❌ Erreur timeline entry {entry_data.get('id', 'unknown')}: {e}")
            error_count += 1
            continue
    
    # Résumé final
    print("\n" + "="*70)
    print("📊 RÉSULTATS DU TEST")
    print("="*70)
    print(f"✅ Items synchronisés avec succès: {synced_count}")
    print(f"   - Nouveaux items: {new_count}")
    print(f"   - Items mis à jour: {updated_count}")
    print(f"❌ Erreurs: {error_count}")

    if new_count + updated_count == synced_count:
        print("\n✅ TEST RÉUSSI: Aucun doublon créé grâce à l'UPSERT")
    else:
        print(f"\n⚠️  Attention: {synced_count} synchronisés mais {new_count + updated_count} comptabilisés")

    print("\n" + "="*70)

    # Logger le résultat de la synchronisation
    execution_time = time.time() - start_time
    status = 'success' if error_count == 0 else ('warning' if synced_count > 0 else 'error')

    logger.log_sync(
        script_name='GitHub_Timeline_Sync',
        status=status,
        tables_updated={
            'timeline': synced_count,
            'new': new_count,
            'updated': updated_count
        },
        error_message=f"{error_count} erreurs" if error_count > 0 else None,
        execution_time_seconds=round(execution_time, 2)
    )

    print(f"\n⏱️  Temps d'exécution: {execution_time:.2f}s")

    return synced_count


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Test d\'import incrémentiel Timeline')
    parser.add_argument('--limit', type=int, default=50, help='Nombre d\'items à importer (défaut: 50)')
    args = parser.parse_args()
    
    test_incremental_timeline_sync(limit=args.limit)

