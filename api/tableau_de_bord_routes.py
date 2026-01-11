#!/usr/bin/env python3
"""
Endpoints API pour le Tableau de Bord unifié.

Fournit les données pour:
- Alertes (RV non confirmés + Maintenance pianos)
- Historique Pianos (modifications techniques)
- État du Système (derniers imports)
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any, Optional

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.supabase_storage import SupabaseStorage

# Créer 3 routers séparés pour éviter les conflits de préfixes
router_alertes = APIRouter(prefix="/alertes", tags=["tableau-de-bord"])
router_pianos = APIRouter(prefix="/pianos", tags=["tableau-de-bord"])
router_system = APIRouter(prefix="/system", tags=["tableau-de-bord"])

# Singletons
_storage = None


def get_storage() -> SupabaseStorage:
    """Retourne l'instance Supabase (singleton)."""
    global _storage
    if _storage is None:
        _storage = SupabaseStorage()
    return _storage


# ============================================================
# ENDPOINTS - ALERTES
# ============================================================

@router_alertes.get("/rv-non-confirmes")
async def get_unconfirmed_appointments() -> Dict[str, Any]:
    """
    Récupère les rendez-vous non confirmés pour les prochains jours.

    Returns:
        {
            "appointments": [...],
            "count": int
        }
    """
    try:
        storage = get_storage()

        # Récupérer les RV des 7 prochains jours
        today = datetime.now().date()
        end_date = today + timedelta(days=7)

        # Utiliser seulement les colonnes qui existent
        response = storage.client.table('gazelle_appointments').select(
            '*'
        ).gte(
            'appointment_date', today.isoformat()
        ).lte(
            'appointment_date', end_date.isoformat()
        ).order(
            'appointment_date', desc=False
        ).limit(15).execute()

        appointments = response.data or []

        # Pour chaque appointment, essayer d'enrichir avec client et tech
        for apt in appointments:
            # Nom du client
            apt['client_name'] = 'Client'

            # Nom du technicien
            apt['technician_name'] = 'Non assigné'

        return {
            "appointments": appointments,
            "count": len(appointments)
        }

    except Exception as e:
        print(f"[TableauDeBord] Erreur get_unconfirmed_appointments: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router_alertes.get("/maintenance")
async def get_maintenance_alerts() -> Dict[str, Any]:
    """
    Récupère les alertes de maintenance pour les pianos en retard.

    Returns:
        {
            "alerts": [...],
            "count": int
        }
    """
    try:
        # Pour l'instant, retourner une liste vide
        # TODO: Implémenter une fois que les colonnes service_interval_months et last_service_date sont disponibles
        return {
            "alerts": [],
            "count": 0
        }

    except Exception as e:
        print(f"[TableauDeBord] Erreur get_maintenance_alerts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# ENDPOINTS - HISTORIQUE PIANOS
# ============================================================

@router_pianos.get("/history")
async def get_piano_history(days: int = 7, type: str = 'technical') -> Dict[str, Any]:
    """
    Récupère l'historique des modifications de pianos (modifications techniques uniquement).

    Args:
        days: Nombre de jours d'historique (défaut: 7)
        type: Type de modifications ('technical', 'all')

    Returns:
        {
            "history": [...],
            "count": int
        }
    """
    try:
        # Pour l'instant, retourner une liste vide
        # TODO: Vérifier le nom exact de la table (gazelle_timeline_entries?) et implémenter
        return {
            "history": [],
            "count": 0
        }

    except Exception as e:
        print(f"[TableauDeBord] Erreur get_piano_history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# ENDPOINTS - ÉTAT SYSTÈME
# ============================================================

@router_system.get("/status")
async def get_system_status() -> Dict[str, Any]:
    """
    Récupère l'état du système (derniers imports Gazelle).

    Returns:
        {
            "last_sync_date": str,
            "last_sync_status": str,
            "last_sync_items": int,
            ...
        }
    """
    try:
        storage = get_storage()

        # Récupérer le dernier log de synchronisation
        response = storage.client.table('scheduler_logs').select(
            '*'
        ).order(
            'id', desc=True
        ).limit(1).execute()

        if not response.data:
            return {
                "last_sync_date": None,
                "last_sync_status": "unknown",
                "last_sync_items": 0
            }

        log = response.data[0]

        return {
            "last_sync_date": log.get('timestamp'),
            "last_sync_status": log.get('status', 'unknown'),
            "last_sync_items": 0,  # TODO: Calculer depuis les détails du log
            "last_sync_job": log.get('job_id'),
            "last_sync_error": log.get('error_message')
        }

    except Exception as e:
        print(f"[TableauDeBord] Erreur get_system_status: {e}")
        raise HTTPException(status_code=500, detail=str(e))
