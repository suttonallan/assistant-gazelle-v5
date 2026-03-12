#!/usr/bin/env python3
"""
Configuration OAuth2 Gmail — Assistant Gazelle V5

Ce script s'exécute UNE SEULE FOIS sur votre Mac local pour :
1. Ouvrir votre navigateur et vous connecter à votre compte Gmail
2. Générer un refresh token permanent
3. Sauvegarder le token dans config/gmail-token.json

Après cette étape, le backend peut envoyer des emails via Gmail
sans jamais redemander de code de vérification.

Prérequis :
- Fichier config/gmail-credentials.json (téléchargé depuis Google Cloud Console)
- Python 3.8+
- pip install google-auth google-auth-oauthlib google-api-python-client

Usage :
    cd /Users/allansutton/Documents/assistant-gazelle-v5
    python scripts/gmail_auth_setup.py
"""

import os
import sys
import json

# Vérifier les dépendances
try:
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
except ImportError:
    print("❌ Dépendances manquantes. Exécutez :")
    print("   pip install google-auth google-auth-oauthlib google-api-python-client")
    sys.exit(1)

# Chemins
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
CONFIG_DIR = os.path.join(PROJECT_DIR, "config")

CREDENTIALS_FILE = os.path.join(CONFIG_DIR, "gmail-credentials.json")
TOKEN_FILE = os.path.join(CONFIG_DIR, "gmail-token.json")

# Scopes Gmail — envoyer des emails seulement
SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.readonly",
]


def verifier_credentials():
    """Vérifie que le fichier credentials existe."""
    if os.path.exists(CREDENTIALS_FILE):
        print(f"✅ Fichier credentials trouvé : {CREDENTIALS_FILE}")
        return True

    print("=" * 60)
    print("❌ FICHIER CREDENTIALS MANQUANT")
    print("=" * 60)
    print()
    print("Vous devez d'abord télécharger vos credentials OAuth2 :")
    print()
    print("1. Allez sur https://console.cloud.google.com/apis/credentials")
    print("   (Projet : ptm-gmail-api)")
    print()
    print("2. Cliquez sur '+ CRÉER DES IDENTIFIANTS' → 'ID client OAuth'")
    print("   - Type : Application de bureau (Desktop app)")
    print("   - Nom : Assistant Gazelle Gmail")
    print()
    print("3. Téléchargez le fichier JSON")
    print()
    print(f"4. Renommez-le et placez-le ici :")
    print(f"   {CREDENTIALS_FILE}")
    print()
    print("5. Relancez ce script")
    print()
    return False


def authentifier():
    """Lance le flow OAuth2 et sauvegarde le token."""
    creds = None

    # Vérifier si un token existe déjà
    if os.path.exists(TOKEN_FILE):
        print(f"📄 Token existant trouvé : {TOKEN_FILE}")
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

        if creds and creds.valid:
            print("✅ Token encore valide — pas besoin de ré-authentifier")
            return creds

        if creds and creds.expired and creds.refresh_token:
            print("🔄 Token expiré, rafraîchissement en cours...")
            try:
                creds.refresh(Request())
                sauvegarder_token(creds)
                print("✅ Token rafraîchi avec succès")
                return creds
            except Exception as e:
                print(f"⚠️ Échec du rafraîchissement : {e}")
                print("   Nouvelle authentification nécessaire...")
                creds = None

    # Nouvelle authentification
    print()
    print("=" * 60)
    print("🔐 AUTHENTIFICATION GMAIL")
    print("=" * 60)
    print()
    print("Votre navigateur va s'ouvrir.")
    print("Connectez-vous avec le compte info@piano-tek.com")
    print("et autorisez l'accès.")
    print()
    input("Appuyez sur Entrée pour continuer...")

    flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
    creds = flow.run_local_server(port=8090, open_browser=True)

    sauvegarder_token(creds)
    return creds


def sauvegarder_token(creds):
    """Sauvegarde le token dans config/gmail-token.json."""
    os.makedirs(CONFIG_DIR, exist_ok=True)

    token_data = {
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "scopes": creds.scopes and list(creds.scopes),
    }

    with open(TOKEN_FILE, "w") as f:
        json.dump(token_data, f, indent=2)

    print(f"💾 Token sauvegardé : {TOKEN_FILE}")


def tester_connexion(creds):
    """Teste l'accès Gmail avec le token obtenu."""
    print()
    print("🧪 Test de connexion Gmail...")

    try:
        service = build("gmail", "v1", credentials=creds)
        profile = service.users().getProfile(userId="me").execute()
        email = profile.get("emailAddress", "inconnu")
        total = profile.get("messagesTotal", 0)

        print(f"✅ Connecté à : {email}")
        print(f"   Messages totaux : {total:,}")
        return True

    except Exception as e:
        print(f"❌ Erreur de connexion : {e}")
        return False


def afficher_resume(creds):
    """Affiche un résumé des prochaines étapes."""
    print()
    print("=" * 60)
    print("✅ CONFIGURATION TERMINÉE")
    print("=" * 60)
    print()
    print("Fichier token créé :")
    print(f"  {TOKEN_FILE}")
    print()
    print("Ce token contient un refresh_token permanent.")
    print("Le backend pourra envoyer des emails via Gmail")
    print("sans jamais redemander de mot de passe ou code 2FA.")
    print()
    print("Prochaines étapes :")
    print("  1. Le token est dans config/ (déjà gitignored)")
    print("  2. Pour Render (production), ajoutez la variable :")
    print("     GMAIL_TOKEN_JSON = <contenu de gmail-token.json>")
    print("  3. Ou stockez-le dans Supabase system_settings")
    print()

    if creds and creds.refresh_token:
        print(f"  Refresh token (début) : {creds.refresh_token[:20]}...")
    print()


def main():
    print()
    print("🎹 Gmail Auth Setup — Assistant Gazelle V5")
    print("=" * 60)
    print()

    # Étape 1 : Vérifier credentials
    if not verifier_credentials():
        sys.exit(1)

    # Étape 2 : Authentification OAuth2
    creds = authentifier()
    if not creds:
        print("❌ Authentification échouée")
        sys.exit(1)

    # Étape 3 : Test
    tester_connexion(creds)

    # Étape 4 : Résumé
    afficher_resume(creds)


if __name__ == "__main__":
    main()
