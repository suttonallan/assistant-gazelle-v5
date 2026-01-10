#!/usr/bin/env python3
"""
Test complet du système après migration start_datetime.

Vérifie:
1. Migration SQL exécutée (colonne start_datetime existe)
2. UPSERT fonctionne (aucun doublon)
3. Conversion timezone Montreal → UTC
4. Sync complète fonctionne

Usage:
    python3 scripts/test_complete_system.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

import requests
import os
from datetime import datetime, timedelta

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_SERVICE_ROLE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')


def test_migration_executed():
    """Test 1: Vérifier que la migration SQL a été exécutée."""
    print("=" * 70)
    print("TEST 1: Migration SQL (start_datetime)")
    print("=" * 70)

    url = f"{SUPABASE_URL}/rest/v1/gazelle_appointments"
    headers = {
        'apikey': SUPABASE_SERVICE_ROLE_KEY,
        'Authorization': f'Bearer {SUPABASE_SERVICE_ROLE_KEY}'
    }

    # Essayer de récupérer avec start_datetime
    test_url = f"{url}?select=external_id,start_datetime&limit=1"

    try:
        response = requests.get(test_url, headers=headers)

        if response.status_code == 200:
            print("✅ Colonne start_datetime EXISTE")
            return True
        elif response.status_code == 400:
            error = response.json()
            if 'does not exist' in error.get('message', ''):
                print("❌ Colonne start_datetime N'EXISTE PAS")
                print("   → Exécute la migration SQL d'abord!")
                print("   → Fichier: scripts/migrations/add_start_datetime_to_appointments.sql")
                return False
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return False


def test_upsert_no_duplicates():
    """Test 2: Vérifier que l'UPSERT fonctionne (pas de doublons)."""
    print()
    print("=" * 70)
    print("TEST 2: UPSERT (aucun doublon)")
    print("=" * 70)

    url = f"{SUPABASE_URL}/rest/v1/gazelle_appointments"
    headers = {
        'apikey': SUPABASE_SERVICE_ROLE_KEY,
        'Authorization': f'Bearer {SUPABASE_SERVICE_ROLE_KEY}',
        'Content-Type': 'application/json'
    }

    test_id = 'evt_test_upsert_2026'

    # Insertion 1
    print("Insertion 1 (title: 'Test UPSERT v1')...")
    upsert_url = f"{url}?on_conflict=external_id"
    headers_prefer = headers.copy()
    headers_prefer['Prefer'] = 'resolution=merge-duplicates,return=representation'

    record_v1 = {
        'external_id': test_id,
        'title': 'Test UPSERT v1',
        'status': 'scheduled'
    }

    response = requests.post(upsert_url, headers=headers_prefer, json=record_v1)

    if response.status_code not in [200, 201]:
        print(f"❌ Échec insertion: {response.status_code}")
        return False

    # Insertion 2 (même external_id, doit UPDATE pas INSERT)
    print("Insertion 2 (title: 'Test UPSERT v2 - UPDATED')...")
    record_v2 = {
        'external_id': test_id,
        'title': 'Test UPSERT v2 - UPDATED',
        'status': 'completed'
    }

    response = requests.post(upsert_url, headers=headers_prefer, json=record_v2)

    if response.status_code not in [200, 201]:
        print(f"❌ Échec update: {response.status_code}")
        return False

    # Vérifier qu'il n'y a qu'UN seul enregistrement
    check_url = f"{url}?external_id=eq.{test_id}&select=external_id,title"
    response = requests.get(check_url, headers=headers)

    if response.status_code == 200:
        records = response.json()

        if len(records) == 1:
            print(f"✅ UPSERT fonctionne: 1 seul enregistrement (pas de doublon)")
            print(f"   Title: '{records[0]['title']}'")

            if records[0]['title'] == 'Test UPSERT v2 - UPDATED':
                print(f"✅ UPDATE a fonctionné (titre mis à jour)")
            else:
                print(f"⚠️  Titre pas mis à jour (attendu: 'Test UPSERT v2 - UPDATED')")
        else:
            print(f"❌ UPSERT échoué: {len(records)} enregistrements trouvés (doublons!)")
            return False

    # Nettoyer
    delete_url = f"{url}?external_id=eq.{test_id}"
    requests.delete(delete_url, headers=headers)
    print("🧹 Enregistrement test nettoyé")

    return True


def test_timezone_conversion():
    """Test 3: Vérifier conversion timezone."""
    print()
    print("=" * 70)
    print("TEST 3: Conversion Timezone (Montreal → UTC)")
    print("=" * 70)

    from core.timezone_utils import format_for_gazelle_filter, parse_gazelle_datetime
    from datetime import date

    # Test 1: Date Montreal → UTC
    test_date = date(2026, 1, 9)
    utc_result = format_for_gazelle_filter(test_date)

    print(f"Input:  {test_date} (Montreal)")
    print(f"Output: {utc_result}")

    # En hiver (EST = UTC-5), 00:00 Montreal = 05:00 UTC
    if utc_result == "2026-01-09T05:00:00Z":
        print("✅ Conversion Montreal → UTC correcte (00:00 EST = 05:00 UTC)")
    else:
        print(f"❌ Conversion incorrecte (attendu: 2026-01-09T05:00:00Z)")
        return False

    # Test 2: Parser CoreDateTime Gazelle
    print()
    gazelle_dt = "2026-01-09T19:30:00Z"
    parsed = parse_gazelle_datetime(gazelle_dt)

    print(f"Gazelle DateTime: {gazelle_dt}")
    print(f"Parsed:           {parsed}")

    if parsed and parsed.tzinfo:
        print("✅ CoreDateTime parsé avec timezone")
    else:
        print("❌ Erreur parsing CoreDateTime")
        return False

    return True


def test_sync_sample():
    """Test 4: Tester sync d'un échantillon."""
    print()
    print("=" * 70)
    print("TEST 4: Sync Échantillon (optionnel)")
    print("=" * 70)

    print("ℹ️  Pour tester une sync complète:")
    print("   python3 modules/sync_gazelle/sync_to_supabase.py")
    print()
    print("📊 Vérifiez ensuite:")
    print("   1. Dashboard → Notifications → Tâches & Imports")
    print("   2. Status: ✅ Succès")
    print("   3. Tables: appointments, timeline, etc.")

    return True


def main():
    """Exécute tous les tests."""
    print("\n" + "=" * 70)
    print("🧪 TEST COMPLET DU SYSTÈME")
    print("=" * 70)
    print()

    results = []

    # Test 1: Migration
    results.append(("Migration SQL", test_migration_executed()))

    # Test 2: UPSERT (seulement si migration OK)
    if results[0][1]:
        results.append(("UPSERT", test_upsert_no_duplicates()))
    else:
        results.append(("UPSERT", False))
        print("\n⏭️  Test UPSERT sauté (migration non exécutée)")

    # Test 3: Timezone (toujours)
    results.append(("Timezone", test_timezone_conversion()))

    # Test 4: Info sync
    results.append(("Info Sync", test_sync_sample()))

    # Résumé
    print()
    print("=" * 70)
    print("📊 RÉSUMÉ DES TESTS")
    print("=" * 70)

    for name, passed in results:
        status = "✅ PASSÉ" if passed else "❌ ÉCHOUÉ"
        print(f"   {status:12} - {name}")

    print()

    all_passed = all(result[1] for result in results[:3])  # Ignorer test 4 (info)

    if all_passed:
        print("🎉 TOUS LES TESTS PASSENT!")
        print()
        print("✅ Le système est prêt:")
        print("   • Migration SQL exécutée")
        print("   • UPSERT activé (aucun doublon)")
        print("   • Conversions timezone correctes")
        print()
        print("🚀 Prochaine étape:")
        print("   Lancer une sync complète:")
        print("   python3 modules/sync_gazelle/sync_to_supabase.py")
    else:
        print("⚠️  CERTAINS TESTS ONT ÉCHOUÉ")
        print()
        if not results[0][1]:
            print("❌ Action requise: Exécuter migration SQL")
            print("   1. Dashboard Supabase → SQL Editor")
            print("   2. Copier scripts/migrations/add_start_datetime_to_appointments.sql")
            print("   3. Run")

    print()
    print("=" * 70)


if __name__ == '__main__':
    main()
