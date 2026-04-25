"""
Détection d'intention pour les actions de soumission.

Approche MVP : regex + heuristiques. Si ambigu, on retourne UNKNOWN
et on demande au user de reformuler.

Pas d'appel LLM coûteux pour cette étape — on veut des patterns déterministes.
"""
import re
from typing import Dict, Optional


# Mots-clés qui déclenchent une intention "créer soumission"
CREATE_KEYWORDS = (
    r"\b(fais|fait|cr[ée]e?[rz]?|nouvelle?|pr[ée]pare[rz]?|monte[rz]?|construis)\b"
    r".+\b(soumission|estimate|estim[ée])\b"
)

# Mots-clés qui déclenchent une intention "améliorer soumission"
IMPROVE_KEYWORDS = (
    r"\b(am[ée]liore[rz]?|refais|refait|corrige[rz]?|reconstruis|revoir|revois)\b"
    r".+\b(soumission|estimate|estim[ée])\b"
)

# Patterns pour extraire le numéro de soumission
ESTIMATE_NUMBER = re.compile(r"#(\d{4,6})|n[°o]\s*(\d{4,6})|num[ée]ro\s*(\d{4,6})|(\b\d{5}\b)")

# Patterns pour bundles connus (extensible)
BUNDLE_PATTERNS = {
    'marteaux': r"\b(marteaux?|hammers?)\b",
    'cordes_basses': r"\b(cordes?\s+(de\s+)?basses?|bass\s+strings?)\b",
    'mortaises': r"\b(mortaises?|key\s+bushings?)\b",
    'grand_entretien': r"\b(grand\s+entretien|major\s+maintenance)\b",
    'pls_install': r"\b(pls|piano\s+life\s+saver|syst[èe]me\s+d['\u2019]?humidit[ée])\b",
    'adsilent': r"\b(adsilent|silencieux|silent)\b",
}


def detect_intent(text: str) -> Dict:
    """
    Analyse le texte du user et retourne :
        {
            'intent': 'create' | 'improve' | 'unknown',
            'estimate_number': int | None,
            'bundles': list[str],          # pour create
            'client_hint': str | None,     # nom client extrait
            'raw_text': str,
        }
    """
    if not text:
        return {'intent': 'unknown', 'raw_text': text or ''}

    text_lc = text.lower()
    result = {
        'intent': 'unknown',
        'estimate_number': None,
        'bundles': [],
        'client_hint': None,
        'raw_text': text,
    }

    # Extraire le numéro de soumission s'il y en a un
    m = ESTIMATE_NUMBER.search(text)
    if m:
        for g in m.groups():
            if g:
                result['estimate_number'] = int(g)
                break

    # Detection : create vs improve
    if re.search(IMPROVE_KEYWORDS, text_lc):
        result['intent'] = 'improve'
    elif re.search(CREATE_KEYWORDS, text_lc):
        result['intent'] = 'create'
    elif result['estimate_number']:
        # Numéro fourni mais pas de verbe clair → assume improve
        result['intent'] = 'improve'

    # Détection des bundles (pour create)
    if result['intent'] == 'create':
        for code, pattern in BUNDLE_PATTERNS.items():
            if re.search(pattern, text_lc):
                result['bundles'].append(code)

    # Extraire un hint de nom client (mots après "pour")
    # Strip optional title prefix (case-insensitive)
    m = re.search(
        r"\bpour\s+(?:(?:m\.|mme\.?|mlle\.?|monsieur|madame|mademoiselle)\s+)?"
        r"([A-ZÀ-Ÿ][\w\-']+(?:\s+[A-ZÀ-Ÿ][\w\-']+){0,2})",
        text,
        re.IGNORECASE,
    )
    if m:
        result['client_hint'] = m.group(1).strip()

    return result
