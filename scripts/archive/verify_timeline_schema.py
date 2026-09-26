#!/usr/bin/env python3
"""Vérifier le schéma de gazelle_timeline_entries et les types acceptés."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from core.supabase_storage import SupabaseStorage
import requests

storage = SupabaseStorage()

print("=" * 70)
print("🔍 VÉRIFICATION SCHÉMA gazelle_timeline_entries")
print("=" * 70)

# 1. Vérifier les colonnes de la table
print("\n1️⃣  Colonnes de la table:")
try:
    # Récupérer une entrée pour voir la structure
    url = f"{storage.api_url}/gazelle_timeline_entries?limit=1"
    resp = requests.get(url, headers=storage._get_headers())

    if resp.status_code == 200:
        data = resp.json()
        if data:
            print("✅ Colonnes disponibles:")
            for key in sorted(data[0].keys()):
                print(f"   - {key}")
        else:
            print("⚠️  Table vide, impossible de voir les colonnes")
    else:
        print(f"❌ Erreur API: {resp.status_code}")
except Exception as e:
    print(f"❌ Erreur: {e}")

# 2. Vérifier les types entry_type distincts existants
print("\n2️⃣  Types entry_type actuellement dans la table:")
try:
    url = f"{storage.api_url}/gazelle_timeline_entries?select=entry_type&limit=1000"
    resp = requests.get(url, headers=storage._get_headers())

    if resp.status_code == 200:
        data = resp.json()
        entry_types = set()
        for item in data:
            if item.get('entry_type'):
                entry_types.add(item['entry_type'])

        print(f"✅ {len(entry_types)} types distincts trouvés:")
        for et in sorted(entry_types):
            print(f"   - {et}")
    else:
        print(f"❌ Erreur API: {resp.status_code}")
except Exception as e:
    print(f"❌ Erreur: {e}")

# 3. Compter le nombre total d'entrées
print("\n3️⃣  Statistiques:")
try:
    url = f"{storage.api_url}/gazelle_timeline_entries?select=id&limit=1"
    headers = storage._get_headers()
    headers['Prefer'] = 'count=exact'

    resp = requests.get(url, headers=headers)

    if resp.status_code == 200:
        count_header = resp.headers.get('content-range', '')
        if count_header:
            total = count_header.split('/')[-1]
            print(f"✅ Nombre total d'entrées: {total}")
        else:
            print("⚠️  Impossible de compter (header manquant)")
    else:
        print(f"❌ Erreur API: {resp.status_code}")
except Exception as e:
    print(f"❌ Erreur: {e}")

print("\n" + "=" * 70)
