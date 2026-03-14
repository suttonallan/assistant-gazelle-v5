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
import logging
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from core.supabase_storage import SupabaseStorage
from core.gazelle_api_client import GazelleAPIClient

router = APIRouter(prefix="/vincent-dindy", tags=["vincent-dindy"])

# NOTE: VINCENT_DINDY_CLIENT_ID supprimé - Utiliser get_institution_config() depuis api/institutions.py

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
    piano_id: Optional[str] = None  # ID Gazelle du piano (pour push automatique)
    date: str
    report_type: str  # "maintenance", "repair", "inspection", etc.
    description: str
    service_history_notes: Optional[str] = None  # Notes envoyées à Gazelle via serviceHistoryNotes
    items_used: Optional[List[Dict[str, Any]]] = None
    hours_worked: Optional[float] = None
    institution: Optional[str] = "vincent-dindy"  # Institution (pour routing modulaire)


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
async def get_pianos(include_inactive: bool = False):
    """
    Récupère tous les pianos depuis Gazelle API.

    Args:
        include_inactive: Si True, inclut les pianos avec tag "non" (masqués par défaut)

    Architecture V7:
    - Gazelle API = Source unique de vérité (tags inclus)
    - Tag "non" dans Gazelle = piano masqué de l'inventaire/tournées
    - Filtre par défaut = masque les pianos avec tag "non"
    - Supabase = Modifications dynamiques (status, notes, etc.)
    """
    try:
        # Charger client_id depuis Supabase institutions
        from api.institutions import get_institution_config
        try:
            config = get_institution_config("vincent-dindy")
            client_id = config.get('gazelle_client_id')
            logging.info(f"✅ Slug reçu: 'vincent-dindy' | Config trouvée: Oui (client_id: {client_id})")
        except Exception as e:
            logging.error(f"❌ Slug reçu: 'vincent-dindy' | Config trouvée: Non | Erreur: {e}")
            raise HTTPException(status_code=500, detail=f"Configuration institution non trouvée: {str(e)}")

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

        # 2. Charger les modifications depuis Supabase (flags + overlays) filtrées par vincent-dindy
        storage = get_supabase_storage()
        supabase_updates = storage.get_all_piano_updates(institution_slug='vincent-dindy')

        logging.info(f"☁️  {len(supabase_updates)} modifications Supabase trouvées pour vincent-dindy")

        # 2b. Charger les dernières validations depuis vdi_service_history
        validation_statuses = {}
        try:
            r = _sh_table_request(
                params="institution_slug=eq.vincent-dindy&status=in.(validated,pushed)&select=piano_id,validated_at&order=validated_at.desc"
            )
            if r.status_code == 200:
                for entry in r.json():
                    pid = entry.get('piano_id')
                    if pid and pid not in validation_statuses:
                        validation_statuses[pid] = entry['validated_at']
        except Exception as e:
            logging.warning(f"⚠️ Chargement validation statuses échoué: {e}")

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

            # Filtrage: Par défaut, masquer les pianos avec tag "non"
            if not include_inactive and has_non_tag:
                continue  # Ignorer les pianos marqués "non"

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
                "is_hidden": updates.get('is_hidden', False),  # Masquer de l'inventaire (False par défaut)
                "gazelleStatus": gz_piano.get('status', 'UNKNOWN'),  # Status Gazelle
                "updated_at": updates.get('updated_at', ''),  # Dernière modification des notes
                "last_validated_at": validation_statuses.get(gz_id, ''),  # Dernière validation par Nicolas
                "service_status": updates.get('service_status', None),  # Lifecycle tournée: None → validated → pushed
            }

            pianos.append(piano)

        logging.info(f"✅ {len(pianos)} pianos retournés (include_inactive={include_inactive})")

        return {
            "pianos": pianos,
            "count": len(pianos),
            "source": "gazelle",
            "clientId": client_id
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

        # Garde : empêcher la modification de travail si le piano est validé ou poussé
        # Exception : effacer aFaire (valeur vide) est toujours permis — c'est une action de gestion
        is_clearing_a_faire = update.aFaire is not None and update.aFaire.strip() == ''
        if update.travail is not None or (update.aFaire is not None and not is_clearing_a_faire):
            existing = storage.get_all_piano_updates(institution_slug='vincent-dindy')
            piano_state = existing.get(piano_id, {})
            if piano_state.get('service_status') in ('validated', 'pushed'):
                raise HTTPException(
                    status_code=400,
                    detail=f"Piano {piano_id} est en état '{piano_state['service_status']}' — lecture seule jusqu'à fin de tournée."
                )

        # Convertir les champs camelCase vers snake_case pour Supabase
        update_dict = update.dict(exclude_none=True)
        update_data = {}
        for key, value in update_dict.items():
            if key == 'aFaire':
                update_data['a_faire'] = value
            elif key == 'dernierAccord':
                update_data['dernier_accord'] = value
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

        # Si statut passe à validated, enregistrer validated_at
        if update_data.get('status') == 'validated':
            if 'validated_at' not in update_data:
                from datetime import datetime
                update_data['validated_at'] = datetime.now().isoformat()

        # Si piano était pushed et on modifie travail/observations → sync_status = modified
        # (géré par trigger SQL auto_mark_sync_modified)

        success = storage.update_piano(piano_id, update_data, institution_slug='vincent-dindy')

        if not success:
            # Retry sans les colonnes optionnelles qui pourraient ne pas exister en base
            optional_cols = ['completed_at', 'validated_at']
            retry_data = {k: v for k, v in update_data.items() if k not in optional_cols}
            if retry_data != update_data:
                print(f"⚠️ Retry sans colonnes optionnelles: {[c for c in optional_cols if c in update_data]}")
                success = storage.update_piano(piano_id, retry_data, institution_slug='vincent-dindy')
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
                elif key == "isHidden":
                    snake_case_update["is_hidden"] = value
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
    Soumet un rapport de technicien et le pousse vers Gazelle (système modulaire multi-institutions).

    Workflow:
    1. Sauvegarde dans Supabase (backup fiable)
    2. Si piano_id fourni → Push automatique vers Gazelle via completeEvent
    3. Retour du résultat avec statut Gazelle

    Le système est modulaire et supporte plusieurs institutions via le champ 'institution'.
    """
    try:
        storage = get_supabase_storage()
        report_data = report.dict()

        # Log pour diagnostic
        logging.info(f"📤 Réception rapport: {list(report_data.keys())}")
        logging.info(f"   technician_name: {report_data.get('technician_name')}")
        logging.info(f"   piano_id: {report_data.get('piano_id')}")
        logging.info(f"   institution: {report_data.get('institution')}")
        logging.info(f"   date: {report_data.get('date')}")
        logging.info(f"   report_type: {report_data.get('report_type')}")

        # 1. Sauvegarder dans Supabase (backup fiable)
        saved_report = storage.add_report(report_data)
        logging.info(f"✅ Rapport sauvegardé dans Supabase: {saved_report['id']}")

        result = {
            "success": True,
            "message": "Rapport sauvegardé dans Supabase",
            "report_id": saved_report["id"],
            "submitted_at": saved_report["submitted_at"],
            "status": saved_report["status"],
            "gazelle_push": None  # Rempli si push vers Gazelle
        }

        # 2. Détection automatique d'alertes d'humidité (3 institutions uniquement)
        institution = report_data.get('institution', 'vincent-dindy')
        monitored_institutions = ['vincent-dindy', 'place-des-arts', 'orford']

        if institution in monitored_institutions:
            try:
                from core.humidity_alert_detector import detect_humidity_issue, create_humidity_alert

                service_notes = report_data.get('service_history_notes') or report_data.get('description', '')
                detection = detect_humidity_issue(service_notes)

                if detection:
                    logging.info(f"🚨 Problème d'humidité détecté: {detection['alert_type']}")

                    # Créer l'alerte dans Supabase si piano_id disponible
                    piano_id_for_alert = report_data.get('piano_id')
                    if piano_id_for_alert:
                        alert_data = create_humidity_alert(
                            piano_id=piano_id_for_alert,
                            client_name=report_data.get('client_name', institution),
                            notes=service_notes,
                            detection_result=detection
                        )

                        # Sauvegarder l'alerte
                        success = storage.update_data(
                            table_name="humidity_alerts_active",
                            data=alert_data,
                            id_field="piano_id",
                            upsert=True
                        )

                        if success:
                            logging.info(f"✅ Alerte d'humidité créée pour piano {piano_id_for_alert}")
                            result['humidity_alert_created'] = True
                            result['alert_type'] = detection['alert_type']
                        else:
                            logging.warning(f"⚠️  Échec création alerte d'humidité")
                    else:
                        logging.info(f"ℹ️  Problème détecté mais pas de piano_id pour créer l'alerte")

            except Exception as e:
                logging.error(f"⚠️  Erreur détection alerte humidité: {e}")
                # Ne pas bloquer la sauvegarde du rapport

        # 3. Push automatique vers Gazelle si piano_id fourni
        piano_id = report_data.get('piano_id')
        if piano_id:
            try:
                from core.service_completion_bridge import complete_service_session

                # Utiliser service_history_notes si fourni, sinon fallback sur description
                service_notes = report_data.get('service_history_notes') or report_data.get('description', '')

                # Mapper report_type vers service_type Gazelle
                service_type_mapping = {
                    'maintenance': 'TUNING',
                    'repair': 'REPAIR',
                    'inspection': 'INSPECTION'
                }
                service_type = service_type_mapping.get(
                    report_data.get('report_type', 'maintenance').lower(),
                    'TUNING'
                )

                # Push vers Gazelle avec le système modulaire
                logging.info(f"🚀 Push vers Gazelle via complete_service_session...")
                gazelle_result = complete_service_session(
                    piano_id=piano_id,
                    service_notes=service_notes,
                    institution=report_data.get('institution', 'vincent-dindy'),
                    technician_name=report_data.get('technician_name'),
                    client_id=report_data.get('client_id'),
                    service_type=service_type,
                    event_date=report_data.get('date')
                )

                if gazelle_result['success']:
                    result['gazelle_push'] = {
                        'success': True,
                        'event_id': gazelle_result.get('gazelle_event_id'),
                        'timeline_created': gazelle_result.get('service_note_created'),
                        'last_tuned_updated': gazelle_result.get('last_tuned_updated')
                    }
                    result['message'] = "Rapport sauvegardé et poussé vers Gazelle avec succès"
                    logging.info(f"✅ Push Gazelle réussi: Event {gazelle_result.get('gazelle_event_id')}")
                else:
                    result['gazelle_push'] = {
                        'success': False,
                        'error': gazelle_result.get('error')
                    }
                    logging.warning(f"⚠️  Push Gazelle échoué: {gazelle_result.get('error')}")
                    result['message'] = f"Rapport sauvegardé mais push Gazelle échoué: {gazelle_result.get('error')}"

            except Exception as e:
                # Log l'erreur mais ne pas fail la requête (rapport déjà sauvegardé)
                error_msg = str(e)
                logging.error(f"❌ Erreur push Gazelle: {error_msg}")
                import traceback
                logging.error(traceback.format_exc())

                result['gazelle_push'] = {
                    'success': False,
                    'error': error_msg
                }
                result['message'] = f"Rapport sauvegardé mais push Gazelle échoué: {error_msg}"

        return result

    except ValueError as e:
        # Erreur de validation (champs manquants, format incorrect, etc.)
        error_msg = str(e)
        logging.error(f"❌ Erreur de validation lors de la sauvegarde du rapport: {error_msg}")
        raise HTTPException(
            status_code=400,
            detail=f"Erreur de validation: {error_msg}"
        )
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        error_msg = str(e)
        logging.error(f"❌ Erreur lors de la sauvegarde du rapport: {error_msg}\n{error_trace}")
        
        # Retourner un message plus informatif selon le type d'erreur
        if "Configuration manquante" in error_msg or "SUPABASE" in error_msg.upper():
            detail_msg = f"Configuration manquante: {error_msg}. Vérifiez SUPABASE_URL et SUPABASE_KEY."
        elif "Champs obligatoires manquants" in error_msg:
            detail_msg = f"Données incomplètes: {error_msg}"
        elif "Erreur Supabase" in error_msg or "Supabase" in error_msg:
            detail_msg = f"Erreur de base de données: {error_msg}. Vérifiez les logs du serveur pour plus de détails."
        else:
            detail_msg = f"Erreur lors de la sauvegarde: {error_msg}"
        
        raise HTTPException(status_code=500, detail=detail_msg)


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
        all_updates = storage.get_all_piano_updates(institution_slug='vincent-dindy')

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


@router.get("/pianos/{piano_id}/history", response_model=Dict[str, Any])
async def get_piano_history(piano_id: str, limit: int = 20):
    """
    Récupère l'historique de service d'un piano depuis gazelle_timeline_entries.

    Args:
        piano_id: ID du piano (gazelleId ou ID local)
        limit: Nombre maximum d'entrées à retourner (défaut: 20)

    Returns:
        {
            "history": [
                {"date": "2026-01-15", "text": "Accord effectué...", "entry_type": "SERVICE"},
                ...
            ],
            "piano_id": "ins_xxx",
            "count": 5
        }
    """
    import requests

    try:
        storage = get_supabase_storage()

        # Requête sur gazelle_timeline_entries
        # Le champ correct est piano_id (pas entity_id)
        # On cherche aussi dans external_id pour les anciens formats
        url = f"{storage.api_url}/gazelle_timeline_entries"
        url += f"?or=(piano_id.eq.{piano_id},external_id.ilike.*{piano_id}*)"
        url += f"&order=occurred_at.desc.nullsfirst,created_at.desc"
        url += f"&limit={limit}"

        print(f"🔍 Requête historique piano: {url}")
        response = requests.get(url, headers=storage._get_headers())

        if response.status_code != 200:
            print(f"⚠️ Erreur timeline entries: {response.status_code} - {response.text[:200]}")
            return {"history": [], "piano_id": piano_id, "count": 0}

        entries = response.json() or []

        # Formatter les entrées pour le frontend
        history = []
        for entry in entries:
            # Extraire la date (occurred_at ou created_at)
            date_str = entry.get('occurred_at') or entry.get('created_at') or ''
            if date_str:
                try:
                    # Parser et formater la date
                    from datetime import datetime
                    dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                    date_formatted = dt.strftime('%Y-%m-%d')
                except:
                    date_formatted = date_str[:10] if len(date_str) >= 10 else date_str
            else:
                date_formatted = ''

            # Extraire le texte (description, title, ou summary)
            text = entry.get('description') or entry.get('title') or entry.get('summary') or ''

            # Type d'entrée
            entry_type = entry.get('entry_type') or entry.get('type') or 'NOTE'

            if text.strip():  # Ne pas inclure les entrées vides
                history.append({
                    "date": date_formatted,
                    "text": text.strip(),
                    "entry_type": entry_type,
                    "technician_id": entry.get('technician_id') or entry.get('user_id'),
                })

        return {
            "history": history,
            "piano_id": piano_id,
            "count": len(history)
        }

    except Exception as e:
        print(f"❌ Erreur get_piano_history: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Erreur lors de la récupération de l'historique: {str(e)}")


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
    etablissement: str = "vincent-dindy"
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
async def get_tournees():
    """
    Récupère toutes les tournées depuis Supabase.

    Architecture V7:
    - Supabase = Source unique pour les tournées
    - Table: public.tournees
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

        # Requête vers la table tournees
        response = supabase.table('tournees').select('*').execute()

        tournees = response.data if response.data else []

        logging.info(f"✅ {len(tournees)} tournées récupérées depuis Supabase")

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

        # Préparer les données
        tournee_data = {
            "id": tournee_id,
            "nom": tournee.nom,
            "date_debut": tournee.date_debut,
            "date_fin": tournee.date_fin,
            "status": tournee.status,
            "etablissement": tournee.etablissement,
            "technicien_responsable": tournee.technicien_responsable,
            "piano_ids": tournee.piano_ids if tournee.piano_ids else [],  # Passer directement la liste, pas JSON string
            "notes": tournee.notes,
            "created_by": tournee.created_by
        }

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

        # Debug: vérifier si la tournée existe AVANT de faire l'update
        check_response = supabase.table('tournees').select('id').eq('id', tournee_id).execute()

        logging.info(f"🔍 Vérification tournée {tournee_id}: {check_response.data}")

        if not check_response.data:
            logging.error(f"❌ Tournée {tournee_id} non trouvée dans Supabase")
            raise HTTPException(status_code=404, detail=f"Tournée non trouvée: {tournee_id}")

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

        # Supprimer de Supabase
        response = supabase.table('tournees').delete().eq('id', tournee_id).execute()

        if not response.data:
            raise HTTPException(status_code=404, detail="Tournée non trouvée")

        logging.info(f"✅ Tournée supprimée: {tournee_id}")

        return {
            "success": True,
            "message": "Tournée supprimée avec succès"
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

            logging.info(f"✅ Piano {gazelle_id} ajouté à tournée {tournee_id}")

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

            logging.info(f"✅ Piano {gazelle_id} retiré de tournée {tournee_id}")

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


@router.post("/push-to-gazelle", response_model=Dict[str, Any], deprecated=True)
async def push_to_gazelle(request: PushToGazelleRequest):
    """
    ⚠️ DÉPRÉCIÉ — Utiliser POST /service-records/{institution}/push à la place.
    Ce endpoint reste actif pour compatibilité mais sera supprimé.

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


# ==========================================
# SERVICE HISTORY — Historique des validations
# ==========================================

class ServiceHistoryValidateRequest(BaseModel):
    piano_ids: List[str]
    validated_by: str = "Unknown"

class ServiceHistoryEditRequest(BaseModel):
    travail: Optional[str] = None
    a_faire: Optional[str] = None
    observations: Optional[str] = None

class ServiceHistoryPushRequest(BaseModel):
    technician_id: str = "usr_HcCiFk7o0vZ9xAI0"
    dry_run: bool = False
    skip_gazelle: bool = False  # Marquer pushed sans écrire dans Gazelle


def _sh_table_request(method: str = "GET", params: str = "",
                      json_body=None, prefer: str = "return=representation"):
    """Requête REST Supabase vers vdi_service_history."""
    sb = get_supabase_storage()
    url = f"{sb.api_url}/vdi_service_history?{params}" if params else f"{sb.api_url}/vdi_service_history"
    headers = {
        "apikey": sb.supabase_key,
        "Authorization": f"Bearer {sb.supabase_key}",
        "Content-Type": "application/json",
        "Prefer": prefer,
    }
    import requests as _req
    if method == "GET":
        return _req.get(url, headers=headers)
    elif method == "POST":
        return _req.post(url, headers=headers, json=json_body)
    elif method == "PATCH":
        return _req.patch(url, headers=headers, json=json_body)
    elif method == "DELETE":
        return _req.delete(url, headers=headers)
    raise ValueError(f"Méthode non supportée: {method}")


@router.get("/service-history", response_model=List[Dict[str, Any]])
async def get_service_history(limit: int = 100, include_imported: bool = False):
    """Retourne l'historique des services validés/poussés, anti-chronologique."""
    status_filter = "" if include_imported else "&status=in.(validated,pushed,error)"
    r = _sh_table_request(params=f"select=*&order=validated_at.desc&limit={limit}{status_filter}")
    if r.status_code != 200:
        raise HTTPException(status_code=500, detail=r.text)
    return r.json()


@router.post("/service-history/validate", response_model=Dict[str, Any])
async def validate_service_history(body: ServiceHistoryValidateRequest):
    """
    Valide un ou plusieurs pianos :
    1. Archive les notes dans vdi_service_history
    2. Nettoie le piano (ardoise propre pour le technicien)
    """
    storage = get_supabase_storage()
    api_client = get_api_client()

    # Charger les données Supabase pour ces pianos
    all_updates = storage.get_all_piano_updates(institution_slug='vincent-dindy')

    # Charger les données Gazelle pour le contexte (local, make, model, etc.)
    piano_context = {}
    try:
        from api.institutions import get_institution_config
        config = get_institution_config("vincent-dindy")
        client_id = config.get('gazelle_client_id')
        if api_client and client_id:
            gz_pianos = api_client.get_pianos_by_client(client_id) or []
            for gz in gz_pianos:
                gz_id = gz.get('gazelleId', '')
                piano_context[gz_id] = {
                    'local': gz.get('location', ''),
                    'name': f"{gz.get('make', '')} {gz.get('model', '')}".strip(),
                    'serie': gz.get('serialNumber', ''),
                    'dernierAccord': gz.get('calculatedLastService', ''),
                }
    except Exception as e:
        logging.warning(f"⚠️ Impossible de charger le contexte Gazelle: {e}")

    created = []
    for piano_id in body.piano_ids:
        updates = all_updates.get(piano_id, {})
        ctx = piano_context.get(piano_id, {})

        travail = updates.get('travail', '')
        if not travail.strip():
            continue  # Pas de notes à archiver

        # Déterminer la date du service
        service_date = None
        dernier = ctx.get('dernierAccord', '')
        if dernier:
            try:
                service_date = dernier[:10]  # ISO date part
            except Exception:
                pass

        entry = {
            "piano_id": piano_id,
            "institution_slug": "vincent-dindy",
            "piano_local": ctx.get('local', updates.get('local', '')),
            "piano_name": ctx.get('name', ''),
            "piano_serie": ctx.get('serie', ''),
            "travail": travail,
            "a_faire": updates.get('a_faire', ''),
            "observations": updates.get('observations', ''),
            "service_date": service_date,
            "status": "validated",
            "validated_by": body.validated_by,
            "validated_at": datetime.utcnow().isoformat(),
        }

        # INSERT dans vdi_service_history
        r = _sh_table_request(method="POST", json_body=entry)
        if r.status_code not in (200, 201):
            logging.error(f"❌ Erreur insert history pour {piano_id}: {r.text}")
            continue

        created_entries = r.json()
        if created_entries:
            created.append(created_entries[0] if isinstance(created_entries, list) else created_entries)

        # Marquer le piano comme validé (notes RESTENT visibles jusqu'à fin de tournée)
        storage.update_piano(piano_id, {
            'service_status': 'validated',
        }, institution_slug='vincent-dindy')

    return {
        "success": True,
        "validated_count": len(created),
        "entries": created,
    }


@router.put("/service-history/{entry_id}", response_model=Dict[str, Any])
async def edit_service_history(entry_id: str, body: ServiceHistoryEditRequest):
    """Modifier une entrée validée (pas encore poussée)."""
    # Vérifier que l'entrée existe et est modifiable
    r = _sh_table_request(params=f"id=eq.{entry_id}&select=status")
    if r.status_code != 200 or not r.json():
        raise HTTPException(status_code=404, detail="Entrée non trouvée")
    entry = r.json()[0]
    if entry.get('status') == 'pushed':
        raise HTTPException(status_code=400, detail="Impossible de modifier une entrée déjà poussée")

    update_data = {}
    if body.travail is not None:
        update_data['travail'] = body.travail
    if body.a_faire is not None:
        update_data['a_faire'] = body.a_faire
    if body.observations is not None:
        update_data['observations'] = body.observations

    if not update_data:
        return {"edited": False, "message": "Aucun champ à modifier"}

    r = _sh_table_request(method="PATCH", params=f"id=eq.{entry_id}",
                          json_body=update_data)
    if r.status_code not in (200, 204):
        raise HTTPException(status_code=500, detail=r.text)

    return {"edited": True, "entry_id": entry_id}


@router.post("/service-history/push-tournee", response_model=Dict[str, Any], deprecated=True)
async def push_tournee(body: ServiceHistoryPushRequest):
    """
    ⚠️ DÉPRÉCIÉ — Utiliser POST /service-records/{institution}/push à la place.
    Pousse toutes les entrées validées vers Gazelle en UN SEUL rendez-vous multi-pianos.
    Pattern identique au bundle-push VDI :
    1. Activer pianos INACTIVE → ACTIVE
    2. Créer un seul événement avec tous les pianos
    3. Compléter avec serviceHistoryNotes individuelles par piano
    4. Remettre pianos INACTIVE
    5. Marquer les entrées comme 'pushed'
    """
    from core.timezone_utils import MONTREAL_TZ
    from collections import defaultdict

    # 1. Récupérer les entrées validées
    r = _sh_table_request(params="status=eq.validated&select=*&order=piano_local.asc")
    if r.status_code != 200:
        raise HTTPException(status_code=500, detail=r.text)
    validated = r.json()

    if not validated:
        return {"success": True, "pushed_count": 0, "message": "Aucune entrée validée à pousser"}

    # Grouper par piano_id
    piano_entries = defaultdict(list)
    for entry in validated:
        piano_entries[entry['piano_id']].append(entry)
    piano_ids = list(piano_entries.keys())

    if body.dry_run:
        return {
            "success": True,
            "dry_run": True,
            "would_push": len(validated),
            "pianos_count": len(piano_ids),
            "pianos": [{"piano_id": v["piano_id"], "local": v.get("piano_local", "")} for v in validated]
        }

    # Mode simulation : marquer pushed sans écrire dans Gazelle
    if body.skip_gazelle:
        logging.info(f"⏭️ skip_gazelle: marquage {len(validated)} entrées comme pushed (sans Gazelle)")
        storage = get_supabase_storage()
        for entry in validated:
            _sh_table_request(
                method="PATCH",
                params=f"id=eq.{entry['id']}",
                json_body={
                    "status": "pushed",
                    "pushed_at": datetime.utcnow().isoformat(),
                    "gazelle_event_id": "SKIPPED",
                }
            )
        # Marquer les pianos comme 'pushed'
        for pid in piano_ids:
            storage.update_piano(pid, {'service_status': 'pushed'}, institution_slug='vincent-dindy')
        return {
            "success": True,
            "pushed_count": len(validated),
            "pianos_count": len(piano_ids),
            "skip_gazelle": True,
            "summary": f"{len(validated)} entrée(s) marquée(s) pushed (Gazelle ignoré)"
        }

    api_client = get_api_client()
    if not api_client:
        raise HTTPException(status_code=500, detail="Client API Gazelle non disponible")

    try:
        # 2. Récupérer le client_id VDI
        from api.institutions import get_institution_config
        config = get_institution_config("vincent-dindy")
        client_id = config.get("gazelle_client_id")

        logging.info(f"🎹 Push tournée: {len(validated)} entrées pour {len(piano_ids)} pianos")

        # 3. Gymnastique: Réactiver les pianos INACTIVE → ACTIVE
        activated_pianos = []
        for pid in piano_ids:
            try:
                status_q = """
                query GetPianoStatus($pianoId: String!) {
                    piano(id: $pianoId) { id status }
                }
                """
                sr = api_client._execute_query(status_q, {"pianoId": pid})
                current_status = sr.get("data", {}).get("piano", {}).get("status")
                if current_status == "INACTIVE":
                    update_m = """
                    mutation ActivatePiano($pianoId: String!, $input: PrivatePianoInput!) {
                        updatePiano(id: $pianoId, input: $input) {
                            piano { id status }
                            mutationErrors { fieldName messages }
                        }
                    }
                    """
                    api_client._execute_query(update_m, {"pianoId": pid, "input": {"status": "ACTIVE"}})
                    activated_pianos.append(pid)
                    logging.info(f"   ✅ Piano {pid} → ACTIVE")
            except Exception as e:
                logging.warning(f"   ⚠️ Activation piano {pid}: {e}")

        # 4. Créer UN SEUL événement multi-pianos
        event_date = datetime.now(MONTREAL_TZ).isoformat()
        pianos_input = [{"pianoId": pid, "isTuning": True} for pid in piano_ids]

        # Texte combiné pour le champ notes
        combined_lines = []
        for pid, entries in piano_entries.items():
            local = entries[0].get('piano_local', pid)
            for e in entries:
                combined_lines.append(f"🎹 {local} : {e.get('travail', '')}")
        combined_text = "\n".join(combined_lines)

        create_mutation = """
        mutation CreateBundleEvent($input: PrivateEventInput!) {
            createEvent(input: $input) {
                event { id title start type status }
                mutationErrors { fieldName messages }
            }
        }
        """
        event_input = {
            "title": f"VDI Accord collectif ({len(piano_ids)} pianos)",
            "start": event_date,
            "duration": 60 * len(piano_ids),
            "type": "APPOINTMENT",
            "notes": combined_text,
            "pianos": pianos_input,
            "userId": body.technician_id,
        }
        if client_id:
            event_input["clientId"] = client_id

        create_result = api_client._execute_query(create_mutation, {"input": event_input})
        create_data = create_result.get("data", {}).get("createEvent", {})
        event = create_data.get("event")
        if not event:
            errors = create_data.get("mutationErrors", [])
            raise Exception(f"Erreur createEvent: {errors}")

        event_id = event["id"]
        logging.info(f"   ✅ Événement créé: {event_id}")

        # 5. Compléter avec serviceHistoryNotes individuelles par piano
        service_notes = []
        for pid, entries in piano_entries.items():
            lines = [e.get('travail', '') for e in entries if e.get('travail')]
            service_notes.append({"pianoId": pid, "notes": "\n".join(lines)})

        complete_mutation = """
        mutation CompleteBundleEvent($eventId: String!, $input: PrivateCompleteEventInput!) {
            completeEvent(eventId: $eventId, input: $input) {
                event { id status }
                mutationErrors { fieldName messages }
            }
        }
        """
        complete_input = {
            "resultType": "COMPLETE",
            "serviceHistoryNotes": service_notes,
        }
        api_client._execute_query(complete_mutation, {"eventId": event_id, "input": complete_input})
        logging.info(f"   ✅ Événement complété avec {len(service_notes)} notes d'historique")

        # 6. Remettre les pianos en INACTIVE
        for pid in activated_pianos:
            try:
                deact_m = """
                mutation DeactivatePiano($pianoId: String!, $input: PrivatePianoInput!) {
                    updatePiano(id: $pianoId, input: $input) {
                        piano { id status }
                        mutationErrors { fieldName messages }
                    }
                }
                """
                api_client._execute_query(deact_m, {"pianoId": pid, "input": {"status": "INACTIVE"}})
                logging.info(f"   ✅ Piano {pid} → INACTIVE")
            except Exception as e:
                logging.warning(f"   ⚠️ Désactivation piano {pid}: {e}")

        # 7. Marquer toutes les entrées comme 'pushed'
        for entry in validated:
            _sh_table_request(
                method="PATCH",
                params=f"id=eq.{entry['id']}",
                json_body={
                    "status": "pushed",
                    "pushed_at": datetime.utcnow().isoformat(),
                    "gazelle_event_id": event_id,
                }
            )

        # 8. Marquer les pianos comme 'pushed' (notes restent visibles jusqu'à fin de tournée)
        storage = get_supabase_storage()
        for pid in piano_ids:
            storage.update_piano(pid, {'service_status': 'pushed'}, institution_slug='vincent-dindy')

        return {
            "success": True,
            "event_id": event_id,
            "pushed_count": len(validated),
            "pianos_count": len(piano_ids),
            "activated_then_deactivated": activated_pianos,
            "summary": f"{len(validated)} entrée(s) pour {len(piano_ids)} piano(s) → 1 rendez-vous Gazelle"
        }

    except Exception as e:
        logging.error(f"❌ Push tournée erreur: {e}")
        # Marquer les entrées en erreur
        for entry in validated:
            _sh_table_request(
                method="PATCH",
                params=f"id=eq.{entry['id']}",
                json_body={"status": "error", "push_error": str(e)}
            )
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================
# TOURNÉE TERMINÉE — Nettoyage des fiches pianos
# ==========================================

@router.post("/service-history/tournee-terminee", response_model=Dict[str, Any])
async def tournee_terminee(institution_slug: str = "vincent-dindy"):
    """
    Nettoyage complet après une tournée :
    1. Vide le champ 'travail' des overlays legacy (vincent_dindy_piano_updates)
    2. Marque les fiches draft/completed orphelines comme 'abandoned'
    3. Remet service_status/is_work_completed à zéro sur les overlays
    """
    storage = get_supabase_storage()
    all_updates = storage.get_all_piano_updates(institution_slug=institution_slug)

    # 1. Nettoyer les overlays legacy qui ont du travail résiduel
    cleaned_overlays = 0
    for piano_id, data in all_updates.items():
        needs_clean = False
        clean_data = {}
        if data.get('travail', '').strip():
            clean_data['travail'] = ''
            needs_clean = True
        if data.get('service_status'):
            clean_data['service_status'] = None
            needs_clean = True
        if data.get('is_work_completed'):
            clean_data['is_work_completed'] = False
            needs_clean = True
        if needs_clean:
            storage.update_piano(piano_id, clean_data, institution_slug=institution_slug)
            cleaned_overlays += 1

    # 2. Marquer les fiches draft/completed orphelines comme 'abandoned'
    sr_cleaned = 0
    try:
        from supabase import create_client as _create_sb
        sb = _create_sb(
            os.getenv("SUPABASE_URL"),
            os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        )
        orphan_resp = (
            sb.table("piano_service_records")
            .select("id,piano_id,status")
            .eq("institution_slug", institution_slug)
            .in_("status", ["draft", "completed"])
            .execute()
        )
        from datetime import datetime
        now = datetime.utcnow().isoformat()
        for rec in (orphan_resp.data or []):
            sb.table("piano_service_records").update({
                "status": "abandoned",
                "updated_at": now
            }).eq("id", rec["id"]).execute()
            sr_cleaned += 1
        if sr_cleaned:
            logging.info(f"🧹 {sr_cleaned} fiche(s) de service orpheline(s) abandonnées")
    except Exception as e:
        logging.warning(f"⚠️ Nettoyage fiches de service: {e}")

    logging.info(f"🧹 Tournée terminée: {cleaned_overlays} overlay(s) nettoyé(s), {sr_cleaned} fiche(s) abandonnée(s)")

    return {
        "success": True,
        "cleaned_overlays": cleaned_overlays,
        "cleaned_service_records": sr_cleaned,
        "total_cleaned": cleaned_overlays + sr_cleaned,
    }


# ==========================================
# TIMELINE / HISTORIQUE D'ENTRETIEN
# ==========================================

_timeline_cache = {}  # { client_id: { "entries": [...], "fetched_at": datetime } }
_TIMELINE_CACHE_TTL = 300  # 5 minutes

@router.get("/pianos/{piano_id}/timeline", response_model=Dict[str, Any])
async def get_piano_timeline(piano_id: str, limit: int = 50):
    """
    Récupère l'historique complet d'entretien d'un piano.

    Fusionne 2 sources :
    1. Gazelle API — allTimelineEntries filtré par clientId VDI + piano.id local
       (cache 5 min pour éviter 34+ appels API par clic)
    2. Supabase — vdi_service_history (services validés/poussés localement)

    NOTE: Le filtre pianoId de allTimelineEntries ne fonctionne pas (bug Gazelle).
    On filtre donc par clientId (institution) puis localement par piano.id.
    """
    try:
        api_client = get_api_client()
        gazelle_entries = []

        if api_client:
            # Charger le clientId de l'institution
            from api.institutions import get_institution_config
            config = get_institution_config("vincent-dindy")
            client_id = config.get('gazelle_client_id')

            # NOTE: Le filtre pianoId de allTimelineEntries ne fonctionne pas (bug Gazelle).
            # On charge TOUTES les entrées du client (cache 5 min) puis filtre par piano.

            # Vérifier le cache
            cached = _timeline_cache.get(client_id)
            now = datetime.utcnow()
            if cached and (now - cached["fetched_at"]).total_seconds() < _TIMELINE_CACHE_TTL:
                all_client_entries = cached["entries"]
                logging.info(f"📋 Cache timeline hit ({len(all_client_entries)} entrées)")
            else:
                # Paginer toutes les entrées du client
                all_client_entries = []
                query = """
                query GetClientTimeline($clientId: String!, $cursor: String) {
                    allTimelineEntries(first: 100, clientId: $clientId, after: $cursor) {
                        edges {
                            node {
                                id
                                occurredAt
                                type
                                summary
                                comment
                                piano { id }
                                user { id firstName lastName }
                                invoice { id number }
                            }
                        }
                        pageInfo { hasNextPage endCursor }
                    }
                }
                """
                try:
                    cursor = None
                    for _ in range(50):  # ~5000 entries max
                        variables = {"clientId": client_id}
                        if cursor:
                            variables["cursor"] = cursor
                        result = api_client._execute_query(query, variables)
                        data = result.get("data", {}).get("allTimelineEntries", {})
                        edges = data.get("edges", [])

                        for edge in edges:
                            node = edge.get("node", {})
                            if node.get("type") == "SYSTEM_MESSAGE":
                                continue
                            entry_piano = node.get("piano") or {}
                            pid = entry_piano.get("id")
                            if not pid:
                                continue
                            user = node.get("user") or {}
                            user_name = f"{user.get('firstName', '')} {user.get('lastName', '')}".strip() or None
                            all_client_entries.append({
                                "source": "gazelle",
                                "piano_id": pid,
                                "id": node.get("id"),
                                "date": node.get("occurredAt"),
                                "type": node.get("type"),
                                "summary": node.get("summary") or "",
                                "comment": node.get("comment") or "",
                                "user": user_name,
                                "invoice_number": (node.get("invoice") or {}).get("number"),
                            })

                        page_info = data.get("pageInfo", {})
                        if not page_info.get("hasNextPage"):
                            break
                        cursor = page_info.get("endCursor")

                    _timeline_cache[client_id] = {"entries": all_client_entries, "fetched_at": now}
                    logging.info(f"📋 Cache timeline rempli: {len(all_client_entries)} entrées (hors SYSTEM_MESSAGE)")
                except Exception as e:
                    logging.warning(f"⚠️ Erreur timeline Gazelle: {e}")

            # Filtrer pour ce piano
            gazelle_entries = [
                {k: v for k, v in e.items() if k != "piano_id"}
                for e in all_client_entries
                if e.get("piano_id") == piano_id
            ][:limit]
            logging.info(f"📋 {len(gazelle_entries)} entrées Gazelle pour piano {piano_id}")

        # 2. Entrées locales depuis vdi_service_history
        local_entries = []
        try:
            r = _sh_table_request(
                params=f"piano_id=eq.{piano_id}&select=*&order=validated_at.desc&limit={limit}"
            )
            if r.status_code == 200:
                for entry in r.json():
                    local_entries.append({
                        "source": "local",
                        "id": entry.get("id"),
                        "date": entry.get("service_date") or entry.get("validated_at") or entry.get("created_at"),
                        "type": "SERVICE",
                        "summary": entry.get("travail") or "",
                        "comment": entry.get("a_faire") or "",
                        "user": entry.get("technician_name"),
                        "status": entry.get("status"),
                        "pushed_at": entry.get("pushed_at"),
                        "gazelle_event_id": entry.get("gazelle_event_id"),
                    })
                logging.info(f"📋 {len(local_entries)} entrées locales pour piano {piano_id}")
        except Exception as e:
            logging.warning(f"⚠️ Erreur service_history pour {piano_id}: {e}")

        # 3. Fusionner et trier anti-chronologiquement
        all_entries = gazelle_entries + local_entries
        all_entries.sort(key=lambda x: x.get("date") or "1970-01-01", reverse=True)

        return {
            "piano_id": piano_id,
            "entries": all_entries,
            "gazelle_count": len(gazelle_entries),
            "local_count": len(local_entries),
        }

    except Exception as e:
        logging.error(f"❌ Timeline piano {piano_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================
# VDI GUEST / ADMIN ROUTES — "ZÉRO FRICTION"
# ==========================================
# Préfixe isolé /vdi pour ne pas interférer avec /vincent-dindy
# Tables Supabase dédiées : vdi_guest_technicians, vdi_notes_buffer, vdi_priority_pianos

import uuid as _uuid
from pydantic import Field

vdi_router = APIRouter(prefix="/vdi", tags=["vdi-guest"])

# ---------- Modèles Pydantic ----------

class VdiGuestNoteUpdate(BaseModel):
    note: str

class VdiGuestTechCreate(BaseModel):
    tech_name: str

class VdiBufferValidation(BaseModel):
    note_ids: List[str]

class VdiBundlePushRequest(BaseModel):
    note_ids: Optional[List[str]] = None          # None = toutes les notes validées
    technician_id: str = "usr_HcCiFk7o0vZ9xAI0"  # Nicolas par défaut
    event_date: Optional[str] = None               # défaut = maintenant (Montréal)

class VdiPriorityToggle(BaseModel):
    piano_id: str


# ---------- Helpers Supabase ----------

def _vdi_sb():
    """Retourne une instance SupabaseStorage pour les tables VDI."""
    return get_supabase_storage()

def _vdi_table_request(table: str, method: str = "GET", params: str = "",
                       json_body=None, prefer: str = "return=representation"):
    """Requête REST Supabase bas-niveau vers une table arbitraire."""
    sb = _vdi_sb()
    url = f"{sb.api_url}/{table}?{params}" if params else f"{sb.api_url}/{table}"
    headers = {
        "apikey": sb.supabase_key,
        "Authorization": f"Bearer {sb.supabase_key}",
        "Content-Type": "application/json",
        "Prefer": prefer,
    }
    import requests as _req
    if method == "GET":
        r = _req.get(url, headers=headers)
    elif method == "POST":
        r = _req.post(url, headers=headers, json=json_body)
    elif method == "PATCH":
        r = _req.patch(url, headers=headers, json=json_body)
    elif method == "DELETE":
        r = _req.delete(url, headers=headers)
    else:
        raise ValueError(f"Méthode HTTP non supportée: {method}")
    return r


# ---------- GUEST routes ----------

@vdi_router.get("/guest/{tech_token}/pianos")
async def vdi_guest_get_pianos(tech_token: str):
    """
    Liste les pianos VDI pour un invité.
    Retourne les pianos triés : prioritaires (🟢) en premier, puis par location.
    Inclut la note existante du buffer pour chaque piano (si elle existe).
    """
    # 1. Valider le token invité
    r = _vdi_table_request("vdi_guest_technicians",
                           params=f"tech_token=eq.{tech_token}&active=eq.true&select=*")
    if r.status_code != 200 or not r.json():
        raise HTTPException(status_code=404, detail="Lien invité invalide ou expiré")
    guest = r.json()[0]
    tech_name = guest["tech_name"]

    # 2. Charger les pianos VDI depuis Gazelle
    from api.institutions import get_institution_config
    config = get_institution_config("vincent-dindy")
    client_id = config.get("gazelle_client_id")
    api_client = get_api_client()
    if not api_client:
        raise HTTPException(status_code=500, detail="Client API Gazelle non disponible")

    query = """
    query GetVDIPianos($clientId: String!) {
      allPianos(first: 200, filters: { clientId: $clientId }) {
        nodes { id serialNumber make model location type status tags }
      }
    }
    """
    result = api_client._execute_query(query, {"clientId": client_id})
    gazelle_pianos = result.get("data", {}).get("allPianos", {}).get("nodes", [])

    # Filtrer les pianos avec tag "non"
    visible = []
    for p in gazelle_pianos:
        tags_raw = p.get("tags", "")
        tags = []
        if tags_raw:
            if isinstance(tags_raw, list):
                tags = tags_raw
            elif isinstance(tags_raw, str):
                try:
                    tags = ast.literal_eval(tags_raw)
                except Exception:
                    tags = []
        if "non" not in [t.lower() for t in tags]:
            visible.append(p)

    # 3. Charger les notes buffer existantes de cet invité
    buf_r = _vdi_table_request("vdi_notes_buffer",
                               params=f"tech_token=eq.{tech_token}&select=*")
    buffer_notes = {}
    if buf_r.status_code == 200:
        for bn in buf_r.json():
            buffer_notes[bn["piano_id"]] = {
                "id": bn["id"],
                "note": bn["note"],
                "status": bn["status"],
                "updated_at": bn["updated_at"],
            }

    # 4. Charger les pianos prioritaires
    prio_r = _vdi_table_request("vdi_priority_pianos", params="select=piano_id")
    prio_ids = set()
    if prio_r.status_code == 200:
        prio_ids = {row["piano_id"] for row in prio_r.json()}

    # 5. Construire la réponse et trier
    pianos_out = []
    for p in visible:
        pid = p["id"]
        pianos_out.append({
            "id": pid,
            "serialNumber": p.get("serialNumber"),
            "make": p.get("make"),
            "model": p.get("model"),
            "location": p.get("location"),
            "type": p.get("type"),
            "is_priority": pid in prio_ids,
            "buffer_note": buffer_notes.get(pid),
        })

    # Tri : prioritaires d'abord, puis par location
    pianos_out.sort(key=lambda x: (not x["is_priority"], x.get("location") or ""))

    return {
        "tech_name": tech_name,
        "pianos": pianos_out,
        "count": len(pianos_out),
    }


@vdi_router.put("/guest/{tech_token}/pianos/{piano_id}/note")
async def vdi_guest_save_note(tech_token: str, piano_id: str, body: VdiGuestNoteUpdate):
    """
    Auto-save (upsert) d'une note dans le buffer.
    Appelé par le debounce côté front (500 ms).
    """
    # Valider le token
    r = _vdi_table_request("vdi_guest_technicians",
                           params=f"tech_token=eq.{tech_token}&active=eq.true&select=tech_name")
    if r.status_code != 200 or not r.json():
        raise HTTPException(status_code=404, detail="Lien invité invalide ou expiré")
    tech_name = r.json()[0]["tech_name"]

    # Upsert via Supabase on-conflict
    row = {
        "tech_token": tech_token,
        "tech_name": tech_name,
        "piano_id": piano_id,
        "note": body.note,
        "status": "draft",
        "updated_at": datetime.utcnow().isoformat(),
    }
    resp = _vdi_table_request(
        "vdi_notes_buffer",
        method="POST",
        json_body=row,
        prefer="return=representation,resolution=merge-duplicates",
        params="on_conflict=tech_token,piano_id",
    )
    if resp.status_code not in (200, 201):
        raise HTTPException(status_code=500, detail=f"Erreur buffer: {resp.text}")

    saved = resp.json()
    return {"saved": True, "note_id": saved[0]["id"] if saved else None}


# ---------- ADMIN routes ----------

@vdi_router.post("/internal/ensure-token")
async def vdi_ensure_token(body: VdiGuestTechCreate):
    """
    Auto-provision: retourne le token existant pour ce tech_name,
    ou en crée un nouveau. Utilisé par l'UI React (derrière PIN).
    """
    # Chercher un token actif existant
    r = _vdi_table_request("vdi_guest_technicians",
                           params=f"tech_name=eq.{body.tech_name}&active=eq.true&select=tech_token,tech_name&limit=1")
    if r.status_code == 200 and r.json():
        existing = r.json()[0]
        return {"tech_token": existing["tech_token"], "tech_name": existing["tech_name"], "created": False}

    # Créer un nouveau token
    token = str(_uuid.uuid4())
    row = {
        "tech_token": token,
        "tech_name": body.tech_name,
        "active": True,
        "created_by": "internal",
        "created_at": datetime.utcnow().isoformat(),
    }
    cr = _vdi_table_request("vdi_guest_technicians", method="POST", json_body=row)
    if cr.status_code not in (200, 201):
        raise HTTPException(status_code=500, detail=f"Erreur création token: {cr.text}")
    return {"tech_token": token, "tech_name": body.tech_name, "created": True}


@vdi_router.post("/admin/guest-technicians")
async def vdi_create_guest(body: VdiGuestTechCreate):
    """Crée un lien invité (token) pour un technicien externe."""
    token = str(_uuid.uuid4())
    row = {
        "tech_token": token,
        "tech_name": body.tech_name,
        "active": True,
        "created_at": datetime.utcnow().isoformat(),
    }
    r = _vdi_table_request("vdi_guest_technicians", method="POST", json_body=row)
    if r.status_code not in (200, 201):
        raise HTTPException(status_code=500, detail=f"Erreur création invité: {r.text}")
    return {"tech_token": token, "tech_name": body.tech_name}


@vdi_router.get("/admin/guest-technicians")
async def vdi_list_guests():
    """Liste tous les techniciens invités."""
    r = _vdi_table_request("vdi_guest_technicians", params="select=*&order=created_at.desc")
    if r.status_code != 200:
        raise HTTPException(status_code=500, detail=r.text)
    return r.json()


@vdi_router.delete("/admin/guest-technicians/{tech_token}")
async def vdi_deactivate_guest(tech_token: str):
    """Désactive un lien invité."""
    r = _vdi_table_request("vdi_guest_technicians", method="PATCH",
                           params=f"tech_token=eq.{tech_token}",
                           json_body={"active": False})
    if r.status_code not in (200, 204):
        raise HTTPException(status_code=500, detail=r.text)
    return {"deactivated": True}


@vdi_router.post("/admin/priority/{piano_id}")
async def vdi_set_priority(piano_id: str):
    """Marque un piano comme prioritaire (🟢)."""
    row = {"piano_id": piano_id, "set_by": "nicolas", "created_at": datetime.utcnow().isoformat()}
    r = _vdi_table_request("vdi_priority_pianos", method="POST", json_body=row,
                           prefer="return=representation,resolution=merge-duplicates",
                           params="on_conflict=piano_id")
    if r.status_code not in (200, 201):
        raise HTTPException(status_code=500, detail=r.text)
    return {"priority": True, "piano_id": piano_id}


@vdi_router.delete("/admin/priority/{piano_id}")
async def vdi_remove_priority(piano_id: str):
    """Retire le marqueur prioritaire d'un piano."""
    r = _vdi_table_request("vdi_priority_pianos", method="DELETE",
                           params=f"piano_id=eq.{piano_id}")
    if r.status_code not in (200, 204):
        raise HTTPException(status_code=500, detail=r.text)
    return {"priority": False, "piano_id": piano_id}


@vdi_router.get("/admin/buffer")
async def vdi_get_buffer(status_filter: Optional[str] = None):
    """
    Retourne toutes les notes du buffer.
    ?status_filter=draft|validated|pushed
    """
    params = "select=*&order=updated_at.desc"
    if status_filter:
        params += f"&status=eq.{status_filter}"
    r = _vdi_table_request("vdi_notes_buffer", params=params)
    if r.status_code != 200:
        raise HTTPException(status_code=500, detail=r.text)
    return r.json()


@vdi_router.put("/admin/buffer/{note_id}")
async def vdi_admin_edit_note(note_id: str, body: VdiGuestNoteUpdate):
    """Nicolas peut éditer une note du buffer avant validation."""
    r = _vdi_table_request("vdi_notes_buffer", method="PATCH",
                           params=f"id=eq.{note_id}",
                           json_body={"note": body.note, "updated_at": datetime.utcnow().isoformat()})
    if r.status_code not in (200, 204):
        raise HTTPException(status_code=500, detail=r.text)
    return {"edited": True}


@vdi_router.post("/admin/buffer/validate")
async def vdi_validate_notes(body: VdiBufferValidation):
    """Marque un lot de notes comme 'validated' (prêtes pour bundle push)."""
    for nid in body.note_ids:
        _vdi_table_request("vdi_notes_buffer", method="PATCH",
                           params=f"id=eq.{nid}",
                           json_body={"status": "validated", "updated_at": datetime.utcnow().isoformat()})
    return {"validated": len(body.note_ids)}


@vdi_router.post("/admin/bundle-push")
async def vdi_bundle_push(body: VdiBundlePushRequest):
    """
    Bundle Push vers Gazelle :
    1. Récupère les notes validées
    2. Regroupe par piano
    3. Crée UN SEUL événement multi-pianos
    4. Complète avec serviceHistoryNotes individuelles
    5. Gymnastique ACTIVE → create → complete → INACTIVE
    """
    from core.timezone_utils import MONTREAL_TZ

    api_client = get_api_client()
    if not api_client:
        raise HTTPException(status_code=500, detail="Client API Gazelle non disponible")

    # 1. Récupérer les notes à pousser
    if body.note_ids:
        # Notes spécifiques
        all_notes = []
        for nid in body.note_ids:
            r = _vdi_table_request("vdi_notes_buffer", params=f"id=eq.{nid}&select=*")
            if r.status_code == 200 and r.json():
                all_notes.append(r.json()[0])
    else:
        # Toutes les notes validées
        r = _vdi_table_request("vdi_notes_buffer", params="status=eq.validated&select=*")
        if r.status_code != 200:
            raise HTTPException(status_code=500, detail="Erreur lecture buffer")
        all_notes = r.json()

    if not all_notes:
        raise HTTPException(status_code=400, detail="Aucune note à pousser")

    # 2. Regrouper les notes par piano_id
    piano_notes: Dict[str, List[Dict]] = {}
    for n in all_notes:
        pid = n["piano_id"]
        piano_notes.setdefault(pid, []).append(n)

    piano_ids = list(piano_notes.keys())
    logging.info(f"🎹 Bundle push: {len(all_notes)} notes pour {len(piano_ids)} pianos")

    # 3. Récupérer le client_id VDI
    from api.institutions import get_institution_config
    config = get_institution_config("vincent-dindy")
    client_id = config.get("gazelle_client_id")

    # 4. Gymnastique: Réactiver les pianos INACTIVE → ACTIVE
    activated_pianos = []
    for pid in piano_ids:
        try:
            status_q = """
            query GetPianoStatus($pianoId: String!) {
                piano(id: $pianoId) { id status }
            }
            """
            sr = api_client._execute_query(status_q, {"pianoId": pid})
            current_status = sr.get("data", {}).get("piano", {}).get("status")
            if current_status == "INACTIVE":
                update_m = """
                mutation ActivatePiano($pianoId: String!, $input: PrivatePianoInput!) {
                    updatePiano(id: $pianoId, input: $input) {
                        piano { id status }
                        mutationErrors { fieldName messages }
                    }
                }
                """
                api_client._execute_query(update_m, {"pianoId": pid, "input": {"status": "ACTIVE"}})
                activated_pianos.append(pid)
                logging.info(f"   ✅ Piano {pid} → ACTIVE")
        except Exception as e:
            logging.warning(f"   ⚠️ Activation piano {pid}: {e}")

    # 5. Créer UN SEUL événement multi-pianos
    event_date = body.event_date or datetime.now(MONTREAL_TZ).isoformat()
    pianos_input = [{"pianoId": pid, "isTuning": True} for pid in piano_ids]

    create_mutation = """
    mutation CreateBundleEvent($input: PrivateEventInput!) {
        createEvent(input: $input) {
            event { id title start type status }
            mutationErrors { fieldName messages }
        }
    }
    """

    # Construire le texte combiné pour le champ notes de l'événement
    combined_lines = []
    for pid, notes_list in piano_notes.items():
        for n in notes_list:
            combined_lines.append(f"🎹 {pid} - {n['tech_name']} : {n['note']}")
    combined_text = "\n".join(combined_lines)

    event_input = {
        "title": f"VDI Accord collectif ({len(piano_ids)} pianos)",
        "start": event_date,
        "duration": 60 * len(piano_ids),
        "type": "APPOINTMENT",
        "notes": combined_text,
        "pianos": pianos_input,
        "userId": body.technician_id,
    }
    if client_id:
        event_input["clientId"] = client_id

    create_result = api_client._execute_query(create_mutation, {"input": event_input})
    create_data = create_result.get("data", {}).get("createEvent", {})
    event = create_data.get("event")
    if not event:
        errors = create_data.get("mutationErrors", [])
        raise HTTPException(status_code=500,
                            detail=f"Erreur createEvent: {errors}")

    event_id = event["id"]
    logging.info(f"   ✅ Événement créé: {event_id}")

    # 6. Compléter avec serviceHistoryNotes individuelles par piano
    service_notes = []
    for pid, notes_list in piano_notes.items():
        lines = [f"{n['tech_name']} : {n['note']}" for n in notes_list]
        service_notes.append({"pianoId": pid, "notes": "\n".join(lines)})

    complete_mutation = """
    mutation CompleteBundleEvent($eventId: String!, $input: PrivateCompleteEventInput!) {
        completeEvent(eventId: $eventId, input: $input) {
            event { id status }
            mutationErrors { fieldName messages }
        }
    }
    """
    complete_input = {
        "resultType": "COMPLETE",
        "serviceHistoryNotes": service_notes,
    }
    api_client._execute_query(complete_mutation, {"eventId": event_id, "input": complete_input})
    logging.info(f"   ✅ Événement complété avec {len(service_notes)} notes d'historique")

    # 7. Remettre les pianos en INACTIVE
    for pid in activated_pianos:
        try:
            deact_m = """
            mutation DeactivatePiano($pianoId: String!, $input: PrivatePianoInput!) {
                updatePiano(id: $pianoId, input: $input) {
                    piano { id status }
                    mutationErrors { fieldName messages }
                }
            }
            """
            api_client._execute_query(deact_m, {"pianoId": pid, "input": {"status": "INACTIVE"}})
            logging.info(f"   ✅ Piano {pid} → INACTIVE")
        except Exception as e:
            logging.warning(f"   ⚠️ Désactivation piano {pid}: {e}")

    # 8. Marquer les notes comme 'pushed'
    for n in all_notes:
        _vdi_table_request("vdi_notes_buffer", method="PATCH",
                           params=f"id=eq.{n['id']}",
                           json_body={"status": "pushed", "updated_at": datetime.utcnow().isoformat()})

    return {
        "success": True,
        "event_id": event_id,
        "pianos_count": len(piano_ids),
        "notes_count": len(all_notes),
        "activated_then_deactivated": activated_pianos,
    }
