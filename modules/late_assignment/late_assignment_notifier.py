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
from config.techniciens_config import GAZELLE_IDS, get_technicien_by_id
import os
import json
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
        print("\nTraitement de la file d'attente late_assignment_queue...")
        
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
                print(f"Erreur récupération queue: {response.status_code}")
                return {'processed': 0, 'sent': 0, 'failed': 0, 'errors': [f"Erreur API: {response.status_code}"]}
            
            queue_items = response.json() or []
            
            if not queue_items:
                print("   Aucune alerte à envoyer")
                return {'processed': 0, 'sent': 0, 'failed': 0}
            
            print(f"   {len(queue_items)} alerte(s) à traiter")
            
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
            
            print(f"   Traitement terminé: {stats['sent']} envoyé(s), {stats['failed']} échec(s)")
            return stats
            
        except Exception as e:
            error_msg = f"Erreur traitement queue: {e}"
            print(f"{error_msg}")
            import traceback
            traceback.print_exc()
            return {'processed': 0, 'sent': 0, 'failed': 0, 'errors': [error_msg]}
    
    def _analyze_cancellation(self, appointment_external_id: str) -> Dict[str, Any]:
        """
        Lit la timeline du client d'un RV annulé pour en tirer, quand c'est possible :
          - la RAISON de l'annulation (texte libre, déduit par Claude, jamais inventé) ;
          - l'AUTEUR de l'annulation, c.-à-d. le membre de l'équipe qui l'a faite, via
            l'entrée SYSTEM_MESSAGE « Rendez-vous annulé pour <date> » qui porte son
            user_id.

        Gazelle n'expose ni raison ni « qui a annulé » sur le RV lui-même (l'annulation
        est détectée par absence). La seule trace fiable vit dans la timeline du client.
        On laisse Claude lire ce texte libre (pas un filtre de mots-clés) : il corrèle
        avec la date/titre du RV, en extrait la raison et le user_id de l'auteur.

        Retourne {reason, author_id, author_prenom, author_email}. Tout champ inconnu
        vaut None. Tolérant aux pannes : toute erreur -> dict vide.
        """
        empty = {'reason': None, 'author_id': None, 'author_prenom': None, 'author_email': None}
        try:
            api_key = os.getenv('ANTHROPIC_API_KEY')
            if not api_key:
                return empty

            # 1. Retrouver le client + contexte du RV annulé.
            appt_url = (
                f"{self.storage.api_url}/gazelle_appointments"
                f"?external_id=eq.{appointment_external_id}"
                f"&select=client_external_id,appointment_date,appointment_time,title"
                f"&limit=1"
            )
            appt_resp = requests.get(appt_url, headers=self.storage._get_headers())
            if appt_resp.status_code != 200 or not appt_resp.json():
                return empty
            appt = appt_resp.json()[0]
            client_id = appt.get('client_external_id')
            if not client_id:
                # RV sans client rattaché (ex. note de planif) : pas de timeline à lire.
                return empty

            # 2. Entrées récentes de la timeline du client (texte libre + user_id).
            from core.timezone_utils import MONTREAL_TZ
            now = datetime.now(MONTREAL_TZ)
            cutoff = (now - timedelta(days=21)).strftime('%Y-%m-%dT%H:%M:%S')
            tl_url = (
                f"{self.storage.api_url}/gazelle_timeline_entries"
                f"?client_id=eq.{client_id}"
                f"&occurred_at=gte.{cutoff}"
                f"&order=occurred_at.desc"
                f"&limit=40"
                f"&select=occurred_at,entry_type,user_id,title,description"
            )
            tl_resp = requests.get(tl_url, headers=self.storage._get_headers())
            if tl_resp.status_code != 200 or not tl_resp.json():
                return empty
            entries = tl_resp.json()

            # Compacter les entrées pour le prompt. On expose le user_id entre crochets
            # pour que Claude puisse renvoyer l'auteur de l'annulation.
            known_user_ids = set()
            lines = []
            for e in entries:
                parts = [str(e.get(k, '')).strip() for k in ('title', 'description')]
                txt = ' — '.join([p for p in parts if p])
                if not txt:
                    continue
                uid = (e.get('user_id') or '').strip()
                if uid:
                    known_user_ids.add(uid)
                when = str(e.get('occurred_at', ''))[:16]
                lines.append(f"[{when} | {e.get('entry_type', '')} | {uid or '-'}] {txt}")
            if not lines:
                return empty
            timeline_text = "\n".join(lines[:40])

            # 3. Laisser Claude corréler : raison + user_id de l'auteur de l'annulation.
            from anthropic import Anthropic
            client = Anthropic(api_key=api_key)

            appt_ctx = (
                f"Date du RV annulé : {appt.get('appointment_date', '?')} "
                f"{appt.get('appointment_time', '') or ''}\n"
                f"Titre du RV : {appt.get('title', '') or '(sans titre)'}"
            )
            system_prompt = (
                "Tu analyses la timeline (journal) d'un client de Piano Tek Musique pour "
                "comprendre l'annulation d'un rendez-vous précis. Chaque ligne est "
                "préfixée par [date | type | user_id].\n\n"
                "Extrais DEUX choses :\n"
                "1. raison : POURQUOI ce rendez-vous a été annulé. Base-toi UNIQUEMENT sur "
                "le texte. N'invente jamais. Corrèle avec la date et le titre du RV ; ignore "
                "les entrées sans rapport. Si rien ne l'explique clairement, raison=null. "
                "Courte (max ~12 mots), français du Québec, sans guillemets ni point final.\n"
                "2. auteur_user_id : le user_id (format usr_...) de l'entrée qui ENREGISTRE "
                "l'annulation de CE rendez-vous — souvent un SYSTEM_MESSAGE « Rendez-vous "
                "annulé pour <date> » dont la date/heure correspond au RV. Recopie le "
                "user_id tel quel. Si aucune entrée d'annulation correspondante, "
                "auteur_user_id=null.\n\n"
                'Réponds UNIQUEMENT en JSON : {"raison": <texte|null>, "auteur_user_id": <usr_...|null>}'
            )
            user_content = (
                f"{appt_ctx}\n\n"
                f"Entrées récentes de la timeline du client (plus récentes en haut) :\n"
                f"{timeline_text}"
            )

            response = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=200,
                system=system_prompt,
                messages=[{"role": "user", "content": user_content}],
            )
            raw = response.content[0].text.strip()
            # Extraire le premier objet JSON, même si Claude entoure d'un bloc
            # ``` ou ajoute du texte avant/après (évite les erreurs "Extra data").
            import re
            m = re.search(r'\{.*\}', raw, re.DOTALL)
            if m:
                raw = m.group(0)
            parsed = json.loads(raw)

            # Raison (ou rien).
            reason = parsed.get('raison')
            if reason and str(reason).strip():
                reason = str(reason).strip().rstrip('.')
                if len(reason) > 120:
                    reason = reason[:117] + '...'
            else:
                reason = None

            # Auteur. Garde-fou anti-hallucination : le user_id doit réellement
            # apparaître dans les entrées, ET correspondre à un membre connu de
            # l'équipe (sinon on ne peut ni le nommer ni le contacter).
            author_id = author_prenom = author_email = None
            cand = parsed.get('auteur_user_id')
            cand = str(cand).strip() if cand else ''
            if cand and cand in known_user_ids:
                tech = get_technicien_by_id(cand)
                if tech and tech.get('email'):
                    author_id = cand
                    author_prenom = tech.get('prenom')
                    author_email = tech.get('email')

            return {
                'reason': reason,
                'author_id': author_id,
                'author_prenom': author_prenom,
                'author_email': author_email,
            }

        except Exception as e:
            print(f"   [avertissement] Analyse annulation {appointment_external_id}: {e}")
            return empty

    def _send_documentation_nudge(self, author_prenom: str, author_email: str,
                                  date_text: str, time_text: str,
                                  client_name: str, location: str) -> None:
        """
        Nudge séparé envoyé à la personne qui a annulé un RV sans documenter de raison,
        pour l'inviter à noter une courte raison dans Gazelle la prochaine fois.
        Best-effort : n'interrompt jamais l'alerte au technicien.
        """
        try:
            if not author_email:
                return
            loc = f"{location}, " if location else ""
            subject = "Rappel — documenter l'annulation d'un rendez-vous"
            plain = (
                f"Bonjour {author_prenom},\n\n"
                f"Tu as annulé le rendez-vous {date_text}{time_text} ({loc}{client_name}) "
                f"sans noter de raison dans Gazelle.\n\n"
                f"Quand tu annules un rendez-vous, ajoute une courte note (ex. « annulé à la "
                f"demande du client », « reporté ») : le technicien concerné est alors informé "
                f"automatiquement de la raison.\n\n"
                f"Merci,\n"
                f"Assistant Gazelle"
            )
            self.email_notifier.send_email(
                to_emails=[author_email],
                subject=subject,
                html_content=plain.replace('\n', '<br>'),
                plain_content=plain,
            )
            print(f"   Nudge documentation envoyé à {author_email}")
        except Exception as e:
            print(f"   [avertissement] Nudge documentation: {e}")

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

            # Filtrer: seulement les techniciens connus (pas Louise/assistants)
            if technician_id not in GAZELLE_IDS:
                print(f"   {technician_id} n'est pas un technicien -> alerte ignorée")
                return True  # Retourner True pour marquer comme "traité" sans erreur

            appointment_date = queue_item.get('appointment_date')
            appointment_time = queue_item.get('appointment_time', '')

            # Ne pas envoyer si le RV est déjà passé
            if appointment_date:
                from datetime import date as date_class
                try:
                    appt_date = date_class.fromisoformat(str(appointment_date)[:10])
                    today = datetime.now(MONTREAL_TZ).date()
                    if appt_date < today:
                        print(f"   RV {appointment_date} est passé -> alerte annulée")
                        return True
                except Exception:
                    pass
            client_name = queue_item.get('client_name') or queue_item.get('location') or 'Client'
            location = queue_item.get('location', '')
            
            # Récupérer l'email du technicien depuis techniciens_config (source de vérité)
            tech = get_technicien_by_id(technician_id)
            if not tech:
                print(f"   Technicien {technician_id} non trouvé dans techniciens_config")
                return False

            email = tech['email']
            technician_name = tech['prenom']
            
            if not email:
                print(f"   Pas d'email pour technicien {technician_id}")
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
                    # Format français (le serveur Render est en locale anglaise)
                    mois_fr = ['', 'janvier', 'février', 'mars', 'avril', 'mai', 'juin',
                               'juillet', 'août', 'septembre', 'octobre', 'novembre', 'décembre']
                    date_text = f"le {appt_date.day} {mois_fr[appt_date.month]} {appt_date.year}"
            else:
                date_text = "prochainement"
            
            # Construire le message selon le type de changement
            time_text = f" à {appointment_time}" if appointment_time else ""
            location_text = f", {location}" if location else ""
            change_type = queue_item.get('change_type', 'new')

            # Sujet et corps adaptés au type de changement
            if change_type == 'cancelled':
                subject = "Plage libérée — rendez-vous annulé"
                analysis = self._analyze_cancellation(queue_item.get('appointment_external_id'))
                reason = analysis.get('reason')
                author_prenom = analysis.get('author_prenom')
                author_email = analysis.get('author_email')
                author_id = analysis.get('author_id')

                if reason:
                    reason_text = f"Raison : {reason}.\n\n"
                elif author_prenom and author_id != technician_id:
                    # Annulation non documentée, mais on connaît l'auteur (et ce n'est
                    # pas le tech notifié) : on le nomme ici ET on le relance séparément.
                    reason_text = (
                        f"{author_prenom} a annulé le rendez-vous sans documenter de raison. "
                        f"À contacter au besoin.\n\n"
                    )
                    self._send_documentation_nudge(
                        author_prenom=author_prenom,
                        author_email=author_email,
                        date_text=date_text,
                        time_text=time_text,
                        client_name=client_name,
                        location=location,
                    )
                else:
                    reason_text = "Le système n'a pas trouvé de raison.\n\n"
                plain_content = (
                    f"Bonjour {technician_name},\n\n"
                    f"Le rendez-vous {date_text}{time_text} a été annulé :\n"
                    f"{location_text.lstrip(', ')}, {client_name}.\n\n"
                    f"{reason_text}"
                    f"Cette plage est maintenant libre dans votre calendrier.\n\n"
                    f"Cordialement,\n"
                    f"Assistant Gazelle"
                )
            elif change_type == 'rescheduled':
                subject = "Rendez-vous déplacé"
                plain_content = (
                    f"Bonjour {technician_name},\n\n"
                    f"Un rendez-vous a été déplacé. Nouvelle date : {date_text}{time_text} :\n"
                    f"{location_text.lstrip(', ')}, {client_name}.\n\n"
                    f"Merci de consulter 'Ma Journée' pour les détails.\n\n"
                    f"Cordialement,\n"
                    f"Assistant Gazelle"
                )
            elif change_type == 'reassigned':
                subject = "Rendez-vous assigné"
                plain_content = (
                    f"Bonjour {technician_name},\n\n"
                    f"Un rendez-vous vous a été assigné pour {date_text} :\n"
                    f"{location_text.lstrip(', ')}{time_text}, {client_name}.\n\n"
                    f"Merci de consulter 'Ma Journée' pour les détails.\n\n"
                    f"Cordialement,\n"
                    f"Assistant Gazelle"
                )
            else:  # 'new'
                subject = "Nouveau rendez-vous"
                plain_content = (
                    f"Bonjour {technician_name},\n\n"
                    f"Un nouveau rendez-vous a été ajouté pour {date_text} :\n"
                    f"{location_text.lstrip(', ')}{time_text}, {client_name}.\n\n"
                    f"Merci de consulter 'Ma Journée' pour les détails.\n\n"
                    f"Cordialement,\n"
                    f"Assistant Gazelle"
                )
            
            # Envoyer l'email (texte brut uniquement)
            success = self.email_notifier.send_email(
                to_emails=[email],
                subject=subject,
                html_content=plain_content.replace('\n', '<br>'),  # Simple conversion pour Resend
                plain_content=plain_content
            )
            
            if success:
                print(f"   Email envoyé à {email} pour RV {queue_item.get('appointment_external_id')}")
            else:
                print(f"   Échec envoi email à {email}")
            
            return success
            
        except Exception as e:
            print(f"   Erreur envoi alerte {queue_item.get('id')}: {e}")
            import traceback
            traceback.print_exc()
            return False
    
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
            print(f"   Erreur marquage sent {queue_id}: {e}")
    
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
            print(f"   Erreur marquage failed {queue_id}: {e}")


def main():
    """Point d'entrée pour exécution standalone."""
    notifier = LateAssignmentNotifier()
    result = notifier.process_queue()
    print(f"\nRésultat: {result}")
    return result


if __name__ == '__main__':
    main()
