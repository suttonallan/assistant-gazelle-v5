#!/usr/bin/env python3
"""
Script de test pour vérifier les données géographiques dans Supabase.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import requests

# Charger .env
env_path = Path(__file__).parent / '.env'
load_dotenv(env_path)

# Configuration Supabase
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ Variables Supabase manquantes")
    sys.exit(1)

# Test 1: Vérifier appointments du 2025-12-30
print("="*60)
print("Test 1: Appointments du 2025-12-30")
print("="*60)

url = f"{SUPABASE_URL}/rest/v1/gazelle_appointments"
headers = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}

params = {
    "select": "external_id,client_id,appointment_time,client:client_id(company_name,default_location_postal_code,default_location_municipality)",
    "appointment_date": "eq.2025-12-30",
    "limit": "3"
}

response = requests.get(url, headers=headers, params=params)

if response.status_code == 200:
    appointments = response.json()
    print(f"✅ Trouvé {len(appointments)} rendez-vous\n")

    for apt in appointments:
        print(f"  ID: {apt.get('external_id')}")
        print(f"  Heure: {apt.get('appointment_time')}")
        print(f"  Client ID: {apt.get('client_id')}")

        client = apt.get('client')
        if client:
            print(f"  Client:")
            print(f"    Nom: {client.get('company_name')}")
            print(f"    Ville: {client.get('default_location_municipality')}")
            print(f"    Code Postal: {client.get('default_location_postal_code')}")
        else:
            print("  Client: NULL (pas de relation)")
        print()
else:
    print(f"❌ Erreur {response.status_code}: {response.text}")

# Test 2: Vérifier un client directement
print("="*60)
print("Test 2: Exemples de clients avec codes postaux")
print("="*60)

url_clients = f"{SUPABASE_URL}/rest/v1/gazelle_clients"
params_clients = {
    "select": "external_id,company_name,default_location_postal_code,default_location_municipality",
    "default_location_postal_code": "not.is.null",
    "limit": "5"
}

response_clients = requests.get(url_clients, headers=headers, params=params_clients)

if response_clients.status_code == 200:
    clients = response_clients.json()
    print(f"✅ Trouvé {len(clients)} clients avec codes postaux\n")

    for client in clients:
        postal = client.get('default_location_postal_code', '')
        city = client.get('default_location_municipality', '')
        name = client.get('company_name', 'Sans nom')

        # Tester le mapping
        from api.chat.geo_mapping import get_neighborhood_from_postal_code
        neighborhood = get_neighborhood_from_postal_code(postal, city)

        print(f"  {name}")
        print(f"    Code Postal: {postal}")
        print(f"    Ville: {city}")
        print(f"    → Quartier: {neighborhood}")
        print()
else:
    print(f"❌ Erreur {response_clients.status_code}: {response_clients.text}")
