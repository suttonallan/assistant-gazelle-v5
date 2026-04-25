"""
Rate limiting pour les actions de l'assistant.

Règle MVP : max 5 actions de type 'estimate.execute' / heure / user.
Si dépassé → bloque + log + (futur : email à Allan).
"""
import logging
from datetime import datetime, timedelta
from typing import Tuple

import requests

from core.supabase_storage import SupabaseStorage

logger = logging.getLogger(__name__)

LIMITS = {
    # action_type : (max, window_minutes)
    'estimate.execute': (5, 60),
}


def check_rate_limit(user_id: str, action_type: str) -> Tuple[bool, str]:
    """Retourne (ok, message). ok=True si l'action peut procéder."""
    if action_type not in LIMITS:
        return True, ""

    max_count, window_min = LIMITS[action_type]
    cutoff = (datetime.now() - timedelta(minutes=window_min)).isoformat()

    storage = SupabaseStorage(silent=True)
    try:
        url = (
            f"{storage.api_url}/assistant_actions_log"
            f"?user_id=eq.{user_id}"
            f"&action_type=eq.{action_type}"
            f"&status=eq.executed"
            f"&created_at=gte.{cutoff}"
            f"&select=id"
        )
        resp = requests.get(url, headers=storage._get_headers(), timeout=10)
        if resp.status_code != 200:
            logger.warning(f"rate_limit check failed: {resp.status_code}")
            return True, ""  # fail-open : ne pas bloquer si la check échoue

        count = len(resp.json() or [])
        if count >= max_count:
            return False, (
                f"Limite atteinte : {count}/{max_count} actions de type "
                f"« {action_type} » dans les {window_min} dernières minutes. "
                f"Réessaie plus tard ou contacte Allan."
            )
        return True, ""
    except Exception as exc:
        logger.warning(f"rate_limit error: {exc}")
        return True, ""  # fail-open
