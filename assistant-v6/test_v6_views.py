#!/usr/bin/env python3
"""
Test rapide de l'assistant v6 avec vues SQL
"""

import sys
import os

# Ajouter le dossier parent au path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from modules.assistant.services.queries_v6_with_views import QueriesServiceV6WithViews

if __name__ == "__main__":
    print("="*80)
    print("🧪 TEST: Assistant v6 avec Vues SQL Gazelle")
    print("="*80)

    service = QueriesServiceV6WithViews()

    # Test 1: Recherche Monique Hallé
    print("\n" + "="*80)
    print("TEST 1: Historique complet de Monique Hallé")
    print("="*80)

    result = service.execute_query(
        "montre-moi l'historique complet de Monique Hallé",
        debug=True
    )

    print("\n📊 RÉSULTAT:")
    print(f"   Type: {result.get('type')}")
    print(f"   Client: {result.get('client_name')}")
    print(f"   Pianos: {result.get('piano_count')}")
    print(f"   Entrées: {result.get('count')} / {result.get('total')}")

    if result.get('entries'):
        print(f"\n📋 Premières entrées:")
        for i, entry in enumerate(result['entries'][:5], 1):
            date = entry.get('entry_date', 'N/A')
            title = entry.get('title', 'N/A')
            print(f"   {i}. [{date}] {title}")

    print("\n" + "="*80)
    print("✅ Test terminé!")
    print("="*80)
