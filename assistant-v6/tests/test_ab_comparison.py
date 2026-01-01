#!/usr/bin/env python3
"""
Test A/B: Comparaison v5 vs v6

Script pour tester les mêmes questions sur v5 et v6 et comparer les résultats.

Usage:
    python test_ab_comparison.py
"""

import os
import sys
import requests
from typing import Dict, Any, List
from datetime import datetime

# Configuration
V5_URL = "http://localhost:8000/assistant/chat"
V6_URL = "http://localhost:8001/v6/assistant/chat"

# Questions de test
TEST_QUESTIONS = [
    "montre-moi l'historique complet de Monique Hallé avec toutes les notes de service",
    "trouve Michelle Alie",
    "mes rv demain",
    "historique de Jean-Philippe Gagné",
    "cherche Allan Sutton",
]


def test_question(question: str, url: str, version: str) -> Dict[str, Any]:
    """
    Teste une question sur un endpoint.

    Args:
        question: Question à tester
        url: URL de l'endpoint
        version: Version (v5 ou v6)

    Returns:
        Résultats du test
    """
    print(f"\n{'='*80}")
    print(f"🧪 Test {version}: {question}")
    print(f"{'='*80}")

    start_time = datetime.now()

    try:
        response = requests.post(
            url,
            json={"question": question},
            timeout=30
        )

        elapsed = (datetime.now() - start_time).total_seconds()

        if response.status_code == 200:
            data = response.json()

            print(f"✅ {version} - Succès ({elapsed:.2f}s)")
            print(f"\n📝 Réponse:")
            print(data.get('response', 'N/A')[:500])  # Limiter à 500 chars

            return {
                'version': version,
                'question': question,
                'success': True,
                'elapsed': elapsed,
                'response': data.get('response'),
                'data': data.get('data', {}),
                'status_code': response.status_code
            }
        else:
            print(f"❌ {version} - Erreur {response.status_code}")
            print(f"   {response.text[:200]}")

            return {
                'version': version,
                'question': question,
                'success': False,
                'elapsed': elapsed,
                'error': response.text,
                'status_code': response.status_code
            }

    except requests.exceptions.ConnectionError:
        print(f"❌ {version} - Serveur non accessible à {url}")
        return {
            'version': version,
            'question': question,
            'success': False,
            'error': 'Serveur non accessible',
            'status_code': 0
        }

    except Exception as e:
        print(f"❌ {version} - Erreur: {e}")
        return {
            'version': version,
            'question': question,
            'success': False,
            'error': str(e),
            'status_code': 0
        }


def compare_results(results_v5: Dict[str, Any], results_v6: Dict[str, Any]):
    """
    Compare les résultats v5 vs v6.

    Args:
        results_v5: Résultats v5
        results_v6: Résultats v6
    """
    print(f"\n{'='*80}")
    print(f"📊 COMPARAISON v5 vs v6")
    print(f"{'='*80}")

    # Temps de réponse
    if results_v5['success'] and results_v6['success']:
        t5 = results_v5['elapsed']
        t6 = results_v6['elapsed']
        print(f"\n⏱️  Temps de réponse:")
        print(f"   v5: {t5:.2f}s")
        print(f"   v6: {t6:.2f}s")
        print(f"   Différence: {abs(t5-t6):.2f}s ({'v6 plus rapide' if t6 < t5 else 'v5 plus rapide'})")

    # Type de résultat
    if results_v5['success'] and results_v6['success']:
        type_v5 = results_v5.get('data', {}).get('type', 'unknown')
        type_v6 = results_v6.get('data', {}).get('type', 'unknown')

        print(f"\n🎯 Type détecté:")
        print(f"   v5: {type_v5}")
        print(f"   v6: {type_v6}")

        if type_v5 != type_v6:
            print(f"   ⚠️  DIFFÉRENCE DE DÉTECTION!")

    # Nombre de résultats
    if results_v5['success'] and results_v6['success']:
        count_v5 = results_v5.get('data', {}).get('count', 0)
        count_v6 = results_v6.get('data', {}).get('count', 0)

        if count_v5 or count_v6:
            print(f"\n📊 Nombre de résultats:")
            print(f"   v5: {count_v5}")
            print(f"   v6: {count_v6}")

            if count_v5 != count_v6:
                print(f"   ⚠️  DIFFÉRENCE DE RÉSULTATS!")

    # Statut
    print(f"\n✅ Succès:")
    print(f"   v5: {'Oui' if results_v5['success'] else 'Non'}")
    print(f"   v6: {'Oui' if results_v6['success'] else 'Non'}")


def run_ab_tests():
    """Lance tous les tests A/B"""
    print(f"{'='*80}")
    print(f"🚀 Tests A/B: v5 vs v6")
    print(f"{'='*80}")
    print(f"\nEndpoints:")
    print(f"   v5: {V5_URL}")
    print(f"   v6: {V6_URL}")
    print(f"\nQuestions: {len(TEST_QUESTIONS)}")
    print(f"{'='*80}")

    all_results = []

    for question in TEST_QUESTIONS:
        print(f"\n\n{'#'*80}")
        print(f"# Question: {question}")
        print(f"{'#'*80}")

        # Tester v5
        results_v5 = test_question(question, V5_URL, "v5")

        # Tester v6
        results_v6 = test_question(question, V6_URL, "v6")

        # Comparer
        compare_results(results_v5, results_v6)

        all_results.append({
            'question': question,
            'v5': results_v5,
            'v6': results_v6
        })

    # Résumé final
    print(f"\n\n{'='*80}")
    print(f"📋 RÉSUMÉ FINAL")
    print(f"{'='*80}")

    successes_v5 = sum(1 for r in all_results if r['v5']['success'])
    successes_v6 = sum(1 for r in all_results if r['v6']['success'])

    print(f"\nTaux de succès:")
    print(f"   v5: {successes_v5}/{len(TEST_QUESTIONS)} ({successes_v5/len(TEST_QUESTIONS)*100:.0f}%)")
    print(f"   v6: {successes_v6}/{len(TEST_QUESTIONS)} ({successes_v6/len(TEST_QUESTIONS)*100:.0f}%)")

    # Temps moyen
    avg_v5 = sum(r['v5']['elapsed'] for r in all_results if r['v5']['success']) / max(successes_v5, 1)
    avg_v6 = sum(r['v6']['elapsed'] for r in all_results if r['v6']['success']) / max(successes_v6, 1)

    print(f"\nTemps moyen:")
    print(f"   v5: {avg_v5:.2f}s")
    print(f"   v6: {avg_v6:.2f}s")

    print(f"\n{'='*80}")


if __name__ == "__main__":
    run_ab_tests()
