"""
Feature flags — contrôlés via Supabase system_settings.

Pour activer un flag : insérer dans system_settings { key: 'flag_xxx', value: 'true' }
Pour désactiver : mettre value à 'false' ou supprimer la ligne.

Usage:
    from core.feature_flags import is_enabled
    if is_enabled('pda_v6_matcher'):
        # nouveau code
    else:
        # ancien code
"""

import logging

logger = logging.getLogger("ptm.flags")

_cache = {}
_cache_ttl = 60  # secondes
_cache_time = 0


def is_enabled(flag_name: str, default: bool = False) -> bool:
    """Vérifie si un feature flag est activé dans system_settings."""
    import time
    global _cache, _cache_time

    now = time.time()
    if now - _cache_time > _cache_ttl:
        _refresh_cache()
        _cache_time = now

    return _cache.get(flag_name, default)


def _refresh_cache():
    global _cache
    try:
        from core.supabase_storage import SupabaseStorage
        import requests as http_requests

        storage = SupabaseStorage(silent=True)
        url = f"{storage.api_url}/system_settings?key=like.flag_*&select=key,value"
        resp = http_requests.get(url, headers=storage._get_headers(), timeout=5)

        if resp.status_code == 200:
            _cache = {}
            for row in resp.json():
                key = row.get("key", "").replace("flag_", "")
                _cache[key] = row.get("value", "").lower() == "true"
    except Exception as e:
        logger.warning(f"Feature flags refresh failed: {e}")
