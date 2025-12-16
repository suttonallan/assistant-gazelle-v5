#!/usr/bin/env python3
"""
Script pour vérifier l'existence des tables Gazelle dans Supabase.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Ajouter le répertoire parent au path
sys.path.insert(0, str(Path(__file__).parent.parent))

load_dotenv()

try:
    import psycopg2
    from urllib.parse import urlparse
except ImportError:
    print("❌ psycopg2 non installé. Installez avec: pip install psycopg2-binary")
    sys.exit(1)


def get_supabase_connection():
    """Crée une connexion psycopg2 à Supabase."""
    supabase_url = os.getenv('SUPABASE_URL')
    if not supabase_url:
        print("❌ SUPABASE_URL non défini dans .env")
        sys.exit(1)
    
    parsed = urlparse(supabase_url)
    host = parsed.hostname
    database = os.getenv('SUPABASE_DATABASE', 'postgres')
    user = os.getenv('SUPABASE_USER', 'postgres')
    password = os.getenv('SUPABASE_PASSWORD')
    
    if not password:
        print("❌ SUPABASE_PASSWORD non défini dans .env")
        sys.exit(1)
    
    # Essayer d'abord le pooler de connexion (port 6543) - plus fiable pour Supabase
    # Si ça échoue, essayer le port direct (5432)
    for port in ['6543', '5432']:
        try:
            print(f"🔄 Tentative de connexion sur le port {port}...")
            conn = psycopg2.connect(
                host=host,
                database=database,
                user=user,
                password=password,
                port=port,
                connect_timeout=10
            )
            print(f"✅ Connexion réussie sur le port {port}")
            return conn
        except Exception as e:
            if port == '5432':
                # Dernière tentative échouée
                print(f"❌ Erreur de connexion sur le port {port}: {e}")
                print("\n💡 Suggestions:")
                print("   1. Vérifiez que SUPABASE_URL est correct")
                print("   2. Vérifiez que SUPABASE_PASSWORD est correct")
                print("   3. Vérifiez votre connexion internet")
                print("   4. Vérifiez les paramètres de sécurité Supabase (peut nécessiter whitelist IP)")
                sys.exit(1)
            continue


def check_tables():
    """Vérifie l'existence des tables Gazelle."""
    conn = get_supabase_connection()
    cursor = conn.cursor()
    
    # Tables attendues
    expected_tables = [
        'gazelle.appointments',
        'gazelle.clients',
        'gazelle.contacts',
        'gazelle.pianos',
        'gazelle.timeline_entries'
    ]
    
    print("=" * 60)
    print("VÉRIFICATION DES TABLES GAZELLE DANS SUPABASE")
    print("=" * 60)
    
    # Vérifier si le schéma gazelle existe
    cursor.execute("""
        SELECT schema_name 
        FROM information_schema.schemata 
        WHERE schema_name = 'gazelle'
    """)
    schema_exists = cursor.fetchone()
    
    if not schema_exists:
        print("\n❌ Le schéma 'gazelle' n'existe pas")
        print("   → Les tables doivent être créées avant de migrer l'assistant")
        return
    
    print("\n✅ Le schéma 'gazelle' existe")
    
    # Vérifier chaque table
    print("\n📊 Vérification des tables:")
    print("-" * 60)
    
    existing_tables = []
    missing_tables = []
    
    for table in expected_tables:
        schema, table_name = table.split('.')
        cursor.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = %s AND table_name = %s
        """, (schema, table_name))
        
        result = cursor.fetchone()
        if result:
            # Compter les lignes
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"  ✅ {table}: {count} lignes")
            existing_tables.append(table)
        else:
            print(f"  ❌ {table}: N'existe pas")
            missing_tables.append(table)
    
    print("\n" + "=" * 60)
    print("RÉSUMÉ")
    print("=" * 60)
    print(f"✅ Tables existantes: {len(existing_tables)}/{len(expected_tables)}")
    print(f"❌ Tables manquantes: {len(missing_tables)}/{len(expected_tables)}")
    
    if missing_tables:
        print("\n⚠️  Tables manquantes:")
        for table in missing_tables:
            print(f"   - {table}")
        print("\n💡 Action requise: Créer les tables manquantes avant de migrer l'assistant")
    else:
        print("\n✅ Toutes les tables Gazelle existent!")
    
    cursor.close()
    conn.close()


if __name__ == "__main__":
    check_tables()

