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
        tables_updated: dict = None,
        error_message: str = None,
        execution_time_seconds: float = None
    ):
        """
        Enregistre un log de synchronisation.

        Args:
            script_name: Nom du script (ex: 'GitHub_Timeline_Sync')
            status: 'success', 'error', 'warning'
            tables_updated: Dict des tables mises à jour (ex: {"timeline": 50})
            error_message: Message d'erreur si status='error'
            execution_time_seconds: Durée d'exécution en secondes
        """
        if not self.client:
            print("⚠️  Supabase client non initialisé, impossible de logger")
            return False

        try:
            data = {
                'script_name': script_name,
                'status': status,
                'tables_updated': json.dumps(tables_updated) if tables_updated else None,
                'error_message': error_message,
                'execution_time_seconds': execution_time_seconds
            }

            result = self.client.table('sync_logs').insert(data).execute()

            print(f"✅ Log enregistré: {script_name} - {status}")
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
