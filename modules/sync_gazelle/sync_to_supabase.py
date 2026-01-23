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

                    # Préparer données pour Supabase
                    client_record = {
                        'external_id': external_id,
                        'company_name': company_name,
                        'first_name': first_name if first_name else None,  # 🆕 Nouveau champ
                        'last_name': last_name if last_name else None,     # 🆕 Nouveau champ
                        'status': status,
                        'email': email,
                        'phone': phone,
                        # Note: 'address' n'existe pas dans gazelle_clients, seulement city et postal_code
                        'city': city,
                        'postal_code': postal_code,
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

                    import requests
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

                    import requests
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
                        'created_at': start_time_utc,  # CoreDateTime UTC avec 'Z'
                        'updated_at': format_for_supabase(datetime.now())
                    }

                    # UPSERT avec on_conflict
                    url = f"{self.storage.api_url}/gazelle_appointments?on_conflict=external_id"
                    headers = self.storage._get_headers()
                    headers["Prefer"] = "resolution=merge-duplicates"

                    import requests
                    response = requests.post(url, headers=headers, json=appointment_record)

                    if response.status_code in [200, 201]:
                        self.stats['appointments']['synced'] += 1
                    elif response.status_code == 409:
                        # 409 = Conflict (déjà synchronisé, normal avec UPSERT)
                        self.stats['appointments']['synced'] += 1
                    else:
                        print(f"❌ Erreur UPSERT appointment {external_id}: {response.status_code} - {response.text}")
                        self.stats['appointments']['errors'] += 1

                except Exception as e:
                    print(f"❌ Erreur appointment {appt_data.get('id', 'unknown')}: {e}")
                    self.stats['appointments']['errors'] += 1

            print(f"✅ {self.stats['appointments']['synced']} rendez-vous synchronisés")

            # NETTOYAGE: Supprimer les rendez-vous qui n'existent plus dans Gazelle
            try:
                print("\n🧹 Nettoyage des rendez-vous supprimés/annulés dans Gazelle...")

                # 1. Récupérer tous les external_id depuis Gazelle (pour la période synchronisée)
                gazelle_ids = {appt.get('id') for appt in api_appointments if appt.get('id')}
                print(f"   📋 {len(gazelle_ids)} rendez-vous actifs dans Gazelle")

                # 2. Récupérer tous les external_id depuis Supabase pour la même période
                # (on ne supprime que les RV de la fenêtre synchronisée, pas tout l'historique)
                if start_date_override:
                    date_filter = start_date_override
                else:
                    date_filter = start_dt.strftime('%Y-%m-%d')

                url = f"{self.storage.api_url}/gazelle_appointments?appointment_date=gte.{date_filter}&select=external_id"
                response = requests.get(url, headers=self.storage._get_headers())

                if response.status_code == 200:
                    supabase_appointments = response.json()
                    supabase_ids = {appt['external_id'] for appt in supabase_appointments if appt.get('external_id')}
                    print(f"   📋 {len(supabase_ids)} rendez-vous dans Supabase (période synchronisée)")

                    # 3. Identifier les RV à supprimer (dans Supabase mais pas dans Gazelle)
                    ids_to_delete = supabase_ids - gazelle_ids

                    if ids_to_delete:
                        print(f"   🗑️  {len(ids_to_delete)} rendez-vous à supprimer (annulés/supprimés dans Gazelle)")

                        # 4. Supprimer les RV obsolètes
                        deleted_count = 0
                        for external_id in ids_to_delete:
                            delete_url = f"{self.storage.api_url}/gazelle_appointments?external_id=eq.{external_id}"
                            delete_response = requests.delete(delete_url, headers=self.storage._get_headers())

                            if delete_response.status_code in [200, 204]:
                                deleted_count += 1
                            else:
                                print(f"   ⚠️  Erreur suppression {external_id}: {delete_response.status_code}")

                        print(f"   ✅ {deleted_count}/{len(ids_to_delete)} rendez-vous supprimés de Supabase")
                    else:
                        print(f"   ✅ Aucun rendez-vous obsolète à supprimer")
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
        Synchronise les timeline entries depuis Gazelle vers Supabase (FENÊTRE GLISSANTE 7 JOURS).

        STRATÉGIE OPTIMISÉE (2026-01-11):
        - Fenêtre glissante de 7 jours uniquement (pas d'historique complet)
        - Clé unique: external_id (on_conflict) pour éviter doublons
        - Suffisant pour capturer notes de Margot et corrections récentes
        - Performance: <30 secondes vs 10 minutes pour historique complet

        POURQUOI 7 JOURS:
        - Base historique déjà dans Supabase
        - Notes récentes capturées rapidement
        - Pas de surcharge inutile
        - Corrections de la semaine incluses

        Returns:
            Nombre d'entrées synchronisées
        """
        print(">>> Connexion à Gazelle lancée...")
        print("\n📖 Synchronisation timeline (fenêtre glissante 7 jours)...")

        try:
            from datetime import datetime, timedelta
            from core.timezone_utils import UTC_TZ

            # Date de cutoff: 7 jours en arrière (fenêtre glissante)
            # IMPORTANT: Utiliser UTC pour garantir timezone-aware
            now = datetime.now(UTC_TZ)
            cutoff_date = now - timedelta(days=7)

            # IMPORTANT: Convertir la date Montreal → UTC pour le filtre API
            cutoff_iso_utc = format_for_gazelle_filter(cutoff_date)

            print(f"📅 Fenêtre de synchronisation: 7 derniers jours seulement")
            print(f"   📍 Cutoff: {cutoff_date.strftime('%Y-%m-%d')} UTC → {cutoff_iso_utc} UTC")
            print(f"   ⚡ Performance optimisée: ~30 secondes")

            # Utiliser le filtre API pour récupérer SEULEMENT les 7 derniers jours
            # Cela évite de télécharger 100,000+ entrées inutiles à chaque sync
            # RÈGLE: On a déjà l'historique complet, on rattrape juste la semaine
            api_entries = self.api_client.get_timeline_entries(
                since_date=cutoff_iso_utc,
                limit=None
            )

            if not api_entries:
                print("✅ Aucune timeline entry récente (7 derniers jours)")
                return 0

            print(f"📥 {len(api_entries)} timeline entries reçues (7 derniers jours)")

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

                                # Vérifier age (7 jours cutoff)
                                # cutoff_date est déjà aware (UTC) depuis la ligne 743
                                if dt_parsed < cutoff_date:
                                    # SKIP cette entrée (plus vieille que 7 jours)
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
                    # TODO: Confirmer avec NotebookLM les vrais noms de champs (description vs summary/comment)
                    title = entry_data.get('summary', '')
                    details = entry_data.get('comment', '')

                    timeline_record = {
                        'external_id': external_id,
                        'client_id': client_id,
                        'piano_id': piano_id,
                        'invoice_id': invoice_id,
                        'estimate_id': estimate_id,
                        'user_id': user_id,
                        'occurred_at': occurred_at_utc,  # CoreDateTime UTC avec 'Z'
                        'entry_type': entry_type,
                        'title': title,
                        'description': details  # Colonne 'description' en DB = champ 'comment' en API
                        # Note: createdAt/updatedAt n'existent pas dans PrivateTimelineEntry
                    }

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
                print(f"✅ {synced_count} timeline entries synchronisées (fenêtre 7 jours)")
            else:
                print(f"✅ {synced_count} timeline entries synchronisées (toutes < 7 jours)")

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
            
            # Récupérer les timeline entries récentes (7 jours) avec piano_id
            from core.timezone_utils import UTC_TZ
            cutoff_date = datetime.now(UTC_TZ) - timedelta(days=7)
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
                            
                            import requests
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
    start_time = time.time()
    logger = SyncLogger()

    # Mode incrémental par défaut (--full pour mode complet)
    incremental_mode = True
    if len(sys.argv) > 1 and sys.argv[1] == '--full':
        incremental_mode = False
        print("⚠️  Mode COMPLET activé (--full)")

    try:
        sync_manager = GazelleToSupabaseSync(incremental_mode=incremental_mode)
        result = sync_manager.sync_all()

        # Logger le résultat dans sync_logs
        execution_time = time.time() - start_time

        if result['success']:
            # Construire le dictionnaire des tables mises à jour
            tables_updated = {
                'users': result['stats'].get('users', {}).get('synced', 0),
                'clients': result['stats']['clients']['synced'],
                'contacts': result['stats']['contacts']['synced'],
                'pianos': result['stats']['pianos']['synced'],
                'appointments': result['stats']['appointments']['synced'],
                'timeline': result['stats']['timeline']['synced']
            }

            # Vérifier s'il y a des erreurs
            total_errors = sum(
                result['stats'][key]['errors']
                for key in ['clients', 'contacts', 'pianos', 'appointments', 'timeline']
                if key in result['stats']
            )

            status = 'success' if total_errors == 0 else 'warning'
            error_msg = f"{total_errors} erreurs" if total_errors > 0 else None

            logger.log_sync(
                script_name='GitHub_Full_Sync',
                status=status,
                tables_updated=tables_updated,
                error_message=error_msg,
                execution_time_seconds=round(execution_time, 2)
            )
        else:
            # Erreur complète
            logger.log_sync(
                script_name='GitHub_Full_Sync',
                status='error',
                error_message=result.get('error', 'Erreur inconnue'),
                execution_time_seconds=round(execution_time, 2)
            )

        # Exit code selon succès
        exit_code = 0 if result['success'] else 1
        sys.exit(exit_code)

    except Exception as e:
        # Logger l'exception
        execution_time = time.time() - start_time
        logger.log_sync(
            script_name='GitHub_Full_Sync',
            status='error',
            error_message=str(e),
            execution_time_seconds=round(execution_time, 2)
        )

        print(f"\n❌ Erreur fatale: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
