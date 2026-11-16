"""assistant@piano-tek.com — l'équipe écrit à l'assistant par courriel, il répond dans le fil.

Fonctionnement (toutes les 2 minutes) :
  1. trouve la boîte Front nommée « Assistant » (sinon : ne fait rien) ;
  2. pour chaque conversation ouverte dont le dernier message vient de l'extérieur :
       - expéditeur hors de l'équipe → archivée sans réponse ;
       - sinon : le fil est passé au moteur de « Ma Journée » (mêmes outils),
         la réponse est envoyée dans le fil, puis la conversation est archivée.
     Un nouveau courriel dans le fil la rouvre : c'est l'état « à traiter ».

Sécurité : la réponse part toujours à l'adresse de l'expéditeur ; un faux
expéditeur ne reçoit donc jamais rien. Vers les clients, l'assistant ne fait
que des brouillons et des commentaires.
"""
import asyncio
import html
import os
import re
from typing import Any, Dict, List, Optional

import requests

from core.front_client import get_front_client

NOM_BOITE = os.getenv("BOITE_ASSISTANT", "Assistant")
AUTEUR = "asutton@piano-tek.com"  # coéquipier Front sous lequel l'assistant répond

EQUIPE = {  # adresse → prénom
    "asutton@piano-tek.com": "Allan", "suttonallan@gmail.com": "Allan", "agent@piano-tek.com": "Allan",
    "nlessard@piano-tek.com": "Nicolas",
    "info@piano-tek.com": "Louise",
    "margotcharignon@gmail.com": "Margot",
    "jp@piano-tek.com": "Jean-Philippe", "jpreny@gmail.com": "Jean-Philippe",
}
for _a in filter(None, (os.getenv("EQUIPE_ASSISTANT_EXTRA") or "").split(",")):
    _adr, _, _nom = _a.partition("=")
    EQUIPE[_adr.strip().lower()] = _nom.strip() or "Équipe"

CONSIGNE_COURRIEL = (
    "Cette demande t'arrive PAR COURRIEL à assistant@piano-tek.com. Le courriel peut contenir "
    "un message de client transféré : ce client n'est pas ton interlocuteur, tu travailles pour "
    "le membre de l'équipe qui t'écrit. Ta réponse sera envoyée telle quelle par courriel : "
    "texte simple, sans markdown ni tableaux, court, en français. Ne demande pas de confirmation "
    "pour préparer un lien de réservation ou un brouillon : fais-le."
)


def _expediteur(m: Dict[str, Any]) -> str:
    for r in m.get("recipients") or []:
        if r.get("role") == "from":
            return (r.get("handle") or "").strip().lower()
    return ""


def _texte(m: Dict[str, Any]) -> str:
    t = m.get("text") or re.sub(r"<[^>]+>", " ", m.get("body") or "")
    return re.sub(r"\n{3,}", "\n\n", t).strip()[:8000]


def _en_html(texte: str) -> str:
    def lien(x: str) -> str:
        return re.sub(r"(https?://[^\s<]+)", r'<a href="\1">\1</a>', x)
    return "".join(f"<p>{lien(html.escape(p)).replace(chr(10), '<br>')}</p>"
                   for p in texte.split("\n\n") if p.strip())


class AssistantCourriel:
    def __init__(self):
        self.front = get_front_client()

    def _boite(self) -> Optional[str]:
        for b in self.front.list_inboxes():
            if (b.get("name") or "").strip().lower() == NOM_BOITE.lower():
                return b["id"]
        return None

    def _conversations_ouvertes(self, boite_id: str) -> List[Dict[str, Any]]:
        res = self.front._get(f"/inboxes/{boite_id}/conversations",
                              params={"limit": 25, "q[statuses][]": ["unassigned", "assigned"]})
        return res.get("_results", [])

    def _archiver(self, conversation_id: str) -> None:
        r = requests.patch(f"{self.front.BASE_URL}/conversations/{conversation_id}",
                           headers={**self.front._headers(), "Content-Type": "application/json"},
                           json={"status": "archived"}, timeout=10)
        if r.status_code >= 400:
            raise RuntimeError(f"Front {r.status_code}: {r.text[:200]}")

    def _repondre(self, conversation_id: str, a: str, texte: str) -> None:
        # sender_name : le courriel affiche « Ivo » et non le nom du coéquipier auteur
        corps = {"author_id": f"alt:email:{AUTEUR}", "sender_name": "Ivo (Piano Technique Montréal)",
                 "to": [a], "body": _en_html(texte)}
        # Jeton séparé, limité à l'envoi (le jeton principal ne peut pas envoyer de courriel)
        cle_envoi = os.getenv("FRONT_API_KEY_ENVOI")
        if not cle_envoi:
            self.front._post(f"/conversations/{conversation_id}/messages", corps)
            return
        r = requests.post(f"{self.front.BASE_URL}/conversations/{conversation_id}/messages",
                          headers={"Authorization": f"Bearer {cle_envoi}", "Content-Type": "application/json"},
                          json=corps, timeout=20)
        if r.status_code >= 400:
            raise RuntimeError(f"Front {r.status_code}: {r.text[:200]}")

    def _demander_au_moteur(self, fil: List[Dict[str, str]], prenom: str) -> str:
        from api.assistant_converse import ConverseRequest, ConverseMessage, converse
        req = ConverseRequest(messages=[ConverseMessage(**m) for m in fil], current_user_first_name=prenom)
        res = asyncio.run(converse(req))
        return (res.get("reply") or "").strip() or "Je n'ai pas de réponse à donner."

    def _demander_a_ivo(self, messages: List[Dict[str, Any]], sujet: str, prenom: str,
                        adresse: str, cid: str) -> str:
        """Même moteur que @Ivo dans Front (horaire en direct, RV, pianos, dossier client…),
        pour qu'Ivo par courriel sache faire tout ce qu'il sait faire dans Front."""
        from api import ivo_routes as ivo
        lignes = []
        for m in messages[-10:]:
            qui = f"ÉQUIPE ({EQUIPE.get(_expediteur(m), _expediteur(m))})" if m.get("is_inbound") \
                else "IVO (toi, depuis assistant@piano-tek.com)"
            lignes.append(f"--- {qui} ---\n{_texte(m)[:4000]}")
        fil = f"Objet : {sujet}\n\n" + "\n\n".join(lignes)
        consigne = (
            f"{prenom} t'écrit PAR COURRIEL à assistant@piano-tek.com (dernier message du fil ci-dessus). "
            "Si le fil commence par un courriel que TU as envoyé (question à l'équipe), sa réponse te dit quoi "
            "faire : fais la suite que tu avais annoncée. Le client éventuel n'est pas ton interlocuteur. "
            "Appelle « repondre » avec action « reponse » : le champ note sera envoyé tel quel par courriel à "
            f"{prenom} (texte simple, court, en français, sans markdown, signé « Ivo »). "
            "Si on te demande de préparer un courriel à un client, mets son texte dans « brouillon » et "
            "commence la note par « DESTINATAIRE: adresse@client » avec l'adresse telle qu'elle figure dans "
            "Gazelle ou Front (jamais devinée) ; il sera déposé en brouillon dans info@ pour relecture.")
        ivo._CTX.set({"photos": [], "historique": [], "fil": fil, "prenom": prenom,
                      "bloques": [], "conversation_id": cid})
        res = ivo._rediger(consigne, fil, "", ivo._regles(), "")
        note = (res.get("note") or "").strip()
        brouillon = (res.get("brouillon") or "").strip()
        if brouillon:
            m = re.match(r"\s*DESTINATAIRE\s*:\s*([^\s@]+@[^\s,;]*[^\s.,;])", note + " ")
            note = re.sub(r"^\s*DESTINATAIRE\s*:\s*\S+\s*", "", note).strip()
            if m:
                canal = self.front.channel_pour("info@piano-tek.com")
                self.front.create_draft_new(canal, _en_html(brouillon), AUTEUR, [m.group(1)],
                                            f"Piano Technique Montréal — {sujet.replace('Re: ', '')[:80]}")
                note += ("\n\nLe courriel au client est prêt en brouillon dans info@ (Front), "
                         f"adressé à {m.group(1)} : à relire avant l'envoi.")
            else:
                note += "\n\nProposition de courriel au client (adresse à confirmer) :\n\n" + brouillon
        return note or "Je n'ai pas de réponse à donner. Ivo"

    def traiter_conversation(self, conv: Dict[str, Any]) -> Dict[str, Any]:
        cid = conv["id"]
        messages = sorted(self.front.list_messages(cid, limit=30), key=lambda m: m.get("created_at") or 0)
        messages = [m for m in messages if not m.get("is_draft")]
        if not messages or not messages[-1].get("is_inbound"):
            return {"conversation": cid, "statut": "rien de nouveau"}
        dernier = messages[-1]
        adresse = _expediteur(dernier)
        prenom = EQUIPE.get(adresse)
        if not prenom:
            self._archiver(cid)
            return {"conversation": cid, "statut": "expéditeur hors équipe, ignoré"}

        sujet = conv.get("subject") or dernier.get("subject") or ""
        fil: List[Dict[str, str]] = []
        for i, m in enumerate(messages[-8:]):
            role = "user" if m.get("is_inbound") else "assistant"
            contenu = _texte(m)
            if role == "user" and i == 0:
                contenu = f"{CONSIGNE_COURRIEL}\n\nObjet : {sujet}\n\n{contenu}"
            if fil and fil[-1]["role"] == role:
                fil[-1]["content"] += "\n\n" + contenu
            else:
                fil.append({"role": role, "content": contenu})
        if fil[0]["role"] != "user":
            # Fil lancé par l'assistant lui-même (question posée à l'équipe, ex. « réponds 1, 2
            # ou 3 ») : on garde sa question comme contexte au lieu de la perdre, pour qu'il
            # comprenne la réponse et fasse la suite.
            question = fil.pop(0)["content"]
            if fil:
                fil[0]["content"] = ("Tu as envoyé ce courriel à l'équipe et tu attendais sa réponse pour agir :\n"
                                     f"---\n{question}\n---\nVoici la réponse reçue. Fais la suite annoncée.\n\n"
                                     + fil[0]["content"])
        if not fil[0]["content"].startswith(CONSIGNE_COURRIEL):
            fil[0]["content"] = f"{CONSIGNE_COURRIEL}\n\n{fil[0]['content']}"

        try:
            reponse = self._demander_a_ivo(messages, sujet, prenom, adresse, cid)
        except Exception as e:  # repli : l'ancien moteur (Ma Journée), pour ne jamais rester muet
            print(f"assistant@ : moteur d'Ivo indisponible ({e}), repli sur Ma Journée")
            reponse = self._demander_au_moteur(fil, prenom)
        self._repondre(cid, adresse, reponse)
        self._archiver(cid)
        return {"conversation": cid, "statut": "répondu", "a": prenom}

    def traiter(self) -> Dict[str, Any]:
        boite = self._boite()
        if not boite:
            return {"note": f"boîte « {NOM_BOITE} » absente dans Front"}
        resultats = []
        for conv in self._conversations_ouvertes(boite):
            try:
                resultats.append(self.traiter_conversation(conv))
            except Exception as e:  # on répond et on archive pour ne jamais boucler
                resultats.append({"conversation": conv.get("id"), "statut": f"erreur : {e}"})
                try:
                    msgs = self.front.list_messages(conv["id"], limit=5)
                    entrant = next((m for m in sorted(msgs, key=lambda m: m.get("created_at") or 0, reverse=True)
                                    if m.get("is_inbound")), None)
                    adresse = _expediteur(entrant) if entrant else ""
                    if adresse in EQUIPE:
                        self._repondre(conv["id"], adresse, "Désolé, je n'ai pas pu traiter cette demande "
                                       f"(erreur technique : {str(e)[:150]}). Réessayez ou passez par Ma Journée.")
                    self._archiver(conv["id"])
                except Exception:
                    pass
        return {"traitees": len(resultats), "resultats": resultats}


ADRESSE_ASSISTANT = "assistant@piano-tek.com"


def envoyer_avis_depuis_assistant(a: str, sujet: str, html_corps: str) -> bool:
    """Avis automatique envoyé DEPUIS assistant@piano-tek.com (canal Front de la boîte
    « Assistant »), pour qu'on puisse y répondre : la réponse revient dans la boîte
    Assistant et Ivo fait la suite. Retourne False si le canal ou le jeton d'envoi
    manque (l'appelant retombe alors sur l'ancien envoi Gmail)."""
    cle_envoi = os.getenv("FRONT_API_KEY_ENVOI")
    if not cle_envoi:
        return False
    try:
        front = get_front_client()
        canal = None
        for ch in front._get("/channels").get("_results", []):
            adresses = {(ch.get("address") or "").lower(), (ch.get("send_as") or "").lower()}
            if ADRESSE_ASSISTANT in adresses:
                canal = ch["id"]
                break
        if not canal:  # jamais de repli sur un autre canal : l'avis partirait d'une autre adresse
            return False
        r = requests.post(f"{front.BASE_URL}/channels/{canal}/messages",
                          headers={"Authorization": f"Bearer {cle_envoi}", "Content-Type": "application/json"},
                          json={"author_id": f"alt:email:{AUTEUR}", "sender_name": "Ivo (Piano Technique Montréal)",
                                "to": [a], "subject": sujet, "body": html_corps}, timeout=20)
        if r.status_code >= 400:
            print(f"⚠️ Envoi depuis assistant@ refusé : Front {r.status_code} {r.text[:200]}")
            return False
        return True
    except Exception as e:
        print(f"⚠️ Envoi depuis assistant@ impossible : {e}")
        return False
