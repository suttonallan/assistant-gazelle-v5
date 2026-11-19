#!/usr/bin/env python3
"""
Script d'auto-refresh du token Gazelle OAuth.

Gère automatiquement l'authentification et le renouvellement du token:
1. Vérifie si le token actuel est expiré
2. Si expiré, génère un nouveau token via OAuth
3. Sauvegarde dans Supabase system_settings

Usage:
    python3 scripts/auto_refresh_token.py
"""

import sys
import os
import time
import requests
from pathlib import Path

# Ajouter le projet au path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv()

from core.supabase_storage import SupabaseStorage

# URLs Gazelle
OAUTH_TOKEN_URL = "https://gazelleapp.io/developer/oauth/token"
OAUTH_AUTHORIZE_URL = "https://gazelleapp.io/developer/oauth/authorize"


def get_credentials():
    """Récupère les credentials OAuth depuis .env ou config."""
    # Jamais de valeur en dur : dépôt public (voir core/gazelle_api_client.py).
    client_id = os.getenv('GAZELLE_CLIENT_ID', '')
    client_secret = os.getenv('GAZELLE_CLIENT_SECRET', '')

    return client_id, client_secret


def check_token_expiry(storage: SupabaseStorage) -> tuple[bool, dict]:
    """
    Vérifie si le token actuel est expiré ou proche de l'expiration.

    Returns:
        (is_expired, token_data)
    """
    token_data = storage.get_system_setting("gazelle_oauth_token")

    if not token_data:
        print("⚠️  Aucun token trouvé dans Supabase")
        return True, None

    created_at = token_data.get('created_at', 0)
    expires_in = token_data.get('expires_in', 0)
    current_time = int(time.time())

    age = current_time - created_at
    time_until_expiry = expires_in - age

    print(f"📊 État du token:")
    print(f"   Créé il y a: {int(age/3600)} heures")
    print(f"   Expire dans: {int(time_until_expiry/3600)} heures")

    # Considérer expiré si moins de 1 heure restante
    is_expired = time_until_expiry < 3600

    if is_expired:
        print(f"   ❌ Token expiré ou expire bientôt")
    else:
        print(f"   ✅ Token valide")

    return is_expired, token_data


def refresh_token_with_refresh_token(storage: SupabaseStorage, refresh_token: str) -> dict:
    """
    Rafraîchit le token en utilisant le refresh_token.

    Args:
        storage: Instance SupabaseStorage
        refresh_token: Token de rafraîchissement

    Returns:
        Nouveau token_data
    """
    client_id, client_secret = get_credentials()

    print("🔄 Rafraîchissement avec refresh_token...")

    payload = {
        'client_id': client_id,
        'client_secret': client_secret,
        'refresh_token': refresh_token,
        'grant_type': 'refresh_token'
    }

    response = requests.post(OAUTH_TOKEN_URL, data=payload)

    if response.status_code == 200:
        new_token_data = response.json()

        # Préserver le refresh_token s'il n'est pas retourné
        if 'refresh_token' not in new_token_data and refresh_token:
            new_token_data['refresh_token'] = refresh_token

        new_token_data['created_at'] = int(time.time())

        print("✅ Token rafraîchi avec succès")
        return new_token_data
    else:
        print(f"❌ Échec refresh: {response.status_code}")
        print(f"   Response: {response.text}")
        return None


def generate_new_token_client_credentials() -> dict:
    """
    Génère un nouveau token avec client_credentials (si supporté).

    Returns:
        Token data ou None
    """
    client_id, client_secret = get_credentials()

    print("🔑 Tentative de génération avec client_credentials...")

    payload = {
        'grant_type': 'client_credentials',
        'client_id': client_id,
        'client_secret': client_secret
    }

    response = requests.post(OAUTH_TOKEN_URL, data=payload)

    if response.status_code == 200:
        token_data = response.json()
        token_data['created_at'] = int(time.time())
        print("✅ Token généré avec client_credentials")
        return token_data
    else:
        print(f"❌ client_credentials non supporté: {response.status_code}")
        return None


def auto_refresh_token(force: bool = False) -> bool:
    """
    Vérifie et rafraîchit automatiquement le token si nécessaire.

    Args:
        force: Si True, force le refresh même si non expiré

    Returns:
        True si le token est valide/rafraîchi, False sinon
    """
    print("="*80)
    print("🔐 AUTO-REFRESH TOKEN GAZELLE")
    print("="*80)
    print()

    storage = SupabaseStorage()

    # 1. Vérifier l'état actuel
    is_expired, current_token_data = check_token_expiry(storage)

    if not force and not is_expired:
        print("\n✅ Token valide, aucun refresh nécessaire")
        return True

    print()

    # 2. Essayer de rafraîchir avec refresh_token
    if current_token_data and current_token_data.get('refresh_token'):
        print("🔄 Tentative de refresh avec refresh_token...")
        new_token_data = refresh_token_with_refresh_token(
            storage,
            current_token_data['refresh_token']
        )

        if new_token_data:
            # Sauvegarder dans Supabase
            print("\n💾 Sauvegarde du nouveau token dans Supabase...")
            storage.save_system_setting('gazelle_oauth_token', new_token_data)
            print("✅ Token sauvegardé dans system_settings")
            return True

    # 3. Si refresh échoue, essayer client_credentials (peut ne pas fonctionner)
    print("\n🔑 Tentative de génération d'un nouveau token...")
    new_token_data = generate_new_token_client_credentials()

    if new_token_data:
        print("\n💾 Sauvegarde du nouveau token dans Supabase...")
        storage.save_system_setting('gazelle_oauth_token', new_token_data)
        print("✅ Token sauvegardé dans system_settings")
        return True

    # 4. Échec complet
    print("\n" + "="*80)
    print("❌ ÉCHEC: Impossible de rafraîchir le token automatiquement")
    print("="*80)
    print()
    print("Actions possibles:")
    print("1. Vérifier les credentials dans .env (GAZELLE_CLIENT_ID, GAZELLE_CLIENT_SECRET)")
    print("2. Générer un nouveau token manuellement via l'interface Gazelle")
    print("3. Contacter le support Gazelle pour obtenir un nouveau refresh_token")
    print()

    return False


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Auto-refresh du token Gazelle OAuth")
    parser.add_argument('--force', action='store_true', help="Force le refresh même si non expiré")
    args = parser.parse_args()

    success = auto_refresh_token(force=args.force)
    sys.exit(0 if success else 1)
