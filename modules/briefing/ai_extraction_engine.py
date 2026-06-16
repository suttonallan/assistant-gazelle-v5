#!/usr/bin/env python3
"""
AI Extraction Engine — Utility functions for Ma Journée V4.

V4 simplified: the narrative generation is now in client_intelligence_service.py.
This module keeps only the shared utility functions:
- TECHNICIAN_NAMES / ADMIN_STAFF_IDS mappings
- compute_client_since()
- resolve_technician_name()
"""

from datetime import datetime, date as date_type
from typing import Dict, List, Optional
from urllib.parse import quote

import requests as http_requests


# ═══════════════════════════════════════════════════════════════════
# TECHNICIAN MAPPINGS
# ═══════════════════════════════════════════════════════════════════

TECHNICIAN_NAMES = {
    "usr_HcCiFk7o0vZ9xAI0": "Nicolas",
    "usr_ReUSmIJmBF86ilY1": "Jean-Philippe",
    "usr_ofYggsCDt2JAVeNP": "Allan",
    "usr_bbt59aCUqUaDWA8n": "Margot",  # technicienne (accorde) + garde l'acces assistante (role frontend)
}

# Assistantes administratives — leurs entrées sont exclues de l'historique technique.
# Margot N'est PLUS ici : elle est devenue technicienne a part entiere (ses interventions
# comptent dans l'historique). Son acces « assistante » passe par le role frontend, distinct.
ADMIN_STAFF_IDS = {
    "usr_tndhXmnT0iakT4HF",  # Louise (assistante uniquement)
}

# Noms des assistantes — affichés UNIQUEMENT comme proprietaire d'un RV (« Ma Journee »),
# jamais dans l'historique technique (timeline / services passes) ni la collaboration.
ADMIN_STAFF_NAMES = {
    "usr_tndhXmnT0iakT4HF": "Louise",
}


# ═══════════════════════════════════════════════════════════════════
# UTILITY FUNCTIONS
# ═══════════════════════════════════════════════════════════════════

def compute_client_since(notes: List[Dict]) -> Optional[str]:
    """Calcule depuis quand le client est avec nous (plus ancienne note).
    LEGACY — utilisé comme fallback si fetch_earliest_client_date() échoue."""
    dates = []
    for n in notes:
        date_str = n.get('date', '')
        if date_str and len(date_str) >= 10:
            try:
                dates.append(datetime.strptime(date_str[:10], '%Y-%m-%d'))
            except ValueError:
                pass

    if not dates:
        return None

    oldest = min(dates)
    return _format_client_since(oldest)


_SAFETY_BLOCKED = "__SAFETY_BLOCKED__"


def fetch_earliest_client_date(storage, client_id: str,
                                client_created_at: str = None) -> Optional[str]:
    """Cherche la plus ancienne date connue pour un client.

    Consulte 3 sources et prend la plus ancienne :
    1. Plus ancienne timeline entry dans Supabase
    2. Plus ancien RV dans Supabase (gazelle_appointments)
    3. Le champ created_at du client dans Gazelle

    Retourne :
        - "depuis X ans/mois" si une date trouvée
        - None si aucune donnée
    """
    candidates = []
    headers = storage._get_headers()
    cid_encoded = quote(client_id, safe='')

    # Source 1 : plus ancienne timeline entry
    try:
        url = (
            f"{storage.api_url}/gazelle_timeline_entries?"
            f"client_id=eq.{cid_encoded}"
            f"&select=occurred_at"
            f"&order=occurred_at.asc"
            f"&limit=1"
        )
        resp = http_requests.get(url, headers=headers, timeout=8)
        if resp.status_code == 200 and resp.json():
            date_str = resp.json()[0].get('occurred_at', '')
            if date_str and len(date_str) >= 10:
                candidates.append(datetime.strptime(date_str[:10], '%Y-%m-%d'))
    except Exception:
        pass

    # Source 2 : plus ancien RV
    try:
        url = (
            f"{storage.api_url}/gazelle_appointments?"
            f"client_external_id=eq.{cid_encoded}"
            f"&select=appointment_date"
            f"&order=appointment_date.asc"
            f"&limit=1"
        )
        resp = http_requests.get(url, headers=headers, timeout=8)
        if resp.status_code == 200 and resp.json():
            date_str = resp.json()[0].get('appointment_date', '')
            if date_str and len(date_str) >= 10:
                candidates.append(datetime.strptime(date_str[:10], '%Y-%m-%d'))
    except Exception:
        pass

    # Source 3 : created_at du client Gazelle
    if client_created_at and len(client_created_at) >= 10:
        try:
            candidates.append(datetime.strptime(client_created_at[:10], '%Y-%m-%d'))
        except ValueError:
            pass

    if not candidates:
        print(f"⚠️  client_since({client_id}): aucune date trouvée")
        return None

    oldest = min(candidates)
    result = _format_client_since(oldest)
    print(f"📅 client_since({client_id}): {result} (oldest={oldest.strftime('%Y-%m-%d')}, sources={len(candidates)})")
    return result


def _format_client_since(oldest: datetime) -> str:
    """Formate une date en durée lisible : 'depuis X ans et Y mois', 'depuis X mois', 'nouveau client'."""
    days = (datetime.now() - oldest).days
    total_months = int(days / 30.44)
    years = total_months // 12
    remaining_months = total_months % 12

    if years >= 2:
        return f"depuis {years} ans"
    if years == 1:
        if remaining_months >= 2:
            return f"depuis 1 an et {remaining_months} mois"
        return "depuis 1 an"
    if total_months >= 1:
        return f"depuis {total_months} mois"
    return "nouveau client"


def resolve_technician_name(user_id: str, include_admin: bool = False) -> str:
    """Résout un user_id Gazelle en nom lisible. Masque les IDs bruts inconnus.

    include_admin=True : les assistantes (Louise/Margot) sont resolues a leur nom.
    A n'utiliser QUE pour le proprietaire d'un RV dans « Ma Journee » — jamais pour
    l'historique technique, les services passes ou la collaboration (cf. §7 M5)."""
    if user_id in ADMIN_STAFF_IDS:
        return ADMIN_STAFF_NAMES.get(user_id, "") if include_admin else ""
    name = TECHNICIAN_NAMES.get(user_id, "")
    if not name and user_id and user_id.startswith("usr_"):
        return ""  # ID inconnu — ne pas afficher le code brut
    return name or user_id or ""
