#!/usr/bin/env python3
"""
Script pour exécuter la migration sync_logs via l'API Supabase.
Utilise des requêtes ALTER TABLE individuelles via l'API REST.
"""

import sys
from pathlib import Path
from dotenv import load_dotenv
import os

sys.path.insert(0, str(Path(__file__).parent.parent))
load_dotenv()

from core.supabase_storage import SupabaseStorage
import requests
import json

def execute_migration():
    """Exécute la migration sync_logs via l'API Supabase."""
    print("="*70)
    print("🔧 MIGRATION sync_logs - Ajout des colonnes manquantes")
    print("="*70)
    
    storage = SupabaseStorage(silent=True)
    
    # Les requêtes ALTER TABLE doivent être exécutées via SQL direct
    # L'API REST Supabase ne supporte pas ALTER TABLE
    # On doit utiliser l'éditeur SQL ou psycopg2
    
    print("\n⚠️  L'API REST Supabase ne permet pas d'exécuter ALTER TABLE directement.")
    print("   Il faut utiliser l'éditeur SQL de Supabase ou psycopg2.")
    print("\n📋 Instructions pour exécuter la migration:")
    print("   1. Ouvrez l'éditeur SQL de Supabase:")
    print(f"      https://supabase.com/dashboard/project/{storage.supabase_url.split('//')[1].split('.')[0]}/sql/new")
    print("   2. Copiez le contenu du fichier: sql/fix_sync_logs_schema.sql")
    print("   3. Collez dans l'éditeur et cliquez sur 'Run'")
    print("\n   OU")
    print("   4. Installez psycopg2: pip install psycopg2-binary")
    print("   5. Ajoutez SUPABASE_DB_PASSWORD dans votre .env")
    print("   6. Relancez: python3 scripts/execute_sql_migration.py")
    
    # Afficher le contenu du fichier SQL
    sql_file = Path(__file__).parent.parent / 'sql' / 'fix_sync_logs_schema.sql'
    if sql_file.exists():
        print(f"\n📄 Contenu du fichier SQL ({sql_file}):")
        print("="*70)
        with open(sql_file, 'r') as f:
            print(f.read())
        print("="*70)
    
    return False

if __name__ == '__main__':
    success = execute_migration()
    sys.exit(0 if success else 1)
