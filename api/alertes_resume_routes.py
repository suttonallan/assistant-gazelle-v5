"""
Résumé unifié de toutes les alertes actives.

Agrège les compteurs de tous les systèmes de surveillance
pour affichage compact dans le Dashboard.
"""

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Dict, Any

import requests as req
from fastapi import APIRouter

router = APIRouter(prefix="/alertes-resume", tags=["alertes-resume"])
logger = logging.getLogger(__name__)


def _get_storage():
    from core.supabase_storage import SupabaseStorage
    return SupabaseStorage(silent=True)


@router.get("")
async def get_alertes_resume() -> Dict[str, Any]:
    """
    Retourne un résumé compact de toutes les alertes actives.

    Catégories:
    - humidity: alertes humidité non résolues
    - urgence_rv: RV non confirmés (dashboard_alerts)
    - pda_oublis: emails PDA non traités 2+ jours
    - late_assignment: assignations tardives en attente
    - validation: fiches de service en attente de validation
    """
    storage = _get_storage()
    headers = storage._get_headers()
    base = storage.api_url
    resume = {}

    # 1. Alertes humidité non résolues
    try:
        resp = req.get(
            f"{base}/humidity_alerts",
            headers=headers,
            params={
                "select": "id",
                "is_resolved": "eq.false",
                "is_archived": "eq.false",
            }
        )
        count = len(resp.json()) if resp.status_code == 200 else 0
        resume['humidity'] = {'count': count, 'label': 'Humidité'}
    except Exception as e:
        logger.warning(f"Erreur comptage humidity_alerts: {e}")
        resume['humidity'] = {'count': 0, 'label': 'Humidité', 'error': str(e)}

    # 2. Alertes RV non résolues (dashboard_alerts)
    try:
        resp = req.get(
            f"{base}/dashboard_alerts",
            headers=headers,
            params={
                "select": "id",
                "acknowledged": "eq.false",
            }
        )
        count = len(resp.json()) if resp.status_code == 200 else 0
        resume['urgence_rv'] = {'count': count, 'label': 'RV non confirmés'}
    except Exception as e:
        logger.warning(f"Erreur comptage dashboard_alerts: {e}")
        resume['urgence_rv'] = {'count': 0, 'label': 'RV non confirmés', 'error': str(e)}

    # 3. Oublis PDA — emails non traités depuis 2+ jours
    #    Vérifie processed_emails: emails récents avec status failed/no_requests/skipped
    #    + scheduler_logs pour le dernier résultat du détecteur
    try:
        # Dernière exécution du détecteur d'oublis
        resp = req.get(
            f"{base}/scheduler_logs",
            headers=headers,
            params={
                "select": "stats,status,completed_at",
                "task_name": "eq.detecter_oublis_pda",
                "order": "completed_at.desc",
                "limit": 1,
            }
        )
        oublis_count = 0
        last_check = None
        if resp.status_code == 200:
            data = resp.json()
            if data:
                stats = data[0].get('stats') or {}
                oublis_count = stats.get('oublis_count', 0)
                last_check = data[0].get('completed_at')

        # Aussi vérifier les emails en échec récents (derniers 7 jours)
        seuil = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
        resp2 = req.get(
            f"{base}/processed_emails",
            headers=headers,
            params={
                "select": "id",
                "status": "in.(failed,no_requests)",
                "processed_at": f"gte.{seuil}",
            }
        )
        failed_count = len(resp2.json()) if resp2.status_code == 200 else 0

        resume['pda_oublis'] = {
            'count': oublis_count + failed_count,
            'label': 'PDA non traités',
            'last_check': last_check,
        }
    except Exception as e:
        logger.warning(f"Erreur comptage oublis PDA: {e}")
        resume['pda_oublis'] = {'count': 0, 'label': 'PDA non traités', 'error': str(e)}

    # 4. Late assignment — en attente d'envoi
    try:
        resp = req.get(
            f"{base}/late_assignment_queue",
            headers=headers,
            params={
                "select": "id",
                "status": "eq.pending",
            }
        )
        count = len(resp.json()) if resp.status_code == 200 else 0
        resume['late_assignment'] = {'count': count, 'label': 'Assignation tardive'}
    except Exception as e:
        logger.warning(f"Erreur comptage late_assignment: {e}")
        resume['late_assignment'] = {'count': 0, 'label': 'Assignation tardive', 'error': str(e)}

    # 5. Fiches de service en attente de validation
    try:
        resp = req.get(
            f"{base}/piano_service_records",
            headers=headers,
            params={
                "select": "id",
                "status": "eq.completed",
            }
        )
        count = len(resp.json()) if resp.status_code == 200 else 0
        resume['validation'] = {'count': count, 'label': 'Fiches à valider'}
    except Exception as e:
        logger.warning(f"Erreur comptage validation: {e}")
        resume['validation'] = {'count': 0, 'label': 'Fiches à valider', 'error': str(e)}

    # Total
    total = sum(cat.get('count', 0) for cat in resume.values())

    return {
        'total_alertes': total,
        'categories': resume,
        'checked_at': datetime.now(timezone.utc).isoformat(),
    }
