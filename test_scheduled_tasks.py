#!/usr/bin/env python3
"""
Script de test manuel pour les tâches planifiées.

Permet d'exécuter individuellement chaque tâche sans attendre
l'heure programmée, pour vérifier qu'elles fonctionnent correctement.

Usage:
    # Tester toutes les tâches
    python3 test_scheduled_tasks.py

    # Tester une tâche spécifique
    python3 test_scheduled_tasks.py --task sync
    python3 test_scheduled_tasks.py --task rapport
    python3 test_scheduled_tasks.py --task backup
    python3 test_scheduled_tasks.py --task alerts
"""

import sys
import argparse
from pathlib import Path

# Ajouter le projet au path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

from core.scheduler import (
    task_sync_gazelle_totale,
    task_generate_rapport_timeline,
    task_backup_database,
    task_sync_rv_and_alerts
)


def test_sync_gazelle():
    """Test de la synchronisation Gazelle complète."""
    print("\n" + "="*70)
    print("🧪 TEST: Sync Gazelle Totale")
    print("="*70)

    try:
        task_sync_gazelle_totale()
        print("\n✅ Test réussi!")
        return True
    except Exception as e:
        print(f"\n❌ Test échoué: {e}")
        return False


def test_rapport_timeline():
    """Test de la génération du rapport Timeline."""
    print("\n" + "="*70)
    print("🧪 TEST: Rapport Timeline Google Sheets")
    print("="*70)

    try:
        task_generate_rapport_timeline()
        print("\n✅ Test réussi!")
        return True
    except Exception as e:
        print(f"\n❌ Test échoué: {e}")
        return False


def test_backup():
    """Test du backup de la base de données."""
    print("\n" + "="*70)
    print("🧪 TEST: Backup Database")
    print("="*70)

    try:
        task_backup_database()
        print("\n✅ Test réussi!")
        return True
    except Exception as e:
        print(f"\n❌ Test échoué: {e}")
        return False


def test_rv_alerts():
    """Test de la synchronisation RV et des alertes."""
    print("\n" + "="*70)
    print("🧪 TEST: Sync RV & Alertes")
    print("="*70)

    try:
        task_sync_rv_and_alerts()
        print("\n✅ Test réussi!")
        return True
    except Exception as e:
        print(f"\n❌ Test échoué: {e}")
        return False


def run_all_tests():
    """Exécute tous les tests."""
    print("\n" + "="*70)
    print("🧪 TEST DE TOUTES LES TÂCHES PLANIFIÉES")
    print("="*70)

    results = {
        'Sync Gazelle': test_sync_gazelle(),
        'Rapport Timeline': test_rapport_timeline(),
        'Backup Database': test_backup(),
        'RV & Alertes': test_rv_alerts()
    }

    print("\n" + "="*70)
    print("📊 RÉSULTATS DES TESTS")
    print("="*70)

    for task_name, success in results.items():
        status = "✅ RÉUSSI" if success else "❌ ÉCHOUÉ"
        print(f"   {task_name}: {status}")

    total = len(results)
    passed = sum(results.values())

    print(f"\n   Total: {passed}/{total} tests réussis")
    print("="*70 + "\n")

    return all(results.values())


def main():
    """Point d'entrée principal."""
    parser = argparse.ArgumentParser(description='Test des tâches planifiées')
    parser.add_argument(
        '--task',
        choices=['sync', 'rapport', 'backup', 'alerts', 'all'],
        default='all',
        help='Tâche à tester (défaut: all)'
    )

    args = parser.parse_args()

    if args.task == 'sync':
        success = test_sync_gazelle()
    elif args.task == 'rapport':
        success = test_rapport_timeline()
    elif args.task == 'backup':
        success = test_backup()
    elif args.task == 'alerts':
        success = test_rv_alerts()
    else:
        success = run_all_tests()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
