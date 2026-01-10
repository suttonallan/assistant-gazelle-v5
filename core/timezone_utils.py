#!/usr/bin/env python3
"""
Utilitaires de gestion des timezones pour l'API Gazelle.

Gazelle API utilise America/Montreal (EST/EDT) comme timezone locale,
mais l'API GraphQL attend des timestamps en UTC (ISO-8601 avec 'Z' ou offset).

Ce module fournit des fonctions pour:
1. Convertir America/Montreal → UTC pour les requêtes API
2. Stocker les CoreDateTime complets avec timezone dans Supabase
3. Garantir la cohérence des dates/heures à travers le système
"""

from datetime import datetime, date, time
from typing import Optional, Union
from zoneinfo import ZoneInfo


# Timezone de référence (utilisée par Gazelle API)
MONTREAL_TZ = ZoneInfo("America/Montreal")
UTC_TZ = ZoneInfo("UTC")


def montreal_to_utc(dt: Union[datetime, str]) -> datetime:
    """
    Convertit un datetime ou string en America/Montreal vers UTC.

    Args:
        dt: datetime aware/naive ou string ISO-8601

    Returns:
        datetime aware en UTC

    Examples:
        >>> # 2026-01-09 14:30 EST → 2026-01-09 19:30 UTC
        >>> montreal_to_utc("2026-01-09T14:30:00")
        datetime.datetime(2026, 1, 9, 19, 30, tzinfo=ZoneInfo('UTC'))
    """
    if isinstance(dt, str):
        # Parser string ISO
        dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))

    # Si naive, assumer America/Montreal
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=MONTREAL_TZ)

    # Convertir vers UTC
    return dt.astimezone(UTC_TZ)


def utc_to_montreal(dt: Union[datetime, str]) -> datetime:
    """
    Convertit un datetime UTC vers America/Montreal.

    Args:
        dt: datetime UTC aware ou string ISO-8601

    Returns:
        datetime aware en America/Montreal

    Examples:
        >>> # 2026-01-09 19:30 UTC → 2026-01-09 14:30 EST
        >>> utc_to_montreal("2026-01-09T19:30:00Z")
        datetime.datetime(2026, 1, 9, 14, 30, tzinfo=ZoneInfo('America/Montreal'))
    """
    if isinstance(dt, str):
        dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC_TZ)

    return dt.astimezone(MONTREAL_TZ)


def format_for_gazelle_filter(dt: Union[datetime, date, str]) -> str:
    """
    Formate une date/datetime pour les filtres API Gazelle (occurredAtGet, etc.).

    IMPORTANT: L'API Gazelle attend UTC en format ISO-8601 avec timezone.

    Args:
        dt: datetime, date ou string

    Returns:
        String ISO-8601 en UTC avec 'Z' (ex: "2026-01-09T19:30:00Z")

    Examples:
        >>> # Input: date Montreal 2026-01-09
        >>> format_for_gazelle_filter(date(2026, 1, 9))
        "2026-01-09T05:00:00Z"  # 00:00 EST = 05:00 UTC

        >>> # Input: datetime Montreal 2026-01-09 14:30
        >>> format_for_gazelle_filter("2026-01-09T14:30:00")
        "2026-01-09T19:30:00Z"  # 14:30 EST = 19:30 UTC
    """
    if isinstance(dt, str):
        dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))
    elif isinstance(dt, date) and not isinstance(dt, datetime):
        # Convertir date → datetime à minuit Montreal
        dt = datetime.combine(dt, time.min)

    # Convertir vers UTC
    dt_utc = montreal_to_utc(dt)

    # Formater en ISO-8601 avec 'Z'
    return dt_utc.strftime('%Y-%m-%dT%H:%M:%SZ')


def parse_gazelle_datetime(dt_string: Optional[str]) -> Optional[datetime]:
    """
    Parse un CoreDateTime de l'API Gazelle (format ISO-8601 avec timezone).

    Args:
        dt_string: String ISO-8601 (ex: "2026-01-09T19:30:00Z" ou "2026-01-09T14:30:00-05:00")

    Returns:
        datetime aware en UTC, ou None si dt_string est None/vide

    Examples:
        >>> parse_gazelle_datetime("2026-01-09T19:30:00Z")
        datetime.datetime(2026, 1, 9, 19, 30, tzinfo=ZoneInfo('UTC'))
    """
    if not dt_string:
        return None

    # Parser ISO-8601 (remplacer 'Z' par '+00:00' pour Python)
    dt = datetime.fromisoformat(dt_string.replace('Z', '+00:00'))

    # Convertir vers UTC
    return dt.astimezone(UTC_TZ)


def format_for_supabase(dt: Union[datetime, str, None]) -> Optional[str]:
    """
    Formate un datetime pour stockage dans Supabase (timestamptz).

    Supabase stocke en UTC mais accepte n'importe quel timezone ISO-8601.
    On envoie du UTC avec 'Z' pour cohérence.

    Args:
        dt: datetime aware/naive ou string ISO-8601

    Returns:
        String ISO-8601 UTC avec 'Z', ou None

    Examples:
        >>> format_for_supabase(datetime(2026, 1, 9, 14, 30, tzinfo=MONTREAL_TZ))
        "2026-01-09T19:30:00Z"
    """
    if dt is None:
        return None

    if isinstance(dt, str):
        dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))

    # Convertir vers UTC
    dt_utc = montreal_to_utc(dt) if dt.tzinfo != UTC_TZ else dt

    return dt_utc.strftime('%Y-%m-%dT%H:%M:%SZ')


def extract_date_time(dt: Union[datetime, str]) -> tuple[str, str]:
    """
    Extrait la date et l'heure séparées d'un datetime (en timezone Montreal).

    Utile pour remplir les colonnes appointment_date et appointment_time.

    Args:
        dt: datetime aware ou string ISO-8601

    Returns:
        Tuple (date_iso, time_iso) en timezone Montreal

    Examples:
        >>> extract_date_time("2026-01-09T19:30:00Z")
        ("2026-01-09", "14:30:00")  # 19:30 UTC = 14:30 EST
    """
    if isinstance(dt, str):
        dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))

    # Convertir vers Montreal
    dt_montreal = utc_to_montreal(dt)

    return (
        dt_montreal.date().isoformat(),
        dt_montreal.time().isoformat()
    )
