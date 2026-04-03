"""
PDA Matcher V6 — embarqué dans v5 pour comparaison.

Copie du matcher v6 (assistant-v6/sandbox/app/modules/pda/matcher.py)
pour exécuter la comparaison sans déployer v6 séparément.
"""

import os
import re
import json
import logging
from typing import Optional, Dict, List

logger = logging.getLogger("ptm.pda.v6matcher")

A_ATTRIBUER_ID = "usr_HihJsEgkmpTEziJo"

REAL_TECHNICIAN_IDS = {
    "usr_HcCiFk7o0vZ9xAI0",
    "usr_ofYggsCDt2JAVeNP",
    "usr_ReUSmIJmBF86ilY1",
    "usr_bbt59aCUqUaDWA8n",
}

TECH_NAMES = {
    "usr_HcCiFk7o0vZ9xAI0": "Nicolas",
    "usr_ofYggsCDt2JAVeNP": "Allan",
    "usr_ReUSmIJmBF86ilY1": "JP",
    "usr_bbt59aCUqUaDWA8n": "Margot",
    "usr_HihJsEgkmpTEziJo": "À attribuer",
}


def tech_name(tech_id):
    if not tech_id:
        return "-"
    return TECH_NAMES.get(tech_id, tech_id[:15])


def find_best_match(request, gazelle_appointments):
    request_date = _normalize_date(request.get("appointment_date"))
    if not request_date:
        return None

    request_room = (request.get("room") or "").upper().strip()
    request_for_who = (request.get("for_who") or "").upper().strip()
    request_hour_limit = _parse_hour_limit(request.get("time") or "")

    candidates = []
    for apt in gazelle_appointments:
        apt_date = _normalize_date(apt.get("appointment_date"))
        if apt_date != request_date:
            continue

        apt_text = _build_search_text(apt)
        apt_hour = _parse_appointment_hour(apt.get("appointment_time"))
        has_real_tech = apt.get("technicien") in REAL_TECHNICIAN_IDS

        quality = _evaluate_match(
            request_room, request_for_who, request_hour_limit,
            apt_text, apt_hour, has_real_tech,
        )
        if quality > 0:
            candidates.append((apt, quality))

    if candidates:
        candidates.sort(key=lambda x: -x[1])
        return candidates[0][0]

    # Fallback IA
    same_day = [
        a for a in gazelle_appointments
        if _normalize_date(a.get("appointment_date")) == request_date
    ]
    if same_day:
        ai_match = _ai_find_match(request, same_day)
        if ai_match:
            ai_match["_matched_by"] = "ai"
            return ai_match

    return None


def matches_request(request, gazelle_apt, allow_ai=True):
    request_date = _normalize_date(request.get("appointment_date"))
    apt_date = _normalize_date(gazelle_apt.get("appointment_date"))
    if not request_date or request_date != apt_date:
        return False

    request_room = (request.get("room") or "").upper().strip()
    request_for_who = (request.get("for_who") or "").upper().strip()
    apt_text = _build_search_text(gazelle_apt)

    if request_room and request_room in apt_text:
        return True
    if request_for_who and _for_who_matches(request_for_who, apt_text):
        return True
    if allow_ai:
        return _ai_confirm_match(request, gazelle_apt)
    return False


def _evaluate_match(request_room, request_for_who, request_hour_limit,
                    apt_text, apt_hour, has_real_tech):
    quality = 0
    room_match = bool(request_room and request_room in apt_text)
    for_who_match = bool(request_for_who and _for_who_matches(request_for_who, apt_text))

    if not room_match and not for_who_match:
        return 0

    if room_match:
        quality += 1
    if for_who_match:
        quality += 1
    if request_hour_limit and apt_hour is not None and apt_hour <= request_hour_limit:
        quality += 1
    if has_real_tech:
        quality += 1
    return quality


def _for_who_matches(request_for_who, apt_text):
    if not request_for_who:
        return False
    if request_for_who in apt_text:
        return True
    words = [w for w in request_for_who.split() if len(w) >= 2]
    return bool(words and any(w in apt_text for w in words))


def _build_search_text(apt):
    return " ".join([
        apt.get("title") or "",
        apt.get("description") or "",
        apt.get("notes") or "",
        apt.get("location") or "",
    ]).upper()


def _normalize_date(date_val):
    if not date_val:
        return None
    return str(date_val)[:10]


def _parse_hour_limit(time_str):
    if not time_str:
        return None
    m = re.search(r"(\d{1,2})\s*h", str(time_str), re.IGNORECASE)
    return int(m.group(1)) if m else None


def _parse_appointment_hour(time_str):
    if not time_str:
        return None
    try:
        return int(str(time_str).split(":")[0])
    except (ValueError, IndexError):
        return None


# ── IA ──

_AI_PROMPT = """Tu es un système de matching pour Piano Technique Montréal.
Tu dois déterminer si un rendez-vous Gazelle correspond à une demande de service Place des Arts.

Exemples de correspondances :
- "Mark PdA" = "Marketing Pda"
- "OSM" = "Orchestre Symphonique de Montréal"
- "CMM" = "Conservatoire de musique de Montréal"
- "ONJ Alain Caron" = "ONJ Alain. Caron"
- "OM" = "Orchestre Métropolitain"

Réponds UNIQUEMENT "OUI" ou "NON"."""


def _format_request(req):
    parts = []
    if req.get("appointment_date"): parts.append(f"Date: {str(req['appointment_date'])[:10]}")
    if req.get("room"): parts.append(f"Salle: {req['room']}")
    if req.get("for_who"): parts.append(f"Événement: {req['for_who']}")
    if req.get("time"): parts.append(f"Heure: {req['time']}")
    return " | ".join(parts)


def _format_apt(apt):
    parts = []
    if apt.get("appointment_date"): parts.append(f"Date: {str(apt['appointment_date'])[:10]}")
    if apt.get("appointment_time"): parts.append(f"Heure: {str(apt['appointment_time'])[:5]}")
    if apt.get("title"): parts.append(f"Titre: {apt['title']}")
    if apt.get("description"): parts.append(f"Desc: {apt['description'][:150]}")
    return " | ".join(parts)


def _ai_confirm_match(request, gazelle_apt):
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return False
    try:
        from anthropic import Anthropic
        client = Anthropic(api_key=api_key)
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=10, temperature=0,
            system=_AI_PROMPT,
            messages=[{"role": "user", "content":
                f"DEMANDE PDA: {_format_request(request)}\nRV GAZELLE: {_format_apt(gazelle_apt)}\nEst-ce le même service ?"}],
        )
        return response.content[0].text.strip().upper().startswith("OUI")
    except Exception as e:
        logger.warning(f"AI confirm failed: {e}")
        return False


def _ai_find_match(request, same_day_apts):
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return None
    try:
        from anthropic import Anthropic
        client = Anthropic(api_key=api_key)
        apts_str = "\n".join(f"[{i}] {_format_apt(a)}" for i, a in enumerate(same_day_apts))
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=20, temperature=0,
            system=_AI_PROMPT + "\nS'il y a plusieurs RV, réponds le NUMÉRO [0], [1], etc. Réponds AUCUN si aucun.",
            messages=[{"role": "user", "content":
                f"DEMANDE PDA: {_format_request(request)}\n\nRV GAZELLE:\n{apts_str}\n\nLequel correspond ?"}],
        )
        m = re.search(r"\[?(\d+)\]?", response.content[0].text.strip())
        if m:
            idx = int(m.group(1))
            if 0 <= idx < len(same_day_apts):
                return same_day_apts[idx]
        return None
    except Exception as e:
        logger.warning(f"AI find failed: {e}")
        return None
