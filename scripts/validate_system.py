#!/usr/bin/env python3
"""
Script de validation système après Grand Ménage.
Vérifie que tous les composants essentiels fonctionnent.
"""

import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_imports():
    """Test 1: Vérifier que tous les imports essentiels fonctionnent."""
    print("=" * 80)
    print("TEST 1: IMPORTS ESSENTIELS")
    print("=" * 80)
    print()

    try:
        from core.supabase_storage import SupabaseStorage
        print("✅ SupabaseStorage")
    except Exception as e:
        print(f"❌ SupabaseStorage: {e}")
        return False

    try:
        from core.gazelle_api_client import GazelleAPIClient
        print("✅ GazelleAPIClient")
    except Exception as e:
        print(f"❌ GazelleAPIClient: {e}")
        return False

    try:
        from modules.alerts.humidity_scanner import HumidityScanner
        print("✅ HumidityScanner")
    except Exception as e:
        print(f"❌ HumidityScanner: {e}")
        return False

    print()
    return True


def test_config():
    """Test 2: Vérifier que la config des alertes est valide."""
    print("=" * 80)
    print("TEST 2: CONFIGURATION ALERTES")
    print("=" * 80)
    print()

    try:
        import json
        config_path = Path(__file__).parent.parent / "config" / "alerts" / "config.json"

        if not config_path.exists():
            print(f"❌ Fichier config manquant: {config_path}")
            return False

        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)

        # Vérifier les catégories (peut être "keywords" ou "alert_keywords")
        categories = ["housse", "alimentation", "reservoir", "environnement"]
        keywords_dict = config.get("keywords") or config.get("alert_keywords", {})

        for cat in categories:
            if cat in keywords_dict:
                count = len(keywords_dict[cat])
                print(f"✅ {cat}: {count} mots-clés")
            else:
                print(f"❌ Catégorie manquante: {cat}")
                return False

        print()
        return True

    except Exception as e:
        print(f"❌ Erreur config: {e}")
        return False


def test_supabase_connection():
    """Test 3: Vérifier connexion Supabase."""
    print("=" * 80)
    print("TEST 3: CONNEXION SUPABASE")
    print("=" * 80)
    print()

    try:
        from core.supabase_storage import SupabaseStorage
        storage = SupabaseStorage()
        print(f"✅ Connexion établie: {storage.api_url}")
        print()
        return True
    except Exception as e:
        print(f"❌ Erreur Supabase: {e}")
        print()
        return False


def test_graphql_connection():
    """Test 4: Vérifier connexion GraphQL Gazelle."""
    print("=" * 80)
    print("TEST 4: CONNEXION GRAPHQL GAZELLE")
    print("=" * 80)
    print()

    try:
        from core.gazelle_api_client import GazelleAPIClient

        client = GazelleAPIClient()

        # Query simple pour tester
        query = """
        query TestQuery {
            allTimelineEntries(first: 1) {
                edges {
                    node {
                        id
                    }
                }
            }
        }
        """

        result = client._execute_query(query, {})

        if result and "data" in result:
            print("✅ Connexion GraphQL OK")
            print()
            return True
        else:
            print("❌ Réponse GraphQL invalide")
            print()
            return False

    except Exception as e:
        print(f"❌ Erreur GraphQL: {e}")
        print()
        return False


def test_vdi_entries():
    """Test 5: Vérifier récupération entrées Vincent d'Indy."""
    print("=" * 80)
    print("TEST 5: RÉCUPÉRATION ENTRÉES VINCENT D'INDY")
    print("=" * 80)
    print()

    try:
        from core.gazelle_api_client import GazelleAPIClient

        VDI_CLIENT_ID = "cli_9UMLkteep8EsISbG"

        client = GazelleAPIClient()

        query = """
        query GetVDI($clientId: String!) {
            allTimelineEntries(first: 10, clientId: $clientId) {
                edges {
                    node {
                        id
                        comment
                        occurredAt
                        client {
                            companyName
                        }
                    }
                }
            }
        }
        """

        result = client._execute_query(query, {"clientId": VDI_CLIENT_ID})

        if result and "data" in result:
            entries = [edge["node"] for edge in result["data"]["allTimelineEntries"]["edges"]]

            if entries:
                print(f"✅ {len(entries)} entrées récupérées")
                print(f"   Client: {entries[0]['client']['companyName']}")
                print(f"   Première entrée: {entries[0]['comment'][:60] if entries[0]['comment'] else 'N/A'}...")
                print()
                return True
            else:
                print("❌ Aucune entrée récupérée")
                print()
                return False
        else:
            print("❌ Erreur lors de la requête")
            print()
            return False

    except Exception as e:
        print(f"❌ Erreur: {e}")
        print()
        return False


def main():
    """Exécute tous les tests de validation."""
    print()
    print("🧪 VALIDATION SYSTÈME APRÈS GRAND MÉNAGE")
    print()

    results = []

    # Test 1: Imports
    results.append(("Imports essentiels", test_imports()))

    # Test 2: Config
    results.append(("Configuration alertes", test_config()))

    # Test 3: Supabase
    results.append(("Connexion Supabase", test_supabase_connection()))

    # Test 4: GraphQL
    results.append(("Connexion GraphQL", test_graphql_connection()))

    # Test 5: VDI
    results.append(("Entrées Vincent d'Indy", test_vdi_entries()))

    # Résumé
    print("=" * 80)
    print("RÉSUMÉ VALIDATION")
    print("=" * 80)
    print()

    all_passed = True
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {name}")
        if not passed:
            all_passed = False

    print()

    if all_passed:
        print("=" * 80)
        print("🎉 TOUS LES TESTS PASSENT - SYSTÈME OPÉRATIONNEL")
        print("=" * 80)
        print()
        return 0
    else:
        print("=" * 80)
        print("⚠️  CERTAINS TESTS ONT ÉCHOUÉ")
        print("=" * 80)
        print()
        return 1


if __name__ == "__main__":
    sys.exit(main())
