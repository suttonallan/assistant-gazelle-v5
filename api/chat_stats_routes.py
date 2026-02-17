"""
Routes API pour les statistiques du chat public (Piano Concierge).
Lecture des tables chat_clients, chat_photo_analyses, chat_sessions.
"""

import os
import requests as http_requests
from fastapi import APIRouter, HTTPException
from typing import Dict, Any
from pydantic import BaseModel
from core.supabase_storage import SupabaseStorage
from core.slack_notifier import SlackNotifier

router = APIRouter(prefix="/chat-stats", tags=["chat-stats"])


def _supabase_get(storage: SupabaseStorage, path: str):
    """Helper: GET request vers Supabase REST API."""
    url = f"{storage.api_url}/{path}"
    headers = storage._get_headers()
    response = http_requests.get(url, headers=headers, timeout=10)
    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail=f"Supabase: {response.text}")
    return response.json()


@router.get("/summary", response_model=Dict[str, Any])
async def get_chat_summary():
    """
    Statistiques globales du chat:
    - Total sessions, clients identifiés, analyses photo
    - Consultations par région
    - Intérêts des clients
    """
    try:
        storage = SupabaseStorage(silent=True)

        # Stats globales (vue)
        stats = _supabase_get(storage, "v_chat_stats?select=*")

        # Par région (vue)
        by_region = _supabase_get(storage, "v_chat_by_region?select=*&order=sessions.desc&limit=20")

        # Intérêts (vue)
        interests = _supabase_get(storage, "v_chat_interests?select=*&order=sessions.desc")

        # Activité 30 jours (vue)
        daily = _supabase_get(storage, "v_chat_daily_activity?select=*&order=jour.desc&limit=30")

        return {
            "stats": stats[0] if stats else {},
            "by_region": by_region,
            "interests": interests,
            "daily_activity": daily
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")


@router.get("/clients", response_model=Dict[str, Any])
async def get_chat_clients(limit: int = 50):
    """
    Liste des clients identifiés (avec email), triés par dernier contact.
    """
    try:
        storage = SupabaseStorage(silent=True)
        limit = min(limit, 200)

        clients = _supabase_get(
            storage,
            f"chat_clients?select=*&order=last_contact_at.desc&limit={limit}"
        )

        return {
            "clients": clients,
            "count": len(clients)
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")


@router.get("/analyses", response_model=Dict[str, Any])
async def get_recent_analyses(limit: int = 30):
    """
    Dernières analyses photo (marque, score, verdict).
    """
    try:
        storage = SupabaseStorage(silent=True)
        limit = min(limit, 100)

        analyses = _supabase_get(
            storage,
            f"chat_photo_analyses?select=*,chat_clients(email,first_name,region)"
            f"&order=created_at.desc&limit={limit}"
        )

        return {
            "analyses": analyses,
            "count": len(analyses)
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")


@router.get("/client/{email}", response_model=Dict[str, Any])
async def get_client_detail(email: str):
    """
    Détail d'un client par email: infos + ses analyses photo.
    """
    try:
        storage = SupabaseStorage(silent=True)

        # Client info
        clients = _supabase_get(storage, f"chat_clients?email=eq.{email}&select=*")
        if not clients:
            raise HTTPException(status_code=404, detail="Client non trouvé")

        client = clients[0]

        # Ses analyses
        analyses = _supabase_get(
            storage,
            f"chat_photo_analyses?client_id=eq.{client['id']}&select=*&order=created_at.desc"
        )

        return {
            "client": client,
            "analyses": analyses,
            "analyses_count": len(analyses)
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")


# ============================================================
# Slack notification webhook (called by ptm-chat-api)
# ============================================================

class ChatNotifyPayload(BaseModel):
    event_type: str  # 'new_contact', 'photo_analysis', 'concierge_interest'
    email: str = None
    region: str = None
    interest: str = None
    piano_brand: str = None
    score: int = None


@router.post("/notify")
async def notify_chat_event(payload: ChatNotifyPayload):
    """
    Reçoit un événement du chat public et envoie une notification Slack à Allan.
    Appelé par ptm-chat-api quand un prospect envoie des photos ou donne son email.
    """
    try:
        success = SlackNotifier.notify_chat_prospect(
            event_type=payload.event_type,
            email=payload.email,
            region=payload.region,
            interest=payload.interest,
            piano_brand=payload.piano_brand,
            score=payload.score
        )
        return {"success": success, "event_type": payload.event_type}
    except Exception as e:
        print(f"⚠️ Erreur notification chat Slack: {e}")
        return {"success": False, "error": str(e)}
