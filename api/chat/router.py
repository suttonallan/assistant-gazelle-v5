"""
API Router pour Chat Intelligent V5/V6.
"""

from fastapi import APIRouter, HTTPException
from .schemas import ChatRequest, ChatResponse
from .service import ChatService

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/intelligent", response_model=ChatResponse)
async def chat_intelligent(request: ChatRequest):
    """
    Endpoint principal du Chat Intelligent.

    Args:
        request: Requête de chat

    Returns:
        Réponse structurée avec données
    """
    try:
        # Initialiser le service (V5 par défaut)
        chat_service = ChatService(data_source="v5")

        # Traiter la requête
        response = chat_service.process_query(request)

        return response

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health():
    """Vérifier l'état du service Chat Intelligent."""
    return {"status": "ok", "service": "chat_intelligent", "version": "v5"}
