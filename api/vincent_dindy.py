#!/usr/bin/env python3
"""
Endpoints API pour le module Vincent-d'Indy.

Gère la réception et le stockage des rapports des techniciens.
Utilise Supabase pour le stockage persistant (rapide et fiable).
"""

import json
import os
import csv
import ast
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from core.supabase_storage import SupabaseStorage
from core.gazelle_api_client import GazelleAPIClient

router = APIRouter(prefix="/vincent-dindy", tags=["vincent-dindy"])

# Mapping institution → client_id Gazelle (importé depuis le bridge)
from core.service_completion_bridge import INSTITUTION_CLIENT_MAPPING

# Client ID Vincent d'Indy dans Gazelle (legacy - à retirer progressivement)
VINCENT_DINDY_CLIENT_ID = "cli_9UMLkteep8EsISbG"

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
async def get_pianos(
    include_inactive: bool = False,
    institution: str = "vincent-dindy"
):
    """
    Récupère tous les pianos depuis Gazelle API.

    Args:
        include_inactive: Si True, inclut les pianos avec tag "non" (masqués par défaut)
        institution: Institution à charger (vincent-dindy, orford, place-des-arts)

    Architecture V7:
    - Gazelle API = Source unique de vérité (tags inclus)
    - Tag "non" dans Gazelle = piano masqué de l'inventaire/tournées
    - Filtre par défaut = masque les pianos avec tag "non"
    - Supabase = Modifications dynamiques (status, notes, etc.)
    """
    try:
        import logging

        # Récupérer le clientId depuis le mapping
        client_id = INSTITUTION_CLIENT_MAPPING.get(institution)
        if not client_id:
            raise HTTPException(
                status_code=400,
                detail=f"Institution '{institution}' non configurée ou clientId manquant"
            )

        logging.info(f"🔍 Chargement des pianos depuis Gazelle (institution: {institution}, client: {client_id})")

        # 1. Charger TOUS les pianos depuis Gazelle
        api_client = get_api_client()

        if not api_client:
            raise HTTPException(status_code=500, detail="Client API Gazelle non disponible")

        query = """
        query GetVincentDIndyPianos($clientId: String!) {
          allPianos(first: 200, filters: { clientId: $clientId }) {
            nodes {
              id
              serialNumber
              make
              model
              location
              type
              status
              notes
              calculatedLastService
              calculatedNextService
              serviceIntervalMonths
              tags
            }
          }
        }
        """

        variables = {"clientId": client_id}
        result = api_client._execute_query(query, variables)
        gazelle_pianos = result.get("data", {}).get("allPianos", {}).get("nodes", [])

        logging.info(f"📋 {len(gazelle_pianos)} pianos chargés depuis Gazelle")

        # 2. Charger les modifications depuis Supabase (flags + overlays)
        storage = get_supabase_storage()
        supabase_updates = storage.get_all_piano_updates()

        logging.info(f"☁️  {len(supabase_updates)} modifications Supabase trouvées")

        # 3. FUSION: Transformer pianos Gazelle + appliquer overlays Supabase
        pianos = []

        for gz_piano in gazelle_pianos:
            gz_id = gz_piano['id']
            serial = gz_piano.get('serialNumber', gz_id)  # Fallback au gazelle_id si pas de serial

            # Trouver les updates Supabase (matcher par gazelleId OU serial)
            # Note: piano_id dans Supabase = gazelleId en priorité
            updates = {}
            for piano_id, data in supabase_updates.items():
                if (piano_id == gz_id or piano_id == serial):
                    updates = data
                    break

            # Parser les tags Gazelle (source unique de vérité)
            # Format Gazelle: peut être une liste Python ['non'] OU une string "['non']"
            tags_raw = gz_piano.get('tags', '')
            tags = []
            if tags_raw:
                try:
                    # Si c'est déjà une liste, utiliser directement
                    if isinstance(tags_raw, list):
                        tags = tags_raw
                    # Sinon, parser la string
                    elif isinstance(tags_raw, str):
                        tags = ast.literal_eval(tags_raw)
                except Exception as e:
                    logging.warning(f"Erreur parsing tags pour piano {serial}: {e} - tags_raw: {tags_raw}")
                    tags = []

            # Filtrage par tag: si le piano a le tag "non", le masquer par défaut
            has_non_tag = 'non' in [t.lower() for t in tags]

            # Filtrage par flag Supabase is_hidden
            is_hidden_in_assistant = updates.get('is_hidden', False)

            # FILTRE DE VISIBILITÉ COMBINÉ (Mode Inventaire vs Mode Révision)
            # Un piano est masqué si: (Tag Gazelle == 'non') OU (Marqué caché dans Assistant/Supabase)
            if not include_inactive and (has_non_tag or is_hidden_in_assistant):
                continue  # Ignorer les pianos masqués (sauf si Mode Révision activé)

            # Construire l'objet piano
            piano_type = gz_piano.get('type', 'UPRIGHT')
            if piano_type:
                type_letter = piano_type[0].upper()  # 'GRAND' → 'G', 'UPRIGHT' → 'U'
            else:
                type_letter = 'D'

            piano = {
                "id": gz_id,  # TOUJOURS utiliser gazelleId comme clé unique (car les serials peuvent être dupliqués)
                "gazelleId": gz_id,
                "local": gz_piano.get('location', ''),
                "piano": gz_piano.get('make', ''),
                "modele": gz_piano.get('model', ''),
                "serie": serial,
                "type": type_letter,
                "usage": "",  # Pas disponible dans Gazelle
                "dernierAccord": gz_piano.get('calculatedLastService', ''),
                "prochainAccord": gz_piano.get('calculatedNextService', ''),
                "status": updates.get('status', 'normal'),
                "aFaire": updates.get('a_faire', ''),
                "travail": updates.get('travail', ''),
                "observations": updates.get('observations', gz_piano.get('notes', '')),
                "is_work_completed": updates.get('is_work_completed', False),  # Checkbox "Travail complété"
                "sync_status": updates.get('sync_status', 'pending'),  # État de synchronisation avec Gazelle
                "tags": tags,  # Tags depuis Gazelle (source unique de vérité)
                "hasNonTag": has_non_tag,  # Flag pour indiquer si le piano est masqué par défaut
                "isHidden": is_hidden_in_assistant,  # Flag pour masquer le piano dans l'Assistant (Supabase)
                "isInCsv": updates.get('is_in_csv', True),  # Flag inventaire CSV (True par défaut si non spécifié)
                "gazelleStatus": gz_piano.get('status', 'UNKNOWN')  # Status Gazelle
            }

            pianos.append(piano)

        logging.info(f"✅ {len(pianos)} pianos retournés (include_inactive={include_inactive})")

        return {
            "pianos": pianos,
            "count": len(pianos),
            "source": "gazelle",
            "clientId": VINCENT_DINDY_CLIENT_ID
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
    isInCsv: Optional[bool] = None  # Flag d'inventaire
    isWorkCompleted: Optional[bool] = None  # Checkbox "Travail complété"
    isHidden: Optional[bool] = None  # Masquer complètement le piano
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
        # Note: On ne vérifie plus si le piano existe dans Gazelle pour des raisons de performance.
        # Supabase acceptera la mise à jour que le piano existe ou non.
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
            elif key == 'isInCsv':
                update_data['is_in_csv'] = value
            elif key == 'isWorkCompleted':
                update_data['is_work_completed'] = value
            elif key == 'isHidden':
                update_data['is_hidden'] = value
            elif key == 'updated_by':
                update_data['updated_by'] = value
            else:
                # status, usage, travail, observations restent identiques
                update_data[key] = value

        # LOGIQUE DE TRANSITION AUTOMATIQUE D'ÉTAT
        # Si travail ou observations remplis ET is_work_completed = false → work_in_progress
        if ('travail' in update_data or 'observations' in update_data) and \
           update_data.get('is_work_completed') == False and \
           'status' not in update_data:
            update_data['status'] = 'work_in_progress'

        # Si is_work_completed = true → completed
        if update_data.get('is_work_completed') == True and 'status' not in update_data:
            update_data['status'] = 'completed'
            # Enregistrer la date de complétion si pas déjà définie
            if 'completed_at' not in update_data:
                from datetime import datetime
                update_data['completed_at'] = datetime.now().isoformat()
            # TODO: Ajouter completed_in_tournee_id si tournée active

        # Si piano était pushed et on modifie travail/observations → sync_status = modified
        # (géré par trigger SQL auto_mark_sync_modified)

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


@router.post("/pianos/{piano_id}/complete-service", response_model=Dict[str, Any])
async def complete_service_for_piano(
    piano_id: str,
    technician_name: Optional[str] = None,
    auto_push: bool = True
):
    """
    Complète un service et push automatiquement vers Gazelle via le pont modulaire.

    Ce endpoint utilise le Service Completion Bridge pour:
    1. Récupérer les notes de service depuis Supabase
    2. Pousser vers Gazelle (Last Tuned + Service Note + Measurements)
    3. Mettre à jour le sync_status dans Supabase

    Path params:
        piano_id: ID du piano (ex: "ins_abc123")

    Query params:
        technician_name: Nom du technicien (ex: "Nicolas", "Isabelle")
                        Défaut: Auto-détecté depuis updated_by
        auto_push: Si True, push immédiatement vers Gazelle
                  Si False, marque juste comme prêt pour push manuel
                  Défaut: True

    Response:
        {
            "success": true,
            "piano_id": "ins_abc123",
            "pushed_to_gazelle": true,
            "gazelle_event_id": "evt_xyz",
            "last_tuned_updated": true,
            "service_note_created": true,
            "measurement_created": true,
            "measurement_values": {"temperature": 22, "humidity": 45}
        }

    Usage depuis le frontend:
        // Après que l'utilisateur clique "Travail complété"
        const response = await fetch(
            `/api/vincent-dindy/pianos/${pianoId}/complete-service?technician_name=Nicolas`,
            { method: 'POST' }
        );
    """
    try:
        import logging
        from core.service_completion_bridge import complete_service_session

        logging.info(f"📋 Complétion de service pour piano {piano_id}")

        # 1. Récupérer les données du piano depuis Supabase
        storage = get_supabase_storage()
        piano_data = storage.get_piano_updates(piano_id)

        if not piano_data:
            raise HTTPException(
                status_code=404,
                detail=f"Piano {piano_id} non trouvé dans Supabase"
            )

        # 2. Vérifier que le piano est bien marqué comme complété
        if piano_data.get('status') != 'completed' or not piano_data.get('is_work_completed'):
            raise HTTPException(
                status_code=400,
                detail=f"Le piano {piano_id} n'est pas marqué comme complété. "
                       f"Status: {piano_data.get('status')}, is_work_completed: {piano_data.get('is_work_completed')}"
            )

        # 3. Extraire les notes de service
        travail = piano_data.get('travail', '')
        observations = piano_data.get('observations', '')

        # Combiner travail + observations
        service_notes = f"{travail}\n{observations}".strip()
        if not service_notes:
            raise HTTPException(
                status_code=400,
                detail=f"Piano {piano_id} n'a pas de notes de service (travail et observations vides)"
            )

        # 4. Déterminer le nom du technicien
        if not technician_name:
            # Auto-détecter depuis updated_by
            updated_by = piano_data.get('updated_by', '')
            # Extraire le prénom depuis l'email (ex: "nlessard@piano-tek.com" → "Nicolas")
            if '@' in updated_by:
                email_prefix = updated_by.split('@')[0].lower()
                if 'nlessard' in email_prefix or 'nicolas' in email_prefix:
                    technician_name = 'Nicolas'
                elif 'isabelle' in email_prefix:
                    technician_name = 'Isabelle'
                elif 'jp' in email_prefix or 'jeanphilippe' in email_prefix:
                    technician_name = 'JP'

        # 5. Si auto_push = False, juste marquer comme prêt et retourner
        if not auto_push:
            # Marquer comme prêt pour push (sync_status = 'pending')
            storage.update_piano(piano_id, {'sync_status': 'pending'})
            logging.info(f"✅ Piano {piano_id} marqué comme prêt pour push (auto_push=False)")

            return {
                "success": True,
                "piano_id": piano_id,
                "pushed_to_gazelle": False,
                "marked_as_ready": True,
                "message": "Piano marqué comme prêt pour push manuel"
            }

        # 6. Push vers Gazelle via le pont modulaire
        logging.info(f"🚀 Push vers Gazelle via Service Completion Bridge")

        bridge_result = complete_service_session(
            piano_id=piano_id,
            service_notes=service_notes,
            institution="vincent-dindy",
            technician_name=technician_name,
            technician_id=None,  # Force None - événement créé sans technicien assigné pour éviter "dossier client introuvable"
            service_type="TUNING",
            event_date=piano_data.get('completed_at'),  # Utiliser la date de complétion
            metadata={
                'updated_by': piano_data.get('updated_by'),
                'status': piano_data.get('status'),
                'sync_status_before': piano_data.get('sync_status')
            }
        )

        # 7. Mettre à jour le sync_status dans Supabase
        if bridge_result['success']:
            storage.update_piano(piano_id, {
                'sync_status': 'pushed',
                'last_sync_at': datetime.now().isoformat(),
                'gazelle_event_id': bridge_result['gazelle_event_id']
            })
            logging.info(f"✅ Piano {piano_id} sync_status mis à jour → pushed")

        # 8. Retourner le résultat
        return {
            "success": bridge_result['success'],
            "piano_id": piano_id,
            "pushed_to_gazelle": True,
            "gazelle_event_id": bridge_result['gazelle_event_id'],
            "last_tuned_updated": bridge_result['last_tuned_updated'],
            "service_note_created": bridge_result['service_note_created'],
            "measurement_created": bridge_result['measurement_created'],
            "measurement_values": bridge_result['measurement_values'],
            "piano_set_inactive": bridge_result['piano_set_inactive'],
            "technician_used": technician_name or "Auto-détecté"
        }

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        import logging
        error_detail = f"Erreur lors de la complétion du service: {str(e)}\n{traceback.format_exc()}"
        logging.error(f"❌ {error_detail}")
        raise HTTPException(status_code=500, detail=error_detail)


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


class TourneeCreate(BaseModel):
    """Modèle pour la création d'une tournée."""
    nom: str
    date_debut: str  # Format: YYYY-MM-DD
    date_fin: str    # Format: YYYY-MM-DD
    status: str = "planifiee"  # planifiee | en_cours | terminee
    etablissement: str = "vincent-dindy"  # Institution (vincent-dindy, orford, etc.)
    technicien_responsable: str
    piano_ids: Optional[List[str]] = []
    notes: Optional[str] = None
    created_by: str = "system"


class TourneeUpdate(BaseModel):
    """Modèle pour la mise à jour d'une tournée."""
    nom: Optional[str] = None
    date_debut: Optional[str] = None
    date_fin: Optional[str] = None
    status: Optional[str] = None
    technicien_responsable: Optional[str] = None
    technicien_assigne: Optional[str] = None
    piano_ids: Optional[List[str]] = None
    notes: Optional[str] = None


@router.get("/tournees", response_model=Dict[str, Any])
async def get_tournees(institution: Optional[str] = None):
    """
    Récupère les tournées depuis Supabase filtrées par institution (client_id).

    Query params:
        institution: Nom de l'institution (ex: "vincent-dindy", "orford")
                    OBLIGATOIRE pour l'étanchéité multi-institutionnelle

    Architecture V7:
    - Supabase = Source unique pour les tournées
    - Table: public.tournees
    - Filtrage par etablissement pour étanchéité multi-institutionnelle
    - SÉCURITÉ: Si institution absent, retourne liste vide pour éviter mélange
    """
    try:
        import logging
        from supabase import create_client

        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

        if not supabase_url or not supabase_key:
            logging.warning("⚠️ Supabase non configuré, retour liste vide")
            return {"tournees": [], "count": 0}

        supabase = create_client(supabase_url, supabase_key)

        # SÉCURITÉ: institution OBLIGATOIRE pour l'étanchéité
        if not institution:
            logging.warning("⚠️ Paramètre institution manquant - retour liste vide pour sécurité")
            return {"tournees": [], "count": 0}

        # VALIDATION: Vérifier que l'institution est valide
        if institution not in INSTITUTION_CLIENT_MAPPING:
            logging.warning(f"⚠️ Institution '{institution}' non reconnue - retour liste vide")
            return {"tournees": [], "count": 0}

        # FILTRAGE PAR INSTITUTION (étanchéité multi-institutionnelle)
        query = supabase.table('tournees').select('*').eq('etablissement', institution)
        logging.info(f"🔒 Filtrage tournées par institution: {institution}")
        
        # Trier par date_debut DESC (plus récente en premier)
        response = query.order('date_debut', desc=True).execute()

        tournees = response.data if response.data else []

        logging.info(f"✅ {len(tournees)} tournées récupérées depuis Supabase (institution: {institution})")

        return {
            "tournees": tournees,
            "count": len(tournees)
        }

    except Exception as e:
        import traceback
        import logging
        error_detail = f"Erreur lors de la récupération des tournées: {str(e)}\n{traceback.format_exc()}"
        logging.error(f"❌ {error_detail}")
        # Retourner liste vide plutôt qu'une erreur pour ne pas bloquer le frontend
        return {"tournees": [], "count": 0, "error": str(e)}


@router.post("/tournees", response_model=Dict[str, Any])
async def create_tournee(tournee: TourneeCreate):
    """
    Crée une nouvelle tournée dans Supabase.

    Body:
        {
            "nom": "Tournée Orford - Janvier 2026",
            "date_debut": "2026-01-15",
            "date_fin": "2026-01-20",
            "status": "planifiee",
            "etablissement": "vincent-dindy",
            "technicien_responsable": "Nicolas",
            "piano_ids": [],
            "notes": "Tournée de janvier",
            "created_by": "nicolas@example.com"
        }

    Response:
        {
            "success": true,
            "tournee_id": "tournee_123456789",
            "message": "Tournée créée avec succès"
        }
    """
    try:
        import logging
        from supabase import create_client
        import time

        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

        if not supabase_url or not supabase_key:
            raise HTTPException(
                status_code=500,
                detail="Configuration Supabase manquante (SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)"
            )

        supabase = create_client(supabase_url, supabase_key)

        # Générer un ID unique pour la tournée
        tournee_id = f"tournee_{int(time.time() * 1000)}"

        # SÉCURITÉ: Valider que l'établissement est valide
        if tournee.etablissement not in INSTITUTION_CLIENT_MAPPING:
            raise HTTPException(
                status_code=400,
                detail=f"Institution '{tournee.etablissement}' non reconnue. Institutions valides: {list(INSTITUTION_CLIENT_MAPPING.keys())}"
            )

        # Préparer les données (etablissement est utilisé pour le filtrage)
        tournee_data = {
            "id": tournee_id,
            "nom": tournee.nom,
            "date_debut": tournee.date_debut,
            "date_fin": tournee.date_fin,
            "status": tournee.status,
            "etablissement": tournee.etablissement,  # Clé de filtrage pour étanchéité multi-institutionnelle
            "technicien_responsable": tournee.technicien_responsable,
            "piano_ids": tournee.piano_ids if tournee.piano_ids else [],  # Passer directement la liste, pas JSON string
            "notes": tournee.notes,
            "created_by": tournee.created_by
        }
        
        logging.info(f"🔒 Création tournée avec établissement: {tournee.etablissement} (client_id: {INSTITUTION_CLIENT_MAPPING.get(tournee.etablissement)})")

        # Insérer dans Supabase
        response = supabase.table('tournees').insert(tournee_data).execute()

        logging.info(f"✅ Tournée créée: {tournee_id}")

        return {
            "success": True,
            "tournee_id": tournee_id,
            "message": "Tournée créée avec succès",
            "data": response.data[0] if response.data else tournee_data
        }

    except Exception as e:
        import traceback
        import logging
        error_detail = f"Erreur lors de la création de la tournée: {str(e)}\n{traceback.format_exc()}"
        logging.error(f"❌ {error_detail}")
        raise HTTPException(status_code=500, detail=error_detail)


@router.patch("/tournees/{tournee_id}", response_model=Dict[str, Any])
async def update_tournee(tournee_id: str, update: TourneeUpdate):
    """
    Met à jour une tournée existante dans Supabase.

    Path params:
        tournee_id: ID de la tournée à modifier

    Body:
        {
            "nom": "Nouveau nom",
            "status": "en_cours",
            "piano_ids": ["ins_abc123", "ins_def456"]
        }

    Response:
        {
            "success": true,
            "message": "Tournée mise à jour avec succès"
        }
    """
    try:
        import logging
        from supabase import create_client

        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

        if not supabase_url or not supabase_key:
            raise HTTPException(
                status_code=500,
                detail="Configuration Supabase manquante"
            )

        supabase = create_client(supabase_url, supabase_key)

        # SÉCURITÉ: Vérifier que la tournée existe et récupérer son établissement
        check_response = supabase.table('tournees').select('id, etablissement').eq('id', tournee_id).execute()

        if not check_response.data:
            logging.error(f"❌ Tournée {tournee_id} non trouvée dans Supabase")
            raise HTTPException(status_code=404, detail=f"Tournée non trouvée: {tournee_id}")
        
        existing_etablissement = check_response.data[0].get('etablissement')
        logging.info(f"🔍 Tournée {tournee_id} trouvée - établissement: {existing_etablissement}")

        # Préparer les données (exclure None)
        update_data = {}
        if update.nom is not None:
            update_data["nom"] = update.nom
        if update.date_debut is not None:
            update_data["date_debut"] = update.date_debut
        if update.date_fin is not None:
            update_data["date_fin"] = update.date_fin
        if update.status is not None:
            update_data["status"] = update.status
        if update.technicien_responsable is not None:
            update_data["technicien_responsable"] = update.technicien_responsable
        if update.technicien_assigne is not None:
            update_data["technicien_assigne"] = update.technicien_assigne
        if update.piano_ids is not None:
            update_data["piano_ids"] = update.piano_ids  # Passer directement la liste
        if update.notes is not None:
            update_data["notes"] = update.notes

        if not update_data:
            raise HTTPException(status_code=400, detail="Aucune donnée à mettre à jour")

        # Mettre à jour dans Supabase
        logging.info(f"🔄 Mise à jour tournée {tournee_id} avec données: {update_data}")
        response = supabase.table('tournees').update(update_data).eq('id', tournee_id).execute()

        logging.info(f"📊 Réponse Supabase update: data={response.data}, count={getattr(response, 'count', None)}")

        # IMPORTANT: Supabase peut retourner data=[] même si l'update réussit
        # On vérifie donc si la tournée existe d'abord (fait ci-dessus)
        if not response.data:
            # Re-fetch pour confirmer que l'update a bien été appliqué
            verify_response = supabase.table('tournees').select('*').eq('id', tournee_id).execute()
            if verify_response.data:
                logging.info(f"✅ Tournée mise à jour (confirmé par re-fetch): {tournee_id}")
                return {
                    "success": True,
                    "message": "Tournée mise à jour avec succès",
                    "data": verify_response.data[0]
                }
            else:
                logging.error(f"❌ Tournée {tournee_id} disparue après update?")
                raise HTTPException(status_code=500, detail="Erreur lors de la vérification de la mise à jour")

        logging.info(f"✅ Tournée mise à jour: {tournee_id}")

        return {
            "success": True,
            "message": "Tournée mise à jour avec succès",
            "data": response.data[0]
        }

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        import logging
        error_detail = f"Erreur lors de la mise à jour de la tournée: {str(e)}\n{traceback.format_exc()}"
        logging.error(f"❌ {error_detail}")
        raise HTTPException(status_code=500, detail=error_detail)


@router.delete("/tournees/{tournee_id}", response_model=Dict[str, Any])
async def delete_tournee(tournee_id: str):
    """
    Supprime une tournée de Supabase.

    Path params:
        tournee_id: ID de la tournée à supprimer

    Response:
        {
            "success": true,
            "message": "Tournée supprimée avec succès"
        }
    """
    try:
        import logging
        from supabase import create_client

        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

        if not supabase_url or not supabase_key:
            raise HTTPException(
                status_code=500,
                detail="Configuration Supabase manquante"
            )

        supabase = create_client(supabase_url, supabase_key)

        # 1. Récupérer la tournée pour obtenir les piano_ids et l'établissement avant suppression
        tournee_response = supabase.table('tournees').select('piano_ids, etablissement').eq('id', tournee_id).execute()

        if not tournee_response.data:
            raise HTTPException(status_code=404, detail="Tournée non trouvée")
        
        tournee_etablissement = tournee_response.data[0].get('etablissement')
        logging.info(f"🔒 Suppression tournée {tournee_id} - établissement: {tournee_etablissement}")

        tournee_data = tournee_response.data[0]
        piano_ids = tournee_data.get('piano_ids', [])

        logging.info(f"🗑️ Suppression de la tournée {tournee_id} avec {len(piano_ids)} pianos associés")

        # 2. Réinitialiser les statuts des pianos associés à 'normal' dans vincent_dindy_piano_updates
        if piano_ids:
            from datetime import datetime
            logging.info(f"   🔄 Réinitialisation de {len(piano_ids)} pianos: {piano_ids}")
            for piano_id in piano_ids:
                try:
                    # Réinitialiser le statut à 'normal' pour chaque piano
                    upsert_data = {
                        'piano_id': piano_id,
                        'status': 'normal',
                        'updated_at': datetime.utcnow().isoformat()
                    }
                    logging.info(f"      🔧 Upsert piano {piano_id} avec data: {upsert_data}")

                    result = supabase.table('vincent_dindy_piano_updates').upsert(upsert_data).execute()

                    logging.info(f"      ✅ Supabase response pour piano {piano_id}: data={result.data}, count={getattr(result, 'count', 'N/A')}")
                except Exception as piano_err:
                    # Ne pas bloquer la suppression si un piano échoue
                    logging.error(f"      ❌ Erreur réinitialisation piano {piano_id}: {piano_err}")
                    import traceback
                    logging.error(traceback.format_exc())
        else:
            logging.info(f"   ℹ️ Aucun piano à réinitialiser (piano_ids est vide)")

        # 3. Supprimer la tournée de Supabase
        response = supabase.table('tournees').delete().eq('id', tournee_id).execute()

        if not response.data:
            raise HTTPException(status_code=404, detail="Tournée non trouvée après vérification")

        logging.info(f"✅ Tournée {tournee_id} supprimée + {len(piano_ids)} pianos réinitialisés")

        return {
            "success": True,
            "message": "Tournée supprimée avec succès",
            "pianos_reset": len(piano_ids)
        }

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        import logging
        error_detail = f"Erreur lors de la suppression de la tournée: {str(e)}\n{traceback.format_exc()}"
        logging.error(f"❌ {error_detail}")
        raise HTTPException(status_code=500, detail=error_detail)


@router.post("/tournees/{tournee_id}/pianos/{gazelle_id}", response_model=Dict[str, Any])
async def add_piano_to_tournee(tournee_id: str, gazelle_id: str):
    """
    Ajoute un piano à une tournée.

    Path params:
        tournee_id: ID de la tournée
        gazelle_id: ID Gazelle du piano (ex: "ins_abc123")

    Response:
        {
            "success": true,
            "message": "Piano ajouté à la tournée",
            "piano_ids": ["ins_abc123", ...]
        }
    """
    try:
        import logging
        from supabase import create_client

        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

        if not supabase_url or not supabase_key:
            raise HTTPException(
                status_code=500,
                detail="Configuration Supabase manquante"
            )

        supabase = create_client(supabase_url, supabase_key)

        # Récupérer la tournée
        response = supabase.table('tournees').select('piano_ids').eq('id', tournee_id).execute()

        if not response.data:
            raise HTTPException(status_code=404, detail="Tournée non trouvée")

        # Parser piano_ids (peut être JSON string ou liste)
        current_piano_ids = response.data[0].get('piano_ids', [])
        if isinstance(current_piano_ids, str):
            current_piano_ids = json.loads(current_piano_ids)

        # Ajouter le piano si pas déjà présent
        if gazelle_id not in current_piano_ids:
            current_piano_ids.append(gazelle_id)

            # Mettre à jour (passer directement la liste)
            update_response = supabase.table('tournees').update({
                'piano_ids': current_piano_ids
            }).eq('id', tournee_id).execute()

            # Mettre à jour le statut du piano à 'proposed' (À faire)
            # pour qu'il apparaisse en jaune dans la tournée
            from datetime import datetime
            supabase.table('vincent_dindy_piano_updates').upsert({
                'piano_id': gazelle_id,
                'status': 'proposed',
                'updated_at': datetime.utcnow().isoformat()
            }).execute()

            logging.info(f"✅ Piano {gazelle_id} ajouté à tournée {tournee_id} + status → 'proposed'")

            return {
                "success": True,
                "message": "Piano ajouté à la tournée",
                "piano_ids": current_piano_ids
            }
        else:
            return {
                "success": True,
                "message": "Piano déjà dans la tournée",
                "piano_ids": current_piano_ids
            }

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        import logging
        error_detail = f"Erreur lors de l'ajout du piano: {str(e)}\n{traceback.format_exc()}"
        logging.error(f"❌ {error_detail}")
        raise HTTPException(status_code=500, detail=error_detail)


@router.delete("/tournees/{tournee_id}/pianos/{gazelle_id}", response_model=Dict[str, Any])
async def remove_piano_from_tournee(tournee_id: str, gazelle_id: str):
    """
    Retire un piano d'une tournée.

    Path params:
        tournee_id: ID de la tournée
        gazelle_id: ID Gazelle du piano

    Response:
        {
            "success": true,
            "message": "Piano retiré de la tournée",
            "piano_ids": [...]
        }
    """
    try:
        import logging
        from supabase import create_client

        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

        if not supabase_url or not supabase_key:
            raise HTTPException(
                status_code=500,
                detail="Configuration Supabase manquante"
            )

        supabase = create_client(supabase_url, supabase_key)

        # Récupérer la tournée
        response = supabase.table('tournees').select('piano_ids').eq('id', tournee_id).execute()

        if not response.data:
            raise HTTPException(status_code=404, detail="Tournée non trouvée")

        # Parser piano_ids
        current_piano_ids = response.data[0].get('piano_ids', [])
        if isinstance(current_piano_ids, str):
            current_piano_ids = json.loads(current_piano_ids)

        # Retirer le piano
        if gazelle_id in current_piano_ids:
            current_piano_ids.remove(gazelle_id)

            # Mettre à jour (passer directement la liste)
            update_response = supabase.table('tournees').update({
                'piano_ids': current_piano_ids
            }).eq('id', tournee_id).execute()

            # Réinitialiser le statut du piano à 'normal'
            # pour qu'il ne soit plus visible dans la tournée
            from datetime import datetime
            supabase.table('vincent_dindy_piano_updates').upsert({
                'piano_id': gazelle_id,
                'status': 'normal',
                'updated_at': datetime.utcnow().isoformat()
            }).execute()

            logging.info(f"✅ Piano {gazelle_id} retiré de tournée {tournee_id} + status → 'normal'")

            return {
                "success": True,
                "message": "Piano retiré de la tournée",
                "piano_ids": current_piano_ids
            }
        else:
            return {
                "success": True,
                "message": "Piano pas dans la tournée",
                "piano_ids": current_piano_ids
            }

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        import logging
        error_detail = f"Erreur lors du retrait du piano: {str(e)}\n{traceback.format_exc()}"
        logging.error(f"❌ {error_detail}")
        raise HTTPException(status_code=500, detail=error_detail)


# ==========================================
# PUSH TO GAZELLE ENDPOINTS
# ==========================================

class PushToGazelleRequest(BaseModel):
    """Modèle pour la requête de push vers Gazelle."""
    piano_ids: Optional[List[str]] = None  # Liste explicite de pianos
    tournee_id: Optional[str] = None       # Filtre par tournée
    technician_id: str = "usr_HcCiFk7o0vZ9xAI0"  # Nick par défaut
    dry_run: bool = False                   # Test sans push réel


@router.post("/push-to-gazelle", response_model=Dict[str, Any])
async def push_to_gazelle(request: PushToGazelleRequest):
    """
    Push manuel de pianos vers Gazelle.

    Processus:
    1. Identifie pianos prêts (completed + work_completed + sync pending/modified/error)
    2. Pour chaque piano:
       - Crée service note via push_technician_service_with_measurements
       - Parse température/humidité automatiquement
       - Crée measurement si détecté
       - Met à jour sync_status dans Supabase
    3. Retourne résumé avec succès/erreurs

    Body:
        {
            "piano_ids": ["ins_abc123", ...],  // Optional
            "tournee_id": "tournee_123",       // Optional
            "technician_id": "usr_xyz",        // Default: Nick
            "dry_run": false                   // Default: false
        }

    Response:
        {
            "success": true,
            "pushed_count": 5,
            "error_count": 1,
            "total_pianos": 6,
            "results": [...],
            "summary": "5/6 pianos pushés avec succès, 1 erreur"
        }
    """
    try:
        from core.gazelle_push_service import GazellePushService
        import logging

        logging.info(f"📤 Push manuel vers Gazelle - piano_ids={request.piano_ids}, tournee_id={request.tournee_id}, dry_run={request.dry_run}")

        service = GazellePushService()

        result = service.push_batch(
            piano_ids=request.piano_ids,
            tournee_id=request.tournee_id,
            technician_id=request.technician_id,
            dry_run=request.dry_run
        )

        logging.info(f"✅ Push terminé: {result['summary']}")

        return result

    except Exception as e:
        import traceback
        import logging
        error_detail = f"Erreur lors du push vers Gazelle: {str(e)}\n{traceback.format_exc()}"
        logging.error(f"❌ {error_detail}")
        raise HTTPException(status_code=500, detail=error_detail)


@router.get("/pianos-ready-for-push", response_model=Dict[str, Any])
async def get_pianos_ready_for_push(
    tournee_id: Optional[str] = None,
    limit: int = 100
):
    """
    Récupère les pianos prêts à être pushés vers Gazelle.

    Critères:
    - status = 'completed'
    - is_work_completed = true
    - sync_status IN ('pending', 'modified', 'error')
    - travail OR observations non NULL

    Query params:
        tournee_id (optional): Filtrer par tournée
        limit (optional): Max pianos à retourner (défaut: 100)

    Response:
        {
            "pianos": [...],
            "count": 5,
            "ready_for_push": true
        }
    """
    try:
        from core.gazelle_push_service import GazellePushService
        import logging

        logging.info(f"🔍 Recherche pianos prêts pour push - tournee_id={tournee_id}, limit={limit}")

        service = GazellePushService()

        pianos = service.get_pianos_ready_for_push(
            tournee_id=tournee_id,
            limit=limit
        )

        logging.info(f"✅ {len(pianos)} pianos prêts pour push")

        return {
            "pianos": pianos,
            "count": len(pianos),
            "ready_for_push": len(pianos) > 0
        }

    except Exception as e:
        import traceback
        import logging
        error_detail = f"Erreur lors de la récupération des pianos prêts: {str(e)}\n{traceback.format_exc()}"
        logging.error(f"❌ {error_detail}")
        # Retourner une liste vide plutôt que de faire échouer l'endpoint
        # (la fonction RPC peut ne pas exister dans Supabase)
        return {
            "pianos": [],
            "count": 0,
            "ready_for_push": False,
            "error": str(e)
        }
