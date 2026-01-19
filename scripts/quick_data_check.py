#!/usr/bin/env python3
"""
🔍 Vérification RAPIDE des données pour l'assistant chat (version robuste)
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.supabase_storage import SupabaseStorage

def main():
    storage = SupabaseStorage()

    print("\n" + "=" * 80)
    print("🔍 VÉRIFICATION RAPIDE - DONNÉES ASSISTANT CHAT")
    print("=" * 80 + "\n")

    # Tables principales
    tables = {
        'gazelle_appointments': 'Rendez-vous (Questions 1-14)',
        'gazelle_clients': 'Clients (Questions 15-26)',
        'gazelle_contacts': 'Contacts',
        'gazelle_pianos': 'Pianos (Questions 27-34)',
        'gazelle_timeline_entries': 'Timeline/Historique',
        'users': 'Utilisateurs/Techniciens',
    }

    results = {}

    for table, description in tables.items():
        try:
            result = storage.client.table(table)\
                .select('id', count='exact')\
                .execute()

            count = result.count or 0
            results[table] = count

            status = "✅" if count > 0 else "❌"
            print(f"{status} {description:<40} {count:>10,} entrées")

        except Exception as e:
            results[table] = 0
            print(f"❌ {description:<40} ERREUR: {str(e)[:40]}")

    print("\n" + "-" * 80)

    # Résumé global
    total_entries = sum(results.values())
    print(f"\n📊 TOTAL: {total_entries:,} entrées dans toutes les tables")

    # Évaluation
    print("\n" + "=" * 80)
    print("🎯 ÉVALUATION POUR LES 40 QUESTIONS")
    print("=" * 80 + "\n")

    checks = []

    # Check RV
    rv_count = results.get('gazelle_appointments', 0)
    if rv_count >= 100:
        checks.append(("✅", "Rendez-vous (Questions 1-14)", f"{rv_count:,} RV"))
    else:
        checks.append(("⚠️", "Rendez-vous (Questions 1-14)", f"Seulement {rv_count:,} RV"))

    # Check Clients
    clients_count = results.get('gazelle_clients', 0)
    if clients_count >= 100:
        checks.append(("✅", "Clients (Questions 15-26)", f"{clients_count:,} clients"))
    else:
        checks.append(("⚠️", "Clients (Questions 15-26)", f"Seulement {clients_count:,} clients"))

    # Check Pianos
    pianos_count = results.get('gazelle_pianos', 0)
    if pianos_count >= 200:
        checks.append(("✅", "Pianos (Questions 27-34)", f"{pianos_count:,} pianos"))
    else:
        checks.append(("⚠️", "Pianos (Questions 27-34)", f"Seulement {pianos_count:,} pianos"))

    # Check Timeline
    timeline_count = results.get('gazelle_timeline_entries', 0)
    if timeline_count >= 10000:
        checks.append(("✅", "Historique Piano", f"{timeline_count:,} entrées"))
    else:
        checks.append(("⚠️", "Historique Piano", f"Seulement {timeline_count:,} entrées"))

    # Check Users
    users_count = results.get('users', 0)
    if users_count >= 5:
        checks.append(("✅", "Techniciens", f"{users_count:,} utilisateurs"))
    else:
        checks.append(("⚠️", "Techniciens", f"Seulement {users_count:,} utilisateurs"))

    for status, category, detail in checks:
        print(f"{status} {category:<40} {detail}")

    # Score global
    passed = sum(1 for c in checks if c[0] == "✅")
    total = len(checks)
    pct = (passed / total) * 100 if total > 0 else 0

    print("\n" + "=" * 80)
    print(f"📊 SCORE: {passed}/{total} checks réussis ({pct:.0f}%)")
    print("=" * 80)

    if pct >= 80:
        print("\n🎉 EXCELLENT! Les données sont suffisantes pour les 40 questions!")
    elif pct >= 60:
        print("\n⚠️  PARTIEL. Certaines questions pourraient échouer.")
    else:
        print("\n❌ INSUFFISANT. Import requis!")

    print("\n💡 ACTIONS RECOMMANDÉES:\n")

    if rv_count < 100:
        print("  • Vérifier l'import des rendez-vous")

    if clients_count < 100:
        print("  • Vérifier l'import des clients")

    if pianos_count < 200:
        print("  • Vérifier l'import des pianos")

    if timeline_count < 10000:
        print(f"  • Continuer l'import timeline (actuellement: {timeline_count:,}/10,000 minimum)")

    if timeline_count < 50000:
        print(f"  • Pour historique complet, viser 50,000+ entrées (actuellement: {timeline_count:,})")

    print("\n" + "=" * 80)
    print("✅ Vérification terminée!")
    print("=" * 80 + "\n")

if __name__ == '__main__':
    main()
