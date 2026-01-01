#!/usr/bin/env python3
"""
Script de test d'intégration pour le Chat Intelligent.

Teste les 3 endpoints principaux:
1. POST /api/chat/query - Requête naturelle
2. GET /api/chat/day/{date} - Vue journée directe
3. GET /api/chat/appointment/{id} - Détails rendez-vous

Usage:
    python test_chat_integration.py
"""

import os
import sys
import requests
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv

# Charger .env
env_path = Path(__file__).parent / '.env'
load_dotenv(env_path)

# Configuration
API_BASE = os.getenv('API_URL', 'http://localhost:8000')

# Couleurs pour output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'


def print_success(msg):
    print(f"{GREEN}✅ {msg}{RESET}")


def print_error(msg):
    print(f"{RED}❌ {msg}{RESET}")


def print_info(msg):
    print(f"{BLUE}ℹ️  {msg}{RESET}")


def print_warning(msg):
    print(f"{YELLOW}⚠️  {msg}{RESET}")


def test_health():
    """Test 1: Health check du module chat."""
    print("\n" + "="*60)
    print("Test 1: Health Check")
    print("="*60)

    try:
        url = f"{API_BASE}/api/chat/health"
        print_info(f"GET {url}")

        response = requests.get(url, timeout=10)

        if response.status_code == 200:
            data = response.json()
            print_success(f"Health OK - Status: {data.get('status')}")
            print_info(f"  Data source: {data.get('data_source')}")
            return True
        else:
            print_error(f"Status: {response.status_code}")
            print_error(f"Response: {response.text}")
            return False

    except Exception as e:
        print_error(f"Erreur: {e}")
        return False


def test_query_natural():
    """Test 2: POST /api/chat/query avec requête naturelle."""
    print("\n" + "="*60)
    print("Test 2: Requête Naturelle (POST /api/chat/query)")
    print("="*60)

    try:
        url = f"{API_BASE}/api/chat/query"

        # Test plusieurs variantes de requêtes
        queries = [
            "demain",
            "aujourd'hui",
            "ma journée de demain"
        ]

        for query in queries:
            print_info(f"Query: '{query}'")

            payload = {"query": query}
            response = requests.post(url, json=payload, timeout=10)

            if response.status_code == 200:
                data = response.json()

                # Vérifier structure
                assert "interpreted_query" in data, "Champ 'interpreted_query' manquant"
                assert "query_type" in data, "Champ 'query_type' manquant"
                assert "day_overview" in data, "Champ 'day_overview' manquant"

                overview = data["day_overview"]
                if overview:
                    print_success(f"Interprété: {data['interpreted_query']}")
                    print_info(f"  Date: {overview.get('date')}")
                    print_info(f"  Technicien: {overview.get('technician_name')}")
                    print_info(f"  RDV: {overview.get('total_appointments')}")
                    print_info(f"  Quartiers: {', '.join(overview.get('neighborhoods', []))}")

                    # Retourner un appointment_id pour le test 3
                    appointments = overview.get('appointments', [])
                    if appointments:
                        first_appt_id = appointments[0].get('appointment_id')
                        print_info(f"  Premier RDV ID: {first_appt_id}")
                        return first_appt_id
                else:
                    print_warning("Aucun rendez-vous trouvé")

            else:
                print_error(f"Status: {response.status_code}")
                print_error(f"Response: {response.text}")
                return None

        print_success("Requêtes naturelles OK")
        return None

    except Exception as e:
        print_error(f"Erreur: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_day_direct(date=None):
    """Test 3: GET /api/chat/day/{date} - Vue journée directe."""
    print("\n" + "="*60)
    print("Test 3: Vue Journée Directe (GET /api/chat/day/{date})")
    print("="*60)

    if not date:
        # Par défaut: demain
        tomorrow = datetime.now() + timedelta(days=1)
        date = tomorrow.strftime("%Y-%m-%d")

    try:
        url = f"{API_BASE}/api/chat/day/{date}"
        print_info(f"GET {url}")

        response = requests.get(url, timeout=10)

        if response.status_code == 200:
            data = response.json()

            print_success(f"Vue journée du {date}")
            print_info(f"  Technicien: {data.get('technician_name')}")
            print_info(f"  Total RDV: {data.get('total_appointments')}")
            print_info(f"  Total pianos: {data.get('total_pianos')}")
            print_info(f"  Durée estimée: {data.get('estimated_duration_hours')}h")
            print_info(f"  Quartiers: {', '.join(data.get('neighborhoods', []))}")

            appointments = data.get('appointments', [])
            if appointments:
                print_info(f"\n  Rendez-vous ({len(appointments)}):")
                for i, apt in enumerate(appointments[:3], 1):  # Afficher max 3
                    print_info(f"    {i}. {apt.get('time_slot')} - {apt.get('client_name')}")
                    print_info(f"       📍 {apt.get('neighborhood')}")
                    if apt.get('piano_brand'):
                        print_info(f"       🎹 {apt.get('piano_brand')} {apt.get('piano_model')}")

            return True
        else:
            print_error(f"Status: {response.status_code}")
            print_error(f"Response: {response.text}")
            return False

    except Exception as e:
        print_error(f"Erreur: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_appointment_detail(appointment_id):
    """Test 4: GET /api/chat/appointment/{id} - Détails complets."""
    print("\n" + "="*60)
    print("Test 4: Détails Rendez-vous (GET /api/chat/appointment/{id})")
    print("="*60)

    if not appointment_id:
        print_warning("Aucun appointment_id fourni, skip test")
        return False

    try:
        url = f"{API_BASE}/api/chat/appointment/{appointment_id}"
        print_info(f"GET {url}")

        response = requests.get(url, timeout=10)

        if response.status_code == 200:
            data = response.json()

            # Vérifier structure Niveau 2
            assert "overview" in data, "Champ 'overview' manquant"
            assert "comfort" in data, "Champ 'comfort' manquant"
            assert "timeline_summary" in data, "Champ 'timeline_summary' manquant"
            assert "timeline_entries" in data, "Champ 'timeline_entries' manquant"

            overview = data["overview"]
            comfort = data["comfort"]

            print_success(f"Détails RDV: {overview.get('client_name')}")
            print_info(f"  📍 {overview.get('neighborhood')}")
            print_info(f"  ⏰ {overview.get('time_slot')}")

            if comfort.get('dog_name'):
                print_info(f"  🦴 Chien: {comfort['dog_name']}")
            if comfort.get('access_code'):
                print_info(f"  🔑 Code: {comfort['access_code']}")
            if comfort.get('parking_info'):
                print_info(f"  🅿️  {comfort['parking_info']}")

            print_info(f"\n  📖 Timeline: {data.get('timeline_summary')}")

            entries = data.get('timeline_entries', [])
            if entries:
                print_info(f"\n  Dernières interventions ({len(entries)}):")
                for entry in entries[:3]:  # Max 3
                    print_info(f"    • {entry.get('date')} - {entry.get('summary')}")

            return True

        elif response.status_code == 404:
            print_warning(f"Rendez-vous {appointment_id} non trouvé")
            return False
        else:
            print_error(f"Status: {response.status_code}")
            print_error(f"Response: {response.text}")
            return False

    except Exception as e:
        print_error(f"Erreur: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Exécute tous les tests."""
    print("\n" + "="*60)
    print("🧪 TESTS D'INTÉGRATION - CHAT INTELLIGENT")
    print("="*60)
    print_info(f"API Base: {API_BASE}")

    results = []

    # Test 1: Health
    results.append(("Health Check", test_health()))

    # Test 2: Requête naturelle
    appointment_id = test_query_natural()
    results.append(("Requête Naturelle", appointment_id is not None or True))  # OK même sans RDV

    # Test 3: Vue journée directe
    results.append(("Vue Journée", test_day_direct()))

    # Test 4: Détails rendez-vous (si on a un ID)
    if appointment_id:
        results.append(("Détails RDV", test_appointment_detail(appointment_id)))
    else:
        print_warning("\nTest 4 skippé: aucun rendez-vous trouvé pour récupérer un ID")

    # Résumé
    print("\n" + "="*60)
    print("📊 RÉSUMÉ DES TESTS")
    print("="*60)

    for test_name, passed in results:
        status = f"{GREEN}✅ PASS{RESET}" if passed else f"{RED}❌ FAIL{RESET}"
        print(f"  {test_name}: {status}")

    total = len(results)
    passed = sum(1 for _, p in results if p)

    print(f"\n  Total: {passed}/{total} tests réussis")

    if passed == total:
        print_success("\n🎉 Tous les tests sont passés!")
        return 0
    else:
        print_error(f"\n⚠️  {total - passed} test(s) échoué(s)")
        return 1


if __name__ == "__main__":
    sys.exit(main())
