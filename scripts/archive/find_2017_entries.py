#!/usr/bin/env python3
"""Find first 2017 entries in Gazelle API."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from core.gazelle_api_client import GazelleAPIClient

api_client = GazelleAPIClient()

query = """
query($first: Int, $after: String, $occurredAtGet: CoreDateTime) {
    allTimelineEntries(first: $first, after: $after, occurredAtGet: $occurredAtGet) {
        nodes {
            id
            occurredAt
            type
            summary
            comment
        }
        pageInfo {
            hasNextPage
            endCursor
        }
    }
}
"""

print("=" * 70)
print("🔍 RECHERCHE D'ENTRÉES 2017 DANS GAZELLE")
print("=" * 70)

cursor = None
page = 0
found_2017 = []

while page < 100 and len(found_2017) < 5:  # Limit to 100 pages
    page += 1

    variables = {
        "first": 100,
        "after": cursor,
        "occurredAtGet": "2017-01-01T05:00:00Z"
    }

    result = api_client._execute_query(query, variables)
    connection = result.get('data', {}).get('allTimelineEntries', {})
    nodes = connection.get('nodes', [])
    page_info = connection.get('pageInfo', {})

    if not nodes:
        break

    # Check years in this page
    years_in_page = set()
    for entry in nodes:
        occurred_at = entry.get('occurredAt', '')
        if occurred_at:
            year = int(occurred_at[:4])
            years_in_page.add(year)

            if year == 2017:
                found_2017.append(entry)

    print(f"Page {page:3d}: Years {sorted(years_in_page)}, Found 2017: {len(found_2017)}", flush=True)

    if found_2017:
        print("\n✅ ENTRÉES 2017 TROUVÉES:\n")
        for i, entry in enumerate(found_2017[:5], 1):
            date = entry.get('occurredAt', '')[:10]
            entry_type = entry.get('type', 'N/A')
            summary = entry.get('summary', 'N/A')[:60]
            comment = entry.get('comment', '')[:80]
            print(f"{i}. {date} | {entry_type:20s}")
            print(f"   Title: {summary}")
            if comment:
                print(f"   Description: {comment}")
            print()
        break

    if not page_info.get('hasNextPage'):
        break

    cursor = page_info.get('endCursor')

if not found_2017:
    print(f"\n⚠️  Aucune entrée 2017 trouvée après {page} pages")
    print("(Il faudrait parcourir plus de pages)")

print("=" * 70)
