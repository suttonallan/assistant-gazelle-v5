"""
Détection d'oublis PDA — Vérifie quotidiennement que tous les emails
PDA reçus ont bien généré des demandes dans l'assistant.

Logique:
1. Scanne Gmail pour les emails PDA récents (7 derniers jours)
2. Compare avec la table processed_emails
3. Si un email reçu il y a 2+ jours n'a jamais été traité → alerte
4. Envoie un récapitulatif par email à info@piano-tek.com

Exécution: Tous les jours à 09:00 (heure Montréal)
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

INFO_EMAIL = os.getenv('LOUISE_EMAIL', 'info@piano-tek.com')

# Seuil: un email non traité après 2 jours = oubli
SEUIL_OUBLI_JOURS = 2


def detecter_oublis_pda() -> Dict[str, Any]:
    """
    Détecte les emails PDA non traités depuis plus de 2 jours.

    Returns:
        Dict avec: oublis_count, oublis (liste), alerte_envoyee, errors
    """
    from core.gmail_scanner import get_gmail_scanner
    from core.supabase_storage import SupabaseStorage

    result = {
        'check_time': datetime.now(timezone.utc).isoformat(),
        'emails_gmail': 0,
        'emails_traites': 0,
        'oublis_count': 0,
        'oublis': [],
        'alerte_envoyee': False,
        'errors': [],
    }

    try:
        # 1. Initialiser le scanner Gmail
        scanner = get_gmail_scanner()
        if not scanner.initialize():
            result['errors'].append("Gmail scanner non initialisé")
            logger.error("Gmail scanner non initialisé pour détection oublis")
            return result

        # 2. Récupérer les IDs déjà traités depuis Supabase
        storage = SupabaseStorage(silent=True)
        processed_ids = _get_processed_email_ids(storage)

        # 3. Scanner Gmail — tous les emails PDA des 7 derniers jours
        #    SANS filtrer par processed_ids (on veut tout voir)
        all_emails = scanner.scan_new_emails(max_results=50, processed_ids=None)
        result['emails_gmail'] = len(all_emails)

        if not all_emails:
            logger.info("Détection oublis: aucun email PDA dans Gmail")
            return result

        # 4. Identifier les emails non traités depuis 2+ jours
        maintenant = datetime.now(timezone.utc)
        seuil = maintenant - timedelta(days=SEUIL_OUBLI_JOURS)

        oublis = []
        traites = 0

        for email in all_emails:
            gmail_id = email.get('gmail_message_id', '')

            if gmail_id in processed_ids:
                traites += 1
                continue

            # Email non traité — vérifier s'il est assez vieux
            received_at = email.get('received_at')
            if not received_at:
                continue

            if received_at <= seuil:
                oublis.append({
                    'gmail_message_id': gmail_id,
                    'sender_email': email.get('sender_email', ''),
                    'sender_name': email.get('sender_name', ''),
                    'subject': email.get('subject', ''),
                    'received_at': received_at.isoformat() if isinstance(received_at, datetime) else str(received_at),
                    'age_jours': (maintenant - received_at).days,
                })

        result['emails_traites'] = traites
        result['oublis_count'] = len(oublis)
        result['oublis'] = oublis

        # 5. Envoyer alerte si des oublis détectés
        if oublis:
            logger.warning(f"Détection oublis PDA: {len(oublis)} email(s) non traité(s)")
            result['alerte_envoyee'] = _envoyer_alerte_oublis(oublis)
        else:
            logger.info(
                f"Détection oublis PDA: tout est OK "
                f"({result['emails_gmail']} emails Gmail, {traites} traités)"
            )

    except Exception as e:
        result['errors'].append(f"Erreur détection oublis: {e}")
        logger.error(f"Erreur détection oublis PDA: {e}", exc_info=True)

    return result


def _get_processed_email_ids(storage) -> set:
    """Récupère les IDs Gmail déjà traités depuis processed_emails."""
    try:
        import requests as req
        resp = req.get(
            f"{storage.api_url}/processed_emails",
            headers=storage._get_headers(),
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


def _envoyer_alerte_oublis(oublis: List[Dict]) -> bool:
    """Envoie un email d'alerte listant les emails PDA oubliés."""
    try:
        from core.email_notifier import EmailNotifier
        notifier = EmailNotifier()

        if not notifier.client:
            logger.warning("Email notifier non configuré — alerte oublis non envoyée")
            return False

        # Construire le tableau HTML
        rows_html = ""
        for oubli in oublis:
            rows_html += f"""
            <tr>
                <td style="padding: 8px; border: 1px solid #ddd;">{oubli['received_at'][:10]}</td>
                <td style="padding: 8px; border: 1px solid #ddd;">{oubli['age_jours']}j</td>
                <td style="padding: 8px; border: 1px solid #ddd;">{oubli['sender_name'] or oubli['sender_email']}</td>
                <td style="padding: 8px; border: 1px solid #ddd;">{oubli['subject']}</td>
            </tr>
            """

        html_content = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .header {{ background: #dc2626; color: white; padding: 15px 20px; border-radius: 8px 8px 0 0; }}
                .content {{ background: #fef2f2; padding: 20px; border: 1px solid #fecaca; }}
                table {{ border-collapse: collapse; width: 100%; margin: 15px 0; }}
                th {{ background: #991b1b; color: white; padding: 10px 8px; text-align: left; font-size: 13px; }}
                td {{ font-size: 13px; }}
                .footer {{ padding: 15px 20px; font-size: 12px; color: #64748b; border-top: 1px solid #e2e8f0; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h2 style="margin:0;">Demandes PDA potentiellement oubliées</h2>
            </div>
            <div class="content">
                <p><strong>{len(oublis)} email(s)</strong> de Place des Arts / Opéra de Montréal
                n'ont pas été traités et ont plus de {SEUIL_OUBLI_JOURS} jours:</p>

                <table>
                    <thead>
                        <tr>
                            <th>Reçu le</th>
                            <th>Âge</th>
                            <th>Expéditeur</th>
                            <th>Objet</th>
                        </tr>
                    </thead>
                    <tbody>
                        {rows_html}
                    </tbody>
                </table>

                <p style="color: #dc2626;">
                    Vérifiez ces emails dans la boîte info@piano-tek.com et
                    créez les demandes manuellement si nécessaire.
                </p>
            </div>
            <div class="footer">
                <p>Vérification automatique quotidienne — Assistant Gazelle V5</p>
            </div>
        </body>
        </html>
        """

        subject = f"[PDA OUBLI] {len(oublis)} email(s) non traité(s) depuis {SEUIL_OUBLI_JOURS}+ jours"

        success = notifier.send_email(
            to_emails=[INFO_EMAIL],
            subject=subject,
            html_content=html_content,
        )

        if success:
            logger.info(f"Alerte oublis PDA envoyée à {INFO_EMAIL}")
        else:
            logger.warning("Échec envoi alerte oublis PDA")

        return success

    except Exception as e:
        logger.error(f"Erreur envoi alerte oublis: {e}", exc_info=True)
        return False
