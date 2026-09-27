"""Endpoints API pour les campagnes clients.

Une « campagne » c'est l'ensemble du travail actif pour un client
institutionnel (Place des Arts, Vincent-d'Indy, Orford…) : pianos,
conversations avec les responsables, commentaires internes, documents
liés. Cet endpoint est le premier étage — agrégation Front uniquement,
pour valider le pattern. Croisement avec Gazelle/Drive à venir.
"""
from fastapi import APIRouter, HTTPException, Query
import logging

from modules.campaigns.campaign_service import get_campaign_context

router = APIRouter(prefix="/campaigns", tags=["campaigns"])
_log = logging.getLogger(__name__)


@router.get("/{client_name}/context")
def campaign_context(
    client_name: str,
    max_conversations: int = Query(10, ge=1, le=50),
    max_recent_comments: int = Query(15, ge=1, le=50),
):
    """Aggrège Front (conversations + commentaires équipe) pour un client.

    Ex :
        GET /campaigns/Place%20des%20Arts/context
        GET /campaigns/Vincent-d%27Indy/context?max_conversations=20
    """
    try:
        return get_campaign_context(
            client_name=client_name,
            max_conversations=max_conversations,
            max_recent_comments_feed=max_recent_comments,
        )
    except ValueError as e:  # FRONT_API_KEY manquant
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        _log.exception("Erreur agrégation campagne %s", client_name)
        raise HTTPException(status_code=502, detail=f"Erreur agrégation Front: {e}")
