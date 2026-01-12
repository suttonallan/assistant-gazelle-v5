#!/usr/bin/env python3
"""
Script de laboratoire pour tester 3 aspects de Vincent d'Indy.

Test 1: Structure des champs de timeline (comment, note, description, summary?)
Test 2: Différence entre allClientLogs vs allTimelineEntries
Test 3: Écart UTC entre Gazelle et machine locale
"""

import sys
import json
from pathlib import Path
from datetime import datetime
import pytz

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.gazelle_api_client import GazelleAPIClient

# Client Vincent d'Indy (École de musique Vincent-d'Indy)
VDI_CLIENT_ID = "cli_9UMLkteep8EsISbG"

def test_1_timeline_fields():
    """Test 1: Structure des champs dans timeline entries."""
    print("=" * 80)
    print("TEST 1: STRUCTURE DES CHAMPS TIMELINE")
    print("=" * 80)
    print()

    graphql = GazelleAPIClient()

    # Query avec clientId pour éviter limite de pagination
    # CHAMPS CONFIRMÉS: comment, summary, occurredAt, type
    query = """
    query GetClientTimeline($clientId: String!) {
        allTimelineEntries(first: 100, clientId: $clientId) {
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
                }
            }
        }
    }
    """

    print(f"📋 Requête GraphQL pour allTimelineEntries (clientId: {VDI_CLIENT_ID})...")
    print()

    result = graphql._execute_query(query, {"clientId": VDI_CLIENT_ID})

    if result and "data" in result:
        data = result["data"]
        timeline_data = data.get("allTimelineEntries", {})
        edges = timeline_data.get("edges", [])
        entries = [edge["node"] for edge in edges]
        print(f"Nombre d'entrées récupérées: {len(entries)}")
        print()

        if entries:
            # Afficher info client
            client_name = entries[0].get("client", {}).get("companyName", "N/A")
            print(f"Client: {client_name}")
            print(f"ID: {VDI_CLIENT_ID}")
            print(f"Nombre d'entrées: {len(entries)}")
            print()

            # Afficher la PREMIÈRE entrée complète (JSON brut)
            print("=" * 80)
            print("PREMIÈRE ENTRÉE (JSON BRUT):")
            print("=" * 80)
            print(json.dumps(entries[0], indent=2, ensure_ascii=False))
            print()

            # Afficher les champs comment et summary des 10 premières entrées
            print("=" * 80)
            print("MAPPING DES CHAMPS (10 premières entrées):")
            print("=" * 80)
            for i, entry in enumerate(entries[:10], 1):
                print(f"\n--- Entrée {i} ---")
                print(f"ID: {entry.get('id')}")
                print(f"Type: {entry.get('type')}")
                print(f"Date: {entry.get('occurredAt')}")
                print(f"  comment   → description (Supabase): {entry.get('comment', 'N/A')[:100] if entry.get('comment') else 'N/A'}")
                print(f"  summary   → title (Supabase):       {entry.get('summary', 'N/A')}")
            print()
        else:
            print("⚠️  Aucune timeline entry trouvée.")
    else:
        print("❌ Erreur lors de la récupération des données.")
        print(json.dumps(result, indent=2))

    print()


def test_2_logs_vs_timeline():
    """Test 2: Analyse des types de timeline entries."""
    print("=" * 80)
    print("TEST 2: ANALYSE DES TYPES D'ENTRÉES")
    print("=" * 80)
    print()

    graphql = GazelleAPIClient()

    # Query avec clientId
    query = """
    query GetTimelineEntries($clientId: String!) {
        allTimelineEntries(first: 100, clientId: $clientId) {
            edges {
                node {
                    id
                    occurredAt
                    type
                    comment
                    summary
                }
            }
        }
    }
    """

    print("📋 Requête GraphQL pour analyser les types...")
    print()

    result = graphql._execute_query(query, {"clientId": VDI_CLIENT_ID})

    if result and "data" in result:
        data = result["data"]
        timeline_data = data.get("allTimelineEntries", {})
        edges = timeline_data.get("edges", [])
        entries = [edge["node"] for edge in edges]

        print(f"Total entrées Vincent d'Indy: {len(entries)}")
        print()

        # Analyse des types
        print("=" * 80)
        print("ANALYSE DES TYPES:")
        print("=" * 80)

        types_count = {}
        for entry in entries:
            entry_type = entry.get("type", "unknown")
            types_count[entry_type] = types_count.get(entry_type, 0) + 1

        for entry_type, count in sorted(types_count.items(), key=lambda x: x[1], reverse=True):
            print(f"  - {entry_type}: {count}")
        print()

    else:
        print("❌ Erreur lors de la récupération des données.")
        print(json.dumps(result, indent=2))

    print()


def test_3_utc_offset():
    """Test 3: Écart UTC entre Gazelle et machine locale."""
    print("=" * 80)
    print("TEST 3: ÉCART UTC GAZELLE vs MACHINE LOCALE")
    print("=" * 80)
    print()

    graphql = GazelleAPIClient()

    # Query avec clientId
    query = """
    query GetRecentEntries($clientId: String!) {
        allTimelineEntries(first: 1, clientId: $clientId) {
            edges {
                node {
                    id
                    occurredAt
                    type
                }
            }
        }
    }
    """

    print("📋 Requête GraphQL pour 1 entrée récente...")
    print()

    # Capturer l'heure AVANT la requête
    local_before = datetime.now()
    local_before_utc = datetime.now(pytz.UTC)

    result = graphql._execute_query(query, {"clientId": VDI_CLIENT_ID})

    # Capturer l'heure APRÈS la requête
    local_after = datetime.now()
    local_after_utc = datetime.now(pytz.UTC)

    print("=" * 80)
    print("HORAIRES MACHINE LOCALE:")
    print("=" * 80)
    print(f"Avant requête (local):     {local_before.isoformat()}")
    print(f"Avant requête (UTC):       {local_before_utc.isoformat()}")
    print(f"Après requête (local):     {local_after.isoformat()}")
    print(f"Après requête (UTC):       {local_after_utc.isoformat()}")
    print()

    if result and "data" in result:
        data = result["data"]
        timeline_data = data.get("allTimelineEntries", {})
        edges = timeline_data.get("edges", [])
        entries = [edge["node"] for edge in edges]

        if entries:
            entry = entries[0]

            print("=" * 80)
            print("HORAIRES GAZELLE (ENTRÉE):")
            print("=" * 80)
            print(f"Entry ID: {entry['id']}")
            print(f"Type: {entry.get('type')}")
            print()
            print(f"occurredAt (brut):  {entry.get('occurredAt')}")
            print()

            # Parser occurredAt
            occurred_at_str = entry.get("occurredAt")
            if occurred_at_str:
                try:
                    # Parser ISO format
                    occurred_at = datetime.fromisoformat(occurred_at_str.replace("Z", "+00:00"))

                    print("=" * 80)
                    print("ANALYSE ÉCART UTC:")
                    print("=" * 80)
                    print(f"occurredAt parsé:           {occurred_at.isoformat()}")
                    print(f"Timezone occurredAt:        {occurred_at.tzinfo}")
                    print()

                    # Calculer écart avec heure actuelle UTC
                    delta = local_after_utc - occurred_at

                    print(f"Heure actuelle (UTC):       {local_after_utc.isoformat()}")
                    print(f"occurredAt (UTC):           {occurred_at.isoformat()}")
                    print(f"Écart (actuelle - occurred): {delta}")
                    print(f"Écart en jours:             {delta.days} jours")
                    print()

                    # Timezone info
                    print("=" * 80)
                    print("TIMEZONE INFO MACHINE:")
                    print("=" * 80)
                    local_tz = datetime.now().astimezone().tzinfo
                    print(f"Timezone locale:            {local_tz}")
                    print(f"UTC offset:                 {local_after.astimezone().strftime('%z')}")
                    print()

                except Exception as e:
                    print(f"❌ Erreur lors du parsing de occurredAt: {e}")
            else:
                print("⚠️  occurredAt est None ou vide")
        else:
            print("⚠️  Aucune entrée trouvée")
    else:
        print("❌ Erreur lors de la récupération des données.")
        print(json.dumps(result, indent=2))

    print()


def main():
    """Exécute les 3 tests en séquence."""
    print()
    print("🧪 LABORATOIRE VINCENT D'INDY - 3 TESTS")
    print()

    try:
        test_1_timeline_fields()
        test_2_logs_vs_timeline()
        test_3_utc_offset()

        print("=" * 80)
        print("✅ TOUS LES TESTS COMPLÉTÉS")
        print("=" * 80)
        print()

    except Exception as e:
        print()
        print("=" * 80)
        print("❌ ERREUR LORS DES TESTS")
        print("=" * 80)
        print(f"Erreur: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
