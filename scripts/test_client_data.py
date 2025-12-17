#!/usr/bin/env python3
"""
Script de test pour vérifier toutes les données disponibles pour un client
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
import os
load_dotenv(Path(__file__).parent.parent / '.env')

from core.supabase_storage import SupabaseStorage
from modules.assistant.services.queries import GazelleQueries
import requests

# Client à tester
CLIENT_ID = "cli_PXsT1CFhK098pNqr"

storage = SupabaseStorage()
queries = GazelleQueries(storage)

print("="*70)
print(f"TEST DES DONNÉES POUR CLIENT: {CLIENT_ID}")
print("="*70)

# 1. Informations client
print("\n1️⃣ INFORMATIONS CLIENT:")
print("-" * 70)
results = queries.search_clients([CLIENT_ID])
if results:
    client = results[0]
    print(f"✅ Client trouvé: {client.get('company_name', 'N/A')}")
    print(f"   Clés disponibles: {list(client.keys())}")
    print(f"   Contenu complet:")
    for key, value in client.items():
        if value:
            print(f"      {key}: {value}")
else:
    print("❌ Client non trouvé")

# 2. Pianos du client
print("\n2️⃣ PIANOS DU CLIENT:")
print("-" * 70)
pianos_url = f"{storage.api_url}/gazelle_pianos?client_external_id=eq.{CLIENT_ID}&select=*&limit=10"
pianos_response = requests.get(pianos_url, headers=storage._get_headers())
if pianos_response.status_code == 200:
    pianos = pianos_response.json()
    print(f"✅ {len(pianos)} piano(s) trouvé(s)")
    for idx, piano in enumerate(pianos, 1):
        print(f"\n   Piano {idx}:")
        print(f"      Clés: {list(piano.keys())}")
        for key, value in piano.items():
            if value:
                print(f"      {key}: {value}")
else:
    print(f"❌ Erreur: {pianos_response.status_code} - {pianos_response.text[:200]}")

# 3. Timeline entries pour le client
print("\n3️⃣ TIMELINE ENTRIES (CLIENT):")
print("-" * 70)
timeline_client = queries.get_timeline_entries(CLIENT_ID, entity_type='client', limit=20)
print(f"✅ {len(timeline_client)} entrée(s) timeline trouvée(s)")
for idx, entry in enumerate(timeline_client[:5], 1):
    print(f"\n   Entrée {idx}:")
    print(f"      Clés: {list(entry.keys())}")
    for key, value in entry.items():
        if value:
            val_str = str(value)[:200] + '...' if len(str(value)) > 200 else str(value)
            print(f"      {key}: {val_str}")

# 4. Timeline entries pour les pianos
print("\n4️⃣ TIMELINE ENTRIES (PIANOS):")
print("-" * 70)
if pianos_response.status_code == 200:
    pianos = pianos_response.json()
    for piano in pianos:
        piano_id = piano.get('external_id')
        if piano_id:
            print(f"\n   Piano {piano_id}:")
            timeline_piano = queries.get_timeline_entries(piano_id, entity_type='piano', limit=10)
            print(f"      ✅ {len(timeline_piano)} entrée(s) timeline")
            for idx, entry in enumerate(timeline_piano[:3], 1):
                print(f"      Entrée {idx}:")
                for key, value in entry.items():
                    if value:
                        val_str = str(value)[:150] + '...' if len(str(value)) > 150 else str(value)
                        print(f"         {key}: {val_str}")

# 5. Contacts associés
print("\n5️⃣ CONTACTS ASSOCIÉS:")
print("-" * 70)
contacts_url = f"{storage.api_url}/gazelle_contacts?client_external_id=eq.{CLIENT_ID}&select=*&limit=10"
contacts_response = requests.get(contacts_url, headers=storage._get_headers())
if contacts_response.status_code == 200:
    contacts = contacts_response.json()
    print(f"✅ {len(contacts)} contact(s) trouvé(s)")
    for idx, contact in enumerate(contacts, 1):
        print(f"\n   Contact {idx}:")
        print(f"      Clés: {list(contact.keys())}")
        for key, value in contact.items():
            if value:
                print(f"      {key}: {value}")
else:
    print(f"❌ Erreur: {contacts_response.status_code} - {contacts_response.text[:200]}")

# 6. Rendez-vous du client
print("\n6️⃣ RENDEZ-VOUS DU CLIENT:")
print("-" * 70)
from datetime import datetime
appointments = queries.get_appointments(date=datetime.now(), technicien=None, limit=50)
client_appts = [a for a in appointments if a.get('client_external_id') == CLIENT_ID]
print(f"✅ {len(client_appts)} rendez-vous trouvé(s)")
for idx, appt in enumerate(client_appts[:3], 1):
    print(f"\n   RV {idx}:")
    print(f"      Clés: {list(appt.keys())}")
    for key, value in appt.items():
        if value:
            val_str = str(value)[:150] + '...' if len(str(value)) > 150 else str(value)
            print(f"      {key}: {val_str}")

print("\n" + "="*70)
print("FIN DU TEST")
print("="*70)

