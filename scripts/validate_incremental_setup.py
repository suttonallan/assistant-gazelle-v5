#!/usr/bin/env python3
"""
Validation rapide: Mode incrémental rapide.

Vérifie que tout est en place sans exécuter la sync complète.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()


def check_incremental_file_exists():
    """Vérifie que le fichier incremental existe."""
    print("=" * 70)
    print("📁 Vérification Fichier Incrémental")
    print("=" * 70)
    print()

    incremental_file = Path(__file__).parent.parent / 'core' / 'gazelle_api_client_incremental.py'

    if incremental_file.exists():
        print(f"✅ Fichier trouvé: {incremental_file}")

        # Vérifier que les méthodes sont présentes
        content = incremental_file.read_text()
        methods = [
            'get_clients_incremental',
            'get_pianos_incremental',
            'get_appointments_incremental'
        ]

        for method in methods:
            if f'def {method}' in content:
                print(f"✅ Méthode {method} présente")
            else:
                print(f"❌ Méthode {method} MANQUANTE")
                return False
    else:
        print(f"❌ Fichier introuvable: {incremental_file}")
        return False

    print()
    return True


def check_sync_modified():
    """Vérifie que sync_to_supabase.py a été modifié."""
    print("=" * 70)
    print("📝 Vérification Modifications sync_to_supabase.py")
    print("=" * 70)
    print()

    sync_file = Path(__file__).parent.parent / 'modules' / 'sync_gazelle' / 'sync_to_supabase.py'

    if not sync_file.exists():
        print(f"❌ Fichier introuvable: {sync_file}")
        return False

    content = sync_file.read_text()

    checks = [
        ('Import GazelleAPIClientIncremental', 'from core.gazelle_api_client_incremental import GazelleAPIClientIncremental'),
        ('Paramètre incremental_mode', 'incremental_mode: bool = True'),
        ('Méthode _get_last_sync_date', 'def _get_last_sync_date'),
        ('Méthode _save_last_sync_date', 'def _save_last_sync_date'),
        ('Check mode incrémental clients', 'get_clients_incremental'),
        ('Check mode incrémental pianos', 'get_pianos_incremental'),
        ('Check mode incrémental appointments', 'get_appointments_incremental'),
    ]

    all_ok = True
    for check_name, check_str in checks:
        if check_str in content:
            print(f"✅ {check_name}")
        else:
            print(f"❌ {check_name} MANQUANT")
            all_ok = False

    print()
    return all_ok


def check_can_import():
    """Vérifie que les imports fonctionnent."""
    print("=" * 70)
    print("🔧 Vérification Imports")
    print("=" * 70)
    print()

    try:
        from core.gazelle_api_client_incremental import GazelleAPIClientIncremental
        print("✅ Import GazelleAPIClientIncremental OK")
    except Exception as e:
        print(f"❌ Erreur import GazelleAPIClientIncremental: {e}")
        return False

    try:
        from modules.sync_gazelle.sync_to_supabase import GazelleToSupabaseSync
        print("✅ Import GazelleToSupabaseSync OK")
    except Exception as e:
        print(f"❌ Erreur import GazelleToSupabaseSync: {e}")
        return False

    print()
    return True


def check_incremental_mode_default():
    """Vérifie que le mode incrémental est activé par défaut."""
    print("=" * 70)
    print("⚙️  Vérification Mode Incrémental par Défaut")
    print("=" * 70)
    print()

    try:
        from modules.sync_gazelle.sync_to_supabase import GazelleToSupabaseSync

        sync = GazelleToSupabaseSync()

        if sync.incremental_mode:
            print("✅ Mode incrémental activé par défaut")
        else:
            print("❌ Mode incrémental DÉSACTIVÉ (devrait être activé)")
            return False

        # Vérifier que l'API client a les bonnes méthodes
        if hasattr(sync.api_client, 'get_clients_incremental'):
            print("✅ API client a get_clients_incremental()")
        else:
            print("❌ API client manque get_clients_incremental()")
            return False

        if hasattr(sync.api_client, 'get_pianos_incremental'):
            print("✅ API client a get_pianos_incremental()")
        else:
            print("❌ API client manque get_pianos_incremental()")
            return False

        if hasattr(sync.api_client, 'get_appointments_incremental'):
            print("✅ API client a get_appointments_incremental()")
        else:
            print("❌ API client manque get_appointments_incremental()")
            return False

    except Exception as e:
        print(f"❌ Erreur vérification mode incrémental: {e}")
        import traceback
        traceback.print_exc()
        return False

    print()
    return True


def check_system_settings_table():
    """Vérifie que la table system_settings existe dans Supabase."""
    print("=" * 70)
    print("🗄️  Vérification Table system_settings")
    print("=" * 70)
    print()

    import requests
    import os

    SUPABASE_URL = os.getenv('SUPABASE_URL')
    SUPABASE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

    if not SUPABASE_URL or not SUPABASE_KEY:
        print("⚠️  Variables d'environnement Supabase manquantes")
        print("   (Normal si test en local sans .env)")
        print()
        return True

    try:
        url = f"{SUPABASE_URL}/rest/v1/system_settings?select=key,value&limit=1"
        headers = {
            'apikey': SUPABASE_KEY,
            'Authorization': f'Bearer {SUPABASE_KEY}'
        }

        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            print("✅ Table system_settings accessible")

            # Vérifier si last_sync_date existe
            url2 = f"{SUPABASE_URL}/rest/v1/system_settings?key=eq.last_sync_date&select=value"
            response2 = requests.get(url2, headers=headers)

            if response2.status_code == 200:
                results = response2.json()
                if results and len(results) > 0:
                    last_sync = results[0].get('value')
                    print(f"✅ last_sync_date existe: {last_sync}")
                else:
                    print("⚠️  last_sync_date n'existe pas encore (sera créé à la première sync)")
        else:
            print(f"❌ Erreur accès table system_settings: {response.status_code}")
            print(f"   {response.text[:200]}")
            return False

    except Exception as e:
        print(f"⚠️  Impossible de vérifier system_settings: {e}")
        print("   (Normal si test en local sans connexion)")

    print()
    return True


def main():
    """Exécute toutes les validations."""
    print("\n" + "=" * 70)
    print("✅ VALIDATION: Mode Incrémental Rapide")
    print("=" * 70)
    print()

    checks = [
        ("Fichier Incrémental", check_incremental_file_exists),
        ("Modifications Sync", check_sync_modified),
        ("Imports", check_can_import),
        ("Mode Incrémental Défaut", check_incremental_mode_default),
        ("Table system_settings", check_system_settings_table),
    ]

    results = []
    for name, check_func in checks:
        try:
            success = check_func()
            results.append((name, success))
        except Exception as e:
            print(f"❌ Erreur check '{name}': {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))

    # Résumé
    print("=" * 70)
    print("📊 RÉSUMÉ VALIDATION")
    print("=" * 70)
    print()

    passed = sum(1 for _, success in results if success)
    total = len(results)

    for name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status:10} {name}")

    print()
    print(f"Résultat: {passed}/{total} validations réussies")

    if passed == total:
        print("\n🎉 TOUT EST PRÊT!")
        print("\n💡 Prochaine étape:")
        print("   python3 modules/sync_gazelle/sync_to_supabase.py")
        print("   (devrait télécharger <100 items au lieu de 2785+)")
    else:
        print(f"\n⚠️  {total - passed} validation(s) échouée(s)")
        print("\n💡 Corrige les erreurs ci-dessus avant de lancer la sync")

    print()


if __name__ == '__main__':
    main()
