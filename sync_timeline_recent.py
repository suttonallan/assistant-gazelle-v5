#!/usr/bin/env python3
"""
Sync rapide des timeline entries depuis septembre 2025.
"""

import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

from modules.sync_gazelle.sync_to_supabase import GazelleToSupabaseSync

if __name__ == "__main__":
    print("🔄 Sync Timeline Entries depuis 1er septembre 2025...")
    print("="*60)

    sync = GazelleToSupabaseSync()

    # Sync seulement timeline depuis septembre
    count = sync.sync_timeline_entries()

    print("="*60)
    print(f"✅ Sync terminé: {count} timeline entries synchronisées")
