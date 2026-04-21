#!/usr/bin/env python3
"""
Endpoints API pour le module Alertes de Rendez-vous non confirmés.

Version cloud-native avec Supabase + SendGrid.
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta, date
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.supabase_storage import SupabaseStorage
from modules.alertes_rv.checker import AppointmentChecker
from modules.alertes_rv.email_sender import EmailSender
from modules.alertes_rv.service import UnconfirmedAlertsService

router = APIRouter(prefix="/alertes-rv", tags=["alertes-rv"])

# Singletons
_storage = None
_checker = None
_email_sender = None
_service = None

# NOTE : le scheduler 16h (urgence_technique_j1) et 09h (RELANCE LOUISE) sont
# maintenant gérés UNIQUEMENT dans core/scheduler.py. Le BackgroundScheduler
# qui vivait ici a été supprimé parce qu'il faisait double-emploi et envoyait
# chaque alerte 2 fois.


def get_storage() -> SupabaseStorage:
    """Retourne l'instance Supabase (singleton)."""
    global _storage
    if _storage is None:
        _storage = SupabaseStorage()
    return _storage


def get_checker() -> AppointmentChecker:
    """Retourne l'instance du checker (singleton)."""
    global _checker
    if _checker is None:
        _checker = AppointmentChecker(get_storage())
    return _checker


def get_email_sender() -> EmailSender:
    """Retourne l'instance de l'email sender (singleton)."""
    global _email_sender
    if _email_sender is None:
        _email_sender = EmailSender(method='sendgrid')  # ou 'smtp' pour dev
    return _email_sender


def get_service() -> UnconfirmedAlertsService:
    """Retourne le service d'alertes (singleton)."""
    global _service
    if _service is None:
        _service = UnconfirmedAlertsService(
            storage=get_storage(),
            checker=get_checker(),
            sender=get_email_sender()
        )
    return _service


# ============================================================
# MODÈLES PYDANTIC
# ============================================================

class CheckRequest(BaseModel):
    """Requête pour vérifier les RV non confirmés."""
    target_date: Optional[str] = None  # Format YYYY-MM-DD (demain par défaut)
    exclude_types: Optional[List[str]] = None  # ['PERSONAL', 'MEMO'] par défaut


class SendAlertsRequest(BaseModel):
    """Requête pour envoyer les alertes."""
    target_date: Optional[str] = None
    technician_ids: Optional[List[str]] = None  # Si None, envoie à tous
    triggered_by: str  # Email de l'utilisateur qui déclenche


class ResolveAlertRequest(BaseModel):
    """Marquer une alerte comme résolue."""
    resolved_by: str


class AlertHistoryEntry(BaseModel):
    """Entrée d'historique d'alerte."""
    technician_id: str
    technician_name: str
    technician_email: str
    appointment_count: int
    sent_at: str
    triggered_by: str
    status: str  # 'sent', 'failed'


# ============================================================
# ENDPOINTS
# ============================================================

@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "service": "alertes-rv"}


@router.get("/check", response_model=Dict[str, Any])
async def check_unconfirmed_appointments(target_date: Optional[str] = None, exclude_types: Optional[str] = None):
    """
    Vérifie les RV non confirmés pour une date.

    Args:
        target_date: Date au format YYYY-MM-DD (demain par défaut)
        exclude_types: Types à exclure, séparés par virgules (ex: "PERSONAL,MEMO")

    Returns:
        Dict avec les RV groupés par technicien
    """
    try:
        checker = get_checker()

        # Parse target_date
        if target_date:
            target_date_obj = datetime.fromisoformat(target_date).date()
        else:
            from core.timezone_utils import MONTREAL_TZ
            target_date_obj = (datetime.now(MONTREAL_TZ) + timedelta(days=1)).date()

        # Parse exclude_types
        exclude_types_list = None
        if exclude_types:
            exclude_types_list = [t.strip() for t in exclude_types.split(',')]

        # Get unconfirmed appointments
        by_technician = checker.get_unconfirmed_appointments(
            target_date=target_date_obj,
            exclude_types=exclude_types_list
        )

        # Enrichir avec infos techniciens
        from core.timezone_utils import MONTREAL_TZ
        result = {
            'target_date': target_date_obj.isoformat(),
            'checked_at': datetime.now(MONTREAL_TZ).isoformat(),
            'technicians': []
        }

        for tech_id, appointments in by_technician.items():
            tech_info = checker.get_technician_info(tech_id)
            if tech_info:
                result['technicians'].append({
                    'id': tech_id,
                    'name': tech_info['name'],
                    'email': tech_info['email'],
                    'unconfirmed_count': len(appointments),
                    'appointments': appointments
                })

        result['total_technicians'] = len(result['technicians'])
        result['total_appointments'] = sum(t['unconfirmed_count'] for t in result['technicians'])

        return result

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Erreur lors de la vérification: {str(e)}")


@router.post("/send", response_model=Dict[str, Any])
async def send_alerts(request: SendAlertsRequest):
    """Envoie les alertes par email aux techniciens."""
    try:
        service = get_service()

        # Parse target_date
        if request.target_date:
            target_date = datetime.fromisoformat(request.target_date).date()
        else:
            target_date = (datetime.now() + timedelta(days=1)).date()

        result = service.send_alerts(
            target_date=target_date,
            technician_ids=request.technician_ids,
            triggered_by=request.triggered_by
        )
        return result

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Erreur lors de l'envoi: {str(e)}")


@router.post("/check-long-term", response_model=Dict[str, Any])
async def check_long_term():
    """
    Vérifie les RV dans 14 jours créés il y a >= 4 mois,
    et envoie un email à l'assistante (lookup via users).
    """
    try:
        service = get_service()
        result = service.check_long_term_appointments()
        if not result.get("success", False):
            raise HTTPException(status_code=500, detail=result.get("message", "Échec envoi long-term"))
        return result
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Erreur long-term: {str(e)}")


@router.get("/history", response_model=Dict[str, Any])
async def get_alerts_history(limit: int = 50, offset: int = 0):
    """
    Récupère l'historique des alertes envoyées.

    Args:
        limit: Nombre maximum d'entrées à retourner
        offset: Offset pour pagination

    Returns:
        Historique des alertes avec stats
    """
    try:
        storage = get_storage()

        # Query Supabase (alert_logs)
        # Utiliser sent_at si disponible, sinon created_at (fallback)
        import requests
        # Essayer d'abord avec sent_at, si erreur 400 alors utiliser created_at
        url = f"{storage.api_url}/alert_logs?order=sent_at.desc&limit={limit}&offset={offset}"
        response = requests.get(url, headers=storage._get_headers())
        
        # Si sent_at n'existe pas encore, utiliser created_at
        if response.status_code == 400 and 'sent_at' in response.text:
            url = f"{storage.api_url}/alert_logs?order=created_at.desc&limit={limit}&offset={offset}"
            response = requests.get(url, headers=storage._get_headers())

        if response.status_code != 200:
            error_detail = response.text
            raise HTTPException(status_code=response.status_code, detail=f"Erreur Supabase: {error_detail}")

        alerts = response.json() or []

        # Stats - utiliser les colonnes qui existent maintenant
        stats_by_user = {}
        stats_by_technician = {}
        total_appointments = 0

        for alert in alerts:
            # Utiliser les nouvelles colonnes si disponibles
            tech_id = alert.get('technician_id', 'unknown')
            tech_name = alert.get('technician_name', 'unknown')
            apt_count = alert.get('appointment_count') or alert.get('count', 1)  # appointment_count ou count
            triggered_by = alert.get('triggered_by', 'unknown')
            
            # Si technician_name n'est pas disponible, essayer de le récupérer depuis users
            if tech_name == 'unknown' and tech_id and tech_id != 'unknown':
                try:
                    user_response = storage.client.table('users').select('first_name, last_name').eq('external_id', tech_id).limit(1).execute()
                    if user_response.data:
                        user = user_response.data[0]
                        tech_name = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip() or tech_id
                    else:
                        tech_name = tech_id
                except:
                    tech_name = tech_id
            
            # Si triggered_by n'est pas disponible, utiliser created_at comme fallback
            if triggered_by == 'unknown':
                triggered_by = alert.get('created_at', 'unknown')

            stats_by_user[triggered_by] = stats_by_user.get(triggered_by, 0) + 1
            stats_by_technician[tech_name] = stats_by_technician.get(tech_name, 0) + apt_count
            total_appointments += apt_count

        return {
            'alerts': alerts,
            'count': len(alerts),
            'total_appointments_alerted': total_appointments,
            'stats_by_user': stats_by_user,
            'stats_by_technician': stats_by_technician
        }

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Erreur lors de la récupération: {str(e)}")


@router.get("/late-assignment", response_model=Dict[str, Any])
async def get_late_assignment_alerts(limit: int = 50):
    """
    Récupère les alertes "dernière minute" (assignations tardives < 24h).
    
    Args:
        limit: Nombre maximum d'alertes à retourner
        
    Returns:
        Liste des alertes dernière minute avec infos enrichies
    """
    try:
        storage = get_storage()
        
        # Récupérer depuis la vue late_assignment_alerts
        response = storage.client.table('late_assignment_alerts').select('*').limit(limit).order('created_at', desc=True).execute()
        
        alerts = response.data if response.data else []
        
        return {
            'alerts': alerts,
            'count': len(alerts),
            'pending': len([a for a in alerts if a.get('status') == 'pending']),
            'sent': len([a for a in alerts if a.get('status') == 'sent']),
            'failed': len([a for a in alerts if a.get('status') == 'failed'])
        }
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")


@router.get("/stats", response_model=Dict[str, Any])
async def get_stats():
    """Retourne des statistiques sur les alertes de RV."""
    try:
        storage = get_storage()

        # Query Supabase pour stats (alert_logs)
        import requests
        url = f"{storage.api_url}/alert_logs?select=*"
        response = requests.get(url, headers=storage._get_headers())

        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail="Erreur Supabase")

        alerts = response.json()

        # Calculer stats
        now = datetime.now()
        last_7_days = now - timedelta(days=7)
        last_30_days = now - timedelta(days=30)

        stats = {
            'total_alerts_sent': len(alerts),
            'alerts_last_7_days': 0,
            'alerts_last_30_days': 0,
            'by_user': {},
            'by_status': {
                'sent': 0,
                'failed': 0
            },
            'total_appointments_alerted': 0
        }

        for alert in alerts:
            sent_at_str = alert.get('sent_at')
            if sent_at_str:
                try:
                    # Normaliser le format de date pour fromisoformat
                    # Gérer les formats: 'Z', '+00:00', ou déjà avec timezone
                    date_str = sent_at_str.replace('Z', '+00:00')
                    
                    # Gérer les microsecondes non standard (5 chiffres au lieu de 6)
                    # Format: 2026-01-24T21:00:15.23983+00:00 -> 2026-01-24T21:00:15.239830+00:00
                    import re
                    # Pattern pour trouver .XXXXX suivi de + ou - (5 chiffres de microsecondes)
                    match = re.search(r'\.(\d{5})([+-]\d{2}:\d{2})', date_str)
                    if match:
                        # Ajouter un zéro pour avoir 6 chiffres
                        microseconds = match.group(1) + '0'  # Ajouter 0 à la fin
                        date_str = date_str.replace(match.group(0), f'.{microseconds}{match.group(2)}')
                    
                    sent_at = datetime.fromisoformat(date_str)
                    if sent_at >= last_7_days:
                        stats['alerts_last_7_days'] += 1
                    if sent_at >= last_30_days:
                        stats['alerts_last_30_days'] += 1
                except Exception as e:
                    # Si le parsing échoue, ignorer cette alerte pour les stats de dates
                    # Mais continuer avec les autres stats
                    print(f"⚠️  Erreur parsing date '{sent_at_str}': {e}")
                    pass

            user = alert.get('triggered_by', 'unknown')
            stats['by_user'][user] = stats['by_user'].get(user, 0) + 1

            status = alert.get('status', 'unknown')
            if status in stats['by_status']:
                stats['by_status'][status] += 1

            apt_count = alert.get('appointment_count', 0)
            stats['total_appointments_alerted'] += apt_count

        return stats

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Erreur lors du calcul des stats: {str(e)}")


# ---------------------------------------------------------------------------
# Alertes non résolues (UI)
# ---------------------------------------------------------------------------


@router.get("/pending", response_model=Dict[str, Any])
async def list_pending_alerts(technician_id: Optional[str] = None):
    """Retourne les alertes non résolues (pour affichage UI)."""
    try:
        service = get_service()
        alerts = service.list_pending(technician_id=technician_id)
        return {"alerts": alerts, "count": len(alerts)}
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Erreur lors de la récupération des alertes: {str(e)}")


@router.post("/resolve/{alert_id}")
async def resolve_alert(alert_id: str, request: ResolveAlertRequest):
    """Marque une alerte comme résolue (acknowledged)."""
    try:
        service = get_service()
        ok = service.resolve_alert(alert_id, resolved_by=request.resolved_by)
        if not ok:
            raise HTTPException(status_code=500, detail="Impossible de marquer comme résolue")
        return {"success": True, "id": alert_id}
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Erreur lors de la résolution: {str(e)}")


# ---------------------------------------------------------------------------
# Scheduler : deplace dans core/scheduler.py (task_urgence_technique_j1 16h
# et RELANCE LOUISE 9h). Pas de cron ici pour eviter les alertes en double.
# ---------------------------------------------------------------------------
