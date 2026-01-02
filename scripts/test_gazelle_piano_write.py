#!/usr/bin/env python3
"""
Script de test pour vérifier l'écriture vers Gazelle:
- Créer une timeline entry (note de service)
- Mettre à jour last_tuned_date
- Tester avec piano actif et inactif
"""

import sys
import os
from pathlib import Path
from datetime import datetime

# Ajouter le parent au path pour les imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.gazelle_api_client import GazelleAPIClient

# Piano de test d'Allan
TEST_PIANO_ID = "ins_9H7Mh59SXwEs2JxL"

# IDs techniciens (IDs Gazelle)
TECHNICIAN_IDS = {
    "nick": "usr_HcCiFk7o0vZ9xAI0",
    "allan": "usr_ofYggsCDt2JAVeNP",
    "jp": "usr_ReUSmIJmBF86ilY1"
}

def test_read_piano(api_client, piano_id):
    """Test: Lire les détails d'un piano"""
    print(f"\n{'='*60}")
    print(f"📖 TEST 1: Lecture du piano {piano_id}")
    print(f"{'='*60}")
    
    try:
        query = """
        query GetPiano($pianoId: String!) {
            piano(id: $pianoId) {
                id
                make
                model
                serialNumber
                location
                status
                calculatedLastService
                calculatedNextService
                tags
            }
        }
        """
        
        variables = {"pianoId": piano_id}
        result = api_client._execute_query(query, variables)
        
        if not result:
            print("❌ Erreur: Aucun résultat retourné")
            return None
        
        piano_data = result.get("data", {}).get("piano")
        if not piano_data:
            print("❌ Erreur: Piano non trouvé")
            print(f"Résultat complet: {result}")
            return None
        
        print(f"✅ Piano trouvé:")
        print(f"   ID: {piano_data.get('id')}")
        print(f"   Marque: {piano_data.get('make', 'N/A')}")
        print(f"   Modèle: {piano_data.get('model', 'N/A')}")
        print(f"   Série: {piano_data.get('serialNumber', 'N/A')}")
        print(f"   Localisation: {piano_data.get('location', 'N/A')}")
        print(f"   Statut: {piano_data.get('status', 'N/A')}")
        print(f"   Calculé dernier service: {piano_data.get('calculatedLastService', 'N/A')}")
        print(f"   Calculé prochain service: {piano_data.get('calculatedNextService', 'N/A')}")
        print(f"   Tags: {piano_data.get('tags', [])}")
        
        is_active = piano_data.get('status') != 'INACTIVE'
        print(f"   ⚠️  Piano {'ACTIF' if is_active else 'INACTIF'}")
        
        return piano_data
        
    except Exception as e:
        print(f"❌ Erreur lors de la lecture: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_create_timeline_entry(api_client, piano_id, technician_id):
    """Test: Créer une timeline entry"""
    print(f"\n{'='*60}")
    print(f"📝 TEST 2: Création d'une timeline entry")
    print(f"{'='*60}")
    
    try:
        summary = "Test - Accord de vérification"
        comment = f"Note de test créée le {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} pour vérifier l'écriture vers Gazelle."
        
        print(f"Piano ID: {piano_id}")
        print(f"Technicien ID: {technician_id}")
        print(f"Summary: {summary}")
        print(f"Comment: {comment}")
        
        timeline_entry = api_client.create_timeline_entry(
            piano_id=piano_id,
            summary=summary,
            comment=comment,
            technician_id=technician_id
        )
        
        print(f"\n✅ Timeline entry créée avec succès!")
        print(f"   Entry ID: {timeline_entry.get('id')}")
        print(f"   Date: {timeline_entry.get('occurredAt')}")
        print(f"   Type: {timeline_entry.get('type')}")
        print(f"   Summary: {timeline_entry.get('summary')}")
        print(f"   Comment: {timeline_entry.get('comment', '')[:100]}...")
        
        return timeline_entry
        
    except Exception as e:
        print(f"❌ Erreur lors de la création de timeline entry: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_update_last_tuned_date(api_client, piano_id):
    """Test: Mettre à jour last_tuned_date"""
    print(f"\n{'='*60}")
    print(f"📅 TEST 3: Mise à jour de last_tuned_date")
    print(f"{'='*60}")
    
    try:
        today = datetime.now().date().isoformat()
        print(f"Date à définir: {today}")
        
        updated_piano = api_client.update_piano_last_tuned_date(
            piano_id=piano_id,
            last_tuned_date=today
        )
        
        print(f"\n✅ Piano mis à jour avec succès!")
        print(f"   Piano ID: {updated_piano.get('id')}")
        print(f"   lastTunedDate: {updated_piano.get('lastTunedDate')}")
        print(f"   calculatedLastService: {updated_piano.get('calculatedLastService', 'N/A')}")
        
        return updated_piano
        
    except Exception as e:
        print(f"❌ Erreur lors de la mise à jour: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_with_inactive_piano(api_client):
    """Test: Chercher un piano inactif et tester l'écriture"""
    print(f"\n{'='*60}")
    print(f"🔍 TEST 4: Recherche d'un piano inactif")
    print(f"{'='*60}")
    
    try:
        # Chercher tous les pianos du client pour trouver un inactif
        query = """
        query GetPianos($clientId: String!) {
            allPianos(first: 50, filters: { clientId: $clientId }) {
                nodes {
                    id
                    make
                    model
                    status
                    location
                }
            }
        }
        """
        
        # Utiliser le client ID de Vincent d'Indy (ou celui configuré)
        client_id = os.getenv("GAZELLE_CLIENT_ID_VDI") or "cli_VOTRE_ID"
        variables = {"clientId": client_id}
        
        result = api_client._execute_query(query, variables)
        pianos = result.get("data", {}).get("allPianos", {}).get("nodes", [])
        
        inactive_pianos = [p for p in pianos if p.get('status') == 'INACTIVE']
        
        if not inactive_pianos:
            print("⚠️  Aucun piano inactif trouvé. Test avec le piano de test...")
            return None
        
        inactive_piano = inactive_pianos[0]
        print(f"✅ Piano inactif trouvé:")
        print(f"   ID: {inactive_piano.get('id')}")
        print(f"   Marque: {inactive_piano.get('make', 'N/A')}")
        print(f"   Statut: {inactive_piano.get('status')}")
        
        # Tester l'écriture sur ce piano inactif
        print(f"\n🧪 Test d'écriture sur piano inactif...")
        inactive_id = inactive_piano.get('id')
        
        # Test timeline entry
        try:
            timeline = api_client.create_timeline_entry(
                piano_id=inactive_id,
                summary="Test - Piano inactif",
                comment="Test d'écriture sur piano inactif",
                technician_id=TECHNICIAN_IDS["allan"]
            )
            print(f"✅ Timeline entry créée sur piano inactif: {timeline.get('id')}")
        except Exception as e:
            print(f"❌ Erreur timeline entry sur piano inactif: {e}")
        
        # Test last_tuned_date
        try:
            updated = api_client.update_piano_last_tuned_date(inactive_id)
            print(f"✅ last_tuned_date mis à jour sur piano inactif: {updated.get('lastTunedDate')}")
        except Exception as e:
            print(f"❌ Erreur last_tuned_date sur piano inactif: {e}")
        
        return inactive_piano
        
    except Exception as e:
        print(f"❌ Erreur lors de la recherche: {e}")
        import traceback
        traceback.print_exc()
        return None

def main():
    print("🧪 TEST D'ÉCRITURE VERS GAZELLE")
    print("=" * 60)
    
    try:
        # Initialiser le client API
        print("\n🔌 Initialisation du client API Gazelle...")
        api_client = GazelleAPIClient()
        print("✅ Client API initialisé")
        
        # TEST 1: Lire le piano de test
        piano_data = test_read_piano(api_client, TEST_PIANO_ID)
        if not piano_data:
            print("\n❌ Impossible de lire le piano. Arrêt des tests.")
            return
        
        # TEST 2: Créer une timeline entry
        technician_id = TECHNICIAN_IDS["allan"]
        timeline_entry = test_create_timeline_entry(
            api_client,
            TEST_PIANO_ID,
            technician_id
        )
        
        if not timeline_entry:
            print("\n⚠️  Timeline entry non créée, mais on continue...")
        
        # TEST 3: Mettre à jour last_tuned_date
        updated_piano = test_update_last_tuned_date(api_client, TEST_PIANO_ID)
        
        if not updated_piano:
            print("\n⚠️  last_tuned_date non mis à jour, mais on continue...")
        
        # TEST 4: Vérifier avec piano inactif
        test_with_inactive_piano(api_client)
        
        # Vérification finale: Relire le piano pour voir les changements
        print(f"\n{'='*60}")
        print(f"🔍 VÉRIFICATION FINALE: Relecture du piano")
        print(f"{'='*60}")
        final_piano = test_read_piano(api_client, TEST_PIANO_ID)
        
        print(f"\n{'='*60}")
        print("✅ TOUS LES TESTS TERMINÉS")
        print(f"{'='*60}")
        
    except Exception as e:
        print(f"\n❌ ERREUR CRITIQUE: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()

