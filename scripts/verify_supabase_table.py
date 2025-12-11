#!/usr/bin/env python3
"""
Script pour vérifier si la table produits_catalogue existe dans Supabase.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.supabase_storage import SupabaseStorage


def verify_table_exists():
    """Vérifie si la table produits_catalogue existe."""
    print("=" * 60)
    print("Vérification de la Table produits_catalogue")
    print("=" * 60)
    
    try:
        storage = SupabaseStorage()
        
        # Essayer de récupérer des données
        print("\n1️⃣  Tentative de lecture depuis produits_catalogue...")
        produits = storage.get_data("produits_catalogue", limit=1)
        
        if produits is not None:
            print("   ✅ Table produits_catalogue existe!")
            
            # Vérifier les colonnes
            print("\n2️⃣  Vérification des colonnes...")
            if produits:
                produit = produits[0]
                print(f"   Colonnes trouvées: {', '.join(produit.keys())[:100]}...")
                
                # Vérifier les colonnes essentielles
                required = ['code_produit', 'nom', 'categorie']
                missing = [col for col in required if col not in produit]
                
                if missing:
                    print(f"   ⚠️  Colonnes manquantes: {', '.join(missing)}")
                else:
                    print("   ✅ Colonnes essentielles présentes")
                
                # Vérifier les colonnes de classification
                classification_cols = ['has_commission', 'commission_rate', 'display_order']
                has_classification = any(col in produit for col in classification_cols)
                
                if has_classification:
                    print("   ✅ Colonnes de classification présentes (migration 002 exécutée)")
                else:
                    print("   ⚠️  Colonnes de classification manquantes (migration 002 non exécutée)")
            else:
                print("   ℹ️  Table existe mais est vide")
            
            return True
        else:
            print("   ❌ Table produits_catalogue n'existe pas ou erreur d'accès")
            return False
            
    except Exception as e:
        error_msg = str(e)
        print(f"   ❌ Erreur: {error_msg}")
        
        # Analyser l'erreur
        if "does not exist" in error_msg or "relation" in error_msg.lower():
            print("\n   🔍 Diagnostic:")
            print("      → La table produits_catalogue n'existe pas")
            print("      → Action: Exécuter la migration 001")
        elif "column" in error_msg.lower():
            print("\n   🔍 Diagnostic:")
            print("      → La table existe mais une colonne manque")
            print("      → Action: Exécuter la migration 002")
        else:
            print("\n   🔍 Diagnostic:")
            print("      → Erreur de connexion ou configuration")
            print("      → Vérifier SUPABASE_URL et SUPABASE_KEY")
        
        return False


def main():
    """Fonction principale."""
    exists = verify_table_exists()
    
    if not exists:
        print("\n" + "=" * 60)
        print("📋 Actions Requises")
        print("=" * 60)
        print("\n1. Ouvrir Supabase Dashboard:")
        print("   https://app.supabase.com/project/beblgzvmjqkcillmcavk")
        print("\n2. Aller dans SQL Editor")
        print("\n3. Exécuter la migration 001:")
        print("   Fichier: modules/inventaire/migrations/001_create_inventory_tables.sql")
        print("\n4. Exécuter la migration 002:")
        print("   Fichier: modules/inventaire/migrations/002_add_product_classifications.sql")
        print("\n5. Relancer ce script pour vérifier")
    
    return 0 if exists else 1


if __name__ == "__main__":
    sys.exit(main())
