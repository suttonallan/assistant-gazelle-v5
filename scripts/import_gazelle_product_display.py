#!/usr/bin/env python3
"""
Script d'importation des classifications de produits depuis Gazelle inv.ProductDisplay.

Synchronise les métadonnées de produits (commissions, variantes, catégories)
depuis SQL Server Gazelle (V4) vers Supabase produits_catalogue (V5).

⚠️  RÈGLE IMPORTANTE: MIGRATION V4 → V5
- LECTURE SEULE depuis V4 (SQL Server Gazelle) - Ne jamais modifier V4
- ÉCRITURE dans V5 (Supabase) - Nouvelle base de données
- V4 continue de fonctionner normalement, on ne le touche pas

📋 RÉFÉRENCE SCHEMA:
- Consulter docs/SCHEMA_PRODUITS_CATALOGUE.md pour les colonnes valides
- Ne jamais inventer de noms de colonnes!
- Utiliser UNIQUEMENT les colonnes définies dans les migrations 001 et 002
"""

import sys
import os
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Charger les variables d'environnement depuis .env
env_path = Path(__file__).parent.parent / '.env'
if env_path.exists():
    load_dotenv(env_path)
    print(f"✅ [DEBUG] Variables d'environnement chargées depuis: {env_path}", flush=True)
else:
    print(f"⚠️  [DEBUG] Fichier .env non trouvé: {env_path}", flush=True)

# Forcer le flush immédiat pour PowerShell
sys.stdout.reconfigure(line_buffering=True) if hasattr(sys.stdout, 'reconfigure') else None

# Changer vers le répertoire du projet (parent du dossier scripts)
script_dir = os.path.dirname(os.path.abspath(__file__))
project_dir = os.path.dirname(script_dir)
os.chdir(project_dir)

# Ajouter le répertoire parent au path
sys.path.insert(0, project_dir)

print("🔍 [DEBUG] Démarrage du script...", flush=True)
print(f"🔍 [DEBUG] Répertoire de travail: {os.getcwd()}", flush=True)
print(f"🔍 [DEBUG] Python path: {sys.path[0]}", flush=True)

try:
    from core.supabase_storage import SupabaseStorage
    print("✅ [DEBUG] Import SupabaseStorage réussi", flush=True)
except Exception as e:
    print(f"❌ [DEBUG] Erreur import SupabaseStorage: {e}", flush=True)
    raise


class GazelleProductDisplayImporter:
    """Importe les classifications de produits depuis Gazelle inv.ProductDisplay."""

    def __init__(self):
        """Initialise l'importateur."""
        print("🔍 [DEBUG] Initialisation de GazelleProductDisplayImporter...", flush=True)
        try:
            print("🔍 [DEBUG] Création de SupabaseStorage...", flush=True)
            self.storage = SupabaseStorage()
            print("✅ [DEBUG] SupabaseStorage créé avec succès", flush=True)
        except Exception as e:
            print(f"❌ [DEBUG] Erreur création SupabaseStorage: {e}", flush=True)
            raise
        self.stats = {
            "total_processed": 0,
            "updated": 0,
            "created": 0,
            "errors": 0,
            "skipped": 0
        }
        print("✅ [DEBUG] Importer initialisé", flush=True)

    def fetch_from_gazelle(self) -> List[Dict[str, Any]]:
        """
        Récupère les données depuis Gazelle inv.ProductDisplay.

        ⚠️  RÈGLE IMPORTANTE: LECTURE SEULE!
        - Cette fonction lit UNIQUEMENT depuis V4 (SQL Server Gazelle)
        - Ne JAMAIS modifier, supprimer ou altérer les données V4
        - Utiliser uniquement des requêtes SELECT (lecture seule)

        NOTE: Cette fonction doit être implémentée selon votre configuration Gazelle.
        Vous devez avoir accès à la base de données SQL Server de Gazelle.

        Returns:
            Liste des produits avec leurs classifications
        """
        # TODO: Implémenter la connexion à Gazelle SQL Server
        # 
        # ⚠️  IMPORTANT: Utiliser les VRAIES colonnes V4!
        # 
        # Colonnes CORRECTES dans V4:
        # - inv.Products.Sku (pas "Code")
        # - inv.Products.Active (pas "IsDeleted")
        # - inv.ProductDisplay.Category (existe)
        # - inv.ProductDisplay.VariantGroup (existe)
        # - inv.ProductDisplay.VariantLabel (existe)
        # - inv.ProductDisplay.DisplayOrder (existe)
        # - inv.ProductDisplay.IsActive (existe)
        #
        # Colonnes qui N'EXISTENT PAS dans V4:
        # - ❌ HasCommission (n'existe pas - initialiser à FALSE dans V5)
        # - ❌ CommissionRate (n'existe pas - initialiser à 0.00 dans V5)
        #
        # Exemple de requête SQL CORRECTE:
        """
        SELECT
            p.ProductId,
            p.Sku AS code_produit,  -- Pas "Code"!
            p.Name AS nom,
            pd.Category AS categorie,
            p.Description AS description,
            p.Unit AS unite_mesure,
            p.UnitPrice AS prix_unitaire,
            p.Supplier AS fournisseur,
            pd.VariantGroup AS variant_group,
            pd.VariantLabel AS variant_label,
            pd.DisplayOrder AS display_order,
            pd.IsActive AS is_active
            -- Ne PAS essayer de lire HasCommission/CommissionRate (n'existent pas)
        FROM inv.Products p
        LEFT JOIN inv.ProductDisplay pd ON p.ProductId = pd.ProductId
        WHERE p.Active = 1  -- Pas "IsDeleted = 0"!
        ORDER BY pd.DisplayOrder, p.Sku
        """

        # Détecter si on est sur Windows (PC) pour utiliser SQL Server
        if sys.platform == "win32":
            try:
                import pyodbc
                print("🔌 Connexion à SQL Server Gazelle (source)...", flush=True)
                
                # Configuration SQL Server depuis variables d'environnement
                db_conn_str = os.environ.get('DB_CONN_STR') or os.environ.get('SQL_SERVER_CONN_STR')
                
                if not db_conn_str:
                    # Essayer une configuration par défaut
                    server = os.environ.get('SQL_SERVER', 'PIANOTEK\\SQLEXPRESS')
                    database = os.environ.get('SQL_DATABASE', 'PianoTek')
                    db_conn_str = f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={server};DATABASE={database};Trusted_Connection=yes;"
                
                conn = pyodbc.connect(db_conn_str)
                cursor = conn.cursor()
                
                # Requête SQL pour récupérer les produits avec ProductDisplay
                # Utilise les VRAIES colonnes qui existent dans SQL Server
                query = """
                SELECT
                    p.ProductId,
                    p.Sku AS code_produit,
                    p.Name AS nom,
                    COALESCE(pd.Category, 'Produit') AS categorie,
                    NULL AS description,
                    'unité' AS unite_mesure,
                    COALESCE(p.UnitCost, 0) AS prix_unitaire,
                    NULL AS fournisseur,
                    pd.VariantGroup AS variant_group,
                    pd.VariantLabel AS variant_label,
                    COALESCE(pd.DisplayOrder, 0) AS display_order,
                    COALESCE(pd.Active, p.Active, 1) AS is_active
                FROM inv.Products p
                LEFT JOIN inv.ProductDisplay pd ON p.ProductId = pd.ProductId
                WHERE p.Active = 1
                ORDER BY pd.DisplayOrder, p.Sku
                """
                
                cursor.execute(query)
                rows = cursor.fetchall()
                
                # Convertir les rows en dictionnaires
                columns = [column[0] for column in cursor.description]
                produits = []
                for row in rows:
                    produit_dict = dict(zip(columns, row))
                    # Nettoyer les valeurs NULL et s'assurer que code_produit existe
                    for key, value in produit_dict.items():
                        if value is None:
                            produit_dict[key] = None
                        elif isinstance(value, str):
                            produit_dict[key] = value.strip() if value else None
                    
                    # Si code_produit est NULL ou vide, utiliser ProductId comme fallback
                    if not produit_dict.get("code_produit"):
                        product_id = produit_dict.get("ProductId")
                        if product_id:
                            produit_dict["code_produit"] = f"PROD-{product_id}"
                    
                    produits.append(produit_dict)
                
                conn.close()
                
                print(f"✅ {len(produits)} produits récupérés depuis Gazelle SQL Server", flush=True)
                print("   Note: has_commission et commission_rate initialisés à FALSE/0.00 (configurés dans V5)", flush=True)
                
                return produits
                
            except ImportError:
                print("⚠️  pyodbc non installé. Installez avec: pip install pyodbc", flush=True)
                return []
            except Exception as e:
                print(f"❌ Erreur de connexion SQL Server: {e}", flush=True)
                return []
        else:
            # Sur Mac, pas d'implémentation SQL Server
            print("⚠️  TODO: Implémenter fetch_from_gazelle()", flush=True)
            print("   Voir la documentation dans le fichier pour la requête SQL", flush=True)
            print("⚠️  [DEBUG] Retour d'une liste vide - aucun produit à importer", flush=True)
            return []

    def map_gazelle_to_supabase(self, gazelle_product: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convertit un produit Gazelle en format Supabase.

        Args:
            gazelle_product: Produit depuis Gazelle

        Returns:
            Produit au format Supabase
        """
        # Récupérer code_produit - peut être dans différentes clés
        code_produit = gazelle_product.get("code_produit") or gazelle_product.get("Sku") or gazelle_product.get("SKU")
        
        # Si toujours pas de code, utiliser ProductId comme fallback
        if not code_produit:
            product_id = gazelle_product.get("ProductId")
            if product_id:
                code_produit = f"PROD-{product_id}"
        
        return {
            "code_produit": code_produit,
            "nom": gazelle_product.get("nom") or gazelle_product.get("Name") or "Produit sans nom",
            "categorie": gazelle_product.get("categorie") or gazelle_product.get("Category") or "Produit",
            "description": gazelle_product.get("description"),
            "unite_mesure": gazelle_product.get("unite_mesure") or "unité",
            "prix_unitaire": float(gazelle_product.get("prix_unitaire") or gazelle_product.get("UnitCost") or 0),
            "fournisseur": gazelle_product.get("fournisseur"),
            # Nouvelles colonnes de classification
            "has_commission": bool(gazelle_product.get("has_commission", False)),
            "commission_rate": float(gazelle_product.get("commission_rate", 0)),
            "variant_group": gazelle_product.get("variant_group"),
            "variant_label": gazelle_product.get("variant_label"),
            "display_order": int(gazelle_product.get("display_order", 0)),
            "is_active": bool(gazelle_product.get("is_active", True)),
            "gazelle_product_id": gazelle_product.get("ProductId"),
            "last_sync_at": datetime.now().isoformat()
        }

    def import_product(self, product_data: Dict[str, Any]) -> bool:
        """
        Importe un produit dans Supabase.

        Args:
            product_data: Données du produit

        Returns:
            True si succès
        """
        try:
            code_produit = product_data.get("code_produit")
            if not code_produit:
                print(f"  ⚠️  Produit sans code, ignoré", flush=True)
                self.stats["skipped"] += 1
                return False

            # Vérifier si le produit existe déjà
            existing = self.storage.get_data(
                "produits_catalogue",
                filters={"code_produit": code_produit}
            )

            success = self.storage.update_data(
                "produits_catalogue",
                product_data,
                id_field="code_produit",
                upsert=True
            )

            if success:
                if existing:
                    print(f"  ✅ {code_produit}: Mis à jour", flush=True)
                    self.stats["updated"] += 1
                else:
                    print(f"  ✅ {code_produit}: Créé", flush=True)
                    self.stats["created"] += 1
                return True
            else:
                print(f"  ❌ {code_produit}: Échec", flush=True)
                self.stats["errors"] += 1
                return False

        except Exception as e:
            print(f"  ❌ Erreur: {e}", flush=True)
            self.stats["errors"] += 1
            return False

    def run(self, dry_run: bool = False) -> Dict[str, int]:
        """
        Exécute l'importation complète.

        Args:
            dry_run: Si True, simule l'import sans modifier la DB

        Returns:
            Statistiques d'importation
        """
        print("🔄 Importation des classifications de produits depuis Gazelle...", flush=True)
        print("", flush=True)

        if dry_run:
            print("⚠️  MODE DRY-RUN: Aucune modification ne sera effectuée", flush=True)
            print("", flush=True)

        # Récupérer les produits depuis Gazelle
        print("📥 Récupération depuis Gazelle inv.ProductDisplay...", flush=True)
        gazelle_products = self.fetch_from_gazelle()

        if not gazelle_products:
            print("⚠️  Aucun produit récupéré depuis Gazelle", flush=True)
            return self.stats

        print(f"   {len(gazelle_products)} produits récupérés", flush=True)
        print("", flush=True)

        # Importer chaque produit
        print("📦 Importation des produits...", flush=True)
        for gazelle_product in gazelle_products:
            self.stats["total_processed"] += 1

            # Convertir au format Supabase
            product_data = self.map_gazelle_to_supabase(gazelle_product)

            if not dry_run:
                self.import_product(product_data)
            else:
                print(f"  🔍 [DRY-RUN] {product_data.get('code_produit')}: {product_data.get('nom')}", flush=True)

        # Afficher les statistiques
        print("", flush=True)
        print("📊 Statistiques d'importation:", flush=True)
        print(f"   Total traité: {self.stats['total_processed']}", flush=True)
        print(f"   ✅ Créés: {self.stats['created']}", flush=True)
        print(f"   ✅ Mis à jour: {self.stats['updated']}", flush=True)
        print(f"   ⚠️  Ignorés: {self.stats['skipped']}", flush=True)
        print(f"   ❌ Erreurs: {self.stats['errors']}", flush=True)

        return self.stats


def main():
    """Point d'entrée principal."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Importe les classifications de produits depuis Gazelle"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simule l'import sans modifier la base de données"
    )

    args = parser.parse_args()

    print("🔍 [DEBUG] Arguments parsés", flush=True)
    print(f"🔍 [DEBUG] Dry-run: {args.dry_run}", flush=True)

    try:
        print("🔍 [DEBUG] Création de l'importer...", flush=True)
        importer = GazelleProductDisplayImporter()
        print("🔍 [DEBUG] Lancement de l'import...", flush=True)
        stats = importer.run(dry_run=args.dry_run)
        print("🔍 [DEBUG] Import terminé", flush=True)

        # Code de sortie basé sur les erreurs
        if stats["errors"] > 0:
            sys.exit(1)
        else:
            sys.exit(0)

    except Exception as e:
        print(f"\n❌ Erreur fatale: {e}", flush=True)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
