"""
Routes FastAPI pour l'Assistant Conversationnel Intelligent (Phase 1: Core Handlers).

Gère les questions avancées:
- Recherche de clients
- Résumés complets de clients
- Mes rendez-vous
- Recherche de pianos

Usage:
    POST /api/conversation/query
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import logging
import traceback
import asyncio

from modules.assistant import ConversationHandler

router = APIRouter(prefix="/conversation", tags=["conversation"])

# Instance du handler (singleton)
conversation_handler = ConversationHandler()


class ConversationRequest(BaseModel):
    """Requête pour l'assistant conversationnel."""
    query: str
    user_id: str
    user_role: str = "technician"


class ConversationResponse(BaseModel):
    """Réponse de l'assistant conversationnel."""
    type: str  # client_search, client_summary, my_appointments, piano_search, error, not_found
    query: str
    formatted_response: Optional[str] = None
    data: Optional[dict] = None  # Données brutes pour affichage avancé si nécessaire


@router.post("/query", response_model=ConversationResponse)
async def process_conversation_query(request: ConversationRequest):
    """
    Traite une requête conversationnelle avancée.

    Examples:
        - "client Vincent-d'Indy"
        - "résumé pour Daniel Markwell"
        - "mes rendez-vous demain"
        - "piano 1234567"
    """
    try:
        # Process query (async)
        result = await conversation_handler.process_query(
            query=request.query,
            user_id=request.user_id,
            user_role=request.user_role
        )

        # Format response
        response_type = result.get('type', 'generic')
        formatted_response = result.get('formatted_response', result.get('message', ''))

        # Extract data based on type
        data = None
        if response_type == 'client_search':
            data = {"clients": result.get('clients', [])}
        elif response_type == 'client_summary':
            data = {
                "client": result.get('client'),
                "timeline_count": result.get('timeline_count', 0),
                "next_appointment": result.get('next_appointment')
            }
        elif response_type == 'my_appointments':
            data = {
                "appointments": result.get('appointments', []),
                "date_range": result.get('date_range', {})
            }
        elif response_type == 'piano_search':
            data = {"piano": result.get('piano')}

        return ConversationResponse(
            type=response_type,
            query=request.query,
            formatted_response=formatted_response,
            data=data
        )

    except Exception as e:
        error_detail = f"Erreur lors du traitement de la requête: {str(e)}\n{traceback.format_exc()}"
        logging.error(f"❌ Conversation query error: {error_detail}")
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "conversation_handler",
        "handlers": ["client_search", "client_summary", "my_appointments", "piano_search"]
    }
