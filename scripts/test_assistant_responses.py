#!/usr/bin/env python3
"""
Script de test pour raffiner les réponses de l'assistant.

Utilise de vraies données clients pour tester différents formats de résumés.
Permet de comparer facilement les versions et d'itérer rapidement.

Usage:
    python scripts/test_assistant_responses.py
    python scripts/test_assistant_responses.py --client "cli_xxx" --verbose
    python scripts/test_assistant_responses.py --test-all
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, List
import json

# Ajouter le projet au path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from modules.assistant.services.parser import ConversationalParser, QueryType
from modules.assistant.services.queries import GazelleQueries
from api.assistant import _format_response
from core.supabase_storage import SupabaseStorage


class AssistantTester:
    """Testeur interactif pour raffiner les réponses de l'assistant."""

    def __init__(self):
        self.parser = ConversationalParser()
        self.queries = GazelleQueries()
        self.storage = SupabaseStorage()
        self.results_file = Path(__file__).parent.parent / 'test_results.json'

    def load_test_scenarios(self, enabled_only: bool = False) -> List[Dict]:
        """
        Charge les scénarios de test depuis questions_test.json.

        Args:
            enabled_only: Si True, charge seulement les questions activées

        Returns:
            Liste de scénarios de test
        """
        questions_file = Path(__file__).parent / 'questions_test.json'

        if not questions_file.exists():
            # Fallback vers scénarios par défaut
            return [
                {
                    'name': 'Journée chargée technicien',
                    'question': '.mes rv',
                    'user_id': 'nlessard@piano-tek.com',
                    'description': 'Test résumé quotidien avec plusieurs RV'
                },
                {
                    'name': 'Recherche client riche',
                    'question': 'client Yannick',
                    'user_id': 'anonymous',
                    'description': 'Client célèbre'
                },
            ]

        with open(questions_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        questions = data['questions']

        if enabled_only:
            questions = [q for q in questions if q.get('enabled', False)]

        # Convertir au format attendu
        scenarios = []
        for q in questions:
            scenarios.append({
                'name': f"{q['category']} - {q['id']}",
                'question': q['question'],
                'user_id': q['user'],
                'description': q['description'],
                'priority': q.get('priority', 'medium'),
                'category': q['category']
            })

        return scenarios

    def find_rich_clients(self, limit: int = 5) -> List[Dict]:
        """
        Trouve les clients avec le plus de données (pour tests intéressants).

        Critères:
        - Plusieurs rendez-vous
        - Plusieurs pianos
        - Historique timeline riche
        """
        print("🔍 Recherche de clients avec données riches...\n")

        # Utiliser la méthode de recherche existante avec des noms connus
        known_names = [
            'Yannick', 'Université', 'Conservatoire', 'Studio',
            'Anne-Marie', 'Marie', 'Jean', 'Michel'
        ]

        results = []
        for name in known_names:
            clients = self.queries.search_clients([name], limit=3)
            for client in clients:
                client_name = f"{client.get('first_name', '')} {client.get('name') or client.get('last_name', '')}".strip()
                if not client_name:
                    client_name = client.get('company_name', 'N/A')

                results.append({
                    'client_id': client.get('external_id', 'N/A'),
                    'name': client_name,
                    'city': client.get('city', 'N/A'),
                    'source': client.get('_source', 'client'),
                    'data': client
                })

        # Dédupliquer par ID
        seen = set()
        unique_results = []
        for r in results:
            if r['client_id'] not in seen:
                seen.add(r['client_id'])
                unique_results.append(r)

        return unique_results[:limit]

    def test_scenario(self, scenario: Dict, template_version: str = 'current') -> Dict:
        """
        Teste un scénario et retourne le résultat.

        Args:
            scenario: Dictionnaire avec question, user_id, etc.
            template_version: Version du template à utiliser

        Returns:
            Résultat du test avec métadonnées
        """
        print(f"\n{'='*70}")
        print(f"📝 Test: {scenario['name']}")
        print(f"{'='*70}")
        print(f"Question: {scenario['question']}")
        print(f"User: {scenario['user_id']}")
        print(f"Description: {scenario['description']}\n")

        # Parser la question
        parsed = self.parser.parse(scenario['question'])
        print(f"🧠 Parsing:")
        print(f"   Type: {parsed['query_type']}")
        print(f"   Confiance: {parsed.get('confidence', 0)*100:.0f}%")
        print(f"   Params: {parsed.get('params', {})}\n")

        # Exécuter la requête
        results = self.queries.execute_query(
            parsed['query_type'],
            parsed.get('params', {}),
            scenario['user_id']
        )

        print(f"📊 Résultats:")
        print(f"   Type: {results.get('type')}")
        print(f"   Count: {results.get('count', 0)}")

        # Formatter la réponse
        response = _format_response(parsed['query_type'], results)

        print(f"\n💬 Réponse générée:")
        print("-" * 70)
        print(response)
        print("-" * 70)

        return {
            'timestamp': datetime.now().isoformat(),
            'scenario': scenario,
            'template_version': template_version,
            'parsed': parsed,
            'results': results,
            'response': response,
            'user_rating': None,  # À remplir manuellement
            'user_comment': None
        }

    def interactive_test(self):
        """Mode interactif pour tester et noter les réponses."""
        print("🎮 MODE INTERACTIF - Test de l'Assistant\n")

        while True:
            print("\nOptions:")
            print("1. Tester un scénario prédéfini")
            print("2. Tester une question personnalisée")
            print("3. Voir les clients avec données riches")
            print("4. Voir historique des tests")
            print("5. Quitter")

            choice = input("\nChoix: ").strip()

            if choice == '1':
                scenarios = self.load_test_scenarios()
                print("\nScénarios disponibles:")
                for i, s in enumerate(scenarios, 1):
                    print(f"{i}. {s['name']} - {s['description']}")

                idx = int(input("\nNuméro du scénario: ")) - 1
                if 0 <= idx < len(scenarios):
                    result = self.test_scenario(scenarios[idx])
                    self._rate_and_save(result)

            elif choice == '2':
                question = input("\nQuestion: ")
                user_id = input("User ID (ou 'anonymous'): ").strip() or 'anonymous'

                scenario = {
                    'name': 'Test personnalisé',
                    'question': question,
                    'user_id': user_id,
                    'description': 'Test manuel'
                }

                result = self.test_scenario(scenario)
                self._rate_and_save(result)

            elif choice == '3':
                clients = self.find_rich_clients(10)
                print("\n📚 Clients avec le plus de données:\n")
                for i, c in enumerate(clients, 1):
                    print(f"{i}. {c['name']} ({c['city']})")
                    print(f"   • ID: {c['client_id']}")
                    print(f"   • Pianos: {c['piano_count']}")
                    print()

            elif choice == '4':
                self._show_test_history()

            elif choice == '5':
                print("\n👋 Au revoir!")
                break

    def _rate_and_save(self, result: Dict):
        """Demande une note et sauvegarde le résultat."""
        print("\n" + "="*70)
        print("📊 ÉVALUATION")
        print("="*70)
        print("\nMode d'évaluation:")
        print("1. Évaluation structurée (note + commentaire)")
        print("2. Feedback en langage naturel")
        print("3. Passer (pas d'évaluation)")

        eval_mode = input("\nChoix (1-3): ").strip()

        if eval_mode == '1':
            # Mode structuré classique
            rating = input("\nNote (1-5): ").strip()
            if rating:
                result['user_rating'] = int(rating)

            comment = input("Commentaire: ").strip()
            if comment:
                result['user_comment'] = comment

        elif eval_mode == '2':
            # Mode langage naturel
            print("\n💬 Feedback en langage naturel")
            print("Exemples:")
            print("  • Tu aurais dû me dire ceci: ...")
            print("  • La réponse devrait inclure ...")
            print("  • Trop verbeux, simplifie en ...")
            print("  • Manque l'information sur ...")
            print("\nTon feedback (Enter pour terminer, ligne vide pour finir):")

            feedback_lines = []
            while True:
                line = input()
                if not line:
                    break
                feedback_lines.append(line)

            if feedback_lines:
                result['natural_feedback'] = '\n'.join(feedback_lines)
                result['feedback_mode'] = 'natural'

                # Essayer d'extraire une note implicite du feedback
                feedback_lower = result['natural_feedback'].lower()
                if any(word in feedback_lower for word in ['excellent', 'parfait', 'impeccable']):
                    result['implicit_rating'] = 5
                elif any(word in feedback_lower for word in ['très bon', 'bien']):
                    result['implicit_rating'] = 4
                elif any(word in feedback_lower for word in ['correct', 'acceptable', 'ok']):
                    result['implicit_rating'] = 3
                elif any(word in feedback_lower for word in ['insuffisant', 'mauvais', 'pas bon']):
                    result['implicit_rating'] = 2
                elif any(word in feedback_lower for word in ['terrible', 'inutilisable', 'incorrect']):
                    result['implicit_rating'] = 1

        elif eval_mode == '3':
            print("\n⏭️  Évaluation passée")
            result['feedback_mode'] = 'skipped'

        # Sauvegarder
        self._save_result(result)
        print("\n✅ Résultat sauvegardé!")

    def _save_result(self, result: Dict):
        """Sauvegarde un résultat de test."""
        results = []

        if self.results_file.exists():
            with open(self.results_file, 'r', encoding='utf-8') as f:
                results = json.load(f)

        results.append(result)

        with open(self.results_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

    def _show_test_history(self):
        """Affiche l'historique des tests."""
        if not self.results_file.exists():
            print("\n❌ Aucun test sauvegardé.")
            return

        with open(self.results_file, 'r', encoding='utf-8') as f:
            results = json.load(f)

        print(f"\n📚 Historique des tests ({len(results)} tests)\n")

        for i, r in enumerate(results[-10:], 1):  # 10 derniers
            timestamp = r.get('timestamp', 'N/A')[:19]
            scenario_name = r['scenario']['name']
            rating = r.get('user_rating', '?')
            implicit_rating = r.get('implicit_rating')

            print(f"{i}. [{timestamp}] {scenario_name}")

            # Afficher note structurée
            if rating != '?' and rating is not None:
                stars = '⭐' * int(rating)
                print(f"   Note: {stars} ({rating}/5)")
            # Ou note implicite du feedback naturel
            elif implicit_rating:
                stars = '⭐' * int(implicit_rating)
                print(f"   Note implicite: {stars} ({implicit_rating}/5)")

            # Afficher commentaire structuré
            if r.get('user_comment'):
                print(f"   💬 {r['user_comment']}")

            # Afficher feedback naturel
            if r.get('natural_feedback'):
                print(f"   🗣️  Feedback naturel:")
                for line in r['natural_feedback'].split('\n'):
                    print(f"      {line}")

            print()


def main():
    """Point d'entrée principal."""
    import argparse

    parser = argparse.ArgumentParser(description='Tester et raffiner les réponses de l\'assistant')
    parser.add_argument('--interactive', '-i', action='store_true', help='Mode interactif')
    parser.add_argument('--test-all', action='store_true', help='Tester tous les scénarios')
    parser.add_argument('--test-enabled', action='store_true', help='Tester seulement les scénarios activés')
    parser.add_argument('--rich-clients', action='store_true', help='Afficher clients avec données riches')
    parser.add_argument('--question', '-q', type=str, help='Tester une question spécifique')
    parser.add_argument('--user', '-u', type=str, default='anonymous', help='User ID')

    args = parser.parse_args()

    tester = AssistantTester()

    if args.interactive or len(sys.argv) == 1:
        tester.interactive_test()

    elif args.rich_clients:
        clients = tester.find_rich_clients(10)
        print("\n📚 Clients trouvés avec données:\n")
        for i, c in enumerate(clients, 1):
            print(f"{i}. {c['name']} ({c['city']})")
            print(f"   • ID: {c['client_id']}")
            print(f"   • Type: {c.get('source', 'client')}")
            print()

    elif args.test_all or args.test_enabled:
        # Tester toutes OU seulement celles activées
        enabled_only = args.test_enabled
        scenarios = tester.load_test_scenarios(enabled_only=enabled_only)

        label = "activés" if enabled_only else "total"
        print(f"\n🧪 Test de {len(scenarios)} scénarios {label}...\n")

        for scenario in scenarios:
            result = tester.test_scenario(scenario)
            tester._save_result(result)
            print("\n" + "="*70 + "\n")

        print(f"\n✅ Test terminé! Résultats sauvegardés dans test_results.json")

    elif args.question:
        scenario = {
            'name': 'Test CLI',
            'question': args.question,
            'user_id': args.user,
            'description': 'Test depuis ligne de commande'
        }
        tester.test_scenario(scenario)


if __name__ == '__main__':
    main()
