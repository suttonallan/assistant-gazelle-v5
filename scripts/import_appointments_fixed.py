#!/usr/bin/env python3
"""
Import complet des rendez-vous Gazelle → Supabase
STOCKAGE EN UTC (conversion Montréal dans les vues SQL)

Ce script:
1. Récupère tous les RVs depuis l'API Gazelle (60 jours passés → 90 jours futurs)
2. Stocke les heures en UTC (tel que fourni par l'API)
3. Insère dans Supabase (la conversion Montréal se fait dans les vues SQL)
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.gazelle_api_client import GazelleAPIClient
from core.supabase_storage import SupabaseStorage
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from supabase import create_client

def main():
    print('\n' + '='*80)
    print('🔄 IMPORT RENDEZ-VOUS GAZELLE → SUPABASE (stockage UTC)')
    print('='*80)

    # Initialisation
    api_client = GazelleAPIClient()
    storage = SupabaseStorage()
    supabase = create_client(storage.supabase_url, storage.supabase_key)

    # Étape 1: Récupérer tous les RVs depuis Gazelle
    print('\n📅 Récupération des rendez-vous depuis Gazelle...')
    api_appointments = api_client.get_appointments(limit=None)

    print(f'✅ {len(api_appointments)} rendez-vous récupérés depuis l\'API Gazelle')

    # Étape 2: Préparer les données (stockage UTC sans conversion)
    print('\n🔧 Préparation des données (stockage UTC)...')
    batch = []
    errors = 0

    for appt_data in api_appointments:
        external_id = appt_data.get('id')
        title = appt_data.get('title', '')
        start_time = appt_data.get('start')  # Format: "2026-01-09T12:00:00Z" (UTC)

        if not start_time:
            continue

        try:
            # STOCKAGE UTC PUR - AUCUNE CONVERSION:
            # On stocke exactement ce que l'API Gazelle fournit (UTC)
            # La conversion UTC → Montréal se fait dans les vues SQL
            #
            # Exemple: API dit 12:00 UTC
            #   → On stocke: 12:00 UTC (tel quel)
            #   → Vue SQL convertit: 12:00 UTC → 07:00 Montréal ✅

            dt_utc = datetime.fromisoformat(start_time.replace('Z', '+00:00'))

            # AUCUNE COMPENSATION - Stockage UTC pur
            appointment_date = dt_utc.date().isoformat()
            appointment_time = dt_utc.time().isoformat()

            # Préparer l'enregistrement
            user_obj = appt_data.get('user', {})
            technicien = user_obj.get('id') if user_obj else None

            appointment_record = {
                'external_id': external_id,
                'client_external_id': appt_data.get('client', {}).get('id') if appt_data.get('client') else None,
                'title': title,
                'description': appt_data.get('notes', ''),
                'appointment_date': appointment_date,
                'appointment_time': appointment_time,
                'duration_minutes': appt_data.get('duration'),
                'status': appt_data.get('status', 'scheduled'),
                'technicien': technicien,
                'location': '',
                'notes': appt_data.get('notes', ''),
                'created_at': start_time,
                'updated_at': datetime.now().isoformat()
            }

            batch.append(appointment_record)

        except Exception as e:
            errors += 1
            if errors <= 5:
                print(f'   ⚠️ Erreur parsing {external_id}: {e}')

    print(f'✅ {len(batch)} rendez-vous préparés ({errors} erreurs)')

    # Étape 3: Afficher quelques exemples AVANT insertion
    print('\n📋 Exemples de données à insérer (5 premiers):')
    print('-'*80)

    for i, appt in enumerate(batch[:5]):
        print(f"{i+1}. {appt['external_id']}")
        print(f"   Titre: {appt['title'][:40]}")
        print(f"   Date: {appt['appointment_date']}")
        print(f"   Heure UTC: {appt['appointment_time']}")
        print()

    # Étape 4: Upsert dans Supabase par lots
    print(f'\n💾 Insertion dans Supabase (par lots de 100)...')

    batch_size = 100
    synced = 0
    upsert_errors = 0

    for i in range(0, len(batch), batch_size):
        chunk = batch[i:i+batch_size]

        try:
            result = supabase.table('gazelle_appointments').upsert(
                chunk,
                on_conflict='external_id'
            ).execute()

            synced += len(chunk)
            print(f'   ✅ Lot {i//batch_size + 1}: {len(chunk)} RVs insérés (total: {synced})')

        except Exception as e:
            upsert_errors += len(chunk)
            print(f'   ❌ Erreur lot {i//batch_size + 1}: {str(e)[:100]}')

    # Résumé final
    print('\n' + '='*80)
    print('📊 RÉSUMÉ DE L\'IMPORT')
    print('='*80)
    print(f'✅ Rendez-vous synchronisés: {synced}')
    print(f'❌ Erreurs d\'insertion: {upsert_errors}')
    print(f'📅 Période couverte: 60 jours passés → 90 jours futurs')
    print(f'🕐 Stockage: UTC (conversion Montréal dans les vues SQL)')
    print('='*80)

    # Vérification post-import
    print('\n🔍 Vérification post-import...')

    try:
        result = supabase.table('gazelle_appointments').select(
            'external_id,title,appointment_date,appointment_time'
        ).limit(5).execute()

        print(f'\n📋 Exemples de RVs importés (5 premiers):')
        print('-'*80)

        for appt in result.data:
            print(f"ID: {appt.get('external_id')}")
            print(f"  {appt.get('appointment_date')} {appt.get('appointment_time')}")
            print(f"  {appt.get('title', 'Sans titre')[:50]}")
            print()

        print(f'\n✅ Import terminé avec succès!')

    except Exception as e:
        print(f'⚠️ Erreur vérification: {e}')

if __name__ == '__main__':
    main()
