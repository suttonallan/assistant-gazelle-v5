#!/usr/bin/env python3
"""
Script de nettoyage et re-scan des alertes d'humidité.

Ce script:
1. Archive toutes les alertes existantes (vieilles/incorrectes)
2. Lance un scan propre des 7 derniers jours
3. Affiche un rapport détaillé

Usage:
    python3 scripts/cleanup_and_rescan_alerts.py
"""

import sys
from pathlib import Path

# Ajouter le dossier parent au path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.supabase_storage import SupabaseStorage
from modules.alerts.humidity_scanner_safe import HumidityScannerSafe
from datetime import datetime


def archive_old_alerts():
    """Archive toutes les alertes existantes."""
    print("🗄️  ÉTAPE 1: Archivage des anciennes alertes")
    print("=" * 60)

    storage = SupabaseStorage()

    # Compter les alertes actuelles
    current = storage.client.table('humidity_alerts').select('*', count='exact').eq('archived', False).execute()
    count_before = current.count if current.count else 0

    print(f"   Alertes non archivées actuelles: {count_before}")

    if count_before == 0:
        print("   ✅ Aucune alerte à archiver")
        return 0

    # Archiver toutes les alertes non archivées
    response = storage.client.table('humidity_alerts').update({
        'archived': True,
        'updated_at': datetime.utcnow().isoformat()
    }).eq('archived', False).execute()

    print(f"   ✅ {count_before} alerte(s) archivée(s)")
    print()

    return count_before


def rescan_alerts(days_back=7):
    """Lance un scan propre des N derniers jours."""
    print(f"🔍 ÉTAPE 2: Scan des {days_back} derniers jours")
    print("=" * 60)

    scanner = HumidityScannerSafe()
    result = scanner.scan_new_entries(days_back=days_back)

    print()
    print(f"   📊 Entrées scannées: {result.get('scanned', 0)}")
    print(f"   🚨 Alertes détectées: {result.get('alerts_found', 0)}")
    print(f"   ✅ Nouvelles alertes créées: {result.get('new_alerts', 0)}")
    print(f"   ⚠️  Erreurs: {result.get('errors', 0)}")
    print()

    return result


def display_new_alerts():
    """Affiche les alertes non archivées."""
    print("📋 ÉTAPE 3: Résumé des nouvelles alertes")
    print("=" * 60)

    storage = SupabaseStorage()

    # Récupérer les alertes via la vue active
    response = storage.client.table('humidity_alerts_active').select('*').execute()

    alerts = response.data if response.data else []

    if not alerts:
        print("   ✅ Aucune alerte active détectée")
        print("   👍 Tous les systèmes d'humidité sont OK!")
        print()
        return

    # Grouper par type
    by_type = {}
    by_client = {}
    unresolved = 0
    institutional = 0

    INSTITUTIONAL_CLIENTS = ['Vincent d\'Indy', 'Place des Arts', 'Orford']

    for alert in alerts:
        # Par type
        alert_type = alert.get('alert_type', 'unknown')
        by_type[alert_type] = by_type.get(alert_type, 0) + 1

        # Par client
        client_name = alert.get('client_name', 'Inconnu')
        if client_name not in by_client:
            by_client[client_name] = []
        by_client[client_name].append(alert)

        # Compteurs
        if not alert.get('is_resolved', False):
            unresolved += 1

            # Vérifier si institutionnel (recherche flexible)
            for inst in INSTITUTIONAL_CLIENTS:
                if inst.lower() in client_name.lower():
                    institutional += 1
                    break

    print(f"   Total: {len(alerts)} alerte(s)")
    print(f"   Non résolues: {unresolved}")
    print(f"   Institutionnelles non résolues: {institutional}")
    print()

    print("   Par type:")
    for alert_type, count in sorted(by_type.items()):
        emoji = {
            'housse': '🛡️',
            'alimentation': '⚡',
            'reservoir': '💧',
            'environnement': '🌡️'
        }.get(alert_type, '❓')
        print(f"      {emoji} {alert_type}: {count}")
    print()

    print("   Par client:")
    for client_name in sorted(by_client.keys()):
        client_alerts = by_client[client_name]
        unresolv_count = sum(1 for a in client_alerts if not a.get('is_resolved', False))
        status = f"({unresolv_count} non résolue(s))" if unresolv_count > 0 else "(toutes résolues)"

        # Marquer les clients institutionnels
        is_institutional = any(inst.lower() in client_name.lower() for inst in INSTITUTIONAL_CLIENTS)
        marker = "🏛️ " if is_institutional else "   "

        print(f"      {marker}{client_name}: {len(client_alerts)} alerte(s) {status}")

        # Afficher détails pour les alertes non résolues
        for alert in client_alerts:
            if not alert.get('is_resolved', False):
                alert_type = alert.get('alert_type', 'unknown')
                description = alert.get('description', 'N/A')
                observed = alert.get('observed_at', 'N/A')[:10]
                print(f"         └─ {alert_type}: {description} ({observed})")
    print()


def main():
    """Fonction principale."""
    print()
    print("🧹 NETTOYAGE ET RE-SCAN DES ALERTES D'HUMIDITÉ")
    print("=" * 60)
    print()

    try:
        # Étape 1: Archiver les anciennes alertes
        archived_count = archive_old_alerts()

        # Étape 2: Re-scanner les 7 derniers jours
        scan_result = rescan_alerts(days_back=7)

        # Étape 3: Afficher le résumé
        display_new_alerts()

        # Résumé final
        print("✅ NETTOYAGE ET RE-SCAN TERMINÉS")
        print("=" * 60)
        print(f"   Anciennes alertes archivées: {archived_count}")
        print(f"   Nouvelles alertes créées: {scan_result.get('new_alerts', 0)}")
        print()
        print("💡 Prochaines étapes:")
        print("   1. Rafraîchis le frontend (F5)")
        print("   2. Va sur 'Tableau de bord'")
        print("   3. Vérifie les alertes affichées")
        print()

        return 0

    except Exception as e:
        print(f"❌ ERREUR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
