"""Endpoints API pour Front (frontapp.com).

Expose la lecture des conversations, messages et commentaires internes
via l'API Front. Enregistré deux fois dans `api/main.py` — sans prefix
(dev, Vite proxy) et avec `/api` prefix (prod Render).
"""
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
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


# ─── Écriture : commentaires internes et brouillons (rien n'est envoyé) ───
EQUIPE_FRONT = {"allan": "asutton@piano-tek.com", "nicolas": "nlessard@piano-tek.com", "louise": "info@piano-tek.com"}


class CommentaireIn(BaseModel):
    texte: str = Field(..., min_length=1, max_length=5000)
    auteur: str = "allan"
    par_ia: bool = True  # signe « Claude IA » : l'équipe sait que ce n'est pas Allan qui tape

SIGNATURE_IA = "🤖 Claude IA (pour {nom}) : "


class BrouillonIn(BaseModel):
    remplacer: bool = False  # supprime d'abord les brouillons existants de cet auteur dans la conversation
    texte: str = Field(..., min_length=1, max_length=20000)
    auteur: str = "allan"
    a: Optional[List[str]] = None
    cc: Optional[List[str]] = None
    sujet: Optional[str] = None


def _email_auteur(auteur: str) -> str:
    if auteur not in EQUIPE_FRONT:
        raise HTTPException(400, f"auteur inconnu (attendu : {', '.join(EQUIPE_FRONT)})")
    return EQUIPE_FRONT[auteur]


@router.post("/conversations/{conversation_id}/commentaires")
def ajouter_commentaire(conversation_id: str, c: CommentaireIn):
    """Commentaire interne dans une conversation (visible de l'équipe seulement)."""
    texte = c.texte
    if c.par_ia:
        texte = SIGNATURE_IA.format(nom=c.auteur.capitalize()) + texte
    return _handle(get_front_client().add_comment, conversation_id, texte, _email_auteur(c.auteur))


@router.post("/conversations/{conversation_id}/brouillon")
def creer_brouillon(conversation_id: str, b: BrouillonIn):
    """Brouillon de réponse partagé, à relire et envoyer depuis Front (jamais envoyé ici)."""
    client = get_front_client()
    email = _email_auteur(b.auteur)
    if b.remplacer:  # modifie le brouillon existant de cet auteur (le jeton n'a pas le droit de supprimer)
        for d in _handle(client.list_drafts, conversation_id):
            if ((d.get("author") or {}).get("email") or "").lower() == email:
                canal = _handle(client._channel_de_conversation, conversation_id)
                return _handle(client.edit_draft, d["id"], d.get("version"), b.texte, canal,
                               subject=b.sujet, to=b.a, cc=b.cc)
    return _handle(get_front_client().create_draft_reply, conversation_id, b.texte,
                   _email_auteur(b.auteur), to=b.a, cc=b.cc, subject=b.sujet)



class NouveauCourrielIn(BaseModel):
    a: List[str]
    sujet: str = Field(..., min_length=1, max_length=300)
    texte: str = Field(..., min_length=1, max_length=20000)
    cc: Optional[List[str]] = None
    auteur: str = "allan"


@router.post("/brouillon-nouveau")
def creer_brouillon_nouveau(b: NouveauCourrielIn):
    """Brouillon d'un nouveau courriel dans Front, à relire et envoyer depuis Front (jamais envoyé ici)."""
    client = get_front_client()
    email = _email_auteur(b.auteur)
    canal = _handle(client.channel_pour, email)
    if not canal:
        raise HTTPException(502, "Aucune boîte d'envoi trouvée dans Front")
    return _handle(client.create_draft_new, canal, b.texte, email, b.a, b.sujet, b.cc)
