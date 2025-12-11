#!/usr/bin/env python3
"""
Script de nettoyage des fichiers devenus inutiles ou redondants.

Identifie et propose de supprimer les fichiers temporaires, redondants ou obsolètes.
"""

import os
import sys
from pathlib import Path
from typing import List, Tuple

# Fichiers à garder (essentiels)
KEEP_FILES = {
    # Documentation essentielle - Architecture
    'docs/ETAT_DES_LIEUX_BACKEND.md',
    'docs/ENDPOINT_CATALOGUE_ADD.md',
    'docs/INDEX_DOCUMENTATION.md',  # Index de la documentation
    
    # Documentation essentielle - Guides principaux
    'docs/GUIDE_IMPORT_COMPLET.md',  # Guide principal import
    'docs/ORDRE_MIGRATIONS.md',  # Ordre migrations SQL
    'docs/PROCESSUS_MIGRATION_STANDARD.md',  # Processus standardisé
    
    # Documentation essentielle - Règles
    'docs/RÈGLE_IMPORTANTE_V4.md',  # Ne jamais modifier V4
    'docs/README_MIGRATION_V4_V5.md',  # Règles migration
    
    # Documentation essentielle - Dépannage
    'docs/RÉSOUDRE_ERREUR_TABLE_MANQUANTE.md',
    'docs/RÉSOUDRE_ERREUR_ENV.md',
    'docs/RÉSOLUTION_CONFUSION_SCRIPTS.md',
    
    # Documentation essentielle - Utilisateur
    'docs/VOIR_DANS_NAVIGATEUR.md',
    'docs/ADRESSES_IMPORTANTES.md',
    
    # Scripts essentiels
    'scripts/import_gazelle_product_display.py',
    'scripts/test_supabase_connection.py',
    'scripts/check_migration_002.py',
    'scripts/verify_migrations.py',
    'scripts/verify_supabase_table.py',
    'scripts/cleanup_unused_files.py',  # Script de nettoyage
    
    # Migrations SQL
    'modules/inventaire/migrations/001_create_inventory_tables.sql',
    'modules/inventaire/migrations/002_add_product_classifications.sql',
}

# Fichiers à supprimer (redondants/temporaires)
FILES_TO_REMOVE = {
    # Documentation redondante ou temporaire
    'docs/REPONSES_QUESTIONS_CLAUDE.md',  # Temporaire, questions répondues
    'docs/CORRECTION_PLAN_IMPORT.md',  # Remplacé par GUIDE_IMPORT_COMPLET.md
    'docs/VÉRIFICATION_ENV_PARTAGE.md',  # Remplacé par GUIDE_PARTAGE_ENV_PC.md
    'docs/CLARIFICATION_CREDENTIALS.md',  # Info intégrée ailleurs
    'docs/TEST_FINAL_PC.md',  # Info dans GUIDE_IMPORT_COMPLET.md
    'docs/GUIDE_MIGRATION_002.md',  # Info dans ORDRE_MIGRATIONS.md
    'docs/INSTRUCTIONS_CURSOR_PC.md',  # Info dans GUIDE_IMPORT_COMPLET.md
    'docs/QUAND_VOIR_MES_DONNÉES.md',  # Info dans GUIDE_IMPORT_COMPLET.md
    'docs/CLARIFICATION_CONNEXION_SUPABASE.md',  # Info dans RÉSOLUTION_CONFUSION_SCRIPTS.md
    'docs/VALIDATION_SCRIPT_PC.md',  # Validation faite
    'docs/GUIDE_PARTAGE_ENV_PC.md',  # Info dans GUIDE_IMPORT_COMPLET.md
    'docs/IMPORTER_LES_63_PRODUITS.md',  # Info dans GUIDE_IMPORT_COMPLET.md
    'docs/TEMPS_EXÉCUTION_IMPORT.md',  # Peut être intégré ailleurs
    'docs/RÉSUMÉ_MIGRATION_INVENTAIRE.md',  # Temporaire
    
    # Scripts temporaires ou redondants
    'scripts/fetch_gazelle_products.py',  # Remplacé par import_gazelle_product_display.py
    'scripts/run_migration_002.py',  # Migration faite manuellement
    'scripts/IMPLÉMENTATION_FETCH_GAZELLE.md',  # Info dans le script principal
    
    # Fichiers racine temporaires
    'PLAN_ACTION_IMMEDIAT.md',  # Info dans GUIDE_IMPORT_COMPLET.md
    'README_IMPORT_PC.md',  # Info dans GUIDE_IMPORT_COMPLET.md
}

# Fichiers à vérifier avant suppression (peut-être utiles)
FILES_TO_REVIEW = {
    'docs/RAPPORT_CLASSIFICATION_PRODUITS.md',  # Peut être utile pour référence
    'docs/STATUT_SCRIPT_IMPORT.md',  # Peut être utile pour référence
}


def check_file_exists(filepath: str) -> bool:
    """Vérifie si un fichier existe."""
    return Path(filepath).exists()


def get_file_size(filepath: str) -> int:
    """Retourne la taille d'un fichier en octets."""
    try:
        return Path(filepath).stat().st_size
    except:
        return 0


def format_size(size: int) -> str:
    """Formate la taille en format lisible."""
    for unit in ['B', 'KB', 'MB']:
        if size < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} GB"


def analyze_files() -> Tuple[List[str], List[str], int]:
    """Analyse les fichiers et retourne ceux à supprimer et à garder."""
    project_root = Path(__file__).parent.parent
    files_to_remove = []
    files_to_keep = []
    total_size = 0
    
    print("=" * 60)
    print("Analyse des Fichiers")
    print("=" * 60)
    
    # Vérifier les fichiers à supprimer
    print("\n📋 Fichiers à supprimer (redondants/temporaires):")
    for filepath in FILES_TO_REMOVE:
        full_path = project_root / filepath
        if full_path.exists():
            size = get_file_size(str(full_path))
            total_size += size
            files_to_remove.append(filepath)
            print(f"  ❌ {filepath} ({format_size(size)})")
        else:
            print(f"  ⚠️  {filepath} (n'existe pas)")
    
    # Vérifier les fichiers essentiels
    print("\n✅ Fichiers essentiels (à garder):")
    for filepath in KEEP_FILES:
        full_path = project_root / filepath
        if full_path.exists():
            files_to_keep.append(filepath)
            print(f"  ✅ {filepath}")
        else:
            print(f"  ⚠️  {filepath} (MANQUANT!)")
    
    return files_to_remove, files_to_keep, total_size


def remove_files(files: List[str], dry_run: bool = True) -> int:
    """Supprime les fichiers listés."""
    project_root = Path(__file__).parent.parent
    removed_count = 0
    total_size = 0
    
    print("\n" + "=" * 60)
    if dry_run:
        print("MODE DRY-RUN: Aucun fichier ne sera supprimé")
    else:
        print("SUPPRESSION DES FICHIERS")
    print("=" * 60)
    
    for filepath in files:
        full_path = project_root / filepath
        if full_path.exists():
            size = get_file_size(str(full_path))
            total_size += size
            
            if dry_run:
                print(f"  🔍 [DRY-RUN] Supprimerait: {filepath} ({format_size(size)})")
            else:
                try:
                    full_path.unlink()
                    print(f"  ✅ Supprimé: {filepath} ({format_size(size)})")
                    removed_count += 1
                except Exception as e:
                    print(f"  ❌ Erreur: {filepath} - {e}")
        else:
            print(f"  ⚠️  {filepath} (n'existe pas)")
    
    if not dry_run:
        print(f"\n📊 Résumé:")
        print(f"   Fichiers supprimés: {removed_count}")
        print(f"   Espace libéré: {format_size(total_size)}")
    
    return removed_count


def main():
    """Fonction principale."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Nettoie les fichiers redondants ou temporaires"
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Exécute réellement la suppression (sinon dry-run)"
    )
    
    args = parser.parse_args()
    
    # Analyser les fichiers
    files_to_remove, files_to_keep, total_size = analyze_files()
    
    if not files_to_remove:
        print("\n✅ Aucun fichier à supprimer!")
        return 0
    
    print(f"\n📊 Total: {len(files_to_remove)} fichier(s) à supprimer")
    print(f"   Espace à libérer: {format_size(total_size)}")
    
    # Supprimer les fichiers
    removed = remove_files(files_to_remove, dry_run=not args.execute)
    
    if not args.execute:
        print("\n💡 Pour exécuter réellement la suppression:")
        print("   python scripts/cleanup_unused_files.py --execute")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
