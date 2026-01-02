#!/usr/bin/env python3
"""
Test: Create piano measurement for Yamatest piano from parsed service note.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.gazelle_api_client import GazelleAPIClient


def test_parse():
    """Test parsing various formats."""
    client = GazelleAPIClient()

    test_cases = [
        ("24c. 34%", {'temperature': 24, 'humidity': 34}),
        ("Temperature: 22°C, humidity: 45%", {'temperature': 22, 'humidity': 45}),
        ("test de entrée de service pour ce piano Yamatest G 24c. 34%",
         {'temperature': 24, 'humidity': 34}),
        ("Only text without measurements", None),
        ("Only temp 22°C", None),
        ("Only humidity 45%", None),
    ]

    print("\n" + "="*70)
    print("TEST: Parsing Temperature/Humidity")
    print("="*70 + "\n")

    all_pass = True
    for text, expected in test_cases:
        result = client.parse_temperature_humidity(text)
        status = "✅" if result == expected else "❌"
        if result != expected:
            all_pass = False
        print(f"{status} '{text[:50]}...' -> {result}")
        if result != expected:
            print(f"   Expected: {expected}")

    print("\n" + "="*70)
    if all_pass:
        print("✅ All parse tests passed!")
    else:
        print("❌ Some parse tests failed")
    print("="*70 + "\n")

    return all_pass


def test_create_measurement():
    """Test creating measurement for Yamatest piano."""
    client = GazelleAPIClient()

    piano_id = "ins_hUTnjvtZc6I6cXxA"  # Yamatest

    print("\n" + "="*70)
    print("TEST: Create Piano Measurement")
    print("="*70)
    print(f"Piano: {piano_id}")
    print(f"Temp:  24°C")
    print(f"Humid: 34%")
    print(f"Date:  2026-01-02")
    print("="*70 + "\n")

    try:
        measurement = client.create_piano_measurement(
            piano_id=piano_id,
            temperature=24,
            humidity=34,
            taken_on="2026-01-02"
        )

        print("✅ Measurement created successfully!")
        print(f"   ID:          {measurement['id']}")
        print(f"   Piano ID:    {measurement['pianoId']}")
        print(f"   Temperature: {measurement['temperature']}°C")
        print(f"   Humidity:    {measurement['humidity']}%")
        print(f"   Taken On:    {measurement['takenOn']}")

        print("\n" + "="*70)
        print("✅ Measurement creation test passed!")
        print("="*70 + "\n")

        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

        print("\n" + "="*70)
        print("❌ Measurement creation test failed")
        print("="*70 + "\n")

        return False


def test_full_workflow():
    """Test complete workflow: service note + measurement."""
    client = GazelleAPIClient()

    print("\n" + "="*70)
    print("TEST: Full Workflow (Service Note + Measurement)")
    print("="*70 + "\n")

    try:
        result = client.push_technician_service_with_measurements(
            piano_id="ins_hUTnjvtZc6I6cXxA",
            technician_note="test de entrée de service pour ce piano Yamatest G 24c. 34%",
            service_type="TUNING",
            technician_id="usr_HcCiFk7o0vZ9xAI0",  # Nick
            client_id="cli_PmqPUBTbPFeCMGmz",  # Orford Musique
        )

        print("\n" + "="*70)
        print("RESULTS")
        print("="*70)
        print(f"✅ Service note created:")
        print(f"   Event ID: {result['service_note']['id']}")

        if result['measurement']:
            print(f"\n✅ Measurement created:")
            print(f"   ID: {result['measurement']['id']}")
            print(f"   Values: {result['parsed_values']}")
        else:
            print(f"\n⚠️  No measurement created")
            print(f"   Parsed: {result['parsed_values']}")

        print("="*70)
        print("✅ Full workflow test passed!")
        print("="*70 + "\n")

        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

        print("\n" + "="*70)
        print("❌ Full workflow test failed")
        print("="*70 + "\n")

        return False


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('--test', choices=['parse', 'measurement', 'workflow', 'all'],
                       default='all', help='Which test to run')
    args = parser.parse_args()

    results = []

    if args.test in ['parse', 'all']:
        results.append(("Parse", test_parse()))

    if args.test in ['measurement', 'all']:
        results.append(("Measurement", test_create_measurement()))

    if args.test in ['workflow', 'all']:
        results.append(("Workflow", test_full_workflow()))

    # Summary
    if len(results) > 1:
        print("\n" + "="*70)
        print("TEST SUMMARY")
        print("="*70)
        for name, passed in results:
            status = "✅" if passed else "❌"
            print(f"{status} {name}")
        print("="*70 + "\n")
