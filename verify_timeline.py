#!/usr/bin/env python3
"""
Vérifier que les timeline entries ont été synchronisées.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

import os
from supabase import create_client

url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

if not url or not key:
    print("❌ SUPABASE_URL ou SUPABASE_SERVICE_ROLE_KEY manquant dans .env")
    sys.exit(1)

print(f"🔗 Connexion à Supabase: {url}")
supabase = create_client(url, key)

# Count timeline entries from Dec 22-28, 2025
result = supabase.table('gazelle_timeline_entries') \
    .select('*', count='exact') \
    .gte('occurred_at', '2025-12-22T00:00:00') \
    .lte('occurred_at', '2025-12-28T23:59:59') \
    .execute()

print(f'\n📊 Timeline entries Dec 22-28, 2025: {result.count}')

# Check SERVICE_ENTRY_MANUAL entries
services = supabase.table('gazelle_timeline_entries') \
    .select('*', count='exact') \
    .eq('entry_type', 'SERVICE_ENTRY_MANUAL') \
    .gte('occurred_at', '2025-12-22T00:00:00') \
    .lte('occurred_at', '2025-12-28T23:59:59') \
    .execute()

print(f'📝 SERVICE_ENTRY_MANUAL entries Dec 22-28: {services.count}')

# Show recent service entries
recent = supabase.table('gazelle_timeline_entries') \
    .select('occurred_at,entry_type,title') \
    .eq('entry_type', 'SERVICE_ENTRY_MANUAL') \
    .order('occurred_at', desc=True) \
    .limit(10) \
    .execute()

print('\n📝 10 most recent service entries:')
for entry in recent.data:
    occurred = entry['occurred_at'][:10] if entry['occurred_at'] else 'N/A'
    title = (entry.get('title') or 'N/A')[:60]
    print(f'  {occurred}: {title}')
