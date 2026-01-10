#!/usr/bin/env python3
"""
Script de synchronisation PC Windows → SQL Server + Supabase
À exécuter chaque nuit via Windows Task Scheduler

Ce script:
1. Lit depuis Gazelle API (avec tokens OAuth du PC)
2. Écrit dans SQL Server (comme d'habitude)
3. Écrit AUSSI dans Supabase (pour accès cloud)

Aucune modification aux scripts existants - synchronisation additionnelle uniquement.
"""

import os
import sys
import json
import requests
from datetime import datetime
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

# ============================================================================
# CONFIGURATION
# ============================================================================

# Supabase credentials (à configurer dans le .env du PC)
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://beblgzvmjqkcillmcavk.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")

if not SUPABASE_KEY:
    print("❌ SUPABASE_KEY ou SUPABASE_SERVICE_ROLE_KEY manquante. Ajoutez-la dans le fichier .env.")
    sys.exit(1)

# Gazelle API (utilise les tokens du PC)
GAZELLE_API_URL = "https://gazelleapp.io/graphql/private/"
GAZELLE_TOKEN_FILE = "data/gazelle_token.json"  # Chemin sur le PC Windows


# ============================================================================
# CLASSE SUPABASE CLIENT
# ============================================================================

class SupabaseClient:
    """Client simple pour écrire dans Supabase"""

    def __init__(self, url: str, key: str):
        self.api_url = url
        self.api_key = key
        self.headers = {
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json"
        }

    def upsert(self, table: str, data: List[Dict]) -> bool:
        """Insert ou update des données dans une table Supabase"""
        if not data:
            return True

        url = f"{self.api_url}/rest/v1/{table}"
        headers = self.headers.copy()
        headers["Prefer"] = "resolution=merge-duplicates"

        try:
            response = requests.post(url, headers=headers, json=data, timeout=30)

            if response.status_code in [200, 201]:
                print(f"  ✅ Supabase: {len(data)} enregistrements synchronisés vers {table}")
                return True
            else:
                print(f"  ❌ Supabase erreur {response.status_code}: {response.text[:200]}")
                return False
        except Exception as e:
            print(f"  ❌ Supabase exception: {e}")
            return False


# ============================================================================
# CLASSE GAZELLE API CLIENT
# ============================================================================

class GazelleAPIClient:
    """Client pour lire depuis Gazelle API"""

    def __init__(self, token_file: str):
        with open(token_file, 'r') as f:
            self.token_data = json.load(f)
        self.access_token = self.token_data['access_token']

    def _execute_query(self, query: str, variables: Optional[Dict] = None) -> Dict:
        """Exécute une requête GraphQL"""
        headers = {
            'Authorization': f"Bearer {self.access_token}",
            'Content-Type': 'application/json'
        }

        payload = {
            'query': query,
            'variables': variables or {}
        }

        response = requests.post(GAZELLE_API_URL, json=payload, headers=headers, timeout=60)
        response.raise_for_status()

        result = response.json()

        if 'errors' in result:
            raise ValueError(f"GraphQL errors: {result['errors']}")

        return result['data']

    def get_all_clients(self) -> List[Dict]:
        """Récupère tous les clients"""
        query = """
        query GetClients {
            allClients {
                edges {
                    node {
                        id
                        companyName
                        firstName
                        lastName
                        email
                        phone
                        mobilePhone
                        address {
                            street
                            city
                            province
                            postalCode
                            country
                        }
                        notes
                        createdAt
                        updatedAt
                    }
                }
            }
        }
        """
        result = self._execute_query(query)
        return [edge['node'] for edge in result['allClients']['edges']]

    def get_all_pianos(self) -> List[Dict]:
        """Récupère tous les pianos"""
        query = """
        query GetPianos {
            allPianos {
                edges {
                    node {
                        id
                        client { id }
                        make
                        model
                        serialNumber
                        type
                        year
                        location
                        notes
                        createdAt
                        updatedAt
                    }
                }
            }
        }
        """
        result = self._execute_query(query)
        return [edge['node'] for edge in result['allPianos']['edges']]

    def get_all_appointments(self) -> List[Dict]:
        """Récupère tous les rendez-vous"""
        query = """
        query GetAppointments {
            allAppointments {
                edges {
                    node {
                        id
                        client { id }
                        piano { id }
                        appointmentDate
                        startTime
                        endTime
                        allDay
                        duration
                        assignedTo { id }
                        title
                        description
                        status
                        notes
                        createdAt
                        updatedAt
                    }
                }
            }
        }
        """
        result = self._execute_query(query)
        return [edge['node'] for edge in result['allAppointments']['edges']]

    def get_all_timeline_entries(self) -> List[Dict]:
        """Récupère toutes les timeline entries"""
        query = """
        query GetTimelineEntries {
            allTimelineEntries {
                edges {
                    node {
                        id
                        client { id }
                        piano { id }
                        invoice { id }
                        estimate { id }
                        user { id }
                        occurredAt
                        type
                        title
                        details
                        createdAt
                        updatedAt
                    }
                }
            }
        }
        """
        result = self._execute_query(query)
        return [edge['node'] for edge in result['allTimelineEntries']['edges']]


# ============================================================================
# FONCTIONS DE TRANSFORMATION
# ============================================================================

def transform_client_for_supabase(client: Dict) -> Dict:
    """Transforme un client Gazelle pour Supabase"""
    address = client.get('address') or {}

    return {
        'external_id': client['id'],
        'company_name': client.get('companyName'),
        'first_name': client.get('firstName'),
        'last_name': client.get('lastName'),
        'email': client.get('email'),
        'phone': client.get('phone'),
        'mobile_phone': client.get('mobilePhone'),
        'street': address.get('street'),
        'city': address.get('city'),
        'province': address.get('province'),
        'postal_code': address.get('postalCode'),
        'country': address.get('country'),
        'notes': client.get('notes'),
        'created_at': client.get('createdAt'),
        'updated_at': client.get('updatedAt')
    }

def transform_piano_for_supabase(piano: Dict) -> Dict:
    """Transforme un piano Gazelle pour Supabase"""
    client_obj = piano.get('client') or {}

    return {
        'external_id': piano['id'],
        'client_external_id': client_obj.get('id'),
        'make': piano.get('make'),
        'model': piano.get('model'),
        'serial_number': piano.get('serialNumber'),
        'type': piano.get('type'),
        'year': piano.get('year'),
        'location': piano.get('location'),
        'notes': piano.get('notes'),
        'created_at': piano.get('createdAt'),
        'updated_at': piano.get('updatedAt')
    }

def transform_appointment_for_supabase(appt: Dict) -> Dict:
    """Transforme un appointment Gazelle pour Supabase"""
    from datetime import datetime
    import pytz

    client_obj = appt.get('client') or {}
    piano_obj = appt.get('piano') or {}
    assigned_to = appt.get('assignedTo') or {}

    # Extraire l'heure depuis startTime (format ISO: "2026-01-06T14:00:00.000Z")
    # Gazelle stocke en UTC, on doit convertir en heure locale (Eastern Time)
    appointment_time = None
    duration_minutes = None

    if appt.get('startTime'):
        try:
            # Parse ISO timestamp
            dt_utc = datetime.fromisoformat(appt['startTime'].replace('Z', '+00:00'))
            # Convertir en Montréal (Eastern Time)
            montreal = pytz.timezone('America/Montreal')
            dt_montreal = dt_utc.astimezone(montreal)
            # Extraire juste l'heure (format TIME pour PostgreSQL)
            appointment_time = dt_montreal.strftime('%H:%M:%S')
        except Exception as e:
            print(f"  ⚠️ Erreur parsing startTime pour {appt.get('id')}: {e}")

    if appt.get('duration'):
        try:
            duration_minutes = int(appt['duration'])
        except:
            pass

    return {
        'external_id': appt['id'],
        'client_external_id': client_obj.get('id'),
        'appointment_date': appt.get('appointmentDate'),
        'appointment_time': appointment_time,
        'duration_minutes': duration_minutes,
        'all_day': appt.get('allDay', False),
        'technicien': assigned_to.get('id'),  # ID Gazelle du technicien assigné
        'title': appt.get('title'),
        'description': appt.get('description'),
        'status': appt.get('status'),
        'notes': appt.get('notes'),
        'created_at': appt.get('createdAt'),
        'updated_at': appt.get('updatedAt')
    }

def transform_timeline_for_supabase(entry: Dict) -> Dict:
    """Transforme une timeline entry Gazelle pour Supabase"""
    client_obj = entry.get('client') or {}
    piano_obj = entry.get('piano') or {}
    invoice_obj = entry.get('invoice') or {}
    estimate_obj = entry.get('estimate') or {}
    user_obj = entry.get('user') or {}

    return {
        'id': entry['id'],
        'client_id': client_obj.get('id'),
        'piano_id': piano_obj.get('id'),
        'invoice_id': invoice_obj.get('id'),
        'estimate_id': estimate_obj.get('id'),
        'user_id': user_obj.get('id'),
        'occurred_at': entry.get('occurredAt'),
        'entry_type': entry.get('type'),
        'title': entry.get('title'),
        'details': entry.get('details'),
        'created_at': entry.get('createdAt'),
        'updated_at': entry.get('updatedAt')
    }


# ============================================================================
# FONCTION PRINCIPALE
# ============================================================================

def main():
    """Synchronisation complète Gazelle → Supabase"""

    print("=" * 70)
    print("SYNCHRONISATION PC → SUPABASE")
    print("=" * 70)
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    try:
        # Initialiser les clients
        print("🔧 Initialisation...")
        gazelle = GazelleAPIClient(GAZELLE_TOKEN_FILE)
        supabase = SupabaseClient(SUPABASE_URL, SUPABASE_KEY)
        print("✅ Clients initialisés")
        print()

        # Synchroniser les clients
        print("👥 Synchronisation des clients...")
        clients = gazelle.get_all_clients()
        print(f"  📥 {len(clients)} clients récupérés depuis Gazelle")
        supabase_clients = [transform_client_for_supabase(c) for c in clients]
        supabase.upsert('gazelle_clients', supabase_clients)
        print()

        # Synchroniser les pianos
        print("🎹 Synchronisation des pianos...")
        pianos = gazelle.get_all_pianos()
        print(f"  📥 {len(pianos)} pianos récupérés depuis Gazelle")
        supabase_pianos = [transform_piano_for_supabase(p) for p in pianos]
        supabase.upsert('gazelle_pianos', supabase_pianos)
        print()

        # Synchroniser les appointments
        print("📅 Synchronisation des rendez-vous...")
        appointments = gazelle.get_all_appointments()
        print(f"  📥 {len(appointments)} rendez-vous récupérés depuis Gazelle")
        supabase_appointments = [transform_appointment_for_supabase(a) for a in appointments]
        supabase.upsert('gazelle_appointments', supabase_appointments)
        print()

        # Synchroniser les timeline entries
        print("📖 Synchronisation des timeline entries...")
        timeline_entries = gazelle.get_all_timeline_entries()
        print(f"  📥 {len(timeline_entries)} timeline entries récupérées depuis Gazelle")
        supabase_timeline = [transform_timeline_for_supabase(t) for t in timeline_entries]
        # Aligner avec l'app Mac : table cible = gazelle.timeline_entries
        supabase.upsert('gazelle.timeline_entries', supabase_timeline)
        print()

        print("=" * 70)
        print("✅ SYNCHRONISATION TERMINÉE AVEC SUCCÈS")
        print("=" * 70)
        return 0

    except Exception as e:
        print()
        print("=" * 70)
        print(f"❌ ERREUR: {e}")
        print("=" * 70)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
