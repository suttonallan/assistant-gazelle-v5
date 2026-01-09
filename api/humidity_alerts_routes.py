"""
Routes API pour les alertes d'humidité institutionnelles
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List
from core.supabase_storage import SupabaseStorage

router = APIRouter(prefix="/humidity-alerts", tags=["humidity-alerts"])


@router.get("/institutional", response_model=Dict[str, Any])
async def get_institutional_alerts():
    """
    Récupère les alertes d'humidité pour les clients institutionnels.

    Clients surveillés:
    - Vincent d'Indy
    - Place des Arts
    - Orford

    Returns:
        {
            "alerts": [
                {
                    "alert_type": "housse",
                    "client_name": "Vincent d'Indy",
                    "piano_make": "Steinway",
                    "piano_model": "B",
                    "description": "Housse enlevée détecté",
                    "is_resolved": false,
                    "observed_at": "2026-01-07T10:30:00Z"
                },
                ...
            ],
            "stats": {
                "total": 5,
                "unresolved": 2,
                "resolved": 3
            }
        }
    """
    try:
        storage = SupabaseStorage()

        # Clients institutionnels à surveiller
        INSTITUTIONAL_CLIENTS = [
            'Vincent d\'Indy',
            'Place des Arts',
            'Orford'
        ]

        # Requête pour récupérer les alertes actives (vue humidity_alerts_active)
        # avec filtre sur les clients institutionnels
        client_filter = ','.join([f'"{client}"' for client in INSTITUTIONAL_CLIENTS])
        url = f"{storage.api_url}/humidity_alerts_active?select=*&client_name=in.({client_filter})&order=observed_at.desc"
        headers = storage._get_headers()

        import requests
        response = requests.get(url, headers=headers)

        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Erreur Supabase: {response.text}"
            )

        all_alerts = response.json()

        # Calculer les statistiques
        total = len(all_alerts)
        unresolved = sum(1 for alert in all_alerts if not alert.get('is_resolved', False))
        resolved = sum(1 for alert in all_alerts if alert.get('is_resolved', False))

        return {
            "alerts": all_alerts,
            "stats": {
                "total": total,
                "unresolved": unresolved,
                "resolved": resolved
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")


@router.get("/all", response_model=Dict[str, Any])
async def get_all_alerts(limit: int = 100, resolved: bool = None):
    """
    Récupère toutes les alertes d'humidité.

    Args:
        limit: Nombre max d'alertes à récupérer (défaut: 100)
        resolved: Filtre par statut résolu (true/false/null pour tous)

    Returns:
        {
            "alerts": [...],
            "count": 45,
            "stats": {
                "total": 45,
                "unresolved": 12,
                "resolved": 33
            }
        }
    """
    try:
        storage = SupabaseStorage()

        # Construire l'URL avec filtres
        url = f"{storage.api_url}/humidity_alerts_active?select=*&order=observed_at.desc&limit={limit}"

        if resolved is not None:
            url += f"&is_resolved=eq.{str(resolved).lower()}"

        headers = storage._get_headers()

        import requests
        response = requests.get(url, headers=headers)

        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Erreur Supabase: {response.text}"
            )

        alerts = response.json()

        # Calculer les statistiques
        total = len(alerts)
        unresolved_count = sum(1 for alert in alerts if not alert.get('is_resolved', False))
        resolved_count = sum(1 for alert in alerts if alert.get('is_resolved', False))

        return {
            "alerts": alerts,
            "count": total,
            "stats": {
                "total": total,
                "unresolved": unresolved_count,
                "resolved": resolved_count
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")


@router.get("/stats", response_model=Dict[str, Any])
async def get_alerts_stats():
    """
    Statistiques globales des alertes d'humidité.

    Returns:
        {
            "total_alerts": 100,
            "unresolved": 15,
            "resolved": 85,
            "by_type": {
                "housse": 40,
                "alimentation": 35,
                "reservoir": 25
            },
            "institutional_unresolved": 3
        }
    """
    try:
        storage = SupabaseStorage()

        # Récupérer toutes les alertes actives
        url = f"{storage.api_url}/humidity_alerts_active?select=*"
        headers = storage._get_headers()

        import requests
        response = requests.get(url, headers=headers)

        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Erreur Supabase: {response.text}"
            )

        all_alerts = response.json()

        # Statistiques globales
        total_alerts = len(all_alerts)
        unresolved = sum(1 for alert in all_alerts if not alert.get('is_resolved', False))
        resolved = sum(1 for alert in all_alerts if alert.get('is_resolved', False))

        # Par type
        by_type = {}
        for alert in all_alerts:
            alert_type = alert.get('alert_type', 'unknown')
            by_type[alert_type] = by_type.get(alert_type, 0) + 1

        # Alertes institutionnelles non résolues
        INSTITUTIONAL_CLIENTS = ['Vincent d\'Indy', 'Place des Arts', 'Orford']
        institutional_unresolved = sum(
            1 for alert in all_alerts
            if alert.get('client_name') in INSTITUTIONAL_CLIENTS
            and not alert.get('is_resolved', False)
        )

        return {
            "total_alerts": total_alerts,
            "unresolved": unresolved,
            "resolved": resolved,
            "by_type": by_type,
            "institutional_unresolved": institutional_unresolved
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")
