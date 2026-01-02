#!/usr/bin/env python3
"""
Script pour lister tous les événements créés pour un piano spécifique
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.gazelle_api_client import GazelleAPIClient

TEST_PIANO_ID = "ins_9H7Mh59SXwEs2JxL"

def list_events_for_piano(api_client, piano_id):
    """Lister tous les événements associés à un piano"""
    print("="*60)
    print(f"📋 LISTE DES ÉVÉNEMENTS POUR LE PIANO {piano_id}")
    print("="*60)
    
    # Récupérer les événements des 30 derniers jours
    start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    end_date = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
    
    print(f"\n🔍 Recherche d'événements du {start_date} au {end_date}...")
    
    try:
        events = api_client.get_appointments(
            limit=200,
            start_date_override=start_date
        )
        
        # Filtrer pour ce piano
        piano_events = []
        for event in events:
            event_pianos = event.get('allEventPianos', {}).get('nodes', [])
            for ep in event_pianos:
                piano_node = ep.get('piano', {})
                if piano_node and piano_node.get('id') == piano_id:
                    piano_events.append(event)
                    break
        
        print(f"\n✅ {len(piano_events)} événement(s) trouvé(s) pour ce piano")
        
        if piano_events:
            print("\n📅 Événements récents:")
            for i, event in enumerate(piano_events, 1):
                print(f"\n{i}. {event.get('title', 'N/A')}")
                print(f"   ID: {event.get('id')}")
                print(f"   Date: {event.get('start', 'N/A')}")
                print(f"   Type: {event.get('type', 'N/A')}")
                print(f"   Statut: {event.get('status', 'N/A')}")
                notes = event.get('notes', '')
                if notes:
                    print(f"   Notes: {notes[:100]}...")
                user = event.get('user', {})
                if user:
                    print(f"   Technicien: {user.get('id')}")
        
        return piano_events
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return []

def main():
    print("🔍 LISTE DES ÉVÉNEMENTS CRÉÉS")
    print("="*60)
    
    api_client = GazelleAPIClient()
    
    events = list_events_for_piano(api_client, TEST_PIANO_ID)
    
    print("\n" + "="*60)
    print(f"📊 TOTAL: {len(events)} événement(s)")
    print("="*60)
    
    if len(events) > 5:
        print("\n⚠️  ATTENTION: Plusieurs événements de test ont été créés.")
        print("   Vous pouvez les supprimer manuellement dans Gazelle si nécessaire.")

if __name__ == "__main__":
    main()

