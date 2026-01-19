#!/usr/bin/env python3
"""Tester différentes variantes de requête timeline."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.gazelle_api_client import GazelleAPIClient

api_client = GazelleAPIClient()

print("=" * 70)
print("🔍 TEST REQUÊTES TIMELINE GAZELLE")
print("=" * 70)

# Test 1: Sans filtre de date (toutes les entrées)
print("\n1️⃣  Test SANS filtre de date (first: 5):")
query1 = """
query GetAllTimeline($cursor: String) {
    allTimelineEntries(
        first: 5,
        after: $cursor
    ) {
        edges {
            node {
                id
                occurredAt
                type
                summary
            }
        }
        pageInfo {
            hasNextPage
            endCursor
        }
        totalCount
    }
}
"""

try:
    result = api_client._execute_query(query1, {"cursor": None})
    timeline = result.get('data', {}).get('allTimelineEntries', {})
    total = timeline.get('totalCount', 'N/A')
    edges = timeline.get('edges', [])

    print(f"✅ Total timeline entries: {total}")
    print(f"✅ Premières 5 entrées:")
    for edge in edges:
        node = edge.get('node', {})
        print(f"   - {node.get('occurredAt')[:10]} | {node.get('type')} | {node.get('summary', '')[:50]}")

except Exception as e:
    print(f"❌ Erreur: {e}")

# Test 2: Avec filtre occurredAtGet (2017-01-01)
print("\n2️⃣  Test AVEC occurredAtGet=2017-01-01 (first: 5):")
query2 = """
query GetTimelineWithFilter($occurredAtGet: CoreDateTime) {
    allTimelineEntries(
        first: 5,
        occurredAtGet: $occurredAtGet
    ) {
        edges {
            node {
                id
                occurredAt
                type
                summary
            }
        }
        totalCount
    }
}
"""

try:
    result = api_client._execute_query(query2, {"occurredAtGet": "2017-01-01T00:00:00Z"})
    timeline = result.get('data', {}).get('allTimelineEntries', {})
    total = timeline.get('totalCount', 'N/A')
    edges = timeline.get('edges', [])

    print(f"✅ Total avec filtre 2017: {total}")
    if edges:
        print(f"✅ Premières entrées 2017:")
        for edge in edges:
            node = edge.get('node', {})
            print(f"   - {node.get('occurredAt')[:10]} | {node.get('type')} | {node.get('summary', '')[:50]}")
    else:
        print("⚠️  Aucune entrée trouvée pour 2017")

except Exception as e:
    print(f"❌ Erreur: {e}")

print("\n" + "=" * 70)
