#!/usr/bin/env python3
"""
Script pour créer une alerte d'humidité de test pour Vincent d'Indy.
Utilise le Global Watcher pour simuler une alerte.
"""

import sys
from pathlib import Path
from datetime import datetime

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.supabase_storage import SupabaseStorage
import requests


def create_test_alert():
    """Crée une alerte de test pour Vincent d'Indy."""
    print("=" * 80)
    print("CRÉATION ALERTE DE TEST - VINCENT D'INDY")
    print("=" * 80)
    print()

    storage = SupabaseStorage()

    # 1. Récupérer l'ID client externe (utiliser le même nom que dans l'API)
    # L'API utilise "Vincent d'Indy" mais dans Supabase c'est "École de musique Vincent-d'Indy"
    print("🔍 Recherche du client institutionnel...")
    try:
        # Chercher avec le pattern utilisé par le scanner (voir humidity_scanner.py ligne 252)
        INSTITUTIONAL_CLIENTS = ["Vincent d'Indy", "Place des Arts", "Orford"]
        client_id = None
        client_name_found = None
        
        # Récupérer tous les clients et chercher par nom partiel
        response = storage.client.table('gazelle_clients').select('external_id, company_name').execute()
        
        for client in response.data:
            company_name = client.get('company_name', '').strip()
            # Chercher correspondance partielle (le scanner fait un "in" sur le nom exact)
            # Mais dans Supabase c'est "École de musique Vincent-d'Indy"
            if any(inst_name.lower() in company_name.lower() for inst_name in INSTITUTIONAL_CLIENTS):
                client_id = client['external_id']
                client_name_found = company_name
                break
        
        if not client_id:
            print("⚠️ Client institutionnel non trouvé")
            return False
        
        print(f"✅ Client trouvé: {client_name_found} (ID: {client_id})")
        print()
    except Exception as e:
        print(f"❌ Erreur recherche client: {e}")
        import traceback
        traceback.print_exc()
        return False

    # 2. Créer une alerte de test
    print("📝 Création de l'alerte de test...")
    
    alert_data = {
        "timeline_entry_id": f"test_{datetime.now().isoformat()}",
        "client_id": client_id,
        "piano_id": None,  # Optionnel
        "alert_type": "housse",
        "description": "Alerte de test - Housse enlevée détectée",
        "is_resolved": False,
        "observed_at": datetime.now().isoformat()
    }

    try:
        url = f"{storage.api_url}/humidity_alerts"
        response = requests.post(
            url,
            headers=storage._get_headers(),
            json=alert_data
        )

        if response.status_code in [200, 201]:
            print("✅ Alerte de test créée avec succès!")
            print(f"   Type: {alert_data['alert_type']}")
            print(f"   Description: {alert_data['description']}")
            print(f"   Client: Vincent d'Indy")
            print()
            return True
        else:
            # Vérifier si c'est une erreur de duplicate (OK si déjà créée)
            if 'duplicate' in response.text.lower() or 'unique' in response.text.lower():
                print("⚠️ Alerte de test déjà existante (c'est OK)")
                print()
                return True
            else:
                print(f"❌ Erreur création alerte: {response.status_code}")
                print(f"   Réponse: {response.text}")
                print()
                return False

    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Point d'entrée principal."""
    success = create_test_alert()
    
    if success:
        print("=" * 80)
        print("✅ TEST TERMINÉ")
        print("=" * 80)
        print()
        print("💡 Vérifiez maintenant le Dashboard:")
        print("   - Le compteur devrait passer de 0 à 1")
        print("   - L'alerte devrait apparaître dans la liste")
        print()
    else:
        print("=" * 80)
        print("❌ ÉCHEC")
        print("=" * 80)
        sys.exit(1)


if __name__ == "__main__":
    main()
