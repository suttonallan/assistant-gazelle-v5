"""
Scanner Gmail pour détecter les nouvelles demandes PDA.

Lit la boîte info@piano-tek.com via l'API Gmail,
filtre par domaines expéditeurs connus (placedesarts.com, operademontreal.com),
et transmet les emails non traités au pipeline de création de demandes.

Prérequis:
- API Gmail activée dans Google Cloud Console
- Credentials OAuth2 dans config/gmail-oauth-credentials.json
- Token généré via scripts/gmail_auth_setup.py
"""

from __future__ import annotations

import os
import base64
import json
import logging
from datetime import datetime, timezone
from typing import List, Dict, Optional, Any
from email.utils import parsedate_to_datetime

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)

# Scopes Gmail (lecture seule)
GMAIL_SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

# Domaines surveillés pour les demandes PDA
PDA_SENDER_DOMAINS = [
    'placedesarts.com',
    'operademontreal.com',
]

# Chemins des fichiers de credentials
OAUTH_CREDENTIALS_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    'config', 'gmail-oauth-credentials.json'
)
TOKEN_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    'config', 'gmail-token.json'
)


class GmailScanner:
    """Scanner Gmail pour les demandes Place des Arts."""

    def __init__(self):
        self.service = None
        self._initialized = False

    def initialize(self) -> bool:
        """
        Initialise la connexion Gmail API.
        Retourne True si l'authentification est réussie.
        """
        try:
            creds = self._get_credentials()
            if not creds:
                logger.error("Impossible d'obtenir les credentials Gmail")
                return False

            self.service = build('gmail', 'v1', credentials=creds)
            self._initialized = True
            logger.info("Gmail scanner initialisé avec succès")
            return True

        except Exception as e:
            logger.error(f"Erreur initialisation Gmail scanner: {e}")
            return False

    def _get_credentials(self) -> Optional[Credentials]:
        """
        Charge ou rafraîchit les credentials OAuth2.

        Ordre de priorité:
        1. Token existant (config/gmail-token.json)
        2. Refresh du token expiré
        3. Nouveau flow OAuth2 (interactif - seulement en local)
        """
        creds = None

        # 1. Charger le token existant
        if os.path.exists(TOKEN_PATH):
            try:
                creds = Credentials.from_authorized_user_file(TOKEN_PATH, GMAIL_SCOPES)
            except Exception as e:
                logger.warning(f"Token Gmail invalide, sera régénéré: {e}")

        # 2. Rafraîchir si expiré
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                # Sauvegarder le token rafraîchi
                self._save_token(creds)
                logger.info("Token Gmail rafraîchi avec succès")
            except Exception as e:
                logger.error(f"Erreur rafraîchissement token Gmail: {e}")
                creds = None

        # 3. Si pas de creds valides, essayer le token depuis Supabase
        if not creds or not creds.valid:
            creds = self._load_token_from_supabase()

        # 4. Si toujours pas de creds, flow interactif (dev local seulement)
        if not creds or not creds.valid:
            if os.path.exists(OAUTH_CREDENTIALS_PATH):
                logger.warning(
                    "Aucun token Gmail valide. "
                    "Exécutez 'python scripts/gmail_auth_setup.py' pour l'authentification initiale."
                )
            else:
                logger.error(
                    f"Fichier credentials OAuth2 manquant: {OAUTH_CREDENTIALS_PATH}. "
                    "Téléchargez-le depuis Google Cloud Console."
                )
            return None

        return creds

    def _save_token(self, creds: Credentials):
        """Sauvegarde le token dans un fichier local et dans Supabase."""
        try:
            # Fichier local
            with open(TOKEN_PATH, 'w') as f:
                f.write(creds.to_json())

            # Supabase (pour accès en production)
            self._save_token_to_supabase(creds)
        except Exception as e:
            logger.warning(f"Erreur sauvegarde token Gmail: {e}")

    def _save_token_to_supabase(self, creds: Credentials):
        """Sauvegarde le token Gmail dans system_settings (Supabase)."""
        try:
            from core.supabase_storage import SupabaseStorage
            storage = SupabaseStorage(silent=True)
            token_data = json.loads(creds.to_json())

            import requests as req
            resp = req.post(
                f"{storage.api_url}/system_settings",
                headers={
                    **storage._get_headers(),
                    "Prefer": "resolution=merge-duplicates"
                },
                json={
                    "key": "gmail_oauth_token",
                    "value": json.dumps(token_data),
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }
            )
            if resp.status_code in (200, 201):
                logger.info("Token Gmail sauvegardé dans Supabase")
        except Exception as e:
            logger.warning(f"Erreur sauvegarde token Gmail dans Supabase: {e}")

    def _load_token_from_supabase(self) -> Optional[Credentials]:
        """Charge le token Gmail depuis Supabase (pour production sur Render)."""
        try:
            from core.supabase_storage import SupabaseStorage
            storage = SupabaseStorage(silent=True)

            import requests as req
            resp = req.get(
                f"{storage.api_url}/system_settings",
                headers=storage._get_headers(),
                params={"key": "eq.gmail_oauth_token", "select": "value"}
            )
            if resp.status_code == 200:
                data = resp.json()
                if data:
                    token_data = json.loads(data[0]['value'])
                    creds = Credentials.from_authorized_user_info(token_data, GMAIL_SCOPES)

                    # Rafraîchir si expiré
                    if creds.expired and creds.refresh_token:
                        creds.refresh(Request())
                        self._save_token_to_supabase(creds)

                    if creds.valid:
                        logger.info("Token Gmail chargé depuis Supabase")
                        return creds
        except Exception as e:
            logger.debug(f"Pas de token Gmail dans Supabase: {e}")
        return None

    def scan_new_emails(
        self,
        max_results: int = 20,
        processed_ids: Optional[set] = None
    ) -> List[Dict[str, Any]]:
        """
        Scanne la boîte Gmail pour les nouveaux emails PDA.

        Args:
            max_results: Nombre max d'emails à récupérer
            processed_ids: Set d'IDs Gmail déjà traités (pour filtrage)

        Returns:
            Liste de dicts avec les infos de chaque email non traité
        """
        if not self._initialized:
            if not self.initialize():
                return []

        try:
            # Construire la requête de recherche
            # Filtrer par domaines expéditeurs
            domain_query = ' OR '.join(
                f'from:@{domain}' for domain in PDA_SENDER_DOMAINS
            )
            query = f'({domain_query}) newer_than:7d'

            logger.info(f"Scan Gmail: query='{query}'")

            # Lister les messages
            results = self.service.users().messages().list(
                userId='me',
                q=query,
                maxResults=max_results
            ).execute()

            messages = results.get('messages', [])
            if not messages:
                logger.info("Aucun email PDA trouvé")
                return []

            logger.info(f"Trouvé {len(messages)} email(s) PDA")

            # Filtrer les déjà traités
            if processed_ids:
                messages = [m for m in messages if m['id'] not in processed_ids]
                logger.info(f"Après filtrage: {len(messages)} email(s) non traités")

            # Récupérer le contenu de chaque email
            emails = []
            for msg_info in messages:
                email_data = self._get_email_content(msg_info['id'])
                if email_data:
                    emails.append(email_data)

            return emails

        except Exception as e:
            logger.error(f"Erreur scan Gmail: {e}", exc_info=True)
            return []

    def _get_email_content(self, message_id: str) -> Optional[Dict[str, Any]]:
        """
        Récupère le contenu complet d'un email.

        Returns:
            Dict avec: gmail_message_id, gmail_thread_id, sender_email,
            sender_name, subject, received_at, body_text
        """
        try:
            msg = self.service.users().messages().get(
                userId='me',
                id=message_id,
                format='full'
            ).execute()

            headers = {h['name'].lower(): h['value'] for h in msg['payload']['headers']}

            # Extraire l'expéditeur
            from_header = headers.get('from', '')
            sender_name, sender_email = self._parse_from_header(from_header)

            # Vérifier que le domaine est autorisé
            if not any(domain in sender_email.lower() for domain in PDA_SENDER_DOMAINS):
                return None

            # Date de réception
            received_at = None
            date_header = headers.get('date', '')
            if date_header:
                try:
                    received_at = parsedate_to_datetime(date_header)
                except Exception:
                    received_at = datetime.now(timezone.utc)
            else:
                # Utiliser internalDate de Gmail (millisecondes depuis epoch)
                internal_date = int(msg.get('internalDate', 0))
                if internal_date:
                    received_at = datetime.fromtimestamp(internal_date / 1000, tz=timezone.utc)

            # Extraire le corps du message (texte brut)
            body_text = self._extract_body_text(msg['payload'])

            return {
                'gmail_message_id': message_id,
                'gmail_thread_id': msg.get('threadId', ''),
                'sender_email': sender_email,
                'sender_name': sender_name,
                'subject': headers.get('subject', '(sans objet)'),
                'received_at': received_at,
                'body_text': body_text,
            }

        except Exception as e:
            logger.error(f"Erreur lecture email {message_id}: {e}")
            return None

    def _parse_from_header(self, from_header: str) -> tuple:
        """Parse 'Annie Jenkins <annie@operademontreal.com>' → ('Annie Jenkins', 'annie@...')"""
        import re
        match = re.match(r'^"?([^"<]*)"?\s*<?([^>]+)>?$', from_header.strip())
        if match:
            name = match.group(1).strip().strip('"')
            email = match.group(2).strip()
            return (name, email)
        return ('', from_header.strip())

    def _extract_body_text(self, payload: Dict) -> str:
        """
        Extrait le texte brut du corps de l'email.
        Gère les formats simple et multipart.
        """
        # Message simple
        if payload.get('mimeType') == 'text/plain' and payload.get('body', {}).get('data'):
            return base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8', errors='replace')

        # Multipart
        parts = payload.get('parts', [])
        for part in parts:
            if part.get('mimeType') == 'text/plain':
                data = part.get('body', {}).get('data', '')
                if data:
                    return base64.urlsafe_b64decode(data).decode('utf-8', errors='replace')

            # Multipart imbriqué
            if part.get('parts'):
                text = self._extract_body_text(part)
                if text:
                    return text

        # Fallback: essayer text/html et extraire le texte
        for part in parts:
            if part.get('mimeType') == 'text/html':
                data = part.get('body', {}).get('data', '')
                if data:
                    html = base64.urlsafe_b64decode(data).decode('utf-8', errors='replace')
                    return self._html_to_text(html)

        return ''

    def _html_to_text(self, html: str) -> str:
        """Conversion basique HTML → texte."""
        import re
        # Supprimer les tags HTML
        text = re.sub(r'<br\s*/?>', '\n', html, flags=re.IGNORECASE)
        text = re.sub(r'<p[^>]*>', '\n', text, flags=re.IGNORECASE)
        text = re.sub(r'</p>', '\n', text, flags=re.IGNORECASE)
        text = re.sub(r'<[^>]+>', '', text)
        # Décoder les entités HTML basiques
        text = text.replace('&nbsp;', ' ')
        text = text.replace('&amp;', '&')
        text = text.replace('&lt;', '<')
        text = text.replace('&gt;', '>')
        text = text.replace('&#39;', "'")
        text = text.replace('&quot;', '"')
        # Nettoyer les espaces multiples
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text.strip()


# Singleton
_scanner_instance: Optional[GmailScanner] = None


def get_gmail_scanner() -> GmailScanner:
    """Retourne l'instance singleton du scanner Gmail."""
    global _scanner_instance
    if _scanner_instance is None:
        _scanner_instance = GmailScanner()
    return _scanner_instance
