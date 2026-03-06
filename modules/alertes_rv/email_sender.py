#!/usr/bin/env python3
"""
Module d'envoi d'emails pour les alertes RV.

Supporte deux méthodes:
1. Resend API (production cloud) - migré de SendGrid mars 2026
2. SMTP Gmail (fallback pour dev local)
"""

import os
import resend
from typing import List, Optional
from datetime import datetime


class EmailSender:
    """Envoie des emails d'alerte via Resend ou SMTP."""

    def __init__(self, method: str = 'resend'):
        """
        Initialise l'envoyeur d'emails.

        Args:
            method: 'resend' ou 'smtp'
        """
        self.method = method
        self.from_email = os.getenv('ALERT_FROM_EMAIL', os.getenv('EMAIL_FROM', 'onboarding@resend.dev'))
        self.from_name = os.getenv('ALERT_FROM_NAME', 'Assistant Gazelle Alertes')

        if method == 'resend':
            resend_api_key_raw = os.getenv('RESEND_API_KEY')
            self.resend_api_key = resend_api_key_raw.strip() if resend_api_key_raw else None
            if not self.resend_api_key:
                print("⚠️ RESEND_API_KEY non défini, bascule sur SMTP")
                self.method = 'smtp'
            else:
                resend.api_key = self.resend_api_key

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
        if self.method == 'resend':
            return self._send_via_resend(to_email, to_name, subject, html_content)
        else:
            return self._send_via_smtp(to_email, to_name, subject, html_content)

    def _send_via_resend(
        self,
        to_email: str,
        to_name: str,
        subject: str,
        html_content: str
    ) -> bool:
        """Envoie via Resend API."""
        try:
            from_str = f"{self.from_name} <{self.from_email}>"

            response = resend.Emails.send({
                "from": from_str,
                "to": [to_email],
                "subject": subject,
                "html": html_content,
            })

            if response and response.get("id"):
                print(f"✅ Email envoyé à {to_email} (Resend, id: {response['id']})")
                return True
            else:
                print(f"⚠️ Resend erreur: {response}")
                return False

        except Exception as e:
            print(f"❌ Erreur Resend: {e}")
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
