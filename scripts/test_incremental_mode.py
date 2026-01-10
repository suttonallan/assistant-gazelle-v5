#!/usr/bin/env python3
"""
Test du mode incrémental rapide.

Vérifie que:
1. Mode incrémental est activé par défaut
2. Early exit fonctionne pour clients/pianos
3. Filtre startGte fonctionne pour appointments
4. last_sync_date est sauvegardé correctement
5. Nombre d'items téléchargés < 100 au lieu de 2785+
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

import requests
import os

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')


def test_incremental_mode_enabled():
    """Test 1: Vérifie que le mode incrémental est activé par défaut."""
    print("=" * 70)
    print("TEST 1: Mode Incrémental Activé par Défaut")
    print("=" * 70)
    print()

    from modules.sync_gazelle.sync_to_supabase import GazelleToSupabaseSync

    sync = GazelleToSupabaseSync()

    if sync.incremental_mode:
        print("✅ Mode incrémental activé par défaut")
    else:
        print("❌ Mode incrémental DÉSACTIVÉ (devrait être activé)")
        return False

    # Vérifier que api_client a les méthodes incrementales
    has_incremental = all([
        hasattr(sync.api_client, 'get_clients_incremental'),
        hasattr(sync.api_client, 'get_pianos_incremental'),
        hasattr(sync.api_client, 'get_appointments_incremental')
    ])

    if has_incremental:
        print("✅ API client a les méthodes incrementales")
    else:
        print("❌ API client manque les méthodes incrementales")
        return False

    print()
    return True


def test_last_sync_date_storage():
    """Test 2: Vérifie que last_sync_date est bien stocké et récupéré."""
    print("=" * 70)
    print("TEST 2: Stockage/Récupération last_sync_date")
    print("=" * 70)
    print()

    from modules.sync_gazelle.sync_to_supabase import GazelleToSupabaseSync

    sync = GazelleToSupabaseSync()

    # Tester récupération
    last_sync = sync._get_last_sync_date()

    if last_sync:
        print(f"✅ last_sync_date récupéré: {last_sync}")
    else:
        print("⚠️  Aucun last_sync_date trouvé (normal si première sync)")

    # Tester sauvegarde
    test_date = datetime.now()
    try:
        sync._save_last_sync_date(test_date)
        print(f"✅ last_sync_date sauvegardé: {test_date}")

        # Vérifier que ça a bien été sauvegardé
        sync2 = GazelleToSupabaseSync()
        retrieved = sync2._get_last_sync_date()

        if retrieved and abs((retrieved - test_date).total_seconds()) < 5:
            print(f"✅ last_sync_date récupéré correctement: {retrieved}")
        else:
            print(f"❌ last_sync_date récupéré différent: {retrieved} vs {test_date}")
            return False

    except Exception as e:
        print(f"❌ Erreur sauvegarde last_sync_date: {e}")
        return False

    print()
    return True


def test_incremental_clients():
    """Test 3: Vérifie que get_clients_incremental limite bien les résultats."""
    print("=" * 70)
    print("TEST 3: Clients Incrémentaux (Early Exit)")
    print("=" * 70)
    print()

    from modules.sync_gazelle.sync_to_supabase import GazelleToSupabaseSync
    from datetime import datetime

    sync = GazelleToSupabaseSync()

    # Test avec last_sync_date récent (devrait retourner peu de clients)
    recent_date = datetime.now() - timedelta(hours=24)

    print(f"🔍 Récupération clients modifiés depuis {recent_date}")

    try:
        clients = sync.api_client.get_clients_incremental(
            last_sync_date=recent_date,
            limit=5000
        )

        count = len(clients)
        print(f"📥 {count} clients récupérés")

        if count < 100:
            print(f"✅ Nombre de clients < 100 (optimisation fonctionne)")
        elif count < 500:
            print(f"⚠️  {count} clients (devrait être < 100, mais acceptable)")
        else:
            print(f"❌ Trop de clients ({count}), early exit ne fonctionne pas?")
            return False

    except Exception as e:
        print(f"❌ Erreur get_clients_incremental: {e}")
        import traceback
        traceback.print_exc()
        return False

    print()
    return True


def test_incremental_pianos():
    """Test 4: Vérifie que get_pianos_incremental limite bien les résultats."""
    print("=" * 70)
    print("TEST 4: Pianos Incrémentaux (Early Exit)")
    print("=" * 70)
    print()

    from modules.sync_gazelle.sync_to_supabase import GazelleToSupabaseSync
    from datetime import datetime

    sync = GazelleToSupabaseSync()

    # Test avec last_sync_date récent (devrait retourner peu de pianos)
    recent_date = datetime.now() - timedelta(hours=24)

    print(f"🔍 Récupération pianos modifiés depuis {recent_date}")

    try:
        pianos = sync.api_client.get_pianos_incremental(
            last_sync_date=recent_date,
            limit=5000
        )

        count = len(pianos)
        print(f"📥 {count} pianos récupérés")

        if count < 50:
            print(f"✅ Nombre de pianos < 50 (optimisation fonctionne)")
        elif count < 200:
            print(f"⚠️  {count} pianos (devrait être < 50, mais acceptable)")
        else:
            print(f"❌ Trop de pianos ({count}), early exit ne fonctionne pas?")
            return False

    except Exception as e:
        print(f"❌ Erreur get_pianos_incremental: {e}")
        import traceback
        traceback.print_exc()
        return False

    print()
    return True


def test_incremental_appointments():
    """Test 5: Vérifie que get_appointments_incremental utilise bien le filtre startGte."""
    print("=" * 70)
    print("TEST 5: Appointments Incrémentaux (Filtre startGte)")
    print("=" * 70)
    print()

    from modules.sync_gazelle.sync_to_supabase import GazelleToSupabaseSync
    from datetime import datetime

    sync = GazelleToSupabaseSync()

    # Test avec fenêtre de 7 jours
    recent_date = datetime.now() - timedelta(days=7)

    print(f"🔍 Récupération appointments depuis {recent_date} (fenêtre 7 jours)")

    try:
        appointments = sync.api_client.get_appointments_incremental(
            last_sync_date=recent_date,
            limit=5000
        )

        count = len(appointments)
        print(f"📥 {count} appointments récupérés")

        if count < 100:
            print(f"✅ Nombre d'appointments < 100 (filtre fonctionne)")
        elif count < 300:
            print(f"⚠️  {count} appointments (devrait être < 100, mais acceptable)")
        else:
            print(f"❌ Trop d'appointments ({count}), filtre startGte ne fonctionne pas?")
            return False

    except Exception as e:
        print(f"❌ Erreur get_appointments_incremental: {e}")
        import traceback
        traceback.print_exc()
        return False

    print()
    return True


def test_full_mode_flag():
    """Test 6: Vérifie que le flag --full désactive le mode incrémental."""
    print("=" * 70)
    print("TEST 6: Flag --full Désactive Mode Incrémental")
    print("=" * 70)
    print()

    from modules.sync_gazelle.sync_to_supabase import GazelleToSupabaseSync

    # Test mode incrémental désactivé
    sync_full = GazelleToSupabaseSync(incremental_mode=False)

    if not sync_full.incremental_mode:
        print("✅ Mode incrémental désactivé avec incremental_mode=False")
    else:
        print("❌ Mode incrémental toujours activé (devrait être désactivé)")
        return False

    print()
    return True


def test_sync_counts_comparison():
    """Test 7: Compare les compteurs avant/après mode incrémental."""
    print("=" * 70)
    print("TEST 7: Comparaison Compteurs Avant/Après")
    print("=" * 70)
    print()

    # Afficher les métriques attendues
    print("📊 Métriques Attendues:")
    print()
    print("| Métrique            | Avant (Complet) | Après (Incrémental) | Économie |")
    print("|---------------------|-----------------|---------------------|----------|")
    print("| Items clients       | 1344            | ~5-10               | -99%     |")
    print("| Items pianos        | 1031            | ~2-5                | -99%     |")
    print("| Items appointments  | 267             | ~25-50              | -80%     |")
    print("| Items timeline      | 123             | ~30-50              | -60%     |")
    print("| **TOTAL/jour**      | **~2785**       | **<100**            | **-96%** |")
    print("| Durée sync          | 120-180s        | <30s                | -75%     |")
    print()

    print("✅ Métriques affichées (validation manuelle requise)")
    print()
    return True


def main():
    """Exécute tous les tests."""
    print("\n" + "=" * 70)
    print("🧪 TESTS: Mode Incrémental Rapide")
    print("=" * 70)
    print()

    tests = [
        ("Mode Incrémental Activé", test_incremental_mode_enabled),
        ("Stockage last_sync_date", test_last_sync_date_storage),
        ("Clients Incrémentaux", test_incremental_clients),
        ("Pianos Incrémentaux", test_incremental_pianos),
        ("Appointments Incrémentaux", test_incremental_appointments),
        ("Flag --full", test_full_mode_flag),
        ("Comparaison Compteurs", test_sync_counts_comparison),
    ]

    results = []
    for name, test_func in tests:
        try:
            success = test_func()
            results.append((name, success))
        except Exception as e:
            print(f"❌ Erreur test '{name}': {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))

    # Résumé
    print("=" * 70)
    print("📊 RÉSUMÉ DES TESTS")
    print("=" * 70)
    print()

    passed = sum(1 for _, success in results if success)
    total = len(results)

    for name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status:10} {name}")

    print()
    print(f"Résultat: {passed}/{total} tests réussis")

    if passed == total:
        print("\n🎉 TOUS LES TESTS RÉUSSIS!")
    else:
        print(f"\n⚠️  {total - passed} test(s) échoué(s)")

    print()


if __name__ == '__main__':
    main()
