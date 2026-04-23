#!/usr/bin/env python3
"""
Service de synchronisation Gazelle → Supabase.

Synchronise les données depuis l'API Gazelle vers les tables gazelle.* dans Supabase.
Exécuté quotidiennement (CRON job) pour maintenir les données à jour.

Tables synchronisées (dans le schéma public):
- gazelle_clients
- gazelle_contacts
- gazelle_pianos
- gazelle_appointments
- gazelle_timeline_entries

Usage:
    python3 modules/sync_gazelle/sync_to_supabase.py
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import requests

# Ajouter le projet au path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dotenv import load_dotenv
load_dotenv()

from core.gazelle_api_client import GazelleAPIClient
from core.gazelle_api_client_incremental import GazelleAPIClientIncremental
from core.supabase_storage import SupabaseStorage
from core.timezone_utils import (
    format_for_gazelle_filter,
    parse_gazelle_datetime,
    format_for_supabase,
    extract_date_time
)
from scripts.sync_logger import SyncLogger
from config.techniciens_config import GAZELLE_IDS

# Types de RV à exclure des alertes Late Assignment
EXCLUDED_EVENT_TYPES = ['MEMO', 'BLOCKED', 'HOLIDAY']  # Note: PERSONAL peut être une institution

# Mots-clés pour identifier les RV d'institutions (alertes même sans client)
INSTITUTION_KEYWORDS = [
    'vincent-d\'indy', 'vincent d\'indy', 'vd ', ' vd', 'v-d',
    'place des arts', 'pda',
    'grands ballets', 'gnb',
    'orford',
    'uqam', 'pierre-péladeau',
    'cmm',
]


def _is_institution_appointment(title: str, location: str, description: str) -> bool:
    """Vérifie si un RV est lié à une institution."""
    text_to_check = f"{title or ''} {location or ''} {description or ''}".lower()
    for keyword in INSTITUTION_KEYWORDS:
        if keyword in text_to_check:
            return True
    return False


class GazelleToSupabaseSync:
    """Synchronise les données Gazelle vers Supabase."""

    def __init__(self, incremental_mode: bool = True):
        """Initialise le gestionnaire de synchronisation.

        Args:
            incremental_mode: Si True, utilise le mode incrémental rapide (<50 items/jour).
                             Si False, sync complète (5000+ items).
        """
        print("🔧 Initialisation du service de synchronisation...")
        self.incremental_mode = incremental_mode

        try:
            if incremental_mode:
                self.api_client = GazelleAPIClientIncremental()
                print("✅ Client API Gazelle initialisé (MODE INCRÉMENTAL RAPIDE)")
            else:
                self.api_client = GazelleAPIClient()
                print("✅ Client API Gazelle initialisé (mode complet)")
        except Exception as e:
            print(f"❌ Erreur d'initialisation API Gazelle: {e}")
            raise

        try:
            self.storage = SupabaseStorage()
            print("✅ Client Supabase initialisé")
        except Exception as e:
            print(f"❌ Erreur d'initialisation Supabase: {e}")
            raise

        self.stats = {
            'clients': {'synced': 0, 'errors': 0},
            'contacts': {'synced': 0, 'errors': 0},
            'pianos': {'synced': 0, 'errors': 0},
            'appointments': {'synced': 0, 'errors': 0},
            'timeline': {'synced': 0, 'errors': 0}
        }

        # Timestamp dernière sync (pour mode incrémental)
        self.last_sync_date = None
        if incremental_mode:
            self.last_sync_date = self._get_last_sync_date()

    def _get_last_sync_date(self) -> Optional[datetime]:
        """
        Récupère la date de dernière sync depuis Supabase (table system_settings).

        Returns:
            datetime de dernière sync, ou None si première sync
        """
        try:
            url = f"{self.storage.api_url}/system_settings?key=eq.last_sync_date&select=value"
            response = requests.get(url, headers=self.storage._get_headers())

            if response.status_code == 200:
                results = response.json()
                if results and len(results) > 0:
                    last_sync_str = results[0].get('value')
                    if last_sync_str:
                        last_sync_str_clean = last_sync_str.replace('Z', '+00:00') if last_sync_str.endswith('Z') else last_sync_str
                        last_sync = datetime.fromisoformat(last_sync_str_clean)
                        # S'assurer que last_sync est timezone-aware (UTC)
                        if last_sync.tzinfo is None:
                            from core.timezone_utils import UTC_TZ
                            last_sync = last_sync.replace(tzinfo=UTC_TZ)
                        else:
                            last_sync = last_sync.astimezone(UTC_TZ)
                        print(f"📅 Dernière sync: {last_sync.strftime('%Y-%m-%d %H:%M:%S')}")
                        return last_sync

            print("📅 Première sync (aucune date enregistrée)")
            return None

        except Exception as e:
            print(f"⚠️ Erreur récupération last_sync_date: {e}")
            return None

    def _save_last_sync_date(self, sync_date: datetime):
        """
        Enregistre la date de dernière sync dans Supabase.

        Args:
            sync_date: datetime à enregistrer
        """
        try:
            url = f"{self.storage.api_url}/system_settings?key=eq.last_sync_date"
            headers = self.storage._get_headers()
            headers["Prefer"] = "resolution=merge-duplicates"

            data = {
                "key": "last_sync_date",
                "value": sync_date.isoformat()
            }

            response = requests.post(url, headers=headers, json=data)

            if response.status_code in [200, 201]:
                print(f"✅ Dernière sync enregistrée: {sync_date.strftime('%Y-%m-%d %H:%M:%S')}")
            else:
                print(f"⚠️ Erreur enregistrement last_sync_date: {response.status_code}")

        except Exception as e:
            print(f"⚠️ Erreur sauvegarde last_sync_date: {e}")

    def _queue_late_assignment_alert(
        self,
        appointment_external_id: str,
        technician_id: str,
        appointment_date: str,
        appointment_time: Optional[str] = None,
        client_name: Optional[str] = None,
        location: Optional[str] = None,
        change_type: str = 'new'
    ):
        """
        Insère une alerte dans la file d'attente late_assignment_queue.
        
        Gère le buffer de 5 minutes et les heures de repos (21h-07h → 07h05).
        
        Args:
            appointment_external_id: ID externe du rendez-vous
            technician_id: ID du technicien (Gazelle)
            appointment_date: Date du rendez-vous (YYYY-MM-DD)
            appointment_time: Heure du rendez-vous (HH:MM)
            client_name: Nom du client
            location: Lieu du rendez-vous
        """
        try:
            from core.timezone_utils import MONTREAL_TZ
            from datetime import time as time_class
            
            now = datetime.now(MONTREAL_TZ)
            current_hour = now.hour
            
            # Calculer l'heure d'envoi
            if current_hour >= 21 or current_hour < 7:
                # Heures de repos: programmer pour 07h05 le matin même
                if current_hour >= 21:
                    # C'est le soir, programmer pour 07h05 demain
                    tomorrow = now.date() + timedelta(days=1)
                else:
                    # C'est la nuit (00h-06h59), programmer pour 07h05 aujourd'hui
                    tomorrow = now.date()
                
                scheduled_send_at = datetime.combine(tomorrow, time_class(7, 5), MONTREAL_TZ)
            else:
                # Heures normales: buffer de 5 minutes
                scheduled_send_at = now + timedelta(minutes=5)
            
            # Anti-doublon: vérifier si une entrée pending OU sent existe déjà
            # pour ce RV+technicien+date (une seule requête pour éviter race conditions)
            check_url = (
                f"{self.storage.api_url}/late_assignment_queue"
                f"?appointment_external_id=eq.{appointment_external_id}"
                f"&technician_id=eq.{technician_id}"
                f"&appointment_date=eq.{appointment_date}"
                f"&status=in.(pending,sent)"
            )
            check_response = requests.get(check_url, headers=self.storage._get_headers())

            if check_response.status_code == 200:
                existing = check_response.json()
                if existing and len(existing) > 0:
                    # Si une entrée sent existe, c'est un doublon complet
                    sent_entries = [e for e in existing if e.get('status') == 'sent']
                    if sent_entries:
                        print(f"⏭️  Alerte déjà envoyée pour RV {appointment_external_id} → tech {technician_id} → doublon ignoré")
                        return

                    # Si une entrée pending existe, reset le timer
                    pending_entry = next((e for e in existing if e.get('status') == 'pending'), None)
                    if pending_entry:
                        update_url = f"{self.storage.api_url}/late_assignment_queue?id=eq.{pending_entry['id']}"
                        update_headers = self.storage._get_headers()
                        update_headers["Prefer"] = "return=representation"

                        update_data = {
                            'scheduled_send_at': scheduled_send_at.isoformat(),
                            'updated_at': now.isoformat()
                        }

                        update_response = requests.patch(update_url, headers=update_headers, json=update_data)
                        if update_response.status_code in [200, 204]:
                            print(f"🔄 Alerte mise à jour (reset timer) pour RV {appointment_external_id} → tech {technician_id}")
                        return
            
            # Créer une nouvelle entrée
            queue_entry = {
                'appointment_external_id': appointment_external_id,
                'technician_id': technician_id,
                'appointment_date': appointment_date,
                'appointment_time': appointment_time,
                'client_name': client_name,
                'location': location,
                'scheduled_send_at': scheduled_send_at.isoformat(),
                'status': 'pending',
                'change_type': change_type
            }

            url = f"{self.storage.api_url}/late_assignment_queue"
            headers = self.storage._get_headers()
            headers["Prefer"] = "resolution=merge-duplicates"

            response = requests.post(url, headers=headers, json=queue_entry)

            # Fallback: si change_type column n'existe pas encore, retry sans
            if response.status_code in [400, 406] and 'change_type' in (response.text or ''):
                del queue_entry['change_type']
                response = requests.post(url, headers=headers, json=queue_entry)
            
            if response.status_code in [200, 201]:
                send_time_str = scheduled_send_at.strftime('%Y-%m-%d %H:%M')
                print(f"📧 Alerte programmée pour RV {appointment_external_id} → tech {technician_id} (envoi: {send_time_str})")
            else:
                print(f"⚠️  Erreur insertion queue alerte {appointment_external_id}: {response.status_code} - {response.text}")
                
        except Exception as e:
            print(f"⚠️  Erreur queue alerte {appointment_external_id}: {e}")
            # Ne pas faire échouer la sync pour ça

    def sync_clients(self) -> int:
        """
        Synchronise les clients depuis l'API vers Supabase.

        Mode incrémental: Seuls les clients modifiés depuis last_sync_date sont récupérés.

        Returns:
            Nombre de clients synchronisés
        """
        print("\n📋 Synchronisation des clients...")

        try:
            # Mode incrémental ou complet
            if self.incremental_mode and hasattr(self.api_client, 'get_clients_incremental'):
                print("🚀 Mode incrémental activé (early exit sur updatedAt)")
                api_clients = self.api_client.get_clients_incremental(
                    last_sync_date=self.last_sync_date,
                    limit=5000  # Sécurité
                )
            else:
                # Mode complet (legacy)
                api_clients = self.api_client.get_clients(limit=1000)

            if not api_clients:
                print("⚠️  Aucun client récupéré depuis l'API")
                return 0

            print(f"📥 {len(api_clients)} clients récupérés depuis l'API")

            for client_data in api_clients:
                try:
                    # Extraire données du client
                    external_id = client_data.get('id')
                    company_name_raw = client_data.get('companyName')
                    company_name = company_name_raw.strip() if company_name_raw else ''
                    status = client_data.get('status', 'active')
                    tags = client_data.get('tags', [])

                    # Contact par défaut (pour first_name/last_name)
                    default_contact = client_data.get('defaultContact', {})

                    # Extraire first_name et last_name du contact
                    first_name = ''
                    last_name = ''
                    if default_contact:
                        first_name_raw = default_contact.get('firstName')
                        last_name_raw = default_contact.get('lastName')
                        first_name = first_name_raw.strip() if first_name_raw else ''
                        last_name = last_name_raw.strip() if last_name_raw else ''

                    # Si CompanyName vide, construire à partir du nom du contact (pour compatibilité)
                    if not company_name and (first_name or last_name):
                        company_name = f"{first_name} {last_name}".strip()

                    # Vérifier qu'on a au moins un identifiant
                    if not company_name and not first_name and not last_name:
                        print(f"⚠️  Client {external_id} ignoré (aucun nom disponible)")
                        self.stats['clients']['errors'] += 1
                        continue

                    # Email, téléphone, ville/code postal du contact
                    email = None
                    phone = None
                    city = None
                    postal_code = None

                    if default_contact:
                        default_email = default_contact.get('defaultEmail', {})
                        if default_email:
                            email = default_email.get('email')

                        default_phone = default_contact.get('defaultPhone', {})
                        if default_phone:
                            phone = default_phone.get('phoneNumber')

                        default_location = default_contact.get('defaultLocation', {})
                        if default_location:
                            city = default_location.get('municipality')
                            postal_code = default_location.get('postalCode')

                    # Notes personnelles et préférences du client
                    personal_notes = client_data.get('personalNotes', '') or ''
                    preference_notes = client_data.get('preferenceNotes', '') or ''

                    # Langue du client (depuis defaultClientLocalization)
                    localization = client_data.get('defaultClientLocalization') or {}
                    locale = localization.get('locale') or None

                    # Préférences de communication du contact
                    wants_email = default_contact.get('wantsEmail') if default_contact else None
                    wants_phone = default_contact.get('wantsPhone') if default_contact else None
                    wants_text = default_contact.get('wantsText') if default_contact else None

                    # Mobile confirmé
                    mobile_phone = None
                    if default_contact:
                        confirmed_mobile = default_contact.get('defaultConfirmedMobilePhone') or {}
                        mobile_phone = confirmed_mobile.get('phoneNumber')

                    # Préparer données pour Supabase
                    client_record = {
                        'external_id': external_id,
                        'company_name': company_name,
                        'first_name': first_name if first_name else None,
                        'last_name': last_name if last_name else None,
                        'status': status,
                        'email': email,
                        'phone': phone,
                        'city': city,
                        'postal_code': postal_code,
                        'personal_notes': personal_notes.strip() if personal_notes else None,
                        'preference_notes': preference_notes.strip() if preference_notes else None,
                        'locale': locale,
                        'preferred_technician_id': client_data.get('preferredTechnicianId'),
                        'client_type': client_data.get('clientType'),
                        'lifecycle_state': client_data.get('lifecycleState'),
                        'referred_by': client_data.get('referredBy'),
                        'no_contact_until': client_data.get('noContactUntil'),
                        'no_contact_reason': client_data.get('noContactReason'),
                        'wants_email': wants_email,
                        'wants_phone': wants_phone,
                        'wants_text': wants_text,
                        'mobile_phone': mobile_phone,
                        'created_at': client_data.get('createdAt'),
                        'updated_at': datetime.now().isoformat()
                    }
                    
                    # ⚠️ IMPORTANT: Ne mettre à jour les tags QUE si l'API en retourne
                    # pour éviter d'écraser les tags existants (ex: 'institutional')
                    if tags:
                        client_record['tags'] = tags

                    # UPSERT dans Supabase (via REST API avec on_conflict)
                    url = f"{self.storage.api_url}/gazelle_clients?on_conflict=external_id"
                    headers = self.storage._get_headers()
                    headers["Prefer"] = "resolution=merge-duplicates"

                    response = requests.post(url, headers=headers, json=client_record)

                    if response.status_code in [200, 201]:
                        self.stats['clients']['synced'] += 1
                    elif response.status_code == 409:
                        # 409 = Conflict (déjà synchronisé, normal avec UPSERT)
                        self.stats['clients']['synced'] += 1
                    else:
                        print(f"❌ Erreur UPSERT client {external_id}: {response.status_code}")
                        print(f"   Response: {response.text[:300]}")
                        self.stats['clients']['errors'] += 1

                except Exception as e:
                    print(f"❌ Erreur client {client_data.get('id', 'unknown')}: {e}")
                    self.stats['clients']['errors'] += 1
                    continue

            print(f"✅ {self.stats['clients']['synced']} clients synchronisés")
            return self.stats['clients']['synced']

        except Exception as e:
            print(f"❌ Erreur lors de la synchronisation des clients: {e}")
            raise

    def sync_contacts(self) -> int:
        """
        Synchronise les contacts depuis l'API vers Supabase.

        Note: Dans Gazelle, les contacts sont des personnes individuelles
        associées aux clients (entités qui paient).

        Returns:
            Nombre de contacts synchronisés
        """
        print("\n👥 Synchronisation des contacts...")

        try:
            # Récupérer contacts depuis API Gazelle
            api_contacts = self.api_client.get_contacts(limit=2000)
            print(f"📥 {len(api_contacts)} contacts récupérés depuis l'API")

            # Initialiser stats
            self.stats['contacts'] = {'total': len(api_contacts), 'synced': 0, 'errors': 0}

            # Synchroniser chaque contact
            for contact_data in api_contacts:
                try:
                    external_id = contact_data.get('id')
                    if not external_id:
                        print(f"⚠️  Contact sans ID ignoré")
                        continue

                    # Extraire les données du contact
                    first_name = contact_data.get('firstName')
                    last_name = contact_data.get('lastName')
                    company_name = contact_data.get('companyName')

                    # Email et téléphone (peuvent être None)
                    default_email = contact_data.get('defaultEmail', {})
                    email = default_email.get('email') if default_email else None

                    default_phone = contact_data.get('defaultPhone', {})
                    phone = default_phone.get('phoneNumber') if default_phone else None

                    # Localisation (peut être None)
                    default_location = contact_data.get('defaultLocation', {})
                    city = default_location.get('municipality') if default_location else None
                    province = default_location.get('province') if default_location else None
                    postal_code = default_location.get('postalCode') if default_location else None
                    street_address = default_location.get('streetAddress') if default_location else None

                    # Client associé (peut être None)
                    client_data = contact_data.get('client', {})
                    client_id = client_data.get('id') if client_data else None
                    client_company_name = client_data.get('companyName') if client_data else None

                    # Construire le payload pour Supabase
                    # Note: Le schéma de la table gazelle_contacts a seulement:
                    # external_id, client_external_id, first_name, last_name, email, phone, is_default, created_at, updated_at
                    contact_payload = {
                        'external_id': external_id,
                        'client_external_id': client_id,
                        'first_name': first_name,
                        'last_name': last_name,
                        'email': email,
                        'phone': phone,
                        'is_default': True,  # C'est le defaultContact du client
                        'created_at': contact_data.get('createdAt'),
                        'updated_at': contact_data.get('updatedAt')
                    }

                    # UPSERT dans Supabase via REST API avec on_conflict
                    url = f"{self.storage.api_url}/gazelle_contacts?on_conflict=external_id"
                    headers = self.storage._get_headers()
                    headers['Prefer'] = 'resolution=merge-duplicates'

                    response = requests.post(url, json=contact_payload, headers=headers)

                    if response.status_code in [200, 201]:
                        self.stats['contacts']['synced'] += 1
                    elif response.status_code == 409:
                        # 409 = Conflict (déjà synchronisé, normal avec UPSERT)
                        self.stats['contacts']['synced'] += 1
                    else:
                        print(f"❌ Erreur UPSERT contact {external_id}: {response.status_code}")
                        self.stats['contacts']['errors'] += 1

                except Exception as e:
                    print(f"❌ Erreur contact {contact_data.get('id', 'unknown')}: {e}")
                    self.stats['contacts']['errors'] += 1
                    continue

            print(f"✅ {self.stats['contacts']['synced']} contacts synchronisés")
            return self.stats['contacts']['synced']

        except Exception as e:
            print(f"❌ Erreur lors de la synchronisation des contacts: {e}")
            raise

    def sync_pianos(self) -> int:
        """
        Synchronise les pianos depuis l'API vers Supabase.

        Mode incrémental: Seuls les pianos modifiés depuis last_sync_date sont récupérés.

        Returns:
            Nombre de pianos synchronisés
        """
        print("\n🎹 Synchronisation des pianos...")

        try:
            # Mode incrémental ou complet
            if self.incremental_mode and hasattr(self.api_client, 'get_pianos_incremental'):
                print("🚀 Mode incrémental activé (early exit sur updatedAt)")
                api_pianos = self.api_client.get_pianos_incremental(
                    last_sync_date=self.last_sync_date,
                    limit=5000  # Sécurité
                )
            else:
                # Mode complet (legacy)
                api_pianos = self.api_client.get_pianos(limit=1000)

            if not api_pianos:
                print("⚠️  Aucun piano récupéré depuis l'API")
                return 0

            print(f"📥 {len(api_pianos)} pianos récupérés depuis l'API")

            for piano_data in api_pianos:
                try:
                    external_id = piano_data.get('id')
                    client_obj = piano_data.get('client', {})
                    client_id = client_obj.get('id') if client_obj else None
                    make = piano_data.get('make', '')
                    model = piano_data.get('model', '')
                    serial_number = piano_data.get('serialNumber')
                    piano_type = piano_data.get('type', 'upright')
                    year = piano_data.get('year')
                    location = piano_data.get('location', '')
                    notes = piano_data.get('notes', '')

                    # Nouveaux champs Dampp-Chaser (si disponibles dans l'API)
                    dampp_chaser_installed = piano_data.get('damppChaserInstalled', False)
                    dampp_chaser_humidistat_model = piano_data.get('damppChaserHumidistatModel')
                    dampp_chaser_mfg_date = piano_data.get('damppChaserMfgDate')

                    piano_record = {
                        'external_id': external_id,
                        'client_external_id': client_id,
                        'make': make,
                        'model': model,
                        'serial_number': serial_number,
                        'type': piano_type,
                        'year': year,
                        'location': location,
                        'notes': notes,
                        'dampp_chaser_installed': dampp_chaser_installed,
                        'dampp_chaser_humidistat_model': dampp_chaser_humidistat_model,
                        'dampp_chaser_mfg_date': dampp_chaser_mfg_date,
                        'updated_at': datetime.now().isoformat()
                    }

                    # UPSERT avec on_conflict
                    url = f"{self.storage.api_url}/gazelle_pianos?on_conflict=external_id"
                    headers = self.storage._get_headers()
                    headers["Prefer"] = "resolution=merge-duplicates"

                    response = requests.post(url, headers=headers, json=piano_record)

                    if response.status_code in [200, 201]:
                        self.stats['pianos']['synced'] += 1
                    elif response.status_code == 409:
                        # 409 = Conflict (déjà synchronisé, normal avec UPSERT)
                        self.stats['pianos']['synced'] += 1
                    else:
                        print(f"❌ Erreur UPSERT piano {external_id}: {response.status_code}")
                        self.stats['pianos']['errors'] += 1

                except Exception as e:
                    print(f"❌ Erreur piano {piano_data.get('id', 'unknown')}: {e}")
                    self.stats['pianos']['errors'] += 1
                    continue

            print(f"✅ {self.stats['pianos']['synced']} pianos synchronisés")
            return self.stats['pianos']['synced']

        except Exception as e:
            print(f"❌ Erreur lors de la synchronisation des pianos: {e}")
            raise

    def sync_appointments(self, start_date_override: Optional[str] = None, force_historical: bool = False) -> int:
        """
        Synchronise les rendez-vous depuis Gazelle vers Supabase.

        LOGIQUE INTELLIGENTE:
        1. Premier import: Récupère TOUT depuis 2017 (historique complet)
        2. Syncs suivants: Seulement les 7 derniers jours (incrémental)

        Utilise un marqueur 'appointments_historical_import_done' dans system_settings.

        Args:
            start_date_override: Date de début explicite (YYYY-MM-DD). Si fourni, force cette date.
            force_historical: Si True, force un import historique complet même si déjà fait.

        Returns:
            Nombre de rendez-vous synchronisés
        """
        print("\n📅 Synchronisation des rendez-vous...")

        # Déterminer si c'est le premier import ou un sync incrémental
        historical_done = False

        if not force_historical and not start_date_override:
            try:
                # Vérifier si l'import historique a déjà été fait
                url = f"{self.storage.api_url}/system_settings?key=eq.appointments_historical_import_done&select=value"
                response = requests.get(url, headers=self.storage._get_headers())

                if response.status_code == 200:
                    data = response.json()
                    if data and len(data) > 0:
                        historical_done = data[0]['value'] == 'true'
            except Exception as e:
                print(f"⚠️  Impossible de vérifier le marqueur d'import: {e}")

        # SÉCURITÉ: Toujours mode incrémental par défaut (7 jours)
        # L'import historique complet doit être lancé MANUELLEMENT avec force_historical=True
        if start_date_override:
            # Override manuel - convertir date Montreal → UTC pour filtre API
            from datetime import datetime as dt
            from core.timezone_utils import MONTREAL_TZ
            # Parser la date et s'assurer qu'elle est timezone-aware (Montreal)
            start_dt = dt.fromisoformat(start_date_override)
            if start_dt.tzinfo is None:
                start_dt = start_dt.replace(tzinfo=MONTREAL_TZ)
            effective_start_date = format_for_gazelle_filter(start_dt)
            print(f"🎯 Mode manuel: import depuis {start_date_override} Montreal → {effective_start_date} UTC")
        else:
            # TOUJOURS mode incrémental: 7 derniers jours (ignore le marqueur historical_done)
            from core.timezone_utils import MONTREAL_TZ
            start_dt = datetime.now(MONTREAL_TZ) - timedelta(days=7)
            effective_start_date = format_for_gazelle_filter(start_dt)
            print(f"🔄 Sync incrémental SÉCURISÉE: derniers 7 jours")
            print(f"   📍 Depuis: {start_dt.strftime('%Y-%m-%d')} Montreal → {effective_start_date} UTC")
            print(f"   ℹ️  Import historique désactivé pour workflow automatique")
            print(f"   ℹ️  Pour import complet 2017-maintenant: lancer manuellement avec force_historical=True")

        try:
            # Mode incrémental rapide ou legacy
            if self.incremental_mode and hasattr(self.api_client, 'get_appointments_incremental'):
                print("🚀 Mode incrémental rapide (sortBy DATE_DESC + filtre)")
                api_appointments = self.api_client.get_appointments_incremental(
                    last_sync_date=self.last_sync_date,
                    limit=None
                )
            else:
                # Mode legacy (allEventsBatched sans sortBy)
                api_appointments = self.api_client.get_appointments(
                    limit=None,
                    start_date_override=effective_start_date
                )

            if not api_appointments:
                print("⚠️  Aucun rendez-vous récupéré depuis l'API")
                return 0

            print(f"📥 {len(api_appointments)} rendez-vous récupérés depuis l'API")

            for appt_data in api_appointments:
                try:
                    external_id = appt_data.get('id')

                    # Client
                    client_obj = appt_data.get('client', {})
                    client_id = client_obj.get('id') if client_obj else None

                    # Titre et notes
                    title = appt_data.get('title', '')
                    notes_raw = appt_data.get('notes', '')
                    description = notes_raw

                    # Date et heure depuis start (CoreDateTime)
                    start_time = appt_data.get('start')
                    appointment_date = None
                    appointment_time = None
                    start_time_utc = None

                    if start_time:
                        try:
                            # Parser le CoreDateTime (UTC) et extraire date/heure en Montreal
                            dt_parsed = parse_gazelle_datetime(start_time)
                            if dt_parsed:
                                # Extraire date/heure en timezone Montreal (pour les colonnes séparées)
                                appointment_date, appointment_time = extract_date_time(dt_parsed)
                                # Formater pour Supabase (UTC avec 'Z')
                                start_time_utc = format_for_supabase(dt_parsed)
                        except Exception as e:
                            print(f"⚠️ Erreur conversion heure '{start_time}': {e}")
                            pass

                    # Durée en minutes
                    duration_minutes = appt_data.get('duration')

                    # Status
                    status = appt_data.get('status', 'scheduled')

                    # Technicien (depuis user.id - maintenant disponible avec V4 query)
                    user_obj = appt_data.get('user', {})
                    technicien = user_obj.get('id') if user_obj else None

                    # Location (pas disponible simplement)
                    location = ''

                    # Notes
                    notes = notes_raw if notes_raw else title

                    # Nouveaux champs V4
                    event_type = appt_data.get('type', 'APPOINTMENT')
                    is_all_day = appt_data.get('isAllDay', False)
                    confirmed_by_client = appt_data.get('confirmedByClient', False)
                    source = appt_data.get('source', 'MANUAL')
                    travel_mode = appt_data.get('travelMode', '')

                    # CreatedAt (Gazelle — date réelle de création du RV)
                    gazelle_created_at = appt_data.get('createdAt')

                    # CreatedBy
                    created_by_obj = appt_data.get('createdBy', {})
                    created_by_user_id = created_by_obj.get('id') if created_by_obj else None

                    # Piano (extraction V4 - ligne 264)
                    piano_id = None
                    piano_nodes = (appt_data.get('allEventPianos') or {}).get('nodes', [])
                    if piano_nodes and len(piano_nodes) > 0:
                        first_piano_node = piano_nodes[0]
                        if first_piano_node and first_piano_node.get('piano'):
                            piano_id = first_piano_node['piano'].get('id')

                    appointment_record = {
                        'external_id': external_id,
                        'client_external_id': client_id,
                        'piano_external_id': piano_id,  # 🔗 Lien direct vers le piano (extrait de allEventPianos)
                        'title': title,
                        'description': description,
                        'appointment_date': appointment_date,
                        'appointment_time': appointment_time,
                        'start_datetime': start_time_utc,  # CoreDateTime complet en UTC
                        'duration_minutes': duration_minutes,
                        'status': status,
                        'technicien': technicien,
                        'location': location,
                        'notes': notes,
                        # NOTE: created_at n'est PAS inclus ici - la DB le set automatiquement sur INSERT
                        # Inclure created_at avec start_time causait des faux positifs dans la détection Late Assignment
                        'updated_at': format_for_supabase(datetime.now())
                    }

                    # Détecter changement AVANT l'UPSERT
                    # Récupérer l'ancien record pour comparer
                    old_record = None
                    try:
                        # Fetch old record — last_notified_schedule may not exist yet (migration pending)
                        check_url = f"{self.storage.api_url}/gazelle_appointments?external_id=eq.{external_id}&select=technicien,last_notified_tech_id,last_notified_schedule,appointment_date,appointment_time,status,updated_at,created_at"
                        check_response = requests.get(check_url, headers=self.storage._get_headers())
                        if check_response.status_code in [400, 406] and 'last_notified_schedule' in (check_response.text or ''):
                            check_url = f"{self.storage.api_url}/gazelle_appointments?external_id=eq.{external_id}&select=technicien,last_notified_tech_id,appointment_date,appointment_time,status,updated_at,created_at"
                            check_response = requests.get(check_url, headers=self.storage._get_headers())
                        if check_response.status_code == 200:
                            old_data = check_response.json()
                            if old_data and len(old_data) > 0:
                                old_record = old_data[0]
                    except Exception as e:
                        print(f"⚠️  Erreur récupération ancien record {external_id}: {e}")

                    # UPSERT avec on_conflict
                    url = f"{self.storage.api_url}/gazelle_appointments?on_conflict=external_id"
                    headers = self.storage._get_headers()
                    headers["Prefer"] = "resolution=merge-duplicates"

                    response = requests.post(url, headers=headers, json=appointment_record)

                    if response.status_code in [200, 201]:
                        self.stats['appointments']['synced'] += 1
                    elif response.status_code == 409:
                        # 409 = Conflict (déjà synchronisé, normal avec UPSERT)
                        self.stats['appointments']['synced'] += 1
                    else:
                        print(f"❌ Erreur UPSERT appointment {external_id}: {response.status_code} - {response.text}")
                        self.stats['appointments']['errors'] += 1
                        continue  # Skip la détection de changement si l'UPSERT a échoué

                    # DÉTECTION DE CHANGEMENT DE TECHNICIEN pour alerte "Late Assignment"
                    # Conditions:
                    # 1. RV avec un CLIENT OU institution (vincent-d'indy, etc.)
                    # 2. Technicien est un vrai technicien (pas Louise/assistants)
                    # 3. Type de RV n'est pas MEMO, BLOCKED, HOLIDAY
                    is_technician = technicien in GAZELLE_IDS
                    is_valid_type = event_type not in EXCLUDED_EVENT_TYPES
                    is_institution = _is_institution_appointment(title, location, description)
                    has_client_or_institution = bool(client_id) or is_institution

                    if technicien and appointment_date and has_client_or_institution and is_technician and is_valid_type:
                        try:
                            from core.timezone_utils import MONTREAL_TZ
                            from datetime import date as date_class, time as time_class

                            now = datetime.now(MONTREAL_TZ)

                            # Parser la date du rendez-vous
                            appt_date = None
                            if isinstance(appointment_date, str):
                                try:
                                    appt_date = date_class.fromisoformat(appointment_date)
                                except:
                                    pass
                            elif isinstance(appointment_date, date_class):
                                appt_date = appointment_date

                            # Parser l'heure du rendez-vous (défaut: 09:00 si non spécifié)
                            appt_time = time_class(9, 0)
                            if appointment_time:
                                try:
                                    if isinstance(appointment_time, str):
                                        # Format HH:MM:SS ou HH:MM
                                        parts = appointment_time.split(':')
                                        appt_time = time_class(int(parts[0]), int(parts[1]))
                                    elif isinstance(appointment_time, time_class):
                                        appt_time = appointment_time
                                except:
                                    pass

                            # Calculer le datetime complet du RV
                            # Fenêtre de 7 jours : les techs consultent leur calendrier de la semaine
                            # le dimanche — toute assignation/changement de la semaine doit être notifié
                            ALERT_WINDOW_HOURS = 7 * 24  # 168h = 7 jours
                            is_within_alert_window = False
                            if appt_date:
                                appt_datetime = datetime.combine(appt_date, appt_time, MONTREAL_TZ)
                                hours_until_appt = (appt_datetime - now).total_seconds() / 3600
                                is_within_alert_window = 0 < hours_until_appt < ALERT_WINDOW_HOURS

                                if is_within_alert_window:
                                    days_until = hours_until_appt / 24
                                    print(f"⏰ RV dans {days_until:.1f}j ({hours_until_appt:.0f}h) → vérification late assignment")

                            if is_within_alert_window:
                                old_technicien = old_record.get('technicien') if old_record else None
                                last_notified = old_record.get('last_notified_tech_id') if old_record else None
                                last_notified_schedule = old_record.get('last_notified_schedule') if old_record else None

                                # Snapshot horaire actuel pour comparaison
                                current_schedule = f"{appointment_date} {appointment_time or '09:00'}"

                                # Vérifier si le RV a été CRÉÉ récemment dans Gazelle (< 24h)
                                is_recently_created = False
                                created_age_hours = None
                                if gazelle_created_at:
                                    try:
                                        created_dt = datetime.fromisoformat(gazelle_created_at.replace('Z', '+00:00'))
                                        created_age_hours = (now - created_dt).total_seconds() / 3600
                                        is_recently_created = created_age_hours < 24
                                    except:
                                        pass

                                print(f"🔍 Late Assignment check {external_id}: tech={technicien}, old={old_technicien}, notified={last_notified}, schedule={current_schedule}, old_schedule={last_notified_schedule}, created_recently={is_recently_created}")

                                # Déterminer le type de changement (par priorité)
                                # 1. Nouveau RV (créé < 24h, jamais vu)
                                # 2. Technicien changé
                                # 3. Horaire modifié (date ou heure)
                                # JAMAIS alerter pour un vieux RV simplement modifié (notes, etc.)
                                change_type = None

                                if not old_record and is_recently_created:
                                    change_type = 'new'
                                    age_str = f"{created_age_hours:.1f}h" if created_age_hours else ""
                                    print(f"   ✅ Nouveau RV (créé il y a {age_str}) → alerte")
                                elif not old_record and not is_recently_created:
                                    age_str = f"{created_age_hours:.1f}h" if created_age_hours else "inconnue"
                                    print(f"   ⏭���  RV absent de la DB mais créé il y a {age_str} → pas d'alerte (vieux RV)")
                                elif old_technicien != technicien and last_notified != technicien:
                                    change_type = 'reassigned'
                                    print(f"   ✅ Technicien changé ({old_technicien} → {technicien}) → alerte")
                                elif current_schedule != last_notified_schedule and last_notified_schedule is not None:
                                    change_type = 'rescheduled'
                                    print(f"   ✅ Horaire modifié ({last_notified_schedule} → {current_schedule}) → alerte")
                                elif last_notified is None and old_record:
                                    # Première notification pour ce RV (jamais notifié, mais existe en DB)
                                    # Seulement si créé récemment OU si on n'a jamais notifié du tout
                                    if is_recently_created:
                                        change_type = 'new'
                                        print(f"   ✅ RV récent jamais notifié → alerte")
                                else:
                                    print(f"   ⏭️  Pas de changement pertinent → pas d'alerte")

                                if change_type:
                                    # Insérer dans la file d'attente avec le type de changement
                                    self._queue_late_assignment_alert(
                                        appointment_external_id=external_id,
                                        technician_id=technicien,
                                        appointment_date=appointment_date,
                                        appointment_time=appointment_time,
                                        client_name=client_obj.get('name', '') if client_obj else None,
                                        location=location,
                                        change_type=change_type
                                    )

                                    # Si réassignation : notifier aussi l'ancien tech
                                    # que sa plage est libérée
                                    if change_type == 'reassigned' and old_technicien and old_technicien in GAZELLE_IDS:
                                        self._queue_late_assignment_alert(
                                            appointment_external_id=external_id,
                                            technician_id=old_technicien,
                                            appointment_date=appointment_date,
                                            appointment_time=appointment_time,
                                            client_name=client_obj.get('name', '') if client_obj else None,
                                            location=location,
                                            change_type='cancelled'
                                        )
                                        print(f"   📤 Plage libérée envoyée à l'ancien tech {old_technicien}")

                                    # Mettre à jour les marqueurs anti-doublon
                                    update_url = f"{self.storage.api_url}/gazelle_appointments?external_id=eq.{external_id}"
                                    update_headers = self.storage._get_headers()
                                    update_headers["Prefer"] = "return=representation"
                                    update_data = {
                                        'last_notified_tech_id': technicien,
                                        'last_notified_schedule': current_schedule
                                    }
                                    patch_resp = requests.patch(update_url, headers=update_headers, json=update_data)
                                    # Fallback: si last_notified_schedule n'existe pas encore
                                    if patch_resp.status_code in [400, 406] and 'last_notified_schedule' in (patch_resp.text or ''):
                                        del update_data['last_notified_schedule']
                                        requests.patch(update_url, headers=update_headers, json=update_data)
                                    
                        except Exception as e:
                            print(f"⚠️  Erreur détection changement technicien {external_id}: {e}")
                            # Ne pas faire échouer la sync pour ça

                except Exception as e:
                    print(f"❌ Erreur appointment {appt_data.get('id', 'unknown')}: {e}")
                    self.stats['appointments']['errors'] += 1

            print(f"✅ {self.stats['appointments']['synced']} rendez-vous synchronisés")

            # ═══════════════════════════════════════════════════════════════════
            # NETTOYAGE RV ANNULÉS: Marquer comme CANCELLED (pas supprimer)
            # Quand un RV disparaît de l'API Gazelle, on le marque CANCELLED
            # dans Supabase plutôt que de le supprimer. C'est réversible et
            # empêche les RV fantômes d'apparaître dans "Ma Journée".
            # ═══════════════════════════════════════════════════════════════════
            MAX_CANCELLATIONS_ALLOWED = 10  # Seuil de sécurité

            try:
                print("\n🧹 Vérification des rendez-vous supprimés/annulés dans Gazelle...")

                # 1. Récupérer tous les external_id depuis Gazelle (pour la période synchronisée)
                gazelle_ids = {appt.get('id') for appt in api_appointments if appt.get('id')}
                print(f"   📋 {len(gazelle_ids)} rendez-vous actifs dans Gazelle")

                # 2. Récupérer tous les external_id ACTIFS depuis Supabase
                # Couvrir les 7 derniers jours ET les 14 prochains jours
                # pour détecter les RV supprimés dans Gazelle avant le jour J
                if start_date_override:
                    date_filter = start_date_override
                else:
                    date_filter = start_dt.strftime('%Y-%m-%d')
                future_filter = (datetime.now(MONTREAL_TZ) + timedelta(days=14)).strftime('%Y-%m-%d')

                url = f"{self.storage.api_url}/gazelle_appointments?appointment_date=gte.{date_filter}&appointment_date=lte.{future_filter}&status=neq.CANCELLED&select=external_id"
                response = requests.get(url, headers=self.storage._get_headers())

                if response.status_code == 200:
                    supabase_appointments = response.json()
                    supabase_ids = {appt['external_id'] for appt in supabase_appointments if appt.get('external_id')}
                    print(f"   📋 {len(supabase_ids)} rendez-vous actifs dans Supabase (période synchronisée)")

                    # 3. Identifier les RV absents de Gazelle (annulés)
                    ids_to_cancel = supabase_ids - gazelle_ids

                    if ids_to_cancel:
                        print(f"   ℹ️  {len(ids_to_cancel)} rendez-vous absents de Gazelle (annulés)")

                        for ext_id in list(ids_to_cancel)[:10]:
                            print(f"      - {ext_id}")
                        if len(ids_to_cancel) > 10:
                            print(f"      ... et {len(ids_to_cancel) - 10} autres")

                        if len(ids_to_cancel) > MAX_CANCELLATIONS_ALLOWED:
                            print(f"   🚨 ALERTE: {len(ids_to_cancel)} > {MAX_CANCELLATIONS_ALLOWED} (seuil max)")
                            print(f"   🔒 MARQUAGE BLOQUÉ - Trop de RV à annuler (possible erreur API)")
                        else:
                            # Marquer comme CANCELLED (réversible, pas de suppression)
                            # ET notifier le technicien que la plage est libérée
                            cancelled_count = 0
                            for ext_id in ids_to_cancel:
                                # Récupérer les infos du RV AVANT de le marquer CANCELLED
                                info_url = f"{self.storage.api_url}/gazelle_appointments?external_id=eq.{ext_id}&select=technicien,appointment_date,appointment_time,title,location"
                                info_response = requests.get(info_url, headers=self.storage._get_headers())
                                rv_info = None
                                if info_response.status_code == 200:
                                    info_data = info_response.json()
                                    if info_data:
                                        rv_info = info_data[0]

                                patch_url = f"{self.storage.api_url}/gazelle_appointments?external_id=eq.{ext_id}"
                                headers = self.storage._get_headers()
                                patch_data = {
                                    'status': 'CANCELLED',
                                    'updated_at': format_for_supabase(datetime.now())
                                }
                                patch_response = requests.patch(patch_url, headers=headers, json=patch_data)

                                if patch_response.status_code in [200, 204]:
                                    cancelled_count += 1
                                    print(f"      ✓ Marqué CANCELLED: {ext_id}")

                                    # Notifier le technicien que la plage est libérée
                                    if rv_info and rv_info.get('technicien') and rv_info['technicien'] in GAZELLE_IDS:
                                        rv_date = rv_info.get('appointment_date')
                                        if rv_date:
                                            from datetime import date as date_class
                                            try:
                                                rv_date_obj = date_class.fromisoformat(str(rv_date)[:10])
                                                today = datetime.now(MONTREAL_TZ).date()
                                                days_until = (rv_date_obj - today).days
                                                # Notifier seulement si le RV était dans les 7 prochains jours
                                                if 0 <= days_until <= 7:
                                                    self._queue_late_assignment_alert(
                                                        appointment_external_id=ext_id,
                                                        technician_id=rv_info['technicien'],
                                                        appointment_date=str(rv_date)[:10],
                                                        appointment_time=rv_info.get('appointment_time'),
                                                        client_name=rv_info.get('title', ''),
                                                        location=rv_info.get('location', ''),
                                                        change_type='cancelled'
                                                    )
                                            except:
                                                pass
                                else:
                                    print(f"      ⚠️  Erreur marquage {ext_id}: {patch_response.status_code}")

                            print(f"   ✅ {cancelled_count}/{len(ids_to_cancel)} rendez-vous marqués CANCELLED")
                    else:
                        print(f"   ✅ Aucun rendez-vous obsolète détecté")
                else:
                    print(f"   ⚠️  Erreur récupération RV Supabase: {response.status_code}")

            except Exception as e:
                print(f"   ⚠️  Erreur lors du nettoyage: {e}")
                # Ne pas faire échouer toute la synchro pour ça

            # Marquer l'import historique comme terminé si c'était un import complet
            if not start_date_override and (force_historical or not historical_done):
                try:
                    print("\n💾 Marquage de l'import historique comme terminé...")
                    url = f"{self.storage.api_url}/system_settings?on_conflict=key"
                    headers = self.storage._get_headers()
                    headers["Prefer"] = "resolution=merge-duplicates"

                    response = requests.post(url, headers=headers, json={
                        'key': 'appointments_historical_import_done',
                        'value': 'true'
                    })

                    if response.status_code in [200, 201]:
                        print("✅ Marqueur 'appointments_historical_import_done' enregistré")
                        print("   → Les prochains syncs seront incrémentaux (7 derniers jours)")
                    else:
                        print(f"⚠️  Erreur lors de l'enregistrement du marqueur: {response.status_code}")
                except Exception as e:
                    print(f"⚠️  Impossible d'enregistrer le marqueur: {e}")

            return self.stats['appointments']['synced']

        except Exception as e:
            print(f"❌ Erreur lors de la synchronisation des rendez-vous: {e}")
            raise

    def sync_timeline_entries(self) -> int:
        """
        Synchronise les timeline entries depuis Gazelle vers Supabase (FENÊTRE GLISSANTE 30 JOURS).

        STRATÉGIE ROBUSTE (2026-02-12):
        - Fenêtre glissante de 30 jours (au lieu de 7) pour résilience
        - Clé unique: external_id (on_conflict) pour éviter doublons
        - Résiste aux pannes serveur, vacances, interruptions de sync
        - Performance: ~1-2 minutes (acceptable pour la sécurité des données)

        POURQUOI 30 JOURS (changé de 7):
        - Résilience: Si sync interrompue pendant vacances, on rattrape tout
        - Sécurité: Les SERVICE complétés ne tombent plus dans le vide
        - UPSERT: Pas de doublons même avec fenêtre plus large
        - Leçon apprise: Bug du 21 décembre causé par fenêtre trop courte

        Returns:
            Nombre d'entrées synchronisées
        """
        print(">>> Connexion à Gazelle lancée...")
        print("\n📖 Synchronisation timeline (fenêtre glissante 30 jours)...")

        try:
            from datetime import datetime, timedelta
            from core.timezone_utils import UTC_TZ

            # ═══════════════════════════════════════════════════════════════
            # VERROU SÉCURITÉ #4: Fenêtre élargie à 30 jours
            # Évite les trous de mémoire si sync interrompue (vacances, panne)
            # ═══════════════════════════════════════════════════════════════
            TIMELINE_SYNC_DAYS = 30  # Était 7, maintenant 30 pour résilience

            now = datetime.now(UTC_TZ)
            cutoff_date = now - timedelta(days=TIMELINE_SYNC_DAYS)

            # IMPORTANT: Convertir la date Montreal → UTC pour le filtre API
            cutoff_iso_utc = format_for_gazelle_filter(cutoff_date)

            print(f"📅 Fenêtre de synchronisation: {TIMELINE_SYNC_DAYS} derniers jours (résilience)")
            print(f"   📍 Cutoff: {cutoff_date.strftime('%Y-%m-%d')} UTC → {cutoff_iso_utc} UTC")
            print(f"   ⚡ Performance: ~1-2 minutes (sécurité > vitesse)")

            # Utiliser le filtre API pour récupérer les N derniers jours
            # Fenêtre élargie à 30j pour ne jamais perdre de SERVICE complétés
            api_entries = self.api_client.get_timeline_entries(
                since_date=cutoff_iso_utc,
                limit=None
            )

            if not api_entries:
                print(f"✅ Aucune timeline entry récente ({TIMELINE_SYNC_DAYS} derniers jours)")
                return 0

            print(f"📥 {len(api_entries)} timeline entries reçues ({TIMELINE_SYNC_DAYS} derniers jours)")

            synced_count = 0
            stopped_by_age = False

            for entry_data in api_entries:
                try:
                    # Parser occurredAt (CoreDateTime) pour validation et stockage
                    occurred_at_raw = entry_data.get('occurredAt')
                    occurred_at_utc = None

                    if occurred_at_raw:
                        try:
                            # Parser le CoreDateTime de Gazelle
                            dt_parsed = parse_gazelle_datetime(occurred_at_raw)
                            if dt_parsed:
                                # Formater pour Supabase (UTC avec 'Z')
                                occurred_at_utc = format_for_supabase(dt_parsed)

                                # Vérifier age (cutoff dynamique basé sur TIMELINE_SYNC_DAYS)
                                # cutoff_date est défini plus haut avec la fenêtre de 30 jours
                                if dt_parsed < cutoff_date:
                                    # SKIP cette entrée (plus vieille que la fenêtre)
                                    continue
                        except Exception as e:
                            print(f"⚠️  Erreur parsing date '{occurred_at_raw}': {e}")

                    external_id = entry_data.get('id')

                    # Client
                    client_obj = entry_data.get('client', {})
                    client_id = client_obj.get('id') if client_obj else None

                    # Piano
                    piano_obj = entry_data.get('piano', {})
                    piano_id = piano_obj.get('id') if piano_obj else None

                    # Invoice et Estimate
                    invoice_obj = entry_data.get('invoice', {})
                    invoice_id = invoice_obj.get('id') if invoice_obj else None

                    estimate_obj = entry_data.get('estimate', {})
                    estimate_id = estimate_obj.get('id') if estimate_obj else None

                    # User (technicien)
                    user_obj = entry_data.get('user', {})
                    user_id = user_obj.get('id') if user_obj else None

                    # Données de l'entrée
                    entry_type = entry_data.get('type', 'UNKNOWN')

                    # ═══════════════════════════════════════════════════════════════
                    # VERROU SÉCURITÉ #1: Mapping robuste multi-champs
                    # Pour les entrées SERVICE, les données peuvent être dans plusieurs champs
                    # On extrait TOUT pour ne rien perdre
                    # ═══════════════════════════════════════════════════════════════
                    title = entry_data.get('summary', '') or ''

                    # Collecter TOUS les champs textuels possibles pour description
                    description_parts = []
                    for field_name in ['comment', 'notes', 'workPerformed', 'description', 'details']:
                        field_value = entry_data.get(field_name, '')
                        if field_value and field_value.strip():
                            description_parts.append(field_value.strip())

                    # Pour les SERVICE, ajouter aussi les tags s'ils existent
                    if entry_type == 'SERVICE':
                        tags = entry_data.get('tags', [])
                        if tags and isinstance(tags, list):
                            tags_str = ', '.join(str(t) for t in tags if t)
                            if tags_str:
                                description_parts.append(f"[Tags: {tags_str}]")

                    details = ' | '.join(description_parts) if description_parts else ''

                    # ═══════════════════════════════════════════════════════════════
                    # VERROU SÉCURITÉ #2: Ne JAMAIS écraser avec des valeurs vides
                    # Si le nouveau contenu est vide, on ne l'inclut pas dans l'UPSERT
                    # Cela préserve les données existantes en base
                    # ═══════════════════════════════════════════════════════════════
                    timeline_record = {
                        'external_id': external_id,
                        'client_id': client_id,
                        'piano_id': piano_id,
                        'invoice_id': invoice_id,
                        'estimate_id': estimate_id,
                        'user_id': user_id,
                        'occurred_at': occurred_at_utc,  # CoreDateTime UTC avec 'Z'
                        'entry_type': entry_type,
                    }

                    # Ajouter title SEULEMENT si non-vide (protection écrasement)
                    if title and title.strip():
                        timeline_record['title'] = title.strip()

                    # Ajouter description SEULEMENT si non-vide (protection écrasement)
                    if details and details.strip():
                        timeline_record['description'] = details.strip()

                    # UPSERT avec on_conflict sur external_id (clé unique Gazelle)
                    # IMPORTANT: Garantit aucun doublon, même si sync multiple fois
                    url = f"{self.storage.api_url}/gazelle_timeline_entries?on_conflict=external_id"
                    headers = self.storage._get_headers()
                    headers["Prefer"] = "resolution=merge-duplicates"

                    response = requests.post(url, headers=headers, json=timeline_record)

                    if response.status_code in [200, 201]:
                        self.stats['timeline']['synced'] += 1
                        synced_count += 1
                    elif response.status_code == 409:
                        # 409 = Déjà existant, mise à jour réussie avec UPSERT
                        self.stats['timeline']['synced'] += 1
                        synced_count += 1
                    else:
                        print(f"❌ Erreur UPSERT timeline {external_id}: {response.status_code}")
                        print(f"   Response: {response.text[:200]}")
                        self.stats['timeline']['errors'] += 1

                except Exception as e:
                    print(f"❌ Erreur timeline entry {entry_data.get('id', 'unknown')}: {e}")
                    self.stats['timeline']['errors'] += 1
                    continue

            # Affichage final
            if stopped_by_age:
                print(f"✅ {synced_count} timeline entries synchronisées (fenêtre {TIMELINE_SYNC_DAYS} jours)")
            else:
                print(f"✅ {synced_count} timeline entries synchronisées (toutes < {TIMELINE_SYNC_DAYS} jours)")

            return synced_count

        except Exception as e:
            print(f"❌ Erreur lors de la synchronisation des timeline entries: {e}")
            raise

    def sync_timeline(self) -> int:
        """
        Alias pour sync_timeline_entries() pour compatibilité avec le scheduler.
        v6: Enrichit aussi avec PrivatePianoMeasurement après la sync.

        Returns:
            Nombre d'entrées synchronisées
        """
        count = self.sync_timeline_entries()
        # Enrichir avec PrivatePianoMeasurement après la sync
        self._enrich_timeline_with_measurements()
        return count
    
    def _enrich_timeline_with_measurements(self):
        """
        v6: Enrichit les timeline entries avec les mesures de PrivatePianoMeasurement.
        
        Stratégie:
        1. Pour chaque piano récemment synchronisé, interroger allPianoMeasurements
        2. Si une mesure existe dans PrivatePianoMeasurement, elle est prioritaire
        3. Sinon, on garde l'extraction du texte (déjà dans metadata)
        4. Met à jour metadata avec les mesures structurées
        """
        print("\n🌡️  Enrichissement avec PrivatePianoMeasurement (v6)...")
        
        try:
            from datetime import datetime, timedelta
            from supabase import create_client
            import json
            
            # Récupérer les timeline entries récentes (30 jours) avec piano_id
            # Aligné avec TIMELINE_SYNC_DAYS pour cohérence
            from core.timezone_utils import UTC_TZ
            cutoff_date = datetime.now(UTC_TZ) - timedelta(days=30)
            cutoff_iso = cutoff_date.isoformat()
            
            supabase = create_client(self.storage.supabase_url, self.storage.supabase_key)
            
            # Récupérer les timeline entries récentes avec piano_id
            result = supabase.table('gazelle_timeline_entries')\
                .select('id, piano_id, occurred_at, metadata')\
                .not_.is_('piano_id', 'null')\
                .gte('occurred_at', cutoff_iso)\
                .execute()
            
            if not result.data:
                print("   ✅ Aucune timeline entry récente avec piano_id")
                return
            
            print(f"   📊 {len(result.data)} timeline entries à enrichir")
            
            # Grouper par piano_id pour optimiser les requêtes
            pianos_to_check = set()
            for entry in result.data:
                if entry.get('piano_id'):
                    pianos_to_check.add(entry['piano_id'])
            
            print(f"   🎹 {len(pianos_to_check)} pianos uniques à vérifier")
            
            # Requête GraphQL pour récupérer les mesures
            query = """
            query($pianoId: ID!) {
                piano(id: $pianoId) {
                    id
                    allPianoMeasurements(first: 10, orderBy: CREATED_AT_DESC) {
                        nodes {
                            id
                            createdAt
                            takenOn
                            temperature
                            humidity
                            notes
                        }
                    }
                }
            }
            """
            
            enriched_count = 0
            
            for piano_id in list(pianos_to_check)[:50]:  # Limiter à 50 pour performance
                try:
                    variables = {"pianoId": piano_id}
                    result_gql = self.api_client._execute_query(query, variables)
                    
                    piano_data = result_gql.get('data', {}).get('piano', {})
                    measurements = piano_data.get('allPianoMeasurements', {}).get('nodes', [])
                    
                    if not measurements:
                        continue
                    
                    # Pour chaque timeline entry de ce piano, chercher une mesure correspondante
                    for entry in result.data:
                        if entry.get('piano_id') != piano_id:
                            continue
                        
                        entry_date = entry.get('occurred_at')
                        if not entry_date:
                            continue
                        
                        # Chercher une mesure proche de la date de l'entrée (±1 jour)
                        try:
                            entry_dt_str = entry_date.replace('Z', '+00:00') if entry_date.endswith('Z') else entry_date
                            entry_dt = datetime.fromisoformat(entry_dt_str)
                            # S'assurer que entry_dt est timezone-aware (UTC)
                            if entry_dt.tzinfo is None:
                                from core.timezone_utils import UTC_TZ
                                entry_dt = entry_dt.replace(tzinfo=UTC_TZ)
                            else:
                                entry_dt = entry_dt.astimezone(UTC_TZ)
                        except:
                            continue
                        
                        best_measurement = None
                        min_diff = timedelta(days=2)
                        
                        for measurement in measurements:
                            taken_on = measurement.get('takenOn') or measurement.get('createdAt')
                            if not taken_on:
                                continue
                            
                            try:
                                measure_dt_str = taken_on.replace('Z', '+00:00') if taken_on.endswith('Z') else taken_on
                                measure_dt = datetime.fromisoformat(measure_dt_str)
                                # S'assurer que measure_dt est timezone-aware (UTC)
                                if measure_dt.tzinfo is None:
                                    from core.timezone_utils import UTC_TZ
                                    measure_dt = measure_dt.replace(tzinfo=UTC_TZ)
                                else:
                                    measure_dt = measure_dt.astimezone(UTC_TZ)
                                diff = abs(entry_dt - measure_dt)
                                if diff < min_diff:
                                    min_diff = diff
                                    best_measurement = measurement
                            except:
                                continue
                        
                        # Si mesure trouvée, mettre à jour metadata
                        if best_measurement:
                            current_metadata = entry.get('metadata') or {}
                            if isinstance(current_metadata, str):
                                try:
                                    current_metadata = json.loads(current_metadata)
                                except:
                                    current_metadata = {}
                            
                            # Priorité: mesure de PrivatePianoMeasurement
                            current_metadata['measurements'] = {
                                'temperature': best_measurement.get('temperature'),
                                'humidity': best_measurement.get('humidity'),
                                'source': 'PrivatePianoMeasurement',
                                'measurement_id': best_measurement.get('id'),
                                'taken_on': best_measurement.get('takenOn')
                            }
                            
                            # Mettre à jour dans Supabase
                            update_url = f"{self.storage.api_url}/gazelle_timeline_entries?id=eq.{entry['id']}"
                            update_headers = self.storage._get_headers()

                            update_resp = requests.patch(
                                update_url,
                                headers=update_headers,
                                json={'metadata': current_metadata}
                            )
                            
                            if update_resp.status_code in [200, 204]:
                                enriched_count += 1
                
                except Exception as e:
                    if enriched_count == 0:  # Afficher seulement la première erreur
                        print(f"   ⚠️  Erreur enrichissement piano {piano_id}: {e}")
                    continue
            
            if enriched_count > 0:
                print(f"   ✅ {enriched_count} timeline entries enrichies avec PrivatePianoMeasurement")
            else:
                print(f"   ℹ️  Aucune mesure PrivatePianoMeasurement trouvée pour les entrées récentes")
        
        except Exception as e:
            print(f"   ⚠️  Erreur enrichissement: {e}")
            import traceback
            traceback.print_exc()

    def sync_users(self, force: bool = False) -> int:
        """
        Synchronise les techniciens (users) depuis l'API Gazelle vers Supabase.

        Args:
            force: Si True, force la sync même si les users existent déjà.
                   Si False (défaut), skip si la table users n'est pas vide.

        Returns:
            Nombre de techniciens synchronisés
        """
        print("\n👥 Synchronisation des techniciens (users)...")

        # Vérifier si les users existent déjà (sauf si force=True)
        if not force:
            try:
                url = f"{self.storage.api_url}/users?select=id&limit=1"
                response = requests.get(url, headers=self.storage._get_headers())
                if response.status_code == 200:
                    existing_users = response.json()
                    if existing_users:
                        print("⏭️  Users déjà synchronisés (table non vide) - skip")
                        print("   💡 Utilise sync_users(force=True) pour forcer la re-sync")
                        return 0
            except Exception as e:
                print(f"⚠️  Impossible de vérifier users existants: {e}")
                # Continue la sync en cas d'erreur

        try:
            # Récupérer les users depuis l'API Gazelle
            users_data = self.api_client.get_users()

            if not users_data:
                print("⚠️  Aucun utilisateur récupéré depuis l'API")
                return 0

            print(f"📥 {len(users_data)} utilisateurs récupérés depuis l'API")

            synced_count = 0

            for user in users_data:
                try:
                    user_id = user.get('id')
                    if not user_id:
                        continue

                    # Préparer les données pour Supabase
                    user_record = {
                        'id': user_id,  # Gazelle ID (ex: usr_ofYggsCDt2JAVeNP)
                        'external_id': user.get('externalId'),
                        'first_name': user.get('firstName'),
                        'last_name': user.get('lastName'),
                        'email': user.get('email'),
                        'phone': user.get('phone'),
                        'role': user.get('role'),
                        'updated_at': datetime.now().isoformat()
                    }

                    # UPSERT via REST API avec on_conflict
                    url = f"{self.storage.api_url}/users?on_conflict=gazelle_user_id"
                    headers = self.storage._get_headers()
                    headers["Prefer"] = "resolution=merge-duplicates"

                    response = requests.post(url, headers=headers, json=user_record)

                    if response.status_code in [200, 201]:
                        synced_count += 1
                    else:
                        print(f"⚠️  Erreur sync user {user_id}: HTTP {response.status_code} - {response.text[:200]}")

                except Exception as e:
                    print(f"❌ Erreur sync user {user.get('id', 'unknown')}: {e}")
                    continue

            print(f"✅ {synced_count} techniciens synchronisés")
            return synced_count

        except Exception as e:
            print(f"❌ Erreur lors de la synchronisation des users: {e}")
            raise

    def sync_all(self) -> Dict[str, Any]:
        """
        Synchronise toutes les tables Gazelle vers Supabase.

        Returns:
            Dictionnaire de statistiques
        """
        print("=" * 70)
        print("🔄 SYNCHRONISATION GAZELLE → SUPABASE")
        print("=" * 70)
        print(f"📅 Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 70)

        start_time = datetime.now()

        try:
            # Synchroniser dans l'ordre de dépendance
            # 0. Users/Techniciens (requis pour timeline entries FK)
            self.sync_users()

            # 1. Clients (requis pour pianos, contacts, etc.)
            self.sync_clients()

            # 2. Contacts (personnes associées aux clients)
            self.sync_contacts()

            # 3. Pianos (dépend de clients)
            self.sync_pianos()

            # 4. Appointments (utilise maintenant allEventsBatched de V4)
            self.sync_appointments()

            # 5. Timeline entries (notes techniques)
            self.sync_timeline_entries()

            # Résumé
            duration = (datetime.now() - start_time).total_seconds()

            print("\n" + "=" * 70)
            print("✅ SYNCHRONISATION TERMINÉE")
            print("=" * 70)
            print(f"⏱️  Durée: {duration:.2f}s")
            print("\n📊 Résumé:")
            print(f"   • Clients:      {self.stats['clients']['synced']:4d} synchronisés, {self.stats['clients']['errors']:2d} erreurs")
            print(f"   • Contacts:     {self.stats['contacts']['synced']:4d} synchronisés, {self.stats['contacts']['errors']:2d} erreurs")
            print(f"   • Pianos:       {self.stats['pianos']['synced']:4d} synchronisés, {self.stats['pianos']['errors']:2d} erreurs")
            print(f"   • RV:           {self.stats['appointments']['synced']:4d} synchronisés, {self.stats['appointments']['errors']:2d} erreurs")
            print(f"   • Timeline:     {self.stats['timeline']['synced']:4d} synchronisés, {self.stats['timeline']['errors']:2d} erreurs")
            print("=" * 70)

            # Sauvegarder timestamp de fin de sync (mode incrémental)
            if self.incremental_mode:
                self._save_last_sync_date(datetime.now())

            # Pré-charger le cache des briefings (aujourd'hui + demain)
            try:
                from modules.briefing.briefing_cache import warm_briefing_cache
                print("\n🔥 Pré-chargement des briefings...")
                warm_briefing_cache()
            except Exception as cache_err:
                print(f"⚠️ Cache briefings non mis à jour: {cache_err}")

            return {
                'success': True,
                'duration_seconds': duration,
                'stats': self.stats,
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            print(f"\n❌ ERREUR FATALE: {e}")
            import traceback
            traceback.print_exc()

            return {
                'success': False,
                'error': str(e),
                'stats': self.stats,
                'timestamp': datetime.now().isoformat()
            }


def main():
    """Point d'entrée principal du script."""
    import time
    import sys
    import os
    import json
    start_time = time.time()
    
    print("\n" + "="*70)
    print("🔍 VÉRIFICATION VARIABLES D'ENVIRONNEMENT SUPABASE")
    print("="*70)
    
    # Vérifier les variables d'environnement Supabase
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    supabase_key_alt = os.getenv('SUPABASE_KEY')
    
    print(f"📋 SUPABASE_URL: {'✅ Défini' if supabase_url else '❌ MANQUANT'}")
    if supabase_url:
        print(f"   Valeur: {supabase_url[:50]}...")
    
    print(f"📋 SUPABASE_SERVICE_ROLE_KEY: {'✅ Défini' if supabase_key else '❌ MANQUANT'}")
    if supabase_key:
        print(f"   Longueur: {len(supabase_key)} caractères")
        print(f"   Préfixe: {supabase_key[:10]}...")
    
    if not supabase_key and supabase_key_alt:
        print(f"📋 SUPABASE_KEY (fallback): ✅ Défini ({len(supabase_key_alt)} caractères)")
    
    if not supabase_url or (not supabase_key and not supabase_key_alt):
        print("\n❌ ERREUR: Variables d'environnement Supabase manquantes!")
        print("   Le script ne pourra pas écrire dans sync_logs")
        sys.exit(1)
    
    print("="*70 + "\n")
    
    # Initialiser le logger
    logger = SyncLogger()
    
    # Vérifier que le logger est bien initialisé
    print("🔍 VÉRIFICATION SYNC LOGGER")
    print("="*70)
    if logger.client is None:
        print("❌ SyncLogger.client est None - impossible d'écrire dans sync_logs")
        print("   Vérifiez que SUPABASE_URL et SUPABASE_SERVICE_ROLE_KEY sont corrects")
    else:
        print("✅ SyncLogger.client initialisé correctement")
        print(f"   URL: {logger.supabase_url}")
        print(f"   Key préfixe: {logger.supabase_key[:10] if logger.supabase_key else 'N/A'}...")
    print("="*70 + "\n")

    # Mode incrémental par défaut (--full pour mode complet)
    incremental_mode = True
    if len(sys.argv) > 1 and sys.argv[1] == '--full':
        incremental_mode = False
        print("⚠️  Mode COMPLET activé (--full)")

    result = None
    sync_manager = None
    
    try:
        sync_manager = GazelleToSupabaseSync(incremental_mode=incremental_mode)
        result = sync_manager.sync_all()

        # Logger le résultat dans sync_logs
        execution_time = time.time() - start_time

        print("\n" + "="*70)
        print("📝 PRÉPARATION ÉCRITURE DANS sync_logs")
        print("="*70)
        
        # Construire le dictionnaire des tables mises à jour (même si échec partiel)
        tables_updated = {}
        if result and 'stats' in result:
            tables_updated = {
                'users': result['stats'].get('users', {}).get('synced', 0) if 'users' in result['stats'] else 0,
                'clients': result['stats'].get('clients', {}).get('synced', 0),
                'contacts': result['stats'].get('contacts', {}).get('synced', 0),
                'pianos': result['stats'].get('pianos', {}).get('synced', 0),
                'appointments': result['stats'].get('appointments', {}).get('synced', 0),
                'timeline': result['stats'].get('timeline', {}).get('synced', 0)
            }
        else:
            # Si result n'a pas de stats, utiliser les stats du sync_manager
            if sync_manager:
                tables_updated = {
                    'users': sync_manager.stats.get('users', {}).get('synced', 0) if 'users' in sync_manager.stats else 0,
                    'clients': sync_manager.stats.get('clients', {}).get('synced', 0),
                    'contacts': sync_manager.stats.get('contacts', {}).get('synced', 0),
                    'pianos': sync_manager.stats.get('pianos', {}).get('synced', 0),
                    'appointments': sync_manager.stats.get('appointments', {}).get('synced', 0),
                    'timeline': sync_manager.stats.get('timeline', {}).get('synced', 0)
                }
        
        print(f"📊 Tables mises à jour:")
        print(f"   users: {tables_updated.get('users', 0)}")
        print(f"   clients: {tables_updated.get('clients', 0)}")
        print(f"   contacts: {tables_updated.get('contacts', 0)}")
        print(f"   pianos: {tables_updated.get('pianos', 0)}")
        print(f"   appointments: {tables_updated.get('appointments', 0)}")
        print(f"   timeline: {tables_updated.get('timeline', 0)}")
        
        # Calculer les erreurs
        total_errors = 0
        if result and 'stats' in result:
            total_errors = sum(
                result['stats'][key].get('errors', 0)
                for key in ['clients', 'contacts', 'pianos', 'appointments', 'timeline']
                if key in result['stats']
            )
        elif sync_manager:
            total_errors = sum(
                sync_manager.stats[key].get('errors', 0)
                for key in ['clients', 'contacts', 'pianos', 'appointments', 'timeline']
                if key in sync_manager.stats
            )
        
        print(f"📊 Total erreurs: {total_errors}")
        
        # Déterminer le status
        if result and result.get('success'):
            status = 'success' if total_errors == 0 else 'warning'
        else:
            status = 'error'
        
        error_msg = None
        if total_errors > 0:
            error_msg = f"{total_errors} erreurs"
        if result and not result.get('success'):
            error_msg = result.get('error', 'Erreur inconnue')
        
        print(f"📊 Status: {status}")
        if error_msg:
            print(f"📊 Message d'erreur: {error_msg}")
        
        print(f"⏱️  Temps d'exécution: {execution_time:.2f} secondes")
        
        # Préparer les données pour le log
        log_data = {
            'script_name': 'GitHub_Full_Sync',
            'status': status,
            'tables_updated': tables_updated,
            'error_message': error_msg,
            'execution_time_seconds': round(execution_time, 2)
        }
        
        print(f"\n📝 Données à écrire dans sync_logs:")
        print(json.dumps(log_data, indent=2, default=str))
        
        print(f"\n🔍 Vérification finale SyncLogger:")
        print(f"   logger.client: {logger.client}")
        print(f"   logger.supabase_url: {logger.supabase_url}")
        print(f"   logger.supabase_key: {'✅ Défini' if logger.supabase_key else '❌ MANQUANT'}")
        
        print("\n" + "="*70)
        print("💾 TENTATIVE D'ÉCRITURE DANS sync_logs")
        print("="*70)
        
        # FORCER l'écriture même si sync partielle
        log_result = logger.log_sync(
            script_name='GitHub_Full_Sync',
            status=status,
            tables_updated=tables_updated,
            error_message=error_msg,
            execution_time_seconds=round(execution_time, 2)
        )
        
        print("\n" + "="*70)
        if log_result:
            print("✅ ÉCRITURE DANS sync_logs RÉUSSIE")
        else:
            print("❌ ÉCHEC ÉCRITURE DANS sync_logs")
            print("   Vérifiez les logs ci-dessus pour identifier le problème")
        print("="*70)
        
        # Exit code selon succès
        exit_code = 0 if result and result.get('success') else 1
        sys.exit(exit_code)

    except Exception as e:
        # Logger l'exception - FORCER l'écriture même en cas d'erreur
        execution_time = time.time() - start_time
        
        print("\n" + "="*70)
        print("❌ EXCEPTION CAPTURÉE - TENTATIVE LOG D'ERREUR")
        print("="*70)
        print(f"Erreur: {e}")
        import traceback
        error_traceback = traceback.format_exc()
        print(f"Traceback:\n{error_traceback}")
        
        # Préparer les stats même en cas d'erreur
        tables_updated = {}
        if sync_manager:
            tables_updated = {
                'users': sync_manager.stats.get('users', {}).get('synced', 0) if 'users' in sync_manager.stats else 0,
                'clients': sync_manager.stats.get('clients', {}).get('synced', 0),
                'contacts': sync_manager.stats.get('contacts', {}).get('synced', 0),
                'pianos': sync_manager.stats.get('pianos', {}).get('synced', 0),
                'appointments': sync_manager.stats.get('appointments', {}).get('synced', 0),
                'timeline': sync_manager.stats.get('timeline', {}).get('synced', 0)
            }
        
        print(f"\n📝 Données à écrire (erreur):")
        log_data_error = {
            'script_name': 'GitHub_Full_Sync',
            'status': 'error',
            'tables_updated': tables_updated,
            'error_message': f"{str(e)}\n\nTraceback:\n{error_traceback[:500]}",  # Limiter la taille
            'execution_time_seconds': round(execution_time, 2)
        }
        print(json.dumps(log_data_error, indent=2, default=str))
        
        print("\n💾 TENTATIVE D'ÉCRITURE DANS sync_logs (erreur)...")
        log_result = logger.log_sync(
            script_name='GitHub_Full_Sync',
            status='error',
            tables_updated=tables_updated,
            error_message=f"{str(e)}\n\nTraceback:\n{error_traceback[:500]}",
            execution_time_seconds=round(execution_time, 2)
        )
        
        if log_result:
            print("✅ Log d'erreur écrit avec succès")
        else:
            print("❌ ÉCHEC ÉCRITURE LOG D'ERREUR")
        
        print("="*70)

        print(f"\n❌ Erreur fatale: {e}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
