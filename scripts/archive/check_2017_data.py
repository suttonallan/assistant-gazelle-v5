#!/usr/bin/env python3
"""Vérifier les données 2017 dans Supabase en temps réel."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from core.supabase_storage import SupabaseStorage
import requests

storage = SupabaseStorage()

print("=" * 70)
print("🔍 VÉRIFICATION DONNÉES 2017 DANS SUPABASE")
print("=" * 70)

# Compter les entrées 2017
try:
    url = f"{storage.api_url}/gazelle_timeline_entries"
    url += "?select=id,occurred_at,entry_type,title"
    url += "&occurred_at=gte.2017-01-01T00:00:00Z"
    url += "&occurred_at=lte.2017-12-31T23:59:59Z"
    url += "&order=occurred_at.asc"
    url += "&limit=10"

    headers = storage._get_headers()
    headers['Prefer'] = 'count=exact'

    resp = requests.get(url, headers=headers)

    if resp.status_code == 200:
        data = resp.json()
        count_header = resp.headers.get('content-range', '')

        if count_header:
            total = count_header.split('/')[-1]
            print(f"\n✅ TOTAL ENTRÉES 2017: {total}\n")
        else:
            print(f"\n✅ Au moins {len(data)} entrées trouvées\n")

        if data:
            print("📋 Échantillon (10 premières):")
            for item in data[:10]:
                date = (item.get('occurred_at') or '')[:10]
                entry_type = item.get('entry_type', 'N/A')
                title = (item.get('title') or '')[:50]
                print(f"   {date} | {entry_type:20s} | {title}")
        else:
            print("⚠️  Aucune donnée 2017 encore (backfill en cours...)")

    else:
        print(f"❌ Erreur API: {resp.status_code}")

except Exception as e:
    print(f"❌ Erreur: {e}")

print("\n" + "=" * 70)
