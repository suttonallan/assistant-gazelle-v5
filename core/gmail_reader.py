#!/usr/bin/env python3
"""
Module de lecture des emails Gmail (info@piano-tek.com).

Utilise le même token OAuth2 que gmail_sender.py.
Permet de lire les emails entrants, chercher par sujet, expéditeur, etc.
"""

import os
import json
import base64
from typing import Optional, List
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime

try:
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
except ImportError:
    Credentials = None

SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.readonly",
]

_MODULE_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_DIR = os.path.dirname(_MODULE_DIR)
_TOKEN_FILE = os.path.join(_PROJECT_DIR, "config", "gmail-token.json")


class GmailReader:
    """Lit les emails entrants via Gmail API."""

    def __init__(self):
        self.service = None
        self.email_address = None
        self._init_service()

    def _load_token_data(self) -> Optional[dict]:
        """Charge le token depuis Supabase, env, ou fichier local."""
        # 1. Supabase
        try:
            from core.supabase_storage import get_supabase_storage
            storage = get_supabase_storage()
            result = storage.client.table("system_settings").select("value").eq("key", "GMAIL_TOKEN_JSON").execute()
            if result.data and result.data[0].get("value"):
                data = result.data[0]["value"]
                if isinstance(data, str):
                    data = json.loads(data)
                return data
        except Exception:
            pass

        # 2. Variable d'environnement
        env_token = os.getenv("GMAIL_TOKEN_JSON")
        if env_token:
            try:
                return json.loads(env_token)
            except json.JSONDecodeError:
                pass

        # 3. Fichier local
        if os.path.exists(_TOKEN_FILE):
            with open(_TOKEN_FILE, "r") as f:
                return json.load(f)

        return None

    def _init_service(self):
        """Initialise le service Gmail API."""
        if Credentials is None:
            print("⚠️ Gmail Reader non disponible (dépendances manquantes)")
            return

        token_data = self._load_token_data()
        if not token_data:
            print("⚠️ Gmail token non trouvé — lecture emails désactivée")
            return

        try:
            creds = Credentials.from_authorized_user_info(token_data, SCOPES)
            if creds.expired and creds.refresh_token:
                creds.refresh(Request())

            self.service = build("gmail", "v1", credentials=creds)
            profile = self.service.users().getProfile(userId="me").execute()
            self.email_address = profile.get("emailAddress")
            print(f"✅ Gmail Reader initialisé — {self.email_address}")
        except Exception as e:
            print(f"❌ Erreur initialisation Gmail Reader : {e}")

    @property
    def is_available(self) -> bool:
        return self.service is not None

    def lire_emails(
        self,
        max_results: int = 10,
        query: Optional[str] = None,
        non_lus_seulement: bool = False,
    ) -> List[dict]:
        """
        Lit les emails entrants.

        Args:
            max_results: Nombre max d'emails à retourner
            query: Recherche Gmail (ex: "from:client@example.com", "subject:facture")
            non_lus_seulement: Si True, retourne seulement les non-lus

        Returns:
            Liste de dicts avec: id, date, from, to, subject, snippet, body, is_unread
        """
        if not self.service:
            return []

        q_parts = []
        if query:
            q_parts.append(query)
        if non_lus_seulement:
            q_parts.append("is:unread")
        q = " ".join(q_parts) if q_parts else None

        try:
            params = {"userId": "me", "maxResults": max_results}
            if q:
                params["q"] = q

            results = self.service.users().messages().list(**params).execute()
            messages = results.get("messages", [])

            emails = []
            for msg_ref in messages:
                email_data = self._lire_email_detail(msg_ref["id"])
                if email_data:
                    emails.append(email_data)

            return emails

        except Exception as e:
            print(f"❌ Erreur lecture emails : {e}")
            return []

    def _lire_email_detail(self, message_id: str) -> Optional[dict]:
        """Lit le détail d'un email."""
        try:
            msg = self.service.users().messages().get(
                userId="me", id=message_id, format="full"
            ).execute()

            headers = {h["name"].lower(): h["value"] for h in msg.get("payload", {}).get("headers", [])}

            # Extraire le body
            body = self._extraire_body(msg.get("payload", {}))

            return {
                "id": message_id,
                "date": headers.get("date", ""),
                "from": headers.get("from", ""),
                "to": headers.get("to", ""),
                "subject": headers.get("subject", ""),
                "snippet": msg.get("snippet", ""),
                "body": body,
                "is_unread": "UNREAD" in msg.get("labelIds", []),
                "labels": msg.get("labelIds", []),
            }
        except Exception as e:
            print(f"⚠️ Erreur lecture email {message_id} : {e}")
            return None

    def _extraire_body(self, payload: dict) -> str:
        """Extrait le contenu texte d'un email."""
        # Email simple
        if payload.get("body", {}).get("data"):
            return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="replace")

        # Email multipart
        for part in payload.get("parts", []):
            mime = part.get("mimeType", "")
            if mime == "text/plain" and part.get("body", {}).get("data"):
                return base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="replace")
            if mime == "text/html" and part.get("body", {}).get("data"):
                return base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="replace")
            # Multipart imbriqué
            if part.get("parts"):
                result = self._extraire_body(part)
                if result:
                    return result

        return ""

    def chercher_emails(
        self,
        de: Optional[str] = None,
        sujet: Optional[str] = None,
        depuis_jours: int = 7,
        max_results: int = 20,
    ) -> List[dict]:
        """
        Recherche d'emails avec filtres simples.

        Args:
            de: Filtrer par expéditeur
            sujet: Filtrer par sujet
            depuis_jours: Chercher dans les X derniers jours
            max_results: Nombre max de résultats

        Returns:
            Liste d'emails
        """
        q_parts = []
        if de:
            q_parts.append(f"from:{de}")
        if sujet:
            q_parts.append(f"subject:{sujet}")
        if depuis_jours:
            date_str = (datetime.now() - timedelta(days=depuis_jours)).strftime("%Y/%m/%d")
            q_parts.append(f"after:{date_str}")

        query = " ".join(q_parts) if q_parts else None
        return self.lire_emails(max_results=max_results, query=query)

    def compter_non_lus(self) -> int:
        """Retourne le nombre d'emails non lus."""
        if not self.service:
            return 0
        try:
            results = self.service.users().messages().list(
                userId="me", q="is:unread", maxResults=1
            ).execute()
            return results.get("resultSizeEstimate", 0)
        except Exception:
            return 0

    def marquer_comme_lu(self, message_id: str) -> bool:
        """Marque un email comme lu."""
        if not self.service:
            return False
        try:
            self.service.users().messages().modify(
                userId="me",
                id=message_id,
                body={"removeLabelIds": ["UNREAD"]},
            ).execute()
            return True
        except Exception as e:
            print(f"⚠️ Erreur marquer comme lu : {e}")
            return False


# Singleton
_gmail_reader: Optional[GmailReader] = None


def get_gmail_reader() -> GmailReader:
    """Retourne l'instance GmailReader (singleton)."""
    global _gmail_reader
    if _gmail_reader is None:
        _gmail_reader = GmailReader()
    return _gmail_reader
