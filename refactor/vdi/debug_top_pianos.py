#!/usr/bin/env python3
"""Debug script pour vérifier les pianos Top dans les tournées"""

import os
from dotenv import load_dotenv
from supabase import create_client

# Load env vars
load_dotenv('/Users/allansutton/Documents/assistant-gazelle-v5/.env')

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ Variables d'environnement manquantes")
    exit(1)

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

print("=== TOUS LES PIANOS TOP (is_top=true) ===")
response = supabase.table('tournee_pianos').select('tournee_id,gazelle_id,is_top').eq('is_top', True).execute()
print(f"Nombre de pianos Top: {len(response.data)}")
for row in response.data:
    print(f"  - Tournée: {row['tournee_id']}, Piano: {row['gazelle_id']}")

print("\n=== TOURNÉES EXISTANTES ===")
tournees = supabase.table('tournees').select('id,nom').execute()
print(f"Nombre de tournées: {len(tournees.data)}")
for t in tournees.data:
    print(f"  - {t['nom']} (ID: {t['id']})")

print("\n=== PIANOS DANS CHAQUE TOURNÉE ===")
for t in tournees.data:
    pianos = supabase.table('tournee_pianos').select('gazelle_id,is_top').eq('tournee_id', t['id']).execute()
    top_count = sum(1 for p in pianos.data if p['is_top'])
    print(f"\n{t['nom']} ({t['id']}):")
    print(f"  Total pianos: {len(pianos.data)}")
    print(f"  Pianos Top: {top_count}")

    if pianos.data:
        for p in pianos.data:
            status = "🟡 TOP" if p['is_top'] else "⚪ normal"
            print(f"    - {p['gazelle_id']}: {status}")
