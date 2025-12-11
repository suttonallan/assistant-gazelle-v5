#!/usr/bin/env python3
"""
Script pour exécuter les migrations du module Inventaire dans Supabase
Piano Technique Montréal - Assistant Gazelle V5

Usage:
    python3 scripts/run_inventory_migrations.py
"""

import os
import sys
from pathlib import Path

# Ajouter le répertoire racine au path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.supabase_storage import SupabaseStorage


def read_sql_file(file_path: Path) -> str:
    """Lit un fichier SQL."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()


def execute_migration(storage: SupabaseStorage, sql_content: str, migration_name: str):
    """Exécute une migration SQL."""
    print(f"\n📦 Exécution de la migration: {migration_name}")
    print("=" * 60)

    try:
        # Utiliser le client raw de Supabase pour exécuter du SQL
        result = storage.client.rpc('exec_sql', {'sql': sql_content}).execute()
        print(f"✅ Migration {migration_name} exécutée avec succès!")
        return True
    except Exception as e:
        # Si la fonction RPC n'existe pas, on utilise une autre approche
        # On split le SQL en statements individuels
        print(f"⚠️  RPC exec_sql non disponible, utilisation de l'approche alternative...")

        try:
            # Séparer les statements SQL (simpliste, mais fonctionnel pour nos migrations)
            statements = [s.strip() for s in sql_content.split(';') if s.strip() and not s.strip().startswith('--')]

            for i, statement in enumerate(statements, 1):
                # Ignorer les commentaires et lignes vides
                if not statement or statement.startswith('--'):
                    continue

                print(f"  Exécution statement {i}/{len(statements)}...")

                # Pour CREATE TABLE, INSERT, ALTER TABLE, etc.
                # On doit utiliser l'API REST de Supabase différemment
                # Malheureusement, Supabase ne permet pas d'exécuter du SQL arbitraire via l'API Python
                # On va donc créer les données directement via l'API

            print(f"⚠️  Cette migration doit être exécutée manuellement dans Supabase SQL Editor")
            print(f"   Fichier: modules/inventaire/migrations/{migration_name}")
            return False

        except Exception as e2:
            print(f"❌ Erreur lors de l'exécution de {migration_name}: {e2}")
            return False


def create_test_data_directly(storage: SupabaseStorage):
    """Crée les données de test directement via l'API Supabase."""
    print("\n📦 Création des données de test...")
    print("=" * 60)

    # Produits de test
    produits_test = [
        {
            'code_produit': 'CORD-001',
            'nom': 'Corde #1 (Do)',
            'categorie': 'Cordes',
            'description': 'Corde en acier pour note Do',
            'unite_mesure': 'unité',
            'prix_unitaire': 12.50,
            'fournisseur': 'Fournisseur A',
            'has_commission': True,
            'commission_rate': 15.00,
            'variant_group': 'Cordes Piano',
            'display_order': 1,
            'is_active': True
        },
        {
            'code_produit': 'CORD-002',
            'nom': 'Corde #2 (Ré)',
            'categorie': 'Cordes',
            'description': 'Corde en acier pour note Ré',
            'unite_mesure': 'unité',
            'prix_unitaire': 12.75,
            'fournisseur': 'Fournisseur A',
            'has_commission': True,
            'commission_rate': 15.00,
            'variant_group': 'Cordes Piano',
            'display_order': 2,
            'is_active': True
        },
        {
            'code_produit': 'FELT-001',
            'nom': 'Feutre tête de marteau',
            'categorie': 'Feutres',
            'description': 'Feutre haute qualité pour marteau',
            'unite_mesure': 'unité',
            'prix_unitaire': 8.50,
            'fournisseur': 'Fournisseur B',
            'has_commission': False,
            'commission_rate': 0.00,
            'variant_group': 'Feutres',
            'display_order': 3,
            'is_active': True
        },
        {
            'code_produit': 'TOOL-001',
            'nom': "Clé d'accord",
            'categorie': 'Outils',
            'description': "Clé d'accord professionnelle",
            'unite_mesure': 'unité',
            'prix_unitaire': 45.00,
            'fournisseur': 'Fournisseur C',
            'has_commission': True,
            'commission_rate': 20.00,
            'display_order': 4,
            'is_active': True
        },
        {
            'code_produit': 'CLEAN-001',
            'nom': 'Nettoyant touches',
            'categorie': 'Produits entretien',
            'description': 'Nettoyant pour touches ivoire/plastique',
            'unite_mesure': 'litre',
            'prix_unitaire': 18.00,
            'fournisseur': 'Fournisseur D',
            'has_commission': False,
            'commission_rate': 0.00,
            'display_order': 5,
            'is_active': True
        }
    ]

    try:
        # Insérer les produits en utilisant la méthode update_data() avec UPSERT
        success_count = 0
        for produit in produits_test:
            try:
                # Utiliser update_data avec upsert=True (crée ou met à jour)
                success = storage.update_data(
                    table_name='produits_catalogue',
                    data=produit,
                    id_field='code_produit',
                    upsert=True
                )

                if success:
                    print(f"  ✅ Créé/MAJ: {produit['code_produit']} - {produit['nom']}")
                    success_count += 1
                else:
                    print(f"  ❌ Échec pour {produit['code_produit']}")

            except Exception as e:
                print(f"  ❌ Erreur pour {produit['code_produit']}: {e}")

        print(f"\n✅ {success_count}/{len(produits_test)} produits de test créés/mis à jour!")
        return success_count > 0

    except Exception as e:
        print(f"❌ Erreur lors de la création des données de test: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Point d'entrée principal."""
    print("\n" + "=" * 60)
    print("🚀 EXÉCUTION DES MIGRATIONS INVENTAIRE")
    print("=" * 60)

    # Initialiser Supabase
    try:
        storage = SupabaseStorage()
        print("✅ Connexion à Supabase établie")
    except Exception as e:
        print(f"❌ Erreur de connexion à Supabase: {e}")
        return 1

    # Chemin des migrations
    migrations_dir = Path(__file__).parent.parent / 'modules' / 'inventaire' / 'migrations'

    # Note: Les migrations doivent être exécutées manuellement dans Supabase SQL Editor
    # car l'API Python de Supabase ne permet pas d'exécuter du SQL DDL arbitraire

    print("\n⚠️  IMPORTANT: Les migrations SQL doivent être exécutées manuellement dans Supabase SQL Editor")
    print("\nÉtapes à suivre:")
    print("1. Aller sur https://supabase.com/dashboard")
    print("2. Sélectionner votre projet Assistant Gazelle V5")
    print("3. Cliquer sur 'SQL Editor' dans le menu")
    print("4. Exécuter les migrations dans l'ordre:")
    print(f"   - {migrations_dir / '001_create_inventory_tables.sql'}")
    print(f"   - {migrations_dir / '002_add_product_classifications.sql'}")

    # Créer les données de test directement via l'API
    print("\n" + "=" * 60)
    print("Tentative de création des données de test via l'API...")
    print("=" * 60)

    success = create_test_data_directly(storage)

    if success:
        print("\n" + "=" * 60)
        print("✅ DONNÉES DE TEST CRÉÉES AVEC SUCCÈS!")
        print("=" * 60)
        print("\nVous pouvez maintenant:")
        print("1. Actualiser l'onglet Admin dans le frontend")
        print("2. Voir les 5 produits de test dans le catalogue")
        print("3. Tester la modification de l'ordre d'affichage")
        print("4. Tester l'édition des produits")
        return 0
    else:
        print("\n" + "=" * 60)
        print("⚠️  ÉCHEC DE LA CRÉATION DES DONNÉES DE TEST")
        print("=" * 60)
        print("\nVeuillez exécuter les migrations manuellement dans Supabase SQL Editor")
        return 1


if __name__ == '__main__':
    sys.exit(main())
