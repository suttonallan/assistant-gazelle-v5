#!/usr/bin/env python3
r"""
Check appointments for tomorrow - dual purpose:
1. ALERT: APPOINTMENT type not confirmed by client (action required)
2. INFO: PERSONAL appointments (filtered) - just for visibility

MODIFIÉ: Envoi par EMAIL à chaque technicien (plus de Slack)

Created: 2025-11-22
Modified: 2025-12-03
Location: C:\Allan Python projets\check_unconfirmed_appointments.py
Scheduled: Daily at 16:00 via Windows Task Scheduler
"""

import sys
import pyodbc
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
import pytz

# Ajouter le chemin pour imports
sys.path.insert(0, r"c:\Allan Python projets\assistant-gazelle\scripts")

from gmail_sender import GmailSender

# Database Configuration
DB_SERVER = "PIANOTEK\\SQLEXPRESS"
DB_NAME = "PianoTek"
DB_DRIVER = "ODBC Driver 17 for SQL Server"

# Email Configuration - Gmail API
CREDENTIALS_FILE = r"c:\Allan Python projets\assistant-gazelle\data\credentials.json"
TOKEN_FILE = r"c:\Allan Python projets\assistant-gazelle\data\token.json"

# Mapping des techniciens avec leurs emails
TECHNICIANS = {
    'usr_ofYggsCDt2JAVeNP': {
        'name': 'Allan',
        'email': 'asutton@piano-tek.com'
    },
    'usr_HcCiFk7o0vZ9xAI0': {
        'name': 'Nicolas',
        'email': 'nlessard@piano-tek.com'
    },
    'usr_ReUSmIJmBF86ilY1': {
        'name': 'Jean-Philippe',
        'email': 'jpreny@gmail.com'
    }
}

# Log file
LOG_FILE = Path(__file__).parent / "unconfirmed_appointments_log.txt"

def log_message(message):
    """Log message with timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {message}"

    # Print to console (handle encoding issues)
    try:
        print(log_entry)
    except UnicodeEncodeError:
        # Fallback for Windows console encoding issues
        print(log_entry.encode('ascii', 'ignore').decode('ascii'))

    # Write to log file with UTF-8 encoding
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(log_entry + "\n")

def get_appointments_tomorrow():
    """
    Get tomorrow's appointments GROUPED BY TECHNICIAN:
    - APPOINTMENT not confirmed → ALERT (action required)
    - Ne retourne que les RV non confirmés, groupés par technicien

    Returns:
        dict: {tech_id: [list of unconfirmed appointments]}
    """
    try:
        tomorrow = (datetime.now() + timedelta(days=1)).date()
        log_message(f"Checking appointments for {tomorrow}")

        # Connect to database
        conn_str = (
            f"DRIVER={{{DB_DRIVER}}};"
            f"SERVER={DB_SERVER};"
            f"DATABASE={DB_NAME};"
            f"Trusted_Connection=yes;"
        )

        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()

        # Query pour RV NON CONFIRMÉS uniquement, avec TechnicianId
        # Exclut les PERSONAL (rendez-vous personnels) et MEMO
        query = """
            SELECT
                a.Id,
                a.StartAt,
                a.Duration,
                a.Description,
                a.TechnicianId,
                c.CompanyName,
                p.Location,
                p.Make,
                p.Model
            FROM dbo.Appointments a
            LEFT JOIN dbo.Clients c ON a.ClientId = c.Id
            LEFT JOIN dbo.Pianos p ON a.PianoId = p.Id
            WHERE CONVERT(DATE, a.StartAt) = ?
              AND a.AppointmentStatus = 'ACTIVE'
              AND (a.ConfirmedByClient = 0 OR a.ConfirmedByClient IS NULL)
              AND a.TechnicianId IS NOT NULL
              AND a.EventType = 'APPOINTMENT'
              AND (a.Description NOT LIKE '%MEMO%' OR a.Description IS NULL)
            ORDER BY a.TechnicianId, a.StartAt
        """

        cursor.execute(query, tomorrow)
        rows = cursor.fetchall()

        # Grouper par technicien
        appointments_by_tech = {}

        for row in rows:
            tech_id = row[4]

            if not tech_id:
                continue

            # Parse time - row[1] est maintenant un datetime
            # Convertir en timezone de Montréal (America/Toronto = America/Montreal)
            start_datetime = row[1]
            try:
                # Si le datetime est offset-aware, convertir en America/Montreal
                if start_datetime.tzinfo is not None:
                    montreal_tz = pytz.timezone('America/Montreal')
                    start_datetime_local = start_datetime.astimezone(montreal_tz)
                else:
                    # Si offset-naive, on assume que c'est déjà en heure locale
                    start_datetime_local = start_datetime
                hour_minute = start_datetime_local.strftime('%H:%M')
            except:
                hour_minute = "N/A"

            # Info piano
            location = row[6] if row[6] else 'N/A'
            make = row[7] if row[7] else ''
            model = row[8] if row[8] else ''

            piano_info = location
            if make or model:
                piano_info += f" - {make} {model}"

            appointment_data = {
                'id': row[0],
                'time': hour_minute,
                'duration': row[2],
                'description': row[3] or "Aucune description",
                'client': row[5] or "Client inconnu",
                'piano_info': piano_info
            }

            if tech_id not in appointments_by_tech:
                appointments_by_tech[tech_id] = []

            appointments_by_tech[tech_id].append(appointment_data)
            log_message(f"  ALERT: {tech_id} - {appointment_data['client']}")

        log_message(f"Results: {len(appointments_by_tech)} techniciens, {sum(len(v) for v in appointments_by_tech.values())} RV total")

        cursor.close()
        conn.close()

        return appointments_by_tech

    except Exception as e:
        log_message(f"ERROR fetching appointments: {e}")
        import traceback
        log_message(traceback.format_exc())
        return {}

def send_email_notifications(appointments_by_tech):
    """
    Envoie des emails à chaque technicien avec SES RV non confirmés

    Args:
        appointments_by_tech (dict): {tech_id: [appointments]}

    Returns:
        bool: True si tous les envois ont réussi
    """
    if not appointments_by_tech:
        log_message("OK - Aucun RV non confirmé pour demain")
        return True

    try:
        tomorrow = (datetime.now() + timedelta(days=1)).date().strftime("%Y-%m-%d")
        gmail = GmailSender(credentials_file=CREDENTIALS_FILE, token_file=TOKEN_FILE)

        success_count = 0
        total_appointments = 0

        for tech_id, appointments in appointments_by_tech.items():
            if tech_id not in TECHNICIANS:
                log_message(f"WARNING: Technicien {tech_id} non configuré, ignoré")
                continue

            tech_info = TECHNICIANS[tech_id]
            count = len(appointments)
            total_appointments += count

            # Sujet
            subject = f"⚠️ {count} rendez-vous {'nécessitent' if count > 1 else 'nécessite'} peut-être une confirmation pour demain ({tomorrow})"

            # Corps HTML
            body_html = f"""
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; color: #333; }}
                    h2 {{ color: #dc3545; }}
                    table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
                    th {{ padding: 12px; text-align: left; background-color: #f8f9fa; border-bottom: 2px solid #dee2e6; }}
                    td {{ padding: 12px; border-bottom: 1px solid #dee2e6; }}
                    .client-name {{ font-weight: bold; }}
                    .footer {{ margin-top: 30px; color: #666; font-size: 0.9em; }}
                </style>
            </head>
            <body>
                <h2>⚠️ Rendez-vous pour demain ({tomorrow})</h2>
                <p>Bonjour {tech_info['name']},</p>
                <p>Vous avez <strong>{count}</strong> rendez-vous qui {'nécessitent' if count > 1 else 'nécessite'} peut-être une confirmation pour demain:</p>
                <table>
                    <thead>
                        <tr>
                            <th>Heure</th>
                            <th>Client</th>
                            <th>Description</th>
                            <th>Piano</th>
                            <th>Durée</th>
                        </tr>
                    </thead>
                    <tbody>
            """

            for apt in appointments:
                body_html += f"""
                        <tr>
                            <td>{apt['time']}</td>
                            <td class="client-name">{apt['client']}</td>
                            <td>{apt['description']}</td>
                            <td>{apt['piano_info']}</td>
                            <td>{apt['duration']} min</td>
                        </tr>
                """

            body_html += """
                    </tbody>
                </table>
                <p style="margin-top: 20px;"><strong>ACTION REQUISE:</strong> Contacter ces clients pour confirmation</p>
                <p class="footer">
                    Cordialement,<br>
                    <strong>Piano Technique Montréal</strong><br>
                    <em>(Email automatique envoyé à 16h)</em>
                </p>
            </body>
            </html>
            """

            # Corps texte
            body_text = f"Bonjour {tech_info['name']},\n\n"
            body_text += f"Vous avez {count} rendez-vous qui {'nécessitent' if count > 1 else 'nécessite'} peut-être une confirmation pour demain ({tomorrow}):\n\n"
            for apt in appointments:
                body_text += f"• {apt['time']} - {apt['client']}\n"
                body_text += f"  Description: {apt['description']}\n"
                body_text += f"  Piano: {apt['piano_info']}\n"
                body_text += f"  Durée: {apt['duration']} min\n\n"
            body_text += "ACTION REQUISE: Contacter ces clients pour confirmation\n\n"
            body_text += "Cordialement,\nPiano Technique Montréal\n(Email automatique envoyé à 16h)"

            # Envoyer
            result = gmail.send_email(
                to=tech_info['email'],
                subject=subject,
                body_text=body_text,
                body_html=body_html
            )

            if result['success']:
                log_message(f"OK Email envoyé à {tech_info['name']} ({tech_info['email']}): {count} RV")
                success_count += 1
            else:
                log_message(f"ERROR Échec envoi à {tech_info['name']}: {result.get('error', 'Unknown')}")

        log_message(f"Results: {success_count}/{len(appointments_by_tech)} emails envoyés ({total_appointments} RV total)")
        return success_count > 0

    except Exception as e:
        log_message(f"ERROR sending email notifications: {e}")
        import traceback
        log_message(traceback.format_exc())
        return False

def main():
    """Main function"""
    log_message("="*60)
    log_message("Starting appointments check for tomorrow")
    log_message("="*60)

    try:
        # Get appointments grouped by technician
        appointments_by_tech = get_appointments_tomorrow()

        # Send email notifications
        success = send_email_notifications(appointments_by_tech)

        if success:
            log_message("OK Check completed successfully")
        else:
            log_message("WARNING Check completed but notification failed")

        log_message("="*60)

        return 0 if success else 1

    except Exception as e:
        log_message(f"CRITICAL ERROR: {e}")
        import traceback
        log_message(traceback.format_exc())
        log_message("="*60)
        return 1

if __name__ == "__main__":
    exit(main())
