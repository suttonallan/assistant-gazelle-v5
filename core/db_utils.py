#!/usr/bin/env python3
"""
Utilitaires pour la gestion de la base de données SQLite.

Gère automatiquement les chemins locaux vs production (Render).
"""

import os


def get_db_path(db_name: str = "db_test_v5.sqlite") -> str:
    """
    Retourne le chemin vers la base de données.
    
    En production (Render) : utilise le volume persistant
    En développement : utilise la racine du projet
    
    Args:
        db_name: Nom du fichier de base de données
        
    Returns:
        Chemin complet vers la base de données
    """
    # Vérifie si on est sur Render (volume persistant)
    render_persistent_disk = os.environ.get('RENDER_PERSISTENT_DISK_PATH')
    if render_persistent_disk:
        # Production : utilise le volume persistant
        return os.path.join(render_persistent_disk, db_name)
    
    # Développement : utilise la racine du projet
    # Remonte depuis core/ vers la racine
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    return os.path.join(project_root, db_name)


def ensure_db_directory(db_path: str) -> None:
    """
    S'assure que le répertoire de la base de données existe.
    
    Args:
        db_path: Chemin complet vers la base de données
    """
    db_dir = os.path.dirname(db_path)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)

