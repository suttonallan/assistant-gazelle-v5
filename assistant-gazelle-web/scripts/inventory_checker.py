#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de vérification et d'alerte des stocks d'inventaire
Piano Technique Montréal - Version Web (Render/Supabase)

Fonctionnalités:
- Vérifie les stocks bas (Quantity <= ReorderThreshold)
- Génère des alertes pour chaque produit en rupture ou sous le seuil
- Compatible Supabase (PostgreSQL), SQLite et SQL Server (fallback)
"""

import os
import sys
from datetime import datetime
from typing import Dict, List, Optional, Any
import logging
from pathlib import Path

# Ajouter le répertoire parent au path pour les imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Détection automatique de la base de données (priorité Supabase)
USE_SUPABASE = bool(os.getenv("SUPABASE_HOST") or os.getenv("SUPABASE_URL"))
USE_SQLITE = os.getenv("USE_SQLITE", "false").lower() == "true" and not USE_SUPABASE


def get_db_connection():
    """Crée une connexion à la base de données (Supabase, SQLite ou SQL Server)"""
    if USE_SUPABASE:
        # Connexion Supabase (PostgreSQL) - PRIORITÉ
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
        
        conn_string = f"postgresql://{user}:{password}@{host}:{port}/{database}"
        return psycopg2.connect(conn_string)
    
    elif USE_SQLITE:
        # Connexion SQLite (pour développement local)
        import sqlite3
        db_path = Path("data/gazelle_web.db")
        db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(db_path), check_same_thread=False)
        conn.execute("PRAGMA foreign_keys = ON")
        return conn
    
    else:
        # Connexion SQL Server (fallback Windows)
        import pyodbc
        DB_CONN_STR = os.getenv("DB_CONN_STR")
        if not DB_CONN_STR:
            raise ValueError("DB_CONN_STR non défini et SUPABASE_HOST non trouvé")
        return pyodbc.connect(DB_CONN_STR)


def check_low_stock(technician_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Vérifie les stocks bas (Quantity <= ReorderThreshold)
    
    Args:
        technician_id: ID Gazelle du technicien (optionnel, None = tous les techniciens)
    
    Returns:
        Liste de dicts avec les alertes de stock bas
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        if USE_SUPABASE:
            # Requête PostgreSQL
            if technician_id:
                query = """
                SELECT
                    p.ProductId,
                    p.Name,
                    p.Sku,
                    i.TechnicianId,
                    i.Quantity,
                    i.ReorderThreshold,
                    i.UpdatedAt,
                    COALESCE(pd.DisplayNameFr, p.Name) AS DisplayName,
                    COALESCE(pd.Category, '') AS Category
                FROM "inv"."Products" p
                INNER JOIN "inv"."Inventory" i ON p.ProductId = i.ProductId
                LEFT JOIN "inv"."ProductDisplay" pd ON p.ProductId = pd.ProductId AND (pd.Active = 1 OR pd.Active IS NULL)
                WHERE p.Active = 1
                  AND i.Quantity <= i.ReorderThreshold
                  AND i.TechnicianId = %s
                ORDER BY i.Quantity ASC, p.Name ASC
                """
                cursor.execute(query, (technician_id,))
            else:
                query = """
                SELECT
                    p.ProductId,
                    p.Name,
                    p.Sku,
                    i.TechnicianId,
                    i.Quantity,
                    i.ReorderThreshold,
                    i.UpdatedAt,
                    COALESCE(pd.DisplayNameFr, p.Name) AS DisplayName,
                    COALESCE(pd.Category, '') AS Category
                FROM "inv"."Products" p
                INNER JOIN "inv"."Inventory" i ON p.ProductId = i.ProductId
                LEFT JOIN "inv"."ProductDisplay" pd ON p.ProductId = pd.ProductId AND (pd.Active = 1 OR pd.Active IS NULL)
                WHERE p.Active = 1
                  AND i.Quantity <= i.ReorderThreshold
                ORDER BY i.Quantity ASC, p.Name ASC
                """
                cursor.execute(query)
        
        elif USE_SQLITE:
            # Requête SQLite
            if technician_id:
                query = """
                SELECT
                    p.ProductId,
                    p.Name,
                    p.Sku,
                    i.TechnicianId,
                    i.Quantity,
                    i.ReorderThreshold,
                    i.UpdatedAt,
                    COALESCE(pd.DisplayNameFr, p.Name) AS DisplayName,
                    COALESCE(pd.Category, '') AS Category
                FROM Products p
                INNER JOIN Inventory i ON p.ProductId = i.ProductId
                LEFT JOIN ProductDisplay pd ON p.ProductId = pd.ProductId AND (pd.Active = 1 OR pd.Active IS NULL)
                WHERE p.Active = 1
                  AND i.Quantity <= i.ReorderThreshold
                  AND i.TechnicianId = ?
                ORDER BY i.Quantity ASC, p.Name ASC
                """
                cursor.execute(query, (technician_id,))
            else:
                query = """
                SELECT
                    p.ProductId,
                    p.Name,
                    p.Sku,
                    i.TechnicianId,
                    i.Quantity,
                    i.ReorderThreshold,
                    i.UpdatedAt,
                    COALESCE(pd.DisplayNameFr, p.Name) AS DisplayName,
                    COALESCE(pd.Category, '') AS Category
                FROM Products p
                INNER JOIN Inventory i ON p.ProductId = i.ProductId
                LEFT JOIN ProductDisplay pd ON p.ProductId = pd.ProductId AND (pd.Active = 1 OR pd.Active IS NULL)
                WHERE p.Active = 1
                  AND i.Quantity <= i.ReorderThreshold
                ORDER BY i.Quantity ASC, p.Name ASC
                """
                cursor.execute(query)
        
        else:
            # Requête SQL Server
            if technician_id:
                query = """
                SELECT
                    p.ProductId,
                    p.Name,
                    p.Sku,
                    i.TechnicianId,
                    i.Quantity,
                    i.ReorderThreshold,
                    i.UpdatedAt,
                    COALESCE(pd.DisplayNameFr, p.Name) AS DisplayName,
                    COALESCE(pd.Category, '') AS Category
                FROM inv.Products p
                INNER JOIN inv.Inventory i ON p.ProductId = i.ProductId
                LEFT JOIN inv.ProductDisplay pd ON p.ProductId = pd.ProductId AND (pd.Active = 1 OR pd.Active IS NULL)
                WHERE p.Active = 1
                  AND i.Quantity <= i.ReorderThreshold
                  AND i.TechnicianId = ?
                ORDER BY i.Quantity ASC, p.Name ASC
                """
                cursor.execute(query, (technician_id,))
            else:
                query = """
                SELECT
                    p.ProductId,
                    p.Name,
                    p.Sku,
                    i.TechnicianId,
                    i.Quantity,
                    i.ReorderThreshold,
                    i.UpdatedAt,
                    COALESCE(pd.DisplayNameFr, p.Name) AS DisplayName,
                    COALESCE(pd.Category, '') AS Category
                FROM inv.Products p
                INNER JOIN inv.Inventory i ON p.ProductId = i.ProductId
                LEFT JOIN inv.ProductDisplay pd ON p.ProductId = pd.ProductId AND (pd.Active = 1 OR pd.Active IS NULL)
                WHERE p.Active = 1
                  AND i.Quantity <= i.ReorderThreshold
                ORDER BY i.Quantity ASC, p.Name ASC
                """
                cursor.execute(query)
        
        alerts = []
        for row in cursor.fetchall():
            alerts.append({
                'product_id': row[0],
                'product_name': row[1],
                'sku': row[2] or '',
                'technician_id': row[3],
                'quantity': row[4],
                'reorder_threshold': row[5],
                'last_updated': row[6].isoformat() if row[6] else None,
                'display_name': row[7] or row[1],
                'category': row[8] or ''
            })
        
        return alerts
        
    except Exception as e:
        logger.error(f"Erreur lors de la vérification des stocks: {e}")
        import traceback
        traceback.print_exc()
        return []
    finally:
        conn.close()


def check_zero_stock(technician_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Vérifie les produits en rupture de stock (Quantity = 0)
    
    Args:
        technician_id: ID Gazelle du technicien (optionnel, None = tous les techniciens)
    
    Returns:
        Liste de dicts avec les alertes de rupture
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Construire la requête selon le type de DB
        if USE_SUPABASE:
            schema_prefix = '"inv".'
            param_style = '%s'
        elif USE_SQLITE:
            schema_prefix = ''
            param_style = '?'
        else:
            schema_prefix = 'inv.'
            param_style = '?'
        
        if technician_id:
            query = f"""
            SELECT
                p.ProductId,
                p.Name,
                p.Sku,
                i.TechnicianId,
                i.Quantity,
                i.ReorderThreshold,
                i.UpdatedAt,
                COALESCE(pd.DisplayNameFr, p.Name) AS DisplayName,
                COALESCE(pd.Category, '') AS Category
            FROM {schema_prefix}Products p
            INNER JOIN {schema_prefix}Inventory i ON p.ProductId = i.ProductId
            LEFT JOIN {schema_prefix}ProductDisplay pd ON p.ProductId = pd.ProductId AND (pd.Active = 1 OR pd.Active IS NULL)
            WHERE p.Active = 1
              AND i.Quantity = 0
              AND i.TechnicianId = {param_style}
            ORDER BY p.Name ASC
            """
            cursor.execute(query, (technician_id,))
        else:
            query = f"""
            SELECT
                p.ProductId,
                p.Name,
                p.Sku,
                i.TechnicianId,
                i.Quantity,
                i.ReorderThreshold,
                i.UpdatedAt,
                COALESCE(pd.DisplayNameFr, p.Name) AS DisplayName,
                COALESCE(pd.Category, '') AS Category
            FROM {schema_prefix}Products p
            INNER JOIN {schema_prefix}Inventory i ON p.ProductId = i.ProductId
            LEFT JOIN {schema_prefix}ProductDisplay pd ON p.ProductId = pd.ProductId AND (pd.Active = 1 OR pd.Active IS NULL)
            WHERE p.Active = 1
              AND i.Quantity = 0
            ORDER BY p.Name ASC
            """
            cursor.execute(query)
        
        alerts = []
        for row in cursor.fetchall():
            alerts.append({
                'product_id': row[0],
                'product_name': row[1],
                'sku': row[2] or '',
                'technician_id': row[3],
                'quantity': row[4],
                'reorder_threshold': row[5],
                'last_updated': row[6].isoformat() if row[6] else None,
                'display_name': row[7] or row[1],
                'category': row[8] or ''
            })
        
        return alerts
        
    except Exception as e:
        logger.error(f"Erreur lors de la vérification des ruptures: {e}")
        import traceback
        traceback.print_exc()
        return []
    finally:
        conn.close()


def generate_alerts(technician_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Génère toutes les alertes de stock
    
    Args:
        technician_id: ID Gazelle du technicien (optionnel)
    
    Returns:
        Dict avec:
            - low_stock: Liste des produits sous le seuil
            - zero_stock: Liste des produits en rupture
            - summary: Résumé des alertes
    """
    # Vérifier stocks bas
    low_stock = check_low_stock(technician_id)
    
    # Vérifier ruptures
    zero_stock = check_zero_stock(technician_id)
    
    # Résumé
    summary = {
        'total_low_stock': len(low_stock),
        'total_zero_stock': len(zero_stock),
        'total_alerts': len(low_stock) + len(zero_stock),
        'checked_at': datetime.now().isoformat()
    }
    
    return {
        'low_stock': low_stock,
        'zero_stock': zero_stock,
        'summary': summary
    }


def main():
    """Fonction principale"""
    print("\n" + "="*60)
    print("🛒 VÉRIFICATION ET ALERTES DE STOCK")
    print("   Piano Technique Montréal - Version Web")
    print("="*60)
    
    # Afficher le type de DB
    if USE_SUPABASE:
        db_type = "Supabase (PostgreSQL)"
    elif USE_SQLITE:
        db_type = "SQLite"
    else:
        db_type = "SQL Server"
    
    print(f"📊 Base de données: {db_type}")
    
    # Vérifier la connexion
    try:
        conn = get_db_connection()
        conn.close()
        print("✅ Connexion à la base de données OK")
    except Exception as e:
        print(f"❌ Erreur de connexion: {e}")
        return
    
    # Générer les alertes
    alerts = generate_alerts()
    
    # Afficher les résultats
    print(f"\n📉 Stocks bas (≤ seuil): {alerts['summary']['total_low_stock']}")
    print(f"❌ Ruptures de stock: {alerts['summary']['total_zero_stock']}")
    print(f"📊 Total d'alertes: {alerts['summary']['total_alerts']}")
    
    return alerts


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Interrompu par l'utilisateur")
    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        import traceback
        traceback.print_exc()

