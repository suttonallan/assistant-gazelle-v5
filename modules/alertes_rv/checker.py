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
from core.gazelle_api_client import GazelleAPIClient


class AppointmentChecker:
    """Vérificateur de rendez-vous non confirmés."""

    def __init__(self, storage: Optional[SupabaseStorage] = None, gazelle_client: Optional[GazelleAPIClient] = None):
        """
        Initialise le vérificateur.

        Args:
            storage: Instance SupabaseStorage (créée si None)
            gazelle_client: Instance GazelleAPIClient (créée si None)
        """
        self.storage = storage or SupabaseStorage()
        self.gazelle_client = gazelle_client or GazelleAPIClient()
        # Cache simple en mémoire pour éviter de recharger les mêmes utilisateurs
        self._user_cache: Dict[str, Dict[str, str]] = {}
        # Cache pour confirmedByClient depuis Gazelle
        self._confirmed_cache: Dict[str, bool] = {}

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
            from core.timezone_utils import MONTREAL_TZ
            target_date = (datetime.now(MONTREAL_TZ) + timedelta(days=1)).date()

        if exclude_types is None:
            exclude_types = ['PERSONAL', 'MEMO']

        try:
            # Query Supabase pour les RV de la date cible
            # Table: gazelle_appointments
            # Colonnes: id, external_id, appointment_date, appointment_time,
            #           title, description, status, confirmed,
            #           technician_external_id, client_external_id

            date_str = target_date.isoformat()

            # Utiliser le client Supabase Python au lieu de requêtes HTTP manuelles
            # La colonne 'confirmed' n'existe PAS - on filtre par status = 'ACTIVE'
            appointments_raw = (
                self.storage.client.table('gazelle_appointments')
                .select('*')
                .gte('start_datetime', f'{date_str}T00:00:00')
                .lt('start_datetime', f'{date_str}T23:59:59')
                .eq('status', 'ACTIVE')  # Seulement les RV actifs
                .execute()
            )

            if not appointments_raw.data:
                return {}

            appointments = appointments_raw.data

            # Filtrer par type (exclure PERSONAL, MEMO) et par présence de client
            filtered = []
            for apt in appointments:
                apt_type = apt.get('type', 'APPOINTMENT')
                # Exclure les types non-client (PERSONAL, MEMO, etc.)
                if apt_type in exclude_types:
                    continue
                # Exclure les RV sans client (RV admin/personnel)
                # Un vrai RV client doit avoir client_external_id
                if not apt.get('client_external_id'):
                    continue
                filtered.append(apt)
            
            # VÉRIFICATION CRITIQUE: Vérifier confirmedByClient depuis Gazelle API
            # Ne garder que les RV qui sont vraiment non confirmés
            unconfirmed_filtered = []
            for apt in filtered:
                external_id = apt.get('external_id')
                if not external_id:
                    continue
                
                # Vérifier dans le cache d'abord
                if external_id in self._confirmed_cache:
                    is_confirmed = self._confirmed_cache[external_id]
                else:
                    # Récupérer depuis Gazelle API
                    is_confirmed = self._check_confirmed_in_gazelle(external_id)
                    self._confirmed_cache[external_id] = is_confirmed
                
                # Ne garder que les RV NON confirmés
                if not is_confirmed:
                    unconfirmed_filtered.append(apt)
            
            filtered = unconfirmed_filtered

            # Grouper par technicien
            by_technician = {}
            for apt in filtered:
                tech_id = apt.get('technicien')  # Colonne réelle dans gazelle_appointments
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
                        client_result = self.storage.client.table('gazelle_clients').select('company_name,email,phone').eq('external_id', client_id).limit(1).execute()
                        if client_result.data:
                            client_data = client_result.data[0]
                            client_name = client_data.get('company_name', client_name)
                            client_email = client_data.get('email')
                            client_phone = client_data.get('phone')

                    by_technician[tech_id].append({
                        'appointment_id': apt.get('id'),
                        'external_id': apt.get('external_id'),
                        'appointment_date': apt.get('appointment_date'),
                        'appointment_time': apt.get('appointment_time'),
                        'title': apt.get('title', ''),
                        'description': apt.get('description', ''),
                        'service_type': apt.get('type', 'APPOINTMENT'),
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
        Retourne les infos d'un technicien via la table users (gazelle_user_id).
        Fallback: cache / None si introuvable.
        """
        if not tech_id:
            return None

        if tech_id in self._user_cache:
            return self._user_cache[tech_id]

        try:
            # Utiliser le client Supabase Python
            # La colonne est 'external_id' pas 'gazelle_user_id'
            user_result = self.storage.client.table('users').select('external_id,first_name,last_name,email').eq('external_id', tech_id).limit(1).execute()
            
            if user_result.data:
                user = user_result.data[0]
                full_name = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()
                info = {
                    "id": tech_id,
                    "name": full_name or "Inconnu",
                    "email": user.get("email"),
                    "username": full_name,
                }
                self._user_cache[tech_id] = info
                return info
        except Exception as e:
            print(f"⚠️ Erreur get_technician_info pour {tech_id}: {e}")

        return None

    def _check_confirmed_in_gazelle(self, external_id: str) -> bool:
        """
        Vérifie si un RV est confirmé dans Gazelle en récupérant confirmedByClient depuis l'API.
        
        Args:
            external_id: ID externe du rendez-vous (ex: evt_xxx)
            
        Returns:
            True si le RV est confirmé OU s'il n'existe plus dans Gazelle (pour l'exclure des alertes)
            False si le RV existe mais n'est pas confirmé
        """
        try:
            # Récupérer les appointments depuis Gazelle
            # Limite augmentée à 500 pour être sûr de trouver tous les RV
            appointments = self.gazelle_client.get_appointments(limit=500)
            
            # Chercher le RV par external_id
            for apt in appointments:
                if apt.get('id') == external_id:
                    confirmed = apt.get('confirmedByClient', False)
                    # Si le RV existe dans Gazelle, retourner son statut de confirmation
                    return bool(confirmed)
            
            # Si le RV n'est pas trouvé dans Gazelle, il a probablement été supprimé/annulé/déplacé
            # On retourne True pour l'exclure des alertes (il n'existe plus)
            print(f"   ℹ️ RV {external_id} non trouvé dans Gazelle - exclu des alertes")
            return True  # Exclure des alertes car n'existe plus
            
        except Exception as e:
            print(f"⚠️ Erreur vérification confirmedByClient pour {external_id}: {e}")
            # En cas d'erreur, on exclut des alertes pour éviter les faux positifs
            return True

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
                        <th style="border: 1px solid #ddd; padding: 8px; text-align: left;">Type</th>
                        <th style="border: 1px solid #ddd; padding: 8px; text-align: left;">Description</th>
                        <th style="border: 1px solid #ddd; padding: 8px; text-align: left;">Contact</th>
                    </tr>
                </thead>
                <tbody>
        """

        for apt in appointments:
            time = apt.get('appointment_time', 'N/A')
            client = apt.get('client_name', 'N/A')
            service_type = apt.get('service_type') or apt.get('title', '') or ''
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
                        <td style="border: 1px solid #ddd; padding: 8px;">{service_type}</td>
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
