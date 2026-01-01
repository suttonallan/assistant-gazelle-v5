import os
import json
import requests
from datetime import datetime
from supabase import create_client

GAZELLE_API_URL = "https://gazelleapp.io/graphql/private/"
GAZELLE_ACCESS_TOKEN = os.getenv("GAZELLE_ACCESS_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY")

START_DATE = os.getenv("TIMELINE_START_DATE", "2025-07-01T00:00:00Z")
PAGE_SIZE = int(os.getenv("TIMELINE_PAGE_SIZE", "100"))
MAX_PAGES = int(os.getenv("TIMELINE_MAX_PAGES", "2"))  # safety for dry-run

QUERY = """
query($first: Int, $after: String, $occurredAtGet: CoreDateTime) {
    allTimelineEntries(first: $first, after: $after, occurredAtGet: $occurredAtGet) {
        totalCount
        nodes {
            id
            occurredAt
            type
            summary
            comment
            client { id }
            piano { id }
            invoice { id }
            estimate { id }
            user { id }
        }
        pageInfo {
            hasNextPage
            endCursor
        }
    }
}
"""


def fetch_timeline_entries():
    """Fetch timeline entries with pagination (limited by MAX_PAGES)."""
    all_entries = []
    cursor = None
    page = 0

    while True:
        page += 1
        print(f"[fetch] Page {page} cursor={cursor}")

        payload = {
            "query": QUERY,
            "variables": {
                "first": PAGE_SIZE,
                "after": cursor,
                "occurredAtGet": START_DATE,
            },
        }
        headers = {"Authorization": f"Bearer {GAZELLE_ACCESS_TOKEN}"}

        resp = requests.post(GAZELLE_API_URL, json=payload, headers=headers, timeout=60)
        try:
            resp.raise_for_status()
        except Exception as e:
            print(f"❌ HTTP error page {page}: {e} -> {resp.text[:500]}")
            break

        data = resp.json()
        if "errors" in data:
            print(f"❌ GraphQL errors page {page}: {data['errors']}")
            break

        connection = data.get("data", {}).get("allTimelineEntries", {})
        nodes = connection.get("nodes", [])
        all_entries.extend(nodes)
        print(f"   → fetched {len(nodes)} entries (cum: {len(all_entries)})")

        if page >= MAX_PAGES:
            print(f"[fetch] stopping at MAX_PAGES={MAX_PAGES} (dry-run safety)")
            break

        page_info = connection.get("pageInfo", {})
        if not page_info.get("hasNextPage"):
            break
        cursor = page_info.get("endCursor")

    return all_entries


def transform_entry(entry: dict) -> dict:
    return {
        "id": entry.get("id"),
        "occurred_at": entry.get("occurredAt"),
        "entry_type": entry.get("type"),
        "title": entry.get("summary"),
        "description": entry.get("comment"),
        "client_id": (entry.get("client") or {}).get("id"),
        "piano_id": (entry.get("piano") or {}).get("id"),
        "invoice_id": (entry.get("invoice") or {}).get("id"),
        "estimate_id": (entry.get("estimate") or {}).get("id"),
        "user_id": (entry.get("user") or {}).get("id"),
    }


def upsert_supabase(entries):
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    batch_size = 100
    for i in range(0, len(entries), batch_size):
        batch = entries[i : i + batch_size]
        print(f"[upsert] batch {i//batch_size+1} ({len(batch)} entries)")
        res = supabase.table("gazelle_timeline_entries").upsert(batch, on_conflict="id").execute()
        if res.get("status_code") and res["status_code"] not in (200, 201):
            print(f"   ⚠️ Upsert error status={res['status_code']} details={res}")
        else:
            print("   ✅ upsert ok")


def main():
    if not GAZELLE_ACCESS_TOKEN:
        print("❌ GAZELLE_ACCESS_TOKEN missing")
        return
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("❌ SUPABASE_URL/KEY missing")
        return

    print("=" * 60)
    print("IMPORT TIMELINE ENTRIES (dry-run limited)")
    print(f"start_date={START_DATE}, page_size={PAGE_SIZE}, max_pages={MAX_PAGES}")
    print("=" * 60)

    entries = fetch_timeline_entries()
    print(f"[fetch] total fetched: {len(entries)}")

    # Transform
    transformed = [transform_entry(e) for e in entries]
    print(f"[transform] sample: {json.dumps(transformed[:2], indent=2)}")

    # Upsert
    if transformed:
        upsert_supabase(transformed)
    print("✅ DONE")


if __name__ == "__main__":
    main()
