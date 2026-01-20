"""
Parser email Place des Arts (porté depuis V4).

Fonctions principales :
- parse_email_text(email_text) -> liste de dict structurés (date, room, piano, etc.)
- parse_email_block / parse_single_line_format / normalize_room
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any


# ------------------------------------------------------------
# Helpers date/heure (version locale, sans app.date_utils)
# ------------------------------------------------------------

def parse_date_flexible(date_str: str, current_date: datetime) -> datetime:
    """
    Parse une date sans année en déterminant l'année intelligemment.
    Supporte formats FR/EN : "30 juillet", "14 juin", "5-Dec", "7-Dec", "15-Jan".
    """
    # Mapping mois français et anglais
    mois_fr = {
        'janvier': 1, 'février': 2, 'fevrier': 2, 'mars': 3, 'avril': 4, 'mai': 5, 'juin': 6,
        'juillet': 7, 'août': 8, 'aout': 8, 'septembre': 9, 'octobre': 10, 'novembre': 11, 'décembre': 12, 'decembre': 12,
        'jan': 1, 'janv': 1, 'fév': 2, 'fev': 2, 'févr': 2, 'fevr': 2, 'mar': 3, 'mars': 3,
        'avr': 4, 'avril': 4, 'mai': 5, 'jui': 6, 'juin': 6, 'jul': 7, 'juil': 7, 'juillet': 7,
        'aoû': 8, 'aou': 8, 'août': 8, 'aout': 8, 'sep': 9, 'sept': 9, 'septembre': 9,
        'oct': 10, 'octobre': 10, 'nov': 11, 'novembre': 11, 'déc': 12, 'dec': 12, 'décembre': 12, 'decembre': 12
    }
    mois_en = {
        'jan': 1, 'january': 1, 'feb': 2, 'february': 2, 'mar': 3, 'march': 3,
        'apr': 4, 'april': 4, 'may': 5, 'jun': 6, 'june': 6,
        'jul': 7, 'july': 7, 'aug': 8, 'august': 8, 'sep': 9, 'september': 9,
        'oct': 10, 'october': 10, 'nov': 11, 'november': 11, 'dec': 12, 'december': 12
    }

    date_str_clean = date_str.strip()

    # Format général "27 November 2025" ou "27 November" ou "5 décembre"
    match_en_full = re.match(r'(\d{1,2})\s+(\w+)(?:\s+(\d{4}))?', date_str_clean, re.IGNORECASE)
    if match_en_full:
        day = int(match_en_full.group(1))
        month_name = match_en_full.group(2).lower()
        year_str = match_en_full.group(3)
        # Check both English and French months
        if month_name in mois_en:
            month = mois_en[month_name]
        elif month_name in mois_fr:
            month = mois_fr[month_name]
        else:
            raise ValueError(f"Mois invalide: {month_name}")

        if year_str:
            return datetime(int(year_str), month, day)
    elif re.match(r'(\d{1,2})[-/](\w{3})', date_str_clean, re.IGNORECASE):
        match_en = re.match(r'(\d{1,2})[-/](\w{3})', date_str_clean, re.IGNORECASE)
        day = int(match_en.group(1))
        month_name = match_en.group(2).lower()
        if month_name in mois_en:
            month = mois_en[month_name]
        elif month_name in mois_fr:
            month = mois_fr[month_name]
        else:
            raise ValueError(f"Mois invalide: {month_name}")
    else:
        match_fr = re.match(r'(\d{1,2})[-/\s]+([a-zàâäéèêëïîôùûü]+)', date_str_clean.lower())
        if not match_fr:
            match_fr = re.match(r'(\d{1,2})([a-zàâäéèêëïîôùûü]{3,})', date_str_clean.lower())
        if not match_fr:
            raise ValueError(f"Format de date invalide: {date_str}")
        day = int(match_fr.group(1))
        month_name = match_fr.group(2).strip()
        month_name_normalized = month_name.replace('é', 'e').replace('û', 'u').replace('ô', 'o').replace('è', 'e')
        if month_name in mois_fr:
            month = mois_fr[month_name]
        elif month_name_normalized in mois_fr:
            month = mois_fr[month_name_normalized]
        else:
            raise ValueError(f"Mois invalide: {month_name} (format: {date_str})")

    current_year = current_date.year

    # Essayer avec l'année actuelle ET l'année prochaine
    try:
        candidate_current = datetime(current_year, month, day)
    except ValueError:
        # Date invalide (ex: 29 février année non bissextile)
        raise ValueError(f"Date invalide: jour={day}, mois={month}")

    try:
        candidate_next = datetime(current_year + 1, month, day)
    except ValueError:
        candidate_next = None

    # Calculer la différence en jours pour les deux options
    days_diff_current = (candidate_current - current_date).days
    days_diff_next = (candidate_next - current_date).days if candidate_next else 999

    # Logique de décision avec fenêtre de 30 jours passé et 6 mois futur:
    # - Si date année actuelle est dans [-30 jours, +180 jours] → année actuelle
    # - Sinon → année prochaine
    if -30 <= days_diff_current <= 180:
        year = current_year
    elif candidate_next and 0 <= days_diff_next <= 180:
        year = current_year + 1
    else:
        # Par défaut, prendre l'option la plus proche
        year = current_year if abs(days_diff_current) < abs(days_diff_next) else current_year + 1

    return datetime(year, month, day)


def parse_time_flexible(time_str: str) -> str:
    """Renvoie la chaîne telle quelle (fallback simple)."""
    return time_str.strip()


# Aliases pour compatibilité
parse_date_with_year = parse_date_flexible
parse_time = parse_time_flexible


# ------------------------------------------------------------
# Parser
# ------------------------------------------------------------

def normalize_room(room_text: str) -> str:
    """
    Normalise les codes de salles PDA selon les règles strictes.

    Salles fixes PDA:
    - Maison Symphonique (MS)
    - 5e salle (5E)
    - Théâtre Maisonneuve (TM)
    - Théâtre Jean-Duceppe (TJD)
    - Wilfrid-Pelletier (WP) + WP loge A
    - Claude-Léveillée (SCL)

    RÈGLE: Mappe les abréviations (CL, SCL) vers noms standards SANS inventer de préfixes.
    """
    if not room_text:
        return ''

    room_text = room_text.strip()

    # Codes connus - acceptés tels quels
    known_codes = ['WP', 'TM', 'MS', 'TJD', '5E', 'SCL']
    if room_text.upper() in known_codes:
        return room_text.upper()

    # Normalisation stricte: CL → SCL (Claude-Léveillée)
    if room_text.upper() == 'CL':
        return 'SCL'

    # WP loge A (cas spécial)
    if 'loge' in room_text.lower() and 'wp' in room_text.lower():
        return 'WP loge A'

    # Mapping vers codes standards (SANS préfixes inventés)
    room_mapping = {
        # Wilfrid-Pelletier
        'wilfrid-pelletier': 'WP',
        'wilfrid pelletier': 'WP',
        'wilfrid': 'WP',
        'pelletier': 'WP',

        # Théâtre Maisonneuve
        'théâtre maisonneuve': 'TM',
        'theatre maisonneuve': 'TM',
        'maisonneuve': 'TM',

        # Maison Symphonique
        'maison symphonique': 'MS',

        # 5e salle
        'cinquième salle': '5E',
        '5e salle': '5E',
        'cinquieme salle': '5E',

        # Claude-Léveillée (pas de préfixes "Studio" ou "Salle")
        'claude-léveillée': 'SCL',
        'claude léveillée': 'SCL',
        'claude leveillee': 'SCL',
        'claude-leveillee': 'SCL',
        'studio claude-léveillée': 'SCL',
        'studio claude léveillée': 'SCL',
        'salle claude léveillée': 'SCL',
        'salle claude-léveillée': 'SCL',
        'cl': 'SCL',  # Abréviation courante

        # Théâtre Jean-Duceppe
        'théâtre jean-duceppe': 'TJD',
        'theatre jean-duceppe': 'TJD',
        'jean-duceppe': 'TJD',
        'duceppe': 'TJD',
    }

    room_lower = room_text.lower()
    for key, code in room_mapping.items():
        if key in room_lower:
            return code

    # Si aucune correspondance, retourner tel quel (majuscules si c'est un code court)
    if len(room_text) <= 10 and room_text.isupper():
        return room_text

    return room_text


def parse_tabular_rows(text: str, current_date: datetime) -> List[Dict]:
    """
    Parse des lignes tabulaires (copier-coller de tableur), délimitées par tabulations.

    RÈGLE 2: Utilise le champ 'Commentaire' (colonne 9) pour infos contextuelles.
    RÈGLE 4: Séparation stricte Date (YYYY-MM-DD) / Heure (ex: 'Avant 10h').

    Attendu (colonnes min):
    0: Date demande (optionnel)
    1: Date RDV (YYYY-MM-DD seulement)
    2: Salle
    3: Pour qui
    4: Diapason
    5: Demandeur
    6: Piano
    7: Heure (ex: '10h', 'Avant 10h', '14h30')
    8: Technicien (nom)
    9: Commentaire (notes contextuelles - ex: 'alternative du samedi 10 janvier')
    """
    rows = []
    tech_map = {
        'nick': 'usr_U9E5bLxrFiXqTbE8',
        'nicolas': 'usr_U9E5bLxrFiXqTbE8',
        'allan': 'usr_allan',
        'louise': 'usr_louise',
        'jp': 'usr_jp',
        'jean-philippe': 'usr_jp',
    }
    for line in text.splitlines():
        if '\t' not in line:
            continue
        parts = [p.strip() for p in line.split('\t')]
        if len(parts) < 8:
            continue
        # RÈGLE 4: Séparation stricte Date / Heure
        req_date_raw = parts[0] or None
        appt_date_raw = parts[1]

        try:
            # Date RDV (YYYY-MM-DD seulement)
            appt_date = parse_date_with_year(appt_date_raw, current_date)
        except Exception:
            continue

        req_date = None
        if req_date_raw:
            try:
                req_date = parse_date_with_year(req_date_raw, current_date)
            except Exception:
                req_date = None

        # Heure (colonne 7) - ne JAMAIS mélanger avec la date
        time_str = parts[7] if len(parts) >= 8 else ''

        # Technicien
        tech = parts[8] if len(parts) >= 9 else ''
        tech_id = tech_map.get(tech.lower())

        # RÈGLE 2: Commentaire (colonne 9) pour infos contextuelles
        # Ex: "alternative du samedi 10 janvier"
        notes_raw = parts[9] if len(parts) >= 10 else ''

        # Calculer le jour de la semaine (seulement samedi/dimanche)
        jours_semaine = ['lundi', 'mardi', 'mercredi', 'jeudi', 'vendredi', 'samedi', 'dimanche']
        jour_semaine = jours_semaine[appt_date.weekday()]
        is_weekend = appt_date.weekday() >= 5  # 5=samedi, 6=dimanche

        # Enrichir le commentaire avec le jour si c'est un weekend
        if is_weekend:
            if notes_raw and jour_semaine.lower() in notes_raw.lower():
                # Jour déjà mentionné, ne pas dupliquer
                notes = notes_raw
            elif notes_raw:
                # Ajouter le jour avant le commentaire
                notes = f"{jour_semaine} - {notes_raw}"
            else:
                # Pas de commentaire, juste le jour
                notes = jour_semaine
        else:
            # Jour de semaine: garder le commentaire tel quel
            notes = notes_raw

        # RÈGLE 1: Champ Demandeur - vérifier et nettoyer
        requester = parts[5].strip() if len(parts) >= 6 else ''
        if requester:
            requester_lower = requester.lower()
            # Ne pas deviner depuis codes de salle
            room_codes = ['wp', 'tm', 'ms', 'tjd', '5e', 'scl', 'cl']
            if requester_lower in room_codes:
                requester = ''  # Vider si c'est un code de salle
            # Mapping Isabelle → IC
            elif 'isabelle' in requester_lower or 'clairoux' in requester_lower:
                requester = 'IC'

        rows.append({
            'date': appt_date,
            'request_date': req_date,
            'room': normalize_room(parts[2]) if len(parts) >= 3 else '',
            'for_who': parts[3] if len(parts) >= 4 else '',
            'diapason': parts[4] if len(parts) >= 5 else '',
            'requester': requester,
            'piano': parts[6] if len(parts) >= 7 else '',
            'time': time_str,  # Heure seule (ex: "Avant 10h", "14h30")
            'technician': tech,
            'technician_id': tech_id or '',
            'notes': notes,  # Commentaire + jour weekend si applicable
            'service': 'Accord standard',
            'confidence': 1.0,
            'warnings': []
        })
    return rows


def parse_single_line_format(line: str, result: Dict, current_date: datetime) -> bool:
    """
    Parse format compact type:
    - '6-Dec MS Concert 2 pianos 442 Piano ... avant 13h'
    - '21-Dec 5E Charlie Brown 440 IC Piano Baldwin (9') avant 8h'

    Format attendu (avec espaces multiples):
    Date Salle PourQui Diapason Demandeur Piano Heure
    """
    words = line.split()
    if len(words) < 4:
        return False
    try:
        # Date
        result['date'] = parse_date_with_year(words[0], current_date)

        # Salle (doit être en position 1 et être un code de salle)
        if words[1] in ['MS', 'WP', 'TM', 'SD', 'C5', 'SCL', 'ODM', '5E', 'CL']:
            result['room'] = normalize_room(words[1])

            # Format compact détecté avec salle en position 1
            # Ordre: Date Salle PourQui Diapason Demandeur Piano Heure

            # Trouver le diapason (3 chiffres)
            diapason_idx = None
            for i, w in enumerate(words):
                if re.match(r'^\d{3}$', w):
                    result['diapason'] = w
                    diapason_idx = i
                    break

            # Trouver l'heure (mot avec 'Xh' ou 'avant')
            time_idx = None
            for i, w in enumerate(words):
                # Rechercher pattern d'heure: \d+h ou "avant"
                if re.search(r'\d+h', w, re.IGNORECASE) or w.lower() == 'avant':
                    if w.lower() == 'avant' and i+1 < len(words):
                        result['time'] = f"{w} {words[i+1]}"
                        time_idx = i
                    else:
                        result['time'] = w
                        time_idx = i
                    break

            # Trouver "Piano" keyword
            piano_idx = None
            for i, w in enumerate(words):
                if w.lower() == 'piano':
                    piano_idx = i
                    break

            # Pour qui: entre salle (idx 1) et diapason (ou Piano si pas de diapason)
            if diapason_idx and diapason_idx > 2:
                for_who_parts = words[2:diapason_idx]
                result['for_who'] = ' '.join(for_who_parts)
            elif piano_idx and piano_idx > 2:
                # Pas de diapason, extraire entre salle et "Piano"
                for_who_parts = words[2:piano_idx]
                result['for_who'] = ' '.join(for_who_parts)
            elif len(words) > 2:
                # Ni diapason ni Piano, prendre tout après la salle jusqu'à l'heure
                end_idx = time_idx if time_idx else len(words)
                for_who_parts = words[2:end_idx]
                result['for_who'] = ' '.join(for_who_parts)

            # Demandeur: entre diapason et "Piano" keyword
            if diapason_idx and piano_idx and piano_idx > diapason_idx + 1:
                requester_parts = words[diapason_idx + 1:piano_idx]
                result['requester'] = ' '.join(requester_parts)

            # Piano: après "Piano" keyword jusqu'à l'heure
            if piano_idx:
                end_idx = time_idx if time_idx else len(words)
                piano_parts = words[piano_idx:end_idx]
                result['piano'] = ' '.join(piano_parts)

            result['confidence'] = 0.85
            return True

        # Format ancien (sans salle en position 1)
        # Diapason
        for w in words:
            if re.match(r'^\d{3}$', w):
                result['diapason'] = w
                break
        # Heure
        for i, w in enumerate(words):
            if 'h' in w or w.lower() == 'avant':
                result['time'] = f"{w} {words[i+1]}" if w.lower() == 'avant' and i+1 < len(words) else w
                break
        # Pour qui (entre début et diapason)
        for_who_parts = []
        start_idx = 2 if result.get('room') else 1
        for i in range(start_idx, len(words)):
            word = words[i]
            if re.match(r'^\d{3}$', word) or word.lower() == 'piano':
                break
            for_who_parts.append(word)
        if for_who_parts:
            result['for_who'] = ' '.join(for_who_parts)
        # Piano (après le mot Piano)
        piano_parts = []
        in_piano = False
        for w in words:
            if w.lower() == 'piano':
                in_piano = True
                continue
            if in_piano:
                if re.match(r'^\d{6}$', w) or re.search(r'\d{1,2}h', w):
                    break
                piano_parts.append(w)
        if piano_parts:
            result['piano'] = ' '.join(piano_parts)
        result['confidence'] = 0.6
        return True
    except Exception:
        return False


def parse_natural_language_request(text: str, current_date: datetime) -> Optional[Dict]:
    """
    Parse des demandes en langage naturel comme:
    "Est-ce possible de faire un accord du Steinway 9' D - New York à 442 de la Salle D le 20 janvier entre 8h00 et 9h00?"

    Patterns détectés:
    - "accord" / "tuning" → service
    - "Steinway 9' D" / "Yamaha C7" → piano
    - "à 442" / "440 Hz" → diapason
    - "Salle D" / "MS" / "WP" → room
    - "20 janvier" → date
    - "entre 8h00 et 9h00" / "avant 10h" → time
    """
    result = {
        'date': None, 'request_date': None, 'time': None, 'room': None,
        'piano': None, 'service': None, 'for_who': None, 'diapason': None,
        'requester': None, 'notes': None, 'confidence': 0.0, 'warnings': []
    }

    text_lower = text.lower()

    # 1. Détecter le service demandé
    service_patterns = [
        (r'accord', 'Accord'),
        (r'tuning', 'Accord'),
        (r'réparation', 'Réparation'),
        (r'voicing', 'Voicing'),
        (r'régulation', 'Régulation'),
        (r'entretien', 'Entretien')
    ]
    for pattern, service_name in service_patterns:
        if re.search(pattern, text_lower):
            result['service'] = service_name
            result['confidence'] += 0.15
            break

    # 2. Détecter le piano (marque + modèle)
    # Format: "Steinway 9' D - New York" ou "Yamaha C7" ou "Baldwin 9'"
    piano_patterns = [
        r'(steinway\s+\d+[\'"]?\s*[a-z]?\s*-?\s*[a-z\s]*)',  # Steinway 9' D - New York
        r'(yamaha\s+[a-z]\d+)',  # Yamaha C7
        r'(kawai\s+[a-z]+\d*)',  # Kawai GX7
        r'(baldwin\s+\d+[\'"]?)',  # Baldwin 9'
        r'(bösendorfer\s+\d+)',  # Bösendorfer 280
        r'(fazioli\s+[a-z]*\d+)'  # Fazioli F278
    ]
    for pattern in piano_patterns:
        match = re.search(pattern, text_lower)
        if match:
            # Extraire le texte original (avec majuscules)
            start, end = match.span()
            result['piano'] = text[start:end].strip()
            result['confidence'] += 0.2
            break

    # 3. Détecter le diapason (440, 441, 442, etc.)
    diapason_match = re.search(r'(?:à|a)\s*(\d{3})(?:\s*hz)?', text_lower)
    if diapason_match:
        result['diapason'] = diapason_match.group(1)
        result['confidence'] += 0.15

    # 4. Détecter la salle
    # Format: "de la Salle D" / "Salle D" / "MS" / "WP"
    room_patterns = [
        (r'salle\s+([a-z])', r'\1'),  # Salle D → D
        (r'\b(ms|wp|tm|tjd|5e|scl)\b', r'\1'),  # Codes standards
        (r'maison\s+symphonique', 'MS'),
        (r'wilfrid[-\s]?pelletier', 'WP'),
        (r'théâtre\s+maisonneuve', 'TM'),
        (r'theater\s+maisonneuve', 'TM'),
        (r'jean[-\s]?duceppe', 'TJD'),
        (r'claude[-\s]?léveillée', 'SCL')
    ]
    for pattern, replacement in room_patterns:
        match = re.search(pattern, text_lower)
        if match:
            if replacement.startswith(r'\1'):
                result['room'] = match.group(1).upper()
            else:
                result['room'] = replacement
            result['confidence'] += 0.15
            break

    # 5. Détecter la date
    # Format: "le 20 janvier" / "20 janvier" / "janvier 20"
    date_patterns = [
        r'(?:le\s+)?(\d{1,2})\s+(janvier|février|fevrier|mars|avril|mai|juin|juillet|août|aout|septembre|octobre|novembre|décembre|decembre)',
        r'(?:le\s+)?(\d{1,2})\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)',
        r'(\d{1,2})[-/](\w{3,})'
    ]
    for pattern in date_patterns:
        match = re.search(pattern, text_lower)
        if match:
            try:
                date_str = match.group(0).replace('le ', '')
                result['date'] = parse_date_flexible(date_str, current_date)
                result['confidence'] += 0.2
                break
            except Exception as e:
                result['warnings'].append(f"Erreur parsing date: {e}")

    # 6. Détecter l'heure
    # Format: "entre 8h00 et 9h00" / "avant 10h" / "à 14h30"
    time_patterns = [
        r'entre\s+(\d{1,2}h\d{2})\s+et\s+(\d{1,2}h\d{2})',  # entre 8h00 et 9h00
        r'avant\s+(\d{1,2}h\d{2})',  # avant 10h
        r'(?:à|a)\s+(\d{1,2}h\d{2})',  # à 14h30
        r'(\d{1,2}h\d{2})',  # 14h30
    ]
    for pattern in time_patterns:
        match = re.search(pattern, text_lower)
        if match:
            if 'entre' in match.group(0):
                result['time'] = f"{match.group(1)}-{match.group(2)}"
            elif 'avant' in match.group(0):
                result['time'] = f"avant {match.group(1)}"
            else:
                result['time'] = match.group(1)
            result['confidence'] += 0.15
            break

    # 7. Détecter le demandeur (signature en fin de message)
    # Chercher les noms connus en fin de texte
    lines = text.split('\n')
    for line in reversed(lines):
        line_stripped = line.strip()
        if not line_stripped or '@' in line_stripped:
            continue
        # Mapping des demandeurs connus
        requester_mapping = {
            'annie jenkins': 'ANNIE JENKINS',
            'annie': 'ANNIE JENKINS',
            'jenkins': 'ANNIE JENKINS',
            'isabelle clairoux': 'IC',
            'isabelle': 'IC',
            'clairoux': 'IC',
            'patricia': 'PT',
            'alain': 'AJ'
        }
        line_lower = line_stripped.lower()
        for name, code in requester_mapping.items():
            if name in line_lower:
                result['requester'] = code
                result['confidence'] += 0.1
                break
        if result['requester']:
            break

    # Retourner None si aucun élément essentiel n'a été détecté
    if not result['date'] and not result['piano'] and not result['room']:
        return None

    # TOUJOURS ajouter un avertissement pour le format naturel (même si confiance élevée)
    # Cela permettra à l'utilisateur de valider et d'apprendre au système
    result['warnings'].append("Format naturel détecté - Veuillez confirmer les champs")

    return result


def parse_email_block(block_text: str, current_date: datetime) -> Dict:
    lines = [l.strip() for l in block_text.strip().split('\n') if l.strip()]
    result = {
        'date': None, 'request_date': None, 'time': None, 'room': None,
        'piano': None, 'service': None, 'for_who': None, 'diapason': None,
        'requester': None, 'notes': None, 'confidence': 0.0, 'warnings': []
    }

    # NOUVEAU: Essayer d'abord le parsing en langage naturel
    natural_result = parse_natural_language_request(block_text, current_date)
    if natural_result and natural_result['confidence'] >= 0.5:
        return natural_result

    # Try single-line format on each line in the block
    for line in lines:
        temp_result = result.copy()
        if parse_single_line_format(line, temp_result, current_date):
            # If we successfully parsed as single-line, return immediately
            return temp_result

    parts_by_dash = [p.strip() for p in block_text.split(' - ')]
    has_enough_parts = len(parts_by_dash) >= 4 and all(len(p) > 0 for p in parts_by_dash[:4])
    parts_have_no_newlines = all('\n' not in p for p in parts_by_dash[:4])
    is_dash_format = has_enough_parts and parts_have_no_newlines

    if is_dash_format:
        parts = parts_by_dash
        if len(parts) >= 4:
            date_time = parts[0]
            date_match = re.match(r'(\d{1,2}\s+[a-zéû]+)\s+(.+)', date_time, re.IGNORECASE)
            if date_match:
                date_str = date_match.group(1)
                time_str = date_match.group(2)
                try:
                    result['date'] = parse_date_with_year(date_str, current_date)
                    result['time'] = parse_time(time_str)
                    result['confidence'] += 0.4
                except Exception as e:
                    result['warnings'].append(f"Erreur parsing date: {e}")
            result['room'] = normalize_room(parts[1]); result['confidence'] += 0.2
            result['piano'] = parts[2]; result['confidence'] += 0.2
            result['service'] = parts[3]; result['confidence'] += 0.2
            if len(parts) > 4:
                result['notes'] = ' - '.join(parts[4:])
    else:
        date_pattern = re.compile(r'^(\d{1,2})[-/\s]*(\w{3,})', re.IGNORECASE)
        room_keywords = ['WP', 'TM', 'MS', 'SD', 'C5', 'SCL', 'ODM', '5E', 'CL']
        piano_keywords = ['Steinway', 'Yamaha', 'Kawai', 'Bösendorfer', 'Fazioli', 'Baldwin', 'Mason']

        # Heuristiques spécifiques au format 6 lignes (date, room, for_who, diapason, piano, time)
        def is_time_line(line: str) -> bool:
            return bool(re.search(r'\d{1,2}h', line, re.IGNORECASE) or 'avant' in line.lower() or 'après' in line.lower() or 'apres' in line.lower())

        def is_diapason_line(line: str) -> bool:
            return bool(re.match(r'^\d{3}$', line.strip()))

        def is_requester_line(line: str) -> bool:
            # Codes de requester valides (initiales connues)
            known_requester_codes = ['IC', 'AJ', 'PT']
            line_upper = line.strip().upper()
            # Seulement si c'est exactement un code connu (pas "ODM" ou autres codes)
            return bool(line_upper in known_requester_codes)

        # Date
        for line in lines:
            if date_pattern.search(line):
                try:
                    result['date'] = parse_date_with_year(line, current_date)
                    result['confidence'] += 0.3
                    break
                except Exception as e:
                    result['warnings'].append(f"Erreur parsing date '{line}': {e}")
        # Salle
        room_found_at_idx = None
        for line_idx, line in enumerate(lines):
            if any(kw.upper() in line.upper() for kw in room_keywords):
                result['room'] = normalize_room(line)
                result['confidence'] += 0.2
                room_found_at_idx = line_idx
                break

        # Détection structurée par rôle (ordre : for_who -> diapason -> requester -> piano -> time)
        candidate_for_who = None
        candidate_piano = None
        candidate_requester = None
        found_data_block = False  # Track if we're in the structured data section

        # Detect if this is a line-by-line format (each field on its own line)
        # Pattern: Date -> Room -> Name (for_who) -> Diapason -> Piano -> Time -> Requester
        is_multiline_format = len(lines) >= 5  # At least date, room, for_who, diapason/piano, time

        def is_candidate_name(line: str) -> bool:
            if not line:
                return False
            if any(ch.isdigit() for ch in line):
                return False
            parts = line.split()
            if len(parts) > 2:
                return False
            if len(line) > 20:
                return False
            # première lettre majuscule
            lower = line.lower()
            polite_words = ['merci', 'bientot', 'bientôt', 'possible', 'confirm', 'avant', 'concert', 'piano']
            if any(w in lower for w in polite_words):
                return False
            return line[0].isupper()

        for idx, line in enumerate(lines):
            ls = line.strip()
            if not ls:
                continue
            if result.get('date') and date_pattern.search(ls):
                continue

            lower = ls.lower()
            has_brand = any(kw.lower() in lower for kw in [k.lower() for k in piano_keywords])
            has_piano_word = ('piano de' in lower) or (lower.startswith('piano ')) or (' piano ' in lower)
            is_concert_label = 'concert' in lower and 'piano' in lower and not has_brand

            # Skip room lines ONLY if they don't contain piano brand/keyword
            if result.get('room') and any(kw.upper() in ls.upper() for kw in room_keywords):
                if not has_brand and not has_piano_word:
                    continue

            # Mark when we enter the structured data block (after date/room)
            if result.get('date') or result.get('room'):
                found_data_block = True

            # In structured data block: names are "for_who"
            # After structured data block (diapason/piano/time found): names are "requester"
            has_structured_data = result.get('diapason') or result.get('piano') or result.get('time')

            # "Pour qui" doit être détecté AVANT les données structurées (diapason, piano, time)
            # Exclure les codes de requester connus (IC, AJ, PT) et les codes de salle
            if (candidate_for_who is None and 
                found_data_block and 
                not has_structured_data and 
                not is_diapason_line(ls) and 
                not is_requester_line(ls) and 
                not is_time_line(ls) and 
                not has_brand and 
                not has_piano_word and
                ls.upper() not in room_keywords):  # Exclure aussi les codes de salle
                candidate_for_who = ls
                continue

            if not result.get('diapason') and is_diapason_line(ls):
                result['diapason'] = ls
                result['confidence'] += 0.1
                continue

            if not result.get('requester') and is_requester_line(ls):
                result['requester'] = ls
                result['confidence'] += 0.1
                continue

            # After structured data, names are requester (signature)
            # MAIS seulement si for_who n'est pas déjà rempli avec cette ligne
            if (candidate_requester is None and 
                has_structured_data and 
                is_candidate_name(ls) and
                candidate_for_who != ls):  # Ne pas capturer si c'est déjà dans for_who
                candidate_requester = ls

            if not result.get('piano') and (has_brand or has_piano_word or is_concert_label):
                result['piano'] = ls
                result['confidence'] += 0.2
                continue

            if not result.get('time') and is_time_line(ls):
                result['time'] = parse_time(ls)
                result['confidence'] += 0.1
                continue

        # Multi-line format: use simple positional logic
        # The line immediately after room is "pour qui"
        if is_multiline_format and room_found_at_idx is not None and not result.get('for_who'):
            next_idx = room_found_at_idx + 1
            if next_idx < len(lines):
                next_line = lines[next_idx].strip()
                # Check if this line is likely a name (not diapason, not piano, not time, not requester code)
                if (next_line and
                    not is_diapason_line(next_line) and
                    not is_time_line(next_line) and
                    not is_requester_line(next_line) and  # Exclure les codes de requester
                    not any(kw.lower() in next_line.lower() for kw in piano_keywords) and
                    'piano' not in next_line.lower()):
                    result['for_who'] = next_line
                    result['confidence'] += 0.2

        if not result.get('piano') and candidate_piano:
            result['piano'] = candidate_piano
            result['confidence'] += 0.1
        # PRIORITÉ: for_who doit être assigné AVANT requester
        # Si on a un candidate_for_who, il a la priorité (même si candidate_requester existe)
        if not result.get('for_who') and candidate_for_who:
            result['for_who'] = candidate_for_who
            result['confidence'] += 0.1
        # Requester seulement si for_who est déjà rempli ET que ce n'est pas le même texte
        if not result.get('requester') and candidate_requester:
            # Ne pas mettre dans requester si c'est déjà dans for_who
            if result.get('for_who') != candidate_requester:
                result['requester'] = candidate_requester
                result['confidence'] += 0.05

        # RÈGLE 1: Champ Demandeur vierge si pas explicitement nommé
        # Mapper les noms de demandeurs connus vers leurs codes
        # Ne jamais deviner à partir des codes de salle
        if result.get('requester'):
            requester_lower = result['requester'].lower().strip()

            # Si c'est juste un code de salle (WP, TM, MS, etc.), VIDER le champ
            room_codes = ['wp', 'tm', 'ms', 'tjd', '5e', 'scl', 'cl', 'sd', 'c5', 'odm']
            # Vérifier aussi si le requester contient un code de salle (ex: "Clown ODM")
            if requester_lower in room_codes or any(code in requester_lower for code in room_codes):
                result['requester'] = ''  # Champ vide si c'est un code de salle
            else:
                # Mapping noms connus → codes
                requester_mapping = {
                    'isabelle': 'IC',
                    'isabelle clairoux': 'IC',
                    'isabelle constantineau': 'IC',
                    'clairoux': 'IC',  # Nom de famille seul
                    # Ajouter d'autres mappings ici au besoin
                    # 'nom': 'CODE',
                }
                for name, code in requester_mapping.items():
                    if name in requester_lower:
                        result['requester'] = code
                        break

                # Si ce n'est PAS un nom de personne reconnu (ex: initiales courtes non mappées),
                # vérifier si c'est un nom valide (contient au moins 3 caractères)
                if result['requester'] and len(result['requester'].strip()) < 3:
                    # Initiales de 1-2 lettres: garder seulement si c'est un code connu
                    known_codes = ['IC', 'AJ', 'PT']  # Liste des codes valides
                    if result['requester'].upper() not in known_codes:
                        result['requester'] = ''  # Vider si code inconnu

        if not result.get('service'):
            result['service'] = 'Accord standard'
        result['request_date'] = None

    if result['confidence'] < 0.5:
        result['warnings'].append("Confiance faible - Vérification manuelle requise")
    return result


def parse_email_text(email_text: str) -> List[Dict]:
    """
    Parse un texte email complet contenant plusieurs demandes.
    Retourne une liste de dicts structurés (date, room, piano, etc.).
    """
    current_date = datetime.now()
    # Heuristique de signature (demandeur global)
    def extract_signature_requester(all_lines: List[str]) -> Optional[str]:
        polite_words = ['merci', 'bientot', 'bientôt', 'possible', 'confirm', 'cordialement', 'bien à vous', 'bien a vous']
        for raw in reversed(all_lines):
            ls = raw.strip()
            if not ls:
                continue
            if any(ch.isdigit() for ch in ls):
                continue
            if '@' in ls:
                continue
            if len(ls.split()) > 3 or len(ls) > 40:
                continue
            lower = ls.lower()
            if any(w in lower for w in polite_words):
                continue
            # Nom court capitalisé → signature candidate
            if ls[0].isupper():
                return ls
        return None
    # 1) Si tabulaire (tableur collé avec tabs), traiter en priorité
    tabular = parse_tabular_rows(email_text, current_date)
    if tabular:
        return tabular

    requests: List[Dict] = []
    greeting_patterns = [
        r'^bonjour\s*,?\s*$', r'^bonsoir\s*,?\s*$', r'^salut\s*,?\s*$',
        r'^hello\s*,?\s*$', r'^hi\s*,?\s*$', r'^cher\s+', r'^chère\s+',
        r'^madame\s*,?\s*$', r'^monsieur\s*,?\s*$', r'^merci\s+', r'^cordiale?ment\s*,?\s*$',
        r'^bien\s+à\s+vous\s*,?\s*$', r'^à\s+bientôt\s*,?\s*$', r'^cordialement\s*,?\s*$',
        r'^best\s+regards\s*,?\s*$', r'voici\s+une?\s+nouvelle?\s+demande.*',
        r'voici\s+les?\s+demandes?.*', r'.*confirmer\s+si\s+c\'?est\s+possible.*',
        r'.*merci\s+de\s+confirmer.*', r'pour\s+accord\s+piano', r'à\s+la\s+salle',
    ]
    data_patterns = [
        r'^(\d{1,2})[-/\s]*(\w{3,})$', r'(WP|TM|MS|SD|C5|SCL|ODM|5E|CL)', r'^\d{3}$',
        r'^(IC|AJ|Piano\s+Tech)$', r'(Steinway|Yamaha|Kawai|Bösendorfer|Fazioli|Baldwin|Mason)', r'\d{1,2}h',
    ]
    all_lines = email_text.split('\n')
    cleaned_lines = []
    signature_requester = extract_signature_requester(all_lines)
    for line in all_lines:
        line_stripped = line.strip()
        if not line_stripped:
            continue
        if any(re.match(p, line_stripped, re.IGNORECASE) for p in greeting_patterns):
            continue
        is_data_line = any(re.search(p, line_stripped, re.IGNORECASE) for p in data_patterns)
        has_piano_brand = bool(re.search(r'(Steinway|Yamaha|Kawai|Bösendorfer|Fazioli|Baldwin|Mason)', line_stripped, re.IGNORECASE))
        has_room_code = bool(re.search(r'(WP|TM|MS|SD|C5|SCL|ODM|5E|CL)', line_stripped, re.IGNORECASE))
        has_time_indicator = 'avant' in line_stripped.lower() or re.search(r'\d{1,2}h', line_stripped, re.IGNORECASE)
        if is_data_line or has_piano_brand or has_room_code or len(line_stripped) <= 100 or has_time_indicator:
            cleaned_lines.append(line_stripped)

    # Détection de début de bloc: date avec mois reconnu (FR/EN)
    months = r"(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|janv|f[eé]v|fev|avr|mai|juin|juil|aou|ao[uû]t|sept|oct|nov|d[eé]c|mars)"
    date_pattern = re.compile(rf'^(\d{{1,2}})[-/\s]+{months}\b', re.IGNORECASE)
    current_block_lines: List[str] = []
    for line in cleaned_lines:
        if date_pattern.search(line) and current_block_lines:
            block_text = '\n'.join(current_block_lines)
            parsed = parse_email_block(block_text, current_date)
            if parsed.get('date') and (parsed.get('room') or parsed.get('piano')):
                requests.append(parsed)
            current_block_lines = [line]
        else:
            current_block_lines.append(line)
    if current_block_lines:
        block_text = '\n'.join(current_block_lines)
        parsed = parse_email_block(block_text, current_date)
        if parsed.get('date') and (parsed.get('room') or parsed.get('piano')):
            requests.append(parsed)

    # Appliquer le demandeur global (signature) aux demandes sans demandeur
    if signature_requester:
        # Mapper Isabelle vers IC si c'est la signature
        signature_lower = signature_requester.lower().strip()
        requester_mapping = {
            'isabelle': 'IC',
            'isabelle clairoux': 'IC',
            'isabelle constantineau': 'IC',
            'clairoux': 'IC',
        }
        mapped_requester = signature_requester
        for name, code in requester_mapping.items():
            if name in signature_lower:
                mapped_requester = code
                break
        
        for req in requests:
            if not req.get('requester'):
                req['requester'] = mapped_requester
                req['confidence'] = min(req.get('confidence', 0.0) + 0.05, 1.0)

    return requests




