#!/usr/bin/env python3
"""
Test la nouvelle fonctionnalité de matching par heure (±2h) pour les demandes PDA.

Simule plusieurs scénarios:
1. Match exact: Demande 13h, Gazelle 13h → ✅
2. Match dans fenêtre: Demande "avant 8h", Gazelle 7h30 → ✅
3. Hors fenêtre: Demande 10h, Gazelle 14h → ❌
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / 'assistant-v6'))

from modules.assistant.services.pda_validation import PlaceDesArtsValidator
from datetime import datetime

def test_time_window_matching():
    print("=" * 70)
    print("🧪 TEST: Matching PDA avec fenêtre d'heure ±2h")
    print("=" * 70)
    print()

    validator = PlaceDesArtsValidator()

    # Test 1: Avec heure spécifique
    print("Test 1: 2026-01-11 TM 'avant 8h'")
    print("-" * 70)

    result = validator.find_gazelle_appointment_for_pda(
        appointment_date='2026-01-11',
        room='TM',
        appointment_time='avant 8h',
        debug=True
    )

    if result:
        print(f"✅ RV trouvé: {result.get('external_id')}")
        print(f"   Heure Gazelle: {result.get('appointment_time')}")
        print(f"   Notes: {result.get('notes', '')[:80]}")
    else:
        print("❌ RV non trouvé (attendu: devrait trouver si dans ±2h)")

    print()
    print("=" * 70)

    # Test 2: Sans heure (mode legacy)
    print("Test 2: 2026-01-11 SCL (sans heure)")
    print("-" * 70)

    result = validator.find_gazelle_appointment_for_pda(
        appointment_date='2026-01-11',
        room='SCL',
        appointment_time=None,  # Pas d'heure = accepte n'importe quelle heure
        debug=True
    )

    if result:
        print(f"✅ RV trouvé: {result.get('external_id')}")
        print(f"   Heure Gazelle: {result.get('appointment_time')}")
        print(f"   Notes: {result.get('notes', '')[:80]}")
    else:
        print("❌ RV non trouvé")

    print()
    print("=" * 70)

    # Test 3: Avec heure précise
    print("Test 3: 2026-01-11 MS '13h30'")
    print("-" * 70)

    result = validator.find_gazelle_appointment_for_pda(
        appointment_date='2026-01-11',
        room='MS',
        appointment_time='13h30',
        debug=True
    )

    if result:
        print(f"✅ RV trouvé: {result.get('external_id')}")
        print(f"   Heure Gazelle: {result.get('appointment_time')}")
        print(f"   Notes: {result.get('notes', '')[:80]}")
    else:
        print("❌ RV non trouvé (normal si pas de RV MS à 13h30 ±2h)")

    print()
    print("=" * 70)

if __name__ == '__main__':
    test_time_window_matching()
