#!/usr/bin/env python3
"""
Test de synchronisation des users depuis Gazelle vers Supabase.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

from modules.sync_gazelle.sync_to_supabase import GazelleToSupabaseSync

if __name__ == "__main__":
    print("🧪 Test de synchronisation des techniciens (users)...")
    print("=" * 60)

    sync = GazelleToSupabaseSync()

    # Synchroniser seulement les users
    count = sync.sync_users()

    print("=" * 60)
    print(f"✅ Test terminé: {count} techniciens synchronisés")

    # Vérifier dans Supabase via REST API
    print("\n📊 Vérification dans Supabase...")
    from core.supabase_storage import SupabaseStorage
    import requests

    storage = SupabaseStorage()
    url = f"{storage.api_url}/users?select=*"
    headers = storage._get_headers()

    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        users = response.json()
        print(f"   Total users dans Supabase: {len(users)}")

        if users:
            print("\n👥 Techniciens synchronisés:")
            for user in users[:10]:
                name = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()
                print(f"   - {user.get('id')}: {name} ({user.get('email', 'N/A')})")
    else:
        print(f"   ❌ Erreur HTTP {response.status_code}")
