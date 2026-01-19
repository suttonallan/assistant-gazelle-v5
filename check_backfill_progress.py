#!/usr/bin/env python3
"""Vérifier la progression du backfill."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from core.supabase_storage import SupabaseStorage
import requests

print("=" * 70)
print("📊 PROGRESSION DU BACKFILL")
print("=" * 70)

storage = SupabaseStorage()

# Total entries
url = f'{storage.api_url}/gazelle_timeline_entries?select=id&limit=1'
headers = storage._get_headers()
headers['Prefer'] = 'count=exact'
resp = requests.get(url, headers=headers)
count_header = resp.headers.get('content-range', '')
if count_header:
    total = int(count_header.split('/')[-1])
    print(f"\n📈 Total entrées dans Supabase: {total:,}\n")

# Breakdown by year
print("Répartition par année:")
print("-" * 70)

for year in range(2016, 2027):
    url = f'{storage.api_url}/gazelle_timeline_entries'
    url += f'?select=id'
    url += f'&occurred_at=gte.{year}-01-01T00:00:00Z'
    url += f'&occurred_at=lte.{year}-12-31T23:59:59Z'
    url += f'&limit=1'

    headers = storage._get_headers()
    headers['Prefer'] = 'count=exact'

    resp = requests.get(url, headers=headers)
    count_header = resp.headers.get('content-range', '')

    if count_header:
        count = int(count_header.split('/')[-1])
        bar = "█" * min(50, count // 100)
        status = "✅" if count > 0 else "⏳"
        print(f"{status} {year}: {count:>6,} entrées {bar}")

print("-" * 70)

# Show last 10 lines of log
print("\n📄 Dernières lignes du log:\n")
try:
    with open('/tmp/backfill_full.log', 'r') as f:
        lines = f.readlines()
        for line in lines[-10:]:
            print(f"   {line.rstrip()}")
except FileNotFoundError:
    print("   ⚠️  Log file not found")

print("\n" + "=" * 70)
print("💡 Commande pour voir le log complet: tail -f /tmp/backfill_full.log")
print("=" * 70 + "\n")
