"""
Scanner automatique PDA/OSM — détecte et importe les demandes depuis Gmail.

Flux :
1. Lit les emails récents de @placedesarts.com, @operademontreal.com, @osm.ca
2. Filtre les emails déjà traités (via processed_emails ou sujet connu)
3. Parse chaque email avec le parser v6 (IA)
4. Importe dans place_des_arts_requests
5. Ajoute un commentaire dans Front pour notifier Louise

Exécution : toutes les heures (8h30-18h30) via le scheduler.
"""

import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger("ptm.pda.auto_scanner")

# Domaines surveillés
WATCHED_DOMAINS = [
    "placedesarts.com",
    "operademontreal.com",
    "osm.ca",
]

# Construire la query Gmail
GMAIL_QUERY = " OR ".join(f"from:@{d}" for d in WATCHED_DOMAINS)


def scan_and_import() -> dict:
    """
    Scan les emails récents et importe les nouvelles demandes PDA.

    Returns:
        {
            "scanned": N emails vérifiés,
            "new_emails": N nouveaux emails détectés,
            "imported": N demandes importées,
            "skipped": N emails déjà traités,
            "errors": [...],
            "imported_details": [...]
        }
    """
    stats = {
        "scanned": 0,
        "new_emails": 0,
        "imported": 0,
        "skipped": 0,
        "errors": [],
        "imported_details": [],
    }

    # 1. Initialiser le lecteur Gmail
    try:
        from core.gmail_reader import GmailReader
        reader = GmailReader()
        if not reader.is_available:
            stats["errors"].append("Gmail non connecté (pas de token)")
            return stats
    except Exception as e:
        stats["errors"].append(f"Erreur init Gmail: {e}")
        return stats

    # 2. Lire les emails récents des domaines surveillés
    try:
        emails = reader.lire_emails(
            max_results=20,
            query=f"({GMAIL_QUERY}) newer_than:3d",
        )
        stats["scanned"] = len(emails)
        logger.info(f"📧 {len(emails)} emails PDA/OSM trouvés")
    except Exception as e:
        stats["errors"].append(f"Erreur lecture emails: {e}")
        return stats

    if not emails:
        return stats

    # 3. Filtrer les emails déjà traités
    processed_ids = _get_processed_email_ids()

    for email in emails:
        email_id = email.get("id", "")
        if email_id in processed_ids:
            stats["skipped"] += 1
            continue

        stats["new_emails"] += 1

        # 4. Parser l'email
        body = email.get("body", "") or email.get("snippet", "")
        subject = email.get("subject", "")
        sender = email.get("from", "")

        if not body or len(body.strip()) < 10:
            continue

        try:
            from modules.pda_v6_email_parser import parse_email
            parsed = parse_email(body)

            if not parsed:
                logger.info(f"📧 Email '{subject}' — aucune demande détectée")
                _mark_email_processed(email_id, subject, sender, 0)
                continue

            # 5. Importer les demandes
            imported_count = 0
            for req in parsed:
                success = _import_request(req, email_id, sender)
                if success:
                    imported_count += 1
                    stats["imported_details"].append({
                        "date": req.get("appointment_date", ""),
                        "room": req.get("room", ""),
                        "for_who": req.get("for_who", ""),
                        "time": req.get("time", ""),
                    })

            stats["imported"] += imported_count

            # 6. Marquer l'email comme traité
            _mark_email_processed(email_id, subject, sender, imported_count)

            # 7. Notifier dans Front
            if imported_count > 0:
                _notify_front(email, parsed)

            logger.info(f"✅ Email '{subject}' → {imported_count} demande(s) importée(s)")

        except Exception as e:
            logger.error(f"❌ Erreur parsing email '{subject}': {e}")
            stats["errors"].append(f"Email '{subject}': {e}")

    return stats


def _get_processed_email_ids() -> set:
    """Récupère les IDs Gmail déjà traités depuis Supabase."""
    try:
        from core.supabase_storage import SupabaseStorage
        import requests as http_requests

        storage = SupabaseStorage(silent=True)
        url = f"{storage.api_url}/processed_emails?select=gmail_message_id"
        resp = http_requests.get(url, headers=storage._get_headers(), timeout=5)
        if resp.status_code == 200:
            return {r.get("gmail_message_id") for r in resp.json() if r.get("gmail_message_id")}
    except Exception:
        pass
    return set()


def _mark_email_processed(gmail_id: str, subject: str, sender: str, count: int):
    """Enregistre un email comme traité dans processed_emails."""
    try:
        from core.supabase_storage import SupabaseStorage
        import requests as http_requests

        storage = SupabaseStorage(silent=True)
        url = f"{storage.api_url}/processed_emails"
        headers = storage._get_headers()
        headers["Prefer"] = "resolution=merge-duplicates"

        http_requests.post(url, headers=headers, json={
            "gmail_message_id": gmail_id,
            "sender_email": sender[:200] if sender else "",
            "subject": subject[:200] if subject else "",
            "status": "imported" if count > 0 else "no_requests",
            "requests_created": count,
            "processed_at": datetime.now().isoformat(),
        })
    except Exception as e:
        logger.warning(f"Erreur marquage email traité: {e}")


def _import_request(req: dict, email_id: str, sender: str) -> bool:
    """Importe une demande parsée dans place_des_arts_requests."""
    try:
        from core.supabase_storage import SupabaseStorage
        import requests as http_requests

        storage = SupabaseStorage(silent=True)

        # Vérifier doublon (même date + même salle + même for_who)
        date_str = str(req.get("appointment_date", ""))[:10]
        room = req.get("room", "")
        for_who = req.get("for_who", "")

        if date_str and (room or for_who):
            check_url = (
                f"{storage.api_url}/place_des_arts_requests?"
                f"appointment_date=eq.{date_str}"
            )
            if room:
                check_url += f"&room=eq.{room}"
            if for_who:
                check_url += f"&for_who=eq.{for_who}"
            check_url += "&limit=1"

            check_resp = http_requests.get(check_url, headers=storage._get_headers(), timeout=5)
            if check_resp.status_code == 200 and check_resp.json():
                logger.info(f"⏭️ Doublon: {date_str} {room} {for_who}")
                return False

        # Insérer
        url = f"{storage.api_url}/place_des_arts_requests"
        headers = storage._get_headers()

        record = {
            "appointment_date": date_str,
            "room": room,
            "room_original": room,
            "for_who": for_who,
            "diapason": req.get("diapason", ""),
            "requester": req.get("requester", ""),
            "piano": req.get("piano", ""),
            "time": req.get("time", ""),
            "status": "PENDING",
            "billing_amount": 175.0,
            "created_by": "auto_scanner",
            "notes": f"Importé automatiquement depuis email ({sender[:50]})",
        }

        resp = http_requests.post(url, headers=headers, json=record)
        return resp.status_code in (200, 201)

    except Exception as e:
        logger.error(f"Erreur import demande: {e}")
        return False


def _notify_front(email: dict, parsed: list):
    """
    Ajoute un commentaire dans Front pour notifier que l'email a été traité.
    Utilise l'API Front via Pipedream (configuré séparément).
    """
    try:
        import os
        import requests as http_requests

        # Construire le résumé des demandes importées
        lines = ["✅ Importé automatiquement dans l'assistant PTM :"]
        for req in parsed:
            date = str(req.get("appointment_date", ""))[:10]
            room = req.get("room", "")
            for_who = req.get("for_who", "")
            time_str = req.get("time", "")
            lines.append(f"  • {date} | {room} | {for_who} | {time_str}")

        comment_text = "\n".join(lines)

        # Appeler l'endpoint Pipedream pour Front (si configuré)
        pipedream_url = os.getenv("PIPEDREAM_FRONT_COMMENT_URL")
        if pipedream_url:
            http_requests.post(pipedream_url, json={
                "email_subject": email.get("subject", ""),
                "email_from": email.get("from", ""),
                "comment": comment_text,
            }, timeout=10)
            logger.info(f"📝 Commentaire Front ajouté")
        else:
            logger.info(f"ℹ️ PIPEDREAM_FRONT_COMMENT_URL non configuré — pas de notification Front")

    except Exception as e:
        logger.warning(f"Erreur notification Front: {e}")
