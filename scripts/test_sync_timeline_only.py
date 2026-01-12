#!/usr/bin/env python3
"""
Script pour tester uniquement la synchronisation de la timeline.
"""

import sys
from pathlib import Path
from datetime import datetime

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from modules.sync_gazelle.sync_to_supabase import GazelleToSupabaseSync

def main():
    print("=" * 80)
    print("TEST SYNCHRONISATION TIMELINE UNIQUEMENT")
    print("=" * 80)
    print()
    print("📅 Fenêtre: Depuis le 1er janvier 2026")
    print()

    try:
        sync = GazelleToSupabaseSync(incremental_mode=True)
        
        print("🚀 Démarrage synchronisation timeline...")
        print()
        
        result = sync.sync_timeline_entries()
        
        print()
        print("=" * 80)
        print(f"✅ RÉSULTAT: {result} entrées timeline synchronisées")
        print("=" * 80)
        print()
        
        return result

    except Exception as e:
        print(f"\n❌ ERREUR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
