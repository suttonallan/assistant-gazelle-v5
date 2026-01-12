#!/usr/bin/env python3
"""
Global Watcher - Version finale
Récupère toutes les activités des dernières 24h avec piano et client.
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
import json

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.gazelle_api_client import GazelleAPIClient


def test_global_watcher():
    """
    Test du Global Watcher - Récupère activités 24h avec piano et client.
    """
    print("=" * 80)
    print("GLOBAL WATCHER - ACTIVITÉS 24H")
    print("=" * 80)
    print()

    client = GazelleAPIClient()

    # Calculer timestamp 24h en arrière
    now = datetime.utcnow()
    yesterday = now - timedelta(hours=24)
    timestamp_24h = yesterday.strftime("%Y-%m-%dT%H:%M:%SZ")

    print(f"Recherche depuis: {timestamp_24h}")
    print(f"Jusqu'à maintenant: {now.strftime('%Y-%m-%dT%H:%M:%SZ')}")
    print()

    # Query GraphQL pour récupérer les activités récentes avec piano et client
    # Note: L'API ne supporte pas 'since', on récupère les 100 dernières et on filtre en Python
    query = """
    query GetRecentActivities {
        allTimelineEntries(first: 100) {
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

    variables = {}

    print("📡 Exécution requête GraphQL...")
    print()

    try:
        result = client._execute_query(query, variables)

        if result and "data" in result:
            data = result["data"]
            timeline_data = data.get("allTimelineEntries", {})
            edges = timeline_data.get("edges", [])
            all_entries = [edge["node"] for edge in edges]

            # Filtrer pour les dernières 24h
            entries = []
            for entry in all_entries:
                occurred_at_str = entry.get("occurredAt")
                if occurred_at_str:
                    try:
                        occurred_at = datetime.fromisoformat(occurred_at_str.replace("Z", "+00:00"))
                        if occurred_at >= yesterday.replace(tzinfo=occurred_at.tzinfo):
                            entries.append(entry)
                    except:
                        pass  # Ignore parsing errors

            print("=" * 80)
            print(f"RÉSULTATS: {len(entries)} activités dans les 24h (sur {len(all_entries)} récupérées)")
            print("=" * 80)
            print()

            if entries:
                # Statistiques par type
                stats_by_type = {}
                stats_by_client = {}
                entries_with_piano = 0

                for entry in entries:
                    entry_type = entry.get("type", "unknown")
                    stats_by_type[entry_type] = stats_by_type.get(entry_type, 0) + 1

                    client_name = entry.get("client", {}).get("companyName", "N/A")
                    if client_name != "N/A":
                        stats_by_client[client_name] = stats_by_client.get(client_name, 0) + 1

                    if entry.get("piano"):
                        entries_with_piano += 1

                # Afficher statistiques
                print("=" * 80)
                print("STATISTIQUES PAR TYPE:")
                print("=" * 80)
                for entry_type, count in sorted(stats_by_type.items(), key=lambda x: x[1], reverse=True):
                    print(f"  {entry_type}: {count}")
                print()

                print("=" * 80)
                print("STATISTIQUES PAR CLIENT (top 10):")
                print("=" * 80)
                for client_name, count in sorted(stats_by_client.items(), key=lambda x: x[1], reverse=True)[:10]:
                    print(f"  {client_name}: {count}")
                print()

                print(f"Entrées avec piano: {entries_with_piano}/{len(entries)}")
                print()

                # Chercher un exemple complet (avec piano ET client)
                print("=" * 80)
                print("EXEMPLE COMPLET (NOTE + PIANO + CLIENT):")
                print("=" * 80)
                print()

                example_found = False
                for entry in entries:
                    if entry.get("piano") and entry.get("client") and entry.get("comment"):
                        print("📋 ENTRÉE COMPLÈTE:")
                        print("-" * 80)
                        print(json.dumps(entry, indent=2, ensure_ascii=False))
                        print()

                        # Afficher dans un format lisible
                        print("=" * 80)
                        print("FORMAT LISIBLE:")
                        print("=" * 80)
                        print(f"🗓️  Date: {entry.get('occurredAt')}")
                        print(f"📝 Type: {entry.get('type')}")
                        print()
                        print(f"👤 Client:")
                        print(f"   ID: {entry.get('client', {}).get('id')}")
                        print(f"   Nom: {entry.get('client', {}).get('companyName')}")
                        print()
                        print(f"🎹 Piano:")
                        print(f"   ID: {entry.get('piano', {}).get('id')}")
                        print(f"   Marque: {entry.get('piano', {}).get('make')}")
                        print(f"   Modèle: {entry.get('piano', {}).get('model')}")
                        print(f"   Série: {entry.get('piano', {}).get('serialNumber')}")
                        print()
                        print(f"💬 Note:")
                        print(f"   {entry.get('comment', 'N/A')[:200]}")
                        print()

                        example_found = True
                        break

                if not example_found:
                    print("⚠️  Aucune entrée complète (piano + client + comment) trouvée.")
                    print()

                    # Afficher au moins une entrée avec client
                    for entry in entries:
                        if entry.get("client"):
                            print("📋 EXEMPLE (sans piano):")
                            print("-" * 80)
                            print(f"Date: {entry.get('occurredAt')}")
                            print(f"Type: {entry.get('type')}")
                            print(f"Client: {entry.get('client', {}).get('companyName')}")
                            print(f"Comment: {entry.get('comment', 'N/A')[:100]}")
                            print()
                            break

                # Chercher des alertes humidité potentielles
                print("=" * 80)
                print("ALERTES HUMIDITÉ POTENTIELLES:")
                print("=" * 80)
                print()

                keywords = ["débranché", "debranche", "housse", "réservoir", "reservoir", "unplugged"]
                alerts_found = []

                for entry in entries:
                    comment = entry.get("comment", "")
                    if comment:
                        for keyword in keywords:
                            if keyword in comment.lower():
                                alerts_found.append({
                                    "date": entry.get("occurredAt"),
                                    "client": entry.get("client", {}).get("companyName", "N/A"),
                                    "piano": f"{entry.get('piano', {}).get('make', 'N/A')} {entry.get('piano', {}).get('model', 'N/A')}",
                                    "comment": comment[:100],
                                    "keyword": keyword
                                })
                                break

                if alerts_found:
                    print(f"🚨 {len(alerts_found)} alertes détectées:")
                    print()
                    for i, alert in enumerate(alerts_found[:5], 1):
                        print(f"Alerte {i}:")
                        print(f"  Date: {alert['date']}")
                        print(f"  Client: {alert['client']}")
                        print(f"  Piano: {alert['piano']}")
                        print(f"  Mot-clé: {alert['keyword']}")
                        print(f"  Note: {alert['comment']}...")
                        print()
                else:
                    print("✅ Aucune alerte détectée dans les dernières 24h")
                    print()

            else:
                print("⚠️  Aucune activité trouvée dans les dernières 24h")
                print()

        else:
            print("❌ Erreur lors de la récupération des données")
            if result:
                print(json.dumps(result, indent=2))

    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()


def analyze_architecture():
    """
    Analyse l'architecture actuelle et identifie les fichiers obsolètes.
    """
    print()
    print("=" * 80)
    print("ANALYSE ARCHITECTURE - FICHIERS OBSOLÈTES")
    print("=" * 80)
    print()

    # Fichiers dans l'archive qui sont potentiellement obsolètes
    obsolete_patterns = [
        "# Anciennes routes API redondantes",
        "_ARCHIVE_SYSTEME/api/routes.py",
        "_ARCHIVE_SYSTEME/api/timeline_routes.py",
        "_ARCHIVE_SYSTEME/api/client_routes.py",
        "_ARCHIVE_SYSTEME/api/piano_routes.py",

        "# Anciens scripts de sync",
        "_ARCHIVE_SYSTEME/scripts/sync_*.py",
        "_ARCHIVE_SYSTEME/scripts/test_*.py (sauf test_global.py)",

        "# Anciennes config",
        "_ARCHIVE_SYSTEME/config/*.old",
        "_ARCHIVE_SYSTEME/config/*.bak",

        "# Documentation obsolète",
        "_ARCHIVE_SYSTEME/docs/*VIEUX*.md",
        "_ARCHIVE_SYSTEME/docs/*OLD*.md",
        "_ARCHIVE_SYSTEME/*DIAGNOSTIC*.md",

        "# Fichiers de déploiement obsolètes",
        "_ARCHIVE_SYSTEME/DEPLOY_*.md",
        "_ARCHIVE_SYSTEME/DEPLOYMENT_*.md",

        "# Guides redondants",
        "_ARCHIVE_SYSTEME/GUIDE_*.md (sauf GUIDE_RETOUR_ARRIERE.md)",
        "_ARCHIVE_SYSTEME/DEMARRAGE_*.md",
        "_ARCHIVE_SYSTEME/DEV_LOCAL_*.md",
    ]

    print("FICHIERS/PATTERNS À CONSIDÉRER POUR SUPPRESSION:")
    print()
    for pattern in obsolete_patterns:
        if pattern.startswith("#"):
            print(f"\n{pattern}")
        else:
            print(f"  ❌ {pattern}")

    print()
    print("=" * 80)
    print("ARCHITECTURE PROPRE RECOMMANDÉE:")
    print("=" * 80)
    print()
    print("GARDER:")
    print("  ✅ core/                    - Modules de base validés")
    print("  ✅ api/                     - Routes FastAPI validées")
    print("  ✅ modules/alerts/          - Scanner humidité validé")
    print("  ✅ config/alerts/           - Configuration validée")
    print("  ✅ scripts/lab_check_vdi.py - Test VDI validé")
    print("  ✅ scripts/test_global.py   - Global Watcher validé")
    print("  ✅ scripts/validate_system.py - Validation système")
    print("  ✅ sql/                     - Migrations Supabase")
    print("  ✅ docs/MIGRATION_*.md      - Doc migration V4→V5")
    print("  ✅ GUIDE_RETOUR_ARRIERE.md  - Procédure rollback")
    print("  ✅ GRAND_MENAGE_COMPLET.md  - Doc du ménage")
    print("  ✅ RAPPORT_FINAL_MENAGE.md  - Rapport final")
    print()
    print("SUPPRIMER (après validation finale):")
    print("  ❌ _ARCHIVE_SYSTEME/        - Archive complète (après 1-2 semaines)")
    print()


def main():
    """Point d'entrée principal."""
    print()
    print("🌍 GLOBAL WATCHER - VERSION FINALE")
    print()

    try:
        # Test 1: Global Watcher
        test_global_watcher()

        # Test 2: Analyse architecture
        analyze_architecture()

        print("=" * 80)
        print("✅ TESTS TERMINÉS")
        print("=" * 80)
        print()

    except Exception as e:
        print()
        print("=" * 80)
        print("❌ ERREUR")
        print("=" * 80)
        print(f"Erreur: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
