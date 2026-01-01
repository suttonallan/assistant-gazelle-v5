#!/usr/bin/env python3
"""
Script pour ajouter la colonne is_hidden à vincent_dindy_piano_updates
Exécuter: python3 add_is_hidden_column.py
"""

import os
from supabase import create_client

# Charger variables d'environnement
from dotenv import load_dotenv
load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_SERVICE_ROLE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
    print("❌ Erreur: SUPABASE_URL ou SUPABASE_SERVICE_ROLE_KEY manquant dans .env")
    exit(1)

# Créer client Supabase
supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

# SQL Migration
migration_sql = """
-- Ajouter colonne is_hidden
ALTER TABLE public.vincent_dindy_piano_updates
ADD COLUMN IF NOT EXISTS is_hidden boolean DEFAULT false;

-- Commentaire explicatif
COMMENT ON COLUMN public.vincent_dindy_piano_updates.is_hidden IS
  'Si true, le piano est masqué de l''inventaire (n''apparaît plus dans Tournées ni Technicien, seulement dans Inventaire avec filtre)';

-- Index pour recherche rapide des pianos masqués
CREATE INDEX IF NOT EXISTS idx_vincent_dindy_piano_updates_is_hidden
  ON public.vincent_dindy_piano_updates(is_hidden)
  WHERE is_hidden = true;
"""

print("🔧 Exécution de la migration...")
print("=" * 60)

try:
    # Exécuter via RPC SQL
    result = supabase.rpc('exec_sql', {'query': migration_sql}).execute()

    print("✅ Migration réussie!")
    print("   Colonne 'is_hidden' ajoutée à vincent_dindy_piano_updates")
    print("   Index créé pour recherche rapide")

except Exception as e:
    print(f"❌ Erreur lors de la migration: {e}")
    print("\n💡 Solution alternative:")
    print("   Copiez ce SQL et exécutez-le manuellement dans Supabase SQL Editor:")
    print("=" * 60)
    print(migration_sql)
    print("=" * 60)
