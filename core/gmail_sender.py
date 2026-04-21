#!/usr/bin/env python3
"""
Module d'envoi d'emails via Gmail API (OAuth2).

Utilise le refresh token généré par scripts/gmail_auth_setup.py.
Cherche le token dans cet ordre :
1. Supabase system_settings (clé GMAIL_TOKEN_JSON) — production
2. Variable d'environnement GMAIL_TOKEN_JSON — CI/CD
3. Fichier config/gmail-token.json — développement local
"""

import os
import sys
import json
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, List

try:
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
except ImportError:
    print("⚠️ google-auth / google-api-python-client non installé")
    Credentials = None

SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.readonly",
]

# Chemins
_MODULE_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_DIR = os.path.dirname(_MODULE_DIR)
_TOKEN_FILE = os.path.join(_PROJECT_DIR, "config", "gmail-token.json")


class GmailSender:
    """Envoie des emails via Gmail API avec OAuth2 refresh token."""

    def __init__(self):
        self.service = None
        self.email_address = None
        self._init_service()

    def _load_token_data(self) -> Optional[dict]:
        """Charge le token JSON depuis Supabase, env, ou fichier local."""
        # 1. Supabase system_settings (source de verite en prod)
        try:
            from core.supabase_storage import SupabaseStorage
            storage = SupabaseStorage(silent=True)
            token_value = storage.get_system_setting("GMAIL_TOKEN_JSON")
            if token_value:
                if isinstance(token_value, str):
                    token_value = json.loads(token_value)
                print("✅ Gmail token chargé depuis Supabase")
                return token_value
        except Exception as exc:
            print(f"⚠️ Echec lecture GMAIL_TOKEN_JSON depuis Supabase : {exc}")

        # 2. Variable d'environnement
        env_token = os.getenv("GMAIL_TOKEN_JSON")
        if env_token:
            try:
                data = json.loads(env_token)
                print("✅ Gmail token chargé depuis variable d'environnement")
                return data
            except json.JSONDecodeError:
                pass

        # 3. Fichier local
        if os.path.exists(_TOKEN_FILE):
            with open(_TOKEN_FILE, "r") as f:
                print(f"✅ Gmail token chargé depuis {_TOKEN_FILE}")
                return json.load(f)

        return None

    def _init_service(self):
        """Initialise le service Gmail API."""
        if Credentials is None:
            print("⚠️ Gmail API non disponible (dépendances manquantes)")
            return

        token_data = self._load_token_data()
        if not token_data:
            print("⚠️ Gmail token non trouvé — emails Gmail désactivés")
            return

        try:
            creds = Credentials.from_authorized_user_info(token_data, SCOPES)

            if creds.expired and creds.refresh_token:
                print("🔄 Rafraîchissement du token Gmail...")
                creds.refresh(Request())
                # Sauvegarder le token rafraîchi localement
                if os.path.exists(_TOKEN_FILE):
                    with open(_TOKEN_FILE, "w") as f:
                        json.dump({
                            "token": creds.token,
                            "refresh_token": creds.refresh_token,
                            "token_uri": creds.token_uri,
                            "client_id": creds.client_id,
                            "client_secret": creds.client_secret,
                            "scopes": list(creds.scopes) if creds.scopes else None,
                        }, f, indent=2)

            self.service = build("gmail", "v1", credentials=creds)
            profile = self.service.users().getProfile(userId="me").execute()
            self.email_address = profile.get("emailAddress")
            print(f"✅ Gmail API initialisé — expéditeur : {self.email_address}")

        except Exception as e:
            print(f"❌ Erreur initialisation Gmail API : {e}")
            self.service = None

    @property
    def is_available(self) -> bool:
        return self.service is not None

    def send_email(
        self,
        to_emails: List[str],
        subject: str,
        html_content: str,
        plain_content: Optional[str] = None,
    ) -> bool:
        """
        Envoie un email via Gmail API.

        Args:
            to_emails: Liste d'emails destinataires
            subject: Sujet
            html_content: Contenu HTML
            plain_content: Contenu texte (optionnel)

        Returns:
            True si envoyé avec succès
        """
        if not self.service:
            print("⚠️ Gmail API non initialisé — email non envoyé")
            return False

        try:
            msg = MIMEMultipart("alternative")
            msg["from"] = self.email_address
            msg["to"] = ", ".join(to_emails)
            msg["subject"] = subject

            if plain_content:
                msg.attach(MIMEText(plain_content, "plain"))
            msg.attach(MIMEText(html_content, "html"))

            raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
            result = self.service.users().messages().send(
                userId="me",
                body={"raw": raw},
            ).execute()

            if result and result.get("id"):
                print(f"✅ Email envoyé via Gmail à {len(to_emails)} destinataire(s) (id: {result['id']})")
                return True
            else:
                print(f"⚠️ Gmail réponse inattendue : {result}")
                return False

        except Exception as e:
            print(f"❌ Erreur envoi Gmail : {e}")
            return False


# Singleton
_gmail_sender: Optional[GmailSender] = None


def get_gmail_sender() -> GmailSender:
    """Retourne l'instance GmailSender (singleton)."""
    global _gmail_sender
    if _gmail_sender is None:
        _gmail_sender = GmailSender()
    return _gmail_sender
