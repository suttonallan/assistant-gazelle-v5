#!/usr/bin/env python3
"""
Applique la migration pour ajouter la colonne is_in_csv.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.supabase_storage import SupabaseStorage
import requests

def apply_migration():
    """Applique la migration SQL."""

    storage = SupabaseStorage()

    # Lire le fichier SQL
    sql_file = os.path.join(os.path.dirname(__file__), 'add_is_in_csv_column.sql')

    with open(sql_file, 'r') as f:
        sql = f.read()

    print("🔧 Application de la migration SQL...")
    print(f"   Fichier: {sql_file}")
    print()

    # Exécuter via l'API Supabase PostgREST (méthode RPC)
    # Note: Pour ALTER TABLE, nous devons utiliser l'API Database directement
    # ou exécuter via SQL Editor dans le dashboard Supabase

    print("📝 Migration SQL à appliquer:")
    print("=" * 80)
    print(sql)
    print("=" * 80)
    print()

    print("⚠️  IMPORTANT:")
    print("Cette migration nécessite un accès direct à la base de données.")
    print()
    print("Options pour appliquer la migration:")
    print()
    print("1. Dashboard Supabase (RECOMMANDÉ):")
    print("   - Ouvrir https://supabase.com/dashboard/project/beblgzvmjqkcillmcavk/sql/new")
    print(f"   - Copier le contenu de: {sql_file}")
    print("   - Cliquer 'RUN'")
    print()
    print("2. Via psql (si accès direct):")
    print(f"   psql <connection_string> -f {sql_file}")
    print()

    # Tentative via API REST (ne fonctionne pas pour ALTER TABLE)
    print("🧪 Tentative via API REST...")

    try:
        # Cette approche ne fonctionnera probablement pas car PostgREST
        # ne supporte pas ALTER TABLE directement

        url = f"{storage.api_url}/rpc/exec_sql"
        headers = storage._get_headers()
        data = {"query": sql}

        response = requests.post(url, json=data, headers=headers)

        if response.status_code == 200:
            print("✅ Migration appliquée avec succès!")
            return True
        else:
            print(f"❌ Échec via API REST: HTTP {response.status_code}")
            print(f"   Réponse: {response.text}")
            print()
            print("💡 Utiliser le Dashboard Supabase à la place")
            return False

    except Exception as e:
        print(f"❌ Erreur: {e}")
        print()
        print("💡 Utiliser le Dashboard Supabase à la place")
        return False


if __name__ == "__main__":
    success = apply_migration()

    if not success:
        print()
        print("=" * 80)
        print("📋 INSTRUCTIONS MANUELLES:")
        print("=" * 80)
        print()
        print("1. Ouvrir le Dashboard Supabase:")
        print("   https://supabase.com/dashboard/project/beblgzvmjqkcillmcavk/sql/new")
        print()
        print("2. Copier ce SQL:")
        print()
        print("```sql")

        sql_file = os.path.join(os.path.dirname(__file__), 'add_is_in_csv_column.sql')
        with open(sql_file, 'r') as f:
            print(f.read())

        print("```")
        print()
        print("3. Coller dans l'éditeur SQL et cliquer 'RUN'")
        print()
        print("4. Ré-exécuter: python3 scripts/reconcile_csv_with_gazelle.py --apply")
        sys.exit(1)
    else:
        sys.exit(0)
