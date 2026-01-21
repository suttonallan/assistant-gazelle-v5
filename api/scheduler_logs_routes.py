"""
Routes API pour les logs du scheduler (tâches planifiées)
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any
from core.supabase_storage import SupabaseStorage
from datetime import datetime, timezone, timedelta

router = APIRouter(prefix="/scheduler-logs", tags=["scheduler-logs"])


@router.get("/recent", response_model=Dict[str, Any])
async def get_recent_scheduler_logs(limit: int = 30):
    """
    Récupère les logs des tâches planifiées les plus récents.

    Args:
        limit: Nombre de logs à récupérer (défaut: 30, max: 100)

    Returns:
        {
            "logs": [...],
            "count": 30,
            "last_success": "2026-01-21T01:00:00Z"
        }
    """
    try:
        # Limiter à 100 max
        limit = min(limit, 100)

        storage = SupabaseStorage()

        # Récupérer les logs récents
        url = f"{storage.api_url}/scheduler_logs?select=*&order=started_at.desc&limit={limit}"
        headers = storage._get_headers()

        import requests
        response = requests.get(url, headers=headers)

        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Erreur Supabase: {response.text}"
            )

        logs = response.json()

        # Trouver le dernier succès
        last_success = None
        for log in logs:
            if log.get('status') == 'success':
                last_success = log.get('started_at')
                break

        return {
            "logs": logs,
            "count": len(logs),
            "last_success": last_success
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")


@router.get("/stats", response_model=Dict[str, Any])
async def get_scheduler_stats():
    """
    Statistiques des tâches planifiées (dernières 24h).

    Returns:
        {
            "total_tasks": 10,
            "success_count": 8,
            "error_count": 2,
            "last_execution": "2026-01-21T01:00:00Z",
            "avg_execution_time": 45.5
        }
    """
    try:
        storage = SupabaseStorage()

        # Timestamp 24h avant maintenant
        yesterday = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()

        # Récupérer tous les logs des dernières 24h
        url = f"{storage.api_url}/scheduler_logs?select=*&started_at=gte.{yesterday}&order=started_at.desc"
        headers = storage._get_headers()

        import requests
        response = requests.get(url, headers=headers)

        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Erreur Supabase: {response.text}"
            )

        logs = response.json()

        # Calculer les stats
        total_tasks = len(logs)
        success_count = sum(1 for log in logs if log.get('status') == 'success')
        error_count = sum(1 for log in logs if log.get('status') == 'error')
        running_count = sum(1 for log in logs if log.get('status') == 'running')

        # Temps d'exécution moyen
        execution_times = [
            log.get('duration_seconds', 0)
            for log in logs
            if log.get('duration_seconds') is not None
        ]
        avg_execution_time = sum(execution_times) / len(execution_times) if execution_times else 0

        # Dernière exécution
        last_execution = logs[0].get('started_at') if logs else None

        return {
            "total_tasks": total_tasks,
            "success_count": success_count,
            "error_count": error_count,
            "running_count": running_count,
            "last_execution": last_execution,
            "avg_execution_time": round(avg_execution_time, 2),
            "period_hours": 24
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")
