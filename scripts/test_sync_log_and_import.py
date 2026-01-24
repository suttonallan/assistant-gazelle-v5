#!/usr/bin/env python3
"""
Script de test pour vérifier les logs de sync et forcer un import de test.

Ce script :
1. Vérifie les dernières entrées dans sync_logs
2. Crée une entrée de test dans sync_logs avec status='success'
3. Vérifie que la coche verte apparaît dans le Dashboard
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
import requests
import json

# Ajouter le projet au path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from core.supabase_storage import SupabaseStorage
from scripts.sync_logger import SyncLogger


def check_recent_sync_logs():
    """Vérifie les logs de sync récents."""
    print("="*70)
    print("🔍 VÉRIFICATION DES LOGS DE SYNC RÉCENTS")
    print("="*70)
    
    storage = SupabaseStorage(silent=True)
    
    try:
        # Récupérer les logs des dernières 24h
        yesterday = (datetime.now() - timedelta(days=1)).isoformat()
        
        response = storage.client.table('sync_logs').select('*').gte('created_at', yesterday).order('created_at', desc=True).limit(10).execute()
        
        logs = response.data if response.data else []
        
        print(f"\n📊 {len(logs)} log(s) trouvé(s) dans les dernières 24h\n")
        
        if logs:
            for i, log in enumerate(logs, 1):
                created_at = log.get('created_at', 'N/A')
                script_name = log.get('script_name', 'N/A')
                status = log.get('status', 'N/A')
                message = log.get('message', '')
                
                status_emoji = '✅' if status == 'success' else '❌' if status == 'error' else '⚠️'
                
                print(f"{i}. {status_emoji} {script_name}")
                print(f"   Status: {status}")
                print(f"   Date: {created_at}")
                if message:
                    print(f"   Message: {message[:100]}")
                print()
        else:
            print("⚠️  Aucun log de sync trouvé dans les dernières 24h")
            print("   C'est probablement pour ça que la coche verte n'apparaît pas !\n")
        
        return logs
        
    except Exception as e:
        print(f"❌ Erreur lors de la vérification: {e}")
        import traceback
        traceback.print_exc()
        return []


def create_test_sync_log():
    """Crée une entrée de test dans sync_logs avec status='success'."""
    print("="*70)
    print("📝 CRÉATION D'UN LOG DE SYNC DE TEST")
    print("="*70)
    
    storage = SupabaseStorage(silent=True)
    
    try:
        # Utiliser uniquement les colonnes qui existent dans sync_logs
        # Colonnes disponibles: id, created_at, script_name, status, error_message, 
        # execution_time_seconds, tables_updated
        import json
        
        stats_dict = {
            'clients': 10,
            'pianos': 25,
            'appointments': 50,
            'timeline': 100
        }
        
        data = {
            'script_name': 'Test Import Manuel',
            'status': 'success',
            'tables_updated': json.dumps(stats_dict),  # Stocker comme JSON string
            'execution_time_seconds': 45,
            'error_message': None,
            'created_at': datetime.now().isoformat()
        }
        
        print(f"\n📋 Données à insérer:")
        print(json.dumps(data, indent=2))
        
        # Insérer directement dans Supabase
        response = storage.client.table('sync_logs').insert(data).execute()
        
        if response.data:
            print("\n✅ Log de test créé avec succès !")
            print(f"   ID: {response.data[0].get('id', 'N/A')}")
            print("   La coche verte devrait maintenant apparaître dans le Dashboard")
            print("   Rafraîchissez la page du Dashboard pour voir le changement")
            return True
        else:
            print("\n❌ Échec de la création du log (pas de données retournées)")
            return False
            
    except Exception as e:
        print(f"\n❌ Erreur lors de la création du log: {e}")
        import traceback
        traceback.print_exc()
        return False


def trigger_manual_sync_via_api():
    """Déclenche une sync manuelle via l'API."""
    print("="*70)
    print("🚀 DÉCLENCHEMENT D'UNE SYNC MANUELLE VIA API")
    print("="*70)
    
    # Récupérer l'URL de l'API depuis les variables d'environnement
    api_url = os.getenv('API_URL', 'https://assistant-gazelle-v5-api.onrender.com')
    
    if not api_url:
        print("❌ API_URL non défini dans les variables d'environnement")
        print("   Définissez API_URL dans votre .env ou passez-le en argument")
        return False
    
    endpoint = f"{api_url}/api/scheduler/run/sync"
    
    print(f"\n📡 Appel de l'endpoint: {endpoint}")
    
    try:
        response = requests.post(
            endpoint,
            json={
                'triggered_by': 'manual',
                'user_email': 'test@example.com'
            },
            timeout=300  # 5 minutes max
        )
        
        if response.status_code == 200:
            result = response.json()
            print("\n✅ Sync déclenchée avec succès !")
            print(f"   Résultat: {json.dumps(result, indent=2)}")
            return True
        else:
            print(f"\n❌ Erreur API: {response.status_code}")
            print(f"   Réponse: {response.text}")
            return False
            
    except Exception as e:
        print(f"\n❌ Erreur lors de l'appel API: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Point d'entrée principal."""
    import os
    
    print("\n" + "="*70)
    print("🧪 SCRIPT DE TEST - SYNC LOGS ET IMPORT")
    print("="*70)
    print()
    
    # 1. Vérifier les logs récents
    logs = check_recent_sync_logs()
    
    # 2. Demander à l'utilisateur ce qu'il veut faire
    print("\n" + "="*70)
    print("📋 OPTIONS DISPONIBLES")
    print("="*70)
    print("1. Créer un log de test (rapide - pour tester la coche verte)")
    print("2. Déclencher une vraie sync via l'API (plus long - vraie synchronisation)")
    print("3. Les deux")
    print()
    
    # Mode non-interactif: utiliser l'argument en ligne de commande ou défaut à "1"
    import sys
    if len(sys.argv) > 1:
        choice = sys.argv[1].strip()
    else:
        choice = "1"  # Par défaut: créer un log de test
    print(f"   Choix sélectionné: {choice}")
    
    success = False
    
    if choice in ['1', '3']:
        print("\n" + "="*70)
        success = create_test_sync_log()
    
    if choice in ['2', '3']:
        print("\n" + "="*70)
        api_success = trigger_manual_sync_via_api()
        if choice == '3':
            success = success and api_success
        else:
            success = api_success
    
    # 3. Vérifier à nouveau les logs
    print("\n" + "="*70)
    print("🔍 VÉRIFICATION FINALE")
    print("="*70)
    final_logs = check_recent_sync_logs()
    
    if success:
        print("\n✅ Test terminé avec succès !")
        print("   Rafraîchissez le Dashboard pour voir la coche verte")
    else:
        print("\n⚠️  Test terminé avec des erreurs")
        print("   Vérifiez les logs ci-dessus pour plus de détails")
    
    print("\n" + "="*70)


if __name__ == '__main__':
    import os
    main()
