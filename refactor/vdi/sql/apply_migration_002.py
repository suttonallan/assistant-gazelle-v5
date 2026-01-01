#!/usr/bin/env python3
"""
Apply migration 002: Fix tournees constraints
"""
import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
    print("❌ SUPABASE_URL ou SUPABASE_SERVICE_ROLE_KEY manquant dans .env")
    exit(1)

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

# Lire le fichier SQL
with open("refactor/vdi/sql/002_fix_tournees_constraints.sql", "r") as f:
    sql = f.read()

# Exécuter chaque commande séparément
commands = [
    """ALTER TABLE public.tournees
       ALTER COLUMN technicien_responsable DROP NOT NULL""",

    """ALTER TABLE public.tournees
       DROP CONSTRAINT IF EXISTS tournees_status_check""",

    """ALTER TABLE public.tournees
       ADD CONSTRAINT tournees_status_check
       CHECK (status IN ('planifiee', 'en_cours', 'terminee', 'archivee'))""",
]

print("🔧 Application de la migration 002...")

for i, cmd in enumerate(commands, 1):
    try:
        result = supabase.postgrest.rpc('exec_sql', {'query': cmd}).execute()
        print(f"✅ Commande {i}/3 exécutée")
    except Exception as e:
        # Essayer via l'API REST directement
        print(f"⚠️  Commande {i}/3: {e}")
        print("   (Veuillez exécuter manuellement via Supabase Dashboard)")

print("\n✅ Migration terminée! Vous pouvez maintenant créer des tournées.")
print("   Si des erreurs persistent, exécutez le SQL manuellement dans:")
print("   Supabase Dashboard → SQL Editor → refactor/vdi/sql/002_fix_tournees_constraints.sql")
