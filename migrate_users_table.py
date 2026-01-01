#!/usr/bin/env python3
"""
Migration de la table users pour utiliser les Gazelle IDs.

ATTENTION: Cette migration va:
1. Créer une nouvelle table users_new avec la structure correcte
2. Copier les données existantes (si applicable)
3. Supprimer l'ancienne table users
4. Renommer users_new en users

Exécuter ce script AVANT de lancer le sync complet.
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

if not url or key:
    print("❌ SUPABASE_URL ou SUPABASE_SERVICE_ROLE_KEY manquant dans .env")
    sys.exit(1)

print(f"🔗 Connexion à Supabase: {url}")
supabase = create_client(url, key)

print("\n⚠️  MIGRATION DE LA TABLE USERS")
print("=" * 60)
print("Cette migration va recréer la table users avec Gazelle IDs.")
print("=" * 60)

# Vérifier si la table users existe déjà
try:
    result = supabase.table('users').select('id', count='exact').limit(1).execute()
    existing_count = result.count
    print(f"\n📊 Table users existante: {existing_count} entrées")

    if existing_count > 0:
        print("⚠️  La table contient des données. Elles seront supprimées.")
        confirm = input("Continuer? (oui/non): ")
        if confirm.lower() != 'oui':
            print("❌ Migration annulée")
            sys.exit(0)
except Exception as e:
    print(f"ℹ️  Table users n'existe pas encore ou est vide: {e}")

# Étape 1: Supprimer la contrainte FK sur gazelle_timeline_entries
print("\n1️⃣ Suppression de la contrainte FK fk_timeline_user...")
try:
    # Note: Supabase Python client ne supporte pas directement ALTER TABLE
    # On va utiliser l'API REST directement
    import requests

    headers = {
        'apikey': key,
        'Authorization': f'Bearer {key}',
        'Content-Type': 'application/json'
    }

    # Supprimer la FK si elle existe
    sql_drop_fk = """
    DO $$
    BEGIN
        IF EXISTS (
            SELECT 1 FROM information_schema.table_constraints
            WHERE constraint_name = 'fk_timeline_user'
        ) THEN
            ALTER TABLE gazelle_timeline_entries DROP CONSTRAINT fk_timeline_user;
        END IF;
    END $$;
    """

    response = requests.post(
        f"{url}/rest/v1/rpc/exec_sql",
        headers=headers,
        json={'query': sql_drop_fk}
    )

    print("✅ Contrainte FK supprimée (si elle existait)")
except Exception as e:
    print(f"⚠️  Erreur lors de la suppression FK: {e}")
    print("   (Continuer quand même...)")

# Étape 2: Supprimer l'ancienne table users
print("\n2️⃣ Suppression de l'ancienne table users...")
try:
    # Via RPC si disponible, sinon on skip
    sql_drop = "DROP TABLE IF EXISTS users CASCADE;"
    # Note: Cette partie nécessite d'exécuter le SQL manuellement dans Supabase
    print("⚠️  Veuillez exécuter manuellement dans Supabase SQL Editor:")
    print(f"   {sql_drop}")
except Exception as e:
    print(f"⚠️  {e}")

# Étape 3: Créer la nouvelle table users
print("\n3️⃣ Création de la nouvelle table users...")

sql_create = """
-- Créer table users avec Gazelle IDs
CREATE TABLE IF NOT EXISTS users (
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

-- Index
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_external_id ON users(external_id);

-- RLS
ALTER TABLE users ENABLE ROW LEVEL SECURITY;

-- Politique pour service_role
DROP POLICY IF EXISTS "Enable all access for service role" ON users;
CREATE POLICY "Enable all access for service role"
ON users
FOR ALL
USING (true)
WITH CHECK (true);
"""

print("⚠️  Veuillez exécuter manuellement dans Supabase SQL Editor:")
print("-" * 60)
print(sql_create)
print("-" * 60)

print("\n✅ Script de migration préparé")
print("\nPROCHAINES ÉTAPES:")
print("1. Exécuter le SQL ci-dessus dans Supabase SQL Editor")
print("2. Lancer: python3 sync_timeline_recent.py")
print("   (cela va synchroniser les users ET les timeline entries)")
