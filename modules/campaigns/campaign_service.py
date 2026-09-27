"""Service d'agrégation des campagnes clients.

Pour un client donné (institutionnel principalement — PDA, Vincent-d'Indy,
Orford), aggrège en un seul appel :
  - Les conversations Front qui parlent de ce client (recherche full-text)
  - Les commentaires internes de l'équipe sur ces conversations
  - Un feed « activité récente » (les N derniers commentaires équipe, tous
    thèmes confondus)

C'est le premier étage de la vue « Campagne » de la maquette Tâches Gazelle
— l'idée étant qu'on ne fait plus jamais chercher qui a dit quoi à qui à
notre équipe : c'est déjà agrégé sur la carte du client.

Prochaine étape (pas encore ici) : croiser avec les pianos Gazelle + les
documents Drive liés au client (proposition, PO, plan quinquennal).
"""
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional

from core.front_client import get_front_client


def _normalize_comment(raw: Dict, conversation_meta: Optional[Dict] = None) -> Dict:
    """Ramène un commentaire Front à un format simple et prêt pour le front-end."""
    author = raw.get("author") or {}
    posted_at = raw.get("posted_at")
    if posted_at:
        # Front renvoie un Unix timestamp (float). On normalise en ISO.
        posted_iso = datetime.fromtimestamp(posted_at, tz=timezone.utc).isoformat()
    else:
        posted_iso = None
    out = {
        "id": raw.get("id"),
        "author_name": author.get("first_name", "") + " " + author.get("last_name", ""),
        "author_email": author.get("email"),
        "posted_at": posted_iso,
        "text": raw.get("body") or "",
    }
    out["author_name"] = out["author_name"].strip() or (author.get("email") or "?")
    if conversation_meta:
        out["conversation_id"] = conversation_meta.get("id")
        out["conversation_subject"] = conversation_meta.get("subject")
    return out


def _normalize_conversation(raw: Dict) -> Dict:
    """Format court d'une conversation, avec participants extraits proprement."""
    recipients = raw.get("recipients") or []
    participants = [r.get("handle") for r in recipients if r.get("handle")]
    last_msg = raw.get("last_message") or {}
    created_at = last_msg.get("created_at")
    last_iso = (
        datetime.fromtimestamp(created_at, tz=timezone.utc).isoformat()
        if created_at else None
    )
    return {
        "id": raw.get("id"),
        "subject": raw.get("subject") or "(sans sujet)",
        "status": raw.get("status"),
        "participants": participants,
        "last_message_at": last_iso,
    }


def get_campaign_context(
    client_name: str,
    max_conversations: int = 10,
    max_comments_per_conv: int = 20,
    max_recent_comments_feed: int = 15,
) -> Dict[str, Any]:
    """Aggrège le contexte Front pour un client donné.

    Args:
        client_name: nom du client à chercher (ex. « Place des Arts »,
            « Vincent-d'Indy », « Orford »).
        max_conversations: nombre max de conversations à ramener (Front
            plafonne à 100 par page).
        max_comments_per_conv: coupe les commentaires par conversation à
            ce nombre (les plus récents en premier chez Front).
        max_recent_comments_feed: nombre d'items dans le feed « activité
            récente équipe » (tous thèmes confondus).

    Returns:
        Un dict prêt à être renvoyé par un endpoint FastAPI :

            {
              "client": "Place des Arts",
              "conversation_count": 10,
              "conversations": [
                {
                  "id", "subject", "status", "participants",
                  "last_message_at",
                  "comment_count", "comments": [...]
                }
              ],
              "recent_team_comments": [
                {author_name, posted_at, text,
                 conversation_id, conversation_subject}
              ]
            }
    """
    client = get_front_client()

    convs_raw = client.search_conversations(client_name, limit=max_conversations)

    conversations: List[Dict] = []
    all_comments: List[Dict] = []

    for c in convs_raw:
        conv_meta = _normalize_conversation(c)
        try:
            comments_raw = client.list_comments(c["id"], limit=max_comments_per_conv)
        except Exception:
            # Une conversation qui refuse ses commentaires ne bloque pas l'ensemble.
            comments_raw = []
        comments = [_normalize_comment(cm, conversation_meta=conv_meta) for cm in comments_raw]
        conv_meta["comment_count"] = len(comments)
        conv_meta["comments"] = comments
        conversations.append(conv_meta)
        all_comments.extend(comments)

    # Feed « activité récente » : les N derniers commentaires équipe, tous
    # threads confondus, plus récent en premier.
    all_comments.sort(key=lambda c: c.get("posted_at") or "", reverse=True)
    recent_feed = all_comments[:max_recent_comments_feed]

    return {
        "client": client_name,
        "conversation_count": len(conversations),
        "conversations": conversations,
        "recent_team_comments": recent_feed,
    }
