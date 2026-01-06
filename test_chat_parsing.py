#!/usr/bin/env python3
"""
Test rapide du parsing intelligent des notes du Chat Technicien.

Usage: python3 test_chat_parsing.py
"""

import sys
sys.path.insert(0, '/Users/allansutton/Documents/assistant-gazelle-v5')

from api.chat.service import V5DataProvider
from core.supabase_storage import SupabaseStorage

def test_comfort_info_parsing():
    """Test l'extraction des infos confort depuis notes."""

    storage = SupabaseStorage()
    provider = V5DataProvider(storage)

    # Note test complète
    test_note = """
    Chien: Max (Labrador)
    Code porte: 1234#
    Parking arrière du bâtiment
    3e étage
    Accord: 442 Hz
    Attention: touche F#3 fragile
    Client parle anglais seulement
    Tempérament: Très sympathique
    """

    # Simuler un appointment brut
    apt_raw = {
        "notes": test_note,
        "client": {
            "first_name": "John",
            "phone": "514-555-1234",
            "email": "john@example.com"
        }
    }

    # Extraire les infos confort
    comfort = provider._map_to_comfort_info(apt_raw)

    # Tests d'assertion
    print("🧪 Test Parsing Infos Confort\n")
    print(f"✓ Chien: {comfort.dog_name} ({comfort.dog_breed})")
    assert comfort.dog_name == "Max", f"Attendu 'Max', obtenu '{comfort.dog_name}'"
    assert comfort.dog_breed == "Labrador", f"Attendu 'Labrador', obtenu '{comfort.dog_breed}'"

    print(f"✓ Code d'accès: {comfort.access_code}")
    assert comfort.access_code == "1234#", f"Attendu '1234#', obtenu '{comfort.access_code}'"

    print(f"✓ Stationnement: {comfort.parking_info}")
    assert "arrière" in comfort.parking_info.lower(), f"Parking info incorrect: {comfort.parking_info}"

    print(f"✓ Étage: {comfort.floor_number}")
    assert comfort.floor_number == "3", f"Attendu '3', obtenu '{comfort.floor_number}'"

    print(f"✓ Accordage: {comfort.preferred_tuning_hz} Hz")
    assert comfort.preferred_tuning_hz == 442, f"Attendu 442, obtenu {comfort.preferred_tuning_hz}"

    print(f"✓ Langue: {comfort.preferred_language}")
    assert comfort.preferred_language == "Anglais", f"Attendu 'Anglais', obtenu '{comfort.preferred_language}'"

    print(f"✓ Tempérament: {comfort.temperament}")
    assert comfort.temperament == "Sympathique", f"Attendu 'Sympathique', obtenu '{comfort.temperament}'"

    print(f"✓ Notes spéciales: {comfort.special_notes[:50]}...")
    assert "fragile" in comfort.special_notes.lower(), f"Notes spéciales incorrectes"

    print(f"\n✅ Tous les tests passés!")
    print(f"\n📊 Résultat ComfortInfo:")
    print(f"   - Contact: {comfort.contact_name}")
    print(f"   - Téléphone: {comfort.contact_phone}")
    print(f"   - 🐕 Chien: {comfort.dog_name} ({comfort.dog_breed})")
    print(f"   - 🔑 Code: {comfort.access_code}")
    print(f"   - 🅿️ Parking: {comfort.parking_info}")
    print(f"   - 🏢 Étage: {comfort.floor_number}")
    print(f"   - 🎵 Accordage: {comfort.preferred_tuning_hz} Hz")
    print(f"   - 🌍 Langue: {comfort.preferred_language}")
    print(f"   - 😊 Tempérament: {comfort.temperament}")
    print(f"   - ⚠️ Notes: {comfort.special_notes}")

if __name__ == "__main__":
    try:
        test_comfort_info_parsing()
    except AssertionError as e:
        print(f"\n❌ Test échoué: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
