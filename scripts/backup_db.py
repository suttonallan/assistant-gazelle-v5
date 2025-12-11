#!/usr/bin/env python3
"""
Script de sauvegarde simple pour la base de données SQLite.

À exécuter périodiquement (via cron job sur Render ou manuellement).
"""

import os
import shutil
import sqlite3
from datetime import datetime
from core.db_utils import get_db_path


def backup_database():
    """Crée une sauvegarde de la base de données."""
    db_path = get_db_path()
    
    if not os.path.exists(db_path):
        print(f"❌ Base de données non trouvée: {db_path}")
        return
    
    # Créer le dossier de backup s'il n'existe pas
    backup_dir = os.path.join(os.path.dirname(db_path), 'backups')
    os.makedirs(backup_dir, exist_ok=True)
    
    # Nom du fichier de backup avec timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_filename = f"db_backup_{timestamp}.sqlite"
    backup_path = os.path.join(backup_dir, backup_filename)
    
    try:
        # Copie la base de données
        shutil.copy2(db_path, backup_path)
        print(f"✅ Backup créé: {backup_path}")
        
        # Garde seulement les 10 derniers backups
        backups = sorted([f for f in os.listdir(backup_dir) if f.startswith('db_backup_')])
        if len(backups) > 10:
            for old_backup in backups[:-10]:
                os.remove(os.path.join(backup_dir, old_backup))
                print(f"🗑️  Ancien backup supprimé: {old_backup}")
                
    except Exception as e:
        print(f"❌ Erreur lors du backup: {e}")


if __name__ == "__main__":
    backup_database()




