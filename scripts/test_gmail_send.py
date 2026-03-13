#!/usr/bin/env python3
"""
Test rapide — Envoyer un email via Gmail API avec le token OAuth2.

Usage :
    python3 scripts/test_gmail_send.py
"""

import os
import sys
import json
import base64
from email.mime.text import MIMEText

try:
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
except ImportError:
    print("❌ pip install google-auth google-api-python-client")
    sys.exit(1)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
TOKEN_FILE = os.path.join(PROJECT_DIR, "config", "gmail-token.json")

SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.readonly",
]


def main():
    # Charger le token
    if not os.path.exists(TOKEN_FILE):
        print(f"❌ Token non trouvé : {TOKEN_FILE}")
        print("   Lancez d'abord : python3 scripts/gmail_auth_setup.py")
        sys.exit(1)

    creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    # Rafraîchir si expiré
    if creds.expired and creds.refresh_token:
        print("🔄 Rafraîchissement du token...")
        creds.refresh(Request())
        print("✅ Token rafraîchi")

    # Construire le service Gmail
    service = build("gmail", "v1", credentials=creds)

    # Vérifier la connexion
    profile = service.users().getProfile(userId="me").execute()
    print(f"✅ Connecté à : {profile['emailAddress']}")

    # Créer un email de test
    destinataire = "allan@sutton.net"
    message = MIMEText(
        "<h2>🎹 Test Gmail API — Assistant Gazelle</h2>"
        "<p>Si vous recevez ce courriel, la connexion Gmail fonctionne parfaitement.</p>"
        "<p>Le refresh token est valide. Plus besoin de code de vérification.</p>"
        "<br><p><em>— Assistant Gazelle V5</em></p>",
        "html"
    )
    message["to"] = destinataire
    message["from"] = profile["emailAddress"]
    message["subject"] = "✅ Test Gmail API — Assistant Gazelle V5"

    # Encoder et envoyer
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    result = service.users().messages().send(
        userId="me",
        body={"raw": raw}
    ).execute()

    print(f"✅ Email envoyé à {destinataire}")
    print(f"   Message ID : {result['id']}")
    print()
    print("🎉 Tout fonctionne ! Vérifiez votre boîte de réception.")


if __name__ == "__main__":
    main()
