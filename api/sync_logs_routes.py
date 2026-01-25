"""
Routes API pour les logs de synchronisation
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List
from datetime import datetime, timedelta, timezone
from core.supabase_storage import SupabaseStorage

router = APIRouter(prefix="/sync-logs", tags=["sync-logs"])


@router.get("/recent", response_model=Dict[str, Any])
async def get_recent_sync_logs(limit: int = 20):
    """
    Récupère les logs de synchronisation les plus récents.

    Args:
        limit: Nombre de logs à récupérer (défaut: 20, max: 100)

    Returns:
        {
            "logs": [...],
            "count": 20,
            "last_success": "2026-01-07T10:30:00Z"
        }
    """
    try:
        # Limiter à 100 max
        limit = min(limit, 100)

        storage = SupabaseStorage()

        # Récupérer les logs récents
        url = f"{storage.api_url}/sync_logs?select=*&order=created_at.desc&limit={limit}"
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
                last_success = log.get('created_at')
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
async def get_sync_stats():
    """
    Statistiques des synchronisations (dernières 24h).

    Returns:
        {
            "total_syncs": 10,
            "success_count": 8,
            "error_count": 2,
            "last_sync": "2026-01-07T10:30:00Z",
            "avg_execution_time": 3.5
        }
    """
    try:
        from datetime import datetime, timedelta

        storage = SupabaseStorage()

        # Timestamp 24h avant maintenant (format URL-safe sans +)
        yesterday = (datetime.now(timezone.utc) - timedelta(hours=24)).strftime('%Y-%m-%dT%H:%M:%SZ')

        # Récupérer tous les logs des dernières 24h
        url = f"{storage.api_url}/sync_logs?select=*&created_at=gte.{yesterday}&order=created_at.desc"
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
        total_syncs = len(logs)
        success_count = sum(1 for log in logs if log.get('status') == 'success')
        error_count = sum(1 for log in logs if log.get('status') == 'error')
        warning_count = sum(1 for log in logs if log.get('status') == 'warning')

        # Temps d'exécution moyen
        execution_times = [
            log.get('execution_time_seconds', 0)
            for log in logs
            if log.get('execution_time_seconds') is not None
        ]
        avg_execution_time = sum(execution_times) / len(execution_times) if execution_times else 0

        # Dernier sync
        last_sync = logs[0].get('created_at') if logs else None

        return {
            "total_syncs": total_syncs,
            "success_count": success_count,
            "error_count": error_count,
            "warning_count": warning_count,
            "last_sync": last_sync,
            "avg_execution_time": round(avg_execution_time, 2),
            "period_hours": 24
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")
