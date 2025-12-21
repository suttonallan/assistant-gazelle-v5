#!/usr/bin/env python3
"""
Crée la table gazelle_admin_feedback pour stocker les notes internes des admins.
"""

import os
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

import requests

def create_admin_feedback_table():
    """Crée la table gazelle_admin_feedback dans Supabase."""

    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY', os.getenv('SUPABASE_KEY'))

    if not supabase_url or not supabase_key:
        print("❌ SUPABASE_URL et SUPABASE_KEY requis")
        return False

    # SQL pour créer la table
    sql = """
    -- Table pour les notes internes des admins sur les clients
    CREATE TABLE IF NOT EXISTS gazelle_admin_feedback (
        id BIGSERIAL PRIMARY KEY,
        client_id TEXT NOT NULL,
        user_email TEXT NOT NULL,
        note TEXT NOT NULL,
        created_at TIMESTAMPTZ DEFAULT NOW(),
        updated_at TIMESTAMPTZ DEFAULT NOW()
    );

    -- Index pour recherche rapide par client
    CREATE INDEX IF NOT EXISTS idx_admin_feedback_client_id
        ON gazelle_admin_feedback(client_id);

    -- Index pour recherche par date
    CREATE INDEX IF NOT EXISTS idx_admin_feedback_created_at
        ON gazelle_admin_feedback(created_at DESC);

    -- RLS (Row Level Security) - désactivé pour service_role
    ALTER TABLE gazelle_admin_feedback ENABLE ROW LEVEL SECURITY;

    -- Policy pour permettre toutes les opérations avec service_role
    DROP POLICY IF EXISTS "Allow all for service_role" ON gazelle_admin_feedback;
    CREATE POLICY "Allow all for service_role" ON gazelle_admin_feedback
        FOR ALL USING (true);
    """

    print("📋 Création de la table gazelle_admin_feedback...")

    # Exécuter via l'API PostgREST avec raw SQL
    # Note: PostgREST ne supporte pas directement les requêtes DDL
    # Il faut utiliser une fonction PL/pgSQL ou exécuter via psql

    print("\n⚠️  IMPORTANT: Cette table doit être créée manuellement dans Supabase")
    print("\nConnectez-vous à Supabase Dashboard > SQL Editor et exécutez:\n")
    print(sql)
    print("\n" + "="*60)

    # Alternative: tester si on peut insérer (la table existe déjà)
    test_url = f"{supabase_url}/rest/v1/gazelle_admin_feedback?limit=1"
    headers = {
        'apikey': supabase_key,
        'Authorization': f'Bearer {supabase_key}'
    }

    resp = requests.get(test_url, headers=headers)

    if resp.status_code == 200:
        print("✅ Table gazelle_admin_feedback existe déjà")
        return True
    elif resp.status_code == 404:
        print("❌ Table gazelle_admin_feedback n'existe pas encore")
        print("\nExécutez le SQL ci-dessus dans Supabase Dashboard")
        return False
    else:
        print(f"⚠️  Status: {resp.status_code}")
        print(f"Response: {resp.text}")
        return False


if __name__ == "__main__":
    create_admin_feedback_table()
