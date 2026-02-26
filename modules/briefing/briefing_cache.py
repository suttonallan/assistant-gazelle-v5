#!/usr/bin/env python3
"""
Cache des briefings pour "Ma Journée" V4.

Pré-calcule les briefings narratifs pour aujourd'hui et demain.
Appelé par le cron de sync ou manuellement.
"""

import json
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.supabase_storage import SupabaseStorage
from modules.briefing.client_intelligence_service import NarrativeBriefingService


class BriefingCache:
    """Gère le cache des briefings pré-calculés."""

    def __init__(self):
        self.storage = SupabaseStorage(silent=True)
        self.service = NarrativeBriefingService()

    async def warm_cache_async(self, days_ahead: int = 2) -> Dict:
        """
        Pré-calcule les briefings (async version).
        Called from FastAPI endpoints or other async contexts.
        """
        stats = {'dates': [], 'total_briefings': 0, 'cached': 0, 'errors': 0}

        for i in range(days_ahead):
            target_date = (datetime.now() + timedelta(days=i)).strftime('%Y-%m-%d')
            stats['dates'].append(target_date)

            try:
                briefings = await self.service.get_daily_briefings(target_date=target_date)
                stats['total_briefings'] += len(briefings)

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
                import traceback
                traceback.print_exc()

        return stats

    def warm_cache(self, days_ahead: int = 2) -> Dict:
        """
        Sync wrapper for warm_cache_async.
        Used by sync callers (cron jobs, CLI).
        """
        return asyncio.run(self.warm_cache_async(days_ahead=days_ahead))

    def get_cached_briefings(self, target_date: str) -> Optional[List[Dict]]:
        """
        Récupère les briefings depuis le cache.
        Returns None if not cached or cache expired (>4h).
        """
        cache_key = f"briefings_{target_date}"
        cached = self._get_cache(cache_key)

        if not cached:
            return None

        # Check freshness (max 4 hours)
        generated_at = cached.get('generated_at', '')
        if generated_at:
            try:
                gen_time = datetime.fromisoformat(generated_at)
                age_hours = (datetime.now() - gen_time).total_seconds() / 3600
                if age_hours > 4:
                    print(f"⚠️ Cache périmé ({age_hours:.1f}h)")
                    return None
            except Exception:
                pass

        return cached.get('briefings', [])

    def _save_cache(self, key: str, data: Dict):
        """Sauvegarde dans system_settings."""
        try:
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
    """Sync function called by cron/sync to pre-warm the cache."""
    print("🔥 Pré-chargement des briefings V4...")
    cache = BriefingCache()
    stats = cache.warm_cache(days_ahead=2)
    print(f"✅ Cache prêt: {stats['cached']} briefings pour {stats['dates']}")
    return stats


async def warm_briefing_cache_async():
    """Async version called from FastAPI endpoints."""
    print("🔥 Pré-chargement des briefings V4 (async)...")
    cache = BriefingCache()
    stats = await cache.warm_cache_async(days_ahead=2)
    print(f"✅ Cache prêt: {stats['cached']} briefings pour {stats['dates']}")
    return stats


if __name__ == '__main__':
    warm_briefing_cache()
