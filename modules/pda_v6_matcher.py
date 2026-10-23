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
    """Lien demande PdA -> RV Gazelle, SANS devinette (règle d'Allan, 2026-10-23).

    Chaque information garde sa responsabilité :
      1. Date : obligatoire et identique.
      2. Aucune contradiction : un RV qui nomme une autre salle, ou dont
         l'heure ne respecte pas celle de la demande (« avant 9h »,
         « à 17h30 », « entre 12h et 13h »), est écarté d'office.
      3. Preuve positive : la salle ou l'événement figure dans le RV.
         Si plusieurs RV sont aussi bons l'un que l'autre -> AUCUN lien.
      4. Sans preuve positive : lien seulement s'il ne reste qu'UN seul RV
         compatible ce jour-là et que l'heure est connue des deux côtés.
    Pas d'IA. Dans le doute, la demande reste « à lier » plutôt que de
    recevoir le technicien d'un autre RV.
    """
    request_date = _normalize_date(request.get("appointment_date"))
    if not request_date:
        return None

    request_room = (request.get("room") or "").upper().strip()
    request_for_who = (request.get("for_who") or "").upper().strip()
    request_time = request.get("time") or ""

    compatible = []
    for apt in gazelle_appointments:
        if _normalize_date(apt.get("appointment_date")) != request_date:
            continue
        if _contradicts(request_room, request_time, apt):
            continue
        compatible.append(apt)

    if not compatible:
        return None

    evidence = []
    for apt in compatible:
        apt_text = _build_search_text(apt)
        room_ok = _room_named(request_room, apt_text)
        fw = _for_who_score(request_for_who, apt_text) if request_for_who else 0
        if room_ok or fw:
            evidence.append((apt, (2 if room_ok else 0) + fw))

    if evidence:
        evidence.sort(key=lambda x: -x[1])
        if len(evidence) > 1 and evidence[0][1] == evidence[1][1]:
            logger.info(f"PdA ambigu ({request_date} {request_room} {request_for_who}) : "
                        f"{len(evidence)} RV aussi plausibles -> pas de lien")
            return None
        best = dict(evidence[0][0])
        best["_matched_by"] = "evidence"
        return best

    if len(compatible) == 1:
        apt = compatible[0]
        if _hour_bounds(request_time) and _parse_appointment_hour(apt.get("appointment_time")) is not None:
            best = dict(apt)
            best["_matched_by"] = "elimination"
            return best

    return None


PDA_ROOM_CODES = {"MS", "TM", "WP", "5E", "TJD", "SCL", "PN", "SH", "CL"}
MAX_HOUR_GAP_FOR_AI = 3


def _room_code(room):
    for code in PDA_ROOM_CODES:
        if re.search(rf"(?<![A-Z0-9]){code}(?![A-Z0-9])", room or ""):
            return code
    return None


def _room_named(request_room, apt_text):
    code = _room_code(request_room)
    if code:
        return bool(re.search(rf"(?<![A-Z0-9]){code}(?![A-Z0-9])", apt_text))
    return bool(request_room) and request_room in apt_text


def _hour_bounds(time_str):
    """Fenêtre d'heure de DÉBUT acceptable pour le RV, selon la demande.
    « avant 9h » -> [5, 9] ; « à 17h30 » -> [16, 18] ; « entre 12h et 13h »
    -> [11, 13] ; « après 18h » -> [18, 23] ; « 18h » -> [15, 19]."""
    t = (time_str or "").lower().strip()
    hours = [int(h) for h in re.findall(r"(\d{1,2})\s*h", t)]
    if not hours:
        return None
    h = hours[0]
    if t.startswith("avant"):
        return (max(h - 4, 0), h)
    if t.startswith("entre") and len(hours) >= 2:
        return (hours[0] - 1, hours[1])
    if t.startswith("après") or t.startswith("apres"):
        return (h, 23)
    if re.match(r"^(a|à)\s", t):
        return (h - 1, h + 1)
    return (h - 3, h + 1)


def _contradicts(request_room, request_time, apt):
    """Vrai si le RV ne peut pas être cette demande : il nomme une autre
    salle PdA, ou son heure de début sort de la fenêtre demandée."""
    apt_text = _build_search_text(apt)
    req_code = _room_code(request_room)
    if req_code:
        apt_codes = {c for c in PDA_ROOM_CODES
                     if re.search(rf"(?<![A-Z0-9]){c}(?![A-Z0-9])", apt_text)}
        if apt_codes and req_code not in apt_codes:
            return True
    apt_hour = _parse_appointment_hour(apt.get("appointment_time"))
    bounds = _hour_bounds(request_time)
    if bounds and apt_hour is not None:
        if not (bounds[0] <= apt_hour <= bounds[1]):
            return True
    return False


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
    fw_score = _for_who_score(request_for_who, apt_text) if request_for_who else 0

    if not room_match and fw_score == 0:
        return 0

    if room_match:
        quality += 1
    quality += fw_score
    if request_hour_limit and apt_hour is not None and apt_hour <= request_hour_limit:
        quality += 1
    if has_real_tech:
        quality += 1
    return quality


STOP_WORDS = {
    "LE", "LA", "LES", "DE", "DU", "DES", "EN", "AU", "AUX",
    "UN", "UNE", "ET", "OU", "PAR", "POUR", "AVEC", "DANS",
    "THE", "OF", "AND", "BY", "FOR", "AT", "IN",
}


def _for_who_matches(request_for_who, apt_text):
    return _for_who_score(request_for_who, apt_text) > 0


def _for_who_score(request_for_who, apt_text):
    if not request_for_who:
        return 0
    if request_for_who in apt_text:
        return 3
    words = [w for w in request_for_who.split() if len(w) >= 2 and w not in STOP_WORDS]
    if not words:
        return 0
    matched = sum(1 for w in words if w in apt_text)
    if matched == 0:
        return 0
    if matched == len(words):
        return 3
    if matched >= 2:
        return 2
    return 1


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
            max_tokens=10,
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
            max_tokens=20,
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
