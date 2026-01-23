#!/usr/bin/env python3
"""
Test rapide de la clé API SendGrid.

Usage:
    python3 test_sendgrid.py
"""

import os
from dotenv import load_dotenv

# Charger .env
load_dotenv()

def test_sendgrid():
    # 1. Vérifier la clé
    api_key = os.getenv('SENDGRID_API_KEY')
    if not api_key:
        print("❌ SENDGRID_API_KEY non trouvée dans .env")
        return False

    print(f"✅ Clé API trouvée: {api_key[:20]}...")

    # 2. Vérifier les emails configurés
    from_email = os.getenv('ALERT_FROM_EMAIL', os.getenv('EMAIL_FROM', 'info@piano-tek.com'))
    to_email = os.getenv('EMAIL_ALLAN', 'asutton@piano-tek.com')

    print(f"📧 FROM: {from_email}")
    print(f"📧 TO: {to_email}")

    # 3. Tester l'envoi
    try:
        from sendgrid import SendGridAPIClient
        from sendgrid.helpers.mail import Mail, Email, To, Content

        message = Mail(
            from_email=Email(from_email, 'Test SendGrid'),
            to_emails=To(to_email),
            subject='Test SendGrid - Verification',
            html_content=Content("text/html", "<p>Si tu vois ce message, SendGrid fonctionne!</p>")
        )

        print("\n📤 Envoi en cours...")

        sg = SendGridAPIClient(api_key)
        response = sg.send(message)

        print(f"\n📊 Status HTTP: {response.status_code}")

        if response.status_code == 202:
            print("✅ SUCCESS! Email accepté par SendGrid.")
            return True
        elif response.status_code == 401:
            print("❌ ERREUR 401: Clé API invalide ou révoquée.")
            print("   → Va sur https://app.sendgrid.com/settings/api_keys")
            print("   → Vérifie que ta clé est active")
            return False
        elif response.status_code == 403:
            print("❌ ERREUR 403: Adresse expéditeur non vérifiée.")
            print(f"   → Vérifie que '{from_email}' est validée dans SendGrid")
            print("   → Settings > Sender Authentication > Single Sender Verification")
            return False
        else:
            print(f"⚠️ Réponse inattendue: {response.status_code}")
            print(f"   Body: {response.body}")
            return False

    except Exception as e:
        print(f"\n❌ Erreur: {e}")

        if "401" in str(e):
            print("\n💡 Solution: Régénère ta clé API dans SendGrid")
        elif "403" in str(e):
            print(f"\n💡 Solution: Valide l'email '{from_email}' dans SendGrid")

        return False

if __name__ == "__main__":
    print("=" * 50)
    print("TEST SENDGRID")
    print("=" * 50 + "\n")

    success = test_sendgrid()

    print("\n" + "=" * 50)
    print("RÉSULTAT:", "✅ OK" if success else "❌ ÉCHEC")
    print("=" * 50)
