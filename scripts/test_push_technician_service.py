#!/usr/bin/env python3
"""
Script de test pour pushTechnicianService
Test avec le piano de test d'Allan
"""

import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.gazelle_api_client import GazelleAPIClient

# Piano de test d'Allan
TEST_PIANO_ID = "ins_9H7Mh59SXwEs2JxL"

# ID de Nick (technicien par défaut)
NICK_TECHNICIAN_ID = "usr_HcCiFk7o0vZ9xAI0"

def test_push_service():
    """Test: Créer un événement de service avec note de technicien"""
    print("="*60)
    print("🧪 TEST: pushTechnicianService")
    print("="*60)
    
    api_client = GazelleAPIClient()
    
    # Note de test spécifique
    technician_note = "Note test technicien : Accord effectué sur piano de garage"
    
    print(f"\n📝 Paramètres:")
    print(f"   Piano ID: {TEST_PIANO_ID}")
    print(f"   Technicien ID: {NICK_TECHNICIAN_ID} (Nick)")
    print(f"   Type de service: TUNING")
    print(f"   Note: {technician_note}")
    
    try:
        event = api_client.push_technician_service(
            piano_id=TEST_PIANO_ID,
            technician_note=technician_note,
            service_type="TUNING",
            technician_id=NICK_TECHNICIAN_ID
        )
        
        print(f"\n✅ Événement créé avec succès!")
        print(f"   Event ID: {event.get('id')}")
        print(f"   Titre: {event.get('title')}")
        print(f"   Date: {event.get('start')}")
        print(f"   Type: {event.get('type')}")
        print(f"   Statut: {event.get('status')}")
        print(f"   Notes: {event.get('notes', '')[:100]}...")
        
        # Vérifier l'auteur
        user = event.get('user', {})
        if user:
            print(f"   Technicien (user): {user.get('id')}")
            if user.get('id') == NICK_TECHNICIAN_ID:
                print(f"   ✅ Auteur correctement associé à Nick")
            else:
                print(f"   ⚠️  Auteur différent de Nick: {user.get('id')}")
        
        # Vérifier le piano associé
        event_pianos = event.get('allEventPianos', {}).get('nodes', [])
        if event_pianos:
            piano_ids = [p.get('piano', {}).get('id') for p in event_pianos if p.get('piano')]
            print(f"   Pianos associés: {piano_ids}")
            if TEST_PIANO_ID in piano_ids:
                print(f"   ✅ Piano correctement associé")
            else:
                print(f"   ⚠️  Piano non trouvé dans les pianos associés")
        
        return event
        
    except Exception as e:
        print(f"\n❌ Erreur lors de la création: {e}")
        import traceback
        traceback.print_exc()
        return None

def verify_timeline_entry(api_client, piano_id):
    """Vérifier que l'événement apparaît dans les timeline entries"""
    print("\n" + "="*60)
    print("🔍 VÉRIFICATION: Timeline Entries")
    print("="*60)
    
    try:
        # Récupérer les timeline entries récentes
        entries = api_client.get_timeline_entries(limit=10)
        
        # Filtrer pour ce piano
        piano_entries = []
        for e in entries:
            if not e:
                continue
            piano_node = e.get('piano')
            if piano_node and isinstance(piano_node, dict) and piano_node.get('id') == piano_id:
                piano_entries.append(e)
        
        print(f"\n📋 Timeline entries pour le piano {piano_id}: {len(piano_entries)}")
        
        if piano_entries:
            print("\n   Entrées récentes:")
            for i, entry in enumerate(piano_entries[:5], 1):
                print(f"\n   {i}. {entry.get('summary', 'N/A')}")
                print(f"      Date: {entry.get('occurredAt')}")
                print(f"      Type: {entry.get('type')}")
                print(f"      Commentaire: {entry.get('comment', '')[:80]}...")
                user = entry.get('user', {})
                if user:
                    print(f"      Technicien: {user.get('id')}")
        else:
            print("   ⚠️  Aucune timeline entry trouvée pour ce piano")
        
    except Exception as e:
        print(f"❌ Erreur lors de la vérification: {e}")

def main():
    print("🧪 TEST pushTechnicianService")
    print("="*60)
    
    api_client = GazelleAPIClient()
    
    # Test 1: Créer l'événement
    event = test_push_service()
    
    if event:
        # Test 2: Vérifier les timeline entries
        verify_timeline_entry(api_client, TEST_PIANO_ID)
        
        print("\n" + "="*60)
        print("✅ TEST TERMINÉ")
        print("="*60)
        print("\n💡 Vérifiez dans Gazelle:")
        print(f"   1. L'événement devrait apparaître dans l'historique du piano {TEST_PIANO_ID}")
        print(f"   2. La note devrait être visible: 'Note test technicien : Accord effectué sur piano de garage'")
        print(f"   3. L'auteur devrait être Nick (usr_HcCiFk7o0vZ9xAI0)")
    else:
        print("\n" + "="*60)
        print("❌ TEST ÉCHOUÉ")
        print("="*60)

if __name__ == "__main__":
    main()

