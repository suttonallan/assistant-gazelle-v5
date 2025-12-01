#!/usr/bin/env python3
"""
Endpoints API pour le module Vincent-d'Indy.

Gère la réception et le stockage des rapports des techniciens.
Utilise GitHub Gist pour le stockage persistant (gratuit).
"""

import json
import os
import csv
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from core.github_gist import GitHubGistStorage
from core.gazelle_api_client import GazelleAPIClient

router = APIRouter(prefix="/vincent-dindy", tags=["vincent-dindy"])

# Initialiser le stockage Gist
_gist_storage = None
_api_client = None

def get_gist_storage() -> GitHubGistStorage:
    """Retourne l'instance du stockage Gist (singleton)."""
    global _gist_storage
    if _gist_storage is None:
        _gist_storage = GitHubGistStorage()
    return _gist_storage

def get_api_client() -> GazelleAPIClient:
    """Retourne l'instance du client API Gazelle (singleton)."""
    global _api_client
    if _api_client is None:
        try:
            _api_client = GazelleAPIClient()
        except Exception as e:
            print(f"⚠️ Erreur lors de l'initialisation du client API: {e}")
            _api_client = None
    return _api_client


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


def get_csv_path() -> str:
    """Retourne le chemin vers le fichier CSV des pianos.
    
    Cherche d'abord dans api/data/ (recommandé), puis dans data_csv_test/ (fallback).
    """
    # Liste des chemins possibles à essayer (par ordre de priorité)
    possible_paths = []
    
    # 1. Chemin relatif depuis le fichier actuel dans api/data/ (RECOMMANDÉ)
    current_file_dir = os.path.dirname(os.path.abspath(__file__))
    possible_paths.append(os.path.join(current_file_dir, 'data', 'pianos_vincent_dindy.csv'))
    
    # 2. Chemin depuis le répertoire courant dans api/data/ (Render)
    possible_paths.append(os.path.join(os.getcwd(), 'api', 'data', 'pianos_vincent_dindy.csv'))
    
    # 3. Fallback : ancien chemin dans data_csv_test/ (pour compatibilité)
    project_root = os.path.dirname(os.path.dirname(current_file_dir))
    possible_paths.append(os.path.join(project_root, 'data_csv_test', 'pianos_vincent_dindy.csv'))
    possible_paths.append(os.path.join(os.getcwd(), 'data_csv_test', 'pianos_vincent_dindy.csv'))
    possible_paths.append('data_csv_test/pianos_vincent_dindy.csv')
    
    # Essayer chaque chemin jusqu'à trouver celui qui existe
    for path in possible_paths:
        if os.path.exists(path):
            return path
    
    # Si aucun n'existe, retourner le premier (pour l'erreur)
    return possible_paths[0]


@router.get("/pianos", response_model=Dict[str, Any])
async def get_pianos():
    """
    Récupère tous les pianos depuis le CSV.
    
    Format CSV attendu : local, Piano, # série, Priorité, Type, À faire
    
    Plus tard, on connectera avec l'API Gazelle.
    """
    try:
        csv_path = get_csv_path()
        
        # Debug: logger le chemin cherché
        import logging
        logging.info(f"🔍 Recherche du CSV à: {csv_path}")
        logging.info(f"📁 Répertoire courant: {os.getcwd()}")
        logging.info(f"📁 Fichier __file__: {__file__}")
        
        if not os.path.exists(csv_path):
            # Si le CSV n'existe pas, retourner une liste vide avec message de debug
            error_msg = f"Fichier CSV non trouvé: {csv_path}. Répertoire courant: {os.getcwd()}"
            logging.error(f"❌ {error_msg}")
            return {
                "pianos": [],
                "count": 0,
                "error": True,
                "message": error_msg,
                "debug": {
                    "csv_path": csv_path,
                    "current_dir": os.getcwd(),
                    "file_exists": os.path.exists(csv_path)
                }
            }
        
        logging.info(f"✅ CSV trouvé: {csv_path}")
        pianos = []
        rows_processed = 0
        rows_skipped = 0
        
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for idx, row in enumerate(reader, start=1):
                rows_processed += 1
                # Nettoyer les noms de colonnes (enlever espaces)
                local = row.get("local", "").strip()
                piano_name = row.get("Piano", "").strip()
                serie = row.get("# série", "").strip() or row.get("série", "").strip()
                priorite = row.get("Priorité", "").strip() or row.get("Priorité ", "").strip()
                type_piano = row.get("Type", "").strip()
                a_faire = row.get("À faire", "").strip()
                
                # Ignorer les lignes vides ou sans piano
                if not piano_name and not serie:
                    rows_skipped += 1
                    continue
                
                # Générer un ID unique (index ou série si disponible)
                piano_id = serie if serie else f"piano_{idx}"
                
                # Déterminer le statut basé sur la priorité
                status = "normal"
                if priorite:
                    # Si priorité existe, proposer le piano
                    status = "proposed"
                
                # Formater les données pour correspondre au format attendu par le frontend
                piano = {
                    "id": piano_id,
                    "local": local if local and local != "?" else "",
                    "piano": piano_name,
                    "serie": serie,
                    "type": type_piano.upper() if type_piano else "D",  # D, Q, ou autre
                    "usage": "",  # Pas dans le CSV pour l'instant
                    "dernierAccord": "",  # Pas dans le CSV pour l'instant
                    "aFaire": a_faire,
                    "status": status,
                    "travail": "",
                    "observations": ""
                }
                pianos.append(piano)
        
        logging.info(f"✅ {len(pianos)} pianos chargés ({rows_processed} lignes traitées, {rows_skipped} ignorées)")
        
        return {
            "pianos": pianos,
            "count": len(pianos),
            "debug": {
                "rows_processed": rows_processed,
                "rows_skipped": rows_skipped
            }
        }
        
    except Exception as e:
        import traceback
        error_detail = f"Erreur lors de la récupération des pianos: {str(e)}\n{traceback.format_exc()}"
        logging.error(f"❌ {error_detail}")
        raise HTTPException(status_code=500, detail=error_detail)


@router.get("/pianos/{piano_id}", response_model=Dict[str, Any])
async def get_piano(piano_id: str):
    """Récupère les détails d'un piano spécifique depuis le CSV."""
    try:
        csv_path = get_csv_path()
        
        if not os.path.exists(csv_path):
            raise HTTPException(status_code=404, detail="Fichier CSV non trouvé")
        
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for idx, row in enumerate(reader, start=1):
                # Nettoyer les noms de colonnes
                serie = row.get("# série", "").strip() or row.get("série", "").strip()
                current_id = serie if serie else f"piano_{idx}"
                
                if current_id == piano_id:
                    local = row.get("local", "").strip()
                    piano_name = row.get("Piano", "").strip()
                    priorite = row.get("Priorité", "").strip() or row.get("Priorité ", "").strip()
                    type_piano = row.get("Type", "").strip()
                    a_faire = row.get("À faire", "").strip()
                    
                    status = "normal"
                    if priorite:
                        status = "proposed"
                    
                    return {
                        "id": current_id,
                        "local": local if local and local != "?" else "",
                        "piano": piano_name,
                        "serie": serie,
                        "type": type_piano.upper() if type_piano else "D",
                        "usage": "",
                        "dernierAccord": "",
                        "aFaire": a_faire,
                        "status": status,
                        "travail": "",
                        "observations": ""
                    }
        
        raise HTTPException(status_code=404, detail="Piano non trouvé")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la récupération: {str(e)}")


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
