#!/usr/bin/env python3
"""
Exécute la migration SQL pour recréer la table users avec Gazelle IDs.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

import os
import requests

url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

if not url or not key:
    print("❌ SUPABASE_URL ou SUPABASE_SERVICE_ROLE_KEY manquant dans .env")
    sys.exit(1)

print(f"🔗 Migration table users vers Gazelle IDs...")
print("=" * 60)

# SQL pour la migration complète
migration_sql = """
-- 1. Supprimer la FK constraint si elle existe
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'fk_timeline_user'
        AND table_name = 'gazelle_timeline_entries'
    ) THEN
        ALTER TABLE gazelle_timeline_entries DROP CONSTRAINT fk_timeline_user;
        RAISE NOTICE 'Contrainte FK supprimée';
    END IF;
END $$;

-- 2. Supprimer l'ancienne table users
DROP TABLE IF EXISTS users CASCADE;

-- 3. Créer la nouvelle table users avec Gazelle IDs
CREATE TABLE users (
    id TEXT PRIMARY KEY,
    external_id TEXT,
    first_name TEXT,
    last_name TEXT,
    email TEXT,
    phone TEXT,
    role TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 4. Index
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_external_id ON users(external_id);

-- 5. RLS
ALTER TABLE users ENABLE ROW LEVEL SECURITY;

-- 6. Politique pour service_role
CREATE POLICY "Enable all access for service role"
ON users
FOR ALL
USING (true)
WITH CHECK (true);

-- 7. Recréer la FK constraint sur gazelle_timeline_entries
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_name = 'gazelle_timeline_entries'
    ) THEN
        ALTER TABLE gazelle_timeline_entries
        ADD CONSTRAINT fk_timeline_user
        FOREIGN KEY (user_id) REFERENCES users(id)
        ON DELETE SET NULL;
        RAISE NOTICE 'Contrainte FK recréée';
    END IF;
END $$;
"""

# Exécuter via PostgREST
headers = {
    'apikey': key,
    'Authorization': f'Bearer {key}',
    'Content-Type': 'application/json',
    'Prefer': 'return=minimal'
}

# Note: L'API PostgREST standard ne permet pas d'exécuter du SQL arbitraire
# Il faut passer par le SQL Editor de Supabase ou créer une fonction RPC

print("\n⚠️  ATTENTION:")
print("L'API Supabase Python ne permet pas d'exécuter du DDL (CREATE/DROP TABLE).")
print("\nVeuillez copier et exécuter le SQL suivant dans Supabase SQL Editor:")
print("=" * 60)
print(migration_sql)
print("=" * 60)
print("\nURL Supabase SQL Editor:")
print(f"{url.replace('supabase.co', 'supabase.co').replace('https://', 'https://app.')}/project/sql/new")

print("\n✅ Instructions affichées")
print("\nPROCHAINES ÉTAPES:")
print("1. Copier le SQL ci-dessus")
print("2. Ouvrir Supabase SQL Editor (URL ci-dessus)")
print("3. Coller et exécuter le SQL")
print("4. Lancer: python3 test_sync_users.py")
