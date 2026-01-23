#!/usr/bin/env python3
"""
Module pour envoyer des notifications par email.
Utilise SendGrid pour l'envoi d'emails (alertes humidité, erreurs système, etc.)
"""

import os
from typing import Optional, List
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content


class EmailNotifier:
    """Gère l'envoi d'emails via SendGrid."""

    # Configuration des destinataires (chargés depuis .env)
    RECIPIENTS = {
        'nicolas': os.getenv('EMAIL_NICOLAS', 'nicolas@example.com'),
        'allan': os.getenv('EMAIL_ALLAN', 'allan@example.com'),
        'louise': os.getenv('EMAIL_LOUISE', 'louise@example.com'),
    }

    # Email expéditeur (utilise asutton@piano-tek.com qui est vérifié dans SendGrid)
    FROM_EMAIL = os.getenv('EMAIL_FROM', 'asutton@piano-tek.com')
    FROM_NAME = os.getenv('EMAIL_FROM_NAME', 'Assistant Gazelle')

    def __init__(self):
        """Initialise le client SendGrid."""
        api_key_raw = os.getenv('SENDGRID_API_KEY')
        # Retirer les espaces et sauts de ligne (problème courant dans .env)
        self.api_key = api_key_raw.strip() if api_key_raw else None
        if not self.api_key:
            print("⚠️ SENDGRID_API_KEY non configurée - emails désactivés")
            self.client = None
        else:
            self.client = SendGridAPIClient(self.api_key)

    def send_email(
        self,
        to_emails: List[str],
        subject: str,
        html_content: str,
        plain_content: Optional[str] = None
    ) -> bool:
        """
        Envoie un email via SendGrid.

        Args:
            to_emails: Liste d'emails destinataires
            subject: Sujet de l'email
            html_content: Contenu HTML de l'email
            plain_content: Contenu texte brut (optionnel, sinon extrait du HTML)

        Returns:
            True si envoyé avec succès
        """
        if not self.client:
            print("⚠️ Client SendGrid non initialisé - email non envoyé")
            return False

        try:
            # Créer l'email
            message = Mail(
                from_email=Email(self.FROM_EMAIL, self.FROM_NAME),
                to_emails=[To(email) for email in to_emails],
                subject=subject,
                html_content=Content("text/html", html_content)
            )

            # Ajouter contenu texte si fourni
            if plain_content:
                message.plain_text_content = Content("text/plain", plain_content)

            # Envoyer
            response = self.client.send(message)

            if response.status_code in [200, 202]:
                print(f"✅ Email envoyé avec succès à {len(to_emails)} destinataire(s)")
                return True
            else:
                print(f"⚠️ Erreur SendGrid {response.status_code}: {response.body}")
                return False

        except Exception as e:
            print(f"❌ Erreur lors de l'envoi email: {e}")
            return False

    def send_humidity_alert(
        self,
        piano_info: dict,
        humidity_value: float,
        alert_type: str,
        recipient: str = 'nicolas'
    ) -> bool:
        """
        Envoie une alerte d'humidité par email.

        Args:
            piano_info: Informations sur le piano (nom, client, lieu)
            humidity_value: Valeur d'humidité détectée
            alert_type: Type d'alerte ('TROP_SEC' ou 'TROP_HUMIDE')
            recipient: Destinataire (nom dans RECIPIENTS)

        Returns:
            True si envoyé avec succès
        """
        recipient_email = self.RECIPIENTS.get(recipient)
        if not recipient_email:
            print(f"⚠️ Destinataire '{recipient}' inconnu")
            return False

        # Emoji selon le type
        emoji = "🏜️" if alert_type == "TROP_SEC" else "💧"
        
        # Couleur selon le type
        color = "#FF6B6B" if alert_type == "TROP_SEC" else "#4ECDC4"

        # Construire le message HTML
        html_content = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; }}
                .alert-box {{ 
                    background: {color}; 
                    color: white; 
                    padding: 20px; 
                    border-radius: 8px;
                    margin: 20px 0;
                }}
                .info-box {{
                    background: #f5f5f5;
                    padding: 15px;
                    border-left: 4px solid {color};
                    margin: 15px 0;
                }}
                .value {{
                    font-size: 24px;
                    font-weight: bold;
                }}
            </style>
        </head>
        <body>
            <div class="alert-box">
                <h2>{emoji} Alerte Humidité - {alert_type.replace('_', ' ')}</h2>
            </div>
            
            <div class="info-box">
                <p><strong>Piano:</strong> {piano_info.get('nom', 'Inconnu')}</p>
                <p><strong>Client:</strong> {piano_info.get('client', 'Inconnu')}</p>
                <p><strong>Lieu:</strong> {piano_info.get('lieu', 'Inconnu')}</p>
                <p class="value"><strong>Humidité:</strong> {humidity_value}%</p>
            </div>

            <p>Cette alerte a été détectée lors du scan automatique nocturne.</p>
            <p>Consultez le Dashboard pour plus de détails.</p>
        </body>
        </html>
        """

        subject = f"{emoji} Alerte Humidité: {piano_info.get('nom', 'Piano')} ({humidity_value}%)"

        return self.send_email(
            to_emails=[recipient_email],
            subject=subject,
            html_content=html_content
        )

    def send_sync_error_notification(
        self,
        task_name: str,
        error_message: str,
        recipient: str = 'nicolas'
    ) -> bool:
        """
        Envoie une notification d'erreur de synchronisation.

        Args:
            task_name: Nom de la tâche qui a échoué
            error_message: Message d'erreur
            recipient: Destinataire (nom dans RECIPIENTS)

        Returns:
            True si envoyé avec succès
        """
        recipient_email = self.RECIPIENTS.get(recipient)
        if not recipient_email:
            print(f"⚠️ Destinataire '{recipient}' inconnu")
            return False

        html_content = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; }}
                .error-box {{ 
                    background: #FF6B6B; 
                    color: white; 
                    padding: 20px; 
                    border-radius: 8px;
                    margin: 20px 0;
                }}
                .error-details {{
                    background: #f5f5f5;
                    padding: 15px;
                    border-left: 4px solid #FF6B6B;
                    margin: 15px 0;
                    font-family: monospace;
                }}
            </style>
        </head>
        <body>
            <div class="error-box">
                <h2>❌ Erreur de Synchronisation</h2>
                <p><strong>Tâche:</strong> {task_name}</p>
            </div>
            
            <div class="error-details">
                <p><strong>Erreur:</strong></p>
                <pre>{error_message}</pre>
            </div>

            <p>Cette erreur nécessite votre attention.</p>
            <p>Consultez le Dashboard → Logs de Santé pour plus de détails.</p>
        </body>
        </html>
        """

        subject = f"❌ Erreur Sync: {task_name}"

        return self.send_email(
            to_emails=[recipient_email],
            subject=subject,
            html_content=html_content
        )


# Singleton
_notifier: Optional[EmailNotifier] = None


def get_email_notifier() -> EmailNotifier:
    """Retourne l'instance du notifier (singleton)."""
    global _notifier
    if _notifier is None:
        _notifier = EmailNotifier()
    return _notifier
