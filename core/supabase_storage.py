#!/usr/bin/env python3
"""
Utilitaires pour stocker les modifications des pianos dans Supabase.

Plus rapide, fiable et scalable que GitHub Gist.
"""

import os
from typing import Dict, List, Any, Optional
from datetime import datetime
import requests


class SupabaseStorage:
    """Gère le stockage des modifications de pianos dans Supabase."""
    
    def __init__(self, supabase_url: Optional[str] = None, supabase_key: Optional[str] = None):
        """
        Initialise le stockage Supabase.
        
        Args:
            supabase_url: URL du projet Supabase (si None, utilise SUPABASE_URL de l'environnement)
            supabase_key: Clé API Supabase (si None, utilise SUPABASE_KEY de l'environnement)
        """
        self.supabase_url = supabase_url or os.environ.get('SUPABASE_URL')
        self.supabase_key = supabase_key or os.environ.get('SUPABASE_KEY')
        
        if not self.supabase_url or not self.supabase_key:
            raise ValueError(
                "SUPABASE_URL et SUPABASE_KEY requis. "
                "Ajoutez-les dans les variables d'environnement."
            )
        
        self.api_url = f"{self.supabase_url}/rest/v1"
        self.table = "vincent_dindy_piano_updates"
    
    def _get_headers(self) -> Dict[str, str]:
        """Retourne les headers pour les requêtes Supabase API."""
        return {
            "apikey": self.supabase_key,
            "Authorization": f"Bearer {self.supabase_key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation"
        }
    
    def get_piano_updates(self, piano_id: str) -> Optional[Dict[str, Any]]:
        """
        Récupère les modifications d'un piano depuis Supabase.
        
        Args:
            piano_id: ID du piano
            
        Returns:
            Dictionnaire des modifications ou None si aucune
        """
        try:
            url = f"{self.api_url}/{self.table}?piano_id=eq.{piano_id}&select=*"
            response = requests.get(url, headers=self._get_headers())
            
            if response.status_code == 200:
                data = response.json()
                if data:
                    # Retourner la modification la plus récente
                    return data[0]
            
            return None
            
        except Exception as e:
            print(f"⚠️ Erreur lors de la récupération du piano {piano_id}: {e}")
            return None
    
    def get_all_piano_updates(self) -> Dict[str, Dict[str, Any]]:
        """
        Récupère toutes les modifications de pianos depuis Supabase.
        
        Returns:
            Dictionnaire {piano_id: modifications}
        """
        try:
            url = f"{self.api_url}/{self.table}?select=*"
            response = requests.get(url, headers=self._get_headers())
            
            if response.status_code == 200:
                data = response.json()
                # Convertir en dictionnaire avec piano_id comme clé
                return {
                    item['piano_id']: item
                    for item in data
                }
            
            return {}
            
        except Exception as e:
            print(f"⚠️ Erreur lors de la récupération des pianos: {e}")
            return {}
    
    def update_piano(self, piano_id: str, updates: Dict[str, Any]) -> bool:
        """
        Sauvegarde les modifications d'un piano dans Supabase en utilisant UPSERT.
        Une seule requête au lieu de 2 (GET + PATCH/POST).

        Args:
            piano_id: ID du piano
            updates: Dictionnaire des champs à mettre à jour

        Returns:
            True si mis à jour avec succès
        """
        try:
            data = {
                "piano_id": piano_id,
                **updates,
                "updated_at": datetime.now().isoformat()
            }

            # UPSERT : insère si n'existe pas, met à jour sinon
            # Header special pour UPSERT : resolution=merge-duplicates
            headers = self._get_headers()
            headers["Prefer"] = "resolution=merge-duplicates"

            url = f"{self.api_url}/{self.table}"
            response = requests.post(url, headers=headers, json=data)

            if response.status_code in [200, 201]:
                print(f"✅ Piano {piano_id} sauvegardé dans Supabase (UPSERT)")
                return True
            else:
                print(f"❌ Erreur Supabase {response.status_code}: {response.text}")
                return False

        except Exception as e:
            print(f"⚠️ Erreur lors de la mise à jour du piano {piano_id}: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def batch_update_pianos(self, updates: List[Dict[str, Any]]) -> bool:
        """
        Met à jour plusieurs pianos en une seule requête (batch UPSERT).
        Beaucoup plus rapide que plusieurs appels individuels.

        Args:
            updates: Liste de dictionnaires contenant piano_id et les champs à mettre à jour
                     Ex: [{"piano_id": "A-001", "status": "top"}, ...]

        Returns:
            True si tous mis à jour avec succès
        """
        try:
            if not updates:
                return True

            # Ajouter updated_at à chaque entrée
            data = [
                {
                    **update,
                    "updated_at": datetime.now().isoformat()
                }
                for update in updates
            ]

            # UPSERT batch
            headers = self._get_headers()
            headers["Prefer"] = "resolution=merge-duplicates"

            url = f"{self.api_url}/{self.table}"
            response = requests.post(url, headers=headers, json=data)

            if response.status_code in [200, 201]:
                print(f"✅ {len(updates)} pianos sauvegardés dans Supabase (batch UPSERT)")
                return True
            else:
                print(f"❌ Erreur Supabase batch {response.status_code}: {response.text}")
                return False

        except Exception as e:
            print(f"⚠️ Erreur lors du batch update: {e}")
            import traceback
            traceback.print_exc()
            return False

    def delete_piano_updates(self, piano_id: str) -> bool:
        """
        Supprime les modifications d'un piano.

        Args:
            piano_id: ID du piano

        Returns:
            True si supprimé avec succès
        """
        try:
            url = f"{self.api_url}/{self.table}?piano_id=eq.{piano_id}"
            response = requests.delete(url, headers=self._get_headers())

            return response.status_code == 204

        except Exception as e:
            print(f"⚠️ Erreur lors de la suppression du piano {piano_id}: {e}")
            return False

