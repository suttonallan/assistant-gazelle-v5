#!/usr/bin/env python3
"""
Script pour mettre à jour manuellement le token Gazelle dans Supabase.

Usage:
    python3 scripts/update_token_manual.py "VOTRE_TOKEN_ICI"
"""

import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.supabase_storage import SupabaseStorage


def update_token(access_token: str, refresh_token: str = None):
    """
    Met à jour le token dans Supabase.

    Args:
        access_token: Le nouveau access token
        refresh_token: Le refresh token (optionnel)
    """
    print("="*80)
    print("🔐 MISE À JOUR MANUELLE DU TOKEN GAZELLE")
    print("="*80)
    print()

    storage = SupabaseStorage()

    token_data = {
        'access_token': access_token,
        'expires_in': 2592000,  # 30 jours
        'created_at': int(time.time())
    }

    if refresh_token:
        token_data['refresh_token'] = refresh_token

    print(f"📝 Token à sauvegarder:")
    print(f"   Access token (20 premiers): {access_token[:20]}...")
    print(f"   Expires in: {token_data['expires_in']} secondes (30 jours)")
    if refresh_token:
        print(f"   Refresh token: Fourni")
    print()

    # Sauvegarder
    print("💾 Sauvegarde dans Supabase system_settings...")
    storage.save_system_setting('gazelle_oauth_token', token_data)

    print("✅ Token sauvegardé avec succès!")
    print()

    # Tester
    print("🧪 Test de l'API...")
    try:
        from core.gazelle_api_client import GazelleAPIClient
        client = GazelleAPIClient()
        result = client.get_clients(limit=1)
        print(f"✅ API FONCTIONNELLE: {len(result)} client récupéré")

        if result:
            print(f"\nExemple: {result[0].get('companyName', 'N/A')}")

    except Exception as e:
        print(f"❌ Erreur lors du test: {e}")
        print("\n💡 Vérifiez que le token est valide")

    print()
    print("="*80)
    print("✅ TERMINÉ")
    print("="*80)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 scripts/update_token_manual.py ACCESS_TOKEN [REFRESH_TOKEN]")
        print()
        print("Exemple:")
        print("  python3 scripts/update_token_manual.py \"B3aiww-JakL9quOHJr-C...\"")
        print("  python3 scripts/update_token_manual.py \"ACCESS\" \"REFRESH\"")
        sys.exit(1)

    access_token = sys.argv[1]
    refresh_token = sys.argv[2] if len(sys.argv) > 2 else None

    update_token(access_token, refresh_token)
