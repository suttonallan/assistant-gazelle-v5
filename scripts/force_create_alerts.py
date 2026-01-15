#!/usr/bin/env python3
"""
Force la création des alertes depuis le scan API Gazelle.

Ce script scanne par institution et crée directement les alertes dans Supabase.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.supabase_storage import SupabaseStorage
from core.gazelle_api_client import GazelleAPIClient
from datetime import datetime, timedelta
import json


INSTITUTIONAL_CLIENTS = {
    'Vincent d\'Indy': 'cli_9UMLkteep8EsISbG',
    'Place des Arts': 'cli_HbEwl9rN11pSuDEU',
    'Orford': 'cli_PmqPUBTbPFeCMGmz'
}

ALERT_KEYWORDS = {
    'housse': ['housse enlevée', 'sans housse', 'housse retiree'],
    'alimentation': ['débranché', 'debranche', 'unplugged', 'rallonge', 'besoin rallonge', 'besoin d\'une rallonge'],
    'reservoir': ['réservoir vide', 'reservoir vide', 'tank empty'],
    'environnement': ['fenêtre ouverte', 'fenetre ouverte', 'trop froid', 'fenêtre', 'sec', 'basse', 'critique']
}


def scan_and_create_alerts(client_id, client_name, days_back=7):
    """Scanne un client et crée les alertes."""
    print(f"\n🔍 Scan de: {client_name}")
    print(f"   ID: {client_id}")

    storage = SupabaseStorage()
    graphql = GazelleAPIClient()

    # Date cutoff
    start_date = datetime.now() - timedelta(days=days_back)
    since_date = start_date.isoformat() + "Z"

    # Query GraphQL avec clientId
    query = """
    query GetClientTimeline($clientId: String, $first: Int!) {
        allTimelineEntries(clientId: $clientId, first: $first) {
            edges {
                node {
                    id
                    type
                    occurredAt
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
                    }
                }
            }
        }
    }
    """

    try:
        result = graphql._execute_query(query, {'clientId': client_id, 'first': 100})

        edges = result.get('data', {}).get('allTimelineEntries', {}).get('edges', [])
        entries = [edge['node'] for edge in edges if edge.get('node')]

        print(f"   📊 {len(entries)} entrées récupérées")

        # Filtrer par date
        recent_entries = []
        for entry in entries:
            occurred_str = entry.get('occurredAt')
            if occurred_str:
                try:
                    occurred_dt = datetime.fromisoformat(occurred_str.replace('Z', '+00:00'))
                    if occurred_dt >= start_date.replace(tzinfo=occurred_dt.tzinfo):
                        recent_entries.append(entry)
                except:
                    pass

        print(f"   📅 {len(recent_entries)} entrées dans les {days_back} derniers jours")

        alerts_created = 0
        alerts_skipped = 0
        errors = 0

        for entry in recent_entries:
            entry_id = entry.get('id')
            comment = (entry.get('comment') or '').lower()
            summary = (entry.get('summary') or '').lower()
            combined = f'{comment} {summary}'

            occurred_at = entry.get('occurredAt')
            entry_client_id = entry.get('client', {}).get('id')
            piano = entry.get('piano', {})
            piano_id = piano.get('id') if piano else None
            piano_make = piano.get('make', 'N/A') if piano else 'N/A'
            piano_model = piano.get('model', '') if piano else ''

            # Détecter les alertes
            for alert_type, keywords in ALERT_KEYWORDS.items():
                for keyword in keywords:
                    if keyword in combined:
                        # Alerte détectée !
                        print(f"   🚨 Alerte: {alert_type} - {piano_make} {piano_model}")

                        # Vérifier si elle existe déjà
                        existing = storage.client.table('humidity_alerts').select('id').eq(
                            'timeline_entry_id', entry_id
                        ).execute()

                        if existing.data and len(existing.data) > 0:
                            print(f"      ⏭️  Déjà existante")
                            alerts_skipped += 1
                            break

                        # Créer l'alerte
                        alert_data = {
                            'timeline_entry_id': entry_id,
                            'client_id': entry_client_id,
                            'piano_id': piano_id,  # Peut être ins_xxx
                            'alert_type': alert_type,
                            'description': (comment or summary)[:500],
                            'is_resolved': False,
                            'observed_at': occurred_at,
                            'archived': False
                        }

                        try:
                            response = storage.client.table('humidity_alerts').insert(alert_data).execute()

                            if response.data and len(response.data) > 0:
                                print(f"      ✅ Créée (ID: {response.data[0]['id']})")
                                alerts_created += 1
                            else:
                                print(f"      ⚠️  Pas de données retournées")
                                errors += 1

                        except Exception as e:
                            error_msg = str(e)

                            # Si erreur de contrainte piano_id, essayer sans
                            if 'foreign key' in error_msg.lower() or 'violates' in error_msg.lower():
                                try:
                                    alert_data_no_piano = {**alert_data}
                                    del alert_data_no_piano['piano_id']

                                    response = storage.client.table('humidity_alerts').insert(alert_data_no_piano).execute()

                                    if response.data:
                                        print(f"      ✅ Créée sans piano_id (ID: {response.data[0]['id']})")
                                        alerts_created += 1
                                    else:
                                        print(f"      ❌ Erreur même sans piano_id")
                                        errors += 1
                                except Exception as e2:
                                    print(f"      ❌ Échec: {str(e2)[:80]}")
                                    errors += 1
                            else:
                                print(f"      ❌ Erreur: {error_msg[:80]}")
                                errors += 1

                        break  # Une alerte par entrée

        print(f"   ✅ Terminé: {alerts_created} créée(s), {alerts_skipped} ignorée(s), {errors} erreur(s)")

        return {
            'created': alerts_created,
            'skipped': alerts_skipped,
            'errors': errors
        }

    except Exception as e:
        print(f"   ❌ Erreur scan: {e}")
        return {'created': 0, 'skipped': 0, 'errors': 1}


def main():
    """Fonction principale."""
    print()
    print("🚀 CRÉATION FORCÉE DES ALERTES D'HUMIDITÉ")
    print("=" * 70)
    print()

    total_created = 0
    total_skipped = 0
    total_errors = 0

    for client_name, client_id in INSTITUTIONAL_CLIENTS.items():
        result = scan_and_create_alerts(client_id, client_name, days_back=7)
        total_created += result['created']
        total_skipped += result['skipped']
        total_errors += result['errors']

    print()
    print("=" * 70)
    print(f"📊 RÉSUMÉ GLOBAL:")
    print(f"   ✅ Alertes créées: {total_created}")
    print(f"   ⏭️  Alertes ignorées (déjà existantes): {total_skipped}")
    print(f"   ❌ Erreurs: {total_errors}")
    print()

    if total_created > 0:
        print("💡 PROCHAINES ÉTAPES:")
        print("   1. Rafraîchis le frontend (F5)")
        print("   2. Va sur 'Tableau de bord'")
        print("   3. Les alertes devraient apparaître!")
        print()

    return 0


if __name__ == "__main__":
    exit(main())
