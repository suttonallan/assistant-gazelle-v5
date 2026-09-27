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


# ─── Singleton ────────────────────────────────────────────────────

_client: Optional[FrontClient] = None


def get_front_client() -> FrontClient:
    """Retourne l'instance singleton du client Front (initialisation paresseuse)."""
    global _client
    if _client is None:
        _client = FrontClient()
    return _client
