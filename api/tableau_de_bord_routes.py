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

router = APIRouter(prefix="/api/alertes", tags=["tableau-de-bord"])

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

@router.get("/rv-non-confirmes")
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

        # Récupérer les RV non confirmés des 7 prochains jours
        today = datetime.now().date()
        end_date = today + timedelta(days=7)

        response = storage.client.table('gazelle_appointments').select(
            'id, gazelle_id, title, appointment_date, appointment_time, '
            'confirmed_by_client, client_id, user_id, status, type, created_at'
        ).eq(
            'confirmed_by_client', False
        ).gte(
            'appointment_date', today.isoformat()
        ).lte(
            'appointment_date', end_date.isoformat()
        ).not_.in_(
            'type', ['PERSONAL', 'MEMO']  # Exclure les types non pertinents
        ).order(
            'appointment_date', desc=False
        ).execute()

        appointments = response.data or []

        # Enrichir avec les noms de clients et techniciens
        for apt in appointments:
            if apt.get('client_id'):
                client_resp = storage.client.table('gazelle_clients').select(
                    'company_name, contact_name'
                ).eq('gazelle_id', apt['client_id']).limit(1).execute()
                if client_resp.data:
                    client = client_resp.data[0]
                    apt['client_name'] = client.get('company_name') or client.get('contact_name') or 'Client inconnu'
                else:
                    apt['client_name'] = 'Client inconnu'
            else:
                apt['client_name'] = 'Client inconnu'

            if apt.get('user_id'):
                user_resp = storage.client.table('gazelle_users').select(
                    'name'
                ).eq('gazelle_id', apt['user_id']).limit(1).execute()
                if user_resp.data:
                    apt['technician_name'] = user_resp.data[0].get('name') or 'Technicien inconnu'
                else:
                    apt['technician_name'] = 'Technicien inconnu'
            else:
                apt['technician_name'] = 'Non assigné'

        return {
            "appointments": appointments,
            "count": len(appointments)
        }

    except Exception as e:
        print(f"[TableauDeBord] Erreur get_unconfirmed_appointments: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/maintenance")
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
        storage = get_storage()

        # Récupérer les pianos avec service_interval et last_service_date
        response = storage.client.table('gazelle_pianos').select(
            'id, gazelle_id, make, model, size, serial_number, '
            'service_interval_months, last_service_date, client_id'
        ).not_.is_(
            'service_interval_months', 'null'
        ).not_.is_(
            'last_service_date', 'null'
        ).execute()

        pianos = response.data or []
        alerts = []
        today = datetime.now().date()

        for piano in pianos:
            interval = piano.get('service_interval_months')
            last_service = piano.get('last_service_date')

            if not interval or not last_service:
                continue

            # Calculer la date de prochain service
            try:
                last_service_dt = datetime.fromisoformat(last_service.replace('Z', '+00:00')).date()
            except:
                continue

            # Ajouter l'intervalle en mois
            months_to_add = int(interval)
            next_service_dt = last_service_dt + timedelta(days=months_to_add * 30)  # Approximation

            # Calculer le retard en jours
            days_overdue = (today - next_service_dt).days

            # Alertes seulement si en retard
            if days_overdue > 0:
                # Enrichir avec nom du client
                client_name = 'Client inconnu'
                if piano.get('client_id'):
                    client_resp = storage.client.table('gazelle_clients').select(
                        'company_name, contact_name'
                    ).eq('gazelle_id', piano['client_id']).limit(1).execute()
                    if client_resp.data:
                        client = client_resp.data[0]
                        client_name = client.get('company_name') or client.get('contact_name') or 'Client inconnu'

                piano_info = f"{piano.get('make', '')} {piano.get('model', '')}".strip() or 'Piano'
                if piano.get('serial_number'):
                    piano_info += f" #{piano['serial_number']}"

                alerts.append({
                    'piano_id': piano['gazelle_id'],
                    'piano_info': piano_info,
                    'client_name': client_name,
                    'days_overdue': days_overdue,
                    'last_service_date': last_service,
                    'next_service_date': next_service_dt.isoformat(),
                    'service_interval_months': interval
                })

        # Trier par retard décroissant
        alerts.sort(key=lambda x: x['days_overdue'], reverse=True)

        return {
            "alerts": alerts,
            "count": len(alerts)
        }

    except Exception as e:
        print(f"[TableauDeBord] Erreur get_maintenance_alerts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# ENDPOINTS - HISTORIQUE PIANOS
# ============================================================

@router.get("/pianos/history")
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
        storage = get_storage()

        # Calculer la date cutoff
        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()

        # Récupérer les modifications récentes depuis gazelle_timeline
        # Filtrer par type = 'Piano' ou 'Service' pour modifications techniques
        response = storage.client.table('gazelle_timeline').select(
            'id, created_at, updated_at, type, title, description, '
            'piano_id, client_id, user_id'
        ).gte(
            'created_at', cutoff_date
        ).in_(
            'type', ['PIANO_NOTE', 'SERVICE', 'PIANO_UPDATE']  # Types techniques
        ).order(
            'created_at', desc=True
        ).limit(100).execute()

        entries = response.data or []
        history = []

        for entry in entries:
            # Enrichir avec infos piano
            piano_info = None
            if entry.get('piano_id'):
                piano_resp = storage.client.table('gazelle_pianos').select(
                    'make, model, serial_number'
                ).eq('gazelle_id', entry['piano_id']).limit(1).execute()
                if piano_resp.data:
                    piano = piano_resp.data[0]
                    piano_info = f"{piano.get('make', '')} {piano.get('model', '')}".strip()
                    if piano.get('serial_number'):
                        piano_info += f" #{piano['serial_number']}"

            # Enrichir avec nom du client
            client_name = None
            if entry.get('client_id'):
                client_resp = storage.client.table('gazelle_clients').select(
                    'company_name, contact_name'
                ).eq('gazelle_id', entry['client_id']).limit(1).execute()
                if client_resp.data:
                    client = client_resp.data[0]
                    client_name = client.get('company_name') or client.get('contact_name')

            history.append({
                'id': entry['id'],
                'modified_at': entry.get('updated_at') or entry.get('created_at'),
                'piano_info': piano_info or 'Piano inconnu',
                'client_name': client_name or 'Client inconnu',
                'change_description': entry.get('title') or entry.get('description') or 'Modification technique',
                'type': entry.get('type')
            })

        return {
            "history": history,
            "count": len(history)
        }

    except Exception as e:
        print(f"[TableauDeBord] Erreur get_piano_history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# ENDPOINTS - ÉTAT SYSTÈME
# ============================================================

@router.get("/system/status")
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
        response = storage.client.table('sync_logs').select(
            'id, started_at, finished_at, status, error_message, '
            'job_name, details'
        ).order(
            'started_at', desc=True
        ).limit(1).execute()

        if not response.data:
            return {
                "last_sync_date": None,
                "last_sync_status": "unknown",
                "last_sync_items": 0
            }

        log = response.data[0]

        # Extraire les stats depuis details (JSONB)
        details = log.get('details') or {}
        total_items = 0

        # Compter les items synchronisés
        if isinstance(details, dict):
            for key in ['clients', 'pianos', 'appointments', 'timeline']:
                total_items += details.get(key, 0)

        return {
            "last_sync_date": log.get('finished_at') or log.get('started_at'),
            "last_sync_status": log.get('status', 'unknown'),
            "last_sync_items": total_items,
            "last_sync_job": log.get('job_name'),
            "last_sync_error": log.get('error_message')
        }

    except Exception as e:
        print(f"[TableauDeBord] Erreur get_system_status: {e}")
        raise HTTPException(status_code=500, detail=str(e))
