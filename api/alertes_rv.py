#!/usr/bin/env python3
"""
Endpoints API pour le module Alertes de Rendez-vous non confirmés.

Version cloud-native avec Supabase + SendGrid.
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta, date
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.supabase_storage import SupabaseStorage
from modules.alertes_rv.checker import AppointmentChecker
from modules.alertes_rv.email_sender import EmailSender

router = APIRouter(prefix="/alertes-rv", tags=["alertes-rv"])

# Singletons
_storage = None
_checker = None
_email_sender = None


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
async def send_alerts(request: SendAlertsRequest, background_tasks: BackgroundTasks):
    """
    Envoie les alertes par email aux techniciens.

    Les emails sont envoyés en arrière-plan pour ne pas bloquer la requête.
    """
    try:
        checker = get_checker()
        sender = get_email_sender()

        # Parse target_date
        if request.target_date:
            target_date = datetime.fromisoformat(request.target_date).date()
        else:
            target_date = (datetime.now() + timedelta(days=1)).date()

        # Get unconfirmed appointments
        by_technician = checker.get_unconfirmed_appointments(target_date=target_date)

        # Filtrer par technician_ids si fourni
        if request.technician_ids:
            by_technician = {k: v for k, v in by_technician.items() if k in request.technician_ids}

        if not by_technician:
            return {
                'success': True,
                'message': 'Aucun RV non confirmé trouvé',
                'sent_count': 0,
                'details': []
            }

        # Préparer les emails
        alerts_to_send = []
        for tech_id, appointments in by_technician.items():
            tech_info = checker.get_technician_info(tech_id)
            if not tech_info:
                continue

            # Formater le message HTML
            html_content = checker.format_alert_message(
                technician_name=tech_info['name'],
                appointments=appointments,
                target_date=target_date
            )

            date_str = target_date.strftime("%d/%m/%Y")
            subject = f"⚠️ {len(appointments)} RV non confirmé(s) pour le {date_str}"

            alerts_to_send.append({
                'to_email': tech_info['email'],
                'to_name': tech_info['name'],
                'subject': subject,
                'html_content': html_content,
                'technician_id': tech_id,
                'appointment_count': len(appointments)
            })

        # Envoyer en arrière-plan
        def send_and_log():
            """Envoie les emails et log dans Supabase."""
            send_results = sender.send_batch_alerts(alerts_to_send)

            # Log dans Supabase (table alerts_history)
            storage = get_storage()
            for i, alert in enumerate(alerts_to_send):
                success = send_results['details'][i]['success']

                history_entry = {
                    'technician_external_id': alert['technician_id'],
                    'technician_name': alert['to_name'],
                    'technician_email': alert['to_email'],
                    'target_date': target_date.isoformat(),
                    'appointment_count': alert['appointment_count'],
                    'sent_at': datetime.now().isoformat(),
                    'triggered_by': request.triggered_by,
                    'status': 'sent' if success else 'failed',
                    'subject': alert['subject']
                }

                try:
                    # Insert dans Supabase
                    import requests
                    url = f"{storage.api_url}/alerts_history"
                    response = requests.post(url, headers=storage._get_headers(), json=history_entry)
                    if response.status_code not in [200, 201]:
                        print(f"⚠️ Erreur log Supabase: {response.status_code}")
                except Exception as e:
                    print(f"⚠️ Erreur lors du log: {e}")

            return send_results

        background_tasks.add_task(send_and_log)

        return {
            'success': True,
            'message': f"{len(alerts_to_send)} alerte(s) en cours d'envoi",
            'sent_count': len(alerts_to_send),
            'target_date': target_date.isoformat(),
            'technicians': [
                {
                    'name': alert['to_name'],
                    'email': alert['to_email'],
                    'appointment_count': alert['appointment_count']
                }
                for alert in alerts_to_send
            ]
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Erreur lors de l'envoi: {str(e)}")


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

        # Query Supabase
        import requests
        url = f"{storage.api_url}/alerts_history?order=sent_at.desc&limit={limit}&offset={offset}"
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

        # Query Supabase pour stats
        import requests
        url = f"{storage.api_url}/alerts_history?select=*"
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
