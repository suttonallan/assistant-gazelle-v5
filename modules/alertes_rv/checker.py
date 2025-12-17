#!/usr/bin/env python3
"""
Module de vérification des RV non confirmés.

Adapté pour architecture cloud (Supabase + Render).
Basé sur check_unconfirmed_appointments.py mais sans dépendances Windows.
"""

from datetime import datetime, timedelta, date
from typing import List, Dict, Any, Optional
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.supabase_storage import SupabaseStorage


class AppointmentChecker:
    """Vérificateur de rendez-vous non confirmés."""

    # Mapping des techniciens (IDs Gazelle → emails)
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

    def __init__(self, storage: Optional[SupabaseStorage] = None):
        """
        Initialise le vérificateur.

        Args:
            storage: Instance SupabaseStorage (créée si None)
        """
        self.storage = storage or SupabaseStorage()

    def get_unconfirmed_appointments(
        self,
        target_date: Optional[date] = None,
        exclude_types: List[str] = None
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Récupère les RV non confirmés pour une date, groupés par technicien.

        Args:
            target_date: Date à vérifier (demain par défaut)
            exclude_types: Types de RV à exclure (PERSONAL, MEMO par défaut)

        Returns:
            dict: {technician_id: [list of unconfirmed appointments]}
        """
        if target_date is None:
            target_date = (datetime.now() + timedelta(days=1)).date()

        if exclude_types is None:
            exclude_types = ['PERSONAL', 'MEMO']

        try:
            # Query Supabase pour les RV de la date cible
            # Table: gazelle_appointments
            # Colonnes: id, external_id, appointment_date, appointment_time,
            #           title, description, status, confirmed,
            #           technician_external_id, client_external_id

            date_str = target_date.isoformat()

            # Construire la query Supabase
            query = (
                f"{self.storage.api_url}/gazelle_appointments?"
                f"appointment_date=eq.{date_str}&"
                f"confirmed=eq.false&"
                f"select=*"
            )

            import requests
            response = requests.get(query, headers=self.storage._get_headers())

            if response.status_code != 200:
                print(f"⚠️ Erreur Supabase: {response.status_code}")
                return {}

            appointments = response.json()

            # Filtrer par type (exclure PERSONAL, MEMO)
            filtered = []
            for apt in appointments:
                apt_type = apt.get('type', 'APPOINTMENT')
                if apt_type not in exclude_types:
                    filtered.append(apt)

            # Grouper par technicien
            by_technician = {}
            for apt in filtered:
                tech_id = apt.get('technician_external_id')
                if tech_id:
                    if tech_id not in by_technician:
                        by_technician[tech_id] = []

                    # Enrichir avec infos client si possible
                    client_id = apt.get('client_external_id')
                    client_name = apt.get('client_name', 'N/A')
                    client_email = None
                    client_phone = None

                    if client_id:
                        # Chercher le client dans Supabase
                        client_query = f"{self.storage.api_url}/gazelle_clients?external_id=eq.{client_id}&select=company_name,email,phone"
                        client_response = requests.get(client_query, headers=self.storage._get_headers())
                        if client_response.status_code == 200:
                            clients = client_response.json()
                            if clients:
                                client_name = clients[0].get('company_name', client_name)
                                client_email = clients[0].get('email')
                                client_phone = clients[0].get('phone')

                    by_technician[tech_id].append({
                        'id': apt.get('external_id'),
                        'appointment_date': apt.get('appointment_date'),
                        'appointment_time': apt.get('appointment_time'),
                        'title': apt.get('title', ''),
                        'description': apt.get('description', ''),
                        'client_id': client_id,
                        'client_name': client_name,
                        'client_email': client_email,
                        'client_phone': client_phone,
                        'status': apt.get('status', 'pending'),
                        'created_at': apt.get('created_at')
                    })

            return by_technician

        except Exception as e:
            print(f"❌ Erreur lors de la récupération des RV: {e}")
            import traceback
            traceback.print_exc()
            return {}

    def get_technician_info(self, tech_id: str) -> Optional[Dict[str, str]]:
        """
        Retourne les infos d'un technicien par son ID Gazelle.

        Args:
            tech_id: ID externe du technicien dans Gazelle

        Returns:
            dict avec 'name' et 'email', ou None si non trouvé
        """
        return self.TECHNICIANS.get(tech_id)

    def format_alert_message(
        self,
        technician_name: str,
        appointments: List[Dict[str, Any]],
        target_date: date
    ) -> str:
        """
        Formate le message d'alerte pour un technicien.

        Args:
            technician_name: Nom du technicien
            appointments: Liste des RV non confirmés
            target_date: Date des RV

        Returns:
            str: Message HTML formaté
        """
        date_str = target_date.strftime("%A %d %B %Y")

        html = f"""
        <html>
        <body style="font-family: Arial, sans-serif;">
            <h2 style="color: #d9534f;">⚠️ Rendez-vous non confirmés pour demain</h2>
            <p>Bonjour {technician_name},</p>
            <p>Les rendez-vous suivants pour <strong>{date_str}</strong> ne sont pas encore confirmés:</p>
            <table style="border-collapse: collapse; width: 100%; margin-top: 20px;">
                <thead>
                    <tr style="background-color: #f2f2f2;">
                        <th style="border: 1px solid #ddd; padding: 8px; text-align: left;">Heure</th>
                        <th style="border: 1px solid #ddd; padding: 8px; text-align: left;">Client</th>
                        <th style="border: 1px solid #ddd; padding: 8px; text-align: left;">Description</th>
                        <th style="border: 1px solid #ddd; padding: 8px; text-align: left;">Contact</th>
                    </tr>
                </thead>
                <tbody>
        """

        for apt in appointments:
            time = apt.get('appointment_time', 'N/A')
            client = apt.get('client_name', 'N/A')
            description = apt.get('title') or apt.get('description', '')
            phone = apt.get('client_phone', '')
            email = apt.get('client_email', '')

            contact = []
            if phone:
                contact.append(f"📞 {phone}")
            if email:
                contact.append(f"✉️ {email}")
            contact_str = "<br>".join(contact) if contact else "N/A"

            html += f"""
                    <tr>
                        <td style="border: 1px solid #ddd; padding: 8px;">{time}</td>
                        <td style="border: 1px solid #ddd; padding: 8px;"><strong>{client}</strong></td>
                        <td style="border: 1px solid #ddd; padding: 8px;">{description}</td>
                        <td style="border: 1px solid #ddd; padding: 8px;">{contact_str}</td>
                    </tr>
            """

        html += """
                </tbody>
            </table>
            <p style="margin-top: 20px;">Merci de contacter ces clients pour confirmer les rendez-vous.</p>
            <hr style="margin-top: 30px;">
            <p style="color: #777; font-size: 12px;">
                Cette alerte a été générée automatiquement par le système Assistant Gazelle V5.
            </p>
        </body>
        </html>
        """

        return html
