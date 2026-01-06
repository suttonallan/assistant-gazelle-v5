"""
Routes FastAPI pour le Chat Intelligent.

Usage:
    POST /api/chat/query
    GET  /api/chat/day/{date}
    GET  /api/chat/appointment/{appointment_id}
"""

from fastapi import APIRouter, HTTPException
from datetime import datetime
from typing import Optional

from api.chat import ChatService, ChatRequest, ChatResponse

router = APIRouter(prefix="/chat", tags=["chat"])

# Instance du service (singleton)
chat_service = ChatService(data_source="v5")


@router.post("/query", response_model=ChatResponse)
async def process_chat_query(request: ChatRequest):
    """
    Traite une requête naturelle du chat.

    Examples:
        - "Ma journée de demain"
        - "Mes rendez-vous aujourd'hui"
        - "Le 30 décembre"
    """
    try:
        response = chat_service.process_query(request)
        return response
    except Exception as e:
        import traceback
        import logging
        error_detail = f"Erreur lors du traitement de la requête: {str(e)}\n{traceback.format_exc()}"
        logging.error(f"❌ Chat query error: {error_detail}")
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")


@router.get("/day/{date}")
async def get_day_overview(
    date: str,
    technician_id: Optional[str] = None
):
    """
    Récupère la vue d'ensemble d'une journée spécifique.

    Args:
        date: Format YYYY-MM-DD
        technician_id: Optionnel, filtre par technicien
    """
    try:
        # Valider format date
        datetime.strptime(date, "%Y-%m-%d")

        request = ChatRequest(
            query=f"Journée du {date}",
            technician_id=technician_id,
            date=date
        )

        response = chat_service.process_query(request)
        return response.day_overview

    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/appointment/{appointment_id}")
async def get_appointment_detail(appointment_id: str):
    """
    Récupère les détails complets d'un rendez-vous.

    Args:
        appointment_id: ID du rendez-vous (ex: apt_123)
    """
    try:
        detail = chat_service.data_provider.get_appointment_detail(appointment_id)
        return detail
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "chat_intelligent",
        "data_source": chat_service.data_source
    }
