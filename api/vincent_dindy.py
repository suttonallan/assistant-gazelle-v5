#!/usr/bin/env python3
"""
Endpoints API pour le module Vincent-d'Indy.

Gère la réception et le stockage des rapports des techniciens.
Utilise Supabase pour le stockage persistant (rapide et fiable).
"""

import json
import os
import csv
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from core.supabase_storage import SupabaseStorage
from core.gazelle_api_client import GazelleAPIClient

router = APIRouter(prefix="/vincent-dindy", tags=["vincent-dindy"])

# Initialiser le stockage Supabase
_supabase_storage = None
_api_client = None

def get_supabase_storage() -> SupabaseStorage:
    """Retourne l'instance du stockage Supabase (singleton)."""
    global _supabase_storage
    if _supabase_storage is None:
        _supabase_storage = SupabaseStorage()
    return _supabase_storage

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
    Récupère tous les pianos en fusionnant CSV (données fixes) + Supabase (modifications).

    Architecture:
    - CSV = Liste de référence des 91 pianos (local, piano, type, usage)
    - Supabase = Modifications dynamiques (status, aFaire, travail, observations)
    - Retour = Fusion des deux (CSV comme base, Supabase overlay)
    """
    try:
        import logging
        logging.info(f"🔍 Chargement des pianos (CSV + Supabase)")

        # 1. Charger la liste complète depuis le CSV (données FIXES)
        csv_path = get_csv_path()
        pianos = []

        if not os.path.exists(csv_path):
            raise FileNotFoundError(f"CSV introuvable: {csv_path}")

        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for idx, row in enumerate(reader, start=1):
                local = row.get("local", "").strip()
                piano_name = row.get("Piano", "").strip()
                serie = row.get("# série", "").strip() or row.get("série", "").strip()
                type_piano = row.get("Type", "").strip()
                usage = row.get("Usage", "").strip()
                a_faire_csv = row.get("À faire", "").strip()

                if not piano_name and not serie:
                    continue

                piano_id = serie if serie else f"piano_{idx}"

                # Données de BASE depuis CSV (FIXES)
                piano = {
                    "id": piano_id,
                    "local": local if local and local != "?" else "",
                    "piano": piano_name,
                    "serie": serie,
                    "type": type_piano.upper() if type_piano else "D",
                    "usage": usage,
                    # Valeurs par défaut pour champs dynamiques
                    "dernierAccord": "",
                    "aFaire": a_faire_csv,
                    "status": "normal",
                    "travail": "",
                    "observations": "",
                    "gazelleId": None  # ID Gazelle (ins_xxxxx) depuis Supabase
                }
                pianos.append(piano)

        logging.info(f"📋 {len(pianos)} pianos chargés depuis CSV")

        # 2. Charger les modifications depuis Supabase (DYNAMIQUES)
        storage = get_supabase_storage()
        supabase_updates = storage.get_all_piano_updates()

        logging.info(f"☁️  {len(supabase_updates)} modifications Supabase trouvées")

        # 3. FUSION: Appliquer les modifications Supabase sur les données CSV
        for piano in pianos:
            piano_id = piano["id"]
            if piano_id in supabase_updates:
                updates = supabase_updates[piano_id]

                # Appliquer UNIQUEMENT les champs DYNAMIQUES depuis Supabase
                if "dernier_accord" in updates:
                    piano["dernierAccord"] = updates["dernier_accord"]
                if "a_faire" in updates:
                    piano["aFaire"] = updates["a_faire"]
                if "status" in updates:
                    piano["status"] = updates["status"]
                if "travail" in updates:
                    piano["travail"] = updates["travail"]
                if "observations" in updates:
                    piano["observations"] = updates["observations"]
                if "gazelle_id" in updates:
                    piano["gazelleId"] = updates["gazelle_id"]

        logging.info(f"✅ Fusion complète: {len(pianos)} pianos retournés")

        return {
            "pianos": pianos,
            "count": len(pianos)
        }
        
    except Exception as e:
        import traceback
        error_detail = f"Erreur lors de la récupération des pianos: {str(e)}\n{traceback.format_exc()}"
        logging.error(f"❌ {error_detail}")
        raise HTTPException(status_code=500, detail=error_detail)


class PianoUpdate(BaseModel):
    """Modèle pour la mise à jour d'un piano."""
    status: Optional[str] = None
    usage: Optional[str] = None
    dernierAccord: Optional[str] = None
    aFaire: Optional[str] = None
    travail: Optional[str] = None
    observations: Optional[str] = None
    updated_by: Optional[str] = None  # Email ou nom de l'utilisateur


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

                    # Récupérer les modifications depuis Supabase si elles existent
                    piano_data = {
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

                    # Appliquer les modifications depuis Supabase
                    try:
                        storage = get_supabase_storage()
                        updates = storage.get_piano_updates(current_id)
                        if updates:
                            piano_data.update(updates)
                    except:
                        pass  # Si pas de modification Supabase, utiliser les données CSV

                    return piano_data

        raise HTTPException(status_code=404, detail="Piano non trouvé")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la récupération: {str(e)}")


@router.put("/pianos/{piano_id}", response_model=Dict[str, Any])
async def update_piano(piano_id: str, update: PianoUpdate):
    """Met à jour un piano (sauvegarde dans Supabase)."""
    try:
        # Vérifier que le piano existe dans le CSV
        csv_path = get_csv_path()
        piano_exists = False

        if os.path.exists(csv_path):
            with open(csv_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for idx, row in enumerate(reader, start=1):
                    serie = row.get("# série", "").strip() or row.get("série", "").strip()
                    current_id = serie if serie else f"piano_{idx}"
                    if current_id == piano_id:
                        piano_exists = True
                        break

        if not piano_exists:
            raise HTTPException(status_code=404, detail="Piano non trouvé")

        # Sauvegarder les modifications dans Supabase
        storage = get_supabase_storage()

        # Convertir les champs camelCase vers snake_case pour Supabase
        update_dict = update.dict(exclude_none=True)
        update_data = {}
        for key, value in update_dict.items():
            if key == 'aFaire':
                update_data['a_faire'] = value
            elif key == 'dernierAccord':
                update_data['dernier_accord'] = value
            elif key == 'updated_by':
                update_data['updated_by'] = value
            else:
                # status, usage, travail, observations restent identiques
                update_data[key] = value

        success = storage.update_piano(piano_id, update_data)
        
        if not success:
            raise HTTPException(
                status_code=500, 
                detail="Échec de la sauvegarde dans Supabase. Vérifiez les logs du serveur."
            )

        return {
            "success": True,
            "message": "Piano mis à jour avec succès",
            "piano_id": piano_id,
            "updates": update_data
        }

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Configuration manquante: {str(e)}. Ajoutez GITHUB_TOKEN dans les variables d'environnement."
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la mise à jour: {str(e)}")


@router.put("/pianos/batch", response_model=Dict[str, Any])
async def batch_update_pianos(updates: List[Dict[str, Any]]):
    """
    Met à jour plusieurs pianos en une seule requête (batch update).
    Beaucoup plus rapide que plusieurs requêtes individuelles.

    Body exemple:
    [
        {"piano_id": "A-001", "status": "top"},
        {"piano_id": "A-002", "status": "proposed", "usage": "Enseignement"}
    ]
    """
    try:
        if not updates:
            return {"success": True, "message": "Aucune mise à jour", "count": 0}

        storage = get_supabase_storage()

        # Préparer les données pour le batch
        batch_data = []
        for update in updates:
            if "piano_id" not in update:
                raise HTTPException(status_code=400, detail="Chaque mise à jour doit contenir 'piano_id'")

            # Convertir les clés camelCase en snake_case pour Supabase
            snake_case_update = {}
            for key, value in update.items():
                if key == "piano_id":
                    snake_case_update["piano_id"] = value
                elif key == "dernierAccord":
                    snake_case_update["dernier_accord"] = value
                elif key == "aFaire":
                    snake_case_update["a_faire"] = value
                else:
                    snake_case_update[key] = value

            batch_data.append(snake_case_update)

        # Exécuter le batch update
        success = storage.batch_update_pianos(batch_data)

        if success:
            return {
                "success": True,
                "message": f"{len(updates)} pianos mis à jour",
                "count": len(updates)
            }
        else:
            raise HTTPException(status_code=500, detail="Échec de la mise à jour batch")

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur batch update: {str(e)}")


@router.post("/reports", response_model=Dict[str, Any])
async def submit_report(report: TechnicianReport):
    """
    Soumet un rapport de technicien.

    Le rapport est sauvegardé dans Supabase (persistant et fiable).
    Plus tard, on pourra pousser ces rapports vers Gazelle.
    """
    try:
        storage = get_supabase_storage()
        report_data = report.dict()

        # Ajouter le rapport au Gist
        saved_report = storage.add_report(report_data)

        return {
            "success": True,
            "message": "Rapport reçu et sauvegardé dans Supabase",
            "report_id": saved_report["id"],
            "submitted_at": saved_report["submitted_at"],
            "status": saved_report["status"]
        }

    except ValueError as e:
        # Configuration Supabase manquante
        raise HTTPException(
            status_code=400,
            detail=f"Configuration manquante: {str(e)}. Ajoutez SUPABASE_URL et SUPABASE_KEY dans les variables d'environnement."
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la sauvegarde: {str(e)}")


@router.get("/reports", response_model=Dict[str, Any])
async def list_reports(status: Optional[str] = None, limit: int = 50):
    """
    Liste les rapports sauvegardés depuis Supabase.
    
    Args:
        status: Filtrer par statut ("pending", "processed", "all")
        limit: Nombre maximum de rapports à retourner
    """
    try:
        storage = get_supabase_storage()
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
    """Récupère un rapport spécifique par son ID depuis Supabase."""
    try:
        storage = get_supabase_storage()
        report = storage.get_report(report_id)
        
        if not report:
            raise HTTPException(status_code=404, detail="Rapport non trouvé")
        
        return report
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la récupération: {str(e)}")


@router.get("/activity", response_model=Dict[str, Any])
async def get_activity(limit: int = 20):
    """
    Récupère l'historique d'activité (qui a modifié quoi, quand).

    Args:
        limit: Nombre maximum d'activités à retourner

    Returns:
        Liste des activités récentes avec updated_by et updated_at
    """
    try:
        storage = get_supabase_storage()
        all_updates = storage.get_all_piano_updates()

        # Convertir en liste triée par date (plus récent en premier)
        activities = []
        for piano_id, update_data in all_updates.items():
            if update_data.get('updated_by') and update_data.get('updated_at'):
                activities.append({
                    "piano_id": piano_id,
                    "updated_by": update_data.get('updated_by'),
                    "updated_at": update_data.get('updated_at'),
                    "status": update_data.get('status'),
                    "observations": update_data.get('observations', '')
                })

        # Trier par date décroissante
        activities.sort(key=lambda x: x.get('updated_at', ''), reverse=True)

        return {
            "activities": activities[:limit],
            "total": len(activities)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la récupération de l'activité: {str(e)}")


@router.get("/stats", response_model=Dict[str, Any])
async def get_stats():
    """Retourne des statistiques sur les rapports depuis Supabase."""
    try:
        storage = get_supabase_storage()
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
