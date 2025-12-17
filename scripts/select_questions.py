#!/usr/bin/env python3
"""
Sélecteur interactif de questions de test.

Interface SUPER FACILE pour choisir quelles questions tester.
"""

import json
from pathlib import Path
from typing import List, Dict


class QuestionSelector:
    """Sélecteur interactif de questions."""

    def __init__(self):
        self.questions_file = Path(__file__).parent / 'questions_test.json'
        self.questions = self.load_questions()

    def load_questions(self) -> List[Dict]:
        """Charge les questions depuis le fichier JSON."""
        with open(self.questions_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data['questions']

    def save_questions(self):
        """Sauvegarde les questions modifiées."""
        with open(self.questions_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        data['questions'] = self.questions

        with open(self.questions_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        print("\n✅ Sélection sauvegardée!")

    def show_summary(self):
        """Affiche un résumé des questions."""
        total = len(self.questions)
        enabled = sum(1 for q in self.questions if q['enabled'])
        disabled = total - enabled

        by_category = {}
        for q in self.questions:
            cat = q['category']
            by_category[cat] = by_category.get(cat, {'total': 0, 'enabled': 0})
            by_category[cat]['total'] += 1
            if q['enabled']:
                by_category[cat]['enabled'] += 1

        print("\n" + "="*70)
        print("📊 RÉSUMÉ DES QUESTIONS")
        print("="*70)
        print(f"Total: {total} questions")
        print(f"✅ Activées: {enabled}")
        print(f"❌ Désactivées: {disabled}\n")

        print("Par catégorie:")
        for cat, stats in sorted(by_category.items()):
            enabled_count = stats['enabled']
            total_count = stats['total']
            percentage = (enabled_count / total_count * 100) if total_count > 0 else 0
            status = "✅" if enabled_count > 0 else "❌"
            print(f"  {status} {cat}: {enabled_count}/{total_count} ({percentage:.0f}%)")

    def quick_select(self):
        """Sélection rapide par présets."""
        print("\n🚀 SÉLECTION RAPIDE\n")
        print("Choisis un preset:")
        print("1. Essentiels uniquement (16 questions)")
        print("2. Haute priorité (11 questions)")
        print("3. Haute + Moyenne priorité (23 questions)")
        print("4. Toutes les questions (40 questions)")
        print("5. Aucune (tout désactiver)")
        print("6. Retour")

        choice = input("\nChoix: ").strip()

        if choice == '1':
            # Garde seulement celles déjà enabled par défaut
            for q in self.questions:
                # Déjà configuré dans le JSON
                pass
            print("\n✅ Preset 'Essentiels' appliqué (16 questions)")

        elif choice == '2':
            for q in self.questions:
                q['enabled'] = (q['priority'] == 'high')
            print("\n✅ Preset 'Haute priorité' appliqué (11 questions)")

        elif choice == '3':
            for q in self.questions:
                q['enabled'] = (q['priority'] in ['high', 'medium'])
            print("\n✅ Preset 'Haute + Moyenne' appliqué (23 questions)")

        elif choice == '4':
            for q in self.questions:
                q['enabled'] = True
            print("\n✅ Preset 'Toutes' appliqué (40 questions)")

        elif choice == '5':
            for q in self.questions:
                q['enabled'] = False
            print("\n✅ Preset 'Aucune' appliqué (0 questions)")

        self.save_questions()
        self.show_summary()

    def select_by_category(self):
        """Sélection par catégorie."""
        categories = sorted(set(q['category'] for q in self.questions))

        print("\n📁 SÉLECTION PAR CATÉGORIE\n")
        for i, cat in enumerate(categories, 1):
            count = sum(1 for q in self.questions if q['category'] == cat)
            enabled = sum(1 for q in self.questions if q['category'] == cat and q['enabled'])
            status = "✅" if enabled > 0 else "❌"
            print(f"{i:2d}. {status} {cat} ({enabled}/{count})")

        print(f"\n{len(categories)+1}. Retour")

        choice = input("\nNuméro de catégorie à activer/désactiver (ou 'a' pour tout activer): ").strip()

        if choice.lower() == 'a':
            cat_idx = int(input("Quelle catégorie activer? ")) - 1
            if 0 <= cat_idx < len(categories):
                selected_cat = categories[cat_idx]
                for q in self.questions:
                    if q['category'] == selected_cat:
                        q['enabled'] = True
                self.save_questions()
                print(f"\n✅ Toutes les questions de '{selected_cat}' activées!")

        elif choice.isdigit():
            cat_idx = int(choice) - 1
            if 0 <= cat_idx < len(categories):
                selected_cat = categories[cat_idx]

                # Afficher les questions de cette catégorie
                cat_questions = [q for q in self.questions if q['category'] == selected_cat]
                print(f"\nQuestions dans '{selected_cat}':\n")
                for q in cat_questions:
                    status = "✅" if q['enabled'] else "❌"
                    print(f"  {status} {q['id']:2d}. {q['question']}")

                toggle = input("\nActiver (a) ou Désactiver (d) toutes? ").strip().lower()
                if toggle == 'a':
                    for q in cat_questions:
                        q['enabled'] = True
                elif toggle == 'd':
                    for q in cat_questions:
                        q['enabled'] = False

                self.save_questions()
                self.show_summary()

    def select_individual(self):
        """Sélection individuelle de questions."""
        print("\n📝 SÉLECTION INDIVIDUELLE\n")

        # Afficher toutes les questions
        for q in self.questions:
            status = "✅" if q['enabled'] else "❌"
            priority_icon = {"high": "🔴", "medium": "🟡", "low": "⚪"}[q['priority']]
            print(f"{q['id']:2d}. {status} {priority_icon} {q['question'][:50]:50s} - {q['category']}")

        print("\nCommandes:")
        print("  Numéro(s) pour toggle (ex: 1,5,12)")
        print("  'r' pour retour")

        choice = input("\n> ").strip()

        if choice.lower() == 'r':
            return

        # Parser les numéros
        try:
            numbers = [int(n.strip()) for n in choice.split(',')]
            for num in numbers:
                q = next((q for q in self.questions if q['id'] == num), None)
                if q:
                    q['enabled'] = not q['enabled']
                    status = "✅ activée" if q['enabled'] else "❌ désactivée"
                    print(f"  Q{num}: {status}")

            self.save_questions()
            print("\n✅ Modifications sauvegardées!")

        except ValueError:
            print("❌ Format invalide. Utilisez: 1,5,12")

    def view_enabled(self):
        """Affiche seulement les questions activées."""
        enabled = [q for q in self.questions if q['enabled']]

        print("\n✅ QUESTIONS ACTIVÉES\n")

        if not enabled:
            print("Aucune question activée.")
            return

        by_category = {}
        for q in enabled:
            cat = q['category']
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(q)

        for cat in sorted(by_category.keys()):
            print(f"\n📁 {cat}")
            for q in by_category[cat]:
                print(f"   {q['id']:2d}. {q['question']}")

        print(f"\nTotal: {len(enabled)} questions activées")

    def run(self):
        """Lance l'interface interactive."""
        print("\n" + "="*70)
        print("🎯 SÉLECTEUR DE QUESTIONS DE TEST")
        print("="*70)

        while True:
            self.show_summary()

            print("\n📋 MENU\n")
            print("1. 🚀 Sélection rapide (presets)")
            print("2. 📁 Sélection par catégorie")
            print("3. 📝 Sélection individuelle")
            print("4. 👀 Voir questions activées")
            print("5. ✅ Terminer et sauvegarder")

            choice = input("\nChoix: ").strip()

            if choice == '1':
                self.quick_select()

            elif choice == '2':
                self.select_by_category()

            elif choice == '3':
                self.select_individual()

            elif choice == '4':
                self.view_enabled()
                input("\nAppuyez sur Entrée pour continuer...")

            elif choice == '5':
                self.save_questions()
                enabled_count = sum(1 for q in self.questions if q['enabled'])
                print(f"\n🎉 Terminé! {enabled_count} questions sélectionnées.")
                print("\nPour tester, lancez:")
                print("  python3 scripts/test_assistant_responses.py --test-enabled")
                break

            else:
                print("\n❌ Choix invalide")


def main():
    """Point d'entrée principal."""
    selector = QuestionSelector()
    selector.run()


if __name__ == '__main__':
    main()
