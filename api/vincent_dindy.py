#!/usr/bin/env python3
"""
Endpoints API pour le module Vincent-d'Indy.

Gère la réception et le stockage des rapports des techniciens.
"""

import json
import os
from datetime import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

router = APIRouter(prefix="/vincent-dindy", tags=["vincent-dindy"])


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
    """Retourne le chemin du dossier pour stocker les rapports."""
    # En production (Render), utilise le volume persistant
    persistent_disk = os.environ.get('RENDER_PERSISTENT_DISK_PATH')
    if persistent_disk:
        reports_dir = os.path.join(persistent_disk, 'reports')
    else:
        # Développement local
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        reports_dir = os.path.join(project_root, 'reports')
    
    os.makedirs(reports_dir, exist_ok=True)
    return reports_dir


@router.post("/reports", response_model=Dict[str, Any])
async def submit_report(report: TechnicianReport):
    """
    Soumet un rapport de technicien.
    
    Le rapport est sauvegardé dans un fichier JSON pour être traité plus tard
    et poussé vers Gazelle.
    """
    try:
        reports_dir = get_reports_dir()
        
        # Créer un nom de fichier unique avec timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"report_{timestamp}_{report.technician_name.replace(' ', '_')}.json"
        filepath = os.path.join(reports_dir, filename)
        
        # Ajouter des métadonnées
        report_data = {
            "submitted_at": datetime.now().isoformat(),
            "status": "pending",  # En attente d'être poussé vers Gazelle
            "report": report.dict()
        }
        
        # Sauvegarder le rapport
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)
        
        return {
            "success": True,
            "message": "Rapport reçu et sauvegardé",
            "report_id": filename,
            "filepath": filepath
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la sauvegarde: {str(e)}")


@router.get("/reports", response_model=Dict[str, Any])
async def list_reports(status: Optional[str] = None, limit: int = 50):
    """
    Liste les rapports sauvegardés.
    
    Args:
        status: Filtrer par statut ("pending", "processed", "all")
        limit: Nombre maximum de rapports à retourner
    """
    try:
        reports_dir = get_reports_dir()
        
        if not os.path.exists(reports_dir):
            return {"reports": [], "count": 0}
        
        reports = []
        for filename in sorted(os.listdir(reports_dir), reverse=True):
            if filename.endswith('.json'):
                filepath = os.path.join(reports_dir, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        report_data = json.load(f)
                    
                    # Filtrer par statut si demandé
                    if status and status != "all" and report_data.get("status") != status:
                        continue
                    
                    report_data["filename"] = filename
                    reports.append(report_data)
                    
                    if len(reports) >= limit:
                        break
                except Exception:
                    continue
        
        return {
            "reports": reports,
            "count": len(reports),
            "status_filter": status or "all"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la récupération: {str(e)}")


@router.get("/reports/{report_id}", response_model=Dict[str, Any])
async def get_report(report_id: str):
    """Récupère un rapport spécifique par son ID (nom de fichier)."""
    try:
        reports_dir = get_reports_dir()
        filepath = os.path.join(reports_dir, report_id)
        
        if not os.path.exists(filepath):
            raise HTTPException(status_code=404, detail="Rapport non trouvé")
        
        with open(filepath, 'r', encoding='utf-8') as f:
            report_data = json.load(f)
        
        report_data["filename"] = report_id
        return report_data
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la récupération: {str(e)}")


@router.get("/stats", response_model=Dict[str, Any])
async def get_stats():
    """Retourne des statistiques sur les rapports."""
    try:
        reports_dir = get_reports_dir()
        
        if not os.path.exists(reports_dir):
            return {
                "total_reports": 0,
                "pending": 0,
                "processed": 0,
                "by_technician": {},
                "by_type": {}
            }
        
        stats = {
            "total_reports": 0,
            "pending": 0,
            "processed": 0,
            "by_technician": {},
            "by_type": {}
        }
        
        for filename in os.listdir(reports_dir):
            if filename.endswith('.json'):
                filepath = os.path.join(reports_dir, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        report_data = json.load(f)
                    
                    stats["total_reports"] += 1
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
                    
                except Exception:
                    continue
        
        return stats
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors du calcul des stats: {str(e)}")

