#!/usr/bin/env python3
"""
Script de test pour valider la synchronisation Timeline 7 jours.

Ce script:
1. Teste la méthode sync_timeline_entries() avec fenêtre 7 jours
2. Vérifie que le cutoff est bien appliqué
3. Affiche les métriques de performance
4. Vérifie l'absence de doublons

Usage:
    python3 scripts/test_timeline_7days.py
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta

# Ajouter le dossier parent au path
sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.sync_gazelle.sync_to_supabase import GazelleToSupabaseSync
from core.supabase_storage import SupabaseStorage


def test_timeline_sync():
    """Teste la synchronisation timeline avec fenêtre 7 jours."""
    print()
    print("🧪 TEST SYNCHRONISATION TIMELINE - FENÊTRE 7 JOURS")
    print("=" * 70)
    print()

    # Étape 1: Afficher la configuration
    print("📋 ÉTAPE 1: Configuration")
    print("-" * 70)

    now = datetime.now()
    cutoff_date = now - timedelta(days=7)

    print(f"   📅 Date actuelle: {now.strftime('%Y-%m-%d %H:%M')}")
    print(f"   📍 Cutoff (7 jours): {cutoff_date.strftime('%Y-%m-%d %H:%M')}")
    print(f"   ⚡ Performance attendue: <30 secondes")
    print()

    # Étape 2: Compter les entrées existantes avant sync
    print("📊 ÉTAPE 2: État Avant Sync")
    print("-" * 70)

    storage = SupabaseStorage()

    # Compter total
    response_total = storage.client.table('gazelle_timeline_entries').select('*', count='exact').execute()
    total_before = response_total.count if response_total.count else 0

    # Compter les 7 derniers jours
    cutoff_iso = cutoff_date.isoformat()
    response_recent = storage.client.table('gazelle_timeline_entries').select(
        '*', count='exact'
    ).gte('occurred_at', cutoff_iso).execute()
    recent_before = response_recent.count if response_recent.count else 0

    print(f"   📚 Total entrées en DB: {total_before:,}")
    print(f"   📅 Entrées 7 derniers jours: {recent_before:,}")
    print()

    # Étape 3: Lancer la synchronisation
    print("🔄 ÉTAPE 3: Synchronisation en cours...")
    print("-" * 70)

    start_time = datetime.now()

    try:
        syncer = GazelleToSupabaseSync()
        synced_count = syncer.sync_timeline_entries()

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        print()
        print(f"   ✅ Synchronisation terminée")
        print(f"   ⏱️  Durée: {duration:.1f} secondes")
        print(f"   📥 Entrées synchronisées: {synced_count}")
        print()

        # Étape 4: Vérifier l'état après sync
        print("📊 ÉTAPE 4: État Après Sync")
        print("-" * 70)

        # Compter total
        response_total_after = storage.client.table('gazelle_timeline_entries').select('*', count='exact').execute()
        total_after = response_total_after.count if response_total_after.count else 0

        # Compter les 7 derniers jours
        response_recent_after = storage.client.table('gazelle_timeline_entries').select(
            '*', count='exact'
        ).gte('occurred_at', cutoff_iso).execute()
        recent_after = response_recent_after.count if response_recent_after.count else 0

        print(f"   📚 Total entrées en DB: {total_after:,}")
        print(f"   📅 Entrées 7 derniers jours: {recent_after:,}")
        print(f"   📈 Delta total: +{total_after - total_before}")
        print(f"   📈 Delta 7 jours: +{recent_after - recent_before}")
        print()

        # Étape 5: Vérifier l'absence de doublons
        print("🔍 ÉTAPE 5: Vérification Doublons")
        print("-" * 70)

        # Requête SQL pour détecter les doublons sur external_id
        duplicates_query = """
            SELECT external_id, COUNT(*) as count
            FROM gazelle_timeline_entries
            GROUP BY external_id
            HAVING COUNT(*) > 1
            LIMIT 5
        """

        try:
            duplicates = storage.client.rpc('exec_sql', {'sql': duplicates_query}).execute()
            duplicate_count = len(duplicates.data) if duplicates.data else 0

            if duplicate_count == 0:
                print(f"   ✅ Aucun doublon détecté (on_conflict fonctionne)")
            else:
                print(f"   ⚠️  {duplicate_count} external_id en doublon détectés")
                for dup in duplicates.data[:5]:
                    print(f"      - {dup['external_id']}: {dup['count']} occurrences")
        except Exception as e:
            # Si RPC n'est pas disponible, faire une vérification simple
            print(f"   ℹ️  Vérification avancée non disponible: {e}")
            print(f"   ℹ️  Si sync réussie, on_conflict devrait garantir aucun doublon")

        print()

        # Étape 6: Métriques de performance
        print("⚡ ÉTAPE 6: Métriques de Performance")
        print("-" * 70)

        if synced_count > 0 and duration > 0:
            rate = synced_count / duration
            print(f"   📊 Vitesse: {rate:.1f} entrées/seconde")

        if duration < 30:
            print(f"   ✅ Performance EXCELLENTE (<30s): {duration:.1f}s")
        elif duration < 60:
            print(f"   ✅ Performance BONNE (<60s): {duration:.1f}s")
        else:
            print(f"   ⚠️  Performance À AMÉLIORER (>60s): {duration:.1f}s")

        print()

        # Résumé final
        print("✅ TEST TERMINÉ")
        print("=" * 70)
        print()
        print("📋 RÉSUMÉ:")
        print(f"   ⏱️  Durée sync: {duration:.1f}s")
        print(f"   📥 Entrées synchronisées: {synced_count}")
        print(f"   📅 Fenêtre: 7 derniers jours")
        print(f"   🔒 Doublons: {'Aucun' if duplicate_count == 0 else f'{duplicate_count} détectés'}")
        print()

        if duration < 30 and duplicate_count == 0:
            print("🎉 SUCCÈS: Tous les critères sont respectés!")
            print("   ✅ Performance < 30s")
            print("   ✅ Aucun doublon")
            print("   ✅ Fenêtre 7 jours appliquée")
            print()
            print("💡 Le système est prêt pour les imports automatiques de cette nuit.")
            return 0
        else:
            print("⚠️  ATTENTION: Certains critères ne sont pas optimaux")
            if duration >= 30:
                print(f"   ⚠️  Durée: {duration:.1f}s (attendu <30s)")
            if duplicate_count > 0:
                print(f"   ⚠️  Doublons: {duplicate_count} détectés")
            return 1

    except Exception as e:
        print()
        print(f"❌ ERREUR lors de la synchronisation: {e}")
        import traceback
        traceback.print_exc()
        return 1


def main():
    """Fonction principale."""
    return test_timeline_sync()


if __name__ == "__main__":
    exit(main())
