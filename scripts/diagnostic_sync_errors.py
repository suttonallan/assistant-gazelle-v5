#!/usr/bin/env python3
"""
Diagnostic des erreurs de synchronisation Gazelle.

Vérifie:
1. Pagination clients/pianos (limite 1000)
2. Erreurs FK et start_datetime
3. Permissions API users
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

import requests
import os

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

def check_sync_counts():
    """Vérifie les compteurs actuels dans Supabase."""
    print("=" * 70)
    print("📊 DIAGNOSTIC: Compteurs Tables Supabase")
    print("=" * 70)
    print()

    tables = ['gazelle_clients', 'gazelle_pianos', 'gazelle_appointments', 'gazelle_timeline_entries', 'users']

    for table in tables:
        url = f"{SUPABASE_URL}/rest/v1/{table}?select=id&limit=1"
        headers = {
            'apikey': SUPABASE_KEY,
            'Authorization': f'Bearer {SUPABASE_KEY}',
            'Prefer': 'count=exact'
        }

        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            count_header = response.headers.get('Content-Range', '')
            if '/' in count_header:
                count = count_header.split('/')[-1]
                status = "✅" if count != "1000" else "⚠️ "
                print(f"{status} {table:30} {count:>6} enregistrements")
            else:
                print(f"⚠️  {table:30} Pas de Content-Range")
        else:
            print(f"❌ {table:30} Erreur: {response.status_code} - {response.text[:100]}")

    print()


def check_start_datetime():
    """Vérifie si start_datetime est bien rempli."""
    print("=" * 70)
    print("🕐 DIAGNOSTIC: Colonne start_datetime")
    print("=" * 70)
    print()

    url = f"{SUPABASE_URL}/rest/v1/gazelle_appointments?select=external_id,start_datetime,appointment_date,appointment_time&limit=5"
    headers = {
        'apikey': SUPABASE_KEY,
        'Authorization': f'Bearer {SUPABASE_KEY}'
    }

    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        appointments = response.json()

        if not appointments:
            print("⚠️  Aucun RV trouvé")
            return

        null_count = 0
        filled_count = 0

        for appt in appointments:
            if appt.get('start_datetime'):
                filled_count += 1
                print(f"✅ {appt['external_id']}: start_datetime = {appt['start_datetime']}")
            else:
                null_count += 1
                print(f"❌ {appt['external_id']}: start_datetime = NULL (date={appt.get('appointment_date')}, time={appt.get('appointment_time')})")

        print()
        print(f"Résumé: {filled_count} remplis, {null_count} NULL")

        if null_count > 0:
            print("\n⚠️  PROBLÈME: start_datetime n'est pas rempli correctement")
            print("   → Vérifie sync_to_supabase.py ligne 494 (assignment start_datetime)")
    else:
        print(f"❌ Erreur API: {response.status_code}")

    print()


def check_fk_errors():
    """Vérifie les erreurs de clés étrangères."""
    print("=" * 70)
    print("🔗 DIAGNOSTIC: Foreign Keys")
    print("=" * 70)
    print()

    # Vérifier timeline entries sans user
    url = f"{SUPABASE_URL}/rest/v1/gazelle_timeline_entries?select=id,performed_by_user_id&performed_by_user_id=is.null&limit=5"
    headers = {
        'apikey': SUPABASE_KEY,
        'Authorization': f'Bearer {SUPABASE_KEY}'
    }

    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        entries = response.json()

        if entries:
            print(f"⚠️  {len(entries)} timeline entries avec performed_by_user_id = NULL")
            for entry in entries[:3]:
                print(f"   - {entry['id']}")
            print("\n   Cause possible: Users pas synchronisés ou ID user invalide")
        else:
            print("✅ Toutes les timeline entries ont un performed_by_user_id valide")
    else:
        print(f"❌ Erreur API: {response.status_code}")

    print()


def check_pagination_issue():
    """Analyse si clients/pianos sont bloqués à 1000."""
    print("=" * 70)
    print("📄 DIAGNOSTIC: Problème Pagination (limite 1000)")
    print("=" * 70)
    print()

    tables_to_check = [
        ('gazelle_clients', 'Clients'),
        ('gazelle_pianos', 'Pianos')
    ]

    for table, label in tables_to_check:
        url = f"{SUPABASE_URL}/rest/v1/{table}?select=id&limit=1"
        headers = {
            'apikey': SUPABASE_KEY,
            'Authorization': f'Bearer {SUPABASE_KEY}',
            'Prefer': 'count=exact'
        }

        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            count_header = response.headers.get('Content-Range', '')
            if '/' in count_header:
                count_str = count_header.split('/')[-1]
                count = int(count_str) if count_str.isdigit() else 0
            else:
                count = 0

            if count == 1000:
                print(f"⚠️  {label}: BLOQUÉ À 1000 enregistrements")
                print(f"   → sync_to_supabase.py utilise probablement get_{table.replace('gazelle_', '')}(limit=1000)")
                print(f"   → Pas de pagination avec curseur")
                print(f"   → SOLUTION: Utiliser all{label}Batched avec pageInfo/cursor")
            elif count > 1000:
                print(f"✅ {label}: {count} enregistrements (pagination fonctionne)")
            else:
                print(f"ℹ️  {label}: {count} enregistrements (< 1000, normal)")
        else:
            print(f"❌ {label}: Erreur {response.status_code}")

        print()


def main():
    """Exécute tous les diagnostics."""
    print("\n" + "=" * 70)
    print("🔍 DIAGNOSTIC COMPLET: Erreurs Synchronisation Gazelle")
    print("=" * 70)
    print()

    check_sync_counts()
    check_start_datetime()
    check_fk_errors()
    check_pagination_issue()

    print("=" * 70)
    print("✅ DIAGNOSTIC TERMINÉ")
    print("=" * 70)
    print()


if __name__ == '__main__':
    main()
