#!/usr/bin/env python3
"""
Test spécifique pour vérifier que pushTechnicianService fonctionne avec un piano INACTIF
"""

import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.gazelle_api_client import GazelleAPIClient

# Piano de test d'Allan (déjà INACTIF)
TEST_PIANO_ID = "ins_9H7Mh59SXwEs2JxL"
NICK_TECHNICIAN_ID = "usr_HcCiFk7o0vZ9xAI0"

def check_piano_status(api_client, piano_id):
    """Vérifier le statut du piano"""
    print("="*60)
    print("🔍 VÉRIFICATION: Statut du piano")
    print("="*60)
    
    query = """
    query GetPianoStatus($pianoId: String!) {
        piano(id: $pianoId) {
            id
            make
            model
            status
            client {
                id
                companyName
            }
        }
    }
    """
    
    try:
        result = api_client._execute_query(query, {"pianoId": piano_id})
        piano = result.get("data", {}).get("piano", {})
        
        if piano:
            status = piano.get("status", "UNKNOWN")
            print(f"✅ Piano trouvé:")
            print(f"   ID: {piano.get('id')}")
            print(f"   Marque: {piano.get('make', 'N/A')}")
            print(f"   Statut: {status}")
            print(f"   Client: {piano.get('client', {}).get('companyName', 'N/A')}")
            
            if status == "INACTIVE":
                print(f"\n   ⚠️  PIANO INACTIF - Test de l'écriture...")
            else:
                print(f"\n   ℹ️  Piano ACTIF")
            
            return status == "INACTIVE"
        else:
            print("❌ Piano non trouvé")
            return False
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return False

def test_push_to_inactive_piano(api_client, piano_id):
    """Test: Pousser une note vers un piano inactif"""
    print("\n" + "="*60)
    print("🧪 TEST: pushTechnicianService sur piano INACTIF")
    print("="*60)
    
    technician_note = f"Test piano inactif - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    
    print(f"\n📝 Paramètres:")
    print(f"   Piano ID: {piano_id}")
    print(f"   Statut: INACTIF")
    print(f"   Technicien: Nick ({NICK_TECHNICIAN_ID})")
    print(f"   Note: {technician_note}")
    
    try:
        event = api_client.push_technician_service(
            piano_id=piano_id,
            technician_note=technician_note,
            service_type="TUNING",
            technician_id=NICK_TECHNICIAN_ID
        )
        
        print(f"\n✅ SUCCÈS! Événement créé sur piano INACTIF")
        print(f"   Event ID: {event.get('id')}")
        print(f"   Statut événement: {event.get('status')}")
        print(f"   Notes: {event.get('notes', '')[:80]}...")
        
        # Vérifier que le piano est associé
        event_pianos = event.get('allEventPianos', {}).get('nodes', [])
        if event_pianos:
            piano_ids = [p.get('piano', {}).get('id') for p in event_pianos if p.get('piano')]
            if piano_id in piano_ids:
                print(f"   ✅ Piano INACTIF correctement associé à l'événement")
            else:
                print(f"   ⚠️  Piano non trouvé dans les pianos associés")
        
        return True
        
    except Exception as e:
        print(f"\n❌ ÉCHEC: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("🧪 TEST: pushTechnicianService avec piano INACTIF")
    print("="*60)
    
    api_client = GazelleAPIClient()
    
    # Étape 1: Vérifier le statut
    is_inactive = check_piano_status(api_client, TEST_PIANO_ID)
    
    if not is_inactive:
        print("\n⚠️  Le piano n'est pas INACTIF. Le test va quand même être effectué.")
    
    # Étape 2: Tester l'écriture
    success = test_push_to_inactive_piano(api_client, TEST_PIANO_ID)
    
    print("\n" + "="*60)
    if success:
        print("✅ TEST RÉUSSI: L'écriture fonctionne même avec un piano INACTIF")
    else:
        print("❌ TEST ÉCHOUÉ: L'écriture ne fonctionne pas avec un piano INACTIF")
    print("="*60)
    
    print("\n💡 Vérifiez dans Gazelle:")
    print(f"   1. L'événement devrait apparaître dans l'historique du piano {TEST_PIANO_ID}")
    print(f"   2. Même si le piano est INACTIF, l'événement devrait être visible")
    print(f"   3. La note du technicien devrait être présente")

if __name__ == "__main__":
    main()



