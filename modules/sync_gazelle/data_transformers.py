#!/usr/bin/env python3
"""
Module de transformation des données pour la synchronisation Gazelle → Supabase.

Reproduit la logique de l'ancien système PC pour garantir la compatibilité
des données importées.

Fonctions:
- clean_price: Sanitisation robuste des prix (remplace ! par 1, supprime $, etc.)
- normalize_technician_name: Supprime les tirets des noms de techniciens
- clean_client_name: Nettoie les noms de clients (supprime ", son historique", etc.)
- parse_flexible_date: Parsing flexible des dates (français/anglais, avec/sans année)
"""

import re
from typing import Optional, Union
from datetime import datetime


def clean_price(value: Union[str, int, float, None]) -> Optional[float]:
    """
    Sanitise un prix selon la logique de l'ancien système PC.
    
    Règles:
    1. Remplace ! par 1 (cas spécial !00$)
    2. Supprime les espaces
    3. Supprime les $
    4. Remplace les , par des .
    5. Convertit en float pour Supabase
    
    Args:
        value: Valeur à nettoyer (peut être string, int, float, ou None)
    
    Returns:
        float ou None si la valeur ne peut pas être convertie
    
    Examples:
        >>> clean_price("!00$")
        100.0
        >>> clean_price("1,234.56$")
        1234.56
        >>> clean_price(" 100 $ ")
        100.0
        >>> clean_price("abc")
        None
    """
    if value is None:
        return None
    
    # Convertir en string pour traitement
    price_str = str(value).strip()
    
    if not price_str:
        return None
    
    # 1. Remplace ! par 1 (cas spécial !00$)
    price_str = price_str.replace('!', '1')
    
    # 2. Supprime les espaces
    price_str = price_str.replace(' ', '')
    
    # 3. Supprime les $
    price_str = price_str.replace('$', '')
    
    # 4. Gérer les virgules et points décimaux intelligemment
    # Si on a un point ET une virgule, la virgule est probablement un séparateur de milliers
    # Sinon, remplacer les virgules par des points
    if '.' in price_str and ',' in price_str:
        # Format: "1,234.56" ou "1.234,56"
        # Si le dernier séparateur est un point, la virgule est un séparateur de milliers
        if price_str.rindex('.') > price_str.rindex(','):
            # Format "1,234.56" -> enlever la virgule
            price_str = price_str.replace(',', '')
        else:
            # Format "1.234,56" -> remplacer point par rien, virgule par point
            price_str = price_str.replace('.', '').replace(',', '.')
    else:
        # Pas de point décimal, remplacer virgule par point
        price_str = price_str.replace(',', '.')
    
    # 5. Convertit en float
    try:
        return float(price_str)
    except (ValueError, TypeError):
        return None


def normalize_technician_name(name: Optional[str]) -> Optional[str]:
    """
    Normalise un nom de technicien en supprimant les tirets.
    
    Cette fonction permet de faire correspondre les noms aux usernames
    qui n'ont pas de tirets.
    
    Args:
        name: Nom du technicien (ex: "jean-philippe")
    
    Returns:
        Nom normalisé (ex: "jeanphilippe") ou None si name est None/vide
    
    Examples:
        >>> normalize_technician_name("jean-philippe")
        'jeanphilippe'
        >>> normalize_technician_name("Marie-Claire")
        'MarieClaire'
        >>> normalize_technician_name(None)
        None
    """
    if not name:
        return None
    
    # Supprime tous les tirets
    return name.replace('-', '')


def clean_client_name(name: Optional[str]) -> Optional[str]:
    """
    Nettoie un nom de client en supprimant les chaînes polluantes.
    
    Supprime notamment ", son historique" et autres suffixes indésirables
    qui polluent les noms de clients.
    
    Args:
        name: Nom du client à nettoyer
    
    Returns:
        Nom nettoyé ou None si name est None/vide
    
    Examples:
        >>> clean_client_name("Client ABC, son historique")
        'Client ABC'
        >>> clean_client_name("Entreprise XYZ")
        'Entreprise XYZ'
        >>> clean_client_name(None)
        None
    """
    if not name:
        return None
    
    # Supprime ", son historique" et variations
    # Pattern flexible pour capturer différentes variations
    patterns = [
        r',\s*son\s+historique.*$',
        r',\s*historique.*$',
        r'\s*,\s*son\s+.*$',  # Plus général pour ", son ..."
    ]
    
    cleaned = name
    for pattern in patterns:
        cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
    
    # Nettoie les espaces en fin
    return cleaned.strip()


def parse_flexible_date(
    date_str: Optional[str],
    default_year: Optional[int] = None
) -> Optional[str]:
    """
    Parse une date de manière flexible (français/anglais, avec/sans année).
    
    Reproduit la logique de l'ancien place_des_arts_parser.py pour gérer
    les dates dans différents formats.
    
    Formats supportés:
    - "15 janvier 2024" (français avec année)
    - "15 janvier" (français sans année, utilise default_year)
    - "January 15, 2024" (anglais avec année)
    - "January 15" (anglais sans année, utilise default_year)
    - "2024-01-15" (ISO)
    - "15/01/2024" (format court)
    
    Args:
        date_str: Chaîne de date à parser
        default_year: Année par défaut si absente (défaut: année actuelle)
    
    Returns:
        Date au format ISO (YYYY-MM-DD) ou None si parsing échoue
    
    Examples:
        >>> parse_flexible_date("15 janvier 2024")
        '2024-01-15'
        >>> parse_flexible_date("15 janvier", default_year=2024)
        '2024-01-15'
        >>> parse_flexible_date("January 15, 2024")
        '2024-01-15'
    """
    if not date_str:
        return None
    
    date_str = date_str.strip()
    
    if not date_str:
        return None
    
    # Si default_year n'est pas fourni, utiliser l'année actuelle
    if default_year is None:
        default_year = datetime.now().year
    
    # Mapping des mois en français
    mois_fr = {
        'janvier': 1, 'février': 2, 'fevrier': 2, 'mars': 3,
        'avril': 4, 'mai': 5, 'juin': 6,
        'juillet': 7, 'août': 8, 'aout': 8, 'septembre': 9,
        'octobre': 10, 'novembre': 11, 'décembre': 12, 'decembre': 12
    }
    
    # Mapping des mois en anglais
    mois_en = {
        'january': 1, 'february': 2, 'march': 3, 'april': 4,
        'may': 5, 'june': 6, 'july': 7, 'august': 8,
        'september': 9, 'october': 10, 'november': 11, 'december': 12
    }
    
    # Essayer format ISO d'abord
    try:
        dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        return dt.date().isoformat()
    except:
        pass
    
    # Essayer format court DD/MM/YYYY ou MM/DD/YYYY
    try:
        parts = date_str.split('/')
        if len(parts) == 3:
            # Essayer DD/MM/YYYY (format français)
            day, month, year = map(int, parts)
            dt = datetime(year, month, day)
            return dt.date().isoformat()
    except:
        pass
    
    # Essayer format français: "15 janvier 2024" ou "15 janvier"
    for mois, num_mois in mois_fr.items():
        pattern = rf'(\d+)\s+{mois}(?:\s+(\d{{4}}))?'
        match = re.search(pattern, date_str, re.IGNORECASE)
        if match:
            jour = int(match.group(1))
            annee_str = match.group(2)
            annee = int(annee_str) if annee_str else default_year
            try:
                dt = datetime(annee, num_mois, jour)
                return dt.date().isoformat()
            except ValueError:
                continue
    
    # Essayer format anglais: "January 15, 2024" ou "January 15"
    for mois, num_mois in mois_en.items():
        # Format "Month Day, Year" ou "Month Day"
        pattern = rf'{mois}\s+(\d+)(?:,\s+(\d{{4}}))?'
        match = re.search(pattern, date_str, re.IGNORECASE)
        if match:
            jour = int(match.group(1))
            annee_str = match.group(2)
            annee = int(annee_str) if annee_str else default_year
            try:
                dt = datetime(annee, num_mois, jour)
                return dt.date().isoformat()
            except ValueError:
                continue
    
    # Si aucun format ne correspond, retourner None
    return None

