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
from core.supabase_storage import SupabaseStorage


class GazelleToSupabaseSync:
    """Synchronise les données Gazelle vers Supabase."""

    def __init__(self):
        """Initialise le gestionnaire de synchronisation."""
        print("🔧 Initialisation du service de synchronisation...")

        try:
            self.api_client = GazelleAPIClient()
            print("✅ Client API Gazelle initialisé")
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

    def sync_clients(self) -> int:
        """
        Synchronise les clients depuis l'API vers Supabase.

        Returns:
            Nombre de clients synchronisés
        """
        print("\n📋 Synchronisation des clients...")

        try:
            # Récupérer clients depuis API Gazelle
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

                    # Contact par défaut
                    default_contact = client_data.get('defaultContact', {})

                    # Si CompanyName vide, utiliser nom du contact
                    if not company_name and default_contact:
                        first_name_raw = default_contact.get('firstName')
                        last_name_raw = default_contact.get('lastName')
                        first_name = first_name_raw.strip() if first_name_raw else ''
                        last_name = last_name_raw.strip() if last_name_raw else ''
                        company_name = f"{first_name} {last_name}".strip()

                    if not company_name:
                        print(f"⚠️  Client {external_id} ignoré (nom vide)")
                        self.stats['clients']['errors'] += 1
                        continue

                    # Email, téléphone, adresse du contact
                    email = None
                    phone = None
                    address = None
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
                            # Construire l'adresse complète depuis street1/street2
                            street1 = default_location.get('street1', '')
                            street2 = default_location.get('street2', '')
                            if street1 and street2:
                                address = f"{street1}, {street2}"
                            elif street1:
                                address = street1
                            elif street2:
                                address = street2

                            city = default_location.get('municipality')
                            postal_code = default_location.get('postalCode')

                    # Préparer données pour Supabase
                    client_record = {
                        'external_id': external_id,
                        'company_name': company_name,
                        'status': status,
                        'tags': tags,
                        'email': email,
                        'phone': phone,
                        'address': address,
                        'city': city,
                        'postal_code': postal_code,
                        'created_at': client_data.get('createdAt'),
                        'updated_at': datetime.now().isoformat()
                    }

                    # UPSERT dans Supabase (via REST API)
                    url = f"{self.storage.api_url}/gazelle_clients"
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

                    # UPSERT dans Supabase via REST API
                    url = f"{self.storage.api_url}/gazelle_contacts"
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

        Returns:
            Nombre de pianos synchronisés
        """
        print("\n🎹 Synchronisation des pianos...")

        try:
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

                    # UPSERT
                    url = f"{self.storage.api_url}/gazelle_pianos"
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

        # Déterminer la date de début
        if start_date_override:
            # Override manuel
            effective_start_date = start_date_override
            print(f"🎯 Mode manuel: import depuis {effective_start_date}")
        elif force_historical or not historical_done:
            # Premier import: tout depuis 2017
            effective_start_date = '2017-01-01'
            print(f"🏛️  IMPORT HISTORIQUE COMPLET depuis {effective_start_date}")
            print("   (Cette opération peut prendre plusieurs minutes...)")
        else:
            # Sync incrémental: seulement les 7 derniers jours
            effective_start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
            print(f"🔄 Sync incrémental: derniers 7 jours (depuis {effective_start_date})")

        try:
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

                    # Date et heure depuis start
                    start_time = appt_data.get('start')
                    appointment_date = None
                    appointment_time = None

                    if start_time:
                        try:
                            from datetime import datetime as dt

                            # CORRECT: Gazelle retourne du VRAI UTC (le 'Z' est fiable)
                            # L'API affiche 09:15 à l'écran (Toronto) et retourne 14:15Z dans l'API (UTC)
                            # On stocke tel quel, sans double conversion.
                            dt_utc = dt.fromisoformat(start_time)

                            appointment_date = dt_utc.date().isoformat()
                            appointment_time = dt_utc.time().isoformat()
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
                        'duration_minutes': duration_minutes,
                        'status': status,
                        'technicien': technicien,
                        'location': location,
                        'notes': notes,
                        'created_at': start_time,  # Utiliser start comme created_at
                        'updated_at': datetime.now().isoformat()
                    }

                    # UPSERT
                    url = f"{self.storage.api_url}/gazelle_appointments"
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

            # Marquer l'import historique comme terminé si c'était un import complet
            if not start_date_override and (force_historical or not historical_done):
                try:
                    print("\n💾 Marquage de l'import historique comme terminé...")
                    url = f"{self.storage.api_url}/system_settings"
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
        Synchronise les timeline entries depuis Gazelle vers Supabase (FENÊTRE 15 JOURS).

        Stratégie simplifiée:
        1. Récupère les entrées de l'API (triées du plus récent au plus ancien)
        2. Arrête dès qu'une entrée a plus de 15 jours
        3. Utilise UPSERT pour mettre à jour les entrées existantes

        Returns:
            Nombre d'entrées synchronisées
        """
        print("\n📖 Synchronisation timeline (fenêtre glissante 30 jours)...")

        try:
            from datetime import datetime, timedelta
            from zoneinfo import ZoneInfo

            # Date de cutoff: maintenant - 30 jours (étendu pour capturer services de fin décembre)
            cutoff_date = datetime.now() - timedelta(days=30)
            cutoff_iso = cutoff_date.isoformat()

            print(f"📅 Fenêtre de synchronisation: entrées depuis {cutoff_iso}")

            # Utiliser le filtre API pour récupérer SEULEMENT les 30 derniers jours
            # Cela évite de télécharger 100,000+ entrées inutiles à chaque sync
            api_entries = self.api_client.get_timeline_entries(
                since_date=cutoff_iso,
                limit=None
            )

            if not api_entries:
                print("⚠️  Aucune timeline entry récupérée depuis l'API")
                return 0

            print(f"📥 {len(api_entries)} timeline entries reçues de l'API")

            synced_count = 0
            stopped_by_age = False

            for entry_data in api_entries:
                try:
                    # CRITICAL: Vérifier si l'entrée est trop ancienne (>30 jours)
                    occurred_at = entry_data.get('occurredAt')

                    if occurred_at:
                        # Parser la date (format ISO)
                        try:
                            entry_date = datetime.fromisoformat(occurred_at.replace('Z', '+00:00'))
                            # Rendre aware si naive
                            if entry_date.tzinfo is None:
                                entry_date = entry_date.replace(tzinfo=ZoneInfo('UTC'))

                            # Comparer avec cutoff (rendre cutoff aware aussi)
                            cutoff_aware = cutoff_date.replace(tzinfo=ZoneInfo('UTC'))

                            if entry_date < cutoff_aware:
                                # SKIP cette entrée (trop vieille), mais continuer la sync
                                continue
                        except Exception as e:
                            print(f"⚠️  Erreur parsing date '{occurred_at}': {e}")

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
                    # IMPORTANT: GraphQL retourne summary/comment, pas title/details
                    title = entry_data.get('summary', '')
                    details = entry_data.get('comment', '')

                    # DEBUG: Logger les SERVICE_ENTRY_MANUAL du 26-28 déc
                    if entry_type == 'SERVICE_ENTRY_MANUAL' and occurred_at and occurred_at >= '2025-12-26':
                        print(f"🔍 SERVICE_ENTRY_MANUAL: {occurred_at} | {(details or title)[:50]}")

                    timeline_record = {
                        'external_id': external_id,
                        'client_id': client_id,
                        'piano_id': piano_id,
                        'invoice_id': invoice_id,
                        'estimate_id': estimate_id,
                        'user_id': user_id,
                        'occurred_at': occurred_at,
                        'entry_type': entry_type,
                        'title': title,
                        'description': details  # La colonne s'appelle 'description' pas 'details'
                        # Note: createdAt/updatedAt n'existent pas dans PrivateTimelineEntry
                    }

                    # UPSERT
                    url = f"{self.storage.api_url}/gazelle_timeline_entries"
                    headers = self.storage._get_headers()
                    headers["Prefer"] = "resolution=merge-duplicates"

                    response = requests.post(url, headers=headers, json=timeline_record)

                    # DEBUG: Logger réponse complète pour services du 26-28 déc
                    if entry_type == 'SERVICE_ENTRY_MANUAL' and occurred_at and occurred_at >= '2025-12-26':
                        print(f"  📤 POST Response: {response.status_code}")
                        print(f"     Body: {response.text[:300]}")

                    if response.status_code in [200, 201]:
                        self.stats['timeline']['synced'] += 1
                        synced_count += 1
                    elif response.status_code == 409:
                        # 409 peut être un succès (merge) OU une erreur - vérifier la réponse
                        print(f"⚠️  409 Conflict pour {external_id}: {response.text[:200]}")
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
                print(f"✅ {synced_count} timeline entries synchronisées (fenêtre 15 jours)")
            else:
                print(f"✅ {synced_count} timeline entries synchronisées (toutes < 15 jours)")

            return synced_count

        except Exception as e:
            print(f"❌ Erreur lors de la synchronisation des timeline entries: {e}")
            raise

    def sync_users(self) -> int:
        """
        Synchronise les techniciens (users) depuis l'API Gazelle vers Supabase.

        Returns:
            Nombre de techniciens synchronisés
        """
        print("\n👥 Synchronisation des techniciens (users)...")

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

                    # UPSERT via REST API
                    url = f"{self.storage.api_url}/users"
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
    try:
        sync_manager = GazelleToSupabaseSync()
        result = sync_manager.sync_all()

        # Exit code selon succès
        exit_code = 0 if result['success'] else 1
        sys.exit(exit_code)

    except Exception as e:
        print(f"\n❌ Erreur fatale: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
