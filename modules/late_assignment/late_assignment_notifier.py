#!/usr/bin/env python3
"""
Module de notification pour les assignations tardives (< 24h).

Traite la file d'attente late_assignment_queue et envoie les emails
aux techniciens lorsqu'un RV leur est assigné/réassigné moins de 24h avant.
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

# Ajouter le projet au path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dotenv import load_dotenv
load_dotenv()

from core.supabase_storage import SupabaseStorage
from core.email_notifier import EmailNotifier
from core.timezone_utils import MONTREAL_TZ
import requests


class LateAssignmentNotifier:
    """Gère l'envoi des alertes pour les assignations tardives."""
    
    def __init__(self):
        """Initialise le notifier."""
        self.storage = SupabaseStorage(silent=True)
        self.email_notifier = EmailNotifier()
    
    def process_queue(self) -> Dict[str, Any]:
        """
        Traite la file d'attente et envoie les emails programmés.
        
        Returns:
            Dict avec stats (processed, sent, failed)
        """
        print("\n📧 Traitement de la file d'attente late_assignment_queue...")
        
        now = datetime.now(MONTREAL_TZ)
        # Convertir en UTC pour la comparaison (scheduled_send_at est stocké en UTC)
        from datetime import timezone
        now_utc = now.astimezone(timezone.utc)
        # Formater en ISO sans timezone pour Supabase (qui attend UTC)
        now_utc_str = now_utc.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
        
        # Récupérer les alertes à envoyer (scheduled_send_at <= now, status = pending)
        try:
            url = (
                f"{self.storage.api_url}/late_assignment_queue"
                f"?scheduled_send_at=lte.{now_utc_str}"
                f"&status=eq.pending"
                f"&order=scheduled_send_at.asc"
            )
            response = requests.get(url, headers=self.storage._get_headers())
            
            if response.status_code != 200:
                print(f"❌ Erreur récupération queue: {response.status_code}")
                return {'processed': 0, 'sent': 0, 'failed': 0, 'errors': [f"Erreur API: {response.status_code}"]}
            
            queue_items = response.json() or []
            
            if not queue_items:
                print("   ✅ Aucune alerte à envoyer")
                return {'processed': 0, 'sent': 0, 'failed': 0}
            
            print(f"   📋 {len(queue_items)} alerte(s) à traiter")
            
            stats = {'processed': 0, 'sent': 0, 'failed': 0, 'errors': []}
            
            for item in queue_items:
                stats['processed'] += 1
                success = self._send_alert(item)
                
                if success:
                    stats['sent'] += 1
                    # Marquer comme envoyé
                    self._mark_as_sent(item['id'])
                else:
                    stats['failed'] += 1
                    # Marquer comme failed
                    self._mark_as_failed(item['id'], "Erreur lors de l'envoi")
            
            print(f"   ✅ Traitement terminé: {stats['sent']} envoyé(s), {stats['failed']} échec(s)")
            return stats
            
        except Exception as e:
            error_msg = f"Erreur traitement queue: {e}"
            print(f"❌ {error_msg}")
            import traceback
            traceback.print_exc()
            return {'processed': 0, 'sent': 0, 'failed': 0, 'errors': [error_msg]}
    
    def _send_alert(self, queue_item: Dict[str, Any]) -> bool:
        """
        Envoie l'email d'alerte pour un item de la queue.
        
        Args:
            queue_item: Item de la queue (avec appointment_external_id, technician_id, etc.)
            
        Returns:
            True si envoyé avec succès
        """
        try:
            technician_id = queue_item.get('technician_id')
            appointment_date = queue_item.get('appointment_date')
            appointment_time = queue_item.get('appointment_time', '')
            client_name = queue_item.get('client_name', 'Client')
            location = queue_item.get('location', '')
            
            # Récupérer l'email du technicien depuis la table users
            user = self._get_user_by_external_id(technician_id)
            if not user:
                print(f"   ⚠️  Technicien {technician_id} non trouvé dans users")
                return False
            
            email = user.get('email')
            first_name = user.get('first_name', '')
            last_name = user.get('last_name', '')
            technician_name = f"{first_name} {last_name}".strip() or f"Technicien {technician_id}"
            
            if not email:
                print(f"   ⚠️  Pas d'email pour technicien {technician_id}")
                return False
            
            # Déterminer "aujourd'hui" ou "demain"
            today = datetime.now(MONTREAL_TZ).date()
            appt_date = None
            if isinstance(appointment_date, str):
                from datetime import date as date_class
                try:
                    appt_date = date_class.fromisoformat(appointment_date)
                except:
                    pass
            
            if appt_date:
                if appt_date == today:
                    date_text = "aujourd'hui"
                elif appt_date == today + timedelta(days=1):
                    date_text = "demain"
                else:
                    date_text = f"le {appt_date.strftime('%d %B %Y')}"
            else:
                date_text = "prochainement"
            
            # Construire le message
            time_text = f" à {appointment_time}" if appointment_time else ""
            location_text = f", {location}" if location else ""
            
            subject = "⚠️ Nouveau rendez-vous assigné (Action requise)"
            
            plain_content = (
                f"Bonjour {technician_name},\n\n"
                f"Un nouveau rendez-vous a été ajouté ou vous a été réassigné pour {date_text} :\n"
                f"{location_text.lstrip(', ')}{time_text}, {client_name}.\n\n"
                f"Merci de consulter 'Ma Journée' pour les détails.\n\n"
                f"Cordialement,\n"
                f"Assistant Gazelle"
            )
            
            # Envoyer l'email (texte brut uniquement)
            success = self.email_notifier.send_email(
                to_emails=[email],
                subject=subject,
                html_content=plain_content.replace('\n', '<br>'),  # Simple conversion pour SendGrid
                plain_content=plain_content
            )
            
            if success:
                print(f"   ✅ Email envoyé à {email} pour RV {queue_item.get('appointment_external_id')}")
            else:
                print(f"   ❌ Échec envoi email à {email}")
            
            return success
            
        except Exception as e:
            print(f"   ❌ Erreur envoi alerte {queue_item.get('id')}: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _get_user_by_external_id(self, external_id: str) -> Optional[Dict[str, Any]]:
        """
        Récupère un utilisateur par son external_id (technician_id Gazelle).
        
        Args:
            external_id: ID externe du technicien
            
        Returns:
            Dict avec les infos utilisateur ou None
        """
        try:
            url = f"{self.storage.api_url}/users?external_id=eq.{external_id}&select=email,first_name,last_name"
            response = requests.get(url, headers=self.storage._get_headers())
            
            if response.status_code == 200:
                users = response.json()
                if users and len(users) > 0:
                    return users[0]
            return None
            
        except Exception as e:
            print(f"   ⚠️  Erreur récupération user {external_id}: {e}")
            return None
    
    def _mark_as_sent(self, queue_id: str):
        """Marque un item de la queue comme envoyé."""
        try:
            url = f"{self.storage.api_url}/late_assignment_queue?id=eq.{queue_id}"
            headers = self.storage._get_headers()
            headers["Prefer"] = "return=representation"
            
            data = {
                'status': 'sent',
                'sent_at': datetime.now(MONTREAL_TZ).isoformat(),
                'updated_at': datetime.now(MONTREAL_TZ).isoformat()
            }
            
            requests.patch(url, headers=headers, json=data)
            
        except Exception as e:
            print(f"   ⚠️  Erreur marquage sent {queue_id}: {e}")
    
    def _mark_as_failed(self, queue_id: str, error_message: str):
        """Marque un item de la queue comme échoué."""
        try:
            url = f"{self.storage.api_url}/late_assignment_queue?id=eq.{queue_id}"
            headers = self.storage._get_headers()
            headers["Prefer"] = "return=representation"
            
            data = {
                'status': 'failed',
                'error_message': error_message[:500],  # Limiter la longueur
                'updated_at': datetime.now(MONTREAL_TZ).isoformat()
            }
            
            requests.patch(url, headers=headers, json=data)
            
        except Exception as e:
            print(f"   ⚠️  Erreur marquage failed {queue_id}: {e}")


def main():
    """Point d'entrée pour exécution standalone."""
    notifier = LateAssignmentNotifier()
    result = notifier.process_queue()
    print(f"\n📊 Résultat: {result}")
    return result


if __name__ == '__main__':
    main()
