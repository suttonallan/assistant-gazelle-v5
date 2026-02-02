#!/usr/bin/env python3
"""
Module pour envoyer des notifications Slack.
Utilisé pour les commentaires d'inventaire et alertes diverses.
"""

import os
import requests
from typing import Optional, Dict, Any, List


class SlackNotifier:
    """Gère l'envoi de notifications Slack via webhooks."""

    # Webhooks par technicien (chargés depuis .env)
    TECH_WEBHOOKS = {
        'Allan': os.getenv('SLACK_WEBHOOK_ALLAN'),
        'Nicolas': os.getenv('SLACK_WEBHOOK_NICOLAS'),
        'Jean-Philippe': os.getenv('SLACK_WEBHOOK_JEANPHILIPPE')
    }

    # Webhooks administrateurs (chargés depuis .env)
    ADMIN_WEBHOOKS = [
        os.getenv('SLACK_WEBHOOK_ADMIN_1'),  # Louise
        os.getenv('SLACK_WEBHOOK_ADMIN_2')   # Nicolas
    ]

    @staticmethod
    def send_simple_message(webhook_url: str, text: str) -> bool:
        """
        Envoie un message Slack simple.

        Args:
            webhook_url: URL du webhook Slack
            text: Texte du message

        Returns:
            True si envoyé avec succès
        """
        # Guard: skip if webhook not configured
        if not webhook_url:
            return False

        try:
            payload = {"text": text}
            response = requests.post(webhook_url, json=payload, timeout=5)

            if response.status_code == 200:
                print(f"✅ Message Slack envoyé avec succès")
                return True
            else:
                print(f"⚠️ Erreur Slack {response.status_code}: {response.text}")
                return False

        except Exception as e:
            print(f"⚠️ Erreur lors de l'envoi Slack: {e}")
            return False

    @staticmethod
    def send_blocks_message(
        webhook_url: str,
        text: str,
        blocks: Optional[List[Dict[str, Any]]] = None
    ) -> bool:
        """
        Envoie un message Slack avec formatage avancé (blocks).

        Args:
            webhook_url: URL du webhook Slack
            text: Texte de fallback
            blocks: Blocs de formatage Slack

        Returns:
            True si envoyé avec succès
        """
        # Guard: skip if webhook not configured
        if not webhook_url:
            return False

        try:
            payload = {"text": text}
            if blocks:
                payload["blocks"] = blocks

            response = requests.post(webhook_url, json=payload, timeout=5)

            if response.status_code == 200:
                print(f"✅ Message Slack (blocks) envoyé avec succès")
                return True
            else:
                print(f"⚠️ Erreur Slack {response.status_code}: {response.text}")
                return False

        except Exception as e:
            print(f"⚠️ Erreur lors de l'envoi Slack: {e}")
            return False

    @classmethod
    def notify_admin(cls, message: str) -> bool:
        """
        Envoie une notification aux administrateurs (Allan/Louise/Nicolas).

        Args:
            message: Message à envoyer

        Returns:
            True si au moins un webhook a réussi
        """
        results = []
        for webhook in cls.ADMIN_WEBHOOKS:
            result = cls.send_simple_message(webhook, message)
            results.append(result)

        return any(results)

    @classmethod
    def notify_technician(cls, tech_name: str, message: str) -> bool:
        """
        Envoie une notification à un technicien spécifique.

        Args:
            tech_name: Nom du technicien (Allan, Nicolas, Jean-Philippe)
            message: Message à envoyer

        Returns:
            True si envoyé avec succès
        """
        webhook = cls.TECH_WEBHOOKS.get(tech_name)
        if not webhook:
            print(f"⚠️ Webhook introuvable pour {tech_name}")
            return False

        return cls.send_simple_message(webhook, message)

    @classmethod
    def notify_inventory_comment(
        cls,
        username: str,
        comment: str,
        notify_admin: bool = True
    ) -> bool:
        """
        Envoie une notification pour un commentaire d'inventaire.
        Format V4: "[Username] Inventaire: [Comment]"

        Args:
            username: Nom de l'utilisateur (ex: "Allan")
            comment: Texte du commentaire
            notify_admin: Si True, notifie les admins (défaut: True)

        Returns:
            True si envoyé avec succès
        """
        message = f"📦 *Inventaire - {username}*\n{comment}"

        if notify_admin:
            return cls.notify_admin(message)
        else:
            return cls.notify_technician(username, message)
