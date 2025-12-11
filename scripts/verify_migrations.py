#!/usr/bin/env python3
"""
Script de vérification rapide pour confirmer que les migrations sont bien exécutées.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.supabase_storage import SupabaseStorage


def verify_migrations():
    """Vérifie que les migrations 001 et 002 sont bien exécutées."""
    print("=" * 60)
    print("Vérification des Migrations")
    print("=" * 60)
    
    try:
        storage = SupabaseStorage()
        
        # Vérifier que la table existe
        print("\n1️⃣  Vérification de la table produits_catalogue...")
        produits = storage.get_data("produits_catalogue", limit=1)
        
        if produits is None:
            print("   ❌ La table produits_catalogue n'existe pas!")
            print("   → Exécutez d'abord la migration 001")
            return False
        
        print("   ✅ Table produits_catalogue existe")
        
        # Vérifier les colonnes de base (migration 001)
        print("\n2️⃣  Vérification des colonnes de base (Migration 001)...")
        base_columns = ['code_produit', 'nom', 'categorie', 'prix_unitaire']
        missing_base = []
        
        if produits:
            produit = produits[0]
            for col in base_columns:
                if col not in produit:
                    missing_base.append(col)
        
        if missing_base:
            print(f"   ❌ Colonnes manquantes: {', '.join(missing_base)}")
            return False
        else:
            print("   ✅ Toutes les colonnes de base existent")
        
        # Vérifier les colonnes de classification (migration 002)
        print("\n3️⃣  Vérification des colonnes de classification (Migration 002)...")
        classification_columns = {
            'has_commission': 'BOOLEAN',
            'commission_rate': 'DECIMAL',
            'display_order': 'INTEGER',
            'variant_group': 'TEXT',
            'variant_label': 'TEXT',
            'is_active': 'BOOLEAN',
            'gazelle_product_id': 'INTEGER',
            'last_sync_at': 'TIMESTAMPTZ'
        }
        
        missing_classification = []
        existing_classification = []
        
        if produits:
            produit = produits[0]
            for col, col_type in classification_columns.items():
                if col in produit:
                    existing_classification.append(col)
                    value = produit[col]
                    print(f"      ✅ {col:25} ({col_type:12}) = {value}")
                else:
                    missing_classification.append(col)
                    print(f"      ❌ {col:25} ({col_type:12}) = MANQUANTE")
        
        if missing_classification:
            print(f"\n   ❌ {len(missing_classification)} colonne(s) manquante(s)")
            print("   → Exécutez la migration 002")
            return False
        else:
            print(f"\n   ✅ Toutes les colonnes de classification existent ({len(existing_classification)} colonnes)")
        
        # Compter les produits
        print("\n4️⃣  Statistiques...")
        all_produits = storage.get_data("produits_catalogue")
        count = len(all_produits) if all_produits else 0
        
        print(f"   📦 Produits dans le catalogue: {count}")
        
        if count == 0:
            print("\n   ⚠️  Le catalogue est vide")
            print("   → Prochaine étape: Importer les données depuis Gazelle")
            print("   → Voir: docs/GUIDE_IMPORT_COMPLET.md")
        else:
            print("\n   ✅ Données présentes dans le catalogue")
        
        # Résumé final
        print("\n" + "=" * 60)
        print("✅ Vérification terminée avec succès!")
        print("=" * 60)
        print("\n✅ Migration 001: OK (tables créées)")
        print("✅ Migration 002: OK (colonnes de classification ajoutées)")
        
        if count > 0:
            print(f"✅ Données: {count} produits dans le catalogue")
        else:
            print("⚠️  Données: Catalogue vide (à importer)")
        
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


if __name__ == "__main__":
    success = verify_migrations()
    sys.exit(0 if success else 1)
