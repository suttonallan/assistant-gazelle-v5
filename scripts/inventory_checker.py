#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de vérification et d'alerte des stocks d'inventaire
Piano Technique Montréal

Fonctionnalités:
- Vérifie les stocks bas (Quantity <= ReorderThreshold)
- Génère des alertes pour chaque produit en rupture ou sous le seuil
- Compatible SQL Server et Supabase (PostgreSQL)
"""

import os
import sys
from datetime import datetime
from typing import Dict, List, Optional, Any
import logging

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Détection automatique de la base de données
USE_SUPABASE = bool(os.getenv("SUPABASE_HOST") or os.getenv("SUPABASE_URL"))


def get_db_connection():
    """Crée une connexion à la base de données (Supabase ou SQL Server)"""
    if USE_SUPABASE:
        # Connexion Supabase (PostgreSQL)
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
    else:
        # Connexion SQL Server (fallback)
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
                  AND i.Quantity = 0
                  AND i.TechnicianId = %s
                ORDER BY p.Name ASC
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
                  AND i.Quantity = 0
                ORDER BY p.Name ASC
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
                  AND i.Quantity = 0
                  AND i.TechnicianId = ?
                ORDER BY p.Name ASC
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
    print("\n" + "="*60)
    print("🔍 VÉRIFICATION DES STOCKS")
    print("="*60)
    
    db_type = "Supabase (PostgreSQL)" if USE_SUPABASE else "SQL Server"
    print(f"📊 Base de données: {db_type}")
    
    if technician_id:
        print(f"👤 Technicien: {technician_id}")
    else:
        print("👤 Tous les techniciens")
    
    # Vérifier stocks bas
    print("\n🔍 Vérification des stocks bas (Quantity <= ReorderThreshold)...")
    low_stock = check_low_stock(technician_id)
    print(f"   ✅ {len(low_stock)} produit(s) sous le seuil")
    
    # Vérifier ruptures
    print("\n🔍 Vérification des ruptures (Quantity = 0)...")
    zero_stock = check_zero_stock(technician_id)
    print(f"   ✅ {len(zero_stock)} produit(s) en rupture")
    
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


def print_alerts(alerts: Dict[str, Any]):
    """Affiche les alertes de manière lisible"""
    print("\n" + "="*60)
    print("📊 RÉSULTATS DES VÉRIFICATIONS")
    print("="*60)
    
    print(f"\n📉 Stocks bas (≤ seuil): {alerts['summary']['total_low_stock']}")
    if alerts['low_stock']:
        for alert in alerts['low_stock']:
            print(f"   ⚠️  {alert['display_name']} (SKU: {alert['sku']})")
            print(f"      Technicien: {alert['technician_id']}")
            print(f"      Stock: {alert['quantity']} / Seuil: {alert['reorder_threshold']}")
            print()
    else:
        print("   ✅ Aucun stock bas")
    
    print(f"\n❌ Ruptures de stock: {alerts['summary']['total_zero_stock']}")
    if alerts['zero_stock']:
        for alert in alerts['zero_stock']:
            print(f"   🔴 {alert['display_name']} (SKU: {alert['sku']})")
            print(f"      Technicien: {alert['technician_id']}")
            print(f"      Stock: 0 / Seuil: {alert['reorder_threshold']}")
            print()
    else:
        print("   ✅ Aucune rupture")
    
    print(f"\n📊 Total d'alertes: {alerts['summary']['total_alerts']}")


def main():
    """Fonction principale"""
    print("\n" + "="*60)
    print("🛒 VÉRIFICATION ET ALERTES DE STOCK")
    print("   Piano Technique Montréal")
    print("="*60)
    
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
    print_alerts(alerts)
    
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

