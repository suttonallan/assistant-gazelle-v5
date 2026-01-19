#!/usr/bin/env python3
"""
Script pour sauvegarder les credentials Google Sheets dans Supabase system_settings.

Ce script:
1. Lit le fichier google-credentials.json
2. Stocke le JSON complet dans Supabase system_settings avec la clé "GOOGLE_SHEETS_JSON"
3. Permet ensuite au code de charger les credentials depuis Supabase au lieu du fichier local

⚠️ ATTENTION: Le code actuel (service_reports.py) utilise uniquement GOOGLE_APPLICATION_CREDENTIALS.
Pour utiliser Supabase, il faudra modifier service_reports.py pour charger depuis Supabase.
"""

import json
import sys
import os

# Ajouter le répertoire parent au path pour importer core
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.supabase_storage import SupabaseStorage

def main():
    # Chemin du fichier de credentials
    file_path = "/Users/allansutton/Documents/assistant-gazelle-v5/google-credentials.json"
    
    if not os.path.exists(file_path):
        print(f"❌ Fichier introuvable: {file_path}")
        return False
    
    # Lire le fichier JSON
    try:
        with open(file_path, 'r') as f:
            credentials_data = json.load(f)
        print(f"✅ Fichier JSON lu: {len(str(credentials_data))} caractères")
    except json.JSONDecodeError as e:
        print(f"❌ Erreur de parsing JSON: {e}")
        return False
    except Exception as e:
        print(f"❌ Erreur lors de la lecture du fichier: {e}")
        return False
    
    # Vérifier que c'est bien un service account
    if credentials_data.get("type") != "service_account":
        print(f"⚠️  Attention: Le type n'est pas 'service_account' mais '{credentials_data.get('type')}'")
        response = input("Continuer quand même? (y/n): ")
        if response.lower() != 'y':
            return False
    
    # Initialiser SupabaseStorage
    try:
        storage = SupabaseStorage(silent=True)
    except Exception as e:
        print(f"❌ Erreur d'initialisation SupabaseStorage: {e}")
        print("   Vérifiez SUPABASE_URL et SUPABASE_KEY dans .env")
        return False
    
    # Sauvegarder dans system_settings
    key = "GOOGLE_SHEETS_JSON"
    try:
        success = storage.save_system_setting(key, credentials_data)
        
        if success:
            print("✅ SUCCÈS : Les credentials sont maintenant dans Supabase system_settings !")
            print(f"   Clé: {key}")
            print(f"   Client Email: {credentials_data.get('client_email', 'N/A')}")
            print(f"   Project ID: {credentials_data.get('project_id', 'N/A')}")
            print("\n📝 Note: Pour utiliser ces credentials dans le code:")
            print("   1. Modifier modules/reports/service_reports.py pour charger depuis Supabase")
            print("   2. OU garder GOOGLE_APPLICATION_CREDENTIALS comme fallback")
            print("\n🗑️  Tu peux maintenant supprimer le fichier JSON local en toute sécurité")
            print("    (mais garde-le comme backup au cas où)")
            return True
        else:
            print("❌ ERREUR : Échec de la sauvegarde dans Supabase")
            return False
            
    except Exception as e:
        print(f"❌ Erreur lors de la sauvegarde: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
