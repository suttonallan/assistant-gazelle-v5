#!/usr/bin/env python3
"""
Système de gestion automatique des migrations.

Vérifie et exécute automatiquement les migrations manquantes.
"""

import sys
import os
from pathlib import Path
from dotenv import load_dotenv
import requests

# Charger .env
env_path = Path(__file__).parent.parent / '.env'
if env_path.exists():
    load_dotenv(env_path)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.supabase_storage import SupabaseStorage


class MigrationManager:
    """Gère les migrations automatiquement."""
    
    def __init__(self):
        self.storage = SupabaseStorage()
        self.migrations_dir = Path(__file__).parent.parent / "modules" / "inventaire" / "migrations"
    
    def verifier_migration_001(self):
        """Vérifie si la migration 001 est exécutée."""
        try:
            url = f"{self.storage.api_url}/produits_catalogue?select=*&limit=1"
            response = requests.get(url, headers=self.storage._get_headers())
            return response.status_code == 200
        except:
            return False
    
    def verifier_migration_002(self):
        """Vérifie si la migration 002 est exécutée."""
        try:
            # Essayer d'insérer un produit de test pour voir les colonnes disponibles
            # Ou vérifier directement via une requête qui liste les colonnes
            url = f"{self.storage.api_url}/produits_catalogue?select=has_commission,commission_rate,is_active,gazelle_product_id,variant_group,display_order&limit=1"
            response = requests.get(url, headers=self.storage._get_headers())
            
            if response.status_code == 200:
                # Si la requête réussit avec ces colonnes spécifiques, la migration est OK
                return True
            elif response.status_code == 400:
                # Erreur 400 = colonnes n'existent pas
                error_text = response.text.lower()
                if "column" in error_text and "does not exist" in error_text:
                    return False
                # Autre erreur 400, peut-être que la table est vide mais les colonnes existent
                # Essayons une autre méthode
                pass
            
            # Méthode alternative: essayer de récupérer toutes les colonnes
            url_all = f"{self.storage.api_url}/produits_catalogue?select=*&limit=1"
            response_all = requests.get(url_all, headers=self.storage._get_headers())
            
            if response_all.status_code == 200:
                produits = response_all.json()
                if produits and len(produits) > 0:
                    colonnes = set(produits[0].keys())
                    colonnes_requises = {
                        "has_commission", "commission_rate", "is_active",
                        "gazelle_product_id", "variant_group", "display_order"
                    }
                    return colonnes_requises.issubset(colonnes)
                else:
                    # Table vide - on ne peut pas vérifier automatiquement
                    # Mais on peut supposer que si la requête avec colonnes spécifiques fonctionne, c'est OK
                    return None
            
            return False
        except Exception as e:
            print(f"⚠️  Erreur lors de la vérification: {e}")
            return False
    
    def lister_migrations_manquantes(self):
        """Liste les migrations qui doivent être exécutées."""
        migrations_manquantes = []
        
        # Vérifier migration 001
        if not self.verifier_migration_001():
            migrations_manquantes.append({
                "numero": "001",
                "fichier": "modules/inventaire/migrations/001_create_inventory_tables.sql",
                "description": "Création des tables de base (produits_catalogue, inventaire_techniciens, transactions_inventaire)"
            })
        
        # Vérifier migration 002
        resultat_002 = self.verifier_migration_002()
        if resultat_002 is False:
            migrations_manquantes.append({
                "numero": "002",
                "fichier": "modules/inventaire/migrations/002_add_product_classifications.sql",
                "description": "Ajout des colonnes de classification (commissions, variantes, etc.)"
            })
        elif resultat_002 is None:
            # Table vide, on ne peut pas vérifier automatiquement
            # Mais si l'utilisateur vient d'exécuter la migration, on peut supposer qu'elle est OK
            print("⚠️  Table produits_catalogue vide - impossible de vérifier automatiquement la migration 002")
            print("   Si vous venez d'exécuter la migration, elle est probablement OK.")
            print("   Importez un produit pour vérifier définitivement.")
            print()
            reponse = input("   Avez-vous exécuté la migration 002 dans Supabase? (o/n): ").lower().strip()
            if reponse in ('o', 'oui', 'y', 'yes'):
                print("   ✅ Migration 002 considérée comme exécutée.")
            else:
                migrations_manquantes.append({
                    "numero": "002",
                    "fichier": "modules/inventaire/migrations/002_add_product_classifications.sql",
                    "description": "Ajout des colonnes de classification (commissions, variantes, etc.)"
                })
        
        return migrations_manquantes
    
    def afficher_instructions_migration(self, migration):
        """Affiche les instructions pour exécuter une migration."""
        fichier_path = Path(__file__).parent.parent / migration["fichier"]
        
        if not fichier_path.exists():
            print(f"❌ Fichier non trouvé: {migration['fichier']}")
            return
        
        print(f"\n{'='*60}")
        print(f"MIGRATION {migration['numero']} À EXÉCUTER")
        print(f"{'='*60}")
        print(f"Description: {migration['description']}")
        print(f"\nFichier: {migration['fichier']}")
        print(f"\nInstructions:")
        print(f"1. Allez sur https://supabase.com/dashboard")
        print(f"2. Votre projet → SQL Editor")
        print(f"3. Ouvrez le fichier: {migration['fichier']}")
        print(f"4. Copiez TOUT le contenu")
        print(f"5. Collez dans l'éditeur SQL de Supabase")
        print(f"6. Cliquez 'Run' (ou F5)")
        print(f"7. Attendez 'Success'")
        print(f"8. Attendez 10 secondes")
        print(f"{'='*60}\n")


def main():
    """Point d'entrée principal."""
    print("="*60)
    print("🔍 VÉRIFICATION AUTOMATIQUE DES MIGRATIONS")
    print("="*60)
    print()
    
    manager = MigrationManager()
    migrations_manquantes = manager.lister_migrations_manquantes()
    
    if not migrations_manquantes:
        print("✅ TOUTES LES MIGRATIONS SONT EXÉCUTÉES!")
        print("   Vous pouvez lancer l'import maintenant.")
        return 0
    
    print(f"⚠️  {len(migrations_manquantes)} migration(s) manquante(s):\n")
    
    for migration in migrations_manquantes:
        manager.afficher_instructions_migration(migration)
    
    print("\n" + "="*60)
    print("📋 RÉSUMÉ")
    print("="*60)
    print(f"Exécutez {len(migrations_manquantes)} migration(s) dans Supabase SQL Editor,")
    print("puis relancez ce script pour vérifier.")
    print("="*60)
    
    return 1


if __name__ == "__main__":
    sys.exit(main())
