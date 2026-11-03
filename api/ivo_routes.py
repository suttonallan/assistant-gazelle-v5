"""Ivo — l'assistant qu'on interpelle dans un commentaire Front.

Fonctionnement :
- Un membre de l'équipe écrit un commentaire interne qui COMMENCE par « @Ivo »
  dans une conversation Front (ex. « @Ivo plus court et plus chaleureux »).
- Une règle Front (« commentaire ajouté » → « envoyer au webhook ») appelle
  POST /api/front/ivo/webhook.
- Ivo relit le fil, réécrit le brouillon de réponse (ou en crée un s'il n'y en
  a pas), répond par un commentaire, et retient la consigne si c'est une règle
  générale (system_settings.ivo_regles_reponse).

Sécurité : le contenu du webhook n'est jamais cru sur parole. Ivo relit le
commentaire directement dans Front avec son propre jeton : seul un vrai
commentaire « @Ivo » d'un coéquipier déclenche quelque chose. Rien n'est
jamais envoyé : Ivo ne touche qu'aux brouillons et aux commentaires.
"""
import html
import json
import logging
import os
import re
import threading
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, Request

from core.front_client import get_front_client

router = APIRouter(prefix="/front/ivo", tags=["front-ivo"])
_log = logging.getLogger(__name__)

VERSION = "ivo-1"
MODELE = os.getenv("IVO_MODELE", "claude-sonnet-5-5")
CLE_REGLES = "ivo_regles_reponse"
PREFIXE_REPONSE = "🤖 Ivo : "
_DECLENCHEUR = re.compile(r"^\s*@?ivo\b[\s,:;.\-–—]*", re.IGNORECASE)

_deja_traites: set = set()          # commentaires déjà pris en charge (évite les doublons)
_verrou = threading.Lock()


# ─── Utilitaires ─────────────────────────────────────────────────

def _texte(html_ou_texte: str) -> str:
    """HTML Front → texte simple."""
    t = re.sub(r"<br\s*/?>|</p>|</div>", "\n", html_ou_texte or "", flags=re.IGNORECASE)
    t = html.unescape(re.sub(r"<[^>]+>", "", t))
    return re.sub(r"\n{3,}", "\n\n", t).strip()


def _en_html(texte: str) -> str:
    """Texte simple → paragraphes HTML (ligne vide = nouveau paragraphe)."""
    blocs = [b for b in re.split(r"\n\s*\n", texte.strip()) if b.strip()]
    return "".join("<p>" + "<br>".join(html.escape(l) for l in b.split("\n")) + "</p>" for b in blocs)


def consigne_ivo(corps: str) -> Optional[str]:
    """Retourne la consigne si le commentaire commence par @Ivo, sinon None."""
    t = _texte(corps)
    if t.startswith("🤖"):
        return None  # nos propres réponses
    m = _DECLENCHEUR.match(t)
    if not m:
        return None
    return t[m.end():].strip() or "Améliore ce brouillon."


def _regles() -> List[str]:
    try:
        from core.supabase_storage import SupabaseStorage
        val = SupabaseStorage(silent=True).get_system_setting(CLE_REGLES)
        if isinstance(val, str):
            val = json.loads(val)
        return list(val or [])
    except Exception:
        _log.exception("Ivo : lecture des règles impossible")
        return []


def _ajouter_regle(regle: str) -> bool:
    try:
        from core.supabase_storage import SupabaseStorage
        regles = _regles()
        if regle in regles:
            return True
        regles.append(regle)
        return SupabaseStorage(silent=True).save_system_setting(CLE_REGLES, regles)
    except Exception:
        _log.exception("Ivo : enregistrement de la règle impossible")
        return False


def _guide_ton() -> str:
    chemin = os.path.join(os.path.dirname(__file__), "..", "workspace", "guide-ton-ptm.md")
    try:
        with open(chemin, encoding="utf-8") as f:
            return f.read()[:6000]
    except OSError:
        return ""


# ─── Rédaction (Claude) ──────────────────────────────────────────

_SYSTEME = """Tu es Ivo, l'assistant de Piano Technique Montréal (PTM), entreprise d'accord et d'entretien de pianos.
Un membre de l'équipe te donne une consigne pour le brouillon de réponse à un client.
Règles absolues :
- N'invente JAMAIS un prix, des frais, une date, une disponibilité ou une règle qui n'est pas dans le fil ou dans les règles fournies. Si une information manque, garde-la entre crochets, ex. [prix à confirmer].
- Réponds dans la langue du client. Vouvoiement par défaut.
- Pas de signature dans le corps (Front l'ajoute) : termine par la formule de politesse seulement.
- Tu ne fais que préparer un brouillon : un humain le relira et l'enverra.
Réponds UNIQUEMENT en JSON : {"brouillon": "...", "regle_generale": "..." ou null, "note": "..."}
- brouillon : le texte complet du nouveau brouillon (texte simple, paragraphes séparés par une ligne vide).
- regle_generale : si la consigne vaut pour toutes les réponses futures (ton, longueur, façon de faire), formule-la en une phrase courte ; sinon null.
- note : une phrase pour l'équipe (ce que tu as changé, ou ce qui reste à vérifier)."""


def _rediger(consigne: str, fil: str, brouillon: str, regles: List[str]) -> Dict[str, Any]:
    from anthropic import Anthropic
    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    systeme = _SYSTEME
    if regles:
        systeme += "\n\nRègles de réponse déjà établies par l'équipe :\n" + "\n".join(f"- {r}" for r in regles)
    ton = _guide_ton()
    if ton:
        systeme += "\n\nGuide de ton de PTM (extrait) :\n" + ton
    contenu = (f"FIL DE LA CONVERSATION (du plus ancien au plus récent) :\n{fil}\n\n"
               f"BROUILLON ACTUEL :\n{brouillon or '(aucun — rédige une première réponse)'}\n\n"
               f"CONSIGNE DE L'ÉQUIPE :\n{consigne}")
    rep = client.messages.create(model=MODELE, max_tokens=2000, system=systeme,
                                 messages=[{"role": "user", "content": contenu}])
    brut = "".join(getattr(b, "text", "") for b in rep.content).strip()
    m = re.search(r"\{.*\}", brut, re.DOTALL)
    return json.loads(m.group(0) if m else brut)


# ─── Traitement ──────────────────────────────────────────────────

def _fil(messages: List[Dict]) -> str:
    lignes = []
    for m in sorted([m for m in messages if not m.get("is_draft")], key=lambda m: m.get("created_at") or 0):
        qui = "CLIENT" if m.get("is_inbound") else "PTM"
        auteur = ((m.get("author") or {}).get("email")) or ""
        lignes.append(f"--- {qui} {auteur} ---\n{_texte(m.get('text') or m.get('body') or '')[:4000]}")
    return "\n\n".join(lignes[-12:])


def traiter(conversation_id: str, comment_id: Optional[str]) -> Dict[str, Any]:
    front = get_front_client()
    commentaires = front.list_comments(conversation_id)
    # Le commentaire visé, relu dans Front (jamais celui du webhook)
    if comment_id:
        cibles = [c for c in commentaires if c.get("id") == comment_id]
    else:
        cibles = sorted(commentaires, key=lambda c: c.get("posted_at") or 0)[-1:]
    if not cibles:
        return {"statut": "ignoré", "raison": "commentaire introuvable"}
    com = cibles[0]
    consigne = consigne_ivo(com.get("body") or "")
    if consigne is None:
        return {"statut": "ignoré", "raison": "pas un commentaire @Ivo"}
    auteur_email = ((com.get("author") or {}).get("email") or "").lower()
    if not auteur_email:
        return {"statut": "ignoré", "raison": "auteur inconnu"}

    with _verrou:
        if com["id"] in _deja_traites:
            return {"statut": "ignoré", "raison": "déjà traité"}
        _deja_traites.add(com["id"])
    # Déjà répondu (après un redémarrage) : un commentaire Ivo plus récent existe
    if any(_texte(c.get("body") or "").startswith("🤖 Ivo")
           and (c.get("posted_at") or 0) > (com.get("posted_at") or 0) for c in commentaires):
        return {"statut": "ignoré", "raison": "déjà traité"}

    messages = front.list_messages(conversation_id)
    brouillons = sorted([m for m in messages if m.get("is_draft")], key=lambda m: m.get("created_at") or 0)
    brouillon = brouillons[-1] if brouillons else None
    texte_brouillon = _texte((brouillon or {}).get("text") or (brouillon or {}).get("body") or "")

    try:
        res = _rediger(consigne, _fil(messages), texte_brouillon, _regles())
        nouveau = (res.get("brouillon") or "").strip()
        if not nouveau:
            raise ValueError("brouillon vide")
    except Exception as e:
        _log.exception("Ivo : rédaction impossible")
        front.add_comment(conversation_id, f"{PREFIXE_REPONSE}je n'ai pas réussi à refaire le brouillon ({e}). "
                                           "Réessayez avec un nouveau commentaire @Ivo.", auteur_email)
        return {"statut": "erreur", "raison": str(e)}

    corps = _en_html(nouveau)
    canal = front._channel_de_conversation(conversation_id)
    if brouillon:
        front.edit_draft(brouillon["id"], brouillon.get("version"), corps, canal)
        action = "brouillon mis à jour"
    else:
        front.create_draft_reply(conversation_id, corps, auteur_email, mode="shared")
        action = "brouillon créé"

    reponse = f"{PREFIXE_REPONSE}{action}."
    if res.get("note"):
        reponse += f" {res['note']}"
    regle = (res.get("regle_generale") or "").strip()
    if regle and _ajouter_regle(regle):
        reponse += f" Règle retenue pour les prochaines fois : « {regle} »"
    front.add_comment(conversation_id, reponse, auteur_email)
    return {"statut": "ok", "action": action, "regle": regle or None}


def _ids_du_webhook(evt: Dict[str, Any]) -> Dict[str, Optional[str]]:
    """Accepte les formes d'événement Front (règle « envoyer au webhook », application)."""
    p = evt.get("payload") if isinstance(evt.get("payload"), dict) else evt
    conv = p.get("conversation") or {}
    cible = (p.get("target") or {}).get("data") or {}
    cid = conv.get("id") or p.get("conversation_id")
    if not cid:
        lien = ((cible.get("_links") or {}).get("related") or {}).get("conversation") or ""
        cid = lien.rstrip("/").rsplit("/", 1)[-1] or None
    com = cible.get("id") if str(cible.get("id", "")).startswith("com_") else p.get("comment_id")
    return {"conversation_id": cid, "comment_id": com}


def _traiter_sans_erreur(conversation_id: str, comment_id: Optional[str]) -> None:
    try:
        _log.info("Ivo : %s", traiter(conversation_id, comment_id))
    except Exception:
        _log.exception("Ivo : échec du traitement")


# ─── Endpoints ───────────────────────────────────────────────────

@router.post("/webhook")
async def webhook(request: Request, background_tasks: BackgroundTasks):
    """Reçoit l'événement Front et répond tout de suite ; le travail se fait en arrière-plan."""
    try:
        evt = await request.json()
    except Exception:
        return {"ok": True, "ignoré": "corps illisible"}
    ids = _ids_du_webhook(evt if isinstance(evt, dict) else {})
    if not ids["conversation_id"] or not str(ids["conversation_id"]).startswith("cnv_"):
        return {"ok": True, "ignoré": "conversation absente"}
    background_tasks.add_task(_traiter_sans_erreur, ids["conversation_id"], ids["comment_id"])
    return {"ok": True}


@router.get("/sante")
def sante():
    return {"ok": True, "version": VERSION, "modele": MODELE,
            "cle_ia": bool(os.getenv("ANTHROPIC_API_KEY")), "cle_front": bool(os.getenv("FRONT_API_KEY"))}


@router.get("/regles")
def regles():
    """Règles de réponse retenues par Ivo au fil des consignes."""
    return {"regles": _regles()}
