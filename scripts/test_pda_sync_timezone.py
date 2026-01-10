#!/usr/bin/env python3
"""
Test la correction timezone pour la synchronisation PDA.

Simule le cas:
- Demande PDA: 2026-01-11 TM "Gala Chinois"
- RV Gazelle: 2026-01-10T23:00:00Z (qui apparaît comme 2026-01-10 en date)
  MAIS c'est le même jour en timezone Montreal (18h EST = 23h UTC)
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / 'assistant-v6'))

from modules.assistant.services.pda_validation import PlaceDesArtsValidator
from datetime import datetime

def test_timezone_window():
    print("=" * 70)
    print("🧪 TEST: Correction Timezone - Fenêtre ±1 jour")
    print("=" * 70)
    print()

    validator = PlaceDesArtsValidator()

    # Test 1: 2026-01-11 TM
    print("Test 1: Recherche RV pour 2026-01-11 TM")
    print("-" * 70)

    result = validator.find_gazelle_appointment_for_pda(
        appointment_date='2026-01-11',
        room='TM',
        debug=True
    )

    if result:
        print(f"✅ RV trouvé: {result.get('external_id')}")
        print(f"   Date RV: {result.get('appointment_date')}")
        print(f"   Notes: {result.get('notes', '')[:80]}")
    else:
        print("❌ RV non trouvé")

    print()
    print("=" * 70)

    # Test 2: 2026-01-11 SCL
    print("Test 2: Recherche RV pour 2026-01-11 SCL")
    print("-" * 70)

    result = validator.find_gazelle_appointment_for_pda(
        appointment_date='2026-01-11',
        room='SCL',
        debug=True
    )

    if result:
        print(f"✅ RV trouvé: {result.get('external_id')}")
        print(f"   Date RV: {result.get('appointment_date')}")
        print(f"   Notes: {result.get('notes', '')[:80]}")
    else:
        print("❌ RV non trouvé")

    print()
    print("=" * 70)

if __name__ == '__main__':
    test_timezone_window()
