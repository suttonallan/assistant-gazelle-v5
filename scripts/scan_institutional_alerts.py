#!/usr/bin/env python3
"""
Scanner d'alertes d'humidité - Version par institution.

Scanne les institutions surveillées une par une pour éviter la limite
de 100 entrées de l'API Gazelle.

Usage:
    python3 scripts/scan_institutional_alerts.py [--days=7]
"""

import sys
from pathlib import Path
import argparse
from typing import Dict, Any, Optional

# Ajouter le dossier parent au path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.supabase_storage import SupabaseStorage
from core.gazelle_api_client import GazelleAPIClient
from modules.alerts.humidity_scanner_safe import HumidityScannerSafe
from datetime import datetime, timedelta


# Institutions à surveiller
INSTITUTIONAL_CLIENTS = {
    'Vincent d\'Indy': 'cli_9UMLkteep8EsISbG',
    'Place des Arts': 'cli_HbEwl9rN11pSuDEU',
    'Orford': None  # ID à déterminer
}


def get_client_id(client_name: str) -> Optional[str]:
    """Récupère l'ID Gazelle d'un client par son nom."""
    storage = SupabaseStorage()

    response = storage.client.table('gazelle_clients').select('external_id').ilike('company_name', f'%{client_name}%').execute()

    if response.data and len(response.data) > 0:
        return response.data[0]['external_id']

    return None


def scan_client_timeline(client_id: str, client_name: str, days_back: int) -> Dict[str, Any]:
    """
    Scanne les entrées timeline d'un client spécifique.

    Args:
        client_id: ID Gazelle du client
        client_name: Nom du client
        days_back: Nombre de jours en arrière

    Returns:
        Stats du scan
    """
    print(f"\n🔍 Scan de: {client_name}")
    print(f"   ID: {client_id}")

    graphql = GazelleAPIClient()
    scanner = HumidityScannerSafe()
    storage = SupabaseStorage()

    # Calculer la date de début
    now_utc = datetime.utcnow()
    start_date = now_utc - timedelta(days=days_back)
    start_date_str = start_date.strftime("%Y-%m-%dT%H:%M:%SZ")

    # Query GraphQL avec filtrage par client
    query = """
    query GetClientTimeline($clientId: String, $first: Int!) {
        allTimelineEntries(clientId: $clientId, first: $first) {
            edges {
                node {
                    id
                    occurredAt
                    type
                    comment
                    summary
                    client {
                        id
                        companyName
                    }
                    piano {
                        id
                        make
                        model
                        serialNumber
                    }
                }
            }
        }
    }
    """

    stats = {
        'scanned': 0,
        'alerts_found': 0,
        'new_alerts': 0,
        'errors': 0
    }

    try:
        result = graphql._execute_query(query, {
            "clientId": client_id,
            "first": 100
        })

        if not result or "data" not in result:
            print(f"   ⚠️  Aucune donnée récupérée")
            return stats

        timeline_data = (result.get("data") or {}).get("allTimelineEntries") or {}
        edges = (timeline_data.get("edges") or [])
        all_entries = [edge.get("node") for edge in edges if edge.get("node")]

        print(f"   📊 {len(all_entries)} entrées récupérées")

        # Filtrer par date
        entries = []
        for entry in all_entries:
            occurred_at_str = (entry or {}).get("occurredAt")
            if occurred_at_str:
                try:
                    occurred_at = datetime.fromisoformat(occurred_at_str.replace("Z", "+00:00"))
                    if occurred_at >= start_date.replace(tzinfo=occurred_at.tzinfo):
                        entries.append(entry)
                except Exception:
                    entries.append(entry)

        print(f"   📅 {len(entries)} entrées dans les {days_back} dernier(s) jour(s)")

        # Charger keywords
        alert_keywords = scanner.config.get("alert_keywords") or {}
        resolution_keywords = scanner.config.get("resolution_keywords") or {}

        # Scanner chaque entrée
        for entry in entries:
            stats['scanned'] += 1

            entry_id = (entry or {}).get("id")
            entry_type = (entry or {}).get("type")
            occurred_at = (entry or {}).get("occurredAt")

            summary = (entry or {}).get("summary")
            comment = (entry or {}).get("comment")

            client = (entry or {}).get("client") or {}
            entry_client_id = client.get("id")
            entry_client_name = client.get("companyName")

            piano = (entry or {}).get("piano") or {}
            piano_id = piano.get("id")
            piano_make = piano.get("make")
            piano_model = piano.get("model")

            # Scanner double: summary puis comment
            issue_detected = None
            text_source = None

            if summary:
                issue_detected = scanner.detect_issue_safe(summary, alert_keywords, resolution_keywords)
                text_source = "summary"

            if not issue_detected and comment:
                issue_detected = scanner.detect_issue_safe(comment, alert_keywords, resolution_keywords)
                text_source = "comment"

            if issue_detected:
                alert_type, description, is_resolved = issue_detected
                stats['alerts_found'] += 1

                print(f"   🚨 Alerte détectée!")
                print(f"      Type: {alert_type}")
                print(f"      Piano: {piano_make or 'N/A'} {piano_model or ''}")
                print(f"      Source: {text_source}")
                print(f"      Résolu: {is_resolved}")

                # Enregistrer dans Supabase
                try:
                    import requests

                    alert_data = {
                        "timeline_entry_id": entry_id,
                        "client_id": entry_client_id,
                        "piano_id": piano_id,
                        "alert_type": alert_type,
                        "description": description,
                        "is_resolved": is_resolved,
                        "observed_at": occurred_at
                    }

                    url = f"{storage.api_url}/humidity_alerts"
                    response = requests.post(
                        url,
                        headers=storage._get_headers(),
                        json=alert_data
                    )

                    if response.status_code in [200, 201]:
                        stats['new_alerts'] += 1
                        print(f"      ✅ Alerte enregistrée")
                    else:
                        if "duplicate" in response.text.lower() or "unique" in response.text.lower():
                            print(f"      ℹ️  Alerte déjà existante")
                        else:
                            print(f"      ⚠️  Erreur: {response.status_code}")
                            stats['errors'] += 1

                except Exception as e:
                    print(f"      ⚠️  Erreur enregistrement: {e}")
                    stats['errors'] += 1

        print(f"   ✅ Scan terminé: {stats['alerts_found']} alertes détectées, {stats['new_alerts']} nouvelles")

    except Exception as e:
        print(f"   ❌ Erreur: {e}")
        stats['errors'] += 1

    return stats


def main():
    """Fonction principale."""
    parser = argparse.ArgumentParser(description='Scanner d\'alertes d\'humidité par institution')
    parser.add_argument('--days', type=int, default=7, help='Nombre de jours en arrière à scanner (défaut: 7)')
    args = parser.parse_args()

    print()
    print("🏛️ SCAN DES ALERTES D'HUMIDITÉ PAR INSTITUTION")
    print("=" * 60)
    print(f"Période: {args.days} derniers jours")
    print()

    total_stats = {
        'scanned': 0,
        'alerts_found': 0,
        'new_alerts': 0,
        'errors': 0
    }

    # Scanner chaque institution
    for client_name, client_id in INSTITUTIONAL_CLIENTS.items():
        if client_id is None:
            print(f"\n⚠️  {client_name}: ID inconnu, recherche...")
            client_id = get_client_id(client_name)
            if client_id:
                print(f"   ✅ ID trouvé: {client_id}")
                INSTITUTIONAL_CLIENTS[client_name] = client_id
            else:
                print(f"   ❌ Client introuvable dans Supabase")
                continue

        stats = scan_client_timeline(client_id, client_name, args.days)

        # Cumuler les stats
        for key in total_stats:
            total_stats[key] += stats[key]

    # Résumé final
    print()
    print("=" * 60)
    print("📊 RÉSUMÉ GLOBAL")
    print("=" * 60)
    print(f"   Entrées scannées: {total_stats['scanned']}")
    print(f"   Alertes détectées: {total_stats['alerts_found']}")
    print(f"   Nouvelles alertes créées: {total_stats['new_alerts']}")
    print(f"   Erreurs: {total_stats['errors']}")
    print()

    if total_stats['new_alerts'] > 0:
        print("💡 Prochaines étapes:")
        print("   1. Rafraîchis le frontend (F5)")
        print("   2. Va sur 'Tableau de bord'")
        print("   3. Les nouvelles alertes s'afficheront automatiquement")
    else:
        print("✅ Aucune nouvelle alerte détectée")
        print("   Tous les systèmes d'humidité sont OK!")

    print()

    return 0 if total_stats['errors'] == 0 else 1


if __name__ == "__main__":
    exit(main())
