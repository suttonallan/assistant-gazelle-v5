#!/usr/bin/env python3
"""
Helper pour logger les synchronisations dans Supabase sync_logs.
"""

import os
import sys
from pathlib import Path
from datetime import datetime
import json

# Ajouter le chemin parent pour imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from supabase import create_client


class SyncLogger:
    """Logger pour les synchronisations automatiques."""

    def __init__(self):
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

        if not self.supabase_url or not self.supabase_key:
            print("⚠️  SUPABASE_URL ou SUPABASE_SERVICE_ROLE_KEY manquant")
            self.client = None
        else:
            self.client = create_client(self.supabase_url, self.supabase_key)

    def log_sync(
        self,
        script_name: str,
        status: str,
        task_type: str = 'sync',
        message: str = None,
        stats: dict = None,
        error_details: str = None,
        execution_time_seconds: float = None,
        triggered_by: str = 'scheduler',
        triggered_by_user: str = None,
        # Rétrocompatibilité
        tables_updated: dict = None,
        error_message: str = None
    ):
        """
        Enregistre un log de synchronisation.

        Args:
            script_name: Nom du script (ex: 'Sync Gazelle Totale')
            status: 'success', 'error', 'warning', 'running'
            task_type: Type de tâche ('sync', 'report', 'chain', 'backup')
            message: Message de succès ou description
            stats: Dict des statistiques (ex: {"clients": 50, "pianos": 100})
            error_details: Message d'erreur détaillé si status='error'
            execution_time_seconds: Durée d'exécution en secondes
            triggered_by: Mode de déclenchement ('scheduler', 'manual', 'api')
            triggered_by_user: Email utilisateur si manuel
            tables_updated: (deprecated) Utilisez 'stats' à la place
            error_message: (deprecated) Utilisez 'error_details' à la place
        """
        if not self.client:
            print("⚠️  Supabase client non initialisé, impossible de logger")
            return False

        try:
            # Rétrocompatibilité
            if tables_updated and not stats:
                stats = tables_updated
            if error_message and not error_details:
                error_details = error_message

            data = {
                'script_name': script_name,
                'task_type': task_type,
                'status': status,
                'message': message,
                'stats': stats or {},
                'error_details': error_details,
                'execution_time_seconds': execution_time_seconds,
                'triggered_by': triggered_by,
                'triggered_by_user': triggered_by_user,
                'created_at': datetime.now().isoformat()
            }

            result = self.client.table('sync_logs').insert(data).execute()

            status_emoji = {
                'success': '✅',
                'error': '❌',
                'warning': '⚠️',
                'running': '⏳'
            }.get(status, '❓')

            print(f"{status_emoji} Log enregistré: {script_name} - {status}")
            return True

        except Exception as e:
            print(f"❌ Erreur lors du logging: {e}")
            return False

    def get_recent_logs(self, limit: int = 10):
        """Récupère les logs récents."""
        if not self.client:
            return []

        try:
            result = self.client.table('sync_logs') \
                .select('*') \
                .order('created_at', desc=True) \
                .limit(limit) \
                .execute()

            return result.data
        except Exception as e:
            print(f"❌ Erreur récupération logs: {e}")
            return []


if __name__ == '__main__':
    # Test du logger
    logger = SyncLogger()

    # Exemple d'utilisation
    logger.log_sync(
        script_name='Test_Script',
        status='success',
        tables_updated={'timeline': 5, 'clients': 2},
        execution_time_seconds=3.5
    )

    # Afficher les logs récents
    logs = logger.get_recent_logs(5)
    print(f"\n📊 {len(logs)} logs récents:")
    for log in logs:
        print(f"  - {log['script_name']}: {log['status']} ({log['created_at']})")
