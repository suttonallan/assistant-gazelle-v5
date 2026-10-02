"""Client API pour Front (frontapp.com).

Wrapper minimal de l'API Front pour lire les conversations, messages et
commentaires internes de l'équipe. Utilisé par l'assistant pour aggréger
le contexte client (proposition, PO, échanges, notes internes) sur les
cartes de campagne.

Singleton — initialisé à la première demande via `get_front_client()`,
sur le même modèle que `GazelleAPIClient` et `SupabaseStorage`.

Config :
    FRONT_API_KEY dans le .env (obtenu depuis Front → Settings →
    Developers → API tokens).

Doc API : https://dev.frontapp.com/reference/introduction
"""
import os
import logging
from typing import List, Dict, Optional, Any
from urllib.parse import quote

import requests


class FrontClient:
    """Client léger de l'API Front (lecture)."""

    BASE_URL = "https://api2.frontapp.com"

    def __init__(self, api_key: Optional[str] = None, timeout: int = 10):
        self.api_key = api_key or os.getenv("FRONT_API_KEY")
        if not self.api_key:
            raise ValueError(
                "FRONT_API_KEY est requis (env var ou paramètre). "
                "Créer un token sur Front → Settings → Developers → API tokens."
            )
        self.timeout = timeout
        self._log = logging.getLogger(__name__)

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
        }

    def _get(self, path: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        url = f"{self.BASE_URL}{path}"
        resp = requests.get(url, headers=self._headers(), params=params, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

    def _post(self, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self.BASE_URL}{path}"
        headers = {**self._headers(), "Content-Type": "application/json"}
        resp = requests.post(url, headers=headers, json=payload, timeout=self.timeout)
        if resp.status_code >= 400:
            raise RuntimeError(f"Front {resp.status_code}: {resp.text[:300]}")
        return resp.json() if resp.text else {}

    # ─── Endpoints ────────────────────────────────────────────────

    def me(self) -> Dict:
        """Retourne le teammate propriétaire du token — test de connectivité."""
        return self._get("/me")

    def list_teammates(self) -> List[Dict]:
        """Liste tous les teammates du workspace."""
        return self._get("/teammates").get("_results", [])

    def list_inboxes(self) -> List[Dict]:
        """Liste les inboxes accessibles au token."""
        return self._get("/inboxes").get("_results", [])

    def search_conversations(self, query: str, limit: int = 25) -> List[Dict]:
        """Recherche full-text dans toutes les conversations accessibles.

        Args:
            query: mot-clé ou phrase (ex. 'Place des Arts', 'Julio Gonzalo').
            limit: nombre max de résultats (Front plafonne à 100 par page).

        Returns:
            Liste des conversations trouvées (structures Front standard).
        """
        path = f"/conversations/search/{quote(query, safe='')}"
        return self._get(path, params={"limit": min(limit, 100)}).get("_results", [])

    def conversations_contact(self, email: str, page_token: Optional[str] = None, limit: int = 25) -> Dict:
        """Conversations d'un contact (par adresse), les plus récentes d'abord, page par page."""
        params: Dict[str, Any] = {"limit": min(limit, 100)}
        if page_token:
            params["page_token"] = page_token
        data = self._get(f"/contacts/alt:email:{quote(email, safe='@')}/conversations", params=params)
        suivant = ((data.get("_pagination") or {}).get("next") or "")
        jeton = None
        if "page_token=" in suivant:
            from urllib.parse import urlparse, parse_qs
            jeton = (parse_qs(urlparse(suivant).query).get("page_token") or [None])[0]
        return {"conversations": data.get("_results", []), "page_suivante": jeton}

    def get_conversation(self, conversation_id: str) -> Dict:
        """Détail d'une conversation (metadata, participants, statut)."""
        return self._get(f"/conversations/{conversation_id}")

    def list_messages(self, conversation_id: str, limit: int = 50) -> List[Dict]:
        """Liste les messages échangés dans une conversation."""
        return self._get(
            f"/conversations/{conversation_id}/messages",
            params={"limit": min(limit, 100)},
        ).get("_results", [])

    def list_comments(self, conversation_id: str, limit: int = 50) -> List[Dict]:
        """Liste les commentaires internes de l'équipe sur une conversation.

        C'est la source des ajouts de scope, décisions d'équipe, notes
        entre techs qui n'apparaissent nulle part ailleurs.
        """
        return self._get(
            f"/conversations/{conversation_id}/comments",
            params={"limit": min(limit, 100)},
        ).get("_results", [])

    # ─── Écriture (jamais d'envoi direct : commentaires internes et brouillons) ───

    def add_comment(self, conversation_id: str, body: str, author_email: str) -> Dict:
        """Ajoute un commentaire interne (visible de l'équipe seulement)."""
        return self._post(f"/conversations/{conversation_id}/comments",
                          {"author_id": f"alt:email:{author_email}", "body": body})

    def ajouter_abonnes(self, conversation_id: str, emails: List[str]) -> None:
        """Abonne des coéquipiers à une conversation : ils sont notifiés des nouveaux commentaires."""
        if emails:
            self._post(f"/conversations/{conversation_id}/followers",
                       {"teammate_ids": [f"alt:email:{e}" for e in emails]})

    def create_discussion(self, subject: str, body: str, author_email: str,
                          teammate_emails: List[str]) -> Dict:
        """Discussion INTERNE (conversation d'équipe, pas un courriel) avec un premier commentaire."""
        return self._post("/conversations", {
            "type": "discussion",
            "subject": subject,
            "teammate_ids": [f"alt:email:{e}" for e in teammate_emails],
            "comment": {"author_id": f"alt:email:{author_email}", "body": body},
        })

    def _channel_de_conversation(self, conversation_id: str) -> Optional[str]:
        inboxes = self._get(f"/conversations/{conversation_id}/inboxes").get("_results", [])
        for inbox in inboxes:
            chans = self._get(f"/inboxes/{inbox['id']}/channels").get("_results", [])
            for ch in chans:
                if ch.get("type") in ("gmail", "imap", "smtp", "email", "office365", "custom"):
                    return ch["id"]
            if chans:
                return chans[0]["id"]
        return None

    def create_draft_reply(self, conversation_id: str, body: str, author_email: str,
                           to: Optional[List[str]] = None, cc: Optional[List[str]] = None,
                           subject: Optional[str] = None, mode: str = "shared") -> Dict:
        """Crée un BROUILLON de réponse dans la conversation (non envoyé). mode : private | shared."""
        payload: Dict[str, Any] = {
            "author_id": f"alt:email:{author_email}",
            "body": body,
            "mode": mode,
        }
        channel = self._channel_de_conversation(conversation_id)
        if channel:
            payload["channel_id"] = channel
        if to:
            payload["to"] = to
        if cc:
            payload["cc"] = cc
        if subject:
            payload["subject"] = subject
        return self._post(f"/conversations/{conversation_id}/drafts", payload)

    def channel_pour(self, email: str) -> Optional[str]:
        """Canal d'envoi (boîte) correspondant à une adresse ; sinon le premier canal courriel."""
        chans = self._get("/channels").get("_results", [])
        for ch in chans:
            if (ch.get("address") or "").lower() == email.lower():
                return ch["id"]
        for ch in chans:
            if ch.get("type") in ("gmail", "imap", "smtp", "email", "office365"):
                return ch["id"]
        return chans[0]["id"] if chans else None

    def send_new_message(self, channel_id: str, to: str, subject: str, body: str, author_email: str) -> Dict:
        """ENVOIE un courriel (pas un brouillon). Réservé aux avis internes déclenchés par un clic
        explicite d'un membre de l'équipe (ex. bouton « Aviser » vers un tech sans compte Front)."""
        import html
        corps = "".join(f"<p>{html.escape(l)}</p>" for l in body.split("\n") if l.strip())
        res = self._post(f"/channels/{channel_id}/messages",
                         {"to": [to], "subject": subject, "body": corps, "author_id": f"alt:email:{author_email}"})
        # Front répond 202 avec l'identifiant du message ; la conversation n'est connue qu'après coup
        return {"id": (res.get("_links", {}).get("related", {}).get("conversation", "") or "").rsplit("/", 1)[-1] or None,
                "message_uid": res.get("message_uid")}

    def create_draft_new(self, channel_id: str, body: str, author_email: str, to: List[str],
                         subject: str, cc: Optional[List[str]] = None, mode: str = "shared") -> Dict:
        """BROUILLON d'un nouveau courriel (nouvelle conversation), non envoyé. mode : private | shared."""
        payload: Dict[str, Any] = {"author_id": f"alt:email:{author_email}", "body": body,
                                   "to": to, "subject": subject, "mode": mode}
        if cc:
            payload["cc"] = cc
        return self._post(f"/channels/{channel_id}/drafts", payload)

    def list_drafts(self, conversation_id: str) -> List[Dict]:
        return self._get(f"/conversations/{conversation_id}/drafts").get("_results", [])

    def edit_draft(self, draft_id: str, version: str, body: str, channel_id: Optional[str],
                   subject: Optional[str] = None, to: Optional[List[str]] = None,
                   cc: Optional[List[str]] = None) -> Dict:
        payload: Dict[str, Any] = {"body": body, "version": version, "mode": "shared"}
        if channel_id:
            payload["channel_id"] = channel_id
        if subject:
            payload["subject"] = subject
        if to:
            payload["to"] = to
        if cc:
            payload["cc"] = cc
        url = f"{self.BASE_URL}/drafts/{draft_id}/"
        headers = {**self._headers(), "Content-Type": "application/json"}
        resp = requests.patch(url, headers=headers, json=payload, timeout=self.timeout)
        if resp.status_code >= 400:
            raise RuntimeError(f"Front {resp.status_code}: {resp.text[:300]}")
        return resp.json() if resp.text else {"ok": True}

    def delete_draft(self, draft_id: str, version: str) -> None:
        url = f"{self.BASE_URL}/drafts/{draft_id}"
        headers = {**self._headers(), "Content-Type": "application/json"}
        resp = requests.delete(url, headers=headers, json={"version": version}, timeout=self.timeout)
        if resp.status_code >= 400:
            raise RuntimeError(f"Front {resp.status_code}: {resp.text[:300]}")


# ─── Singleton ────────────────────────────────────────────────────

_client: Optional[FrontClient] = None


def get_front_client() -> FrontClient:
    """Retourne l'instance singleton du client Front (initialisation paresseuse)."""
    global _client
    if _client is None:
        _client = FrontClient()
    return _client
