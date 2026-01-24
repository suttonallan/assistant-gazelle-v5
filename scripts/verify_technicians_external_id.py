#!/usr/bin/env python3
"""
Script de vérification: S'assure que tous les techniciens ont leur ID Gazelle
dans la colonne external_id de la table users.

Ce script est essentiel pour le bon fonctionnement du système Late Assignment.
"""

import sys
from pathlib import Path

# Ajouter le projet au path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from core.supabase_storage import SupabaseStorage


def main():
    """Vérifie que tous les techniciens ont leur external_id."""
    print("="*70)
    print("🔍 VÉRIFICATION: Techniciens avec external_id (ID Gazelle)")
    print("="*70)
    
    storage = SupabaseStorage(silent=True)
    
    try:
        # Récupérer tous les utilisateurs
        result = storage.client.table('users').select('id,email,first_name,last_name,external_id').execute()
        
        if not result.data:
            print("\n⚠️  Aucun utilisateur trouvé dans la table users")
            return
        
        users = result.data
        print(f"\n📊 {len(users)} utilisateur(s) trouvé(s)\n")
        
        # Analyser
        with_external_id = []
        without_external_id = []
        
        for user in users:
            external_id = user.get('external_id')
            name = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip() or 'N/A'
            email = user.get('email', 'N/A')
            
            if external_id:
                with_external_id.append((name, email, external_id))
            else:
                without_external_id.append((name, email))
        
        # Afficher les résultats
        print("✅ Techniciens avec external_id (ID Gazelle):")
        if with_external_id:
            for name, email, ext_id in with_external_id:
                print(f"   • {name} ({email}): {ext_id}")
        else:
            print("   Aucun")
        
        print(f"\n❌ Techniciens SANS external_id ({len(without_external_id)}):")
        if without_external_id:
            for name, email in without_external_id:
                print(f"   ⚠️  {name} ({email})")
            print("\n🔧 ACTION REQUISE:")
            print("   Ces techniciens doivent avoir leur ID Gazelle dans external_id.")
            print("   Pour corriger:")
            print("   1. Trouver l'ID Gazelle du technicien (depuis l'API Gazelle)")
            print("   2. Mettre à jour dans Supabase:")
            print("      UPDATE users SET external_id = 'usr_XXXXX' WHERE email = 'email@example.com';")
        else:
            print("   ✅ Aucun - Tous les techniciens ont leur external_id !")
        
        # Résumé
        print("\n" + "="*70)
        print("📊 RÉSUMÉ:")
        print(f"   ✅ Avec external_id: {len(with_external_id)}/{len(users)}")
        print(f"   ❌ Sans external_id: {len(without_external_id)}/{len(users)}")
        
        if len(without_external_id) == 0:
            print("\n✅ Tous les techniciens sont correctement configurés !")
            print("   Le système Late Assignment fonctionnera correctement.")
        else:
            print(f"\n⚠️  {len(without_external_id)} technicien(s) doivent être mis à jour.")
            print("   Le système Late Assignment ne pourra pas envoyer d'alertes à ces techniciens.")
        
        print("="*70)
        
    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
