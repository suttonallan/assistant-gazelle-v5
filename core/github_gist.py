#!/usr/bin/env python3
"""
Utilitaires pour stocker les rapports dans GitHub Gist.

Gratuit, persistant, et simple à utiliser.
"""

import json
import os
import requests
from typing import Dict, List, Any, Optional
from datetime import datetime


class GitHubGistStorage:
    """Gère le stockage des rapports dans un Gist GitHub."""
    
    def __init__(self, gist_id: Optional[str] = None, github_token: Optional[str] = None):
        """
        Initialise le stockage Gist.
        
        Args:
            gist_id: ID du Gist existant (si None, en crée un nouveau)
            github_token: Token GitHub (si None, utilise GITHUB_TOKEN de l'environnement)
        """
        self.github_token = github_token or os.environ.get('GITHUB_TOKEN')
        self.gist_id = gist_id or os.environ.get('GITHUB_GIST_ID')
        self.api_url = "https://api.github.com/gists"
        
        if not self.github_token:
            # Si pas de token, on peut quand même créer un Gist public (mais limité)
            # Pour l'instant, on utilise un token optionnel
            pass
    
    def _get_headers(self) -> Dict[str, str]:
        """Retourne les headers pour les requêtes GitHub API."""
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "Content-Type": "application/json"
        }
        if self.github_token:
            headers["Authorization"] = f"token {self.github_token}"
        return headers
    
    def create_gist(self, description: str = "Rapports des techniciens - Vincent-d'Indy") -> str:
        """
        Crée un nouveau Gist pour stocker les rapports.
        
        Args:
            description: Description du Gist
            
        Returns:
            ID du Gist créé
        """
        if not self.github_token:
            raise ValueError(
                "GITHUB_TOKEN requis pour créer un Gist. "
                "Ajoute-le dans les variables d'environnement Render."
            )
        
        data = {
            "description": description,
            "public": False,  # Gist privé
            "files": {
                "reports.json": {
                    "content": json.dumps({"reports": []}, indent=2)
                }
            }
        }
        
        response = requests.post(
            self.api_url,
            headers=self._get_headers(),
            json=data
        )
        
        if response.status_code != 201:
            raise Exception(f"Erreur lors de la création du Gist: {response.text}")
        
        gist_data = response.json()
        self.gist_id = gist_data["id"]
        return self.gist_id
    
    def get_reports(self) -> List[Dict[str, Any]]:
        """
        Récupère tous les rapports depuis le Gist.
        
        Returns:
            Liste des rapports
        """
        if not self.gist_id:
            return []
        
        try:
            response = requests.get(
                f"{self.api_url}/{self.gist_id}",
                headers=self._get_headers()
            )
            
            if response.status_code == 404:
                # Gist n'existe pas encore
                return []
            
            if response.status_code != 200:
                raise Exception(f"Erreur lors de la récupération: {response.text}")
            
            gist_data = response.json()
            reports_file = gist_data.get("files", {}).get("reports.json", {})
            content = reports_file.get("content", "{}")
            
            data = json.loads(content)
            return data.get("reports", [])
            
        except Exception as e:
            print(f"⚠️ Erreur lors de la récupération des rapports: {e}")
            return []
    
    def add_report(self, report: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ajoute un rapport au Gist.
        
        Args:
            report: Données du rapport à ajouter
            
        Returns:
            Rapport ajouté avec métadonnées
        """
        if not self.gist_id:
            # Créer un nouveau Gist si nécessaire
            if not self.github_token:
                raise ValueError("GITHUB_TOKEN requis pour créer un Gist")
            self.create_gist()
        
        # Récupérer les rapports existants
        reports = self.get_reports()
        
        # Ajouter le nouveau rapport
        report_with_metadata = {
            "id": f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "submitted_at": datetime.now().isoformat(),
            "status": "pending",
            "report": report
        }
        reports.append(report_with_metadata)
        
        # Mettre à jour le Gist
        if not self.github_token:
            raise ValueError("GITHUB_TOKEN requis pour mettre à jour un Gist")
        
        data = {
            "files": {
                "reports.json": {
                    "content": json.dumps({"reports": reports}, indent=2, ensure_ascii=False)
                }
            }
        }
        
        response = requests.patch(
            f"{self.api_url}/{self.gist_id}",
            headers=self._get_headers(),
            json=data
        )
        
        if response.status_code != 200:
            raise Exception(f"Erreur lors de la mise à jour du Gist: {response.text}")
        
        return report_with_metadata
    
    def get_report(self, report_id: str) -> Optional[Dict[str, Any]]:
        """
        Récupère un rapport spécifique par son ID.
        
        Args:
            report_id: ID du rapport
            
        Returns:
            Rapport ou None si non trouvé
        """
        reports = self.get_reports()
        for report in reports:
            if report.get("id") == report_id:
                return report
        return None
    
    def update_report_status(self, report_id: str, status: str) -> bool:
        """
        Met à jour le statut d'un rapport.
        
        Args:
            report_id: ID du rapport
            status: Nouveau statut ("pending", "processed", etc.)
            
        Returns:
            True si mis à jour avec succès
        """
        reports = self.get_reports()
        updated = False
        
        for report in reports:
            if report.get("id") == report_id:
                report["status"] = status
                updated = True
                break
        
        if not updated:
            return False
        
        # Mettre à jour le Gist
        if not self.github_token:
            raise ValueError("GITHUB_TOKEN requis pour mettre à jour un Gist")
        
        data = {
            "files": {
                "reports.json": {
                    "content": json.dumps({"reports": reports}, indent=2, ensure_ascii=False)
                }
            }
        }
        
        response = requests.patch(
            f"{self.api_url}/{self.gist_id}",
            headers=self._get_headers(),
            json=data
        )
        
        return response.status_code == 200


