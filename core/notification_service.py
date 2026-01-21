#!/usr/bin/env python3
"""
Service de notifications unifié pour Assistant Gazelle V5.

Routage intelligent des notifications:
- Erreurs de sync → Slack (admins)
- Alertes humidité → Email (Nicolas) + Slack (optionnel)
- Alertes RV → Email (techniciens concernés)
- Messages admin → Slack

Configuration centralisée et facile à modifier.
"""

from typing import Optional, List, Dict, Any
from core.slack_notifier import SlackNotifier
from core.email_notifier import EmailNotifier, get_email_notifier


class NotificationService:
    """Service centralisé pour gérer toutes les notifications."""

    def __init__(self):
        """Initialise les notifiers."""
        self.slack = SlackNotifier()
        self.email = get_email_notifier()

    def notify_sync_error(
        self,
        task_name: str,
        error_message: str,
        send_slack: bool = True,
        send_email: bool = False
    ) -> Dict[str, bool]:
        """
        Notifie une erreur de synchronisation.

        Par défaut: Slack seulement (rapide, temps réel)
        Option: Email également pour les erreurs critiques

        Args:
            task_name: Nom de la tâche qui a échoué
            error_message: Message d'erreur
            send_slack: Envoyer notification Slack (défaut: True)
            send_email: Envoyer notification Email (défaut: False)

        Returns:
            Dict avec les résultats: {'slack': bool, 'email': bool}
        """
        results = {'slack': False, 'email': False}

        # Message Slack
        if send_slack:
            slack_message = f"❌ *Erreur Synchronisation*\n\n" \
                          f"*Tâche:* {task_name}\n" \
                          f"*Erreur:* {error_message}\n\n" \
                          f"Consultez le Dashboard → Logs de Santé"
            
            results['slack'] = self.slack.notify_admin(slack_message)

        # Email (optionnel, pour erreurs critiques)
        if send_email:
            results['email'] = self.email.send_sync_error_notification(
                task_name=task_name,
                error_message=error_message,
                recipient='nicolas'
            )

        return results

    def notify_humidity_alert(
        self,
        piano_info: dict,
        humidity_value: float,
        alert_type: str,
        send_email: bool = True,
        send_slack: bool = True
    ) -> Dict[str, bool]:
        """
        Notifie une alerte d'humidité.

        Par défaut: Email (Nicolas) + Slack (Louise + Nicolas)

        Args:
            piano_info: Informations sur le piano
            humidity_value: Valeur d'humidité détectée
            alert_type: Type d'alerte ('TROP_SEC' ou 'TROP_HUMIDE')
            send_email: Envoyer email à Nicolas (défaut: True)
            send_slack: Envoyer Slack à Louise + Nicolas (défaut: True)

        Returns:
            Dict avec les résultats: {'email': bool, 'slack': bool}
        """
        results = {'email': False, 'slack': False}

        # Email à Nicolas
        if send_email:
            results['email'] = self.email.send_humidity_alert(
                piano_info=piano_info,
                humidity_value=humidity_value,
                alert_type=alert_type,
                recipient='nicolas'
            )

        # Slack à Louise + Nicolas
        if send_slack:
            emoji = "🏜️" if alert_type == "TROP_SEC" else "💧"
            slack_message = f"{emoji} *Alerte Humidité - {alert_type.replace('_', ' ')}*\n\n" \
                          f"*Piano:* {piano_info.get('nom', 'Inconnu')}\n" \
                          f"*Client:* {piano_info.get('client', 'Inconnu')}\n" \
                          f"*Lieu:* {piano_info.get('lieu', 'Inconnu')}\n" \
                          f"*Humidité:* {humidity_value}%\n\n" \
                          f"Consultez le Dashboard pour plus de détails."
            
            results['slack'] = self.slack.notify_admin(slack_message)

        return results

    def notify_sync_success(
        self,
        task_name: str,
        stats: Dict[str, Any],
        send_slack: bool = False
    ) -> bool:
        """
        Notifie le succès d'une synchronisation.

        Par défaut: Pas de notification (éviter le spam)
        Option: Slack pour les syncs importantes

        Args:
            task_name: Nom de la tâche réussie
            stats: Statistiques de la sync
            send_slack: Envoyer notification Slack (défaut: False)

        Returns:
            True si envoyé avec succès (ou si skip)
        """
        if not send_slack:
            return True

        # Message Slack
        stats_text = "\n".join([f"  • {k}: {v}" for k, v in stats.items()])
        slack_message = f"✅ *Synchronisation Réussie*\n\n" \
                      f"*Tâche:* {task_name}\n" \
                      f"*Statistiques:*\n{stats_text}"
        
        return self.slack.notify_admin(slack_message)

    def notify_chain_completion(
        self,
        chain_name: str,
        tasks: List[Dict[str, Any]],
        send_slack: bool = True
    ) -> bool:
        """
        Notifie la complétion d'une chaîne de tâches orchestrées.

        Args:
            chain_name: Nom de la chaîne (ex: "Gazelle → Timeline")
            tasks: Liste des tâches avec leurs statuts
            send_slack: Envoyer notification Slack (défaut: True)

        Returns:
            True si envoyé avec succès
        """
        if not send_slack:
            return True

        # Déterminer le statut global
        all_success = all(t.get('status') == 'success' for t in tasks)
        emoji = "✅" if all_success else "⚠️"

        # Construire le message
        tasks_text = "\n".join([
            f"  {('✅' if t.get('status') == 'success' else '❌')} {t.get('name')}"
            for t in tasks
        ])

        slack_message = f"{emoji} *Chaîne de Tâches: {chain_name}*\n\n" \
                      f"*Tâches:*\n{tasks_text}\n\n" \
                      f"Consultez le Dashboard → Logs de Santé"
        
        return self.slack.notify_admin(slack_message)


# Singleton
_service: Optional[NotificationService] = None


def get_notification_service() -> NotificationService:
    """Retourne l'instance du service (singleton)."""
    global _service
    if _service is None:
        _service = NotificationService()
    return _service
