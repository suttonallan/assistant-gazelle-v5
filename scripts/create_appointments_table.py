#!/usr/bin/env python3
"""
Script pour créer la table gazelle_appointments dans Supabase.

Usage:
    python3 scripts/create_appointments_table.py
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
    for port in ['6543', '5432']:
        try:
            conn = psycopg2.connect(
                host=host,
                database=database,
                user=user,
                password=password,
                port=port,
                connect_timeout=10
            )
            return conn
        except Exception as e:
            if port == '5432':
                print(f"❌ Erreur de connexion: {e}")
                print("\n💡 Utilisez plutôt le Supabase Dashboard → SQL Editor")
                sys.exit(1)
            continue


def read_sql_file():
    """Lit le fichier SQL."""
    sql_file = Path(__file__).parent.parent / 'modules' / 'sync_gazelle' / 'create_appointments_table.sql'
    
    if not sql_file.exists():
        print(f"❌ Fichier SQL non trouvé: {sql_file}")
        sys.exit(1)
    
    with open(sql_file, 'r', encoding='utf-8') as f:
        return f.read()


def main():
    """Point d'entrée principal."""
    print("=" * 60)
    print("🔧 CRÉATION DE LA TABLE gazelle_appointments")
    print("=" * 60)
    
    # Lire le SQL
    sql_content = read_sql_file()
    print("✅ Fichier SQL chargé")
    
    # Se connecter à Supabase
    print("\n🔄 Connexion à Supabase...")
    try:
        conn = get_supabase_connection()
        print("✅ Connexion réussie")
    except Exception as e:
        print(f"❌ Erreur de connexion: {e}")
        print("\n💡 Alternative: Utilisez le Supabase Dashboard → SQL Editor")
        print(f"   Fichier SQL: modules/sync_gazelle/create_appointments_table.sql")
        sys.exit(1)
    
    # Exécuter le SQL
    print("\n📝 Exécution du script SQL...")
    cursor = conn.cursor()
    
    try:
        cursor.execute(sql_content)
        conn.commit()
        print("✅ Table gazelle_appointments créée avec succès!")
        print("\n📊 Vérification...")
        
        # Vérifier que la table existe
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = 'gazelle_appointments'
        """)
        
        if cursor.fetchone():
            print("✅ Table vérifiée dans Supabase")
        else:
            print("⚠️ Table créée mais non trouvée dans information_schema")
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Erreur lors de l'exécution: {e}")
        sys.exit(1)
    finally:
        cursor.close()
        conn.close()
    
    print("\n" + "=" * 60)
    print("✅ TERMINÉ")
    print("=" * 60)
    print("\n💡 La table est maintenant accessible via:")
    print("   GET /rest/v1/gazelle_appointments")


if __name__ == "__main__":
    main()



