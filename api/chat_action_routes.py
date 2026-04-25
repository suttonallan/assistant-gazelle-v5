"""
API routes pour les actions exécutables via chat (création/amélioration soumissions).

POST /chat/action/preview  — analyse une demande, retourne un plan + preview_token
POST /chat/action/execute  — exécute l'action après confirmation (avec preview_token)

⚠️ MVP : execute est limité à des actions simples (rejet par défaut tant que la
logique de mutation n'est pas pleinement testée). La preview est toujours safe.
"""
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from modules.assistant_actions.intent_router import dispatch_chat_action
from modules.assistant_actions.audit_log import (
    find_pending_preview, mark_executed, log_action
)


router = APIRouter(prefix="/chat/action", tags=["chat-action"])


class PreviewRequest(BaseModel):
    text: str = Field(..., description="Demande naturelle de l'utilisateur")
    user_id: str = Field(..., description="ID ou email de l'utilisateur")
    user_role: str = Field(default='technicien', description="admin|technicien|coordinator")


class PreviewResponse(BaseModel):
    recognized: bool
    action_type: Optional[str] = None
    preview: Optional[dict] = None
    preview_token: Optional[str] = None
    message: str


class ExecuteRequest(BaseModel):
    preview_token: str = Field(..., description="Token reçu lors de la preview")
    user_id: str
    user_role: str = 'technicien'
    confirmed: bool = Field(default=False, description="Doit être True pour exécuter")


@router.post("/preview", response_model=PreviewResponse)
async def preview_action(req: PreviewRequest):
    """
    Analyse une demande naturelle, retourne le plan d'action et un preview_token.
    Aucune mutation Gazelle. Toujours safe.
    """
    try:
        result = dispatch_chat_action(req.text, req.user_id, req.user_role)
        return PreviewResponse(**result)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/execute")
async def execute_action(req: ExecuteRequest):
    """
    Exécute l'action après confirmation explicite.

    MVP : retourne 501 NOT_IMPLEMENTED. La logique de mutation Gazelle
    sera ajoutée après validation du flow de preview.
    """
    if not req.confirmed:
        raise HTTPException(status_code=400, detail="confirmed=false : action rejetée par sécurité")

    pending = find_pending_preview(req.preview_token)
    if not pending:
        raise HTTPException(status_code=404, detail="preview_token introuvable ou déjà utilisé")

    if pending.get('user_id') != req.user_id:
        raise HTTPException(status_code=403, detail="preview_token n'appartient pas à cet utilisateur")

    # MVP : on ne touche pas encore à Gazelle automatiquement.
    # Marquer comme 'confirmed' et logger pour qu'Allan puisse finaliser manuellement.
    mark_executed(
        pending['id'],
        response={'note': 'Confirmé par utilisateur. Création/modification à finaliser manuellement.'},
        status='confirmed',
    )

    return {
        'status': 'confirmed',
        'message': (
            "Action confirmée et journalisée. "
            "MVP : l'exécution automatique sur Gazelle sera activée après validation Allan."
        ),
        'action_type': pending.get('action_type'),
        'log_id': pending['id'],
    }
