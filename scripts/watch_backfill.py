#!/usr/bin/env python3
"""
🔍 MONITORING EN TEMPS RÉEL du backfill historique
Affiche la progression en direct avec rafraîchissement automatique
"""

import sys
import os
import time
from datetime import datetime
from typing import Dict, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.supabase_storage import SupabaseStorage


class BackfillMonitor:
    """Moniteur temps réel du backfill."""

    def __init__(self):
        self.storage = SupabaseStorage()
        self.last_count = {}
        self.start_time = datetime.now()

    def clear_screen(self):
        """Efface l'écran (compatible macOS/Linux)."""
        os.system('clear')

    def get_year_stats(self, year: int) -> Dict:
        """Récupère les stats pour une année."""
        try:
            result = self.storage.client.table('gazelle_timeline_entries')\
                .select('id', count='exact')\
                .gte('occurred_at', f'{year}-01-01T00:00:00Z')\
                .lt('occurred_at', f'{year+1}-01-01T00:00:00Z')\
                .execute()

            return {
                'count': result.count or 0,
                'year': year
            }
        except Exception as e:
            return {'count': 0, 'year': year, 'error': str(e)}

    def get_total_stats(self) -> Dict:
        """Récupère les stats totales."""
        try:
            result = self.storage.client.table('gazelle_timeline_entries')\
                .select('id', count='exact')\
                .execute()

            return {
                'total': result.count or 0
            }
        except Exception as e:
            return {'total': 0, 'error': str(e)}

    def get_recent_entries(self, limit: int = 5):
        """Récupère les dernières entrées importées."""
        try:
            result = self.storage.client.table('gazelle_timeline_entries')\
                .select('external_id, entry_type, occurred_at, created_at')\
                .order('created_at', desc=True)\
                .limit(limit)\
                .execute()

            return result.data if result.data else []
        except Exception as e:
            return []

    def calculate_rate(self, year: int, current_count: int) -> str:
        """Calcule le taux d'import (entrées/sec)."""
        if year not in self.last_count:
            self.last_count[year] = {'count': current_count, 'time': datetime.now()}
            return "Calcul..."

        last = self.last_count[year]
        delta_count = current_count - last['count']
        delta_time = (datetime.now() - last['time']).total_seconds()

        if delta_time > 0 and delta_count > 0:
            rate = delta_count / delta_time
            self.last_count[year] = {'count': current_count, 'time': datetime.now()}

            # Estimer temps restant (si on connaît le total attendu)
            # Pour 2024, environ 50,000 entrées attendues
            total_expected = 50000
            remaining = total_expected - current_count
            if rate > 0 and remaining > 0:
                eta_seconds = remaining / rate
                eta_min = int(eta_seconds / 60)
                return f"{rate:.1f} e/s (ETA: ~{eta_min} min)"

            return f"{rate:.1f} e/s"

        return "Stable"

    def display_dashboard(self, years: list):
        """Affiche le dashboard de monitoring."""
        self.clear_screen()

        # En-tête
        print("=" * 80)
        print("🔍 MONITORING BACKFILL EN TEMPS RÉEL")
        print("=" * 80)
        print(f"⏰ Démarré: {self.start_time.strftime('%H:%M:%S')}")
        print(f"⏱️  Uptime: {(datetime.now() - self.start_time).total_seconds():.0f}s")
        print(f"🔄 Rafraîchissement: toutes les 3 secondes (Ctrl+C pour quitter)")
        print("=" * 80)
        print()

        # Stats totales
        total_stats = self.get_total_stats()
        print(f"📊 TOTAL DANS SUPABASE: {total_stats['total']:,} entrées")
        print()

        # Stats par année
        print("📅 PAR ANNÉE:")
        print("-" * 80)
        print(f"{'Année':<10} {'Entrées':<15} {'Taux':<20} {'Statut':<20}")
        print("-" * 80)

        for year in years:
            stats = self.get_year_stats(year)
            count = stats['count']
            rate = self.calculate_rate(year, count)

            # Indicateur de progression
            if count == 0:
                status = "⏸️  Pas commencé"
            elif count < 1000:
                status = "🟡 En cours (début)"
            elif count < 10000:
                status = "🟢 En cours (actif)"
            else:
                status = "✅ Avancé"

            print(f"{year:<10} {count:<15,} {rate:<20} {status:<20}")

        print("-" * 80)
        print()

        # Dernières entrées importées
        print("📝 DERNIÈRES ENTRÉES IMPORTÉES:")
        print("-" * 80)
        recent = self.get_recent_entries(5)

        if recent:
            for entry in recent:
                external_id = (entry.get('external_id') or 'N/A')[:20]
                entry_type = (entry.get('entry_type') or 'N/A')[:20]
                occurred_at = (entry.get('occurred_at') or 'N/A')[:19]
                created_at = (entry.get('created_at') or 'N/A')[:19]

                print(f"  • {external_id:<20} | {entry_type:<20} | {occurred_at}")
        else:
            print("  Aucune entrée récente")

        print("-" * 80)
        print()

        # Instructions
        print("💡 AIDE:")
        print("  - Le dashboard se rafraîchit automatiquement")
        print("  - Taux = entrées/seconde (ETA = temps estimé restant)")
        print("  - Si le taux est 'Stable', l'import est peut-être terminé ou bloqué")
        print("  - Ctrl+C pour quitter")
        print("=" * 80)

    def run(self, years: list = None, refresh_interval: int = 3):
        """Lance le monitoring en boucle."""
        if years is None:
            years = [2024, 2023, 2022, 2021, 2020]

        print(f"🚀 Démarrage du monitoring pour les années: {years}")
        print(f"⏱️  Rafraîchissement toutes les {refresh_interval} secondes")
        print("⌨️  Appuyez sur Ctrl+C pour quitter\n")
        time.sleep(2)

        try:
            while True:
                self.display_dashboard(years)
                time.sleep(refresh_interval)
        except KeyboardInterrupt:
            self.clear_screen()
            print("\n✅ Monitoring arrêté par l'utilisateur")
            print(f"⏱️  Durée totale: {(datetime.now() - self.start_time).total_seconds():.0f}s")

            # Stats finales
            print("\n📊 STATS FINALES:")
            total_stats = self.get_total_stats()
            print(f"Total entrées: {total_stats['total']:,}")

            for year in years:
                stats = self.get_year_stats(year)
                print(f"  {year}: {stats['count']:,} entrées")


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(
        description='Monitoring en temps réel du backfill historique',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples:
  # Monitorer 2024 uniquement
  python3 scripts/watch_backfill.py --years 2024

  # Monitorer plusieurs années
  python3 scripts/watch_backfill.py --years 2024 2023 2022

  # Rafraîchissement rapide (1 seconde)
  python3 scripts/watch_backfill.py --interval 1

  # Monitorer toutes les années 2016-2024
  python3 scripts/watch_backfill.py --years 2024 2023 2022 2021 2020 2019 2018 2017 2016
        """
    )

    parser.add_argument(
        '--years',
        type=int,
        nargs='+',
        default=[2024],
        help='Années à monitorer (défaut: 2024)'
    )

    parser.add_argument(
        '--interval',
        type=int,
        default=3,
        help='Intervalle de rafraîchissement en secondes (défaut: 3)'
    )

    args = parser.parse_args()

    monitor = BackfillMonitor()
    monitor.run(years=args.years, refresh_interval=args.interval)
