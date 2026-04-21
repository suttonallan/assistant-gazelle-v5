#!/usr/bin/env python3
"""
Module d'envoi d'emails pour les alertes RV.

Priorite : Gmail API (OAuth2) > Resend > SMTP.
Historique : SendGrid -> Resend (mars 2026) -> Gmail API (mars 2026).

REGLE DE HONNETETE : si un envoi echoue ou n'est pas possible, on retourne
False. Pas de mode simulation qui ment : les alertes manquees doivent
apparaitre comme 'failed' dans alert_logs pour qu'Allan le voie.
"""

import os
from typing import List
from datetime import datetime


class EmailSender:
    """Envoie des emails d'alerte via Gmail API, Resend ou SMTP."""

    def __init__(self, method: str = 'gmail'):
        """
        Initialise l'envoyeur d'emails.

        Args:
            method: 'gmail', 'resend' ou 'smtp'. La valeur sert de preference
                    initiale ; si la methode demandee n'est pas disponible,
                    on fait automatiquement le fallback dans l'ordre
                    Gmail -> Resend -> SMTP.
        """
        self.method = None
        self._gmail_sender = None
        self.resend_api_key = None
        self.from_email = os.getenv('ALERT_FROM_EMAIL', os.getenv('EMAIL_FROM', 'asutton@piano-tek.com'))
        self.from_name = os.getenv('ALERT_FROM_NAME', 'Assistant Gazelle Alertes')

        # 1. Tenter Gmail API (priorite absolue)
        try:
            from core.gmail_sender import get_gmail_sender
            gmail = get_gmail_sender()
            if gmail.is_available:
                self._gmail_sender = gmail
                self.method = 'gmail'
                print("✅ EmailSender : Gmail API active")
                return
        except Exception as exc:
            print(f"⚠️ Gmail API non disponible : {exc}")

        # 2. Fallback sur Resend
        try:
            import resend
            resend_api_key_raw = os.getenv('RESEND_API_KEY')
            self.resend_api_key = resend_api_key_raw.strip() if resend_api_key_raw else None
            if self.resend_api_key:
                resend.api_key = self.resend_api_key
                self.method = 'resend'
                print("✅ EmailSender : Resend active (fallback)")
                return
        except Exception:
            pass

        # 3. Fallback sur SMTP
        if os.getenv('SMTP_USER') and os.getenv('SMTP_PASSWORD'):
            self.method = 'smtp'
            print("⚠️ EmailSender : SMTP active (dernier fallback)")
            return

        # Rien de configure : on log fort et on echouera honnetement
        self.method = None
        print("🚨 CRITIQUE : aucune methode d'envoi email disponible "
              "(ni Gmail API token, ni RESEND_API_KEY, ni SMTP creds). "
              "AUCUN email d'alerte ne partira. Configure une methode sur Render.")

    def send_email(
        self,
        to_email: str,
        to_name: str,
        subject: str,
        html_content: str
    ) -> bool:
        """Envoie un email. Retourne True UNIQUEMENT si un email reel a ete transmis."""
        if self.method == 'gmail' and self._gmail_sender:
            return self._gmail_sender.send_email(
                to_emails=[to_email],
                subject=subject,
                html_content=html_content,
            )
        if self.method == 'resend':
            return self._send_via_resend(to_email, to_name, subject, html_content)
        if self.method == 'smtp':
            return self._send_via_smtp(to_email, to_name, subject, html_content)
        # Aucune methode disponible
        print(f"❌ Aucune methode d'envoi active - email NON envoye a {to_email}")
        return False

    def _send_via_resend(
        self,
        to_email: str,
        to_name: str,
        subject: str,
        html_content: str
    ) -> bool:
        """Fallback Resend."""
        try:
            import resend
            from_str = f"{self.from_name} <{self.from_email}>"
            response = resend.Emails.send({
                "from": from_str,
                "to": [to_email],
                "subject": subject,
                "html": html_content,
            })
            if response and response.get("id"):
                print(f"✅ Email envoye a {to_email} (Resend, id: {response['id']})")
                return True
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
        """Dernier fallback SMTP Gmail."""
        smtp_user = os.getenv('SMTP_USER')
        smtp_password = os.getenv('SMTP_PASSWORD')
        if not smtp_user or not smtp_password:
            print(f"❌ SMTP_USER/SMTP_PASSWORD manquants - email NON envoye a {to_email}")
            return False
        try:
            import smtplib
            from email.mime.multipart import MIMEMultipart
            from email.mime.text import MIMEText

            msg = MIMEMultipart('alternative')
            msg['From'] = f"{self.from_name} <{self.from_email}>"
            msg['To'] = f"{to_name} <{to_email}>"
            msg['Subject'] = subject
            msg.attach(MIMEText(html_content, 'html'))

            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(msg)
            server.quit()

            print(f"✅ Email envoye a {to_email} (SMTP)")
            return True
        except Exception as e:
            print(f"❌ Erreur SMTP: {e} - Email NON envoye a {to_email}")
            return False

    def send_batch_alerts(self, alerts: List[dict]) -> dict:
        """Envoie plusieurs alertes en batch. Retourne le rapport."""
        results = {'success': 0, 'failed': 0, 'details': []}
        for alert in alerts:
            success = self.send_email(
                to_email=alert['to_email'],
                to_name=alert['to_name'],
                subject=alert['subject'],
                html_content=alert['html_content'],
            )
            if success:
                results['success'] += 1
            else:
                results['failed'] += 1
            results['details'].append({
                'to_email': alert['to_email'],
                'success': success,
                'timestamp': datetime.now().isoformat(),
            })
        return results
