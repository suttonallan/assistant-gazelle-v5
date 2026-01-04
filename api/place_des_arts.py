"""
Routes FastAPI - Place des Arts (stub migration V5).

Objectif : préparer l'import CSV sans écrire de données tant que
la logique V4 n'est pas portée.
"""

import sys
import os
import logging
from pathlib import Path
from typing import List, Literal, Optional, Dict, Any
import requests
from datetime import datetime, timedelta
import time

from fastapi import APIRouter, UploadFile, File, HTTPException, Query, Response
from starlette.responses import StreamingResponse
from pydantic import BaseModel

# Ajouter le parent au path pour les imports locaux
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.supabase_storage import SupabaseStorage  # noqa: E402
from core.gazelle_api_client import GazelleAPIClient  # noqa: E402
from modules.place_des_arts.services.event_parser import EventParser  # noqa: E402
from modules.place_des_arts.services.event_manager import EventManager  # noqa: E402
from modules.place_des_arts.services.email_parser import parse_email_text  # noqa: E402

router = APIRouter(prefix="/place-des-arts", tags=["place-des-arts"])

# NOTE: PLACE_DES_ARTS_CLIENT_ID supprimé - Utiliser get_institution_config() depuis api/institutions.py

# Singletons
_api_client = None

def get_api_client() -> Optional[GazelleAPIClient]:
    """Retourne l'instance du client API Gazelle (singleton)."""
    global _api_client
    if _api_client is None:
        try:
            _api_client = GazelleAPIClient()
        except Exception as e:
            print(f"⚠️ Erreur lors de l'initialisation du client API: {e}")
            _api_client = None
    return _api_client

# Singletons légers
_storage = None
_parser = None
_manager = None

# Cache pour l'inventaire (évite les appels répétés à Gazelle)
_inventory_cache = {
    "data": None,
    "timestamp": None,
    "ttl_seconds": 300  # 5 minutes
}


def get_storage() -> SupabaseStorage:
    global _storage
    if _storage is None:
        # Utiliser silent=True pour éviter les logs répétés (singleton)
        _storage = SupabaseStorage(silent=True)
    return _storage


def get_parser() -> EventParser:
    global _parser
    if _parser is None:
        _parser = EventParser()
    return _parser


def get_manager() -> EventManager:
    global _manager
    if _manager is None:
        _manager = EventManager(get_storage())
    return _manager


def find_duplicate_candidates(row: Dict[str, Any]) -> List[str]:
    """
    Cherche des doublons potentiels dans place_des_arts_requests pour une ligne donnée.
    Critères : même date (jour), même salle, et rapprochement sur piano OU for_who.
    """
    storage = get_storage()
    appt = row.get("appointment_date")
    room = (row.get("room") or "").strip()
    if not appt or not room:
        return []
    try:
        appt_date = appt[:10]
        gte = f"{appt_date}T00:00:00"
        lt = f"{appt_date}T23:59:59.999999"
    except Exception:
        return []

    params = [
        "select=id,appointment_date,room,piano,for_who",
        f"appointment_date=gte.{gte}",
        f"appointment_date=lt.{lt}",
        f"room=eq.{room}",
        "limit=50"
    ]
    url = f"{storage.api_url}/place_des_arts_requests?{'&'.join(params)}"
    resp = requests.get(url, headers=storage._get_headers())
    if resp.status_code != 200:
        return []
    candidates = resp.json() or []

    def normalize(val: Optional[str]) -> str:
        return (val or "").strip().lower()

    piano_in = normalize(row.get("piano"))
    forwho_in = normalize(row.get("for_who"))

    dup_ids: List[str] = []
    for c in candidates:
        cp = normalize(c.get("piano"))
        cf = normalize(c.get("for_who"))
        if piano_in and piano_in and piano_in in cp or cp in piano_in:
            dup_ids.append(c.get("id"))
            continue
        if forwho_in and (forwho_in in cf or cf in forwho_in):
            dup_ids.append(c.get("id"))
    return dup_ids


class ImportCSVResponse(BaseModel):
    dry_run: bool
    received: int
    inserted: int
    updated: int
    errors: List[str]
    message: str


class UpdateCellRequest(BaseModel):
    request_id: str
    field: str
    value: Any

class PushToGazelleRequest(BaseModel):
    """Requête pour pousser une note vers Gazelle"""
    request_id: str
    piano_id: str  # ID Gazelle du piano
    technician_id: str  # ID Gazelle du technicien
    summary: str  # Résumé (ex: "Accord", "Humidité à faire")
    comment: str  # Commentaire détaillé (notes de travail)
    update_last_tuned: bool = True  # Mettre à jour last_tuned_date si True (déprécié, toujours True via événement)


class StatusBatchRequest(BaseModel):
    request_ids: List[str]
    status: str
    billed_by: Optional[str] = None


class DeleteRequest(BaseModel):
    request_ids: List[str]


class PreviewRequest(BaseModel):
    """Stub pour prévisualisation import email/texte."""
    raw_text: Optional[str] = None
    source: Optional[str] = None  # ex: "email"


class ImportRequest(BaseModel):
    """Stub pour import email/texte."""
    raw_text: str
    source: Optional[str] = None  # ex: "email"


@router.get("/health")
async def health_check():
    """Health check minimal du module Place des Arts."""
    return {"status": "ok", "module": "place-des-arts"}


@router.get("/pianos", response_model=Dict[str, Any])
async def get_pianos(include_inactive: bool = False):
    """
    Récupère tous les pianos Place des Arts depuis Gazelle API.
    
    Args:
        include_inactive: Si True, inclut les pianos avec tag "non" (masqués par défaut)
    
    Architecture:
    - Gazelle API = Source unique de vérité (filtre par client ID Place des Arts)
    - Tag "non" dans Gazelle = piano masqué de l'inventaire
    - Filtre par défaut = masque les pianos avec tag "non"
    - Supabase = Modifications dynamiques (status, notes, etc.)
    """
    import logging
    import ast
    
    try:
        # Charger client_id depuis Supabase institutions
        from api.institutions import get_institution_config
        try:
            config = get_institution_config("place-des-arts")
            client_id = config.get('gazelle_client_id')
            logging.info(f"✅ Slug reçu: 'place-des-arts' | Config trouvée: Oui (client_id: {client_id})")
        except Exception as e:
            logging.error(f"❌ Slug reçu: 'place-des-arts' | Config trouvée: Non | Erreur: {e}")
            raise HTTPException(status_code=500, detail=f"Configuration institution non trouvée: {str(e)}")
        
        # 1. Charger TOUS les pianos Place des Arts depuis Gazelle
        api_client = get_api_client()
        
        if not api_client:
            raise HTTPException(status_code=500, detail="Client API Gazelle non disponible")
        
        query = """
        query GetPlaceDesArtsPianos($clientId: String!) {
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
        
        logging.info(f"📋 {len(gazelle_pianos)} pianos Place des Arts chargés depuis Gazelle")
        
        # 2. Charger les modifications depuis Supabase (flags + overlays)
        # Note: Pour Place des Arts, on pourrait utiliser une table spécifique
        # ou la même table avec un filtre par client_id
        storage = get_storage()
        # TODO: Créer une table place_des_arts_piano_updates ou utiliser vincent_dindy_piano_updates avec filtre
        # Pour l'instant, on utilise la même table mais on pourrait filtrer par client_id
        supabase_updates = storage.get_all_piano_updates()  # TODO: Filtrer par client Place des Arts
        
        logging.info(f"☁️  {len(supabase_updates)} modifications Supabase trouvées")
        
        # 3. FUSION: Transformer pianos Gazelle + appliquer overlays Supabase
        pianos = []
        
        for gz_piano in gazelle_pianos:
            # Gérer les deux formats possibles : 'id' ou 'instrument_id'
            gz_id = gz_piano.get('id') or gz_piano.get('instrument_id')
            if not gz_id:
                logging.warning(f"⚠️ Piano sans ID trouvé: {gz_piano}")
                continue
            serial = gz_piano.get('serialNumber', gz_id)
            
            # Trouver les updates Supabase
            updates = {}
            for piano_id, data in supabase_updates.items():
                if (piano_id == gz_id or piano_id == serial):
                    updates = data
                    break
            
            # Parser les tags Gazelle
            tags_raw = gz_piano.get('tags', '')
            tags = []
            if tags_raw:
                try:
                    if isinstance(tags_raw, list):
                        tags = tags_raw
                    elif isinstance(tags_raw, str):
                        tags = ast.literal_eval(tags_raw)
                except Exception as e:
                    logging.warning(f"Erreur parsing tags pour piano {serial}: {e}")
                    tags = []
            
            # Filtrage par tag "non"
            has_non_tag = 'non' in [t.lower() for t in tags]
            
            if not include_inactive and has_non_tag:
                continue  # Ignorer les pianos marqués "non"
            
            # Construire l'objet piano
            piano_type = gz_piano.get('type', 'UPRIGHT')
            type_letter = piano_type[0].upper() if piano_type else 'D'
            
            piano = {
                "id": gz_id,
                "gazelleId": gz_id,
                "local": gz_piano.get('location', ''),
                "piano": gz_piano.get('make', ''),
                "modele": gz_piano.get('model', ''),
                "serie": serial,
                "type": type_letter,
                "usage": "",
                "dernierAccord": gz_piano.get('calculatedLastService', ''),
                "prochainAccord": gz_piano.get('calculatedNextService', ''),
                "status": updates.get('status', 'normal'),
                "aFaire": updates.get('a_faire', ''),
                "travail": updates.get('travail', ''),
                "observations": updates.get('observations', gz_piano.get('notes', '')),
                "tags": tags,
                "hasNonTag": has_non_tag,
                "isInCsv": updates.get('is_in_csv', True),
                "gazelleStatus": gz_piano.get('status', 'UNKNOWN')
            }
            
            pianos.append(piano)
        
        # Mettre à jour le cache
        result_data = {
            "pianos": pianos,
            "count": len(pianos),
            "source": "gazelle_api",
            "client_id": client_id,
            "include_inactive": include_inactive
        }
        
        _inventory_cache["data"] = result_data
        _inventory_cache["timestamp"] = time.time()
        
        # Filtrer les inactifs si nécessaire
        if not include_inactive:
            filtered_pianos = [p for p in pianos if not p.get("hasNonTag", False)]
            return {
                **result_data,
                "pianos": filtered_pianos,
                "count": len(filtered_pianos),
                "cached": False
            }
        
        return {
            **result_data,
            "cached": False
        }
        
    except Exception as e:
        logging.error(f"❌ Erreur lors de la récupération des pianos Place des Arts: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")


@router.get("/requests")
async def list_requests(
    status: Optional[str] = Query(default=None),
    month: Optional[str] = Query(default=None, description="Format AAAA-MM"),
    technician_id: Optional[str] = Query(default=None),
    room: Optional[str] = Query(default=None),
    limit: int = Query(default=200, le=500),
):
    """
    Liste des demandes Place des Arts (limité à 500).
    Filtres simples: status, month (AAAA-MM), technician_id, room.
    """
    storage = get_storage()
    params = ["select=*"]
    if status:
        params.append(f"status=eq.{status}")
    if technician_id:
        params.append(f"technician_id=eq.{technician_id}")
    if room:
        params.append(f"room=eq.{room}")
    if month:
        params.append(f"appointment_date=gte.{month}-01")
        params.append(f"appointment_date=lt.{month}-32")
    params.append("order=appointment_date.desc")
    params.append(f"limit={limit}")

    url = f"{storage.api_url}/place_des_arts_requests?{'&'.join(params)}"
    resp = requests.get(url, headers=storage._get_headers())
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    return resp.json()


@router.get("/export")
async def export_csv():
    """
    Export CSV simple (toutes les demandes, limit 2000, tri date desc).
    """
    storage = get_storage()
    params = [
        "select=*",
        "order=appointment_date.desc",
        "limit=2000",
        "format=csv"
    ]
    url = f"{storage.api_url}/place_des_arts_requests?{'&'.join(params)}"
    hdrs = storage._get_headers().copy()
    hdrs["Accept"] = "text/csv"
    resp = requests.get(url, headers=hdrs, stream=True)
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    return StreamingResponse(resp.iter_content(chunk_size=8192),
                             media_type="text/csv",
                             headers={"Content-Disposition": "attachment; filename=place_des_arts.csv"})


@router.get("/stats")
async def stats():
    manager = get_manager()
    try:
        return manager.get_stats()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/requests/{request_id}/gazelle-piano-id")
async def get_gazelle_piano_id(request_id: str):
    """
    Récupère l'ID Gazelle du piano associé à une demande Place des Arts.
    
    Cherche le piano par:
    1. Mapping PDA (si existe dans pda_piano_mappings)
    2. Room/location dans les pianos Gazelle
    3. Champ 'piano' de la demande
    """
    try:
        storage = get_storage()
        
        # Récupérer la demande
        url = f"{storage.api_url}/place_des_arts_requests?id=eq.{request_id}&select=*&limit=1"
        resp = requests.get(url, headers=storage._get_headers())
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail="Demande non trouvée")
        
        requests_data = resp.json()
        if not requests_data:
            raise HTTPException(status_code=404, detail="Demande non trouvée")
        
        request_data = requests_data[0]
        room = request_data.get('room', '')
        piano_abbrev = request_data.get('piano', '')
        
        # 1. Chercher dans le mapping PDA
        # TODO: Implémenter la recherche dans pda_piano_mappings si la table existe
        
        # 2. Chercher dans les pianos Gazelle par location/room
        from api.institutions import get_institution_config
        try:
            config = get_institution_config("place-des-arts")
            client_id = config.get('gazelle_client_id')
        except Exception as e:
            logging.error(f"❌ Configuration place-des-arts non trouvée: {e}")
            client_id = None
        
        api_client = get_api_client()
        if api_client and client_id:
            # Récupérer les pianos directement depuis Gazelle
            query = """
            query GetPlaceDesArtsPianos($clientId: String!) {
              allPianos(first: 200, filters: { clientId: $clientId }) {
                nodes {
                  id
                  location
                  make
                  model
                  serialNumber
                }
              }
            }
            """
            variables = {"clientId": client_id}
            result = api_client._execute_query(query, variables)
            gazelle_pianos = result.get("data", {}).get("allPianos", {}).get("nodes", [])
            
            # Chercher par room/location
            for piano in gazelle_pianos:
                piano_location = piano.get('location', '').upper()
                if piano_location and piano_location == room.upper():
                    # Gérer les deux formats possibles : 'id' ou 'instrument_id'
                    piano_id = piano.get('id') or piano.get('instrument_id')
                    return {
                        "piano_id": piano_id,
                        "found_by": "location",
                        "piano_info": {
                            "make": piano.get('make'),
                            "model": piano.get('model'),
                            "location": piano.get('location')
                        }
                    }
            
            # Chercher par abréviation piano
            if piano_abbrev:
                for piano in gazelle_pianos:
                    piano_make = (piano.get('make', '') or '').upper()
                    if piano_abbrev.upper() in piano_make or piano_make in piano_abbrev.upper():
                        # Gérer les deux formats possibles : 'id' ou 'instrument_id'
                        piano_id = piano.get('id') or piano.get('instrument_id')
                        return {
                            "piano_id": piano_id,
                            "found_by": "piano_abbrev",
                            "piano_info": {
                                "make": piano.get('make'),
                                "model": piano.get('model'),
                                "location": piano.get('location')
                            }
                        }
        
        return {
            "piano_id": None,
            "found_by": None,
            "message": "Piano Gazelle non trouvé pour cette demande"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")


@router.post("/requests/push-to-gazelle")
async def push_to_gazelle(payload: PushToGazelleRequest):
    """
    Pousse une note de service vers Gazelle via createEvent.
    
    Miroir de la logique du module Tournée:
    - Crée un événement de type APPOINTMENT avec statut COMPLETE
    - Associe le piano à l'événement
    - La note du technicien est incluse dans le champ notes
    - L'événement apparaîtra dans l'historique du piano dans Gazelle
    """
    try:
        api_client = get_api_client()
        if not api_client:
            raise HTTPException(
                status_code=500,
                detail="Client API Gazelle non disponible. Vérifiez la configuration OAuth."
            )

        # Utiliser push_technician_service qui crée un événement complet
        event = api_client.push_technician_service(
            piano_id=payload.piano_id,
            technician_note=payload.comment,
            service_type=payload.summary or "TUNING",
            technician_id=payload.technician_id
        )

        return {
            "success": True,
            "message": "Mis à jour dans Gazelle",
            "event": {
                "id": event.get("id"),
                "title": event.get("title"),
                "status": event.get("status"),
                "notes": event.get("notes")
            },
            "piano_id": payload.piano_id,
            "technician_id": payload.technician_id
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Erreur lors de la mise à jour Gazelle: {str(e)}")


@router.post("/requests/update-cell")
async def update_cell(payload: UpdateCellRequest):
    manager = get_manager()
    result = manager.update_cell(payload.request_id, payload.field, payload.value)
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error", "Erreur update"))
    return result


@router.post("/requests/update-status-batch")
async def update_status_batch(payload: StatusBatchRequest):
    manager = get_manager()
    result = manager.update_status_batch(payload.request_ids, payload.status, payload.billed_by)
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error", "Erreur batch status"))
    return result


@router.post("/requests/bill")
async def bill_requests(payload: StatusBatchRequest):
    manager = get_manager()
    result = manager.bill_requests(payload.request_ids, payload.billed_by or "system")
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error", "Erreur facturation"))
    return result


@router.post("/requests/delete")
async def delete_requests(payload: DeleteRequest):
    manager = get_manager()
    result = manager.delete_requests(payload.request_ids)
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error", "Erreur suppression"))
    return result


@router.get("/requests/find-duplicates")
async def find_duplicates():
    """
    Trouve les doublons sans les supprimer.
    Retourne la liste des enregistrements qui seraient supprimés.
    """
    manager = get_manager()
    duplicates = manager.find_duplicates()
    return {"duplicates": duplicates, "count": len(duplicates)}


@router.post("/requests/delete-duplicates")
async def delete_duplicates():
    manager = get_manager()
    result = manager.delete_duplicates()
    if not result.get("ok", True):
        raise HTTPException(status_code=400, detail=result.get("error", "Erreur doublons"))
    return result


# ------------------------------------------------------------
# Stubs preview/import email + sync + diagnostic
# ------------------------------------------------------------

@router.post("/preview")
async def preview_email(payload: PreviewRequest):
    """
    Prévisualisation import email (parsing texte, sans écriture).
    """
    if not payload.raw_text:
        raise HTTPException(status_code=400, detail="raw_text requis")
    parsed = parse_email_text(payload.raw_text)
    # Map vers format normalisé (mais sans id)
    preview = []
    for idx, item in enumerate(parsed, start=1):
        appt_val = item.get("date")
        if isinstance(appt_val, datetime):
            appt_val = appt_val.date().isoformat()
        row = {
            "appointment_date": appt_val if isinstance(appt_val, str) else item.get("date"),
            "room": item.get("room"),
            "for_who": item.get("for_who"),
            "diapason": item.get("diapason"),
            "requester": item.get("requester"),
            "piano": item.get("piano"),
            "time": item.get("time"),
            "service": item.get("service"),
            "notes": item.get("notes"),
            "confidence": item.get("confidence"),
            "warnings": item.get("warnings"),
        }
        row["duplicate_of"] = find_duplicate_candidates(
            {
                "appointment_date": row.get("appointment_date"),
                "room": row.get("room"),
                "piano": row.get("piano"),
                "for_who": row.get("for_who"),
            }
        )
        preview.append(row)
    return {"success": True, "preview": preview, "count": len(preview)}


@router.post("/import")
async def import_email(payload: ImportRequest):
    """
    Import email/texte : parse, normalise, UPSERT.
    """
    if not payload.raw_text:
        raise HTTPException(status_code=400, detail="raw_text requis")
    parsed = parse_email_text(payload.raw_text)
    if not parsed:
        return {"success": True, "imported": 0, "warnings": ["Aucune demande détectée"]}

    storage = get_storage()

    def exists_duplicate(row: Dict[str, Any]) -> bool:
        # Critère V4 : même date, salle, pour qui, heure
        params = [
            f"appointment_date=eq.{row.get('appointment_date')}",
            f"room=eq.{row.get('room') or ''}",
            f"for_who=eq.{row.get('for_who') or ''}",
            f"time=eq.{row.get('time') or ''}",
            "select=id",
            "limit=1"
        ]
        url = f"{storage.api_url}/place_des_arts_requests?{'&'.join(params)}"
        resp = requests.get(url, headers=storage._get_headers())
        return resp.status_code == 200 and resp.json()

    rows = []
    duplicates = []
    today_iso = datetime.utcnow().date().isoformat()
    for idx, item in enumerate(parsed, start=1):
        appointment_date = item.get("date")
        if isinstance(appointment_date, datetime):
            appointment_date = appointment_date.date().isoformat()
        elif not appointment_date:
            continue  # saute si pas de date

        row = {
            "id": f"pda_email_{idx:04d}_{int(datetime.utcnow().timestamp())}",
            "request_date": today_iso,
            "appointment_date": appointment_date,
            "room": item.get("room") or "",
            "room_original": item.get("room"),
            "for_who": item.get("for_who") or "",
            "diapason": item.get("diapason") or "",
            "requester": item.get("requester") or "",
            "piano": item.get("piano") or "",
            "time": item.get("time") or "",
            "technician_id": None,
            "status": "PENDING",
            "original_raw_text": payload.raw_text,
            "notes": item.get("notes") or "",
        }
        if exists_duplicate(row):
            duplicates.append(row)
        else:
            rows.append(row)

    if not rows:
        return {
            "success": True,
            "imported": 0,
            "warnings": ["Aucune ligne exploitable (dates manquantes ou doublons existants)"],
            "duplicates": duplicates
        }

    manager = get_manager()
    result = manager.import_csv(rows, on_conflict="update")
    if result.get("errors"):
        raise HTTPException(status_code=400, detail=result["errors"])
    return {
        "success": True,
        "imported": result.get("inserted", 0),
        "message": result.get("message", ""),
        "duplicates_skipped": len(duplicates),
        "duplicates": duplicates
    }


class SyncManualRequest(BaseModel):
    request_ids: Optional[List[str]] = None


@router.post("/sync-manual")
async def sync_manual(payload: Optional[SyncManualRequest] = None):
    """
    Synchronisation manuelle: Met à jour le statut 'Créé Gazelle' pour les demandes
    qui ont un RV correspondant dans Gazelle.

    Si request_ids est fourni, synchronise seulement ces demandes.
    Sinon, synchronise toutes les demandes avec statut ASSIGN_OK.
    """
    try:
        # Importer le validateur
        sys.path.insert(0, str(Path(__file__).parent.parent / "assistant-v6" / "modules" / "assistant" / "services"))
        from pda_validation import PlaceDesArtsValidator

        validator = PlaceDesArtsValidator()
        storage = get_storage()

        # Si des IDs spécifiques sont fournis, les récupérer
        if payload and payload.request_ids:
            # Récupérer seulement les demandes spécifiques
            url = f"{storage.api_url}/place_des_arts_requests"
            url += f"?id=in.({','.join(payload.request_ids)})"
            url += "&select=*"
            resp = requests.get(url, headers=storage._get_headers())

            if resp.status_code != 200:
                raise HTTPException(status_code=resp.status_code, detail="Erreur récupération demandes")

            requests_to_check = resp.json()
        else:
            # Récupérer toutes les demandes assignées mais pas encore marquées "Créé Gazelle"
            params = [
                "select=*",
                "status=eq.ASSIGN_OK",
                "limit=200"
            ]
            url = f"{storage.api_url}/place_des_arts_requests?{'&'.join(params)}"
            resp = requests.get(url, headers=storage._get_headers())

            if resp.status_code != 200:
                raise HTTPException(status_code=resp.status_code, detail="Erreur récupération demandes")

            requests_to_check = resp.json()
        updated_count = 0
        not_found_warnings = []

        # Pour chaque demande assignée, vérifier si un RV existe dans Gazelle
        for req in requests_to_check:
            req_id = req.get('id')
            room = req.get('room', '')
            appt_date = req.get('appointment_date', '')
            for_who = req.get('for_who', '')

            # Chercher le RV dans Gazelle
            gazelle_appt = validator.find_gazelle_appointment_for_pda(
                appointment_date=appt_date,
                room=room,
                debug=False
            )

            # Si trouvé, mettre à jour le statut
            if gazelle_appt:
                update_url = f"{storage.api_url}/place_des_arts_requests"
                update_params = f"?id=eq.{req_id}"
                update_data = {"status": "CREATED_IN_GAZELLE"}

                update_resp = requests.patch(
                    update_url + update_params,
                    headers=storage._get_headers(),
                    json=update_data
                )

                if update_resp.status_code in (200, 204):
                    updated_count += 1
            else:
                # RV non trouvé - ajouter un warning
                not_found_warnings.append({
                    "id": req_id,
                    "date": appt_date,
                    "room": room,
                    "for_who": for_who
                })

        return {
            "success": True,
            "message": f"Synchronisation terminée: {updated_count} demande(s) mise(s) à jour",
            "updated": updated_count,
            "checked": len(requests_to_check),
            "warnings": not_found_warnings,
            "has_warnings": len(not_found_warnings) > 0
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur sync: {str(e)}") from e


@router.post("/validate-gazelle-rv")
async def validate_gazelle_rv(payload: Dict[str, Any]):
    """
    Valide qu'un RV existe dans Gazelle pour une demande Place des Arts.
    Retourne {"found": true/false, "appointment": {...}} si trouvé.
    """
    try:
        request_id = payload.get("request_id")
        appointment_date = payload.get("appointment_date")
        room = payload.get("room")

        if not appointment_date or not room:
            return {"found": False, "error": "Date ou salle manquante"}

        # Importer le validateur
        sys.path.insert(0, str(Path(__file__).parent.parent / "assistant-v6" / "modules" / "assistant" / "services"))
        from pda_validation import PlaceDesArtsValidator

        validator = PlaceDesArtsValidator()

        # Chercher le RV dans Gazelle
        gazelle_appt = validator.find_gazelle_appointment_for_pda(
            appointment_date=appointment_date,
            room=room,
            debug=False
        )

        if gazelle_appt:
            return {
                "found": True,
                "appointment": {
                    "external_id": gazelle_appt.get("external_id"),
                    "appointment_time": gazelle_appt.get("appointment_time"),
                    "notes": gazelle_appt.get("notes", "")[:100]
                }
            }
        else:
            return {"found": False}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur validation: {str(e)}") from e


@router.get("/diagnostic")
async def diagnostic():
    """
    Diagnostic rapide (stub).
    """
    return {"success": True, "message": "Diagnostic non implémenté (stub)."}


@router.post("/requests/import-csv", response_model=ImportCSVResponse)
async def import_requests_csv(
    file: UploadFile = File(...),
    dry_run: bool = True,
    on_conflict: Literal["ignore", "update"] = "update"
):
    """
    Stub d'import CSV Place des Arts.

    - Ne réalise aucune écriture tant que la migration n'est pas finalisée.
    - Vérifie simplement le format et retourne un accusé.
    """
    if file.content_type not in {"text/csv", "application/vnd.ms-excel", "application/csv"}:
        raise HTTPException(status_code=400, detail="Format CSV attendu (text/csv).")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Fichier CSV vide.")

    parser = get_parser()
    manager = get_manager()

    try:
        rows = parser.parse_csv_bytes(content)
    except Exception as exc:  # pragma: no cover - stub
        raise HTTPException(status_code=400, detail=f"CSV invalide: {exc}") from exc

    if dry_run:
        result = manager.import_csv_preview(rows)
    else:
        result = manager.import_csv(rows, on_conflict=on_conflict)

    return ImportCSVResponse(
        dry_run=dry_run,
        received=result.get("received", len(rows)),
        inserted=result.get("inserted", 0),
        updated=result.get("updated", 0),
        errors=result.get("errors", []),
        message=result.get("message", "Stub: aucune écriture tant que la migration n'est pas finalisée.")
    )


# ============================================================
# APPRENTISSAGE INTELLIGENT (Learning)
# ============================================================

class LearningCorrectionRequest(BaseModel):
    """Correction manuelle d'un parsing pour apprentissage."""
    original_text: str

    # Champs parsés automatiquement
    parsed_date: Optional[str] = None
    parsed_room: Optional[str] = None
    parsed_for_who: Optional[str] = None
    parsed_diapason: Optional[str] = None
    parsed_piano: Optional[str] = None
    parsed_time: Optional[str] = None
    parsed_requester: Optional[str] = None
    parsed_confidence: Optional[float] = None

    # Champs corrigés manuellement
    corrected_date: Optional[str] = None
    corrected_room: Optional[str] = None
    corrected_for_who: Optional[str] = None
    corrected_diapason: Optional[str] = None
    corrected_piano: Optional[str] = None
    corrected_time: Optional[str] = None
    corrected_requester: Optional[str] = None

    corrected_by: str  # Email de l'utilisateur


@router.post("/learn")
async def save_correction(payload: LearningCorrectionRequest):
    """
    Enregistre une correction manuelle pour améliorer le parser.
    Utilisé quand l'utilisateur corrige des champs après parsing.
    """
    storage = get_storage()

    correction_data = {
        "original_text": payload.original_text,
        "parsed_date": payload.parsed_date,
        "parsed_room": payload.parsed_room,
        "parsed_for_who": payload.parsed_for_who,
        "parsed_diapason": payload.parsed_diapason,
        "parsed_piano": payload.parsed_piano,
        "parsed_time": payload.parsed_time,
        "parsed_requester": payload.parsed_requester,
        "parsed_confidence": payload.parsed_confidence,
        "corrected_date": payload.corrected_date,
        "corrected_room": payload.corrected_room,
        "corrected_for_who": payload.corrected_for_who,
        "corrected_diapason": payload.corrected_diapason,
        "corrected_piano": payload.corrected_piano,
        "corrected_time": payload.corrected_time,
        "corrected_requester": payload.corrected_requester,
        "corrected_by": payload.corrected_by,
    }

    try:
        # Upsert dans parsing_corrections
        url = f"{storage.api_url}/parsing_corrections"
        headers = {
            **storage._get_headers(),
            "Prefer": "resolution=merge-duplicates"
        }

        resp = requests.post(url, headers=headers, json=correction_data)

        if resp.status_code not in (200, 201):
            raise HTTPException(
                status_code=resp.status_code,
                detail=f"Erreur Supabase: {resp.text}"
            )

        return {
            "success": True,
            "message": "Correction enregistrée pour apprentissage futur"
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur enregistrement correction: {str(e)}"
        ) from e


@router.get("/learning-stats")
async def get_learning_stats():
    """
    Retourne des statistiques sur les corrections d'apprentissage.
    """
    storage = get_storage()

    try:
        # Compter les corrections par champ
        url = f"{storage.api_url}/parsing_corrections?select=*"
        resp = requests.get(url, headers=storage._get_headers())

        if resp.status_code != 200:
            return {"success": False, "corrections": []}

        corrections = resp.json()

        # Analyser les corrections
        stats = {
            "total_corrections": len(corrections),
            "fields_corrected": {
                "date": 0,
                "room": 0,
                "for_who": 0,
                "diapason": 0,
                "piano": 0,
                "time": 0,
                "requester": 0
            },
            "recent_corrections": corrections[-10:] if len(corrections) > 10 else corrections
        }

        for c in corrections:
            for field in ["date", "room", "for_who", "diapason", "piano", "time", "requester"]:
                if c.get(f"corrected_{field}") != c.get(f"parsed_{field}"):
                    stats["fields_corrected"][field] += 1

        return {
            "success": True,
            "stats": stats
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
