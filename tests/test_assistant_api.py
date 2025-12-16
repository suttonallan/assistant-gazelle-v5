#!/usr/bin/env python3
"""
Tests pour l'API Assistant Conversationnel.

Usage:
    python3 tests/test_assistant_api.py
"""

import sys
from pathlib import Path

# Ajouter le répertoire parent au path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

import requests
import json


BASE_URL = "http://localhost:8000"


def test_health():
    """Test du endpoint /assistant/health."""
    print("\n" + "="*60)
    print("TEST: /assistant/health")
    print("="*60)

    response = requests.get(f"{BASE_URL}/assistant/health")

    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")

    assert response.status_code == 200, f"Expected 200, got {response.status_code}"

    data = response.json()
    assert data['status'] in ['healthy', 'degraded'], "Invalid status"
    assert data['parser_loaded'], "Parser not loaded"
    assert data['queries_loaded'], "Queries not loaded"
    assert data['vector_search_loaded'], "Vector search not loaded"
    assert data['vector_index_size'] == 126519, f"Expected 126519, got {data['vector_index_size']}"

    print("✅ Test PASSED")


def test_chat_help():
    """Test de la commande .aide."""
    print("\n" + "="*60)
    print("TEST: /assistant/chat - Commande .aide")
    print("="*60)

    response = requests.post(
        f"{BASE_URL}/assistant/chat",
        json={"question": ".aide"}
    )

    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Query Type: {data['query_type']}")
    print(f"Confidence: {data['confidence']}")
    print(f"Answer (preview): {data['answer'][:200]}...")

    assert response.status_code == 200
    assert data['query_type'] == 'help'
    assert data['confidence'] == 1.0

    print("✅ Test PASSED")


def test_chat_appointments():
    """Test de la commande .mes rv."""
    print("\n" + "="*60)
    print("TEST: /assistant/chat - Commande .mes rv")
    print("="*60)

    response = requests.post(
        f"{BASE_URL}/assistant/chat",
        json={"question": ".mes rv"}
    )

    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Query Type: {data['query_type']}")
    print(f"Confidence: {data['confidence']}")
    print(f"Answer (preview): {data['answer'][:200]}...")

    assert response.status_code == 200
    assert data['query_type'] == 'appointments'
    assert data['confidence'] == 1.0

    print("✅ Test PASSED")


def test_chat_search():
    """Test de recherche avec termes."""
    print("\n" + "="*60)
    print("TEST: /assistant/chat - Recherche 'cherche Yamaha'")
    print("="*60)

    response = requests.post(
        f"{BASE_URL}/assistant/chat",
        json={"question": "cherche Yamaha"}
    )

    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Query Type: {data['query_type']}")
    print(f"Confidence: {data['confidence']}")
    print(f"Answer (preview): {data['answer'][:200]}...")

    assert response.status_code == 200
    # Devrait être search_client ou search_piano
    assert 'search' in data['query_type']

    print("✅ Test PASSED")


def test_chat_vector_search():
    """Test de recherche vectorielle (question non reconnue)."""
    print("\n" + "="*60)
    print("TEST: /assistant/chat - Recherche vectorielle")
    print("="*60)

    response = requests.post(
        f"{BASE_URL}/assistant/chat",
        json={"question": "Comment accorder un piano?"}
    )

    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Query Type: {data['query_type']}")
    print(f"Vector Search Used: {data.get('vector_search_used', False)}")

    if data.get('vector_search_used'):
        print(f"Number of vector results: {len(data.get('vector_results', []))}")
        if data.get('vector_results'):
            print(f"Best match similarity: {data['vector_results'][0]['similarity']:.2%}")

    print(f"Answer (preview): {data['answer'][:200]}...")

    assert response.status_code == 200

    print("✅ Test PASSED")


def run_all_tests():
    """Exécute tous les tests."""
    print("\n" + "="*60)
    print("🧪 TESTS ASSISTANT CONVERSATIONNEL API")
    print("="*60)

    try:
        # Vérifier que l'API est accessible
        response = requests.get(f"{BASE_URL}/health", timeout=2)
        if response.status_code != 200:
            print("❌ API non accessible. Démarrez d'abord l'API avec: python3 api/main.py")
            sys.exit(1)
    except requests.exceptions.ConnectionError:
        print("❌ API non accessible. Démarrez d'abord l'API avec: python3 api/main.py")
        sys.exit(1)

    tests = [
        test_health,
        test_chat_help,
        test_chat_appointments,
        test_chat_search,
        test_chat_vector_search
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"❌ Test FAILED: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print("\n" + "="*60)
    print(f"RÉSULTATS: {passed} passed, {failed} failed")
    print("="*60)

    if failed == 0:
        print("✅ Tous les tests ont réussi!")
    else:
        print(f"❌ {failed} test(s) échoué(s)")
        sys.exit(1)


if __name__ == "__main__":
    run_all_tests()
