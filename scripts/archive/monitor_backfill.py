#!/usr/bin/env python3
"""Monitorer le backfill en temps réel."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from core.supabase_storage import SupabaseStorage
import requests
import time

storage = SupabaseStorage()

print("🔄 MONITORING BACKFILL EN TEMPS RÉEL")
print("=" * 70)
print("Appuyez sur Ctrl+C pour arrêter\n")

last_count = 0

try:
    while True:
        # Compter TOUTES les entrées timeline
        url = f"{storage.api_url}/gazelle_timeline_entries?select=id&limit=1"
        headers = storage._get_headers()
        headers['Prefer'] = 'count=exact'

        resp = requests.get(url, headers=headers)

        if resp.status_code == 200:
            count_header = resp.headers.get('content-range', '')
            if count_header:
                total = int(count_header.split('/')[-1])

                # Afficher seulement si changement
                if total != last_count:
                    delta = total - last_count
                    print(f"✅ {time.strftime('%H:%M:%S')} | Total: {total:,} (+{delta})")
                    last_count = total

        time.sleep(5)  # Vérifier toutes les 5 secondes

except KeyboardInterrupt:
    print(f"\n\n✅ Monitoring arrêté. Dernier comptage: {last_count:,} entrées")
