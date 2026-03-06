#!/usr/bin/env python3
"""
Module pour envoyer des notifications par email.
Utilise Resend pour l'envoi d'emails (alertes humidité, erreurs système, etc.)
Historique: Migration de SendGrid vers Resend (mars 2026) - essai gratuit SendGrid expiré.
"""

import os
import resend
from typing import Optional, List


class EmailNotifier:
    """Gère l'envoi d'emails via Resend."""

    # Configuration des destinataires (chargés depuis .env)
    RECIPIENTS = {
        'nicolas': os.getenv('EMAIL_NICOLAS', 'nlessard@piano-tek.com'),
        'allan': os.getenv('EMAIL_ALLAN', 'allan@example.com'),
        'louise': os.getenv('EMAIL_LOUISE', 'louise@example.com'),
    }

    # Email expéditeur - utilise onboarding@resend.dev tant que le domaine n'est pas vérifié
    # Une fois piano-tek.com vérifié dans Resend, changer pour asutton@piano-tek.com
    FROM_EMAIL = os.getenv('EMAIL_FROM', 'onboarding@resend.dev')
    FROM_NAME = os.getenv('EMAIL_FROM_NAME', 'Assistant Gazelle')

    def __init__(self):
        """Initialise le client Resend."""
        api_key_raw = os.getenv('RESEND_API_KEY')
        # Retirer les espaces et sauts de ligne (problème courant dans .env)
        self.api_key = api_key_raw.strip() if api_key_raw else None
        if not self.api_key:
            print("⚠️ RESEND_API_KEY non configurée - emails désactivés")
            self.client = None
        else:
            resend.api_key = self.api_key
            self.client = True
            print("✅ Resend initialisé avec succès")

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
            print("⚠️ Client Resend non initialisé - email non envoyé")
            return False

        try:
            from_str = f"{self.FROM_NAME} <{self.FROM_EMAIL}>"

            params = {
                "from": from_str,
                "to": to_emails,
                "subject": subject,
                "html": html_content,
            }

            if plain_content:
                params["text"] = plain_content

            response = resend.Emails.send(params)

            if response and response.get("id"):
                print(f"✅ Email envoyé avec succès à {len(to_emails)} destinataire(s) (id: {response['id']})")
                return True
            else:
                print(f"⚠️ Erreur Resend: {response}")
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

    def send_inventory_comment(
        self,
        username: str,
        comment: str
    ) -> bool:
        """
        Envoie un commentaire d'inventaire au CTO (Allan).

        Args:
            username: Nom du technicien qui envoie
            comment: Texte du commentaire

        Returns:
            True si envoyé avec succès
        """
        # Toujours envoyer au CTO (Allan)
        cto_email = 'asutton@piano-tek.com'

        html_content = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; }}
                .comment-box {{
                    background: #3B82F6;
                    color: white;
                    padding: 20px;
                    border-radius: 8px;
                    margin: 20px 0;
                }}
                .message-box {{
                    background: #f5f5f5;
                    padding: 15px;
                    border-left: 4px solid #3B82F6;
                    margin: 15px 0;
                }}
            </style>
        </head>
        <body>
            <div class="comment-box">
                <h2>📦 Commentaire Inventaire</h2>
                <p><strong>De:</strong> {username}</p>
            </div>

            <div class="message-box">
                <p>{comment}</p>
            </div>

            <p style="color: #666; font-size: 12px;">
                Envoyé depuis le Dashboard Inventaire V5
            </p>
        </body>
        </html>
        """

        subject = f"📦 Inventaire - {username}"

        return self.send_email(
            to_emails=[cto_email],
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
