#!/usr/bin/env python3
"""
📊 Stats rapides - Affichage simple sans rafraîchissement
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.supabase_storage import SupabaseStorage

def main():
    print("\n" + "="*70)
    print("📊 STATS RAPIDES TIMELINE ENTRIES")
    print("="*70 + "\n")

    storage = SupabaseStorage()

    # Total
    print("📍 Calcul du total...")
    result_total = storage.client.table('gazelle_timeline_entries')\
        .select('id', count='exact')\
        .execute()
    total = result_total.count or 0
    print(f"✅ TOTAL: {total:,} entrées\n")

    # Par année
    print("📅 Par année:")
    print("-" * 70)
    for year in [2024, 2023, 2022, 2021, 2020]:
        result = storage.client.table('gazelle_timeline_entries')\
            .select('id', count='exact')\
            .gte('occurred_at', f'{year}-01-01T00:00:00Z')\
            .lt('occurred_at', f'{year+1}-01-01T00:00:00Z')\
            .execute()

        count = result.count or 0
        print(f"  {year}: {count:,} entrées")

    print("-" * 70)

    # Dernières entrées
    print("\n📝 5 dernières entrées importées:")
    print("-" * 70)
    result = storage.client.table('gazelle_timeline_entries')\
        .select('external_id, entry_type, occurred_at')\
        .order('created_at', desc=True)\
        .limit(5)\
        .execute()

    if result.data:
        for entry in result.data:
            ext_id = (entry.get('external_id') or 'N/A')[:20]
            etype = (entry.get('entry_type') or 'N/A')[:25]
            occurred = (entry.get('occurred_at') or 'N/A')[:19]
            print(f"  • {ext_id:<20} | {etype:<25} | {occurred}")
    else:
        print("  Aucune entrée trouvée")

    print("-" * 70)
    print("\n✅ Terminé!\n")

if __name__ == '__main__':
    main()
