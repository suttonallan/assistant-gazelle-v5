#!/usr/bin/env python3
"""
Script pour importer événements, pianos, clients depuis le 9 décembre 2024

Usage:
    python3 scripts/import_from_dec9.py
"""
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Ajouter le projet au path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from modules.sync_gazelle.sync_to_supabase import GazelleToSupabaseSync

print("="*70)
print("🚀 IMPORT DEPUIS LE 9 DÉCEMBRE 2024")
print("="*70)
print(f"   Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("="*70)

syncer = GazelleToSupabaseSync()

# 1. Clients (toujours tous les clients)
print("\n📋 1/4: Import Clients...")
clients_count = syncer.sync_clients()
print(f"✅ {clients_count} clients importés")

# 2. Pianos (toujours tous les pianos)
print("\n🎹 2/4: Import Pianos...")
pianos_count = syncer.sync_pianos()
print(f"✅ {pianos_count} pianos importés")

# 3. Timeline depuis le 9 décembre
# Note: sync_timeline_entries utilise une fenêtre de 30 jours par défaut
# Le 9 décembre 2024 est dans cette fenêtre (on est en janvier 2025)
print("\n📖 3/4: Import Timeline (événements)...")
print("   Note: Import des 30 derniers jours (inclut le 9 décembre)")
timeline_count = syncer.sync_timeline_entries()
print(f"✅ {timeline_count} événements timeline importés")

# 4. Appointments depuis le 9 décembre
print("\n📅 4/4: Import Appointments (rendez-vous) depuis le 9 décembre...")
appointments_count = syncer.sync_appointments(
    start_date_override='2024-12-09',
    force_historical=False
)
print(f"✅ {appointments_count} appointments importés")

print("\n" + "="*70)
print("✅ IMPORT TERMINÉ")
print("="*70)
print(f"   Clients: {clients_count}")
print(f"   Pianos: {pianos_count}")
print(f"   Timeline (événements): {timeline_count}")
print(f"   Appointments (rendez-vous): {appointments_count}")
print("="*70)
print("\n💡 Les prochaines synchronisations se feront automatiquement:")
print("   - 01:00 chaque jour: Sync complète (clients, pianos, timeline, appointments)")
print("   - 16:00 chaque jour: Sync appointments + alertes RV")
print()
