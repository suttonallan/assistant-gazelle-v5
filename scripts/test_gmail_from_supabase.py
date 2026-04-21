#!/usr/bin/env python3
"""
Test — Envoyer un email via Gmail API avec le token stocké dans Supabase.
Simule le comportement en production (Render).

Usage :
    python3 scripts/test_gmail_from_supabase.py
"""

import os
import sys
import json
import base64
from email.mime.text import MIMEText

from dotenv import load_dotenv
load_dotenv()

try:
    from supabase import create_client
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
except ImportError:
    print("❌ pip install supabase google-auth google-api-python-client")
    sys.exit(1)

SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.readonly",
]


def main():
    # 1. Charger le token depuis Supabase
    print("📡 Chargement du token depuis Supabase...")
    sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_ROLE_KEY"))
    result = sb.table("system_settings").select("value").eq("key", "GMAIL_TOKEN_JSON").execute()

    if not result.data or not result.data[0].get("value"):
        print("❌ Token GMAIL_TOKEN_JSON non trouvé dans Supabase")
        sys.exit(1)

    token_data = result.data[0]["value"]
    if isinstance(token_data, str):
        token_data = json.loads(token_data)

    print("✅ Token chargé depuis Supabase")

    # 2. Créer les credentials
    creds = Credentials.from_authorized_user_info(token_data, SCOPES)

    if creds.expired and creds.refresh_token:
        print("🔄 Rafraîchissement du token...")
        creds.refresh(Request())
        print("✅ Token rafraîchi")

    # 3. Construire le service Gmail
    service = build("gmail", "v1", credentials=creds)
    profile = service.users().getProfile(userId="me").execute()
    print(f"✅ Connecté à : {profile['emailAddress']}")

    # 4. Envoyer un email de test
    destinataire = "allan@sutton.net"
    message = MIMEText(
        "<h2>🎹 Test Gmail API — depuis Supabase</h2>"
        "<p>Ce courriel a été envoyé en utilisant le token stocké dans <strong>Supabase</strong>.</p>"
        "<p>C'est exactement comme ça que Render enverra les emails en production.</p>"
        "<br><p><em>— Assistant Gazelle V5</em></p>",
        "html"
    )
    message["to"] = destinataire
    message["from"] = profile["emailAddress"]
    message["subject"] = "✅ Test Gmail API — Token Supabase (production)"

    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    result = service.users().messages().send(
        userId="me",
        body={"raw": raw},
    ).execute()

    print(f"✅ Email envoyé à {destinataire}")
    print(f"   Message ID : {result['id']}")
    print()
    print("🎉 Le token Supabase fonctionne ! Production-ready.")


if __name__ == "__main__":
    main()
