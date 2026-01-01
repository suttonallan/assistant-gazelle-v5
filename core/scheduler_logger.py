#!/usr/bin/env python3
"""
Helper pour logger les exécutions des tâches planifiées dans Supabase.

Permet de tracer toutes les exécutions (succès/échec) dans la table scheduler_logs.
"""

import os
from datetime import datetime
from typing import Optional, Dict, Any
from supabase import create_client, Client


class SchedulerLogger:
    """Logger pour les tâches planifiées."""

    def __init__(self):
        """Initialise le client Supabase."""
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

        if not supabase_url or not supabase_key:
            raise ValueError("Variables SUPABASE_URL et SUPABASE_SERVICE_ROLE_KEY requises")

        self.client: Client = create_client(supabase_url, supabase_key)

    def start_task(
        self,
        task_name: str,
        task_label: str,
        triggered_by: str = 'scheduler',
        triggered_by_user: Optional[str] = None
    ) -> str:
        """
        Enregistre le démarrage d'une tâche.

        Args:
            task_name: Nom technique de la tâche
            task_label: Libellé affiché dans l'UI
            triggered_by: Mode de déclenchement ('scheduler', 'manual', 'api')
            triggered_by_user: Email de l'utilisateur si manuel

        Returns:
            ID du log créé
        """
        try:
            response = self.client.table('scheduler_logs').insert({
                'task_name': task_name,
                'task_label': task_label,
                'status': 'running',
                'triggered_by': triggered_by,
                'triggered_by_user': triggered_by_user,
                'started_at': datetime.now().isoformat()
            }).execute()

            if response.data:
                log_id = response.data[0]['id']
                print(f"📝 Log créé: {log_id} - {task_label}")
                return log_id
            else:
                print(f"⚠️  Erreur création log: {response}")
                return None

        except Exception as e:
            print(f"❌ Erreur logging start: {e}")
            return None

    def complete_task(
        self,
        log_id: str,
        status: str = 'success',
        message: Optional[str] = None,
        stats: Optional[Dict[str, Any]] = None
    ):
        """
        Enregistre la fin d'une tâche.

        Args:
            log_id: ID du log à mettre à jour
            status: Statut final ('success' ou 'error')
            message: Message de détail ou d'erreur
            stats: Statistiques de l'exécution (dict)
        """
        if not log_id:
            print("⚠️  Pas de log_id fourni, skip logging")
            return

        try:
            # Récupérer l'heure de début pour calculer la durée
            log_data = self.client.table('scheduler_logs').select('started_at').eq('id', log_id).execute()

            duration_seconds = None
            if log_data.data:
                started_at = datetime.fromisoformat(log_data.data[0]['started_at'].replace('Z', '+00:00'))
                duration_seconds = int((datetime.now().astimezone() - started_at).total_seconds())

            # Mettre à jour le log
            update_data = {
                'status': status,
                'completed_at': datetime.now().isoformat(),
                'duration_seconds': duration_seconds,
                'message': message,
                'stats': stats or {}
            }

            self.client.table('scheduler_logs').update(update_data).eq('id', log_id).execute()

            status_emoji = "✅" if status == 'success' else "❌"
            print(f"{status_emoji} Log mis à jour: {log_id} - {status}")

        except Exception as e:
            print(f"❌ Erreur logging complete: {e}")

    def get_recent_logs(self, limit: int = 20) -> list:
        """
        Récupère les logs récents.

        Args:
            limit: Nombre de logs à récupérer

        Returns:
            Liste des logs récents
        """
        try:
            response = self.client.table('scheduler_logs')\
                .select('*')\
                .order('started_at', desc=True)\
                .limit(limit)\
                .execute()

            return response.data if response.data else []

        except Exception as e:
            print(f"❌ Erreur récupération logs: {e}")
            return []


# Singleton
_logger: Optional[SchedulerLogger] = None


def get_logger() -> SchedulerLogger:
    """Retourne l'instance du logger (singleton)."""
    global _logger
    if _logger is None:
        _logger = SchedulerLogger()
    return _logger
