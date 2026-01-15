#!/usr/bin/env python3
"""
Scanner d'alertes d'humidité depuis les données Supabase existantes.

Ce script scanne les timeline entries DÉJÀ synchronisées dans Supabase
pour détecter des alertes d'humidité, sans avoir besoin d'accéder à l'API Gazelle.
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
import json

# Ajouter le dossier parent au path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.supabase_storage import SupabaseStorage


# Mots-clés pour détecter les alertes
ALERT_KEYWORDS = {
    'housse': ['housse enlevée', 'sans housse', 'housse retiree', 'enlever housse'],
    'alimentation': ['débranché', 'debranche', 'unplugged', 'rallonge', 'besoin rallonge'],
    'reservoir': ['réservoir vide', 'reservoir vide', 'tank empty', 'remplir reservoir'],
    'environnement': ['fenêtre ouverte', 'fenetre ouverte', 'température basse', 'trop froid']
}

# Clients institutionnels prioritaires
INSTITUTIONAL_CLIENTS = {
    "cli_9UMLkteep8EsISbG": "Vincent d'Indy",
    "cli_a8lkjsdf9sdfkljs": "Place des Arts",
    "cli_orford123456789": "Orford"
}


def scan_timeline_entries(days_back=7):
    """
    Scanne les timeline entries pour détecter des alertes.

    Args:
        days_back: Nombre de jours à scanner (défaut: 7)
    """
    print()
    print("🔍 SCAN DES ALERTES D'HUMIDITÉ DEPUIS SUPABASE")
    print("=" * 70)
    print()

    storage = SupabaseStorage()

    # Date de cutoff
    cutoff_date = datetime.now() - timedelta(days=days_back)
    cutoff_iso = cutoff_date.isoformat()

    print(f"📅 Période de scan: {days_back} derniers jours")
    print(f"   Cutoff: {cutoff_date.strftime('%Y-%m-%d %H:%M')}")
    print()

    # Récupérer les timeline entries récentes
    print("📥 Récupération des timeline entries...")

    response = storage.client.table('gazelle_timeline_entries').select(
        'external_id, occurred_at, client_id, piano_id, entry_type, title, description'
    ).gte(
        'occurred_at', cutoff_iso
    ).order('occurred_at', desc=True).execute()

    entries = response.data if response.data else []
    print(f"   {len(entries)} entrées récupérées")
    print()

    if not entries:
        print("✅ Aucune entrée récente trouvée")
        return

    # Scanner chaque entrée
    print("🔍 Scan en cours...")
    print()

    alerts_found = []
    scanned_count = 0

    for entry in entries:
        scanned_count += 1

        # Récupérer les textes à scanner
        title = (entry.get('title') or '').lower()
        description = (entry.get('description') or '').lower()
        combined_text = f"{title} {description}"

        # Détecter les alertes
        for alert_type, keywords in ALERT_KEYWORDS.items():
            for keyword in keywords:
                if keyword.lower() in combined_text:
                    # Alerte détectée !
                    alert_info = {
                        'timeline_entry_id': entry.get('external_id'),
                        'alert_type': alert_type,
                        'keyword': keyword,
                        'occurred_at': entry.get('occurred_at'),
                        'client_id': entry.get('client_id'),
                        'piano_id': entry.get('piano_id'),
                        'description': entry.get('description', '')[:200],  # Limiter à 200 chars
                        'entry_type': entry.get('entry_type')
                    }
                    alerts_found.append(alert_info)
                    break  # Une alerte par entrée suffit

    print(f"   ✅ {scanned_count} entrées scannées")
    print(f"   🚨 {len(alerts_found)} alerte(s) détectée(s)")
    print()

    if not alerts_found:
        print("✅ Aucune alerte détectée dans la période")
        print("   Tous les systèmes d'humidité semblent OK!")
        return

    # Afficher les alertes trouvées
    print("📋 ALERTES DÉTECTÉES:")
    print("-" * 70)
    print()

    # Grouper par type
    by_type = {}
    institutional_count = 0

    for alert in alerts_found:
        alert_type = alert['alert_type']
        if alert_type not in by_type:
            by_type[alert_type] = []
        by_type[alert_type].append(alert)

        # Compter les institutionnelles
        if alert['client_id'] in INSTITUTIONAL_CLIENTS:
            institutional_count += 1

    print(f"   Total: {len(alerts_found)} alerte(s)")
    print(f"   Institutionnelles: {institutional_count}")
    print()

    # Afficher par type
    for alert_type, type_alerts in sorted(by_type.items()):
        emoji = {
            'housse': '🛡️',
            'alimentation': '⚡',
            'reservoir': '💧',
            'environnement': '🌡️'
        }.get(alert_type, '❓')

        print(f"{emoji} {alert_type.upper()}: {len(type_alerts)} alerte(s)")

        for alert in type_alerts[:5]:  # Limiter à 5 par type
            client_id = alert['client_id']
            client_name = INSTITUTIONAL_CLIENTS.get(client_id, client_id or 'Inconnu')
            occurred = alert['occurred_at'][:10] if alert['occurred_at'] else 'N/A'
            keyword = alert['keyword']

            marker = "🏛️ " if client_id in INSTITUTIONAL_CLIENTS else "   "

            print(f"{marker}  - {client_name} ({occurred})")
            print(f"      Mot-clé: '{keyword}'")

            desc = alert['description'][:100]
            if desc:
                print(f"      Description: {desc}...")
            print()

    # Proposer d'écrire dans Supabase
    print()
    print("💡 PROCHAINES ÉTAPES:")
    print("-" * 70)
    print()
    print("Pour créer ces alertes dans Supabase:")
    print()
    print("1. Utilise le script cleanup_and_rescan_alerts.py pour un scan complet")
    print("   python3 scripts/cleanup_and_rescan_alerts.py")
    print()
    print("2. Ou utilise l'API Gazelle avec scan_institutional_alerts.py")
    print("   (nécessite token OAuth)")
    print()

    return {
        'scanned': scanned_count,
        'alerts_found': len(alerts_found),
        'institutional': institutional_count,
        'by_type': {k: len(v) for k, v in by_type.items()}
    }


def main():
    """Fonction principale."""
    try:
        result = scan_timeline_entries(days_back=7)

        print()
        print("✅ SCAN TERMINÉ")
        print("=" * 70)

        if result:
            print()
            print(f"📊 Résumé:")
            print(f"   Entrées scannées: {result['scanned']}")
            print(f"   Alertes trouvées: {result['alerts_found']}")
            print(f"   Institutionnelles: {result['institutional']}")
            print()

            if result['alerts_found'] > 0:
                print("⚠️  ATTENTION: Des alertes ont été détectées!")
                print("   Utilise cleanup_and_rescan_alerts.py pour les créer dans Supabase")
                return 1
            else:
                print("✅ Aucune alerte détectée - Tous les systèmes OK")
                return 0

        return 0

    except Exception as e:
        print()
        print(f"❌ ERREUR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
