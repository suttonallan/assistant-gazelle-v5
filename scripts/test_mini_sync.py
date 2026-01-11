#!/usr/bin/env python3
"""
Mini-sync de test - Vérifie que la sync incrémentale est rapide.

Critères de validation:
- Durée < 1 minute
- Nombre d'items < 50
"""

import sys
from pathlib import Path
from datetime import datetime
import time

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from modules.sync_gazelle.sync_to_supabase import GazelleToSupabaseSync

def main():
    print("=" * 70)
    print("🧪 TEST: Mini-Sync Incrémentale")
    print("=" * 70)
    print()
    print("Critères de validation:")
    print("  ✅ Durée < 1 minute")
    print("  ✅ Nombre d'items < 50")
    print()

    # Démarrer le timer
    start_time = time.time()

    try:
        # Initialiser le syncer en mode incrémental
        syncer = GazelleToSupabaseSync(incremental_mode=True)

        # Lancer la sync complète
        print("🚀 Démarrage de la sync incrémentale...")
        print()

        total_items = 0
        stats = {}

        # Sync clients
        clients_count = syncer.sync_clients()
        stats['clients'] = clients_count
        total_items += clients_count
        print(f"📋 Clients: {clients_count} items")

        # Sync pianos
        pianos_count = syncer.sync_pianos()
        stats['pianos'] = pianos_count
        total_items += pianos_count
        print(f"🎹 Pianos: {pianos_count} items")

        # Sync timeline (30 jours)
        timeline_count = syncer.sync_timeline_entries()
        stats['timeline'] = timeline_count
        total_items += timeline_count
        print(f"📖 Timeline: {timeline_count} items")

        # Sync appointments (7 jours)
        appointments_count = syncer.sync_appointments()
        stats['appointments'] = appointments_count
        total_items += appointments_count
        print(f"📅 Appointments: {appointments_count} items")

        # Sauvegarder last_sync_date
        syncer._save_last_sync_date(datetime.now())

        # Arrêter le timer
        duration = time.time() - start_time
        duration_seconds = int(duration)

        print()
        print("=" * 70)
        print("📊 RÉSULTATS")
        print("=" * 70)
        print()
        print(f"Durée: {duration_seconds} secondes ({duration_seconds // 60}m {duration_seconds % 60}s)")
        print(f"Total items: {total_items}")
        print()
        print("Détail par type:")
        for item_type, count in stats.items():
            print(f"  - {item_type}: {count}")
        print()

        # Validation
        print("=" * 70)
        print("✅ VALIDATION")
        print("=" * 70)
        print()

        success = True

        if duration < 60:
            print(f"✅ Durée < 1 minute ({duration_seconds}s)")
        else:
            print(f"❌ Durée >= 1 minute ({duration_seconds}s)")
            success = False

        if total_items < 50:
            print(f"✅ Nombre d'items < 50 ({total_items})")
        else:
            print(f"❌ Nombre d'items >= 50 ({total_items})")
            success = False

        print()

        if success:
            print("🎉 TEST RÉUSSI - La sync incrémentale fonctionne correctement!")
        else:
            print("⚠️  TEST ÉCHOUÉ - Vérifier les critères ci-dessus")

        print()

    except Exception as e:
        duration = time.time() - start_time
        print()
        print(f"❌ ERREUR après {int(duration)}s: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
