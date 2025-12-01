#!/usr/bin/env python3
"""
Endpoints API pour le module Vincent-d'Indy.

Gère la réception et le stockage des rapports des techniciens.
Utilise GitHub Gist pour le stockage persistant (gratuit).
"""

import json
import os
from datetime import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from core.github_gist import GitHubGistStorage

router = APIRouter(prefix="/vincent-dindy", tags=["vincent-dindy"])

# Initialiser le stockage Gist
_gist_storage = None

def get_gist_storage() -> GitHubGistStorage:
    """Retourne l'instance du stockage Gist (singleton)."""
    global _gist_storage
    if _gist_storage is None:
        _gist_storage = GitHubGistStorage()
    return _gist_storage


class TechnicianReport(BaseModel):
    """Modèle pour un rapport de technicien."""
    technician_name: str
    client_name: Optional[str] = None
    client_id: Optional[str] = None
    date: str
    report_type: str  # "maintenance", "repair", "inspection", etc.
    description: str
    notes: Optional[str] = None
    items_used: Optional[List[Dict[str, Any]]] = None
    hours_worked: Optional[float] = None


def get_reports_dir() -> str:
    """
    Retourne le chemin du dossier pour stocker les rapports.
    
    Note: Sur Render gratuit (sans persistent disk), les fichiers sont temporaires.
    Les rapports seront perdus au redémarrage. Utilisez l'endpoint /push-to-gazelle
    pour pousser les rapports vers Gazelle avant qu'ils ne soient perdus.
    """
    # En production (Render), utilise le volume persistant si disponible
    persistent_disk = os.environ.get('RENDER_PERSISTENT_DISK_PATH')
    if persistent_disk:
        reports_dir = os.path.join(persistent_disk, 'reports')
    else:
        # Développement local ou Render gratuit (temporaire)
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        reports_dir = os.path.join(project_root, 'reports')
    
    os.makedirs(reports_dir, exist_ok=True)
    return reports_dir


@router.post("/reports", response_model=Dict[str, Any])
async def submit_report(report: TechnicianReport):
    """
    Soumet un rapport de technicien.
    
    Le rapport est sauvegardé dans un Gist GitHub (persistant et gratuit).
    Plus tard, on pourra pousser ces rapports vers Gazelle.
    """
    try:
        storage = get_gist_storage()
        report_data = report.dict()
        
        # Ajouter le rapport au Gist
        saved_report = storage.add_report(report_data)
        
        return {
            "success": True,
            "message": "Rapport reçu et sauvegardé dans GitHub Gist",
            "report_id": saved_report["id"],
            "submitted_at": saved_report["submitted_at"],
            "status": saved_report["status"]
        }
        
    except ValueError as e:
        # Token GitHub manquant
        raise HTTPException(
            status_code=400,
            detail=f"Configuration manquante: {str(e)}. Ajoutez GITHUB_TOKEN dans les variables d'environnement Render."
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la sauvegarde: {str(e)}")


@router.get("/reports", response_model=Dict[str, Any])
async def list_reports(status: Optional[str] = None, limit: int = 50):
    """
    Liste les rapports sauvegardés depuis GitHub Gist.
    
    Args:
        status: Filtrer par statut ("pending", "processed", "all")
        limit: Nombre maximum de rapports à retourner
    """
    try:
        storage = get_gist_storage()
        all_reports = storage.get_reports()
        
        # Filtrer par statut si demandé
        if status and status != "all":
            all_reports = [r for r in all_reports if r.get("status") == status]
        
        # Limiter le nombre de résultats
        reports = sorted(all_reports, key=lambda x: x.get("submitted_at", ""), reverse=True)[:limit]
        
        return {
            "reports": reports,
            "count": len(reports),
            "total": len(all_reports),
            "status_filter": status or "all"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la récupération: {str(e)}")


@router.get("/reports/{report_id}", response_model=Dict[str, Any])
async def get_report(report_id: str):
    """Récupère un rapport spécifique par son ID depuis GitHub Gist."""
    try:
        storage = get_gist_storage()
        report = storage.get_report(report_id)
        
        if not report:
            raise HTTPException(status_code=404, detail="Rapport non trouvé")
        
        return report
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la récupération: {str(e)}")


@router.get("/stats", response_model=Dict[str, Any])
async def get_stats():
    """Retourne des statistiques sur les rapports depuis GitHub Gist."""
    try:
        storage = get_gist_storage()
        reports = storage.get_reports()
        
        stats = {
            "total_reports": len(reports),
            "pending": 0,
            "processed": 0,
            "by_technician": {},
            "by_type": {}
        }
        
        for report_data in reports:
            status = report_data.get("status", "pending")
            if status == "pending":
                stats["pending"] += 1
            elif status == "processed":
                stats["processed"] += 1
            
            # Stats par technicien
            tech_name = report_data.get("report", {}).get("technician_name", "Unknown")
            stats["by_technician"][tech_name] = stats["by_technician"].get(tech_name, 0) + 1
            
            # Stats par type
            report_type = report_data.get("report", {}).get("report_type", "unknown")
            stats["by_type"][report_type] = stats["by_type"].get(report_type, 0) + 1
        
        return stats
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors du calcul des stats: {str(e)}")

