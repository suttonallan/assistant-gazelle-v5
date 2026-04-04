"""
Scanner automatique PDA/OSM — surveille les demandes et alerte si non traitées.

Flux :
1. Lit les emails récents de @placedesarts.com, @operademontreal.com, @osm.ca
2. Filtre les réponses courtes ("ok merci", "reçu", etc.) — ne garde que les vraies demandes
3. Parse chaque demande avec le parser v6 (IA) pour extraire date/salle
4. Enregistre dans pda_email_watchlist (PAS dans place_des_arts_requests — Nicolas gère)
5. Après 24h, vérifie si un RV existe dans Gazelle → sinon alerte

Nicolas garde le contrôle total. Le système ne fait que surveiller et alerter.
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

# Pas de liste de patterns — on détecte les réponses par leur structure :
# un email court sans date ni salle ni piano = confirmation, pas une demande


def scan_and_watch() -> dict:
    """
    Scan les emails récents PDA/OSM et les met en surveillance.
    NE les importe PAS — Nicolas gère manuellement.
    Après 24h sans RV dans Gazelle → alerte.

    Returns:
        {
            "scanned": N emails vérifiés,
            "new_demands": N nouvelles demandes détectées,
            "replies_ignored": N réponses courtes ignorées,
            "skipped": N emails déjà traités,
            "alerts_sent": N alertes pour demandes non traitées,
            "errors": [...]
        }
    """
    stats = {
        "scanned": 0,
        "new_demands": 0,
        "replies_ignored": 0,
        "skipped": 0,
        "alerts_sent": 0,
        "errors": [],
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
    except Exception as e:
        stats["errors"].append(f"Erreur lecture emails: {e}")
        return stats

    if not emails:
        return stats

    # 3. Traiter chaque email
    processed_ids = _get_processed_email_ids()

    for email in emails:
        email_id = email.get("id", "")
        if email_id in processed_ids:
            stats["skipped"] += 1
            continue

        body = email.get("body", "") or email.get("snippet", "")
        subject = email.get("subject", "")
        sender = email.get("from", "")

        if not body or len(body.strip()) < 10:
            _mark_email_processed(email_id, subject, sender, 0, "empty")
            continue

        # Ignorer les réponses courtes (ok merci, reçu, etc.)
        if _is_short_reply(body):
            stats["replies_ignored"] += 1
            _mark_email_processed(email_id, subject, sender, 0, "reply")
            continue

        # Parser pour détecter les demandes
        try:
            from modules.pda_v6_email_parser import parse_email
            parsed = parse_email(body)

            if not parsed:
                _mark_email_processed(email_id, subject, sender, 0, "no_demands")
                continue

            # Enregistrer dans la watchlist (pas d'import)
            for req in parsed:
                _add_to_watchlist(req, email_id, sender, subject)
                stats["new_demands"] += 1

            _mark_email_processed(email_id, subject, sender, len(parsed), "watched")
            logger.info(f"👁️ Email '{subject}' → {len(parsed)} demande(s) en surveillance")

        except Exception as e:
            logger.error(f"❌ Erreur parsing '{subject}': {e}")
            stats["errors"].append(f"'{subject}': {e}")

    # 4. Vérifier les demandes en surveillance > 24h sans RV
    alerts = _check_overdue_watchlist()
    stats["alerts_sent"] = alerts

    return stats


def check_overdue_demands() -> dict:
    """Vérifie les demandes PDA en surveillance depuis > 24h sans RV Gazelle."""
    alerts = _check_overdue_watchlist()
    return {"alerts_sent": alerts}


def _is_short_reply(body: str) -> bool:
    """
    Détecte les réponses/confirmations qui ne sont pas des demandes.

    Logique : un email court sans indicateurs de demande (date, salle, piano, heure)
    est une confirmation. Peu importe les mots exacts — "parfait!", "super merci",
    "noté 👍", "Excellent, on s'en occupe" sont tous des confirmations.
    """
    import re

    # Nettoyer (enlever signatures, lignes vides, quoted text)
    lines = body.strip().split("\n")
    clean_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith(">") or stripped.startswith("--"):
            break  # Arrêter au quoted text ou signature
        if stripped:
            clean_lines.append(stripped)

    clean = " ".join(clean_lines).lower()

    # Email très court (< 100 chars sans quoted text) = probablement une confirmation
    if len(clean) < 100:
        # Vérifier qu'il ne contient PAS d'indicateurs de demande
        has_date = bool(re.search(r'\d{1,2}[-/\s](?:jan|fév|feb|mar|avr|apr|mai|may|jun|jui|jul|aoû|aug|sep|oct|nov|déc|dec)', clean))
        has_room = any(code in clean for code in ['wp', 'ms', 'tm', '5e', 'scl', 'tjd', 'maison symphonique', 'wilfrid'])
        has_piano = 'piano' in clean or 'steinway' in clean or 'yamaha' in clean or 'baldwin' in clean
        has_time = bool(re.search(r'avant\s+\d', clean))

        if not has_date and not has_room and not has_piano and not has_time:
            return True

    return False


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


def _mark_email_processed(gmail_id: str, subject: str, sender: str, count: int, status: str = "processed"):
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
            "status": status,
            "requests_created": count,
            "processed_at": datetime.now().isoformat(),
        })
    except Exception as e:
        logger.warning(f"Erreur marquage email traité: {e}")


def _add_to_watchlist(req: dict, email_id: str, sender: str, subject: str):
    """Ajoute une demande détectée dans la watchlist de surveillance."""
    try:
        from core.supabase_storage import SupabaseStorage
        import requests as http_requests

        storage = SupabaseStorage(silent=True)
        date_str = str(req.get("appointment_date", ""))[:10]
        room = req.get("room", "")
        for_who = req.get("for_who", "")

        # Vérifier doublon dans la watchlist
        check_url = (
            f"{storage.api_url}/system_settings?"
            f"key=eq.pda_watchlist_{date_str}_{room}_{for_who}"
            f"&limit=1"
        )
        check_resp = http_requests.get(check_url, headers=storage._get_headers(), timeout=5)
        if check_resp.status_code == 200 and check_resp.json():
            return  # Déjà en surveillance

        # Ajouter à la watchlist via system_settings
        url = f"{storage.api_url}/system_settings"
        headers = storage._get_headers()
        headers["Prefer"] = "resolution=merge-duplicates"

        import json
        http_requests.post(url, headers=headers, json={
            "key": f"pda_watchlist_{date_str}_{room}_{for_who}",
            "value": json.dumps({
                "appointment_date": date_str,
                "room": room,
                "for_who": for_who,
                "time": req.get("time", ""),
                "piano": req.get("piano", ""),
                "sender": sender[:100],
                "subject": subject[:100],
                "detected_at": datetime.now().isoformat(),
                "gmail_id": email_id,
                "alerted": False,
            }),
        })
        logger.info(f"👁️ Watchlist: {date_str} {room} {for_who}")
    except Exception as e:
        logger.warning(f"Erreur ajout watchlist: {e}")


def _check_overdue_watchlist() -> int:
    """
    Vérifie les demandes en surveillance depuis > 24h sans RV Gazelle.
    Envoie une alerte pour chaque demande non traitée.
    """
    try:
        from core.supabase_storage import SupabaseStorage
        import requests as http_requests
        import json

        storage = SupabaseStorage(silent=True)
        headers = storage._get_headers()

        # Récupérer toutes les entrées watchlist
        url = f"{storage.api_url}/system_settings?key=like.pda_watchlist_*"
        resp = http_requests.get(url, headers=headers, timeout=8)
        if resp.status_code != 200:
            return 0

        alerts_sent = 0
        now = datetime.now()

        for row in resp.json():
            try:
                data = json.loads(row.get("value", "{}"))
            except (json.JSONDecodeError, TypeError):
                continue

            if data.get("alerted"):
                continue

            detected_at = data.get("detected_at", "")
            if not detected_at:
                continue

            detected = datetime.fromisoformat(detected_at)
            hours_since = (now - detected).total_seconds() / 3600

            if hours_since < 24:
                continue

            # Vérifier si un RV existe dans Gazelle pour cette date
            date_str = data.get("appointment_date", "")
            room = data.get("room", "")
            for_who = data.get("for_who", "")

            has_rv = _check_gazelle_rv_exists(storage, headers, date_str, room, for_who)

            if has_rv:
                # RV créé → marquer comme traité et supprimer de la watchlist
                data["alerted"] = True
                data["resolved"] = True
                http_requests.patch(
                    f"{storage.api_url}/system_settings?key=eq.{row['key']}",
                    headers={**headers, "Prefer": "return=representation"},
                    json={"value": json.dumps(data)},
                )
                continue

            # Pas de RV après 24h → ALERTE
            _send_overdue_alert(data)
            alerts_sent += 1

            # Marquer comme alerté
            data["alerted"] = True
            http_requests.patch(
                f"{storage.api_url}/system_settings?key=eq.{row['key']}",
                headers={**headers, "Prefer": "return=representation"},
                json={"value": json.dumps(data)},
            )

        return alerts_sent

    except Exception as e:
        logger.error(f"Erreur vérification watchlist: {e}")
        return 0


def _check_gazelle_rv_exists(storage, headers, date_str: str, room: str, for_who: str) -> bool:
    """Vérifie si un RV Gazelle existe pour cette date (client PDA ou titre PDA)."""
    try:
        import requests as http_requests
        PDA_CLIENT_ID = "cli_HbEwl9rN11pSuDEU"

        url = (
            f"{storage.api_url}/gazelle_appointments?"
            f"appointment_date=eq.{date_str}"
            f"&client_external_id=eq.{PDA_CLIENT_ID}"
            f"&limit=1"
        )
        resp = http_requests.get(url, headers=headers, timeout=5)
        if resp.status_code == 200 and resp.json():
            return True

        # Chercher aussi par titre "Place des Arts"
        url2 = (
            f"{storage.api_url}/gazelle_appointments?"
            f"appointment_date=eq.{date_str}"
            f"&title=ilike.*Place des Arts*"
            f"&limit=1"
        )
        resp2 = http_requests.get(url2, headers=headers, timeout=5)
        if resp2.status_code == 200 and resp2.json():
            return True

        return False
    except Exception:
        return False


def _send_overdue_alert(data: dict):
    """Envoie une alerte pour une demande PDA non traitée après 24h."""
    date_str = data.get("appointment_date", "")
    room = data.get("room", "")
    for_who = data.get("for_who", "")
    time_str = data.get("time", "")
    sender = data.get("sender", "")

    message = (
        f"⚠️ DEMANDE PDA NON TRAITÉE (>24h)\n"
        f"Date: {date_str}\n"
        f"Salle: {room}\n"
        f"Événement: {for_who}\n"
        f"Heure: {time_str}\n"
        f"Envoyée par: {sender}\n\n"
        f"Aucun RV trouvé dans Gazelle pour cette date."
    )

    logger.warning(message)

    # Envoyer par email à Allan
    try:
        from core.email_notifier import EmailNotifier
        notifier = EmailNotifier()
        notifier.send_email(
            to_emails=["asutton@piano-tek.com"],
            subject=f"⚠️ Demande PDA non traitée: {for_who} {date_str}",
            html_content=message.replace("\n", "<br>"),
            plain_content=message,
        )
    except Exception as e:
        logger.warning(f"Erreur envoi alerte email: {e}")
