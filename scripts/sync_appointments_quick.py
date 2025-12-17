#!/usr/bin/env python3
"""
Synchronisation rapide de quelques rendez-vous pour tester la correction timezone.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.gazelle_api_client import GazelleAPIClient
from core.supabase_storage import SupabaseStorage
from datetime import datetime
from zoneinfo import ZoneInfo
import requests

api_client = GazelleAPIClient()
storage = SupabaseStorage()

print("📅 Récupération de 10 RV depuis l'API...")
api_appointments = api_client.get_appointments(limit=10)

print(f"\n🔄 Synchronisation de {len(api_appointments)} RV avec correction timezone...\n")

synced = 0
for appt_data in api_appointments:
    external_id = appt_data.get('id')
    title = appt_data.get('title', '')
    start_time = appt_data.get('start')

    if start_time:
        try:
            # NOUVELLE LOGIQUE: Interpréter comme Eastern
            dt_obj = datetime.fromisoformat(start_time.replace('Z', ''))
            eastern_tz = ZoneInfo('America/Toronto')
            dt_eastern = dt_obj.replace(tzinfo=eastern_tz)
            dt_utc = dt_eastern.astimezone(ZoneInfo('UTC'))

            appointment_date = dt_utc.date().isoformat()
            appointment_time = dt_utc.time().isoformat()

            print(f"{title[:30]:30s} | API: {start_time[:19]} → Stocké: {appointment_time[:5]} UTC → Affiche: {dt_obj.strftime('%H:%M')} Eastern")

            # UPSERT
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

            url = f"{storage.api_url}/gazelle_appointments"
            headers = storage._get_headers()
            headers["Prefer"] = "resolution=merge-duplicates"

            response = requests.post(url, headers=headers, json=appointment_record)

            if response.status_code in [200, 201]:
                synced += 1
            else:
                print(f"   ❌ Erreur {response.status_code}")

        except Exception as e:
            print(f"   ⚠️ Erreur: {e}")

print(f"\n✅ {synced}/{len(api_appointments)} rendez-vous synchronisés")
print("\nMaintenant testez avec: python3 scripts/test_timezone_fix.py")
