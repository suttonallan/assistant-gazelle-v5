#!/usr/bin/env python3
"""
Script de Push Automatique Quotidien vers Gazelle.

Ce script est appelé par cron à 01:00 chaque jour pour pusher automatiquement
les pianos marqués comme completed vers Gazelle.

Cron configuration:
    0 1 * * * /usr/bin/python3 /path/to/scripts/scheduled_push_to_gazelle.py

Logs:
    - Stdout/stderr: Capturés par cron (mail ou fichier log)
    - Fichier custom: /var/log/gazelle_push.log
"""

import sys
from pathlib import Path

# Ajouter le répertoire parent au path pour import
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.gazelle_push_service import GazellePushService
from datetime import datetime


def main():
    """Exécute le push automatique quotidien."""
    print(f"\n{'='*80}")
    print(f"PUSH AUTOMATIQUE QUOTIDIEN VERS GAZELLE")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*80}\n")

    try:
        service = GazellePushService()

        # Push tous les pianos prêts (toutes tournées confondues)
        result = service.schedule_daily_push(
            tournee_id=None,  # Tous les établissements
            technician_id="usr_HcCiFk7o0vZ9xAI0"  # Nick par défaut
        )

        # Afficher résumé
        print(f"\n{'='*80}")
        print("RÉSULTAT DU PUSH AUTOMATIQUE")
        print(f"{'='*80}")
        print(f"Pianos pushés:  {result['pushed_count']}/{result.get('total_pianos', 0)}")
        print(f"Erreurs:        {result['error_count']}")
        print(f"Succès global:  {'✅ OUI' if result['success'] else '❌ NON'}")
        print(f"{'='*80}\n")

        # Détails des erreurs si présentes
        if result['error_count'] > 0:
            print("\n⚠️  ERREURS DÉTAILLÉES:")
            print("-" * 80)
            for r in result['results']:
                if r['status'] == 'error':
                    print(f"Piano: {r['piano_id']}")
                    print(f"Erreur: {r['error']}")
                    print("-" * 80)

        # Exit code
        sys.exit(0 if result['success'] else 1)

    except Exception as e:
        print(f"\n❌ ERREUR FATALE lors du push automatique:")
        print(f"{e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
