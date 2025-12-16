#!/usr/bin/env python3
"""
Script pour exécuter des migrations SQL sur Supabase.
Usage: python scripts/run_migration.py <migration_file.sql>
"""

import os
import sys
import requests
from pathlib import Path

def run_migration(sql_file_path: str):
    """
    Exécute une migration SQL sur Supabase via l'API.

    Args:
        sql_file_path: Chemin vers le fichier .sql
    """
    # Charger les variables d'environnement
    from dotenv import load_dotenv
    load_dotenv()

    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_KEY')

    if not supabase_url or not supabase_key:
        print("❌ Variables SUPABASE_URL et SUPABASE_KEY requises dans .env")
        sys.exit(1)

    # Lire le fichier SQL
    sql_path = Path(sql_file_path)
    if not sql_path.exists():
        print(f"❌ Fichier introuvable: {sql_file_path}")
        sys.exit(1)

    with open(sql_path, 'r', encoding='utf-8') as f:
        sql_content = f.read()

    print(f"📄 Migration: {sql_path.name}")
    print(f"📝 Contenu SQL ({len(sql_content)} caractères):")
    print("-" * 60)
    print(sql_content[:500] + "..." if len(sql_content) > 500 else sql_content)
    print("-" * 60)

    # Préparer les headers pour API Supabase
    api_url = f"{supabase_url}/rest/v1"
    headers = {
        "apikey": supabase_key,
        "Authorization": f"Bearer {supabase_key}",
        "Content-Type": "application/json"
    }
    print("✅ Configuration Supabase prête")

    # IMPORTANT: L'API Supabase REST ne supporte pas l'exécution directe de DDL (ALTER TABLE, CREATE INDEX)
    # Ces migrations doivent être exécutées via le SQL Editor de Supabase Dashboard
    print("\n⚠️  ATTENTION:")
    print("L'API Supabase REST ne permet pas d'exécuter des commandes DDL (ALTER TABLE, CREATE INDEX).")
    print("\n📌 Pour appliquer cette migration:")
    print(f"1. Ouvrir Supabase Dashboard: {supabase_url.replace('supabase.co', 'supabase.com')}")
    print("2. Aller dans SQL Editor")
    print("3. Copier-coller le contenu SQL ci-dessus")
    print("4. Exécuter la requête\n")

    # Alternative: Afficher un exemple de requête pour vérifier si les colonnes existent
    print("🔍 Vérification rapide (via API):")
    try:
        url = f"{api_url}/produits_catalogue?limit=1"
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            data = response.json()
            if data:
                colonnes = list(data[0].keys())
                print(f"✅ Colonnes actuelles dans produits_catalogue: {', '.join(colonnes)}")

                # Vérifier colonnes manquantes
                colonnes_v4 = ['has_commission', 'commission_rate', 'variant_group', 'variant_label', 'display_order', 'is_active']
                manquantes = [col for col in colonnes_v4 if col not in colonnes]
                if manquantes:
                    print(f"⚠️  Colonnes manquantes: {', '.join(manquantes)}")
                else:
                    print("✅ Toutes les colonnes V4 sont présentes!")
            else:
                print("⚠️  Table vide, impossible de vérifier les colonnes")
        else:
            print(f"❌ Erreur API {response.status_code}: {response.text}")
    except Exception as e:
        print(f"⚠️  Erreur lors de la vérification: {e}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python scripts/run_migration.py <migration_file.sql>")
        print("Exemple: python scripts/run_migration.py scripts/migrations/002_add_v4_columns_to_produits.sql")
        sys.exit(1)

    run_migration(sys.argv[1])
