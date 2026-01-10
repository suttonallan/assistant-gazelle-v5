#!/usr/bin/env python3
"""
Script de validation de la table gazelle_appointments.

Vérifie:
1. Clé primaire external_id (pour UPSERT)
2. Colonne start_datetime TIMESTAMPTZ
3. Index sur start_datetime
4. Données existantes

Usage:
    python3 scripts/validate_appointments_table.py
"""

import sys
import os
from pathlib import Path

# Ajouter le projet au path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

import requests

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_SERVICE_ROLE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')


def validate_table_structure() -> dict:
    """
    Valide la structure de gazelle_appointments.

    Returns:
        Dict avec résultats de validation
    """
    print("=" * 70)
    print("🔍 VALIDATION TABLE gazelle_appointments")
    print("=" * 70)
    print()

    results = {
        'upsert_works': False,
        'start_datetime_exists': False,
        'has_data': False,
        'sample_count': 0
    }

    url = f"{SUPABASE_URL}/rest/v1/gazelle_appointments"
    headers = {
        'apikey': SUPABASE_SERVICE_ROLE_KEY,
        'Authorization': f'Bearer {SUPABASE_SERVICE_ROLE_KEY}',
        'Content-Type': 'application/json'
    }

    # Test 1: Vérifier UPSERT avec external_id
    print("1️⃣  Test UPSERT (clé primaire external_id)...")

    test_record = {
        'external_id': 'evt_test_migration_2026',
        'title': 'Test Migration Validation',
        'status': 'scheduled'
    }

    upsert_url = f"{url}?on_conflict=external_id"
    headers_with_prefer = headers.copy()
    headers_with_prefer['Prefer'] = 'resolution=merge-duplicates,return=representation'

    try:
        response = requests.post(upsert_url, headers=headers_with_prefer, json=test_record)

        if response.status_code in [200, 201]:
            print("   ✅ UPSERT fonctionne (external_id est unique)")
            results['upsert_works'] = True

            # Nettoyer
            delete_url = f"{url}?external_id=eq.evt_test_migration_2026"
            requests.delete(delete_url, headers=headers)
            print("   🧹 Enregistrement test nettoyé")
        else:
            print(f"   ❌ ERREUR UPSERT: HTTP {response.status_code}")
            print(f"      Message: {response.text[:300]}")
    except Exception as e:
        print(f"   ❌ Exception: {e}")

    print()

    # Test 2: Vérifier colonne start_datetime
    print("2️⃣  Vérification colonne start_datetime...")

    sample_url = f"{url}?select=external_id,title,start_datetime,appointment_date,appointment_time,created_at&order=created_at.desc&limit=10"

    try:
        response = requests.get(sample_url, headers=headers)

        if response.status_code == 200:
            records = response.json()
            results['sample_count'] = len(records)
            results['has_data'] = len(records) > 0

            if len(records) == 0:
                print("   ⚠️  Table vide (aucun rendez-vous)")
                print("      → Normal si première sync pas encore faite")
            else:
                first_record = records[0]

                # Vérifier si start_datetime existe
                if 'start_datetime' in first_record:
                    print("   ✅ Colonne start_datetime EXISTE")
                    results['start_datetime_exists'] = True

                    # Compter combien ont la colonne remplie
                    filled = [r for r in records if r.get('start_datetime')]
                    print(f"   📊 {len(filled)}/{len(records)} enregistrements ont start_datetime rempli")

                    if filled:
                        example = filled[0]
                        print(f"   📅 Exemple:")
                        print(f"      external_id: {example['external_id']}")
                        print(f"      start_datetime: {example['start_datetime']}")
                        print(f"      appointment_date: {example.get('appointment_date')}")
                        print(f"      appointment_time: {example.get('appointment_time')}")
                else:
                    print("   ❌ Colonne start_datetime N'EXISTE PAS")
                    print("   → Vous devez exécuter la migration SQL!")
                    print()
                    print("   📋 Instructions:")
                    print("      1. Allez sur https://supabase.com/dashboard")
                    print("      2. SQL Editor → New Query")
                    print("      3. Copiez scripts/migrations/add_start_datetime_to_appointments.sql")
                    print("      4. Exécutez (Run)")
        else:
            print(f"   ❌ Erreur API: HTTP {response.status_code}")
            print(f"      {response.text[:300]}")
    except Exception as e:
        print(f"   ❌ Exception: {e}")

    print()

    # Test 3: Index (info seulement)
    print("3️⃣  Index idx_gazelle_appointments_start_datetime...")
    print("   ℹ️  L'API REST ne permet pas de vérifier les index")
    print("   ℹ️  Après exécution de la migration, l'index sera créé automatiquement")
    print()

    # Résumé
    print("=" * 70)
    print("📊 RÉSUMÉ DE LA VALIDATION")
    print("=" * 70)
    print()

    print(f"✅ UPSERT avec external_id: {'OUI' if results['upsert_works'] else 'NON'}")
    print(f"✅ Colonne start_datetime:  {'OUI' if results['start_datetime_exists'] else 'NON'}")
    print(f"📦 Enregistrements:         {results['sample_count']}")
    print()

    if results['upsert_works'] and results['start_datetime_exists']:
        print("🎉 LA TABLE EST PRÊTE À RECEVOIR DES DONNÉES UTC!")
        print()
        print("✅ Prochaines étapes:")
        print("   1. Lancer une sync: python3 modules/sync_gazelle/sync_to_supabase.py")
        print("   2. Vérifier les logs: Dashboard → Notifications → Tâches & Imports")
        print("   3. Valider données UTC: SELECT start_datetime FROM gazelle_appointments LIMIT 5;")
    elif not results['start_datetime_exists']:
        print("⚠️  MIGRATION REQUISE!")
        print()
        print("🔧 Exécutez la migration SQL:")
        print("   Fichier: scripts/migrations/add_start_datetime_to_appointments.sql")
        print("   Méthode: Dashboard Supabase → SQL Editor → Run")
    elif not results['upsert_works']:
        print("❌ PROBLÈME DE CLÉ PRIMAIRE!")
        print()
        print("⚠️  external_id n'est pas une clé unique")
        print("   Vérifiez le schéma de la table dans Supabase")

    print()
    print("=" * 70)

    return results


if __name__ == '__main__':
    validate_table_structure()
