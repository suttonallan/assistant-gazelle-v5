#!/usr/bin/env python3
"""
Script pour exécuter une migration SQL directement dans Supabase.
Utilise psycopg2 pour se connecter directement à PostgreSQL.
"""

import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

# Récupérer les credentials Supabase
supabase_url = os.getenv('SUPABASE_URL')
supabase_db_password = os.getenv('SUPABASE_DB_PASSWORD')
supabase_db_host = os.getenv('SUPABASE_DB_HOST', 'db.' + supabase_url.replace('https://', '').replace('.supabase.co', '') + '.supabase.co') if supabase_url else None
supabase_db_name = os.getenv('SUPABASE_DB_NAME', 'postgres')
supabase_db_user = os.getenv('SUPABASE_DB_USER', 'postgres')

if not supabase_db_password:
    print("❌ SUPABASE_DB_PASSWORD non défini dans .env")
    print("   Pour exécuter SQL directement, vous avez besoin de:")
    print("   - SUPABASE_DB_PASSWORD (mot de passe de la base de données)")
    print("   - SUPABASE_DB_HOST (optionnel, déduit depuis SUPABASE_URL)")
    print("\n   Alternative: Exécutez le SQL manuellement dans l'éditeur SQL de Supabase")
    sys.exit(1)

try:
    import psycopg2
    from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
except ImportError:
    print("❌ psycopg2 non installé")
    print("   Installez-le avec: pip install psycopg2-binary")
    print("\n   Alternative: Exécutez le SQL manuellement dans l'éditeur SQL de Supabase")
    sys.exit(1)

def execute_sql_file(sql_file_path: Path):
    """Exécute un fichier SQL dans Supabase."""
    print("="*70)
    print("🔧 EXÉCUTION DE LA MIGRATION SQL")
    print("="*70)
    
    # Lire le fichier SQL
    with open(sql_file_path, 'r') as f:
        sql_content = f.read()
    
    print(f"\n📋 Fichier: {sql_file_path}")
    print(f"📏 Taille: {len(sql_content)} caractères")
    
    # Construire la connection string
    if not supabase_db_host:
        # Extraire le host depuis SUPABASE_URL
        if supabase_url:
            project_ref = supabase_url.replace('https://', '').split('.')[0]
            supabase_db_host = f"db.{project_ref}.supabase.co"
        else:
            print("❌ Impossible de déterminer SUPABASE_DB_HOST")
            sys.exit(1)
    
    conn_string = f"host={supabase_db_host} dbname={supabase_db_name} user={supabase_db_user} password={supabase_db_password} port=5432"
    
    print(f"\n🔌 Connexion à: {supabase_db_host}")
    
    try:
        # Se connecter à la base
        conn = psycopg2.connect(conn_string)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        print("✅ Connecté à la base de données")
        
        # Exécuter le SQL
        print("\n📝 Exécution de la migration...")
        cursor.execute(sql_content)
        
        print("✅ Migration exécutée avec succès !")
        
        # Vérifier les colonnes ajoutées
        cursor.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'sync_logs' 
            ORDER BY column_name;
        """)
        
        columns = cursor.fetchall()
        print(f"\n📋 Colonnes dans sync_logs ({len(columns)}):")
        for col_name, col_type in columns:
            print(f"   ✅ {col_name:30} ({col_type})")
        
        cursor.close()
        conn.close()
        
        return True
        
    except psycopg2.Error as e:
        print(f"\n❌ Erreur PostgreSQL: {e}")
        import traceback
        traceback.print_exc()
        return False
    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    # Chemin du fichier SQL
    sql_file = Path(__file__).parent.parent / 'sql' / 'fix_sync_logs_schema.sql'
    
    if not sql_file.exists():
        print(f"❌ Fichier SQL non trouvé: {sql_file}")
        sys.exit(1)
    
    success = execute_sql_file(sql_file)
    
    if success:
        print("\n✅ Migration terminée avec succès !")
        print("   Vous pouvez maintenant relancer le script de test complet.")
    else:
        print("\n❌ Migration échouée")
        print("   Vérifiez les erreurs ci-dessus ou exécutez le SQL manuellement dans Supabase")
    
    sys.exit(0 if success else 1)
