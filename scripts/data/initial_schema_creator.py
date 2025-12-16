#!/usr/bin/env python3
"""
Script d'initialisation des schémas BDD centraux pour Assistant Gazelle V5.
Vérifie les tables existantes et guide l'utilisateur pour créer les schémas manquants.

Usage:
    python scripts/data/initial_schema_creator.py --check    # Vérifier les tables existantes
    python scripts/data/initial_schema_creator.py --create   # Créer les tables (via SQL Editor)
"""

import os
import sys
import argparse
import requests
from pathlib import Path
from typing import List, Dict, Any

# Ajouter le répertoire parent au PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dotenv import load_dotenv
load_dotenv()


class SchemaChecker:
    """Vérifie et guide la création des schémas BDD centraux."""

    # Tables attendues pour la V5
    EXPECTED_TABLES = [
        'clients',
        'pianos',
        'appointments',
        'invoices',
        'invoice_items',
        'produits_catalogue',
        'inventaire_techniciens',
        'transactions_inventaire'
    ]

    # Colonnes critiques par table
    CRITICAL_COLUMNS = {
        'clients': ['id', 'gazelle_id', 'nom', 'email', 'statut'],
        'pianos': ['id', 'gazelle_id', 'client_id', 'numero_serie', 'marque'],
        'appointments': ['id', 'gazelle_id', 'client_id', 'date_debut', 'statut', 'technicien_nom'],
        'invoices': ['id', 'gazelle_id', 'numero_facture', 'client_id', 'montant_ttc', 'statut'],
        'invoice_items': ['id', 'invoice_id', 'description', 'quantite', 'prix_unitaire'],
        'produits_catalogue': ['code_produit', 'nom', 'categorie', 'prix_unitaire', 'is_active'],
        'inventaire_techniciens': ['id', 'code_produit', 'technicien', 'quantite_stock'],
        'transactions_inventaire': ['id', 'code_produit', 'technicien', 'type_transaction', 'quantite']
    }

    def __init__(self):
        """Initialise la connexion Supabase."""
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_KEY')

        if not self.supabase_url or not self.supabase_key:
            print("❌ Variables SUPABASE_URL et SUPABASE_KEY requises dans .env")
            sys.exit(1)

        self.api_url = f"{self.supabase_url}/rest/v1"
        self.headers = {
            "apikey": self.supabase_key,
            "Authorization": f"Bearer {self.supabase_key}",
            "Content-Type": "application/json"
        }

    def table_exists(self, table_name: str) -> bool:
        """Vérifie si une table existe en tentant un GET."""
        try:
            url = f"{self.api_url}/{table_name}?limit=0"
            response = requests.get(url, headers=self.headers, timeout=5)
            return response.status_code == 200
        except Exception as e:
            print(f"⚠️  Erreur vérification table {table_name}: {e}")
            return False

    def get_table_columns(self, table_name: str) -> List[str]:
        """Récupère les colonnes d'une table."""
        try:
            url = f"{self.api_url}/{table_name}?limit=1"
            response = requests.get(url, headers=self.headers, timeout=5)

            if response.status_code == 200:
                data = response.json()
                if data:
                    return list(data[0].keys())
                else:
                    # Table vide, essayer avec un HEAD pour récupérer les headers
                    return []
            else:
                return []
        except Exception as e:
            print(f"⚠️  Erreur récupération colonnes {table_name}: {e}")
            return []

    def check_all_tables(self) -> Dict[str, Any]:
        """Vérifie toutes les tables attendues."""
        print("\n" + "=" * 70)
        print("🔍 VÉRIFICATION DES SCHÉMAS BDD CENTRAUX")
        print("=" * 70 + "\n")

        results = {
            'existing': [],
            'missing': [],
            'incomplete': []
        }

        for table in self.EXPECTED_TABLES:
            print(f"📋 Table: {table}...", end=" ")

            if self.table_exists(table):
                print("✅ Existe")
                results['existing'].append(table)

                # Vérifier les colonnes critiques
                if table in self.CRITICAL_COLUMNS:
                    columns = self.get_table_columns(table)
                    if columns:
                        expected = self.CRITICAL_COLUMNS[table]
                        missing_cols = [col for col in expected if col not in columns]

                        if missing_cols:
                            print(f"   ⚠️  Colonnes manquantes: {', '.join(missing_cols)}")
                            results['incomplete'].append({
                                'table': table,
                                'missing_columns': missing_cols
                            })
                        else:
                            print(f"   ✅ Toutes les colonnes critiques présentes")
            else:
                print("❌ Manquante")
                results['missing'].append(table)

        return results

    def print_summary(self, results: Dict[str, Any]):
        """Affiche le résumé de la vérification."""
        print("\n" + "=" * 70)
        print("📊 RÉSUMÉ")
        print("=" * 70)

        print(f"\n✅ Tables existantes: {len(results['existing'])}/{len(self.EXPECTED_TABLES)}")
        if results['existing']:
            for table in results['existing']:
                print(f"   - {table}")

        if results['missing']:
            print(f"\n❌ Tables manquantes: {len(results['missing'])}")
            for table in results['missing']:
                print(f"   - {table}")

        if results['incomplete']:
            print(f"\n⚠️  Tables incomplètes: {len(results['incomplete'])}")
            for item in results['incomplete']:
                print(f"   - {item['table']}: {', '.join(item['missing_columns'])}")

        # Recommandations
        print("\n" + "=" * 70)
        print("📌 PROCHAINES ÉTAPES")
        print("=" * 70 + "\n")

        if results['missing'] or results['incomplete']:
            print("1️⃣  Ouvrir Supabase Dashboard:")
            print(f"   {self.supabase_url.replace('supabase.co', 'supabase.com')}\n")

            print("2️⃣  Aller dans SQL Editor\n")

            if results['missing'] and any(t in ['clients', 'pianos', 'appointments', 'invoices', 'invoice_items'] for t in results['missing']):
                print("3️⃣  Exécuter le script de migration:")
                print("   scripts/migrations/003_create_central_schemas.sql\n")

            if results['incomplete']:
                for item in results['incomplete']:
                    if item['table'] == 'produits_catalogue':
                        print("4️⃣  Exécuter le script de migration:")
                        print("   scripts/migrations/002_add_v4_columns_to_produits.sql\n")
        else:
            print("✅ Tous les schémas sont prêts!")
            print("Vous pouvez maintenant migrer les autres modules (Briefings, Alertes).\n")

    def create_guide(self):
        """Affiche le guide de création des schémas."""
        print("\n" + "=" * 70)
        print("📚 GUIDE DE CRÉATION DES SCHÉMAS CENTRAUX")
        print("=" * 70 + "\n")

        migration_file = Path("scripts/migrations/003_create_central_schemas.sql")

        if migration_file.exists():
            with open(migration_file, 'r', encoding='utf-8') as f:
                sql_content = f.read()

            print(f"📄 Fichier: {migration_file}")
            print(f"📝 Taille: {len(sql_content)} caractères\n")
            print("🎯 Contenu du script:")
            print("-" * 70)
            # Afficher les 50 premières lignes
            lines = sql_content.split('\n')
            for i, line in enumerate(lines[:50], 1):
                print(f"{i:3}│ {line}")
            if len(lines) > 50:
                print(f"... ({len(lines) - 50} lignes supplémentaires)")
            print("-" * 70)

            print("\n📌 Pour exécuter:")
            print(f"1. Ouvrir: {self.supabase_url.replace('supabase.co', 'supabase.com')}")
            print("2. SQL Editor → New Query")
            print("3. Copier-coller le contenu complet")
            print("4. Cliquer 'Run'\n")
        else:
            print(f"❌ Fichier de migration introuvable: {migration_file}")


def main():
    """Point d'entrée du script."""
    parser = argparse.ArgumentParser(
        description="Vérification et création des schémas BDD centraux V5"
    )
    parser.add_argument(
        '--check',
        action='store_true',
        help='Vérifier les tables existantes'
    )
    parser.add_argument(
        '--create',
        action='store_true',
        help='Afficher le guide de création'
    )

    args = parser.parse_args()

    if not args.check and not args.create:
        parser.print_help()
        sys.exit(0)

    checker = SchemaChecker()

    if args.check:
        results = checker.check_all_tables()
        checker.print_summary(results)

    if args.create:
        checker.create_guide()


if __name__ == "__main__":
    main()
