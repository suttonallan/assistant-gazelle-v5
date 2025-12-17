#!/usr/bin/env python3
"""
Test rapide pour vérifier que la correction timezone fonctionne.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.supabase_storage import SupabaseStorage
import requests
from datetime import datetime
from zoneinfo import ZoneInfo

storage = SupabaseStorage()
url = f'{storage.api_url}/gazelle_appointments'
headers = storage._get_headers()

# Récupérer quelques RV récents
params = {
    'select': 'external_id,title,appointment_date,appointment_time,technicien',
    'limit': 10,
    'order': 'appointment_date.desc'
}

response = requests.get(url, headers=headers, params=params)

if response.status_code == 200:
    appts = response.json()

    print('🔍 Vérification des heures après re-synchronisation:')
    print('=' * 70)

    for appt in appts[:5]:
        title = appt.get('title', 'N/A')
        date = appt.get('appointment_date', 'N/A')
        time_utc = appt.get('appointment_time', 'N/A')

        # Conversion UTC → Eastern (comme dans queries.py)
        if time_utc and ':' in time_utc:
            parts = time_utc.split(':')
            hour_utc = int(parts[0])
            minute_utc = int(parts[1][:2])

            date_parts = date.split('-')
            if len(date_parts) == 3:
                year, month, day = int(date_parts[0]), int(date_parts[1]), int(date_parts[2])

                dt_utc = datetime(year, month, day, hour_utc, minute_utc, tzinfo=ZoneInfo('UTC'))
                dt_eastern = dt_utc.astimezone(ZoneInfo('America/Toronto'))
                time_eastern = dt_eastern.strftime('%H:%M')

                print(f'\n{title}')
                print(f'  Date: {date}')
                print(f'  Stocké (UTC): {time_utc}')
                print(f'  Affiché (Eastern): {time_eastern}')

    print('\n' + '=' * 70)
    print('✅ Si les heures affichées sont cohérentes, la correction fonctionne!')
else:
    print(f'❌ Erreur: {response.status_code}')
