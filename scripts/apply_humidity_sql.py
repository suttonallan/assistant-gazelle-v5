#!/usr/bin/env python3
"""
Applique la migration SQL pour les alertes d'humidité.
Utilise l'API REST de Supabase pour exécuter le SQL.
"""

import os
import sys
from pathlib import Path

# Ajouter le dossier parent au path pour importer les modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

def apply_migration():
    """Applique le SQL de migration via l'API Supabase."""

    # Lire le fichier SQL
    sql_path = Path(__file__).parent.parent / "sql" / "add_archived_to_humidity_alerts_fixed.sql"

    print(f"📂 Lecture du fichier SQL: {sql_path}")

    if not sql_path.exists():
        print(f"❌ Fichier SQL introuvable: {sql_path}")
        return False

    with open(sql_path, 'r', encoding='utf-8') as f:
        sql_content = f.read()

    print(f"✅ Fichier SQL chargé ({len(sql_content)} caractères)")
    print()

    # Afficher le SQL pour copier-coller manuellement
    print("="*80)
    print("📋 COPIE CE SQL ET EXÉCUTE-LE DANS SUPABASE SQL EDITOR:")
    print("="*80)
    print()
    print("1. Ouvre https://supabase.com/dashboard")
    print("2. Va dans 'SQL Editor'")
    print("3. Clique 'New Query'")
    print("4. Copie-colle le SQL ci-dessous")
    print("5. Clique 'Run' (ou Ctrl+Enter)")
    print()
    print("="*80)
    print(sql_content)
    print("="*80)
    print()

    # Test de validation
    print("🧪 APRÈS L'EXÉCUTION, TESTE AVEC CETTE REQUÊTE:")
    print("-"*80)
    print("SELECT COUNT(*) as count FROM humidity_alerts_active;")
    print("-"*80)
    print()
    print("✅ Si tu vois un nombre (même 0) → Succès!")
    print("❌ Si erreur 'relation does not exist' → Le SQL n'a pas été exécuté")
    print()

    return True

if __name__ == "__main__":
    print()
    print("🔧 MIGRATION SQL - ALERTES D'HUMIDITÉ")
    print("="*80)
    print()

    success = apply_migration()

    if success:
        print("✅ Instructions affichées ci-dessus")
        print()
        print("Une fois le SQL exécuté sur Supabase, teste avec:")
        print("  ./scripts/test_humidity_integration.sh")
        print()
        sys.exit(0)
    else:
        print("❌ Erreur lors de la lecture du fichier SQL")
        sys.exit(1)
