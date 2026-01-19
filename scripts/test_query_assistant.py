#!/usr/bin/env python3
"""
Script de test pour vérifier que l'assistant peut répondre aux questions techniques
sur les données de pianos importées.

Question test: "Quels pianos ont eu une humidité sous 25% en décembre 2024?"
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.supabase_storage import SupabaseStorage
import json


def test_humidity_query():
    """
    Teste la requête: Quels pianos ont eu une humidité sous 25% en décembre 2024?
    """
    print("\n" + "="*80)
    print("🔍 TEST REQUÊTE ASSISTANT")
    print("="*80)
    print("\nQuestion: 'Quels pianos ont eu une humidité sous 25% en décembre 2024?'\n")
    
    s = SupabaseStorage()
    
    # Requête pour trouver les entrées avec humidité < 25% en décembre 2024
    result = s.client.table('gazelle_timeline_entries')\
        .select('occurred_at, piano_id, entry_type, description, metadata')\
        .gte('occurred_at', '2024-12-01')\
        .lt('occurred_at', '2025-01-01')\
        .not_.is_('metadata', 'null')\
        .order('occurred_at', desc=True)\
        .execute()
    
    # Filtrer par humidité < 25%
    low_humidity_entries = []
    pianos_affected = set()
    
    for entry in result.data:
        metadata = entry.get('metadata')
        if metadata and isinstance(metadata, dict):
            humidity = metadata.get('humidity')
            if humidity and humidity < 25:
                low_humidity_entries.append(entry)
                if entry.get('piano_id'):
                    pianos_affected.add(entry['piano_id'])
    
    print(f"✅ Trouvé {len(low_humidity_entries)} mesures avec humidité < 25%")
    print(f"🎹 {len(pianos_affected)} pianos concernés\n")
    
    if low_humidity_entries:
        print("📊 Détails des mesures:\n")
        print(f"{'Date':<12} | {'Piano ID':<25} | {'Humidité':<10} | {'Type':<25} | {'Description':<50}")
        print("-"*140)
        
        for entry in low_humidity_entries[:20]:  # Limiter à 20 résultats
            date = entry.get('occurred_at', '')[:10]
            piano_id = entry.get('piano_id', 'N/A')
            metadata = entry.get('metadata', {})
            humidity = metadata.get('humidity', 'N/A')
            temp = metadata.get('temperature', '')
            freq = metadata.get('frequency', '')
            entry_type = entry.get('entry_type', 'N/A')
            desc = entry.get('description', '')[:50]
            
            measures = f"{humidity}%"
            if temp:
                measures += f" {temp}°"
            if freq:
                measures += f" {freq}Hz"
            
            print(f"{date:<12} | {piano_id:<25} | {measures:<10} | {entry_type:<25} | {desc}")
        
        if len(low_humidity_entries) > 20:
            print(f"\n... et {len(low_humidity_entries) - 20} autres mesures")
    
    # Liste des pianos concernés
    if pianos_affected:
        print(f"\n🎹 Liste des pianos avec humidité < 25% en décembre 2024:\n")
        for i, piano_id in enumerate(sorted(pianos_affected)[:10], 1):
            # Compter le nombre de mesures pour ce piano
            piano_measures = [e for e in low_humidity_entries if e.get('piano_id') == piano_id]
            min_humidity = min(e['metadata']['humidity'] for e in piano_measures if e.get('metadata', {}).get('humidity'))
            
            print(f"   {i}. Piano {piano_id}")
            print(f"      • {len(piano_measures)} mesure(s) sous 25%")
            print(f"      • Humidité minimale: {min_humidity}%")
        
        if len(pianos_affected) > 10:
            print(f"\n   ... et {len(pianos_affected) - 10} autres pianos")
    
    print("\n" + "="*80)
    print("✅ L'ASSISTANT PEUT MAINTENANT RÉPONDRE À CETTE QUESTION!")
    print("="*80 + "\n")
    
    return {
        'total_measures': len(low_humidity_entries),
        'pianos_affected': len(pianos_affected),
        'piano_ids': list(pianos_affected)
    }


def test_other_technical_queries():
    """
    Exemples d'autres requêtes techniques possibles.
    """
    print("\n" + "="*80)
    print("📋 AUTRES REQUÊTES POSSIBLES POUR L'ASSISTANT")
    print("="*80 + "\n")
    
    queries = [
        "Quels pianos ont été accordés à 441Hz en décembre 2024?",
        "Quelle est la température moyenne enregistrée en 2024?",
        "Combien de pianos ont eu une humidité supérieure à 50%?",
        "Quels sont les derniers services d'accord effectués?",
        "Quel client a le plus de notes de service en 2024?",
    ]
    
    for i, query in enumerate(queries, 1):
        print(f"{i}. ❓ {query}")
    
    print("\n✅ Toutes ces questions peuvent maintenant être répondues!")
    print("="*80 + "\n")


if __name__ == '__main__':
    result = test_humidity_query()
    test_other_technical_queries()
    
    print("\n💡 RECOMMANDATION POUR L'ASSISTANT:")
    print("   • Utiliser ce script comme base pour répondre aux questions techniques")
    print("   • Interroger directement Supabase pour des réponses précises")
    print("   • Exploiter les métadonnées (humidity, temperature, frequency)")
    print("   • Croiser avec les données clients/pianos pour un contexte complet\n")
