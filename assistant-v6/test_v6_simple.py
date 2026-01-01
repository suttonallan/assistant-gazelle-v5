#!/usr/bin/env python3
"""
Test simple v6 avec vues - charge le .env parent
"""

import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Charger le .env du projet parent (assistant-gazelle-v5)
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

print(f"✅ .env chargé depuis: {env_path}")
print(f"   SUPABASE_URL: {os.getenv('SUPABASE_URL', 'NON DÉFINI')[:40]}...")

# Ajouter au path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from modules.assistant.services.queries_v6_with_views import QueriesServiceV6WithViews

if __name__ == "__main__":
    print("\n" + "="*80)
    print("🧪 TEST: Assistant v6 avec Vues SQL Gazelle")
    print("="*80)

    service = QueriesServiceV6WithViews()

    # Test: Historique Monique Hallé
    result = service.execute_query(
        "montre-moi l'historique complet de Monique Hallé",
        debug=True
    )

    print("\n" + "="*80)
    print("📊 RÉSULTAT FINAL")
    print("="*80)
    print(f"Type: {result.get('type')}")
    print(f"Client: {result.get('client_name')}")
    print(f"Pianos: {result.get('piano_count')}")
    print(f"Entrées timeline: {result.get('count')} / {result.get('total')}")

    if result.get('entries'):
        print(f"\n📋 Aperçu des 5 premières entrées:")
        for i, entry in enumerate(result['entries'][:5], 1):
            date = entry.get('entry_date', 'N/A')
            title = entry.get('title', '(sans titre)')[:60]
            print(f"   {i}. [{date}] {title}")

    print("\n" + "="*80)
    print("✅ TEST RÉUSSI!")
    print("="*80)
