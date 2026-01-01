#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════════════╗
║                    CONFIGURATION CENTRALISÉE DES TECHNICIENS              ║
║                          SOURCE DE VÉRITÉ UNIQUE                          ║
╚═══════════════════════════════════════════════════════════════════════════╝

Ce fichier est la SEULE source de vérité pour toutes les informations des techniciens.
TOUS les autres fichiers Python doivent importer depuis ici.

⚠️ NE JAMAIS dupliquer ces informations ailleurs dans le code!
⚠️ TOUJOURS importer depuis ce fichier.

Utilisation:
    from config.techniciens_config import TECHNICIENS, get_technicien_by_id, get_technicien_by_email
"""

from typing import Dict, List, Optional

# ==========================================
# MAPPING COMPLET DES TECHNICIENS
# ==========================================

TECHNICIENS: Dict[str, Dict] = {
    "allan": {
        # Identifiants
        "gazelle_id": "usr_ofYggsCDt2JAVeNP",
        "supabase_id": "usr_ofYggsCDt2JAVeNP",

        # Informations personnelles
        "prenom": "Allan",
        "nom": "Sutton",
        "nom_complet": "Allan Sutton",
        "abbreviation": "Allan",
        "username": "allan",

        # Contact
        "email": "asutton@piano-tek.com",
        "slack": None,  # Réservé pour usage futur

        # Rôle et permissions
        "role": "admin",
        "is_admin": True,
        "is_technicien": True,
        "is_assistant": False
    },

    "nicolas": {
        # Identifiants
        "gazelle_id": "usr_HcCiFk7o0vZ9xAI0",
        "supabase_id": "usr_HcCiFk7o0vZ9xAI0",

        # Informations personnelles
        "prenom": "Nicolas",
        "nom": "Lessard",
        "nom_complet": "Nicolas Lessard",
        "abbreviation": "Nick",  # ⭐ IMPORTANT: Afficher "Nick" dans l'UI
        "username": "nicolas",

        # Contact
        "email": "nlessard@piano-tek.com",
        "slack": None,

        # Rôle et permissions
        "role": "technicien",
        "is_admin": False,
        "is_technicien": True,
        "is_assistant": False
    },

    "jeanphilippe": {
        # Identifiants
        "gazelle_id": "usr_ReUSmIJmBF86ilY1",
        "supabase_id": "usr_ReUSmIJmBF86ilY1",

        # Informations personnelles
        "prenom": "Jean-Philippe",
        "nom": "Reny",
        "nom_complet": "Jean-Philippe Reny",
        "abbreviation": "JP",
        "username": "jeanphilippe",

        # Contact
        "email": "jpreny@gmail.com",
        "slack": None,

        # Rôle et permissions
        "role": "technicien",
        "is_admin": False,
        "is_technicien": True,
        "is_assistant": False
    }
}

# ==========================================
# LISTES UTILITAIRES
# ==========================================

# Liste des techniciens
TECHNICIENS_LISTE: List[Dict] = list(TECHNICIENS.values())

# Liste des IDs Gazelle uniquement
GAZELLE_IDS: List[str] = [t["gazelle_id"] for t in TECHNICIENS_LISTE]

# Liste des emails uniquement
EMAILS: List[str] = [t["email"] for t in TECHNICIENS_LISTE]

# Liste des usernames uniquement
USERNAMES: List[str] = [t["username"] for t in TECHNICIENS_LISTE]

# Mapping ID Gazelle → Nom complet (pour compatibilité avec ancien code)
MAPPING_TECHNICIENS: Dict[str, str] = {
    t["gazelle_id"]: t["nom_complet"]
    for t in TECHNICIENS_LISTE
}

# ==========================================
# FONCTIONS UTILITAIRES
# ==========================================

def get_technicien_by_id(gazelle_id: str) -> Optional[Dict]:
    """
    Récupérer un technicien par son ID Gazelle.

    Args:
        gazelle_id: ID Gazelle (ex: "usr_HcCiFk7o0vZ9xAI0")

    Returns:
        Dict technicien ou None si non trouvé
    """
    for tech in TECHNICIENS_LISTE:
        if tech["gazelle_id"] == gazelle_id:
            return tech
    return None


def get_technicien_by_email(email: str) -> Optional[Dict]:
    """
    Récupérer un technicien par son email.

    Args:
        email: Email du technicien

    Returns:
        Dict technicien ou None si non trouvé
    """
    if not email:
        return None

    email_lower = email.lower()
    for tech in TECHNICIENS_LISTE:
        if tech["email"].lower() == email_lower:
            return tech
    return None


def get_technicien_by_username(username: str) -> Optional[Dict]:
    """
    Récupérer un technicien par son username.

    Args:
        username: Username (ex: "nicolas", "allan")

    Returns:
        Dict technicien ou None si non trouvé
    """
    if not username:
        return None

    username_lower = username.lower()
    for tech in TECHNICIENS_LISTE:
        if tech["username"].lower() == username_lower:
            return tech
    return None


def nom_vers_username(nom: str) -> Optional[str]:
    """
    Convertir un nom (Nicolas, Nick, etc.) vers le username normalisé.
    Gère les variations de noms et les alias.

    Args:
        nom: Nom ou alias (ex: "Nick", "Nicolas", "Allan")

    Returns:
        Username normalisé ou None
    """
    if not nom:
        return None

    nom_lower = nom.lower().strip()

    # Mapping des variations de noms
    variations = {
        "nicolas": "nicolas",
        "nick": "nicolas",
        "nicolas lessard": "nicolas",
        "n. lessard": "nicolas",

        "allan": "allan",
        "allan sutton": "allan",
        "a. sutton": "allan",

        "jean-philippe": "jeanphilippe",
        "jeanphilippe": "jeanphilippe",
        "jp": "jeanphilippe",
        "jean philippe": "jeanphilippe",
        "j-p reny": "jeanphilippe"
    }

    return variations.get(nom_lower)


def get_abbreviation(gazelle_id: str) -> str:
    """
    Obtenir l'abbréviation d'affichage (ex: "Nick" au lieu de "Nicolas").

    Args:
        gazelle_id: ID Gazelle

    Returns:
        Abbréviation pour affichage UI
    """
    tech = get_technicien_by_id(gazelle_id)
    if tech:
        return tech.get("abbreviation") or tech.get("prenom") or "Inconnu"
    return "Inconnu"


def is_valid_gazelle_id(gazelle_id: str) -> bool:
    """
    Vérifier si un ID Gazelle est valide.

    Args:
        gazelle_id: ID à vérifier

    Returns:
        True si l'ID existe
    """
    return gazelle_id in GAZELLE_IDS


def get_technicien_name(gazelle_id: str) -> Optional[str]:
    """
    Obtenir le prénom d'un technicien par son ID Gazelle.
    Pour compatibilité avec l'ancien code.

    Args:
        gazelle_id: ID Gazelle

    Returns:
        Prénom du technicien ou None
    """
    tech = get_technicien_by_id(gazelle_id)
    return tech["prenom"] if tech else None


# ==========================================
# VALIDATION AU CHARGEMENT
# ==========================================

def _validate_config():
    """Valider la configuration au chargement du module."""
    # Vérifier que tous les IDs Gazelle sont uniques
    if len(GAZELLE_IDS) != len(set(GAZELLE_IDS)):
        raise ValueError("❌ IDs Gazelle dupliqués détectés!")

    # Vérifier que tous les emails sont uniques
    if len(EMAILS) != len(set(EMAILS)):
        raise ValueError("❌ Emails dupliqués détectés!")

    # Vérifier que tous les usernames sont uniques
    if len(USERNAMES) != len(set(USERNAMES)):
        raise ValueError("❌ Usernames dupliqués détectés!")

    print("✅ Configuration des techniciens validée")


# Valider au chargement
_validate_config()


# ==========================================
# EXPORTS
# ==========================================

__all__ = [
    "TECHNICIENS",
    "TECHNICIENS_LISTE",
    "GAZELLE_IDS",
    "EMAILS",
    "USERNAMES",
    "MAPPING_TECHNICIENS",
    "get_technicien_by_id",
    "get_technicien_by_email",
    "get_technicien_by_username",
    "nom_vers_username",
    "get_abbreviation",
    "is_valid_gazelle_id",
    "get_technicien_name"
]
