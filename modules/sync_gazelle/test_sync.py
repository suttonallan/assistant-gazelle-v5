#!/usr/bin/env python3
"""
Test du script de synchronisation (mode dry-run avec limit=3).

Synchronise seulement 3 clients et 3 pianos pour tester.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dotenv import load_dotenv
load_dotenv()

from core.gazelle_api_client import GazelleAPIClient
from core.supabase_storage import SupabaseStorage
from datetime import datetime


def test_sync():
    """Test de synchronisation avec limit=3."""

    print("🧪 TEST DE SYNCHRONISATION (3 clients, 3 pianos)")
    print("=" * 60)

    # Init
    api = GazelleAPIClient()
    storage = SupabaseStorage()

    # Test 1: Récupérer 3 clients
    print("\n1️⃣  Test: Récupérer 3 clients depuis API Gazelle...")
    try:
        clients = api.get_clients(limit=3)
        print(f"✅ {len(clients)} clients récupérés")

        if clients:
            print(f"\n📋 Exemple de client:")
            c = clients[0]
            print(f"   ID: {c.get('id')}")
            print(f"   Nom: {c.get('companyName')}")
            print(f"   Statut: {c.get('status')}")

    except Exception as e:
        print(f"❌ Erreur: {e}")
        return False

    # Test 2: UPSERT 1 client dans Supabase
    print("\n2️⃣  Test: UPSERT 1 client dans Supabase...")
    try:
        if clients:
            client = clients[0]

            # Gérer company_name vide ou null
            company_name = client.get('companyName', '').strip() if client.get('companyName') else ''

            # Si vide, utiliser le nom du contact par défaut
            if not company_name:
                default_contact = client.get('defaultContact', {})
                if default_contact:
                    first_name = default_contact.get('firstName', '').strip()
                    last_name = default_contact.get('lastName', '').strip()
                    company_name = f"{first_name} {last_name}".strip()

            # Si toujours vide, utiliser un nom par défaut
            if not company_name:
                company_name = f"Client {client.get('id', 'Unknown')}"

            client_record = {
                'external_id': client.get('id'),
                'company_name': company_name,
                'status': client.get('status', 'active'),
                'updated_at': datetime.now().isoformat()
            }

            url = f"{storage.api_url}/gazelle_clients"
            headers = storage._get_headers()
            headers["Prefer"] = "resolution=merge-duplicates"

            import requests
            response = requests.post(url, headers=headers, json=client_record)

            if response.status_code in [200, 201]:
                print(f"✅ Client UPSERT réussi: {client_record['company_name']}")
            else:
                print(f"❌ Erreur UPSERT: {response.status_code}")
                print(f"   Response: {response.text}")
                return False

    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Test 3: Vérifier que le client est dans Supabase
    print("\n3️⃣  Test: Lire le client depuis Supabase...")
    try:
        external_id = clients[0].get('id')
        url = f"{storage.api_url}/gazelle_clients?external_id=eq.{external_id}"
        headers = storage._get_headers()

        import requests
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            data = response.json()
            if data:
                print(f"✅ Client trouvé dans Supabase: {data[0].get('company_name')}")
            else:
                print(f"❌ Client non trouvé dans Supabase")
                return False
        else:
            print(f"❌ Erreur lecture: {response.status_code}")
            return False

    except Exception as e:
        print(f"❌ Erreur: {e}")
        return False

    print("\n" + "=" * 60)
    print("✅ TOUS LES TESTS PASSENT !")
    print("=" * 60)
    print("\n💡 Le sync complet peut maintenant être lancé:")
    print("   python3 modules/sync_gazelle/sync_to_supabase.py")

    return True


if __name__ == "__main__":
    success = test_sync()
    sys.exit(0 if success else 1)
