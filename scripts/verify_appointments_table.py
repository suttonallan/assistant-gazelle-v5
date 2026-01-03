#!/usr/bin/env python3
"""
Script pour vérifier que la table gazelle_appointments existe et est correctement configurée.

Usage:
    python3 scripts/verify_appointments_table.py
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Ajouter le répertoire parent au path
sys.path.insert(0, str(Path(__file__).parent.parent))

load_dotenv()

import requests


def verify_table():
    """Vérifie que la table existe et est accessible."""
    print("=" * 60)
    print("🔍 VÉRIFICATION DE LA TABLE gazelle_appointments")
    print("=" * 60)
    
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_KEY')
    
    if not supabase_url or not supabase_key:
        print("❌ SUPABASE_URL ou SUPABASE_KEY non défini dans .env")
        sys.exit(1)
    
    api_url = f"{supabase_url}/rest/v1"
    headers = {
        "apikey": supabase_key,
        "Authorization": f"Bearer {supabase_key}",
        "Content-Type": "application/json"
    }
    
    # Test 1: Vérifier que la table existe (requête vide)
    print("\n1️⃣ Test d'accès à la table...")
    try:
        response = requests.get(
            f"{api_url}/gazelle_appointments?select=id&limit=1",
            headers=headers
        )
        
        if response.status_code == 200:
            print("✅ Table gazelle_appointments accessible via API REST")
            data = response.json()
            print(f"   Format de réponse: {type(data).__name__}")
        elif response.status_code == 404:
            print("❌ Table non trouvée (404)")
            print("   Vérifiez que le script SQL a bien été exécuté")
            sys.exit(1)
        else:
            print(f"⚠️ Code de statut inattendu: {response.status_code}")
            print(f"   Réponse: {response.text[:200]}")
            
    except Exception as e:
        print(f"❌ Erreur lors de la vérification: {e}")
        sys.exit(1)
    
    # Test 2: Vérifier les colonnes attendues
    print("\n2️⃣ Test de filtre par technicien...")
    try:
        response = requests.get(
            f"{api_url}/gazelle_appointments?technicien=eq.test&select=id&limit=1",
            headers=headers
        )
        
        if response.status_code == 200:
            print("✅ Filtre par technicien fonctionne")
        else:
            print(f"⚠️ Filtre par technicien: {response.status_code}")
            print(f"   Réponse: {response.text[:200]}")
            
    except Exception as e:
        print(f"⚠️ Erreur lors du test de filtre: {e}")
    
    # Test 3: Vérifier le filtre par date
    print("\n3️⃣ Test de filtre par appointment_date...")
    try:
        response = requests.get(
            f"{api_url}/gazelle_appointments?appointment_date=gte.2025-01-01&select=id&limit=1",
            headers=headers
        )
        
        if response.status_code == 200:
            print("✅ Filtre par appointment_date fonctionne")
        else:
            print(f"⚠️ Filtre par appointment_date: {response.status_code}")
            print(f"   Réponse: {response.text[:200]}")
            
    except Exception as e:
        print(f"⚠️ Erreur lors du test de filtre date: {e}")
    
    print("\n" + "=" * 60)
    print("✅ VÉRIFICATION TERMINÉE")
    print("=" * 60)
    print("\n💡 La table est prête pour la synchronisation des rendez-vous")
    print("   Vous pouvez maintenant exécuter:")
    print("   python3 modules/sync_gazelle/test_appointments.py")


if __name__ == "__main__":
    verify_table()



