#!/usr/bin/env python3
"""
Gestionnaire de référence - Consulte et met à jour docs/REFERENCE_COMPLETE.md automatiquement.

Utilisation:
    from core.reference_manager import ReferenceManager
    
    ref = ReferenceManager()
    
    # Consulter le mapping des techniciens
    technicien_nom = ref.get_technicien_name("usr_xxx")
    
    # Consulter les colonnes valides
    colonnes = ref.get_valid_columns("produits_catalogue")
    
    # Mettre à jour après un succès
    ref.update_after_success("technicien_mapping", {"usr_new": "Nouveau Technicien"})
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Any
import json

REFERENCE_FILE = Path(__file__).parent.parent / "docs" / "REFERENCE_COMPLETE.md"
CACHE_FILE = Path(__file__).parent.parent / ".reference_cache.json"


class ReferenceManager:
    """Gère la consultation et la mise à jour du document de référence."""
    
    def __init__(self):
        """Initialise le gestionnaire de référence."""
        self.reference_path = REFERENCE_FILE
        self.cache_path = CACHE_FILE
        self._cache = self._load_cache()
        self._reference_content = None
    
    def _load_cache(self) -> Dict[str, Any]:
        """Charge le cache depuis le fichier JSON."""
        if self.cache_path.exists():
            try:
                with open(self.cache_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def _save_cache(self):
        """Sauvegarde le cache dans le fichier JSON."""
        try:
            with open(self.cache_path, 'w', encoding='utf-8') as f:
                json.dump(self._cache, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"⚠️  Erreur sauvegarde cache: {e}")
    
    def _load_reference(self) -> str:
        """Charge le contenu du document de référence."""
        if self._reference_content is None:
            if self.reference_path.exists():
                with open(self.reference_path, 'r', encoding='utf-8') as f:
                    self._reference_content = f.read()
            else:
                raise FileNotFoundError(f"Document de référence non trouvé: {self.reference_path}")
        return self._reference_content
    
    def get_technicien_name(self, technicien_id: str) -> Optional[str]:
        """
        Récupère le nom d'un technicien depuis son ID Supabase.
        
        Args:
            technicien_id: ID Supabase (ex: "usr_xxx")
            
        Returns:
            Nom du technicien ou None si non trouvé
        """
        # Vérifier le cache d'abord
        cache_key = f"technicien_{technicien_id}"
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        # Charger depuis la référence
        content = self._load_reference()
        
        # Extraire le mapping depuis la section
        pattern = r"```python\s+TECHNICIENS_MAPPING\s*=\s*\{([^}]+)\}\s*```"
        match = re.search(pattern, content, re.DOTALL)
        
        if match:
            mapping_text = match.group(1)
            # Parser le mapping
            for line in mapping_text.split('\n'):
                if f"'{technicien_id}'" in line or f'"{technicien_id}"' in line:
                    # Extraire le nom
                    name_match = re.search(r"'name':\s*'([^']+)'", line)
                    if name_match:
                        name = name_match.group(1)
                        # Mettre en cache
                        self._cache[cache_key] = name
                        self._save_cache()
                        return name
        
        # Si pas trouvé, chercher dans README.md
        readme_path = Path(__file__).parent.parent / "README.md"
        if readme_path.exists():
            with open(readme_path, 'r', encoding='utf-8') as f:
                readme_content = f.read()
                pattern = rf"'{technicien_id}':\s*{{[^}}]*'name':\s*'([^']+)'"
                match = re.search(pattern, readme_content)
                if match:
                    name = match.group(1)
                    self._cache[cache_key] = name
                    self._save_cache()
                    return name
        
        return None
    
    def get_valid_columns(self, table_name: str) -> List[str]:
        """
        Récupère la liste des colonnes valides pour une table.
        
        Args:
            table_name: Nom de la table (ex: "produits_catalogue")
            
        Returns:
            Liste des colonnes valides
        """
        cache_key = f"columns_{table_name}"
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        content = self._load_reference()
        columns = []
        
        # Chercher la section de la table
        pattern = rf"### Table: `{table_name}`(.*?)(?=###|##|$)"
        match = re.search(pattern, content, re.DOTALL)
        
        if match:
            table_section = match.group(1)
            # Extraire les colonnes depuis les blocs SQL
            column_pattern = r"(\w+)\s+\w+(?:\([^)]+\))?(?:\s+[^,\n]+)?,?\s*--.*"
            for line in table_section.split('\n'):
                if 'TEXT' in line or 'INTEGER' in line or 'DECIMAL' in line or 'BOOLEAN' in line or 'TIMESTAMPTZ' in line:
                    col_match = re.match(r"(\w+)\s+", line.strip())
                    if col_match:
                        col_name = col_match.group(1)
                        if col_name not in ['CREATE', 'ALTER', 'PRIMARY', 'UNIQUE', 'INDEX', 'IF', 'NOT', 'DEFAULT']:
                            columns.append(col_name)
        
        # Mettre en cache
        self._cache[cache_key] = columns
        self._save_cache()
        return columns
    
    def validate_column(self, table_name: str, column_name: str) -> bool:
        """
        Valide qu'une colonne existe pour une table.
        
        Args:
            table_name: Nom de la table
            column_name: Nom de la colonne
            
        Returns:
            True si la colonne est valide
        """
        valid_columns = self.get_valid_columns(table_name)
        return column_name in valid_columns
    
    def update_after_success(self, update_type: str, data: Dict[str, Any]):
        """
        Met à jour la référence après un succès.
        
        Args:
            update_type: Type de mise à jour ("technicien_mapping", "column_info", etc.)
            data: Données à ajouter/mettre à jour
        """
        if update_type == "technicien_mapping":
            # Mettre à jour le cache
            for tech_id, tech_name in data.items():
                cache_key = f"technicien_{tech_id}"
                self._cache[cache_key] = tech_name
            
            # Mettre à jour le fichier de référence
            self._update_reference_techniciens(data)
        
        elif update_type == "column_info":
            # Mettre à jour les informations sur les colonnes
            table_name = data.get("table_name")
            if table_name:
                cache_key = f"columns_{table_name}"
                self._cache[cache_key] = data.get("columns", [])
        
        self._save_cache()
    
    def _update_reference_techniciens(self, new_mappings: Dict[str, str]):
        """Met à jour la section des techniciens dans la référence."""
        content = self._load_reference()
        
        # Trouver la section des techniciens
        pattern = r"(```python\s+TECHNICIENS_MAPPING\s*=\s*\{)([^}]+)(\}\s*```)"
        match = re.search(pattern, content, re.DOTALL)
        
        if match:
            # Ajouter les nouveaux mappings
            existing_mappings = match.group(2)
            new_lines = []
            for tech_id, tech_name in new_mappings.items():
                if tech_id not in existing_mappings:
                    new_lines.append(f"    '{tech_id}': '{tech_name}',  # Ajouté automatiquement")
            
            if new_lines:
                updated_mappings = existing_mappings.rstrip() + "\n" + "\n".join(new_lines) + "\n"
                new_content = content[:match.start()] + match.group(1) + updated_mappings + match.group(3) + content[match.end():]
                
                # Sauvegarder
                with open(self.reference_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                self._reference_content = new_content
                print(f"✅ Référence mise à jour avec {len(new_lines)} nouveau(x) mapping(s)")
    
    def ensure_reference_consulted(self, action: str):
        """
        S'assure que la référence a été consultée avant une action.
        
        Args:
            action: Description de l'action (ex: "mapping_techniciens", "import_produits")
        """
        cache_key = f"last_consult_{action}"
        if cache_key not in self._cache:
            print(f"📚 Consultation de la référence pour: {action}")
            print(f"   Fichier: {self.reference_path}", flush=True)
            # Vérifier que le fichier existe
            if not self.reference_path.exists():
                print(f"   ⚠️  ATTENTION: Document de référence non trouvé!", flush=True)
            self._cache[cache_key] = True
            self._save_cache()
    
    def log_reference_usage(self, action: str, details: str = ""):
        """
        Enregistre l'utilisation de la référence (pour audit).
        
        Args:
            action: Action effectuée
            details: Détails supplémentaires
        """
        log_key = f"usage_{action}"
        if log_key not in self._cache:
            self._cache[log_key] = []
        
        import datetime
        self._cache[log_key].append({
            "timestamp": datetime.datetime.now().isoformat(),
            "details": details
        })
        self._save_cache()


# Instance globale pour faciliter l'utilisation
_reference_manager = None

def get_reference_manager() -> ReferenceManager:
    """Retourne l'instance globale du gestionnaire de référence."""
    global _reference_manager
    if _reference_manager is None:
        _reference_manager = ReferenceManager()
    return _reference_manager




