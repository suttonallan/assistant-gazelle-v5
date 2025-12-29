"""
Mapping géographique Montréal & Région.

Transforme les codes postaux en noms de quartiers lisibles.
Priorise les zones denses et fréquemment visitées.
"""

# Mapping code postal (3 premiers caractères) → Quartier
MTL_POSTAL_TO_NEIGHBORHOOD = {
    # ============================================================
    # MONTRÉAL CENTRAL & PLATEAU
    # ============================================================
    'H2W': 'Plateau Mont-Royal',
    'H2J': 'Plateau Mont-Royal',
    'H2T': 'Plateau Mont-Royal',
    'H2H': 'Plateau (Est)',
    'H2X': 'McGill / Place-des-Arts',
    'H2L': 'Centre-Sud',

    # ============================================================
    # NORD & ROSEMONT
    # ============================================================
    'H2R': 'Villeray',
    'H2S': 'Petite-Patrie',
    'H2G': 'Rosemont',
    'H1Y': 'Rosemont (Est)',
    'H2E': 'Villeray (Nord)',
    'H2P': 'Villeray (Parc-Jarry)',

    # ============================================================
    # OUEST & SUD-OUEST
    # ============================================================
    'H3Y': 'Westmount',
    'H3Z': 'Westmount',
    'H4C': 'Saint-Henri',
    'H3J': 'Petite-Bourgogne',
    'H4E': 'Verdun / Ville Émard',
    'H3K': 'Pointe-Saint-Charles',
    'H3H': 'Downtown / Shaughnessy',

    # ============================================================
    # OUTREMONT & CÔTE-DES-NEIGES
    # ============================================================
    'H2V': 'Outremont',
    'H3P': 'Mont-Royal (TMR)',
    'H3S': 'Côte-des-Neiges',
    'H3T': 'Côte-des-Neiges (Ouest)',

    # ============================================================
    # HOCHELAGA & EST
    # ============================================================
    'H1W': 'Hochelaga',
    'H1V': 'Maisonneuve',
    'H1N': 'Mercier',
    'H1M': 'Anjou',

    # ============================================================
    # NDG & OUEST-DE-L'ÎLE
    # ============================================================
    'H4A': 'NDG (Sherbrooke)',
    'H4B': 'NDG (Ouest)',
    'H3N': 'NDG (Monkland)',
    'H9A': 'Pointe-Claire',
    'H9B': 'Beaconsfield',
    'H9H': 'Kirkland',

    # ============================================================
    # LAVAL
    # ============================================================
    'H7N': 'Laval (Pont-Viau)',
    'H7V': 'Laval (Chomedey)',
    'H7W': 'Laval (Sainte-Rose)',
    'H7X': 'Laval (Vimont)',
    'H7Y': 'Laval (Auteuil)',
    'H7E': 'Laval (Duvernay)',

    # ============================================================
    # RIVE-SUD (LONGUEUIL & ENVIRONS)
    # ============================================================
    'J4J': 'Longueuil',
    'J4K': 'Longueuil',
    'J4L': 'Longueuil',
    'J4M': 'Longueuil (Saint-Hubert)',
    'J4N': 'Longueuil (Saint-Hubert)',
    'J3Y': 'Saint-Hubert',
    'J4B': 'Boucherville',
    'J4G': 'Greenfield Park',
    'J4H': 'Greenfield Park',

    # ============================================================
    # RIVE-SUD (AUTRES)
    # ============================================================
    'J4W': 'Brossard',
    'J4X': 'Brossard',
    'J4Y': 'Brossard',
    'J4Z': 'Brossard',
    'J5A': 'Saint-Lambert',
    'J3V': 'Saint-Bruno',

    # ============================================================
    # RIVE-NORD
    # ============================================================
    'J7H': 'Blainville',
    'J7C': 'Rosemère',
    'J7A': 'Repentigny',
    'J6A': 'Terrebonne',
    'J6W': 'Terrebonne (Lachenaie)',
    'J7J': 'Saint-Eustache',
    'J7R': 'Boisbriand',

    # ============================================================
    # AUTRES ZONES FRÉQUENTES
    # ============================================================
    'H1K': 'Montréal-Nord',
    'H1H': 'Rivière-des-Prairies',
    'H1G': 'Pointe-aux-Trembles',
    'H8R': 'LaSalle',
    'H8N': 'LaSalle',
    'H8P': 'LaSalle',
    'H9K': 'Dollard-des-Ormeaux',
    'H9J': 'Pierrefonds',
}


def get_neighborhood_from_postal_code(postal_code: str, fallback_city: str = None) -> str:
    """
    Extrait le quartier à partir d'un code postal.

    Args:
        postal_code: Code postal complet (ex: "H2G 2J8")
        fallback_city: Ville à utiliser si le code postal n'est pas dans le mapping

    Returns:
        Nom du quartier ou ville

    Examples:
        >>> get_neighborhood_from_postal_code("H2G 2J8")
        'Rosemont'

        >>> get_neighborhood_from_postal_code("J9Z 1A1", "Sainte-Thérèse")
        'Sainte-Thérèse'

        >>> get_neighborhood_from_postal_code("", "Montréal")
        'Montréal'
    """
    if not postal_code:
        return fallback_city or ""

    # Nettoyer: garder les 3 premiers caractères alphanumériques en majuscules
    cleaned = ''.join(c.upper() for c in postal_code if c.isalnum())[:3]

    if not cleaned:
        return fallback_city or ""

    # Lookup dans le mapping
    neighborhood = MTL_POSTAL_TO_NEIGHBORHOOD.get(cleaned)

    if neighborhood:
        return neighborhood

    # Fallback: utiliser la ville fournie
    return fallback_city or cleaned


def format_neighborhood_display(postal_code: str, city: str = None) -> str:
    """
    Formate l'affichage du quartier avec le code postal entre parenthèses.

    Args:
        postal_code: Code postal complet
        city: Ville (utilisé en fallback)

    Returns:
        Format: "Quartier (H2G)" ou "Ville"

    Examples:
        >>> format_neighborhood_display("H2G 2J8", "Montréal")
        'Rosemont (H2G)'

        >>> format_neighborhood_display("J9Z 1A1", "Sainte-Thérèse")
        'Sainte-Thérèse'
    """
    neighborhood = get_neighborhood_from_postal_code(postal_code, city)

    if not neighborhood:
        return ""

    # Si on a trouvé un mapping, ajouter le code postal entre parenthèses
    if postal_code:
        cleaned_code = ''.join(c.upper() for c in postal_code if c.isalnum())[:3]
        if cleaned_code in MTL_POSTAL_TO_NEIGHBORHOOD:
            return f"{neighborhood} ({cleaned_code})"

    # Sinon, juste le nom de la ville
    return neighborhood


# Export public
__all__ = [
    'MTL_POSTAL_TO_NEIGHBORHOOD',
    'get_neighborhood_from_postal_code',
    'format_neighborhood_display',
]
