#!/usr/bin/env python3
"""
Script pour lister les événements de test créés récemment
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.gazelle_api_client import GazelleAPIClient

TEST_PIANO_ID = "ins_9H7Mh59SXwEs2JxL"

def list_recent_test_events(api_client):
    """Lister les événements de test créés aujourd'hui"""
    print("="*60)
    print("📋 ÉVÉNEMENTS DE TEST CRÉÉS RÉCEMMENT")
    print("="*60)
    
    # Récupérer les événements des dernières 24 heures
    start_date = datetime.now().strftime('%Y-%m-%d')
    
    print(f"\n🔍 Recherche d'événements depuis {start_date}...")
    
    try:
        events = api_client.get_appointments(
            limit=200,
            start_date_override=start_date
        )
        
        print(f"✅ {len(events)} événement(s) récupéré(s)")
        
        # Filtrer les événements de test (ceux avec "TUNING" ou "test" dans les notes/titre)
        test_events = []
        for event in events:
            notes = (event.get('notes', '') or '').lower()
            title = (event.get('title', '') or '').lower()
            
            # Chercher les événements de test
            if 'tuning' in notes and ('test' in notes or 'garage' in notes or 'note test' in notes):
                test_events.append(event)
        
        print(f"\n📊 {len(test_events)} événement(s) de test trouvé(s)\n")
        
        if test_events:
            print("📅 Liste des événements de test:")
            for i, event in enumerate(test_events, 1):
                print(f"\n{i}. {event.get('title', 'N/A')}")
                print(f"   ID: {event.get('id')}")
                print(f"   Date: {event.get('start', 'N/A')}")
                print(f"   Type: {event.get('type', 'N/A')}")
                print(f"   Statut: {event.get('status', 'N/A')}")
                notes = event.get('notes', '')
                if notes:
                    print(f"   Notes: {notes[:100]}...")
                
                # Vérifier les pianos associés
                event_pianos = event.get('allEventPianos', {})
                if event_pianos:
                    nodes = event_pianos.get('nodes', [])
                    if nodes:
                        piano_ids = [n.get('piano', {}).get('id') for n in nodes if n.get('piano')]
                        print(f"   Pianos associés: {piano_ids}")
                        if TEST_PIANO_ID in piano_ids:
                            print(f"   ✅ Piano de test trouvé!")
                    else:
                        print(f"   ⚠️  Aucun piano associé visible")
                else:
                    print(f"   ⚠️  Structure allEventPianos vide")
        
        return test_events
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return []

def main():
    print("🔍 RECHERCHE D'ÉVÉNEMENTS DE TEST")
    print("="*60)
    
    api_client = GazelleAPIClient()
    
    events = list_recent_test_events(api_client)
    
    print("\n" + "="*60)
    print(f"📊 TOTAL: {len(events)} événement(s) de test")
    print("="*60)
    
    if len(events) > 0:
        print("\n💡 Ces événements ont été créés lors des tests.")
        print("   Vous pouvez les supprimer manuellement dans Gazelle si nécessaire.")
        print("   Ou les garder comme historique de test.")

if __name__ == "__main__":
    main()




