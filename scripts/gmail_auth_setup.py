#!/usr/bin/env python3
"""
Script d'authentification initiale Gmail OAuth2.

Usage:
    python scripts/gmail_auth_setup.py

Prérequis:
    1. API Gmail activée dans Google Cloud Console
    2. Credentials OAuth2 "Desktop app" téléchargés dans:
       config/gmail-oauth-credentials.json

Ce script:
    1. Ouvre un navigateur pour l'authentification Google
    2. Demande l'accès en lecture seule à Gmail
    3. Sauvegarde le token dans config/gmail-token.json
    4. Sauvegarde aussi dans Supabase (pour accès en production)
    5. Teste la connexion en listant les derniers emails

À exécuter UNE SEULE FOIS en local. Le refresh token est valide indéfiniment
tant que l'accès n'est pas révoqué.
"""

import os
import sys
import json

# Ajouter le répertoire racine au path
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)

# Charger .env si présent
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(ROOT_DIR, '.env'))
except ImportError:
    pass

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
CREDENTIALS_PATH = os.path.join(ROOT_DIR, 'config', 'gmail-oauth-credentials.json')
TOKEN_PATH = os.path.join(ROOT_DIR, 'config', 'gmail-token.json')


def main():
    print("=" * 60)
    print("  Gmail OAuth2 - Authentification initiale")
    print("=" * 60)
    print()

    # Vérifier que le fichier credentials existe
    if not os.path.exists(CREDENTIALS_PATH):
        print(f"ERREUR: Fichier credentials manquant:")
        print(f"  {CREDENTIALS_PATH}")
        print()
        print("Instructions:")
        print("  1. Allez sur https://console.cloud.google.com")
        print("  2. Sélectionnez votre projet")
        print("  3. API et services → Identifiants")
        print("  4. Créer un identifiant → ID client OAuth 2.0")
        print("  5. Type: 'Application de bureau'")
        print("  6. Téléchargez le JSON")
        print(f"  7. Renommez-le et placez-le dans: config/gmail-oauth-credentials.json")
        sys.exit(1)

    # Vérifier si un token existe déjà
    creds = None
    if os.path.exists(TOKEN_PATH):
        try:
            creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
            if creds and creds.valid:
                print(f"Token existant trouvé et valide: {TOKEN_PATH}")
                print("Voulez-vous le régénérer ? (o/N) ", end="")
                response = input().strip().lower()
                if response != 'o':
                    print("\nToken existant conservé.")
                    _test_connection(creds)
                    return
            elif creds and creds.expired and creds.refresh_token:
                print("Token expiré, rafraîchissement...")
                creds.refresh(Request())
                _save_token(creds)
                print("Token rafraîchi avec succès!")
                _test_connection(creds)
                return
        except Exception as e:
            print(f"Token existant invalide ({e}), régénération...")
            creds = None

    # Flow OAuth2 interactif
    print("Lancement de l'authentification OAuth2...")
    print("Un navigateur va s'ouvrir pour vous connecter avec le compte Google.")
    print()
    print("IMPORTANT: Connectez-vous avec le compte qui a accès à info@piano-tek.com")
    print()

    flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)

    # Essayer d'abord le serveur local, sinon mode console
    try:
        creds = flow.run_local_server(port=8090, open_browser=True)
    except Exception:
        print("Impossible d'ouvrir le navigateur. Mode console:")
        creds = flow.run_console()

    if not creds:
        print("ERREUR: Authentification échouée")
        sys.exit(1)

    # Sauvegarder le token
    _save_token(creds)

    print()
    print("Authentification réussie!")
    print()

    # Tester la connexion
    _test_connection(creds)


def _save_token(creds):
    """Sauvegarde le token localement et dans Supabase."""
    # Fichier local
    with open(TOKEN_PATH, 'w') as f:
        f.write(creds.to_json())
    print(f"Token sauvegardé: {TOKEN_PATH}")

    # Supabase (pour production)
    try:
        from core.supabase_storage import SupabaseStorage
        import requests

        storage = SupabaseStorage(silent=True)
        token_data = json.loads(creds.to_json())

        resp = requests.post(
            f"{storage.api_url}/system_settings",
            headers={
                **storage._get_headers(),
                "Prefer": "resolution=merge-duplicates"
            },
            json={
                "key": "gmail_oauth_token",
                "value": json.dumps(token_data),
                "updated_at": creds.expiry.isoformat() if creds.expiry else None
            }
        )
        if resp.status_code in (200, 201):
            print("Token aussi sauvegardé dans Supabase (pour production)")
        else:
            print(f"Avertissement: sauvegarde Supabase échouée ({resp.status_code})")
    except Exception as e:
        print(f"Avertissement: sauvegarde Supabase non disponible ({e})")


def _test_connection(creds):
    """Teste la connexion Gmail en listant les derniers emails."""
    print()
    print("-" * 40)
    print("  Test de connexion Gmail")
    print("-" * 40)

    try:
        service = build('gmail', 'v1', credentials=creds)

        # Profil
        profile = service.users().getProfile(userId='me').execute()
        print(f"  Compte: {profile.get('emailAddress')}")
        print(f"  Messages totaux: {profile.get('messagesTotal', '?')}")

        # Derniers emails PDA
        from core.gmail_scanner import PDA_SENDER_DOMAINS
        domain_query = ' OR '.join(f'from:@{d}' for d in PDA_SENDER_DOMAINS)
        query = f'({domain_query}) newer_than:30d'

        results = service.users().messages().list(
            userId='me', q=query, maxResults=5
        ).execute()

        messages = results.get('messages', [])
        print(f"\n  Derniers emails PDA (30 jours): {len(messages)} trouvé(s)")

        for msg_info in messages[:5]:
            msg = service.users().messages().get(
                userId='me', id=msg_info['id'], format='metadata',
                metadataHeaders=['From', 'Subject', 'Date']
            ).execute()
            headers = {h['name']: h['value'] for h in msg['payload']['headers']}
            print(f"    - {headers.get('Date', '?')} | {headers.get('From', '?')}")
            print(f"      {headers.get('Subject', '(sans objet)')}")

        print()
        print("Connexion Gmail OK! Le scanner est prêt.")
        print()

    except Exception as e:
        print(f"  ERREUR test: {e}")
        print("  La connexion a échoué. Vérifiez les credentials et réessayez.")


if __name__ == '__main__':
    main()
