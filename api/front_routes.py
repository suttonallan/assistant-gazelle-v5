"""Endpoints API pour Front (frontapp.com).

Expose la lecture des conversations, messages et commentaires internes
via l'API Front. Enregistré deux fois dans `api/main.py` — sans prefix
(dev, Vite proxy) et avec `/api` prefix (prod Render).
"""
from fastapi import APIRouter, HTTPException, Query
import logging

from core.front_client import get_front_client

router = APIRouter(prefix="/front", tags=["front"])
_log = logging.getLogger(__name__)


def _handle(fn, *args, **kwargs):
    """Wrap un appel client et convertit les erreurs en HTTPException propres."""
    try:
        return fn(*args, **kwargs)
    except ValueError as e:  # FRONT_API_KEY manquant
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        _log.exception("Erreur Front API")
        raise HTTPException(status_code=502, detail=f"Erreur Front API: {e}")


@router.get("/me")
def whoami():
    """Test de connectivité — retourne le teammate propriétaire du token."""
    return _handle(get_front_client().me)


@router.get("/inboxes")
def list_inboxes():
    """Liste les inboxes accessibles au token."""
    return {"inboxes": _handle(get_front_client().list_inboxes)}


@router.get("/teammates")
def list_teammates():
    """Liste les teammates du workspace Front."""
    return {"teammates": _handle(get_front_client().list_teammates)}


@router.get("/search")
def search(q: str = Query(..., min_length=2, description="Mot-clé ou phrase"),
           limit: int = Query(25, ge=1, le=100)):
    """Recherche full-text dans les conversations.

    Ex : `GET /front/search?q=Place%20des%20Arts&limit=10`
    """
    results = _handle(get_front_client().search_conversations, q, limit=limit)
    return {"count": len(results), "results": results}


@router.get("/conversations/{conversation_id}")
def get_conversation_full(conversation_id: str):
    """Détail complet d'une conversation : metadata + messages + commentaires.

    C'est l'appel qu'utilisera l'assistant pour construire la vue d'une
    campagne (agréger la proposition, les échanges avec le client, et
    les commentaires internes de l'équipe).
    """
    client = get_front_client()
    return {
        "conversation": _handle(client.get_conversation, conversation_id),
        "messages":     _handle(client.list_messages,    conversation_id),
        "comments":     _handle(client.list_comments,    conversation_id),
    }
