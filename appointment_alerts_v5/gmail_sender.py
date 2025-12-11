"""
Module d'envoi d'emails via Gmail API
Piano Technique Montréal

Utilise OAuth2 pour une authentification sécurisée
"""

import os
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Scopes nécessaires pour envoyer des emails
SCOPES = ['https://www.googleapis.com/auth/gmail.send']

class GmailSender:
    """Classe pour envoyer des emails via Gmail API"""

    def __init__(self, credentials_file='credentials.json', token_file='token.json'):
        """
        Initialise le service Gmail

        Args:
            credentials_file: Chemin vers le fichier credentials.json de Google Cloud
            token_file: Chemin vers le fichier token.json (créé automatiquement)
        """
        self.credentials_file = credentials_file
        self.token_file = token_file
        self.service = None
        self._authenticate()

    def _authenticate(self):
        """Authentifie l'utilisateur via OAuth2"""
        creds = None

        # Le fichier token.json stocke les tokens d'accès et de rafraîchissement
        if os.path.exists(self.token_file):
            creds = Credentials.from_authorized_user_file(self.token_file, SCOPES)

        # Si pas de credentials valides, demander à l'utilisateur de se connecter
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(self.credentials_file):
                    raise FileNotFoundError(
                        f"Le fichier {self.credentials_file} n'existe pas. "
                        "Téléchargez-le depuis Google Cloud Console."
                    )
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_file, SCOPES)
                # Forcer Google à demander le choix du compte
                creds = flow.run_local_server(
                    port=0,
                    prompt='select_account'  # Force le choix du compte
                )

            # Sauvegarder les credentials pour la prochaine fois
            with open(self.token_file, 'w') as token:
                token.write(creds.to_json())

        self.service = build('gmail', 'v1', credentials=creds)

    def send_email(self, to, subject, body_text, body_html=None, from_name="Piano Technique Montréal"):
        """
        Envoie un email

        Args:
            to: Adresse email du destinataire (ou liste d'adresses)
            subject: Sujet de l'email
            body_text: Corps de l'email en texte brut
            body_html: Corps de l'email en HTML (optionnel)
            from_name: Nom de l'expéditeur (optionnel)

        Returns:
            dict: Résultat de l'envoi avec 'success' et 'message_id' ou 'error'
        """
        try:
            # Créer le message
            message = MIMEMultipart('alternative')
            message['Subject'] = subject
            message['From'] = from_name

            # Gérer destinataires multiples
            if isinstance(to, list):
                message['To'] = ', '.join(to)
            else:
                message['To'] = to

            # Ajouter le corps en texte brut
            part1 = MIMEText(body_text, 'plain', 'utf-8')
            message.attach(part1)

            # Ajouter le corps HTML si fourni
            if body_html:
                part2 = MIMEText(body_html, 'html', 'utf-8')
                message.attach(part2)

            # Encoder le message en base64
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')

            # Envoyer via Gmail API
            send_message = self.service.users().messages().send(
                userId='me',
                body={'raw': raw_message}
            ).execute()

            return {
                'success': True,
                'message_id': send_message['id']
            }

        except HttpError as error:
            return {
                'success': False,
                'error': f'Gmail API error: {error}'
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'Error sending email: {str(e)}'
            }

    def send_unconfirmed_appointments_alert(self, technician_email, technician_name, appointments):
        """
        Envoie une alerte pour les rendez-vous non confirmés

        Args:
            technician_email: Email du technicien
            technician_name: Nom du technicien
            appointments: Liste des rendez-vous non confirmés

        Returns:
            dict: Résultat de l'envoi
        """
        if not appointments:
            return {'success': True, 'message': 'No appointments to send'}

        # Construire le sujet
        count = len(appointments)
        subject = f"⚠️ {count} rendez-vous non confirmé{'s' if count > 1 else ''} pour demain"

        # Construire le corps en texte
        body_text = f"Bonjour {technician_name},\n\n"
        body_text += f"Vous avez {count} rendez-vous non confirmé{'s' if count > 1 else ''} pour demain:\n\n"

        for apt in appointments:
            body_text += f"• {apt['client_name']}\n"
            body_text += f"  Heure: {apt['start_at']}\n"
            body_text += f"  Description: {apt['description']}\n\n"

        body_text += "Veuillez contacter ces clients pour confirmer.\n\n"
        body_text += "Cordialement,\n"
        body_text += "Piano Technique Montréal"

        # Construire le corps en HTML
        body_html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; color: #333;">
            <h2 style="color: #dc3545;">⚠️ Rendez-vous non confirmés</h2>
            <p>Bonjour {technician_name},</p>
            <p>Vous avez <strong>{count}</strong> rendez-vous non confirmé{'s' if count > 1 else ''} pour demain:</p>

            <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
                <thead>
                    <tr style="background-color: #f8f9fa;">
                        <th style="padding: 10px; text-align: left; border-bottom: 2px solid #dee2e6;">Client</th>
                        <th style="padding: 10px; text-align: left; border-bottom: 2px solid #dee2e6;">Heure</th>
                        <th style="padding: 10px; text-align: left; border-bottom: 2px solid #dee2e6;">Description</th>
                    </tr>
                </thead>
                <tbody>
        """

        for apt in appointments:
            body_html += f"""
                    <tr>
                        <td style="padding: 10px; border-bottom: 1px solid #dee2e6;">{apt['client_name']}</td>
                        <td style="padding: 10px; border-bottom: 1px solid #dee2e6;">{apt['start_at']}</td>
                        <td style="padding: 10px; border-bottom: 1px solid #dee2e6;">{apt['description']}</td>
                    </tr>
            """

        body_html += """
                </tbody>
            </table>

            <p style="margin-top: 20px;">Veuillez contacter ces clients pour confirmer.</p>

            <p style="margin-top: 30px; color: #666;">
                Cordialement,<br>
                <strong>Piano Technique Montréal</strong>
            </p>
        </body>
        </html>
        """

        return self.send_email(
            to=technician_email,
            subject=subject,
            body_text=body_text,
            body_html=body_html
        )


# Fonction d'aide pour utilisation simple
def send_simple_email(to, subject, message):
    """
    Fonction simple pour envoyer un email rapidement

    Args:
        to: Destinataire
        subject: Sujet
        message: Message

    Returns:
        bool: True si envoyé avec succès
    """
    try:
        sender = GmailSender()
        result = sender.send_email(to, subject, message)
        return result.get('success', False)
    except Exception as e:
        print(f"Erreur: {e}")
        return False


if __name__ == '__main__':
    # Test d'envoi
    print("Test d'envoi d'email via Gmail API")
    print("=" * 50)

    # Créer une instance
    try:
        gmail = GmailSender()

        # Demander les informations de test
        to_email = input("Email destinataire: ")

        result = gmail.send_email(
            to=to_email,
            subject="Test - Piano Technique Montréal",
            body_text="Ceci est un email de test envoyé via Gmail API.",
            body_html="<h2>Test Gmail API</h2><p>Ceci est un email de test envoyé via Gmail API.</p>"
        )

        if result['success']:
            print(f"✅ Email envoyé avec succès! Message ID: {result['message_id']}")
        else:
            print(f"❌ Erreur: {result['error']}")

    except Exception as e:
        print(f"❌ Erreur: {e}")
