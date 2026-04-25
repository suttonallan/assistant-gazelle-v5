"""Journal d'audit des actions exécutées via le chat."""
import json
import logging
from datetime import datetime
from typing import Dict, Optional
import uuid

import requests

from core.supabase_storage import SupabaseStorage

logger = logging.getLogger(__name__)


def log_action(
    user_id: str,
    user_role: str,
    action_type: str,
    intent_text: str,
    target_resource: Optional[str] = None,
    payload: Optional[Dict] = None,
    response: Optional[Dict] = None,
    status: str = 'preview',
    error_message: Optional[str] = None,
    preview_token: Optional[str] = None,
) -> Optional[str]:
    """Écrit une entrée dans assistant_actions_log. Retourne l'id ou None si échec."""
    storage = SupabaseStorage(silent=True)
    row = {
        'user_id': user_id,
        'user_role': user_role,
        'action_type': action_type,
        'intent_text': intent_text[:1000] if intent_text else None,
        'target_resource': target_resource,
        'payload': payload,
        'response': response,
        'status': status,
        'error_message': error_message[:1000] if error_message else None,
        'preview_token': preview_token,
    }
    if status in ('confirmed', 'executed'):
        row['confirmed_at'] = datetime.now().isoformat()
    try:
        url = f"{storage.api_url}/assistant_actions_log"
        headers = {**storage._get_headers(), 'Prefer': 'return=representation'}
        resp = requests.post(url, headers=headers, json=row, timeout=10)
        if resp.status_code in (200, 201):
            data = resp.json()
            if isinstance(data, list) and data:
                return data[0].get('id')
            return None
        logger.warning(f"audit_log POST {resp.status_code}: {resp.text[:200]}")
    except Exception as exc:
        logger.warning(f"audit_log error: {exc}")
    return None


def find_pending_preview(token: str) -> Optional[Dict]:
    """Trouve une preview en attente par son token (si pas encore exécutée)."""
    storage = SupabaseStorage(silent=True)
    try:
        url = (
            f"{storage.api_url}/assistant_actions_log"
            f"?preview_token=eq.{token}"
            f"&status=eq.preview"
            f"&order=created_at.desc&limit=1"
        )
        resp = requests.get(url, headers=storage._get_headers(), timeout=10)
        if resp.status_code == 200:
            data = resp.json() or []
            return data[0] if data else None
    except Exception as exc:
        logger.warning(f"find_pending_preview error: {exc}")
    return None


def mark_executed(log_id: str, response: Dict, status: str = 'executed', error: Optional[str] = None):
    """Met à jour un log entry comme exécuté."""
    storage = SupabaseStorage(silent=True)
    try:
        url = f"{storage.api_url}/assistant_actions_log?id=eq.{log_id}"
        headers = {**storage._get_headers(), 'Prefer': 'return=minimal'}
        body = {
            'status': status,
            'response': response,
            'confirmed_at': datetime.now().isoformat(),
        }
        if error:
            body['error_message'] = error[:1000]
        requests.patch(url, headers=headers, json=body, timeout=10)
    except Exception as exc:
        logger.warning(f"mark_executed error: {exc}")


def generate_preview_token() -> str:
    """Génère un token unique pour lier preview → execute."""
    return f"prv_{uuid.uuid4().hex[:24]}"
