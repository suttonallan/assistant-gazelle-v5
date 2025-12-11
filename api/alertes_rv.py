#!/usr/bin/env python3
"""
Endpoints API pour le module Alertes de Rendez-vous non confirmés.

Gère la détection et l'envoi d'alertes pour les RV non confirmés.
"""

import os
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from core.gazelle_api_client import GazelleAPIClient

router = APIRouter(prefix="/alertes-rv", tags=["alertes-rv"])

# Client API Gazelle
_api_client = None

def get_api_client() -> GazelleAPIClient:
    """Retourne l'instance du client API Gazelle (singleton)."""
    global _api_client
    if _api_client is None:
        try:
            _api_client = GazelleAPIClient()
        except Exception as e:
            print(f"⚠️ Erreur lors de l'initialisation du client API: {e}")
            _api_client = None
    return _api_client


class AppointmentAlert(BaseModel):
    """Modèle pour une alerte de rendez-vous."""
    appointment_id: str
    client_name: str
    client_email: Optional[str] = None
    appointment_date: str
    alert_sent_by: str  # Email de l'utilisateur qui a déclenché


@router.get("/check", response_model=Dict[str, Any])
async def check_unconfirmed_appointments(days_threshold: int = 3):
    """
    Vérifie les rendez-vous non confirmés depuis plus de X jours.

    Args:
        days_threshold: Nombre de jours sans confirmation avant alerte

    Returns:
        Liste des RV non confirmés nécessitant une alerte
    """
    try:
        api_client = get_api_client()
        if not api_client:
            return {
                "unconfirmed": [],
                "count": 0,
                "error": "Client API Gazelle non disponible"
            }

        # TODO: Appeler l'API Gazelle pour récupérer les appointments
        # appointments = api_client.get_appointments(status='pending')

        # Pour l'instant, retourner des données mockées
        now = datetime.now()
        threshold_date = now - timedelta(days=days_threshold)

        mock_appointments = [
            {
                "id": "apt_001",
                "client_name": "Jean Dupont",
                "client_email": "jean.dupont@example.com",
                "appointment_date": (now - timedelta(days=5)).isoformat(),
                "created_at": (now - timedelta(days=5)).isoformat(),
                "confirmed": False,
                "technician": "Nicolas"
            },
            {
                "id": "apt_002",
                "client_name": "Marie Martin",
                "client_email": "marie.martin@example.com",
                "appointment_date": (now - timedelta(days=4)).isoformat(),
                "created_at": (now - timedelta(days=4)).isoformat(),
                "confirmed": False,
                "technician": "JP"
            }
        ]

        # Filtrer ceux non confirmés depuis plus de X jours
        unconfirmed = [
            apt for apt in mock_appointments
            if not apt['confirmed'] and
            datetime.fromisoformat(apt['created_at']) < threshold_date
        ]

        return {
            "unconfirmed": unconfirmed,
            "count": len(unconfirmed),
            "threshold_days": days_threshold,
            "checked_at": now.isoformat()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la vérification: {str(e)}")


@router.post("/send/{appointment_id}", response_model=Dict[str, Any])
async def send_alert(appointment_id: str, alert: AppointmentAlert):
    """
    Envoie une alerte pour un rendez-vous spécifique.

    Args:
        appointment_id: ID du rendez-vous
        alert: Données de l'alerte à envoyer

    Returns:
        Confirmation de l'envoi avec détails
    """
    try:
        # TODO: Implémenter l'envoi d'email réel
        # - Récupérer le template d'email
        # - Envoyer via service email (SendGrid, etc.)
        # - Logger dans Supabase

        alert_data = {
            "appointment_id": appointment_id,
            "client_name": alert.client_name,
            "client_email": alert.client_email,
            "appointment_date": alert.appointment_date,
            "alert_sent_at": datetime.now().isoformat(),
            "alert_sent_by": alert.alert_sent_by,
            "status": "sent"
        }

        # Pour l'instant, simuler l'envoi
        print(f"📧 Alerte envoyée à {alert.client_email} pour RV {appointment_id}")

        return {
            "success": True,
            "message": f"Alerte envoyée à {alert.client_email}",
            "alert": alert_data
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de l'envoi: {str(e)}")


@router.get("/alerts", response_model=Dict[str, Any])
async def list_alerts(limit: int = 50):
    """
    Liste toutes les alertes envoyées.

    Args:
        limit: Nombre maximum d'alertes à retourner

    Returns:
        Liste des alertes avec statistiques
    """
    try:
        # TODO: Récupérer depuis Supabase
        # Pour l'instant, retourner des données mockées

        now = datetime.now()
        mock_alerts = [
            {
                "id": 1,
                "appointment_id": "apt_001",
                "client_name": "Jean Dupont",
                "client_email": "jean.dupont@example.com",
                "appointment_date": (now - timedelta(days=5)).isoformat(),
                "alert_sent_at": (now - timedelta(hours=2)).isoformat(),
                "alert_sent_by": "allan@pianotekinc.com",
                "status": "sent"
            },
            {
                "id": 2,
                "appointment_id": "apt_002",
                "client_name": "Marie Martin",
                "client_email": "marie.martin@example.com",
                "appointment_date": (now - timedelta(days=4)).isoformat(),
                "alert_sent_at": (now - timedelta(hours=1)).isoformat(),
                "alert_sent_by": "louise@pianotekinc.com",
                "status": "sent"
            }
        ]

        # Stats par utilisateur
        stats_by_user = {}
        for alert in mock_alerts:
            user = alert['alert_sent_by']
            stats_by_user[user] = stats_by_user.get(user, 0) + 1

        return {
            "alerts": mock_alerts[:limit],
            "count": len(mock_alerts),
            "stats_by_user": stats_by_user
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la récupération: {str(e)}")


@router.get("/stats", response_model=Dict[str, Any])
async def get_stats():
    """Retourne des statistiques sur les alertes de RV."""
    try:
        # TODO: Calculer depuis Supabase

        return {
            "total_alerts_sent": 15,
            "alerts_last_7_days": 5,
            "alerts_last_30_days": 12,
            "by_user": {
                "allan@pianotekinc.com": 8,
                "louise@pianotekinc.com": 7
            },
            "by_status": {
                "sent": 10,
                "confirmed": 3,
                "cancelled": 2
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors du calcul des stats: {str(e)}")
