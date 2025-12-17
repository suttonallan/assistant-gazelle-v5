#!/usr/bin/env python3
"""
Script de debug pour Olivier Asselin dans train_summaries.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import os
from dotenv import load_dotenv
load_dotenv()

from core.supabase_storage import SupabaseStorage
from modules.assistant.services.queries import GazelleQueries

def main():
    storage = SupabaseStorage()
    queries = GazelleQueries(storage)

    print("="*70)
    print("DEBUG: Olivier Asselin dans train_summaries")
    print("="*70)

    # 1. Rechercher le client
    print("\n1. Recherche client 'olivier asselin'...")
    results = queries.search_clients(['olivier asselin'])
    olivier = None
    for r in results:
        name = r.get('name') or r.get('company_name')
        if 'asselin' in name.lower():
            olivier = r
            print(f"✅ Trouvé: {name} (ID: {r.get('external_id')})")
            break

    if not olivier:
        print("❌ Olivier Asselin non trouvé!")
        return

    client_id = olivier.get('external_id')
    print(f"\n2. Client ID: {client_id}")
    print(f"   Source: {olivier.get('_source')}")
    print(f"   Company name: {olivier.get('company_name')}")

    # 2. Vérifier les pianos
    print(f"\n3. Recherche pianos...")
    import requests
    pianos_url = f"{storage.api_url}/gazelle_pianos?client_external_id=eq.{client_id}"
    pianos_response = requests.get(pianos_url, headers=storage._get_headers())
    print(f"   Status: {pianos_response.status_code}")

    if pianos_response.status_code == 200:
        pianos = pianos_response.json()
        print(f"   ✅ {len(pianos)} pianos trouvés")
        for p in pianos:
            print(f"      - {p.get('make')} {p.get('model')} (ID: {p.get('external_id')})")
    else:
        print(f"   ❌ Erreur: {pianos_response.text}")

    # 3. Vérifier timeline
    print(f"\n4. Recherche timeline...")
    try:
        timeline = queries.get_timeline_entries(client_id, entity_type='client', limit=10)
        print(f"   ✅ {len(timeline)} entrées timeline trouvées")
        if timeline:
            print(f"      Première entrée: {timeline[0].get('notes', '')[:100]}...")
    except Exception as e:
        print(f"   ❌ Erreur timeline: {e}")

    # 4. Vérifier contacts associés
    print(f"\n5. Recherche contacts associés...")
    try:
        contacts_url = f"{storage.api_url}/gazelle_contacts?company_external_id=eq.{client_id}"
        contacts_response = requests.get(contacts_url, headers=storage._get_headers())
        print(f"   Status: {contacts_response.status_code}")

        if contacts_response.status_code == 200:
            contacts = contacts_response.json()
            print(f"   ✅ {len(contacts)} contacts trouvés")
            for c in contacts:
                print(f"      - {c.get('first_name')} {c.get('last_name')}")
        else:
            print(f"   ❌ Erreur: {contacts_response.text}")
    except Exception as e:
        print(f"   ❌ Erreur contacts: {e}")

    # 5. Générer un sommaire client
    print(f"\n6. Génération sommaire client format 'detailed'...")
    try:
        from scripts.train_summaries import SummaryTrainer
        trainer = SummaryTrainer()

        summary = trainer.generate_client_summary(client_id, format_style='detailed')

        print("\n" + "="*70)
        print("RÉSULTAT:")
        print("="*70)
        print(summary['summary'])
        print("="*70)

    except Exception as e:
        print(f"   ❌ Erreur génération sommaire: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
