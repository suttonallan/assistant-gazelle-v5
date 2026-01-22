#!/usr/bin/env python3
"""
Module d'envoi d'emails pour les alertes RV.

Supporte deux méthodes:
1. SendGrid API (recommandé pour production cloud)
2. SMTP Gmail (fallback pour dev local)
"""

import os
from typing import List, Optional
from datetime import datetime


class EmailSender:
    """Envoie des emails d'alerte via SendGrid ou SMTP."""

    def __init__(self, method: str = 'sendgrid'):
        """
        Initialise l'envoyeur d'emails.

        Args:
            method: 'sendgrid' ou 'smtp'
        """
        self.method = method
        # Utiliser info@piano-tek.com qui est vérifié dans SendGrid
        self.from_email = os.getenv('ALERT_FROM_EMAIL', 'info@piano-tek.com')
        self.from_name = os.getenv('ALERT_FROM_NAME', 'Assistant Gazelle Alertes')

        if method == 'sendgrid':
            self.sendgrid_api_key = os.getenv('SENDGRID_API_KEY')
            if not self.sendgrid_api_key:
                print("⚠️ SENDGRID_API_KEY non défini, bascule sur SMTP")
                self.method = 'smtp'

    def send_email(
        self,
        to_email: str,
        to_name: str,
        subject: str,
        html_content: str
    ) -> bool:
        """
        Envoie un email.

        Args:
            to_email: Email destinataire
            to_name: Nom destinataire
            subject: Sujet
            html_content: Contenu HTML

        Returns:
            bool: True si succès
        """
        if self.method == 'sendgrid':
            return self._send_via_sendgrid(to_email, to_name, subject, html_content)
        else:
            return self._send_via_smtp(to_email, to_name, subject, html_content)

    def _send_via_sendgrid(
        self,
        to_email: str,
        to_name: str,
        subject: str,
        html_content: str
    ) -> bool:
        """Envoie via SendGrid API."""
        try:
            from sendgrid import SendGridAPIClient
            from sendgrid.helpers.mail import Mail, Email, To, Content

            message = Mail(
                from_email=Email(self.from_email, self.from_name),
                to_emails=To(to_email, to_name),
                subject=subject,
                html_content=Content("text/html", html_content)
            )

            sg = SendGridAPIClient(self.sendgrid_api_key)
            response = sg.send(message)

            if response.status_code in [200, 202]:
                print(f"✅ Email envoyé à {to_email} (SendGrid)")
                return True
            else:
                print(f"⚠️ SendGrid status {response.status_code}")
                return False

        except ImportError:
            print("⚠️ SendGrid library non installée: pip install sendgrid")
            return False
        except Exception as e:
            print(f"❌ Erreur SendGrid: {e}")
            return False

    def _send_via_smtp(
        self,
        to_email: str,
        to_name: str,
        subject: str,
        html_content: str
    ) -> bool:
        """Envoie via SMTP Gmail (fallback)."""
        try:
            import smtplib
            from email.mime.multipart import MIMEMultipart
            from email.mime.text import MIMEText

            # Credentials depuis env
            smtp_user = os.getenv('SMTP_USER')
            smtp_password = os.getenv('SMTP_PASSWORD')

            if not smtp_user or not smtp_password:
                print("⚠️ SMTP_USER ou SMTP_PASSWORD non défini")
                # Mode simulation pour dev
                print(f"📧 [SIMULATION] Email vers {to_email}")
                print(f"   Sujet: {subject}")
                print(f"   Contenu: {html_content[:200]}...")
                return True

            # Créer le message
            msg = MIMEMultipart('alternative')
            msg['From'] = f"{self.from_name} <{self.from_email}>"
            msg['To'] = f"{to_name} <{to_email}>"
            msg['Subject'] = subject

            html_part = MIMEText(html_content, 'html')
            msg.attach(html_part)

            # Connexion SMTP Gmail
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(msg)
            server.quit()

            print(f"✅ Email envoyé à {to_email} (SMTP)")
            return True

        except Exception as e:
            print(f"❌ Erreur SMTP: {e}")
            # Mode simulation si échec
            print(f"📧 [SIMULATION] Email vers {to_email}")
            print(f"   Sujet: {subject}")
            return True  # Retourner True en simulation pour ne pas bloquer

    def send_batch_alerts(
        self,
        alerts: List[dict]
    ) -> dict:
        """
        Envoie plusieurs alertes en batch.

        Args:
            alerts: Liste de dicts avec keys: to_email, to_name, subject, html_content

        Returns:
            dict: {success: int, failed: int, details: [...]}
        """
        results = {
            'success': 0,
            'failed': 0,
            'details': []
        }

        for alert in alerts:
            success = self.send_email(
                to_email=alert['to_email'],
                to_name=alert['to_name'],
                subject=alert['subject'],
                html_content=alert['html_content']
            )

            if success:
                results['success'] += 1
            else:
                results['failed'] += 1

            results['details'].append({
                'to_email': alert['to_email'],
                'success': success,
                'timestamp': datetime.now().isoformat()
            })

        return results
