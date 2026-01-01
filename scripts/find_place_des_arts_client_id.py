#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script utilitaire pour trouver le Client ID Place des Arts dans Gazelle.

Ce script interroge l'API Gazelle pour trouver le client ID correspondant
à "Place des Arts" ou variations du nom.
"""

import sys
from pathlib import Path

# Ajouter le répertoire parent au path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.gazelle_api_client import GazelleAPIClient

# Variations possibles du nom Place des Arts
SEARCH_TERMS = [
    "Place des Arts",
    "Place-des-Arts",
    "PlaceDesArts",
    "PDA",
    "Place des arts",
    "place des arts"
]


def find_place_des_arts_client():
    """Recherche le client Place des Arts dans Gazelle"""
    print("\n" + "="*80)
    print("🔍 RECHERCHE CLIENT ID PLACE DES ARTS DANS GAZELLE")
    print("="*80)
    
    try:
        # Initialiser le client API
        print("\n📂 Initialisation du client API Gazelle...")
        api_client = GazelleAPIClient()
        print("✅ Client API initialisé")
        
        # Récupérer tous les clients
        print("\n📋 Récupération de tous les clients depuis Gazelle...")
        clients = api_client.get_clients(limit=1000)
        print(f"✅ {len(clients)} clients récupérés")
        
        # Rechercher Place des Arts
        print("\n🔍 Recherche de Place des Arts...")
        matches = []
        
        for client in clients:
            company_name = client.get('companyName') or ''
            if not company_name:
                continue
            company_name = company_name.lower()
            
            # Vérifier si le nom correspond à un des termes de recherche
            for term in SEARCH_TERMS:
                if term.lower() in company_name:
                    matches.append({
                        'id': client.get('id'),
                        'companyName': client.get('companyName'),
                        'status': client.get('status'),
                        'tags': client.get('tags', [])
                    })
                    break
        
        # Afficher les résultats
        if matches:
            print(f"\n✅ {len(matches)} client(s) trouvé(s):")
            print("-"*80)
            
            for i, match in enumerate(matches, 1):
                print(f"\n{i}. Client trouvé:")
                print(f"   ID: {match['id']}")
                print(f"   Nom: {match['companyName']}")
                print(f"   Statut: {match['status']}")
                print(f"   Tags: {match['tags']}")
                
                # Afficher la commande pour .env
                print(f"\n   📝 À ajouter dans .env:")
                print(f"   GAZELLE_CLIENT_ID_PDA={match['id']}")
            
            print("\n" + "="*80)
            print("✅ RÉSULTAT")
            print("="*80)
            print(f"\nClient ID Place des Arts: {matches[0]['id']}")
            print(f"\nAjoutez cette ligne dans votre fichier .env:")
            print(f"GAZELLE_CLIENT_ID_PDA={matches[0]['id']}")
            
            if len(matches) > 1:
                print(f"\n⚠️  ATTENTION: {len(matches)} clients trouvés!")
                print("   Vérifiez lequel est le bon client Place des Arts.")
        else:
            print("\n❌ Aucun client Place des Arts trouvé")
            print("\n💡 Suggestions:")
            print("   1. Vérifiez le nom exact dans Gazelle")
            print("   2. Essayez de rechercher manuellement dans Gazelle")
            print("   3. Le client ID peut être trouvé dans l'URL Gazelle:")
            print("      https://gazelleapp.io/clients/[CLIENT_ID]")
            
            # Afficher quelques clients pour référence
            print("\n📋 Exemples de clients trouvés (premiers 10):")
            for i, client in enumerate(clients[:10], 1):
                print(f"   {i}. {client.get('companyName')} (ID: {client.get('id')})")
        
    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    try:
        find_place_des_arts_client()
    except KeyboardInterrupt:
        print("\n\n❌ Interrompu par l'utilisateur")
    except Exception as e:
        print(f"\n❌ Erreur inattendue: {e}")
        import traceback
        traceback.print_exc()

