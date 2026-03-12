"""
Pipeline automatisé: Email PDA → Parsing → Création demandes → Confirmation.

Orchestre le flux complet:
1. Récupère les emails non traités via Gmail scanner
2. Parse chaque email avec email_parser
3. Crée les demandes dans Supabase (place_des_arts_requests)
4. Envoie un email récapitulatif de confirmation à info@
5. Enregistre l'email comme traité (processed_emails)
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

# Email de confirmation (destinataire)
INFO_EMAIL = os.getenv('LOUISE_EMAIL', 'info@piano-tek.com')


class PDAEmailProcessor:
    """Processeur automatique des emails PDA."""

    def __init__(self):
        self._storage = None
        self._manager = None

    @property
    def storage(self):
        if self._storage is None:
            from core.supabase_storage import SupabaseStorage
            self._storage = SupabaseStorage(silent=True)
        return self._storage

    @property
    def manager(self):
        if self._manager is None:
            from modules.place_des_arts.services.event_manager import EventManager
            self._manager = EventManager(self.storage)
        return self._manager

    def run_scan(self) -> Dict[str, Any]:
        """
        Exécute un scan complet: Gmail → parsing → création → confirmation.

        Returns:
            Résumé du scan avec stats et erreurs
        """
        from core.gmail_scanner import get_gmail_scanner

        result = {
            'scan_time': datetime.now(timezone.utc).isoformat(),
            'emails_found': 0,
            'emails_processed': 0,
            'requests_created': 0,
            'confirmations_sent': 0,
            'errors': [],
        }

        try:
            scanner = get_gmail_scanner()
            if not scanner.initialize():
                result['errors'].append("Gmail scanner non initialisé (credentials manquantes?)")
                logger.error("Gmail scanner non initialisé")
                return result

            # Récupérer les IDs déjà traités
            processed_ids = self._get_processed_email_ids()

            # Scanner les nouveaux emails
            emails = scanner.scan_new_emails(
                max_results=30,
                processed_ids=processed_ids
            )
            result['emails_found'] = len(emails)

            if not emails:
                logger.info("Aucun nouvel email PDA à traiter")
                return result

            # Traiter chaque email
            for email_data in emails:
                try:
                    email_result = self._process_single_email(email_data)
                    result['emails_processed'] += 1
                    result['requests_created'] += email_result.get('requests_created', 0)
                    if email_result.get('confirmation_sent'):
                        result['confirmations_sent'] += 1
                except Exception as e:
                    error_msg = f"Erreur traitement email {email_data.get('gmail_message_id', '?')}: {e}"
                    result['errors'].append(error_msg)
                    logger.error(error_msg, exc_info=True)

                    # Enregistrer l'échec
                    self._record_processed_email(
                        email_data,
                        status='failed',
                        error_message=str(e)
                    )

            logger.info(
                f"Scan terminé: {result['emails_found']} trouvés, "
                f"{result['emails_processed']} traités, "
                f"{result['requests_created']} demandes créées"
            )

        except Exception as e:
            result['errors'].append(f"Erreur globale scan: {e}")
            logger.error(f"Erreur globale scan PDA: {e}", exc_info=True)

        return result

    def _process_single_email(self, email_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Traite un seul email: parsing → création → confirmation.

        Returns:
            Dict avec requests_created, confirmation_sent, request_ids
        """
        gmail_id = email_data['gmail_message_id']
        body_text = email_data.get('body_text', '')
        sender = email_data.get('sender_email', '')
        subject = email_data.get('subject', '')

        logger.info(f"Traitement email: {subject} (de {sender})")

        if not body_text.strip():
            logger.warning(f"Email vide: {gmail_id}")
            self._record_processed_email(email_data, status='skipped', error_message='Corps vide')
            return {'requests_created': 0, 'confirmation_sent': False}

        # 1. Parser l'email
        from modules.place_des_arts.services.email_parser import parse_email_text
        parsed_requests = parse_email_text(body_text)

        if not parsed_requests:
            logger.info(f"Aucune demande détectée dans l'email: {subject}")
            self._record_processed_email(email_data, status='no_requests')
            return {'requests_created': 0, 'confirmation_sent': False}

        logger.info(f"Détecté {len(parsed_requests)} demande(s) dans l'email")

        # 2. Créer les demandes dans Supabase
        created_ids = []
        for i, req in enumerate(parsed_requests):
            try:
                req_id = self._create_request(req, email_data, index=i)
                if req_id:
                    created_ids.append(req_id)
            except Exception as e:
                logger.error(f"Erreur création demande {i+1}: {e}")

        # 3. Envoyer l'email de confirmation (groupé)
        confirmation_sent = False
        if created_ids:
            confirmation_sent = self._send_confirmation_email(
                email_data, parsed_requests, created_ids
            )

        # 4. Enregistrer comme traité
        self._record_processed_email(
            email_data,
            status='processed',
            requests_created=len(created_ids),
            request_ids=created_ids,
            confirmation_sent=confirmation_sent
        )

        return {
            'requests_created': len(created_ids),
            'confirmation_sent': confirmation_sent,
            'request_ids': created_ids,
        }

    def _create_request(
        self, parsed: Dict, email_data: Dict, index: int
    ) -> Optional[str]:
        """
        Crée une demande PDA dans Supabase à partir des données parsées.

        Returns:
            L'ID de la demande créée, ou None si échec
        """
        now_ts = int(datetime.now(timezone.utc).timestamp())
        req_id = f"pda_auto_{now_ts}_{index}"

        # Formatter la date du RDV
        appointment_date = None
        if parsed.get('date'):
            if isinstance(parsed['date'], datetime):
                appointment_date = parsed['date'].strftime('%Y-%m-%d')
            else:
                appointment_date = str(parsed['date'])

        # Date de la demande
        request_date = parsed.get('request_date')
        if not request_date:
            received = email_data.get('received_at')
            if received:
                request_date = received.strftime('%Y-%m-%d')
            else:
                request_date = datetime.now(timezone.utc).strftime('%Y-%m-%d')

        row = {
            "id": req_id,
            "request_date": request_date,
            "appointment_date": appointment_date,
            "room": parsed.get('room') or '',
            "room_original": parsed.get('room') or '',
            "for_who": parsed.get('for_who') or '',
            "diapason": parsed.get('diapason') or '',
            "requester": parsed.get('requester') or '',
            "piano": parsed.get('piano') or '',
            "time": parsed.get('time') or '',
            "technician_id": None,
            "status": "PENDING",
            "notes": f"Import auto depuis email: {email_data.get('subject', '')}",
            "billing_amount": 175.0,
            "parking": '',
            "created_by": "gmail_scanner",
        }

        # Auto-détection stationnement
        try:
            from modules.place_des_arts.services.gazelle_sync import extract_parking_amount
            for text_field in (row.get("for_who", ""), row.get("notes", "")):
                parking_val = extract_parking_amount(text_field)
                if parking_val:
                    row["parking"] = parking_val
                    break
        except Exception:
            pass

        result = self.manager.import_csv([row], on_conflict="update")

        if result.get("errors"):
            logger.error(f"Erreur import demande {req_id}: {result['errors']}")
            return None

        logger.info(
            f"Demande créée: {req_id} | "
            f"{appointment_date} | {row['room']} | {row['for_who']}"
        )
        return req_id

    def _send_confirmation_email(
        self,
        email_data: Dict,
        parsed_requests: List[Dict],
        created_ids: List[str]
    ) -> bool:
        """
        Envoie un email récapitulatif de confirmation à info@.

        Format: Un seul email groupé avec toutes les demandes de l'email source.
        """
        try:
            from core.email_notifier import EmailNotifier
            notifier = EmailNotifier()

            sender = email_data.get('sender_name') or email_data.get('sender_email', '')
            subject = email_data.get('subject', 'Demande PDA')

            # Construire le tableau récapitulatif
            rows_html = ""
            for i, req in enumerate(parsed_requests):
                date_str = ''
                if req.get('date'):
                    if isinstance(req['date'], datetime):
                        date_str = req['date'].strftime('%d/%m/%Y')
                    else:
                        date_str = str(req['date'])

                status_badge = '🟢' if i < len(created_ids) else '🔴'
                rows_html += f"""
                <tr>
                    <td style="padding: 8px; border: 1px solid #ddd;">{status_badge}</td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{date_str}</td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{req.get('room', '')}</td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{req.get('for_who', '')}</td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{req.get('piano', '')}</td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{req.get('diapason', '')}</td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{req.get('time', '')}</td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{req.get('requester', '')}</td>
                </tr>
                """

            html_content = f"""
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                    .header {{ background: #2563eb; color: white; padding: 15px 20px; border-radius: 8px 8px 0 0; }}
                    .content {{ background: #f8fafc; padding: 20px; border: 1px solid #e2e8f0; }}
                    table {{ border-collapse: collapse; width: 100%; margin: 15px 0; }}
                    th {{ background: #1e40af; color: white; padding: 10px 8px; text-align: left; font-size: 13px; }}
                    td {{ font-size: 13px; }}
                    .footer {{ padding: 15px 20px; font-size: 12px; color: #64748b; border-top: 1px solid #e2e8f0; }}
                </style>
            </head>
            <body>
                <div class="header">
                    <h2 style="margin:0;">Nouvelles demandes PDA enregistrées</h2>
                </div>
                <div class="content">
                    <p><strong>Email source:</strong> {subject}</p>
                    <p><strong>De:</strong> {sender}</p>
                    <p><strong>{len(created_ids)} demande(s)</strong> ont été automatiquement créées dans l'assistant:</p>

                    <table>
                        <thead>
                            <tr>
                                <th></th>
                                <th>Date RDV</th>
                                <th>Salle</th>
                                <th>Pour qui</th>
                                <th>Piano</th>
                                <th>Diap.</th>
                                <th>Heure</th>
                                <th>Dem.</th>
                            </tr>
                        </thead>
                        <tbody>
                            {rows_html}
                        </tbody>
                    </table>

                    <p style="color: #2563eb;">
                        Ces demandes ont le statut <strong>PENDING</strong> et doivent être
                        synchronisées avec Gazelle.
                    </p>
                </div>
                <div class="footer">
                    <p>Email généré automatiquement par Assistant Gazelle - Scanner PDA</p>
                </div>
            </body>
            </html>
            """

            email_subject = f"[PDA Auto] {len(created_ids)} demande(s) importée(s) - {sender}"

            success = notifier.send_email(
                to_emails=[INFO_EMAIL],
                subject=email_subject,
                html_content=html_content,
            )

            if success:
                logger.info(f"Email de confirmation envoyé à {INFO_EMAIL}")
            else:
                logger.warning("Échec envoi email de confirmation")

            return success

        except Exception as e:
            logger.error(f"Erreur envoi confirmation: {e}", exc_info=True)
            return False

    def _get_processed_email_ids(self) -> set:
        """Récupère les IDs Gmail déjà traités depuis Supabase."""
        try:
            import requests as req
            resp = req.get(
                f"{self.storage.api_url}/processed_emails",
                headers=self.storage._get_headers(),
                params={
                    "select": "gmail_message_id",
                    "order": "processed_at.desc",
                    "limit": 500,
                }
            )
            if resp.status_code == 200:
                data = resp.json()
                return {row['gmail_message_id'] for row in data}
        except Exception as e:
            logger.warning(f"Erreur lecture processed_emails: {e}")
        return set()

    def _record_processed_email(
        self,
        email_data: Dict,
        status: str = 'processed',
        requests_created: int = 0,
        request_ids: Optional[List[str]] = None,
        confirmation_sent: bool = False,
        error_message: Optional[str] = None,
    ):
        """Enregistre un email traité dans processed_emails."""
        try:
            import requests as req

            body_text = email_data.get('body_text', '')
            preview = body_text[:500] if body_text else ''

            received_at = email_data.get('received_at')
            if isinstance(received_at, datetime):
                received_at = received_at.isoformat()

            row = {
                "gmail_message_id": email_data['gmail_message_id'],
                "gmail_thread_id": email_data.get('gmail_thread_id', ''),
                "sender_email": email_data.get('sender_email', ''),
                "sender_name": email_data.get('sender_name', ''),
                "subject": email_data.get('subject', ''),
                "received_at": received_at,
                "requests_created": requests_created,
                "requests_ids": request_ids or [],
                "status": status,
                "error_message": error_message,
                "confirmation_sent": confirmation_sent,
                "raw_body_preview": preview,
            }

            resp = req.post(
                f"{self.storage.api_url}/processed_emails",
                headers={
                    **self.storage._get_headers(),
                    "Prefer": "resolution=merge-duplicates"
                },
                json=row
            )

            if resp.status_code not in (200, 201):
                logger.warning(f"Erreur enregistrement processed_email: {resp.status_code} {resp.text}")

        except Exception as e:
            logger.error(f"Erreur enregistrement processed_email: {e}")

    def get_scan_history(self, limit: int = 20) -> List[Dict]:
        """Retourne l'historique des scans récents."""
        try:
            import requests as req
            resp = req.get(
                f"{self.storage.api_url}/processed_emails",
                headers=self.storage._get_headers(),
                params={
                    "select": "*",
                    "order": "processed_at.desc",
                    "limit": limit,
                }
            )
            if resp.status_code == 200:
                return resp.json()
        except Exception as e:
            logger.error(f"Erreur lecture historique scans: {e}")
        return []


# Singleton
_processor_instance: Optional[PDAEmailProcessor] = None


def get_email_processor() -> PDAEmailProcessor:
    """Retourne l'instance singleton du processeur."""
    global _processor_instance
    if _processor_instance is None:
        _processor_instance = PDAEmailProcessor()
    return _processor_instance
