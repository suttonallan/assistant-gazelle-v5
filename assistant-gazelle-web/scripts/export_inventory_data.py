#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script d'export des données d'inventaire actuelles
Piano Technique Montréal - Version Web (Render/Supabase)

Exporte:
- Products (catalogue)
- Inventory (stock par technicien)
- ProductDisplay (métadonnées d'affichage, si existe)
- Transactions (historique, optionnel)

Formats: CSV et JSON
Compatible: Supabase (PostgreSQL), SQLite et SQL Server
"""

import os
import sys
import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

# Ajouter le répertoire parent au path pour les imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Détection automatique de la base de données
USE_SUPABASE = bool(os.getenv("SUPABASE_HOST") or os.getenv("SUPABASE_URL"))
USE_SQLITE = os.getenv("USE_SQLITE", "false").lower() == "true" and not USE_SUPABASE


def get_db_connection():
    """Crée une connexion à la base de données"""
    if USE_SUPABASE:
        import psycopg2
        from dotenv import load_dotenv
        load_dotenv()
        
        supabase_url = os.getenv('SUPABASE_URL')
        if supabase_url:
            from urllib.parse import urlparse
            parsed = urlparse(supabase_url)
            host = parsed.hostname
            database = os.getenv('SUPABASE_DATABASE', 'postgres')
            user = os.getenv('SUPABASE_USER', 'postgres')
            password = os.getenv('SUPABASE_PASSWORD')
            port = os.getenv('SUPABASE_PORT', '5432')
        else:
            host = os.getenv('SUPABASE_HOST')
            database = os.getenv('SUPABASE_DATABASE', 'postgres')
            user = os.getenv('SUPABASE_USER', 'postgres')
            password = os.getenv('SUPABASE_PASSWORD')
            port = int(os.getenv('SUPABASE_PORT', '5432'))
        
        if not password:
            raise ValueError("SUPABASE_PASSWORD non défini")
        
        return psycopg2.connect(f"postgresql://{user}:{password}@{host}:{port}/{database}")
    
    elif USE_SQLITE:
        import sqlite3
        db_path = Path("data/gazelle_web.db")
        db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(db_path), check_same_thread=False)
        conn.execute("PRAGMA foreign_keys = ON")
        return conn
    
    else:
        import pyodbc
        DB_CONN_STR = os.getenv("DB_CONN_STR")
        if not DB_CONN_STR:
            raise ValueError("DB_CONN_STR non défini et SUPABASE_HOST non trouvé")
        return pyodbc.connect(DB_CONN_STR)


def _get_schema_prefix():
    """Retourne le préfixe de schéma selon le type de DB"""
    if USE_SUPABASE:
        return '"inv".'
    elif USE_SQLITE:
        return ''
    else:
        return 'inv.'


def export_products(output_dir: Path) -> int:
    """Exporte Products en CSV et JSON"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        schema_prefix = _get_schema_prefix()
        query = f"""
        SELECT ProductId, Name, Sku, UnitCost, RetailPrice, Active, CreatedAt
        FROM {schema_prefix}Products
        ORDER BY ProductId
        """
        
        cursor.execute(query)
        rows = cursor.fetchall()
        
        # Préparer les données
        products = []
        for row in rows:
            products.append({
                'ProductId': row[0],
                'Name': row[1],
                'Sku': row[2] or '',
                'UnitCost': float(row[3]) if row[3] else 0.0,
                'RetailPrice': float(row[4]) if row[4] else 0.0,
                'Active': bool(row[5]) if row[5] is not None else True,
                'CreatedAt': row[6].isoformat() if row[6] else None
            })
        
        # Export CSV
        csv_path = output_dir / 'products.csv'
        with open(csv_path, 'w', newline='', encoding='utf-8-sig') as f:
            if products:
                writer = csv.DictWriter(f, fieldnames=products[0].keys())
                writer.writeheader()
                writer.writerows(products)
        
        # Export JSON
        json_path = output_dir / 'products.json'
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(products, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Products: {len(products)} produits exportés")
        return len(products)
        
    except Exception as e:
        print(f"❌ Erreur export Products: {e}")
        import traceback
        traceback.print_exc()
        return 0
    finally:
        conn.close()


def export_inventory(output_dir: Path) -> int:
    """Exporte Inventory en CSV et JSON"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        schema_prefix = _get_schema_prefix()
        query = f"""
        SELECT InventoryId, ProductId, TechnicianId, Quantity, ReorderThreshold, UpdatedAt
        FROM {schema_prefix}Inventory
        ORDER BY ProductId, TechnicianId
        """
        
        cursor.execute(query)
        rows = cursor.fetchall()
        
        # Préparer les données
        inventory = []
        for row in rows:
            inventory.append({
                'InventoryId': row[0],
                'ProductId': row[1],
                'TechnicianId': row[2],
                'Quantity': row[3],
                'ReorderThreshold': row[4] if row[4] else 0,
                'UpdatedAt': row[5].isoformat() if row[5] else None
            })
        
        # Export CSV
        csv_path = output_dir / 'inventory.csv'
        with open(csv_path, 'w', newline='', encoding='utf-8-sig') as f:
            if inventory:
                writer = csv.DictWriter(f, fieldnames=inventory[0].keys())
                writer.writeheader()
                writer.writerows(inventory)
        
        # Export JSON
        json_path = output_dir / 'inventory.json'
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(inventory, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Inventory: {len(inventory)} entrées exportées")
        return len(inventory)
        
    except Exception as e:
        print(f"❌ Erreur export Inventory: {e}")
        import traceback
        traceback.print_exc()
        return 0
    finally:
        conn.close()


def export_product_display(output_dir: Path) -> int:
    """Exporte ProductDisplay en CSV et JSON (si existe)"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Vérifier si la table existe
        if USE_SUPABASE:
            cursor.execute("""
                SELECT COUNT(*) FROM information_schema.tables
                WHERE table_schema = 'inv' AND table_name = 'ProductDisplay'
            """)
        elif USE_SQLITE:
            cursor.execute("""
                SELECT COUNT(*) FROM sqlite_master
                WHERE type='table' AND name='ProductDisplay'
            """)
        else:
            cursor.execute("""
                SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES
                WHERE TABLE_SCHEMA = 'inv' AND TABLE_NAME = 'ProductDisplay'
            """)
        
        exists = cursor.fetchone()[0] > 0
        
        if not exists:
            print("⚠️  ProductDisplay n'existe pas - ignoré")
            return 0
        
        # Exporter
        schema_prefix = _get_schema_prefix()
        query = f"""
        SELECT DisplayId, ProductId, DisplayOrder, DisplayNameFr, DisplayNameEn,
               Category, VariantGroup, VariantLabel, MSLId, MSLName,
               HasCommission, CommissionRate, Active, CreatedAt, UpdatedAt
        FROM {schema_prefix}ProductDisplay
        ORDER BY ProductId
        """
        
        cursor.execute(query)
        rows = cursor.fetchall()
        
        # Préparer les données
        product_display = []
        for row in rows:
            product_display.append({
                'DisplayId': row[0],
                'ProductId': row[1],
                'DisplayOrder': row[2] if row[2] else 9999,
                'DisplayNameFr': row[3] or '',
                'DisplayNameEn': row[4] or '',
                'Category': row[5] or '',
                'VariantGroup': row[6] or '',
                'VariantLabel': row[7] or '',
                'MSLId': row[8] or '',
                'MSLName': row[9] or '',
                'HasCommission': bool(row[10]) if row[10] is not None else False,
                'CommissionRate': float(row[11]) if row[11] else 0.0,
                'Active': bool(row[12]) if row[12] is not None else True,
                'CreatedAt': row[13].isoformat() if row[13] else None,
                'UpdatedAt': row[14].isoformat() if row[14] else None
            })
        
        # Export CSV
        csv_path = output_dir / 'product_display.csv'
        with open(csv_path, 'w', newline='', encoding='utf-8-sig') as f:
            if product_display:
                writer = csv.DictWriter(f, fieldnames=product_display[0].keys())
                writer.writeheader()
                writer.writerows(product_display)
        
        # Export JSON
        json_path = output_dir / 'product_display.json'
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(product_display, f, indent=2, ensure_ascii=False)
        
        print(f"✅ ProductDisplay: {len(product_display)} entrées exportées")
        return len(product_display)
        
    except Exception as e:
        print(f"❌ Erreur export ProductDisplay: {e}")
        import traceback
        traceback.print_exc()
        return 0
    finally:
        conn.close()


def main():
    """Fonction principale"""
    print("\n" + "="*60)
    print("📦 EXPORT DES DONNÉES D'INVENTAIRE")
    print("   Piano Technique Montréal - Version Web")
    print("="*60)
    
    # Déterminer le répertoire de sortie
    output_dir = Path("data/export_inventory")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    if USE_SUPABASE:
        db_type = "Supabase (PostgreSQL)"
    elif USE_SQLITE:
        db_type = "SQLite"
    else:
        db_type = "SQL Server"
    
    print(f"\n📊 Base de données: {db_type}")
    print(f"📁 Répertoire de sortie: {output_dir.absolute()}")
    
    # Vérifier la connexion
    try:
        conn = get_db_connection()
        conn.close()
        print("✅ Connexion à la base de données OK")
    except Exception as e:
        print(f"❌ Erreur de connexion: {e}")
        return
    
    # Exporter chaque table
    print("\n📤 Export en cours...")
    
    total = {
        'products': 0,
        'inventory': 0,
        'product_display': 0
    }
    
    total['products'] = export_products(output_dir)
    total['inventory'] = export_inventory(output_dir)
    total['product_display'] = export_product_display(output_dir)
    
    # Résumé
    print("\n" + "="*60)
    print("📊 RÉSUMÉ DE L'EXPORT")
    print("="*60)
    print(f"   Products: {total['products']} produits")
    print(f"   Inventory: {total['inventory']} entrées")
    print(f"   ProductDisplay: {total['product_display']} entrées")
    print(f"\n📁 Fichiers créés dans: {output_dir.absolute()}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Interrompu par l'utilisateur")
    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        import traceback
        traceback.print_exc()

