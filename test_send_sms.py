#!/usr/bin/env python3
"""
Script de test pour envoyer un SMS manuellement via Zoom Phone.

Usage:
    python3 test_send_sms.py <numéro> <message>
    
Exemples:
    python3 test_send_sms.py +15551234567 "Bonjour, ceci est un test"
    python3 test_send_sms.py 5551234567 "Test SMS"
    python3 test_send_sms.py 5145551234 "Message de test"
"""

import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Charger les variables d'environnement depuis .env à la racine du projet
PROJECT_ROOT = Path(__file__).parent
env_path = PROJECT_ROOT / '.env'
load_dotenv(env_path)

# Ajouter le projet au path
sys.path.insert(0, str(PROJECT_ROOT))

from core.zoom_sms import send_zoom_sms, format_phone_number


def main():
    """Fonction principale du script de test."""
    print("="*70)
    print("📱 TEST ENVOI SMS VIA ZOOM PHONE")
    print("="*70)
    
    # Vérifier les arguments
    if len(sys.argv) < 3:
        print("\n❌ Usage: python3 test_send_sms.py <numéro> <message>")
        print("\nExemples:")
        print("  python3 test_send_sms.py +15551234567 \"Bonjour, ceci est un test\"")
        print("  python3 test_send_sms.py 5551234567 \"Test SMS\"")
        print("  python3 test_send_sms.py 5145551234 \"Message de test\"")
        sys.exit(1)
    
    to_number = sys.argv[1]
    message = ' '.join(sys.argv[2:])
    
    print(f"\n📤 Configuration:")
    print(f"   Destinataire: {to_number}")
    print(f"   Message: {message}")
    print(f"   Longueur: {len(message)} caractères")
    
    # Formater le numéro
    try:
        formatted_number = format_phone_number(to_number)
        print(f"   Numéro formaté (E.164): {formatted_number}")
    except ValueError as e:
        print(f"\n❌ Erreur formatage numéro: {e}")
        sys.exit(1)
    
    # Envoyer le SMS
    print(f"\n📤 Envoi du SMS...")
    result = send_zoom_sms(to_number, message)
    
    # Afficher le résultat
    print("\n" + "="*70)
    if result.get('success'):
        print("✅ SMS envoyé avec succès!")
        print(f"   Message ID: {result.get('message_id', 'N/A')}")
        print(f"   Destinataire: {result.get('to', formatted_number)}")
        if result.get('response'):
            print(f"   Réponse API: {result.get('response')}")
    else:
        print("❌ Erreur lors de l'envoi du SMS")
        print(f"   Erreur: {result.get('error', 'Erreur inconnue')}")
        if result.get('status_code'):
            print(f"   Code HTTP: {result.get('status_code')}")
        sys.exit(1)
    
    print("="*70)


if __name__ == "__main__":
    main()
