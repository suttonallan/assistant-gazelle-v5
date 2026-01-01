#!/usr/bin/env python3
"""
Fix: Mettre à jour les user_id NULL dans gazelle_timeline_entries.

Tous les user_id sont NULL à cause du workaround temporaire.
Maintenant que les users existent, il faut récupérer les user_id depuis Gazelle API
et mettre à jour les entries existantes.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

from core.gazelle_api_client import GazelleAPIClient
from core.supabase_storage import SupabaseStorage
import requests

if __name__ == "__main__":
    print("🔧 Fix: Mise à jour des user_id dans gazelle_timeline_entries")
    print("=" * 70)

    # Init clients
    api_client = GazelleAPIClient()
    storage = SupabaseStorage()

    # Récupérer toutes les timeline entries depuis Gazelle avec user_id
    print("\n📥 Récupération des timeline entries depuis Gazelle...")

    # Utiliser GraphQL pour récupérer avec user_id
    query = """
    query GetTimelineWithUsers($cursor: String) {
        allTimelineEntries(first: 100, after: $cursor) {
            edges {
                node {
                    id
                    user {
                        id
                    }
                }
            }
            pageInfo {
                hasNextPage
                endCursor
            }
        }
    }
    """

    user_ids_map = {}  # external_id -> user_id
    cursor = None
    page_count = 0

    while True:
        variables = {}
        if cursor:
            variables["cursor"] = cursor

        result = api_client._execute_query(query, variables)
        batch_data = result.get('data', {}).get('allTimelineEntries', {})
        edges = batch_data.get('edges', [])
        page_info = batch_data.get('pageInfo', {})

        for edge in edges:
            node = edge.get('node', {})
            external_id = node.get('id')
            user = node.get('user')

            if external_id and user:
                user_id = user.get('id')
                if user_id:
                    user_ids_map[external_id] = user_id

        page_count += 1
        print(f"📄 Page {page_count}: {len(user_ids_map)} entries avec user_id")

        if not page_info.get('hasNextPage'):
            print("✅ Toutes les pages récupérées")
            break

        cursor = page_info.get('endCursor')

    print(f"\n✅ {len(user_ids_map)} timeline entries avec user_id trouvées")

    if not user_ids_map:
        print("❌ Aucune entrée trouvée, abandon")
        sys.exit(1)

    # Mettre à jour dans Supabase
    print(f"\n📤 Mise à jour dans Supabase...")

    headers = storage._get_headers()
    updated_count = 0
    skipped_count = 0

    for external_id, user_id in user_ids_map.items():
        # Update via PATCH
        url = f"{storage.api_url}/gazelle_timeline_entries"
        params = {'external_id': f'eq.{external_id}'}
        data = {'user_id': user_id}

        try:
            response = requests.patch(url, headers=headers, params=params, json=data)

            if response.status_code in [200, 204]:
                updated_count += 1
                if updated_count % 100 == 0:
                    print(f"   {updated_count} entrées mises à jour...")
            else:
                skipped_count += 1
                if skipped_count <= 5:
                    print(f"⚠️  Skip {external_id}: HTTP {response.status_code}")
        except Exception as e:
            skipped_count += 1
            if skipped_count <= 5:
                print(f"❌ Erreur {external_id}: {e}")

    print("\n" + "=" * 70)
    print(f"✅ Mise à jour terminée:")
    print(f"   - Mises à jour réussies: {updated_count}")
    print(f"   - Ignorées/Erreurs: {skipped_count}")
    print("=" * 70)

    # Vérifier
    print("\n📊 Vérification...")
    url = f"{storage.api_url}/gazelle_timeline_entries"
    params = {
        'select': 'user_id',
        'entry_type': 'eq.SERVICE_ENTRY_MANUAL',
        'limit': 100
    }

    response = requests.get(url, headers=headers, params=params)

    if response.status_code == 200:
        entries = response.json()
        total = len(entries)
        with_user = sum(1 for e in entries if e.get('user_id'))

        print(f"   SERVICE_ENTRY_MANUAL (100 premiers):")
        print(f"   - Total: {total}")
        print(f"   - Avec user_id: {with_user}")
        print(f"   - Sans user_id: {total - with_user}")
