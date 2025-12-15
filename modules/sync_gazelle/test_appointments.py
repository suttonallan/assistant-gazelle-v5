#!/usr/bin/env python3
"""
Test de synchronisation appointments avec la requête V4.

Synchronise seulement les appointments (pas clients ni pianos) pour tester rapidement.
"""

import sys
import os

# Ajouter le dossier parent au path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from modules.sync_gazelle.sync_to_supabase import GazelleToSupabaseSync

def main():
    print("=" * 70)
    print("🧪 TEST SYNC APPOINTMENTS (Requête V4)")
    print("=" * 70)

    syncer = GazelleToSupabaseSync()

    try:
        # Test uniquement appointments
        syncer.sync_appointments()

        print("\n" + "=" * 70)
        print("✅ TEST TERMINÉ")
        print("=" * 70)
        print(f"\n📊 Résultats:")
        print(f"   • Appointments: {syncer.stats['appointments']['synced']} synchronisés, {syncer.stats['appointments']['errors']} erreurs")

    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
