#!/usr/bin/env python3
"""
Crée la table service_inventory_consumption dans Supabase.
Cette table associe les services MSL Gazelle avec les matériaux consommés.
"""

import os
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

import requests

def create_service_consumption_table():
    """Crée la table service_inventory_consumption dans Supabase."""

    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY', os.getenv('SUPABASE_KEY'))

    if not supabase_url or not supabase_key:
        print("❌ SUPABASE_URL et SUPABASE_KEY requis")
        return False

    # Lire le fichier SQL
    sql_file = Path(__file__).parent / 'create_service_consumption_table.sql'

    if not sql_file.exists():
        print(f"❌ Fichier SQL introuvable: {sql_file}")
        return False

    with open(sql_file, 'r', encoding='utf-8') as f:
        sql = f.read()

    print("="*60)
    print("📋 Création de la table service_inventory_consumption")
    print("="*60)
    print("\n⚠️  IMPORTANT: Cette table doit être créée manuellement dans Supabase")
    print("\n1. Connectez-vous à Supabase Dashboard")
    print("   → https://supabase.com/dashboard")
    print("\n2. Allez dans SQL Editor")
    print("   → Cliquez sur 'New Query'")
    print("\n3. Copiez-collez le SQL ci-dessous:")
    print("\n" + "="*60 + "\n")
    print(sql)
    print("\n" + "="*60)

    # Tester si la table existe déjà
    test_url = f"{supabase_url}/rest/v1/service_inventory_consumption?limit=1"
    headers = {
        'apikey': supabase_key,
        'Authorization': f'Bearer {supabase_key}'
    }

    print("\n🔍 Vérification si la table existe...")
    resp = requests.get(test_url, headers=headers)

    if resp.status_code == 200:
        print("✅ Table service_inventory_consumption existe déjà!")

        # Afficher quelques statistiques
        count_url = f"{supabase_url}/rest/v1/service_inventory_consumption?select=count"
        count_resp = requests.get(count_url, headers={
            **headers,
            'Prefer': 'count=exact'
        })

        if count_resp.status_code == 200:
            count = count_resp.headers.get('Content-Range', '0-0/0').split('/')[-1]
            print(f"   → {count} règles de consommation enregistrées")

        return True

    elif resp.status_code == 404:
        print("❌ Table service_inventory_consumption n'existe pas encore")
        print("\n👉 Exécutez le SQL ci-dessus dans Supabase Dashboard")
        print("\n💡 Alternative: Utilisez psql si vous avez accès direct:")
        print(f"   psql '{supabase_url.replace('/rest/v1', '')}' -f {sql_file}")
        return False

    else:
        print(f"⚠️  Status: {resp.status_code}")
        print(f"Response: {resp.text}")
        return False


if __name__ == "__main__":
    success = create_service_consumption_table()
    sys.exit(0 if success else 1)
