#!/usr/bin/env python3
"""
Cache des briefings pour "Ma Journée".

Pré-calcule les briefings pour aujourd'hui et demain pour un chargement instantané.
Appelé par le cron de sync ou manuellement.
"""

import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.supabase_storage import SupabaseStorage
from modules.briefing.client_intelligence_service import ClientIntelligenceService


class BriefingCache:
    """Gère le cache des briefings pré-calculés."""

    def __init__(self):
        self.storage = SupabaseStorage(silent=True)
        self.service = ClientIntelligenceService()

    def warm_cache(self, days_ahead: int = 2) -> Dict:
        """
        Pré-calcule les briefings pour aujourd'hui et les prochains jours.

        Args:
            days_ahead: Nombre de jours à pré-calculer (défaut: 2 = aujourd'hui + demain)

        Returns:
            Stats du pré-calcul
        """
        stats = {'dates': [], 'total_briefings': 0, 'cached': 0, 'errors': 0}

        for i in range(days_ahead):
            target_date = (datetime.now() + timedelta(days=i)).strftime('%Y-%m-%d')
            stats['dates'].append(target_date)

            try:
                # Générer les briefings pour cette date
                briefings = self.service.get_daily_briefings(target_date=target_date)
                stats['total_briefings'] += len(briefings)

                # Sauvegarder en cache
                cache_key = f"briefings_{target_date}"
                cache_data = {
                    'date': target_date,
                    'generated_at': datetime.now().isoformat(),
                    'count': len(briefings),
                    'briefings': briefings,
                }

                self._save_cache(cache_key, cache_data)
                stats['cached'] += len(briefings)
                print(f"✅ {target_date}: {len(briefings)} briefings mis en cache")

            except Exception as e:
                stats['errors'] += 1
                print(f"❌ {target_date}: Erreur - {e}")

        return stats

    def get_cached_briefings(self, target_date: str) -> Optional[List[Dict]]:
        """
        Récupère les briefings depuis le cache.

        Args:
            target_date: Date au format YYYY-MM-DD

        Returns:
            Liste des briefings ou None si pas en cache
        """
        cache_key = f"briefings_{target_date}"
        cached = self._get_cache(cache_key)

        if not cached:
            return None

        # Vérifier la fraîcheur (max 4 heures)
        generated_at = cached.get('generated_at', '')
        if generated_at:
            try:
                gen_time = datetime.fromisoformat(generated_at)
                age_hours = (datetime.now() - gen_time).total_seconds() / 3600
                if age_hours > 4:
                    print(f"⚠️ Cache périmé ({age_hours:.1f}h)")
                    return None
            except:
                pass

        return cached.get('briefings', [])

    def _save_cache(self, key: str, data: Dict):
        """Sauvegarde dans system_settings."""
        try:
            # Upsert dans system_settings
            self.storage.client.table('system_settings').upsert({
                'key': key,
                'value': json.dumps(data),
                'updated_at': datetime.now().isoformat(),
            }, on_conflict='key').execute()
        except Exception as e:
            print(f"⚠️ Erreur sauvegarde cache: {e}")

    def _get_cache(self, key: str) -> Optional[Dict]:
        """Récupère depuis system_settings."""
        try:
            result = self.storage.client.table('system_settings')\
                .select('value')\
                .eq('key', key)\
                .execute()

            if result.data and len(result.data) > 0:
                return json.loads(result.data[0]['value'])
        except Exception as e:
            print(f"⚠️ Erreur lecture cache: {e}")

        return None


def warm_briefing_cache():
    """Fonction appelée par le cron pour pré-chauffer le cache."""
    print("🔥 Pré-chargement des briefings...")
    cache = BriefingCache()
    stats = cache.warm_cache(days_ahead=2)
    print(f"✅ Cache prêt: {stats['cached']} briefings pour {stats['dates']}")
    return stats


if __name__ == '__main__':
    warm_briefing_cache()
