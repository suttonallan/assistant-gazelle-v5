#!/usr/bin/env python3
"""
Script d'importation des classifications de produits depuis Gazelle inv.ProductDisplay.

Synchronise les métadonnées de produits (commissions, variantes, catégories)
depuis SQL Server Gazelle (V4) vers Supabase produits_catalogue (V5).

⚠️  RÈGLE IMPORTANTE: MIGRATION V4 → V5
- LECTURE SEULE depuis V4 (SQL Server Gazelle) - Ne jamais modifier V4
- ÉCRITURE dans V5 (Supabase) - Nouvelle base de données
- V4 continue de fonctionner normalement, on ne le touche pas

📚 RÉFÉRENCE OBLIGATOIRE:
- Consulter docs/REFERENCE_COMPLETE.md pour:
  * Noms de colonnes valides (NE JAMAIS inventer)
  * Mapping V4 → V5
  * Schéma des tables Supabase
  * Colonnes qui existent/n'existent pas dans SQL Server
"""

import sys
import os
from typing import List, Dict, Any, Optional
from datetime import datetime

# Ajouter le répertoire parent au path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.supabase_storage import SupabaseStorage


class GazelleProductDisplayImporter:
    """Importe les classifications de produits depuis Gazelle inv.ProductDisplay."""

    def __init__(self):
        """Initialise l'importateur."""
        self.storage = SupabaseStorage()
        self.stats = {
            "total_processed": 0,
            "updated": 0,
            "created": 0,
            "errors": 0,
            "skipped": 0
        }

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

        print("⚠️  TODO: Implémenter fetch_from_gazelle()")
        print("   Voir la documentation dans le fichier pour la requête SQL")
        return []

    def map_gazelle_to_supabase(self, gazelle_product: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convertit un produit Gazelle en format Supabase.

        Args:
            gazelle_product: Produit depuis Gazelle

        Returns:
            Produit au format Supabase
        """
        return {
            "code_produit": gazelle_product.get("code_produit"),
            "nom": gazelle_product.get("nom"),
            "categorie": gazelle_product.get("categorie", "Produit"),
            "description": gazelle_product.get("description"),
            "unite_mesure": gazelle_product.get("unite_mesure", "unité"),
            "prix_unitaire": float(gazelle_product.get("prix_unitaire", 0)),
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
                print(f"  ⚠️  Produit sans code, ignoré")
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
                    print(f"  ✅ {code_produit}: Mis à jour")
                    self.stats["updated"] += 1
                else:
                    print(f"  ✅ {code_produit}: Créé")
                    self.stats["created"] += 1
                return True
            else:
                print(f"  ❌ {code_produit}: Échec")
                self.stats["errors"] += 1
                return False

        except Exception as e:
            print(f"  ❌ Erreur: {e}")
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
        print("🔄 Importation des classifications de produits depuis Gazelle...")
        print()

        if dry_run:
            print("⚠️  MODE DRY-RUN: Aucune modification ne sera effectuée")
            print()

        # Récupérer les produits depuis Gazelle
        print("📥 Récupération depuis Gazelle inv.ProductDisplay...")
        gazelle_products = self.fetch_from_gazelle()

        if not gazelle_products:
            print("⚠️  Aucun produit récupéré depuis Gazelle")
            return self.stats

        print(f"   {len(gazelle_products)} produits récupérés")
        print()

        # Importer chaque produit
        print("📦 Importation des produits...")
        for gazelle_product in gazelle_products:
            self.stats["total_processed"] += 1

            # Convertir au format Supabase
            product_data = self.map_gazelle_to_supabase(gazelle_product)

            if not dry_run:
                self.import_product(product_data)
            else:
                print(f"  🔍 [DRY-RUN] {product_data.get('code_produit')}: {product_data.get('nom')}")

        # Afficher les statistiques
        print()
        print("📊 Statistiques d'importation:")
        print(f"   Total traité: {self.stats['total_processed']}")
        print(f"   ✅ Créés: {self.stats['created']}")
        print(f"   ✅ Mis à jour: {self.stats['updated']}")
        print(f"   ⚠️  Ignorés: {self.stats['skipped']}")
        print(f"   ❌ Erreurs: {self.stats['errors']}")

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

    try:
        importer = GazelleProductDisplayImporter()
        stats = importer.run(dry_run=args.dry_run)

        # Code de sortie basé sur les erreurs
        if stats["errors"] > 0:
            sys.exit(1)
        else:
            sys.exit(0)

    except Exception as e:
        print(f"\n❌ Erreur fatale: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
