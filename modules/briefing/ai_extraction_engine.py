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
    """Requête directe Supabase : la TOUTE PREMIÈRE entrée de timeline pour un client.

    Ignore les limites de batch et les filtres de type d'entrée.
    Logique de sécurité : si la date la plus ancienne == date de création Gazelle
    ET que cette date est >= 2024-01-01, on considère que l'historique n'est pas
    encore backfillé → retourne _SAFETY_BLOCKED (pas de fausse ancienneté).

    Retourne :
        - "depuis X ans/mois" si données fiables
        - _SAFETY_BLOCKED si données suspectes (bloque aussi le fallback)
        - None si aucune donnée ou erreur (le fallback peut tenter)
    """
    try:
        cid_encoded = quote(client_id, safe='')
        url = (
            f"{storage.api_url}/gazelle_timeline_entries?"
            f"client_id=eq.{cid_encoded}"
            f"&select=occurred_at"
            f"&order=occurred_at.asc"
            f"&limit=1"
        )
        resp = http_requests.get(url, headers=storage._get_headers(), timeout=8)
        if resp.status_code != 200 or not resp.json():
            return None

        oldest_str = resp.json()[0].get('occurred_at', '')
        if not oldest_str or len(oldest_str) < 10:
            return None

        oldest_date = datetime.strptime(oldest_str[:10], '%Y-%m-%d')

        # ── Logique de sécurité ──
        # Si la plus ancienne entrée tombe le même jour que la création du
        # dossier Gazelle ET qu'il n'y a qu'une seule entrée, on ne peut pas
        # se fier à cette date (pas de backfill). Mais s'il y a plusieurs
        # entrées étalées dans le temps, c'est un vrai historique.
        if client_created_at and len(client_created_at) >= 10:
            try:
                created_date = datetime.strptime(client_created_at[:10], '%Y-%m-%d')
                if (oldest_date.date() == created_date.date()
                        and created_date.date() >= date_type(2024, 1, 1)):
                    # Vérifier s'il y a un historique réel (>1 entrée étalée)
                    count_url = (
                        f"{storage.api_url}/gazelle_timeline_entries?"
                        f"client_id=eq.{cid_encoded}"
                        f"&select=occurred_at"
                        f"&order=occurred_at.desc"
                        f"&limit=1"
                    )
                    count_resp = http_requests.get(count_url, headers=storage._get_headers(), timeout=5)
                    if count_resp.status_code == 200 and count_resp.json():
                        newest_str = count_resp.json()[0].get('occurred_at', '')
                        if newest_str and len(newest_str) >= 10:
                            newest_date = datetime.strptime(newest_str[:10], '%Y-%m-%d')
                            # Si plus de 30 jours entre la plus ancienne et la plus récente,
                            # c'est un vrai historique, pas un artefact de création
                            if (newest_date - oldest_date).days > 30:
                                pass  # Historique réel → ne pas bloquer
                            else:
                                return _SAFETY_BLOCKED
                    else:
                        return _SAFETY_BLOCKED
            except ValueError:
                pass

        return _format_client_since(oldest_date)

    except Exception as e:
        print(f"⚠️  fetch_earliest_client_date error ({client_id}): {e}")
        return None


def _format_client_since(oldest: datetime) -> str:
    """Formate une date en durée lisible : 'depuis X ans', 'depuis X mois', 'nouveau client'."""
    days = (datetime.now() - oldest).days
    years = days / 365.25
    if years >= 1:
        y = int(years)
        return f"depuis {y} an{'s' if y > 1 else ''}"
    months = int(days / 30.44)
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
