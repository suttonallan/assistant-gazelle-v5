"""
PDA Email Parser v6 — Parse les emails de demande Place des Arts.

2 niveaux :
1. TABULAIRE : si le texte contient des tabulations → parsing direct par colonnes
2. IA : pour tout autre format (compact, langage naturel, variantes)

Le parser IA utilise Claude Haiku pour extraire les champs structurés.
Coût : ~0.002$ par email. Fiabilité : >>99%.
"""

import os
import re
import json
import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger("ptm.pda.email_parser")

# Salles connues PDA
KNOWN_ROOMS = {
    "WP": "WP", "WILFRID-PELLETIER": "WP", "WILFRID PELLETIER": "WP",
    "MS": "MS", "MAISON SYMPHONIQUE": "MS",
    "TM": "TM", "MAISONNEUVE": "TM", "THÉÂTRE MAISONNEUVE": "TM",
    "5E": "5E", "5E SALLE": "5E", "CINQUIÈME SALLE": "5E",
    "SCL": "SCL", "CL": "SCL", "CLAUDE-LÉVEILLÉE": "SCL",
    "TJD": "TJD", "JEAN-DUCEPPE": "TJD", "DUCEPPE": "TJD",
    "ODM": "ODM", "SALLE E": "Salle E",
}

# Demanderesses connues
REQUESTER_MAP = {
    "AJ": "AJ", "ANNIE": "AJ", "ANNIE JENKINS": "AJ", "JENKINS": "AJ",
    "IC": "IC", "ISABELLE": "IC", "ISABELLE CLAIROUX": "IC", "CLAIROUX": "IC",
    "PT": "PT", "PATRICIA": "PT",
}


def parse_email(raw_text: str) -> list[dict]:
    """
    Parse un email PDA et retourne une liste de demandes structurées.

    Chaque demande contient :
    - appointment_date (YYYY-MM-DD)
    - room (WP, MS, 5E, etc.)
    - for_who (événement/organisme)
    - diapason (440, 442, etc.)
    - requester (AJ, IC, etc.)
    - piano (description du piano)
    - time (avant 12h, etc.)
    - confidence (0-1)
    - method (tabular, ai)
    """
    if not raw_text or not raw_text.strip():
        return []

    text = raw_text.strip(" \n\r")  # Préserver les tabs (important pour le parsing tabulaire)

    # Détecter le format
    if "\t" in text:
        results = _parse_tabular(text)
        if results:
            return results

    # Fallback : parsing IA
    return _parse_with_ai(text)


def _parse_tabular(text: str) -> list[dict]:
    """Parse le format tabulaire (copier-coller de tableur)."""
    results = []
    now = datetime.now()

    for line in text.splitlines():
        if "\t" not in line:
            continue
        parts = [p.strip() for p in line.split("\t")]
        if len(parts) < 7:
            continue

        # Colonnes attendues :
        # 0: Date demande | 1: Date RV | 2: Salle | 3: Pour qui
        # 4: Diapason | 5: Demandeur | 6: Piano | 7: Heure

        # Date RV (obligatoire)
        date_str = parts[1] if len(parts) > 1 else ""
        appointment_date = _parse_date(date_str, now)
        if not appointment_date:
            continue

        # Date demande (optionnel)
        request_date = _parse_date(parts[0], now) if parts[0] else None

        room = _normalize_room(parts[2]) if len(parts) > 2 else ""
        for_who = parts[3] if len(parts) > 3 else ""
        diapason = parts[4] if len(parts) > 4 else ""
        requester = _normalize_requester(parts[5]) if len(parts) > 5 else ""
        piano = parts[6] if len(parts) > 6 else ""
        time_str = parts[7] if len(parts) > 7 else ""

        results.append({
            "appointment_date": appointment_date,
            "request_date": request_date,
            "room": room,
            "for_who": for_who,
            "diapason": diapason,
            "requester": requester,
            "piano": piano,
            "time": time_str,
            "confidence": 1.0,
            "method": "tabular",
            "warnings": [],
        })

    return results


def _parse_with_ai(text: str) -> list[dict]:
    """Parse n'importe quel format d'email PDA via Claude Haiku."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        logger.warning("ANTHROPIC_API_KEY not set, AI parsing disabled")
        return _parse_compact_fallback(text)

    try:
        from anthropic import Anthropic
        client = Anthropic(api_key=api_key)

        today = datetime.now().strftime("%Y-%m-%d")

        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1000,
            temperature=0,
            system=f"""Tu parses des emails de demande d'accord de piano pour Place des Arts (Montréal).
Date du jour : {today}.

Chaque demande contient certains de ces champs :
- appointment_date : date du RV (format YYYY-MM-DD). Si l'année manque, utiliser l'année la plus logique par rapport à aujourd'hui.
- room : code de salle (WP, MS, TM, 5E, SCL, TJD, ODM, Salle E, ou tel quel si inconnu)
- for_who : événement ou organisme qui loue la salle (OSM, ONJ, OM, nom du concert, etc.)
- diapason : fréquence d'accordage (440, 442, etc.)
- requester : qui fait la demande (initiales ou nom)
- piano : description du piano (Steinway 9', Baldwin, etc.)
- time : exigence horaire (avant 12h, avant 9h, etc.)

Un email peut contenir PLUSIEURS demandes (plusieurs dates/salles).

Retourne UNIQUEMENT un JSON array :
[{{"appointment_date": "YYYY-MM-DD", "room": "...", "for_who": "...", "diapason": "...", "requester": "...", "piano": "...", "time": "..."}}]

Si un champ n'est pas mentionné, mettre une chaîne vide.""",
            messages=[{"role": "user", "content": text}],
        )

        raw = response.content[0].text.strip()
        if raw.startswith("```"):
            raw = re.sub(r"^```(?:json)?\s*", "", raw)
            raw = re.sub(r"\s*```$", "", raw)

        parsed = json.loads(raw)
        if not isinstance(parsed, list):
            parsed = [parsed]

        results = []
        for item in parsed:
            item["confidence"] = 0.9
            item["method"] = "ai"
            item["warnings"] = []
            # Normaliser
            item["room"] = _normalize_room(item.get("room", ""))
            item["requester"] = _normalize_requester(item.get("requester", ""))
            results.append(item)

        logger.info(f"AI parsed {len(results)} request(s) from email")
        return results

    except Exception as e:
        logger.error(f"AI email parsing failed: {e}")
        return _parse_compact_fallback(text)


def _parse_compact_fallback(text: str) -> list[dict]:
    """
    Fallback sans IA — tente de parser le format compact.
    Ex: '6-Dec MS Concert 2 pianos 442 Piano Steinway avant 13h'
    """
    results = []
    now = datetime.now()

    for line in text.splitlines():
        line = line.strip()
        if not line or len(line) < 10:
            continue

        words = line.split()
        if len(words) < 3:
            continue

        # Essayer de trouver une date au début
        date = _parse_date(words[0], now)
        if not date:
            continue

        # Essayer de trouver une salle
        room = ""
        if len(words) > 1 and words[1].upper() in KNOWN_ROOMS:
            room = _normalize_room(words[1])

        # Extraire le diapason (3 chiffres)
        diapason = ""
        for w in words:
            if re.match(r"^\d{3}$", w):
                diapason = w
                break

        # Extraire l'heure
        time_str = ""
        for i, w in enumerate(words):
            if re.search(r"\d+h", w, re.IGNORECASE) or w.lower() == "avant":
                if w.lower() == "avant" and i + 1 < len(words):
                    time_str = f"{w} {words[i + 1]}"
                else:
                    time_str = w
                break

        results.append({
            "appointment_date": date,
            "room": room,
            "for_who": "",
            "diapason": diapason,
            "requester": "",
            "piano": "",
            "time": time_str,
            "confidence": 0.5,
            "method": "compact_fallback",
            "warnings": ["Parsing basique — vérifier les champs"],
        })

    return results


# ── Helpers ──


def _parse_date(date_str: str, now: datetime) -> Optional[str]:
    """Parse une date flexible → YYYY-MM-DD ou None."""
    if not date_str:
        return None

    date_str = date_str.strip()

    # Format YYYY-MM-DD
    if re.match(r"\d{4}-\d{2}-\d{2}", date_str):
        return date_str[:10]

    # Format DD/MM/YYYY ou DD-MM-YYYY
    m = re.match(r"(\d{1,2})[/-](\d{1,2})[/-](\d{4})", date_str)
    if m:
        return f"{m.group(3)}-{int(m.group(2)):02d}-{int(m.group(1)):02d}"

    # Format avec mois texte (6-Dec, 21 décembre, etc.)
    mois = {
        "jan": 1, "fev": 2, "feb": 2, "mar": 3, "avr": 4, "apr": 4,
        "mai": 5, "may": 5, "jun": 6, "jui": 6, "jul": 7, "aou": 8,
        "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12, "déc": 12,
    }
    # Normaliser les accents pour le matching
    import unicodedata
    def _strip_accents(s):
        return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")

    m = re.match(r"(\d{1,2})[-/\s]+([a-zéèûôàâê]+)", date_str.lower())
    if m:
        day = int(m.group(1))
        month_text = m.group(2)
        month_str = month_text[:3]
        month = mois.get(month_str)
        if not month:
            month = mois.get(_strip_accents(month_str))
        if month:
            year = now.year
            candidate = datetime(year, month, day)
            if (candidate - now).days < -30:
                year += 1
            return f"{year}-{month:02d}-{day:02d}"

    return None


def _normalize_room(room: str) -> str:
    if not room:
        return ""
    upper = room.strip().upper()
    return KNOWN_ROOMS.get(upper, room.strip())


def _normalize_requester(req: str) -> str:
    if not req:
        return ""
    upper = req.strip().upper()
    return REQUESTER_MAP.get(upper, req.strip())
