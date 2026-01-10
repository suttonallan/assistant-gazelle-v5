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
from apscheduler.schedulers.background import BackgroundScheduler

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
_scheduler = None  # Lazy init dans startup
JOB_ID = "rv_unconfirmed_16h"
JOB_LONG_TERM_ID = "rv_long_term_09h"


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


@router.post("/check", response_model=Dict[str, Any])
async def check_unconfirmed_appointments(request: CheckRequest):
    """
    Vérifie les RV non confirmés pour une date.

    Returns:
        Dict avec les RV groupés par technicien
    """
    try:
        checker = get_checker()

        # Parse target_date
        if request.target_date:
            target_date = datetime.fromisoformat(request.target_date).date()
        else:
            target_date = (datetime.now() + timedelta(days=1)).date()

        # Get unconfirmed appointments
        by_technician = checker.get_unconfirmed_appointments(
            target_date=target_date,
            exclude_types=request.exclude_types
        )

        # Enrichir avec infos techniciens
        result = {
            'target_date': target_date.isoformat(),
            'checked_at': datetime.now().isoformat(),
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
        import requests
        url = f"{storage.api_url}/alert_logs?order=sent_at.desc&limit={limit}&offset={offset}"
        response = requests.get(url, headers=storage._get_headers())

        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail="Erreur Supabase")

        alerts = response.json()

        # Stats
        stats_by_user = {}
        stats_by_technician = {}
        total_appointments = 0

        for alert in alerts:
            triggered_by = alert.get('triggered_by', 'unknown')
            tech_name = alert.get('technician_name', 'unknown')
            apt_count = alert.get('appointment_count', 0)

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
                sent_at = datetime.fromisoformat(sent_at_str.replace('Z', '+00:00'))
                if sent_at >= last_7_days:
                    stats['alerts_last_7_days'] += 1
                if sent_at >= last_30_days:
                    stats['alerts_last_30_days'] += 1

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
# Scheduler 16h00
# ---------------------------------------------------------------------------


def _run_daily_job():
    """Job exécuté à 16h Montréal pour envoyer les alertes."""
    service = get_service()
    service.send_alerts(triggered_by="system@piano-tek.com")

def _run_long_term_job():
    """Job exécuté à 09h Montréal pour les RV longue durée."""
    service = get_service()
    service.check_long_term_appointments()


@router.on_event("startup")
def start_scheduler():
    global _scheduler
    try:
        print("📅 Démarrage du Scheduler alertes-rv...")

        # Initialisation lazy du scheduler
        if _scheduler is None:
            print("   → Création du BackgroundScheduler (timezone=America/Montreal)")
            _scheduler = BackgroundScheduler(timezone="America/Montreal")

        if not _scheduler.running:
            print("   → Démarrage du scheduler en mode pausé")
            _scheduler.start(paused=True)

        if not _scheduler.get_job(JOB_ID):
            print(f"   → Ajout job quotidien {JOB_ID} (16h)")
            _scheduler.add_job(
                _run_daily_job,
                trigger="cron",
                hour=16,
                minute=0,
                id=JOB_ID,
                replace_existing=True,
            )

        if not _scheduler.get_job(JOB_LONG_TERM_ID):
            print(f"   → Ajout job longue durée {JOB_LONG_TERM_ID} (9h)")
            _scheduler.add_job(
                _run_long_term_job,
                trigger="cron",
                hour=9,
                minute=0,
                id=JOB_LONG_TERM_ID,
                replace_existing=True,
            )

        if _scheduler.state == 2:  # paused
            print("   → Reprise du scheduler")
            _scheduler.resume()

        print("✅ Scheduler alertes-rv démarré avec succès")
    except Exception as e:
        print(f"⚠️ Scheduler alertes-rv non démarré: {e}")
        import traceback
        traceback.print_exc()


@router.on_event("shutdown")
def shutdown_scheduler():
    try:
        print("🛑 Arrêt du Scheduler alertes-rv...")
        if _scheduler and _scheduler.running:
            _scheduler.shutdown(wait=False)
            print("✅ Scheduler alertes-rv arrêté")
    except Exception as e:
        print(f"⚠️ Erreur arrêt scheduler: {e}")
