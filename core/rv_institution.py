"""Règle unique : un RV est-il rattaché à une institution ?

Utilisée par la synchro (avis de création/annulation) et par l'assistant
(RV d'accompagnement). Un RV PERSONNEL rattaché à une institution (Place des
Arts, Vincent-d'Indy, Orford…) compte comme un RV client.
"""

INSTITUTION_KEYWORDS = [
    'vincent-d\'indy', 'vincent d\'indy', 'vd ', ' vd', 'v-d',
    'place des arts', 'pda',
    'grands ballets', 'gnb',
    'orford',
    'uqam', 'pierre-péladeau',
    'cmm',  # Conservatoire de musique de Montréal
    'osm', 'orchestre symphonique',
]


def is_institution_appointment(title: str, location: str, description: str) -> bool:
    """Vérifie si un RV est lié à une institution (mots-clés dans titre/lieu/notes)."""
    text_to_check = f"{title or ''} {location or ''} {description or ''}".lower()
    return any(keyword in text_to_check for keyword in INSTITUTION_KEYWORDS)
