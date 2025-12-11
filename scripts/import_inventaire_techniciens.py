#!/usr/bin/env python3
"""
Script d'importation de l'inventaire des techniciens depuis Gazelle inv.Inventory.

Importe les stocks par technicien depuis SQL Server Gazelle (V4) vers Supabase inventaire_techniciens (V5).

⚠️  RÈGLE IMPORTANTE: MIGRATION V4 → V5
- LECTURE SEULE depuis V4 (SQL Server Gazelle) - Ne jamais modifier V4
- ÉCRITURE dans V5 (Supabase) - Nouvelle base de données
"""

import sys
import os
from typing import List, Dict, Any
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Charger .env
env_path = Path(__file__).parent.parent / '.env'
if env_path.exists():
    load_dotenv(env_path)

# Changer vers le répertoire du projet
script_dir = os.path.dirname(os.path.abspath(__file__))
project_dir = os.path.dirname(script_dir)
os.chdir(project_dir)

sys.path.insert(0, project_dir)

from core.supabase_storage import SupabaseStorage
import requests

# Forcer le flush immédiat
sys.stdout.reconfigure(line_buffering=True) if hasattr(sys.stdout, 'reconfigure') else None

print("🔄 Importation de l'inventaire des techniciens depuis Gazelle...", flush=True)
print()

def fetch_inventaire_from_gazelle() -> List[Dict[str, Any]]:
    """Récupère l'inventaire des techniciens depuis Gazelle inv.Inventory."""
    if sys.platform != "win32":
        print("⚠️  Ce script doit être exécuté sur Windows (PC) pour accéder à SQL Server", flush=True)
        return []
    
    try:
        import pyodbc
        print("🔌 Connexion à SQL Server Gazelle...", flush=True)
        
        # Configuration SQL Server
        db_conn_str = os.environ.get('DB_CONN_STR') or os.environ.get('SQL_SERVER_CONN_STR')
        if not db_conn_str:
            server = os.environ.get('SQL_SERVER', 'PIANOTEK\\SQLEXPRESS')
            database = os.environ.get('SQL_DATABASE', 'PianoTek')
            db_conn_str = f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={server};DATABASE={database};Trusted_Connection=yes;"
        
        conn = pyodbc.connect(db_conn_str)
        cursor = conn.cursor()
        
        # Requête pour récupérer l'inventaire avec les noms de produits
        # Essayer de joindre avec Users pour obtenir le nom du technicien
        # Si pas de table Users, utiliser TechnicianId tel quel
        query = """
        SELECT
            p.ProductId,
            COALESCE(NULLIF(p.Sku, ''), 'PROD-' + CAST(p.ProductId AS VARCHAR)) AS code_produit,
            p.Name AS nom_produit,
            CAST(i.TechnicianId AS VARCHAR) AS technicien_id,
            COALESCE(u.FirstName + ' ' + u.LastName, u.Email, CAST(i.TechnicianId AS VARCHAR)) AS technicien,
            i.Quantity AS quantite_stock,
            i.ReorderThreshold AS seuil_reapprovisionnement,
            i.UpdatedAt AS derniere_verification
        FROM inv.Inventory i
        INNER JOIN inv.Products p ON i.ProductId = p.ProductId
        LEFT JOIN auth.Users u ON CAST(i.TechnicianId AS VARCHAR) = u.Id
        WHERE p.Active = 1
          AND i.Quantity > 0
        ORDER BY i.TechnicianId, p.Sku
        """
        
        cursor.execute(query)
        rows = cursor.fetchall()
        
        # Convertir en dictionnaires
        columns = [column[0] for column in cursor.description]
        inventaire = []
        for row in rows:
            inventaire_dict = dict(zip(columns, row))
            # Nettoyer les valeurs
            for key, value in inventaire_dict.items():
                if isinstance(value, str):
                    inventaire_dict[key] = value.strip() if value else None
            
            # Fallback final pour code_produit si toujours NULL
            if not inventaire_dict.get("code_produit"):
                product_id = inventaire_dict.get("ProductId")
                if product_id:
                    inventaire_dict["code_produit"] = f"PROD-{product_id}"
            
            inventaire.append(inventaire_dict)
        
        conn.close()
        
        print(f"✅ {len(inventaire)} enregistrements d'inventaire récupérés depuis Gazelle SQL Server", flush=True)
        return inventaire
        
    except ImportError:
        print("⚠️  pyodbc non installé. Installez avec: pip install pyodbc", flush=True)
        return []
    except Exception as e:
        print(f"❌ Erreur de connexion SQL Server: {e}", flush=True)
        return []

def map_to_supabase(inventaire_item: Dict[str, Any]) -> Dict[str, Any]:
    """Convertit un enregistrement d'inventaire Gazelle en format Supabase."""
    # technicien est déjà dans le format string depuis la requête SQL
    technicien = str(inventaire_item.get("technicien", "")).strip()
    
    return {
        "code_produit": inventaire_item.get("code_produit"),
        "technicien": technicien,
        "quantite_stock": float(inventaire_item.get("quantite_stock", 0)),
        "emplacement": "Atelier",  # Par défaut, peut être modifié plus tard
        "derniere_verification": inventaire_item.get("derniere_verification").isoformat() if inventaire_item.get("derniere_verification") else None
    }

def import_inventaire():
    """Importe l'inventaire des techniciens dans Supabase."""
    try:
        storage = SupabaseStorage()
        
        # Récupérer depuis Gazelle
        inventaire_gazelle = fetch_inventaire_from_gazelle()
        
        if not inventaire_gazelle:
            print("⚠️  Aucun inventaire à importer", flush=True)
            return
        
        print()
        print("📦 Importation dans Supabase...", flush=True)
        
        stats = {"total": 0, "crees": 0, "mis_a_jour": 0, "erreurs": 0}
        
        for item in inventaire_gazelle:
            stats["total"] += 1
            code_produit = item.get("code_produit")
            
            if not code_produit:
                print(f"  ⚠️  Enregistrement sans code_produit, ignoré", flush=True)
                stats["erreurs"] += 1
                continue
            
            # Vérifier que le produit existe dans le catalogue
            produit_catalogue = storage.get_data("produits_catalogue", filters={"code_produit": code_produit})
            if not produit_catalogue:
                print(f"  ⚠️  {code_produit}: Produit non trouvé dans le catalogue, ignoré", flush=True)
                stats["erreurs"] += 1
                continue
            
            # Convertir au format Supabase
            inventaire_data = map_to_supabase(item)
            
            # Vérifier si existe déjà
            existing = storage.get_data(
                "inventaire_techniciens",
                filters={
                    "code_produit": code_produit,
                    "technicien": inventaire_data["technicien"],
                    "emplacement": inventaire_data["emplacement"]
                }
            )
            
            # Pour inventaire_techniciens, utiliser PATCH avec filtre composite
            # Si 404, faire POST
            if existing:
                # Mise à jour
                url = f"{storage.api_url}/inventaire_techniciens?code_produit=eq.{code_produit}&technicien=eq.{inventaire_data['technicien']}&emplacement=eq.{inventaire_data['emplacement']}"
                headers = storage._get_headers()
                response = requests.patch(url, headers=headers, json=inventaire_data)
                success = response.status_code in [200, 204]
            else:
                # Création
                url = f"{storage.api_url}/inventaire_techniciens"
                headers = storage._get_headers()
                headers["Prefer"] = "return=representation"
                response = requests.post(url, headers=headers, json=inventaire_data)
                success = response.status_code in [200, 201]
            
            if not success:
                try:
                    error_data = response.json()
                    error = error_data.get('message') or error_data.get('hint') or error_data.get('details') or str(error_data)
                    print(f"  ❌ {code_produit} - {inventaire_data['technicien']}: {error}", flush=True)
                    # Si erreur de clé étrangère, vérifier si le produit existe dans le catalogue
                    if "foreign key" in error.lower() or "violates foreign key" in error.lower():
                        # Vérifier si le produit existe dans le catalogue
                        produit_catalogue = storage.get_data("produits_catalogue", filters={"code_produit": code_produit})
                        if not produit_catalogue:
                            print(f"     ⚠️  Le produit {code_produit} n'existe pas dans le catalogue. Il doit être importé d'abord.", flush=True)
                except:
                    print(f"  ❌ {code_produit} - {inventaire_data['technicien']}: Erreur {response.status_code}: {response.text}", flush=True)
            
            if success:
                if existing:
                    print(f"  ✅ {code_produit} - {inventaire_data['technicien']}: Mis à jour (qty: {inventaire_data['quantite_stock']})", flush=True)
                    stats["mis_a_jour"] += 1
                else:
                    print(f"  ✅ {code_produit} - {inventaire_data['technicien']}: Créé (qty: {inventaire_data['quantite_stock']})", flush=True)
                    stats["crees"] += 1
            else:
                print(f"  ❌ {code_produit} - {inventaire_data['technicien']}: Échec", flush=True)
                stats["erreurs"] += 1
        
        print()
        print("📊 Statistiques d'importation:", flush=True)
        print(f"   Total traité: {stats['total']}", flush=True)
        print(f"   ✅ Créés: {stats['crees']}", flush=True)
        print(f"   ✅ Mis à jour: {stats['mis_a_jour']}", flush=True)
        print(f"   ❌ Erreurs: {stats['erreurs']}", flush=True)
        
    except Exception as e:
        print(f"\n❌ Erreur fatale: {e}", flush=True)
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    import_inventaire()
