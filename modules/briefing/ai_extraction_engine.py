#!/usr/bin/env python3
"""
AI Extraction Engine — Utility functions for Ma Journée V4.

V4 simplified: the narrative generation is now in client_intelligence_service.py.
This module keeps only the shared utility functions:
- TECHNICIAN_NAMES / ADMIN_STAFF_IDS mappings
- compute_client_since()
- resolve_technician_name()
"""

from datetime import datetime
from typing import Dict, List, Optional


# ═══════════════════════════════════════════════════════════════════
# TECHNICIAN MAPPINGS
# ═══════════════════════════════════════════════════════════════════

TECHNICIAN_NAMES = {
    "usr_HcCiFk7o0vZ9xAI0": "Nicolas",
    "usr_ReUSmIJmBF86ilY1": "Jean-Philippe",
    "usr_ofYggsCDt2JAVeNP": "Allan",
}

# Assistantes administratives — leurs entrées sont exclues de l'historique technique
ADMIN_STAFF_IDS = {
    "usr_tndhXmnT0iakT4HF",  # Louise
    "usr_bbt59aCUqUaDWA8n",  # Margot
}


# ═══════════════════════════════════════════════════════════════════
# UTILITY FUNCTIONS
# ═══════════════════════════════════════════════════════════════════

def compute_client_since(notes: List[Dict]) -> Optional[str]:
    """Calcule depuis quand le client est avec nous (plus ancienne note)."""
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
    years = (datetime.now() - oldest).days / 365.25
    if years >= 1:
        return f"depuis {int(years)} an{'s' if int(years) > 1 else ''}"
    months = int((datetime.now() - oldest).days / 30.44)
    if months >= 1:
        return f"depuis {months} mois"
    return "nouveau client"


def resolve_technician_name(user_id: str) -> str:
    """Résout un user_id Gazelle en nom lisible. Masque les IDs bruts inconnus."""
    if user_id in ADMIN_STAFF_IDS:
        return ""  # Pas un technicien
    name = TECHNICIAN_NAMES.get(user_id, "")
    if not name and user_id and user_id.startswith("usr_"):
        return ""  # ID inconnu — ne pas afficher le code brut
    return name or user_id or ""
