#!/usr/bin/env python3
"""Test backfill with debugging output."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import requests
from datetime import datetime, timezone
from core.gazelle_api_client import GazelleAPIClient
from core.supabase_storage import SupabaseStorage

print("=" * 70)
print("🔍 TEST BACKFILL 2017 (DEBUG)")
print("=" * 70)

api_client = GazelleAPIClient()
storage = SupabaseStorage()

query = """
query($first: Int, $occurredAtGet: CoreDateTime) {
    allTimelineEntries(first: $first, occurredAtGet: $occurredAtGet) {
        totalCount
        nodes {
            id
            occurredAt
            type
            summary
            comment
            client { id }
            piano { id }
        }
        pageInfo {
            hasNextPage
            endCursor
        }
    }
}
"""

variables = {
    "first": 10,  # Just 10 entries for testing
    "occurredAtGet": "2017-01-01T05:00:00Z"
}

print("\n📡 Envoi de la requête Gazelle...")
result = api_client._execute_query(query, variables)
print(f"✅ Réponse reçue")

connection = result.get('data', {}).get('allTimelineEntries', {})
nodes = connection.get('nodes', [])
total_count = connection.get('totalCount', 'N/A')

print(f"\n📊 Total disponible depuis 2017: {total_count}")
print(f"📋 Entrées récupérées: {len(nodes)}\n")

if nodes:
    print("📝 Premières entrées:")
    for i, entry in enumerate(nodes[:5], 1):
        entry_id = entry.get('id')
        entry_type = entry.get('type')
        occurred_at = entry.get('occurredAt', '')[:10]
        summary = entry.get('summary', 'N/A')[:50]
        print(f"   {i}. {occurred_at} | {entry_type:20s} | {summary}")

    # Test d'insertion de la première entrée
    print(f"\n🧪 Test d'insertion de la première entrée dans Supabase...")
    entry = nodes[0]

    occurred_at_raw = entry.get('occurredAt')
    occurred_at_aware = None
    if occurred_at_raw:
        try:
            dt = datetime.fromisoformat(occurred_at_raw.replace('Z', '+00:00'))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            occurred_at_aware = dt.isoformat()
        except Exception as e:
            print(f"   ⚠️  Erreur timezone: {e}")
            occurred_at_aware = occurred_at_raw

    record = {
        'external_id': entry.get('id'),
        'entry_type': entry.get('type'),
        'description': entry.get('comment'),
        'title': entry.get('summary'),
        'occurred_at': occurred_at_aware,
        'entity_id': entry.get('client', {}).get('id') if entry.get('client') else None,
        'piano_id': entry.get('piano', {}).get('id') if entry.get('piano') else None,
    }

    print(f"   📦 Record: external_id={record['external_id']}, type={record['entry_type']}")

    # UPSERT
    url = f"{storage.api_url}/gazelle_timeline_entries?on_conflict=external_id"
    headers = storage._get_headers()
    headers['Prefer'] = 'resolution=merge-duplicates'

    resp = requests.post(url, headers=headers, json=record)

    if resp.status_code in [200, 201]:
        print(f"   ✅ Insertion réussie: {resp.status_code}")
    else:
        print(f"   ❌ Erreur insertion: {resp.status_code}")
        print(f"   Réponse: {resp.text[:200]}")

else:
    print("❌ Aucune entrée récupérée!")

print("\n" + "=" * 70)
