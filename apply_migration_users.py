#!/usr/bin/env python3
"""
Applique la migration SQL pour recréer la table users avec Gazelle IDs.
Utilise l'API Supabase directement.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

import os
from supabase import create_client

url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

if not url or not key:
    print("❌ SUPABASE_URL ou SUPABASE_SERVICE_ROLE_KEY manquant dans .env")
    sys.exit(1)

print(f"🔗 Connexion à Supabase: {url}")
supabase = create_client(url, key)

print("\n⚠️  MIGRATION DE LA TABLE USERS")
print("=" * 60)
print("Cette migration va:")
print("1. Supprimer la FK constraint fk_timeline_user")
print("2. Supprimer l'ancienne table users")
print("3. Créer la nouvelle table users avec Gazelle IDs (TEXT)")
print("4. Recréer la FK constraint")
print("=" * 60)

confirm = input("\nContinuer? (oui/non): ")
if confirm.lower() != 'oui':
    print("❌ Migration annulée")
    sys.exit(0)

print("\n🔄 Exécution de la migration...")

# Étape 1: Supprimer FK constraint
print("\n1️⃣ Suppression FK constraint fk_timeline_user...")
try:
    result = supabase.rpc('exec_sql', {
        'sql': """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.table_constraints
                WHERE constraint_name = 'fk_timeline_user'
                AND table_name = 'gazelle_timeline_entries'
            ) THEN
                ALTER TABLE gazelle_timeline_entries DROP CONSTRAINT fk_timeline_user;
            END IF;
        END $$;
        """
    }).execute()
    print("   ✅ FK constraint supprimée")
except Exception as e:
    # RPC exec_sql n'existe probablement pas, on va utiliser une approche différente
    print(f"   ⚠️  RPC non disponible: {e}")
    print("   On va essayer une approche alternative...")

# Approche alternative: Utiliser psycopg2 si disponible
try:
    import psycopg2
    from urllib.parse import urlparse

    # Parser l'URL Supabase pour obtenir les credentials PostgreSQL
    # Format: https://PROJECT_REF.supabase.co
    project_ref = url.replace('https://', '').replace('.supabase.co', '')

    # Connection string pour Supabase
    # Note: Ceci nécessite le mot de passe de la base de données
    print("\n⚠️  Pour exécuter le DDL, nous avons besoin d'une connexion PostgreSQL directe.")
    print("   Les credentials Supabase REST API ne suffisent pas.")
    print("\n   Veuillez exécuter manuellement le SQL suivant dans Supabase SQL Editor:")

except ImportError:
    print("\n⚠️  psycopg2 n'est pas installé.")
    print("   Veuillez exécuter manuellement le SQL suivant dans Supabase SQL Editor:")

# Afficher le SQL complet
migration_sql = """
-- Migration: Recréer table users avec Gazelle IDs
-- Date: 2025-12-28

-- 1. Supprimer FK constraint
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'fk_timeline_user'
        AND table_name = 'gazelle_timeline_entries'
    ) THEN
        ALTER TABLE gazelle_timeline_entries DROP CONSTRAINT fk_timeline_user;
        RAISE NOTICE 'FK constraint supprimée';
    END IF;
END $$;

-- 2. Supprimer ancienne table
DROP TABLE IF EXISTS users CASCADE;

-- 3. Créer nouvelle table users
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

CREATE POLICY "Enable all access for service role"
ON users FOR ALL
USING (true)
WITH CHECK (true);

-- 6. Recréer FK constraint
ALTER TABLE gazelle_timeline_entries
ADD CONSTRAINT fk_timeline_user
FOREIGN KEY (user_id) REFERENCES users(id)
ON DELETE SET NULL;
"""

print("\n" + "=" * 60)
print(migration_sql)
print("=" * 60)

print("\n📋 INSTRUCTIONS:")
print(f"1. Ouvrir: https://supabase.com/dashboard/project/{url.split('//')[1].split('.')[0]}/sql/new")
print("2. Copier/coller le SQL ci-dessus")
print("3. Cliquer 'Run'")
print("4. Revenir ici et lancer: python3 test_sync_users.py")
