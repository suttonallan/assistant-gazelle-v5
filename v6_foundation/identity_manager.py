"""
Identity Manager v6 - Gestion centralisée des credentials Google.

Ce module:
- Charge les credentials depuis Supabase system_settings
- Crée des fichiers temporaires sécurisés pour satisfaire les API Google
- Gère le cycle de vie des fichiers temporaires
"""

import os
import json
import tempfile
from typing import Optional
from pathlib import Path

from core.supabase_storage import SupabaseStorage


class IdentityManager:
    """
    Gestionnaire d'identité pour les credentials Google Service Account.
    
    Charge les credentials depuis Supabase et crée des fichiers temporaires
    pour les API Google qui nécessitent un chemin de fichier.
    """
    
    CREDENTIALS_KEY = "GOOGLE_SHEETS_JSON"
    
    def __init__(self, storage: Optional[SupabaseStorage] = None):
        """
        Initialise le gestionnaire d'identité.
        
        Args:
            storage: Instance SupabaseStorage (optionnel, créée automatiquement si None)
        """
        self.storage = storage or SupabaseStorage(silent=True)
        self._temp_file: Optional[Path] = None
    
    def get_google_credentials_path(self) -> Optional[str]:
        """
        Retourne le chemin vers un fichier de credentials Google Service Account.
        
        Priorité:
        1. Supabase system_settings (clé GOOGLE_SHEETS_JSON)
        2. Variable d'environnement GOOGLE_APPLICATION_CREDENTIALS (fallback)
        
        Returns:
            Chemin vers le fichier de credentials, ou None si introuvable
            
        Raises:
            FileNotFoundError: Si aucun credentials n'est trouvé
        """
        # 1. Essayer Supabase en premier (v6)
        try:
            credentials_data = self.storage.get_system_setting(self.CREDENTIALS_KEY)
            if credentials_data:
                # Créer un fichier temporaire
                temp_file = self._create_temp_credentials_file(credentials_data)
                if temp_file:
                    self._temp_file = temp_file
                    print(f"✅ Credentials Google chargés depuis Supabase (v6)")
                    return str(temp_file)
        except Exception as e:
            print(f"⚠️  Impossible de charger depuis Supabase: {e}")
            # Continue avec le fallback
        
        # 2. Fallback: Variable d'environnement (v5)
        env_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        if env_path and os.path.exists(env_path):
            print(f"✅ Credentials Google chargés depuis GOOGLE_APPLICATION_CREDENTIALS (v5 fallback)")
            return env_path
        
        # 3. Aucun credentials trouvé
        raise FileNotFoundError(
            f"Credentials Google introuvables. "
            f"Vérifiez Supabase system_settings['{self.CREDENTIALS_KEY}'] "
            f"ou la variable d'environnement GOOGLE_APPLICATION_CREDENTIALS"
        )
    
    def _create_temp_credentials_file(self, credentials_data: dict) -> Optional[Path]:
        """
        Crée un fichier temporaire avec les credentials Google.
        
        Args:
            credentials_data: Dictionnaire contenant les credentials JSON
            
        Returns:
            Path vers le fichier temporaire créé
        """
        try:
            # Créer un fichier temporaire sécurisé (supprimé automatiquement à la fermeture)
            # mode='w' pour écriture texte, delete=False pour garder le fichier ouvert
            temp_fd, temp_path = tempfile.mkstemp(
                suffix='.json',
                prefix='google_credentials_',
                text=True
            )
            
            try:
                # Écrire les credentials JSON dans le fichier temporaire
                with os.fdopen(temp_fd, 'w') as f:
                    json.dump(credentials_data, f, indent=2)
                
                # Convertir en Path pour faciliter la manipulation
                temp_file_path = Path(temp_path)
                
                # Vérifier que le fichier a été créé correctement
                if not temp_file_path.exists():
                    raise FileNotFoundError(f"Fichier temporaire non créé: {temp_path}")
                
                # Vérifier que c'est bien un JSON valide de service account
                with open(temp_file_path, 'r') as f:
                    loaded_data = json.load(f)
                    if loaded_data.get("type") != "service_account":
                        print(f"⚠️  Attention: Type '{loaded_data.get('type')}' au lieu de 'service_account'")
                
                return temp_file_path
                
            except Exception as e:
                # Nettoyer en cas d'erreur
                try:
                    os.unlink(temp_path)
                except:
                    pass
                raise e
                
        except Exception as e:
            print(f"❌ Erreur lors de la création du fichier temporaire: {e}")
            return None
    
    def cleanup(self):
        """
        Nettoie le fichier temporaire créé (appelé à la fin de l'utilisation).
        
        Note: Les fichiers temporaires créés avec mkstemp sont normalement
        supprimés automatiquement, mais cette méthode permet un nettoyage explicite.
        """
        if self._temp_file and self._temp_file.exists():
            try:
                self._temp_file.unlink()
                print(f"🧹 Fichier temporaire supprimé: {self._temp_file}")
            except Exception as e:
                print(f"⚠️  Impossible de supprimer le fichier temporaire: {e}")
            finally:
                self._temp_file = None
    
    def __enter__(self):
        """Support pour context manager (with statement)."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Nettoyage automatique à la sortie du context manager."""
        self.cleanup()
