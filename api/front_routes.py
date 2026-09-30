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
EQUIPE_FRONT = {"allan": "asutton@piano-tek.com", "nicolas": "nlessard@piano-tek.com", "louise": "info@piano-tek.com",
                "margot": "margotcharignon@gmail.com"}


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
    prive: bool = True  # visible seulement par l'auteur dans Front (False = toute l'équipe le voit)


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
        # Brouillons de la conversation : ceux de l'auteur, ou ceux créés par l'API (auteur « api_jwt… »)
        brouillons = [m for m in _handle(client.list_messages, conversation_id) if m.get("is_draft")]
        for d in brouillons:
            auteur = ((d.get("author") or {}).get("email") or "").lower()
            if auteur == email or auteur.startswith("api_jwt"):
                canal = _handle(client._channel_de_conversation, conversation_id)
                return _handle(client.edit_draft, d["id"], d.get("version"), b.texte, canal,
                               subject=b.sujet, to=b.a, cc=b.cc)
    return _handle(get_front_client().create_draft_reply, conversation_id, b.texte,
                   _email_auteur(b.auteur), to=b.a, cc=b.cc, subject=b.sujet,
                   mode="private" if b.prive else "shared")



class NouveauCourrielIn(BaseModel):
    a: List[str]
    sujet: str = Field(..., min_length=1, max_length=300)
    texte: str = Field(..., min_length=1, max_length=20000)
    cc: Optional[List[str]] = None
    auteur: str = "allan"
    prive: bool = True  # visible seulement par l'auteur dans Front (False = toute l'équipe le voit)


@router.post("/brouillon-nouveau")
def creer_brouillon_nouveau(b: NouveauCourrielIn):
    """Brouillon d'un nouveau courriel dans Front, à relire et envoyer depuis Front (jamais envoyé ici)."""
    client = get_front_client()
    email = _email_auteur(b.auteur)
    canal = _handle(client.channel_pour, email)
    if not canal:
        raise HTTPException(502, "Aucune boîte d'envoi trouvée dans Front")
    return _handle(client.create_draft_new, canal, b.texte, email, b.a, b.sujet, b.cc,
                   "private" if b.prive else "shared")



class DiscussionIn(BaseModel):
    avec: List[str]  # membres de l'équipe : margot, nicolas, louise…
    sujet: str = Field(..., min_length=1, max_length=300)
    texte: str = Field(..., min_length=1, max_length=5000)
    auteur: str = "allan"
    par_ia: bool = True


@router.post("/discussion")
def creer_discussion(d: DiscussionIn):
    """Discussion interne Front avec des membres de l'équipe (plutôt qu'un courriel). Publiée tout de suite."""
    membres = [_email_auteur(m) for m in d.avec]
    texte = (SIGNATURE_IA.format(nom=d.auteur.capitalize()) + d.texte) if d.par_ia else d.texte
    return _handle(get_front_client().create_discussion, d.sujet, texte, _email_auteur(d.auteur),
                   sorted(set(membres + [_email_auteur(d.auteur)])))



@router.get("/contact-fils")
def fils_contact(email: str = Query(..., min_length=5), page: Optional[str] = None,
                 limite: int = Query(20, ge=1, le=50)):
    """LECTURE SEULE — conversations d'un contact avec messages et commentaires (texte abrégé).
    Sert aux analyses (ex. questions restées sans réponse). Paginer avec « page »."""
    import time as _t
    client = get_front_client()
    lot = _handle(client.conversations_contact, email, page, limite)
    fils = []
    for c in lot["conversations"]:
        try:
            msgs = client.list_messages(c["id"], limit=100)
            coms = client.list_comments(c["id"], limit=100)
        except Exception as e:  # noqa: BLE001
            fils.append({"id": c["id"], "sujet": c.get("subject"), "erreur": str(e)[:200]})
            continue
        fils.append({
            "id": c["id"], "sujet": c.get("subject"), "cree": c.get("created_at"),
            "messages": [{
                "t": m.get("created_at"), "entrant": m.get("is_inbound"), "brouillon": m.get("is_draft"),
                "de": next((r.get("handle") for r in m.get("recipients", []) if r.get("role") == "from"), None),
                "a": [r.get("handle") for r in m.get("recipients", []) if r.get("role") in ("to", "cc")],
                "texte": (m.get("text") or m.get("blurb") or "")[:2500],
            } for m in msgs],
            "commentaires": [{
                "t": x.get("posted_at"), "auteur": ((x.get("author") or {}).get("email")),
                "texte": (x.get("body") or "")[:1500],
            } for x in coms],
        })
        _t.sleep(0.3)  # ménage la limite de débit Front
    return {"fils": fils, "page_suivante": lot["page_suivante"]}
