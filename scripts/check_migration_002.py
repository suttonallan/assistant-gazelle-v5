#!/usr/bin/env python3
"""
Script pour vérifier si la migration 002 a été exécutée.

Ce script vérifie si les colonnes de classification existent dans produits_catalogue
en utilisant l'API REST de Supabase (plus simple que la connexion PostgreSQL directe).
"""

import os
import sys
from pathlib import Path

# Ajouter le répertoire parent au path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.supabase_storage import SupabaseStorage


def check_columns_via_api():
    """
    Vérifie si les colonnes existent en essayant de récupérer un produit
    et en vérifiant la présence des nouvelles colonnes.
    """
    try:
        storage = SupabaseStorage()
        
        # Récupérer un produit (ou tous les produits)
        produits = storage.get_data("produits_catalogue", limit=1)
        
        if not produits:
            print("⚠️  Aucun produit trouvé dans produits_catalogue")
            print("   La table existe mais est vide.")
            print("\n   Colonnes à vérifier manuellement dans Supabase Dashboard:")
            print("   - has_commission")
            print("   - commission_rate")
            print("   - display_order")
            print("   - variant_group")
            print("   - variant_label")
            print("   - is_active")
            print("   - gazelle_product_id")
            print("   - last_sync_at")
            return False
        
        # Vérifier les colonnes dans le premier produit
        produit = produits[0]
        required_columns = {
            'has_commission': 'BOOLEAN',
            'commission_rate': 'DECIMAL',
            'display_order': 'INTEGER',
            'variant_group': 'TEXT',
            'variant_label': 'TEXT',
            'is_active': 'BOOLEAN',
            'gazelle_product_id': 'INTEGER',
            'last_sync_at': 'TIMESTAMPTZ'
        }
        
        print("=" * 60)
        print("Vérification des colonnes de classification")
        print("=" * 60)
        print(f"\n📦 Produit de test: {produit.get('code_produit', 'N/A')}")
        print("\n🔍 Vérification des colonnes:\n")
        
        existing = []
        missing = []
        
        for col, col_type in required_columns.items():
            if col in produit:
                existing.append(col)
                value = produit[col]
                print(f"  ✅ {col:25} ({col_type:12}) = {value}")
            else:
                missing.append(col)
                print(f"  ❌ {col:25} ({col_type:12}) = MANQUANTE")
        
        print("\n" + "=" * 60)
        
        if missing:
            print(f"\n❌ {len(missing)} colonne(s) manquante(s):")
            for col in missing:
                print(f"   - {col}")
            print("\n📝 Action requise:")
            print("   1. Allez dans Supabase Dashboard → SQL Editor")
            print("   2. Copiez le contenu de:")
            print("      modules/inventaire/migrations/002_add_product_classifications.sql")
            print("   3. Exécutez le script SQL")
            print("   4. Relancez ce script pour vérifier")
            return False
        else:
            print(f"\n✅ Toutes les colonnes existent! ({len(existing)} colonnes)")
            print("\n   La migration 002 a été exécutée avec succès.")
            return True
        
    except ValueError as e:
        print(f"❌ Erreur de configuration: {e}")
        print("\n   Vérifiez que SUPABASE_URL et SUPABASE_KEY sont définis dans .env")
        return False
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Fonction principale."""
    success = check_columns_via_api()
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
