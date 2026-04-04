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
from datetime import datetime, timedelta, timezone
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
from modules.place_des_arts.services.concert_search import rechercher_concert  # noqa: E402

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


def normalize_text_for_comparison(text: str) -> str:
    """Normalise un texte pour comparaison (minuscules, espaces normalisés)."""
    import re
    # Remplacer sauts de ligne et espaces multiples par un seul espace
    normalized = re.sub(r'\s+', ' ', text.strip().lower())
    return normalized


def normalize_date_for_comparison(date_value) -> Optional[str]:
    """Normalise une date pour comparaison (retourne ISO string ou None)."""
    if date_value is None:
        return None
    if isinstance(date_value, datetime):
        return date_value.date().isoformat()
    if isinstance(date_value, str):
        # Essayer de parser la date
        try:
            from dateutil import parser
            parsed = parser.parse(date_value)
            return parsed.date().isoformat()
        except:
            return date_value
    return str(date_value)


def normalize_room_for_comparison(room: Optional[str]) -> Optional[str]:
    """Normalise un code de salle pour comparaison."""
    if not room:
        return None
    # Normaliser les variations communes (espaces, casse)
    normalized = room.strip().upper()
    # Mapper les variations connues
    room_mapping = {
        'WP': 'WP', 'WILFRID-PELLETIER': 'WP', 'WILFRID PELLETIER': 'WP',
        'TM': 'TM', 'THEATRE MAISONNEUVE': 'TM', 'THÉÂTRE MAISONNEUVE': 'TM',
        'MS': 'MS', 'MAISON SYMPHONIQUE': 'MS',
        'SD': 'SD', 'SALLE DES PROVINCES': 'SD',
        'C5': 'C5', 'CINQUIEME SALLE': 'C5', 'CINQUIÈME SALLE': 'C5',
        'SCL': 'SCL', 'STUDIO CLAUDE-LÉVEILLÉE': 'SCL',
        'ODM': 'ODM', 'ODM': 'ODM',
        '5E': '5E', '5E SALLE': '5E',
        'CL': 'CL'
    }
    return room_mapping.get(normalized, normalized)


def normalize_piano_for_comparison(piano: Optional[str]) -> Optional[str]:
    """Normalise un type de piano pour comparaison."""
    if not piano:
        return None
    # Extraire la marque principale (Steinway, Yamaha, etc.)
    import re
    piano_upper = piano.upper()
    brands = ['STEINWAY', 'YAMAH', 'KAWAI', 'BÖSENDORFER', 'BOSENDORFER', 'FAZIOLI', 'BALDWIN', 'MASON']
    for brand in brands:
        if brand in piano_upper:
            return brand
    # Si pas de marque claire, retourner le texte normalisé
    return normalize_text_for_comparison(piano)


def normalize_time_for_comparison(time_value: Optional[str]) -> Optional[str]:
    """Normalise une heure pour comparaison."""
    if not time_value:
        return None
    import re
    # Extraire l'heure (format HH ou HH:MM)
    time_match = re.search(r'(\d{1,2})[:h](\d{2})?', str(time_value).lower())
    if time_match:
        hour = int(time_match.group(1))
        minute = int(time_match.group(2)) if time_match.group(2) else 0
        return f"{hour:02d}:{minute:02d}"
    return None


def merge_duplicate_requests(requests: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Fusionne intelligemment les demandes dupliquées.
    
    Règles:
    - Si date ET room (lieu) sont identiques:
      * Si l'heure OU le type de piano est différent → garder les deux demandes séparées
      * Sinon → fusionner les informations dans une seule demande
    
    Args:
        requests: Liste de demandes parsées
        
    Returns:
        Liste de demandes fusionnées
    """
    if len(requests) <= 1:
        return requests
    
    merged = []
    processed_indices = set()
    
    for i, req1 in enumerate(requests):
        if i in processed_indices:
            continue
        
        # Normaliser les valeurs de comparaison
        date1 = normalize_date_for_comparison(req1.get('date'))
        room1 = normalize_room_for_comparison(req1.get('room'))
        piano1 = normalize_piano_for_comparison(req1.get('piano'))
        time1 = normalize_time_for_comparison(req1.get('time'))
        
        # Chercher des doublons potentiels
        duplicates_to_merge = [i]
        
        for j in range(i + 1, len(requests)):
            if j in processed_indices:
                continue
            
            req2 = requests[j]
            date2 = normalize_date_for_comparison(req2.get('date'))
            room2 = normalize_room_for_comparison(req2.get('room'))
            piano2 = normalize_piano_for_comparison(req2.get('piano'))
            time2 = normalize_time_for_comparison(req2.get('time'))
            
            # Vérifier si date et room sont identiques
            if date1 and date2 and date1 == date2 and room1 and room2 and room1 == room2:
                # Date et lieu identiques → vérifier heure et piano
                piano_different = piano1 != piano2 and piano1 and piano2
                time_different = time1 != time2 and time1 and time2
                
                if piano_different or time_different:
                    # Heure ou piano différent → garder séparé (ne pas fusionner)
                    continue
                else:
                    # Même date, même lieu, même heure (ou pas d'heure), même piano (ou pas de piano)
                    # → C'est un doublon, fusionner
                    duplicates_to_merge.append(j)
        
        # Si on a trouvé des doublons à fusionner
        if len(duplicates_to_merge) > 1:
            # Fusionner les demandes
            merged_req = requests[duplicates_to_merge[0]].copy()
            
            # Fusionner les champs manquants depuis les autres demandes
            for idx in duplicates_to_merge[1:]:
                req_other = requests[idx]
                
                # Pour chaque champ, prendre la valeur non-vide la plus complète
                for field in ['room', 'for_who', 'diapason', 'piano', 'time', 'service', 'notes', 'requester']:
                    value_other = req_other.get(field)
                    value_current = merged_req.get(field)
                    
                    # Si le champ actuel est vide ou None, prendre celui de l'autre
                    if not value_current and value_other:
                        merged_req[field] = value_other
                    # Si les deux ont des valeurs différentes et non vides, combiner intelligemment
                    elif value_current and value_other and value_current != value_other:
                        # Pour les notes, combiner avec séparateur
                        if field == 'notes':
                            merged_req[field] = f"{value_current}; {value_other}".strip()
                        # Pour les autres champs, garder la valeur la plus longue (plus d'info)
                        elif len(str(value_other)) > len(str(value_current)):
                            merged_req[field] = value_other
                
                # Améliorer la confiance si plusieurs sources concordent
                confidence_other = req_other.get('confidence', 0.0)
                confidence_current = merged_req.get('confidence', 0.0)
                merged_req['confidence'] = min(max(confidence_current, confidence_other) + 0.1, 1.0)
                
                # Combiner les warnings
                warnings_current = merged_req.get('warnings', [])
                warnings_other = req_other.get('warnings', [])
                merged_req['warnings'] = list(set(warnings_current + warnings_other))
            
            # Ajouter un warning indiquant que des doublons ont été fusionnés
            if 'warnings' not in merged_req:
                merged_req['warnings'] = []
            merged_req['warnings'].append(f"Fusionné avec {len(duplicates_to_merge) - 1} autre(s) demande(s) similaire(s)")
            
            merged.append(merged_req)
            
            # Marquer toutes les demandes fusionnées comme traitées
            for idx in duplicates_to_merge:
                processed_indices.add(idx)
        else:
            # Pas de doublon, garder la demande telle quelle
            merged.append(req1)
            processed_indices.add(i)
    
    logging.info(f"🔀 Fusion intelligente: {len(requests)} demandes → {len(merged)} demandes (fusionné {len(requests) - len(merged)} doublon(s))")
    
    return merged


def find_learned_correction(block_text: str) -> Optional[Dict[str, Any]]:
    """
    Cherche si un texte similaire a déjà été corrigé manuellement.
    Retourne les valeurs corrigées si trouvé, None sinon.
    """
    storage = get_storage()
    normalized_input = normalize_text_for_comparison(block_text)

    try:
        # Récupérer toutes les corrections (on pourrait optimiser avec une recherche côté Supabase)
        url = f"{storage.api_url}/parsing_corrections?select=*"
        resp = requests.get(url, headers=storage._get_headers())

        if resp.status_code != 200:
            return None

        corrections = resp.json()

        for correction in corrections:
            original = correction.get("original_text", "")
            if normalize_text_for_comparison(original) == normalized_input:
                # Trouvé ! Retourner les valeurs corrigées
                return {
                    "date": correction.get("corrected_date"),
                    "room": correction.get("corrected_room"),
                    "for_who": correction.get("corrected_for_who"),
                    "diapason": correction.get("corrected_diapason"),
                    "piano": correction.get("corrected_piano"),
                    "time": correction.get("corrected_time"),
                    "requester": correction.get("corrected_requester"),
                    "confidence": 1.0,  # Confiance maximale car validé par humain
                    "warnings": [],
                    "learned": True  # Flag pour indiquer que c'est appris
                }

        return None
    except Exception as e:
        print(f"⚠️ Erreur recherche correction apprise: {e}")
        return None


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
    Enrichit les demandes avec le technicien du RV Gazelle si appointment_id existe.
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
    
    requests_data = resp.json()
    
    # Enrichir avec le technicien du RV Gazelle si appointment_id existe
    # Inclure aussi "À attribuer" (usr_HihJsEgkmpTEziJo) si présent dans Gazelle
    # Mettre à jour le statut à CREATED_IN_GAZELLE si le RV existe dans Gazelle
    # Vérifier les incohérences entre PDA et Gazelle
    # Extraire le stationnement depuis la description Gazelle
    appointment_ids = [r.get("appointment_id") for r in requests_data if r.get("appointment_id")]
    if appointment_ids:
        try:
            # Récupérer les RV Gazelle correspondants (inclure description/notes pour parking)
            gazelle_appts = storage.client.table('gazelle_appointments')\
                .select('external_id,technicien,description,notes')\
                .in_('external_id', appointment_ids)\
                .execute()

            # Créer un index par external_id (inclure "À attribuer" aussi)
            tech_by_appt = {apt.get('external_id'): apt.get('technicien') for apt in (gazelle_appts.data or []) if apt.get('technicien')}
            # Index complet des RV Gazelle par external_id (pour extraction parking)
            appt_by_id = {apt.get('external_id'): apt for apt in (gazelle_appts.data or [])}
            # Liste des appointment_id trouvés dans Gazelle (même sans technicien)
            found_appt_ids = {apt.get('external_id') for apt in (gazelle_appts.data or [])}
            
            # Enrichir les demandes
            for request in requests_data:
                appointment_id = request.get("appointment_id")
                if appointment_id:
                    # Si le RV existe dans Gazelle, mettre à jour le statut à CREATED_IN_GAZELLE
                    # MAIS ne pas écraser COMPLETED ou BILLED
                    current_status = request.get("status")
                    if appointment_id in found_appt_ids and current_status not in ("CREATED_IN_GAZELLE", "COMPLETED", "BILLED"):
                        request["status"] = "CREATED_IN_GAZELLE"
                        logging.debug(f"Statut mis à jour à CREATED_IN_GAZELLE pour demande {request.get('id')} (RV trouvé dans Gazelle)")
                    
                    # Récupérer le technicien réel dans Gazelle
                    tech_from_gazelle = tech_by_appt.get(appointment_id)
                    current_tech = request.get("technician_id")
                    
                    # Toujours inclure le technicien de Gazelle pour comparaison
                    if tech_from_gazelle:
                        request["gazelle_technician_id"] = tech_from_gazelle
                    
                    # Vérifier incohérence : technicien PDA différent de Gazelle
                    # IMPORTANT: "À attribuer" = "À attribuer" n'est PAS une incohérence, c'est un état normal
                    A_ATTRIBUER_ID = 'usr_HihJsEgkmpTEziJo'
                    if current_tech and tech_from_gazelle and current_tech != tech_from_gazelle:
                        # Ne pas marquer comme incohérence si les deux sont "À attribuer"
                        if not (current_tech == A_ATTRIBUER_ID and tech_from_gazelle == A_ATTRIBUER_ID):
                            # Incohérence détectée : PDA a un technicien mais Gazelle en a un autre
                            request["technician_mismatch"] = True
                            request["gazelle_technician_id"] = tech_from_gazelle
                            logging.warning(f"Incohérence détectée pour demande {request.get('id')}: PDA={current_tech}, Gazelle={tech_from_gazelle}")
                    
                    # Gazelle est la source de vérité : toujours mettre à jour le technicien depuis Gazelle
                    if tech_from_gazelle:
                        # Si le technicien dans Gazelle est différent de PDA, mettre à jour
                        if current_tech != tech_from_gazelle:
                            request["technician_id"] = tech_from_gazelle
                            request["technician_from_gazelle"] = True
                            if current_tech:
                                # Il y avait une incohérence, on l'a corrigée
                                request["technician_mismatch"] = False
                                logging.info(f"Corrigé technicien pour demande {request.get('id')}: {current_tech} → {tech_from_gazelle} (depuis Gazelle)")
                            else:
                                logging.debug(f"Enrichi demande {request.get('id')} avec technicien {tech_from_gazelle} depuis RV Gazelle")
                        else:
                            # Déjà synchronisé, pas besoin de mettre à jour
                            request["technician_from_gazelle"] = True

                    # NOTE: Le stationnement est extrait uniquement depuis les notes
                    # de service (timeline entries), pas depuis description/notes du RV.
                    # L'extraction se fait dans _extract_parking_from_appointment()
                    # lors de la sync (pas ici en lecture).
        except Exception as e:
            logging.warning(f"Erreur enrichissement technicien depuis Gazelle: {e}")
    
    return requests_data


@router.get("/export")
async def export_csv(month: str = None):
    """
    Export CSV enrichi des demandes Place des Arts.
    Si month est fourni (format YYYY-MM), filtre par ce mois.
    Sinon exporte tout (limit 2000, tri date desc).
    Colonnes ordonnées pour lisibilité.
    """
    import csv
    import io

    storage = get_storage()

    # Construire l'URL avec filtre mois si fourni
    url = f"{storage.api_url}/place_des_arts_requests?select=*&order=appointment_date.desc&limit=2000"
    if month:
        # month = "YYYY-MM" → filtrer appointment_date entre début et premier jour du mois suivant
        from calendar import monthrange
        year, mon = int(month[:4]), int(month[5:7])
        last_day = monthrange(year, mon)[1]
        url += f"&appointment_date=gte.{month}-01&appointment_date=lte.{month}-{last_day}"

    resp = requests.get(url, headers=storage._get_headers())
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)

    data = resp.json()
    filename = f"place_des_arts_{month}.csv" if month else "place_des_arts.csv"

    if not data:
        return StreamingResponse(
            iter(["Aucune donnée"]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )

    # Enrichir avec les descriptions de service Gazelle + service history
    apt_ids = [r.get('appointment_id') for r in data if r.get('appointment_id')]
    gazelle_map = {}
    service_history_map = {}
    if apt_ids:
        try:
            gazelle_result = storage.client.table('gazelle_appointments')\
                .select('external_id,description,notes,piano_external_id,appointment_date')\
                .in_('external_id', apt_ids)\
                .execute()
            gazelle_map = {
                a['external_id']: a.get('description') or a.get('notes') or ''
                for a in (gazelle_result.data or [])
            }

            # Récupérer le service history depuis gazelle_timeline_entries
            # Lien: même piano_external_id + même date que le RV
            piano_date_to_apt = {}  # (piano_id, date) → apt_external_id
            piano_ids_set = set()
            for a in (gazelle_result.data or []):
                pid = a.get('piano_external_id')
                dt = (a.get('appointment_date') or '')[:10]
                if pid and dt:
                    piano_ids_set.add(pid)
                    piano_date_to_apt[(pid, dt)] = a['external_id']

            if piano_ids_set:
                timeline_result = storage.client.table('gazelle_timeline_entries')\
                    .select('piano_id,occurred_at,title,description,entry_type')\
                    .in_('piano_id', list(piano_ids_set))\
                    .in_('entry_type', ['APPOINTMENT_COMPLETION', 'NOTE', 'SERVICE_ENTRY_MANUAL'])\
                    .order('occurred_at', desc=True)\
                    .limit(500)\
                    .execute()

                for te in (timeline_result.data or []):
                    te_date = (te.get('occurred_at') or '')[:10]
                    te_piano = te.get('piano_id')
                    apt_id = piano_date_to_apt.get((te_piano, te_date))
                    if apt_id:
                        desc = te.get('description') or te.get('title') or ''
                        if desc:
                            existing = service_history_map.get(apt_id, '')
                            service_history_map[apt_id] = f"{existing} | {desc}".strip(' |') if existing else desc

        except Exception as e:
            logging.warning(f"Erreur enrichissement Gazelle pour export: {e}")

    # Colonnes ordonnées pour lisibilité
    fieldnames = [
        'appointment_date', 'time', 'room', 'for_who', 'piano',
        'diapason', 'requester', 'technician_id', 'status',
        'billing_amount', 'parking', 'notes', 'gazelle_service_notes',
        'service_history', 'request_date', 'appointment_id', 'id',
    ]

    # Construire les lignes avec les colonnes enrichies
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction='ignore')
    writer.writeheader()
    for row in data:
        apt_id = row.get('appointment_id', '')
        row['gazelle_service_notes'] = gazelle_map.get(apt_id, '')
        row['service_history'] = service_history_map.get(apt_id, '')
        writer.writerow(row)

    csv_content = output.getvalue()
    output.close()

    return StreamingResponse(
        iter([csv_content]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


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


@router.post("/requests/create")
async def create_request(payload: Dict[str, Any]):
    """Crée manuellement une demande PDA."""
    try:
        today_iso = datetime.now(timezone.utc).date().isoformat()
        row = {
            "id": f"pda_manual_{int(datetime.now(timezone.utc).timestamp())}",
            "request_date": today_iso,
            "appointment_date": payload.get("appointment_date") or None,
            "room": payload.get("room") or "",
            "room_original": payload.get("room"),
            "for_who": payload.get("for_who") or "",
            "diapason": payload.get("diapason") or "",
            "requester": payload.get("requester") or "",
            "piano": payload.get("piano") or "",
            "time": payload.get("time") or "",
            "technician_id": payload.get("technician_id") or None,
            "status": payload.get("status") or "PENDING",
            "notes": payload.get("notes") or "",
            "billing_amount": float(payload["billing_amount"]) if payload.get("billing_amount") else None,
            "parking": payload.get("parking") or "",
        }
        # NOTE: Le stationnement est extrait uniquement depuis les notes de service
        # (timeline entries). Pas d'auto-détection dans for_who/notes de la demande.
        # Lier au RV Gazelle si appointment_id fourni (ex: ajout depuis orphelin)
        if payload.get("appointment_id"):
            row["appointment_id"] = payload["appointment_id"]

        manager = get_manager()
        result = manager.import_csv([row], on_conflict="update")

        if result.get("errors"):
            raise HTTPException(status_code=400, detail=str(result["errors"]))

        return {"success": True, "message": "Demande créée", "id": row["id"]}
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Erreur création demande: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


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

    NOUVEAU: Détection intelligente des formats inhabituels
    - Si format habituel (tabulaire, compact) → import direct
    - Si format inhabituel (langage naturel) → demande validation utilisateur
    """
    if not payload.raw_text:
        raise HTTPException(status_code=400, detail="raw_text requis")
    
    # Log pour débogage
    logging.info(f"🔍 Preview appelé avec texte ({len(payload.raw_text)} chars): {payload.raw_text[:200]}")

    # Extraire le demandeur global (signature à la fin du texte complet)
    # Le demandeur est le même pour toutes les demandes collées ensemble
    import re
    raw_text = payload.raw_text.strip()
    lines = raw_text.split('\n')
    requester_mapping = {
        'isabelle': 'IC', 'isabelle clairoux': 'IC', 'clairoux': 'IC',
        'patricia': 'PT', 'annie': 'AJ', 'annie jenkins': 'AJ', 'jenkins': 'AJ'
    }
    global_requester = None
    for line in reversed(lines):
        line_stripped = line.strip().lower()
        if not line_stripped:
            continue
        for name, code in requester_mapping.items():
            if name in line_stripped:
                global_requester = code
                break
        if global_requester:
            break

    from core.feature_flags import is_enabled
    if is_enabled('pda_v6_parser'):
        # V6 parser : tabulaire direct + IA fallback
        from modules.pda_v6_matcher import _format_request  # juste pour vérifier l'import
        from modules.pda_v6_email_parser import parse_email as parse_email_v6
        logging.info(f"📝 Utilisation du parser V6 (IA-assisted)")
        parsed_v6 = parse_email_v6(payload.raw_text)
        # Convertir le format v6 → format attendu par le reste du code
        parsed = []
        for r in parsed_v6:
            from datetime import datetime
            date_val = r.get('appointment_date', '')
            if isinstance(date_val, str) and len(date_val) >= 10:
                try:
                    date_val = datetime.strptime(date_val[:10], '%Y-%m-%d')
                except ValueError:
                    pass
            req_date_val = r.get('request_date')
            if isinstance(req_date_val, str) and len(req_date_val) >= 10:
                try:
                    req_date_val = datetime.strptime(req_date_val[:10], '%Y-%m-%d')
                except ValueError:
                    req_date_val = None
            parsed.append({
                'date': date_val,
                'request_date': req_date_val,
                'room': r.get('room', ''),
                'for_who': r.get('for_who', ''),
                'diapason': r.get('diapason', ''),
                'requester': r.get('requester', ''),
                'piano': r.get('piano', ''),
                'time': r.get('time', ''),
                'confidence': r.get('confidence', 0.9),
                'method': r.get('method', 'v6'),
                'warnings': r.get('warnings', []),
            })
    else:
        logging.info(f"📝 Utilisation de parse_email_text() V5 (regex)")
        parsed = parse_email_text(payload.raw_text)
    
    logging.info(f"🔍 Parsing résultat: {len(parsed)} demande(s) détectée(s)")
    if parsed:
        logging.info(f"   Première demande - champs: date={parsed[0].get('date')}, room={parsed[0].get('room')}, piano={parsed[0].get('piano')}, for_who={parsed[0].get('for_who')}")
    
    if not parsed:
        return {
            "success": True,
            "requests": [],
            "count": 0,
            "warnings": ["Aucune demande détectée dans le texte"],
            "message": "Aucune demande détectée. Vérifiez le format du texte."
        }
    
    # Convertir les datetime en strings pour la réponse JSON
    formatted_requests = []
    all_warnings = []
    for req in parsed:
        formatted_req = req.copy()
        if formatted_req.get('date'):
            formatted_req['date'] = formatted_req['date'].isoformat() if hasattr(formatted_req['date'], 'isoformat') else str(formatted_req['date'])
        if formatted_req.get('request_date'):
            formatted_req['request_date'] = formatted_req['request_date'].isoformat() if hasattr(formatted_req['request_date'], 'isoformat') else str(formatted_req['request_date'])
        # Collecter les warnings
        if formatted_req.get('warnings'):
            all_warnings.extend(formatted_req['warnings'])
        formatted_requests.append(formatted_req)
    
    logging.info(f"📤 Après formatage: {len(formatted_requests)} demande(s)")
    if formatted_requests:
        logging.info(f"   Première demande formatée - champs: date={formatted_requests[0].get('date')}, room={formatted_requests[0].get('room')}, piano={formatted_requests[0].get('piano')}")
    
    # Appliquer le demandeur global si détecté (signature en fin de texte)
    if global_requester:
        for req in formatted_requests:
            if not req.get('requester'):
                req['requester'] = global_requester
    
    # Fusion intelligente: comparer les demandes et fusionner celles qui ont la même date et le même lieu
    # Ne créer une deuxième demande que si l'heure ou le type de piano est explicitement différent
    formatted_requests = merge_duplicate_requests(formatted_requests)
    
    logging.info(f"🔄 Après merge: {len(formatted_requests)} demande(s)")
    if formatted_requests:
        logging.info(f"   Première demande après merge - champs: date={formatted_requests[0].get('date')}, room={formatted_requests[0].get('room')}, piano={formatted_requests[0].get('piano')}")
    
    # Convertir en format preview attendu par le frontend
    preview = []
    for req in formatted_requests:
        # Extraire la date (peut être string ISO ou datetime)
        appt_date = req.get('date')
        appt_date_iso = None
        
        if appt_date:
            if isinstance(appt_date, str):
                # Si c'est une string ISO avec heure (ex: "2026-02-07T00:00:00"), extraire juste la date
                if 'T' in appt_date:
                    appt_date_iso = appt_date.split('T')[0]  # Prendre juste YYYY-MM-DD
                else:
                    # Déjà au format YYYY-MM-DD
                    appt_date_iso = appt_date
            elif hasattr(appt_date, 'date'):
                # Si c'est un datetime, extraire la date
                appt_date_iso = appt_date.date().isoformat()
            else:
                appt_date_iso = str(appt_date)
        
        # Extraire request_date si parsée
        req_date = req.get('request_date')
        req_date_iso = None
        if req_date:
            if isinstance(req_date, str):
                req_date_iso = req_date.split('T')[0] if 'T' in req_date else req_date
            elif hasattr(req_date, 'date'):
                req_date_iso = req_date.date().isoformat()

        preview.append({
            "appointment_date": appt_date_iso,
            "request_date": req_date_iso,
            "room": req.get('room') or None,
            "for_who": req.get('for_who') or None,
            "diapason": req.get('diapason') or None,
            "requester": req.get('requester') or None,
            "piano": req.get('piano') or None,
            "time": req.get('time') or None,
            "service": req.get('service', 'Accord standard') or None,
            "notes": req.get('notes') or None,
            "confidence": req.get('confidence', 0.0),
            "warnings": req.get('warnings', []),
            "needs_validation": req.get('confidence', 0.0) < 1.0 or len(req.get('warnings', [])) > 0
        })
    
    logging.info(f"✅ Format preview final: {len(preview)} demande(s)")
    if preview:
        logging.info(f"   Première demande preview - appointment_date={preview[0].get('appointment_date')}, room={preview[0].get('room')}, piano={preview[0].get('piano')}, for_who={preview[0].get('for_who')}")
    
    # Le frontend attend "preview" et "needs_validation" dans la réponse
    needs_validation = any(req.get('needs_validation', False) for req in preview)
    
    return {
        "success": True,
        "preview": preview,  # Frontend attend "preview" (ligne 649 de PlaceDesArtsDashboard.jsx)
        "requests": preview,  # Garder aussi "requests" pour compatibilité
        "count": len(preview),
        "warnings": all_warnings if all_warnings else [],
        "needs_validation": needs_validation,
        "message": f"{len(preview)} demande(s) détectée(s)"
    }


class ImportPreviewRequest(BaseModel):
    items: List[Dict[str, Any]]


@router.post("/import-preview")
async def import_preview(payload: ImportPreviewRequest):
    """
    Import depuis les données de preview (avec corrections manuelles).
    Utilise directement les données passées sans re-parser.
    """
    try:
        if not payload.items:
            return {"success": True, "imported": 0, "message": "Aucune demande à importer"}

        storage = get_storage()

        def exists_duplicate(row: Dict[str, Any]) -> bool:
            try:
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
                if resp.status_code == 200:
                    data = resp.json()
                    return bool(data and isinstance(data, list) and len(data) > 0)
                return False
            except Exception as e:
                logging.warning(f"Erreur vérification doublon: {e}")
                return False

        rows = []
        duplicates = []
        today_iso = datetime.now(timezone.utc).date().isoformat()

        for idx, item in enumerate(payload.items, start=1):
            try:
                appointment_date = item.get("appointment_date")
                room = item.get("room") or ""
                piano = item.get("piano") or ""
                
                # NOUVEAU: Permettre l'import si au moins un champ essentiel est présent
                # (date, room, ou piano) - l'utilisateur peut compléter le reste plus tard
                if not appointment_date and not room and not piano:
                    logging.warning(f"Item {idx} ignoré: aucun champ essentiel (date, room, piano)")
                    continue

                row = {
                    "id": f"pda_preview_{idx:04d}_{int(datetime.now(timezone.utc).timestamp())}",
                    "request_date": item.get("request_date") or today_iso,
                    "appointment_date": appointment_date or None,  # Permettre None si pas de date
                    "room": item.get("room") or "",
                    "room_original": item.get("room"),
                    "for_who": item.get("for_who") or "",
                    "diapason": item.get("diapason") or "",
                    "requester": item.get("requester") or "",
                    "piano": item.get("piano") or "",
                    "time": item.get("time") or "",
                    "technician_id": None,
                    "status": "PENDING",
                    "notes": item.get("notes") or "",
                }

                if exists_duplicate(row):
                    duplicates.append(row)
                else:
                    rows.append(row)
            except Exception as e:
                logging.warning(f"Erreur traitement item {idx}: {e}")
                continue

        if not rows:
            return {
                "success": True,
                "imported": 0,
                "message": f"Aucune nouvelle demande ({len(duplicates)} doublon(s) détecté(s))"
            }

        manager = get_manager()
        result = manager.import_csv(rows, on_conflict="update")

        if result.get("errors"):
            error_msg = result["errors"] if isinstance(result["errors"], str) else "; ".join(result["errors"]) if isinstance(result["errors"], list) else str(result["errors"])
            raise HTTPException(status_code=400, detail=error_msg)

        return {
            "success": True,
            "imported": result.get("inserted", 0),
            "message": f"{result.get('inserted', 0)} demande(s) importée(s)",
            "duplicates_skipped": len(duplicates)
        }

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Erreur import preview: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erreur lors de l'import: {str(e)}")


@router.post("/import")
async def import_email(payload: ImportRequest):
    """
    Import email/texte : parse, normalise, UPSERT.
    """
    try:
        if not payload.raw_text:
            raise HTTPException(status_code=400, detail="raw_text requis")
        
        parsed = parse_email_text(payload.raw_text)
        if not parsed:
            return {"success": True, "imported": 0, "warnings": ["Aucune demande détectée"], "message": "Aucune demande détectée dans le texte"}

        storage = get_storage()

        def exists_duplicate(row: Dict[str, Any]) -> bool:
            # Critère V4 : même date, salle, pour qui, heure
            try:
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
                if resp.status_code == 200:
                    data = resp.json()
                    return bool(data and isinstance(data, list) and len(data) > 0)
                return False
            except Exception as e:
                logging.warning(f"Erreur vérification doublon: {e}")
                return False

        rows = []
        duplicates = []
        today_iso = datetime.now(timezone.utc).date().isoformat()
        
        for idx, item in enumerate(parsed, start=1):
            try:
                appointment_date = item.get("date")
                if isinstance(appointment_date, datetime):
                    appointment_date = appointment_date.date().isoformat()
                elif not appointment_date:
                    continue  # saute si pas de date

                row = {
                    "id": f"pda_email_{idx:04d}_{int(datetime.now(timezone.utc).timestamp())}",
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
            except Exception as e:
                logging.warning(f"Erreur traitement item {idx}: {e}")
                continue

        if not rows:
            return {
                "success": True,
                "imported": 0,
                "warnings": ["Aucune ligne exploitable (dates manquantes ou doublons existants)"],
                "duplicates": duplicates,
                "message": f"Aucune nouvelle demande ({(len(duplicates))} doublon(s) détecté(s))"
            }

        manager = get_manager()
        result = manager.import_csv(rows, on_conflict="update")
        
        if result.get("errors"):
            error_msg = result["errors"] if isinstance(result["errors"], str) else "; ".join(result["errors"]) if isinstance(result["errors"], list) else str(result["errors"])
            raise HTTPException(status_code=400, detail=error_msg)
        
        return {
            "success": True,
            "imported": result.get("inserted", 0),
            "message": result.get("message", f"{result.get('inserted', 0)} demande(s) importée(s)"),
            "duplicates_skipped": len(duplicates),
            "duplicates": duplicates
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Erreur import email: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erreur lors de l'import: {str(e)}")


class SyncManualRequest(BaseModel):
    request_ids: Optional[List[str]] = None


@router.post("/sync-manual")
async def sync_manual(payload: SyncManualRequest):
    """
    Synchronisation manuelle: Met à jour le statut 'Créé Gazelle' pour les demandes
    qui ont un RV correspondant dans Gazelle.
    
    Trouve automatiquement les RV Gazelle correspondant aux demandes Place des Arts
    et lie les deux systèmes via le champ appointment_id.
    """
    try:
        from modules.place_des_arts.services.gazelle_sync import GazelleSyncService
        
        storage = get_storage()
        sync_service = GazelleSyncService(storage)
        
        # Synchroniser
        result = sync_service.sync_requests_with_gazelle(
            request_ids=payload.request_ids if payload else None,
            dry_run=False
        )
        
        return {
            "success": result.get("success", True),
            "message": result.get("message", "Synchronisation terminée"),
            "updated": result.get("updated", 0),
            "checked": result.get("checked", 0),
            "matched": result.get("matched", 0),
            "details": result.get("details", []),
            "warnings": result.get("warnings", []),
            "has_warnings": len(result.get("warnings", [])) > 0
        }
        
    except Exception as e:
        logging.error(f"Erreur synchronisation: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la synchronisation: {str(e)}"
        )


@router.post("/requests/{request_id}/verify-technician")
async def verify_technician_in_gazelle(
    request_id: str,
    payload: Dict[str, Any]
):
    """
    Vérifie que le technicien spécifié est bien assigné au RV dans Gazelle.
    Retourne {"confirmed": true/false} selon si le technicien correspond.
    """
    try:
        storage = get_storage()
        technician_id = payload.get('technician_id')
        
        if not technician_id:
            return {"confirmed": False, "error": "technician_id requis"}
        
        # Récupérer la demande
        request = storage.get_data(
            "place_des_arts_requests",
            filters={"id": request_id},
            limit=1
        )
        
        if not request:
            return {"confirmed": False, "error": "Demande non trouvée"}
        
        request = request[0]
        appointment_id = request.get('appointment_id')
        
        if not appointment_id:
            return {"confirmed": False, "error": "Pas de RV lié à cette demande"}
        
        # Vérifier le technicien dans le RV Gazelle
        try:
            gazelle_apt = storage.client.table('gazelle_appointments')\
                .select('external_id,technicien')\
                .eq('external_id', appointment_id)\
                .single()\
                .execute()
            
            if gazelle_apt.data:
                gazelle_technician = gazelle_apt.data.get('technicien')
                confirmed = gazelle_technician == technician_id
                
                return {
                    "confirmed": confirmed,
                    "gazelle_technician": gazelle_technician,
                    "requested_technician": technician_id,
                    "message": "Confirmé" if confirmed else f"Le RV dans Gazelle a le technicien: {gazelle_technician}"
                }
            else:
                return {"confirmed": False, "error": "RV non trouvé dans Gazelle"}
                
        except Exception as e:
            logging.error(f"Erreur vérification technicien Gazelle: {e}")
            return {"confirmed": False, "error": str(e)}
            
    except Exception as e:
        logging.error(f"Erreur verify_technician: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la vérification: {str(e)}"
        )


@router.post("/check-completed")
async def check_completed_requests():
    """
    Vérifie toutes les demandes PDA pour trouver les RV complétés dans Gazelle
    qui ne sont pas encore marqués comme complétés.
    
    Cette fonction vérifie :
    - Les demandes déjà liées avec RV complétés
    - Les demandes non liées mais avec RV complétés correspondants
    - Les demandes avec RV trouvés mais pas encore marqués "créé gazelle"
    """
    try:
        from modules.place_des_arts.services.gazelle_sync import GazelleSyncService
        
        storage = get_storage()
        sync_service = GazelleSyncService(storage)
        
        # Récupérer toutes les demandes non complétées
        try:
            result = storage.client.table('place_des_arts_requests')\
                .select('*')\
                .neq('status', 'COMPLETED')\
                .neq('status', 'BILLED')\
                .order('appointment_date', desc=False)\
                .execute()
            
            all_requests = result.data if result.data else []
        except Exception as e:
            logging.error(f"Erreur récupération demandes: {e}")
            raise HTTPException(status_code=500, detail=f"Erreur récupération: {str(e)}")
        
        if not all_requests:
            return {
                "success": True,
                "checked": 0,
                "found_completed": 0,
                "found_unlinked": 0,
                "found_not_created": 0,
                "updated": 0,
                "message": "Aucune demande à vérifier"
            }
        
        # Récupérer tous les RV Gazelle
        gazelle_appointments = sync_service._get_gazelle_appointments()
        gazelle_by_id = {apt.get('external_id'): apt for apt in gazelle_appointments}
        
        found_completed = []
        found_unlinked = []
        found_not_created = []
        
        for request in all_requests:
            request_id = request.get('id')
            appointment_id = request.get('appointment_id')
            status = request.get('status', '')
            
            # Si déjà liée, vérifier le statut du RV
            if appointment_id:
                gazelle_apt = gazelle_by_id.get(appointment_id)
                if gazelle_apt:
                    gazelle_status = gazelle_apt.get('status', '').upper()
                    if gazelle_status in ('COMPLETE', 'COMPLETED'):
                        found_completed.append({
                            'request_id': request_id,
                            'appointment_id': appointment_id,
                            'appointment_date': request.get('appointment_date', '')[:10],
                            'room': request.get('room', ''),
                            'for_who': request.get('for_who', ''),
                            'current_status': status
                        })
            else:
                # Pas de lien, chercher un RV correspondant
                matched_apt = sync_service._find_matching_appointment(
                    request,
                    gazelle_appointments
                )
                
                if matched_apt:
                    apt_id = matched_apt.get('external_id')
                    gazelle_status = matched_apt.get('status', '').upper()
                    
                    if gazelle_status in ('COMPLETE', 'COMPLETED'):
                        found_unlinked.append({
                            'request_id': request_id,
                            'appointment_id': apt_id,
                            'appointment_date': request.get('appointment_date', '')[:10],
                            'room': request.get('room', ''),
                            'for_who': request.get('for_who', ''),
                            'current_status': status
                        })
                    elif status != 'CREATED_IN_GAZELLE':
                        found_not_created.append({
                            'request_id': request_id,
                            'appointment_id': apt_id,
                            'appointment_date': request.get('appointment_date', '')[:10],
                            'room': request.get('room', ''),
                            'for_who': request.get('for_who', ''),
                            'current_status': status
                        })
        
        # Mettre à jour les statuts ET les techniciens en base de données
        updated_count = 0

        # Mettre à jour les demandes avec RV complété (déjà liées)
        for item in found_completed:
            # Extraire le stationnement depuis la description Gazelle
            gazelle_apt = gazelle_by_id.get(item['appointment_id'])
            parking = sync_service._extract_parking_from_appointment(gazelle_apt) if gazelle_apt else None
            if parking:
                logging.info(f"🅿️ Stationnement détecté pour {item['request_id']}: {parking} $")
            success = sync_service._update_request_status(item['request_id'], 'COMPLETED', parking=parking)
            if success:
                updated_count += 1

        # Lier et mettre à jour les demandes avec RV complété (pas liées)
        for item in found_unlinked:
            apt_technician = None
            parking = None
            # Récupérer le technicien et le stationnement du RV
            gazelle_apt = gazelle_by_id.get(item['appointment_id'])
            if gazelle_apt:
                apt_technician = gazelle_apt.get('technicien')
                parking = sync_service._extract_parking_from_appointment(gazelle_apt)
                if parking:
                    logging.info(f"🅿️ Stationnement détecté pour {item['request_id']}: {parking} $")

            link_success = sync_service._link_request_to_appointment(
                item['request_id'],
                item['appointment_id'],
                apt_technician,
                parking=parking
            )

            if link_success:
                status_success = sync_service._update_request_status(item['request_id'], 'COMPLETED', parking=parking)
                if status_success:
                    updated_count += 1

        # Lier et mettre à jour les demandes avec RV trouvé mais pas "créé gazelle"
        for item in found_not_created:
            apt_technician = None
            parking = None
            gazelle_apt = gazelle_by_id.get(item['appointment_id'])
            if gazelle_apt:
                apt_technician = gazelle_apt.get('technicien')
                parking = sync_service._extract_parking_from_appointment(gazelle_apt)
                if parking:
                    logging.info(f"🅿️ Stationnement détecté pour {item['request_id']}: {parking} $")

            link_success = sync_service._link_request_to_appointment(
                item['request_id'],
                item['appointment_id'],
                apt_technician,
                parking=parking
            )

            if link_success:
                updated_count += 1
        
        # IMPORTANT: Synchroniser aussi les techniciens pour toutes les demandes liées
        # pour corriger les incohérences (Gazelle = source de vérité)
        linked_request_ids = [r.get('id') for r in all_requests if r.get('appointment_id')]
        if linked_request_ids:
            try:
                # Récupérer les techniciens depuis Gazelle pour toutes les demandes liées
                linked_appt_ids = [r.get('appointment_id') for r in all_requests if r.get('appointment_id')]
                if linked_appt_ids:
                    linked_gazelle_appts = storage.client.table('gazelle_appointments')\
                        .select('external_id,technicien')\
                        .in_('external_id', linked_appt_ids)\
                        .execute()
                    
                    tech_by_appt_linked = {apt.get('external_id'): apt.get('technicien') 
                                         for apt in (linked_gazelle_appts.data or []) if apt.get('technicien')}
                    
                    # Mettre à jour les techniciens en base pour correspondre à Gazelle
                    for request in all_requests:
                        request_id = request.get('id')
                        appointment_id = request.get('appointment_id')
                        current_tech = request.get('technician_id')
                        gazelle_tech = tech_by_appt_linked.get(appointment_id) if appointment_id else None
                        
                        if gazelle_tech and current_tech != gazelle_tech:
                            # Incohérence détectée, mettre à jour en base
                            try:
                                storage.client.table('place_des_arts_requests')\
                                    .update({
                                        'technician_id': gazelle_tech,
                                        'updated_at': datetime.now().isoformat()
                                    })\
                                    .eq('id', request_id)\
                                    .execute()
                                logging.info(f"Technicien synchronisé en base pour demande {request_id}: {current_tech} → {gazelle_tech}")
                            except Exception as e:
                                logging.warning(f"Erreur mise à jour technicien en base pour {request_id}: {e}")
            except Exception as e:
                logging.warning(f"Erreur synchronisation techniciens en base: {e}")
        
        # Détecter les RV Gazelle PDA sans demande correspondante (orphelins)
        orphan_services = []
        try:
            # Récupérer TOUTES les demandes PDA (incluant COMPLETED/BILLED)
            all_pda_result = storage.client.table('place_des_arts_requests')\
                .select('appointment_id,appointment_date,for_who,room,time')\
                .execute()
            linked_apt_ids = {r['appointment_id'] for r in (all_pda_result.data or []) if r.get('appointment_id')}
            # Garder aussi toutes les demandes pour le matching par scoring
            all_pda_requests = all_pda_result.data or []

            # Récupérer les orphelins ignorés
            dismissed_ids = _get_dismissed_orphan_ids(storage)

            for apt in gazelle_appointments:
                title = (apt.get('title') or '').upper()
                if 'PLACE DES ARTS' not in title:
                    continue
                if apt.get('external_id') in linked_apt_ids:
                    continue
                if apt.get('external_id') in dismissed_ids:
                    continue
                # Vérifier si une demande existante correspond
                from core.feature_flags import is_enabled
                if is_enabled('pda_v6_matcher'):
                    from modules.pda_v6_matcher import matches_request
                    matched = any(matches_request(req, apt, allow_ai=False) for req in all_pda_requests)
                else:
                    matched = sync_service._find_matching_appointment_for_orphan(apt, all_pda_requests)
                if matched:
                    continue
                orphan_services.append({
                    'appointment_id': apt.get('external_id'),
                    'date': (apt.get('appointment_date') or '')[:10],
                    'time': apt.get('appointment_time', ''),
                    'title': apt.get('title', ''),
                    'technician_id': apt.get('technicien'),
                    'status': apt.get('status', ''),
                    'description': apt.get('description') or apt.get('notes') or '',
                })
            if orphan_services:
                logging.info(f"🔍 {len(orphan_services)} service(s) Gazelle PDA sans demande correspondante")
        except Exception as e:
            logging.warning(f"Erreur détection orphelins: {e}")

        return {
            "success": True,
            "checked": len(all_requests),
            "found_completed": len(found_completed),
            "found_unlinked": len(found_unlinked),
            "found_not_created": len(found_not_created),
            "updated": updated_count,
            "orphan_services": orphan_services,
            "details": {
                "completed": found_completed,
                "unlinked": found_unlinked,
                "not_created": found_not_created
            },
            "message": f"{updated_count} demande(s) mise(s) à jour ({len(found_completed)} complétées, {len(found_unlinked)} liées et complétées, {len(found_not_created)} liées)"
        }

    except Exception as e:
        logging.error(f"Erreur vérification complétés: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la vérification: {str(e)}"
        )


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


@router.get("/appointments/today", response_model=Dict[str, Any])
async def get_today_appointments():
    """
    Récupère les rendez-vous du jour pour Place des Arts depuis Supabase.
    Sync matinale à 7h00 et 17h00 via cron job.
    
    Returns:
        {
            "appointments": [
                {
                    "id": "appt_123",
                    "title": "Accord piano",
                    "start": "2024-01-15T09:00:00Z",
                    "duration": 60,
                    "piano_ids": ["ins_abc123", "ins_def456"]
                }
            ],
            "count": 5,
            "date": "2024-01-15"
        }
    """
    try:
        from datetime import date
        from supabase import create_client
        
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        
        if not supabase_url or not supabase_key:
            raise HTTPException(
                status_code=500,
                detail="Configuration Supabase manquante"
            )
        
        supabase = create_client(supabase_url, supabase_key)
        today = date.today().isoformat()
        
        # ID client Place des Arts
        pda_client_id = "cli_HbEwl9rN11pSuDEU"
        
        # Requête Supabase : appointments du jour pour Place des Arts
        # Note: La structure exacte de la table sera déterminée lors de la création du sync
        # Pour l'instant, on récupère tous les appointments du jour
        # TODO: Filtrer par client_id une fois la structure de la table connue
        try:
            response = supabase.table('gazelle_appointments')\
                .select('*')\
                .gte('start_datetime', f'{today}T00:00:00')\
                .lt('start_datetime', f'{today}T23:59:59')\
                .order('start_datetime')\
                .execute()
        except Exception as table_error:
            # Si la table n'existe pas ou a une structure différente, retourner liste vide
            logging.warning(f"⚠️ Table gazelle_appointments non disponible: {table_error}")
            return {
                "appointments": [],
                "count": 0,
                "date": today,
                "note": "Table gazelle_appointments sera créée par le sync matinal"
            }
        
        appointments = response.data if response.data else []
        
        # Formater les données pour le frontend
        formatted_appointments = []
        for apt in appointments:
            # Extraire les piano_ids depuis allEventPianos si disponible
            piano_ids = []
            if apt.get('piano_ids'):
                if isinstance(apt['piano_ids'], list):
                    piano_ids = apt['piano_ids']
                elif isinstance(apt['piano_ids'], str):
                    try:
                        import json
                        piano_ids = json.loads(apt['piano_ids'])
                    except:
                        piano_ids = []
            
            formatted_appointments.append({
                "id": apt.get('id'),
                "title": apt.get('title', 'Rendez-vous'),
                "start": apt.get('start_datetime') or apt.get('start'),
                "duration": apt.get('duration', 60),
                "piano_ids": piano_ids,
                "room": apt.get('room'),
                "for_who": apt.get('for_who')
            })
        
        return {
            "appointments": formatted_appointments,
            "count": len(formatted_appointments),
            "date": today
        }
        
    except Exception as e:
        logging.error(f"❌ Erreur récupération RV du jour: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la récupération des rendez-vous: {str(e)}"
        )


# ── Recherche de concerts ──────────────────────────────────────────

@router.get("/concert-search")
async def search_concert_program(
    for_who: str = Query(..., description="Nom de l'artiste ou ensemble"),
    date: Optional[str] = Query(None, description="Date du rendez-vous (YYYY-MM-DD)"),
    room: Optional[str] = Query(None, description="Code salle (WP, TM, MS, etc.)"),
):
    """
    Recherche le programme de concert sur placedesarts.com
    pour un artiste/ensemble donné, avec date et salle optionnelles.
    """
    result = await rechercher_concert(
        for_who=for_who,
        appointment_date=date,
        room=room,
    )
    return result


# ── Services orphelins ignorés ─────────────────────────────────────

def _get_dismissed_orphan_ids(storage) -> set:
    """Récupère les appointment_ids des orphelins ignorés depuis system_settings."""
    try:
        result = storage.client.table('system_settings')\
            .select('value')\
            .eq('key', 'pda_dismissed_orphans')\
            .execute()
        if result.data and result.data[0].get('value'):
            import json
            ids = json.loads(result.data[0]['value']) if isinstance(result.data[0]['value'], str) else result.data[0]['value']
            return set(ids) if isinstance(ids, list) else set()
    except Exception as e:
        logging.warning(f"Erreur lecture orphelins ignorés: {e}")
    return set()


def _save_dismissed_orphan_ids(storage, ids: set):
    """Sauvegarde les appointment_ids des orphelins ignorés dans system_settings."""
    import json
    value = json.dumps(sorted(ids))
    try:
        # Upsert dans system_settings
        storage.client.table('system_settings')\
            .upsert({'key': 'pda_dismissed_orphans', 'value': value}, on_conflict='key')\
            .execute()
    except Exception as e:
        logging.error(f"Erreur sauvegarde orphelins ignorés: {e}")
        raise


@router.post("/orphans/dismiss")
async def dismiss_orphan(body: dict):
    """Ignorer un service orphelin (persistant)."""
    appointment_id = body.get('appointment_id')
    if not appointment_id:
        raise HTTPException(status_code=400, detail="appointment_id requis")

    storage = get_storage()
    ids = _get_dismissed_orphan_ids(storage)
    ids.add(appointment_id)
    _save_dismissed_orphan_ids(storage, ids)
    return {"success": True, "dismissed_count": len(ids)}


@router.post("/orphans/restore")
async def restore_orphan(body: dict):
    """Restaurer un service orphelin précédemment ignoré."""
    appointment_id = body.get('appointment_id')
    if not appointment_id:
        raise HTTPException(status_code=400, detail="appointment_id requis")

    storage = get_storage()
    ids = _get_dismissed_orphan_ids(storage)
    ids.discard(appointment_id)
    _save_dismissed_orphan_ids(storage, ids)
    return {"success": True, "dismissed_count": len(ids)}


@router.get("/orphans/dismissed")
async def list_dismissed_orphans():
    """Liste les IDs des orphelins ignorés."""
    storage = get_storage()
    ids = _get_dismissed_orphan_ids(storage)
    return {"dismissed_ids": sorted(ids), "count": len(ids)}


# ------------------------------------------------------------
# Scanner Gmail - Import automatique des demandes PDA
# ------------------------------------------------------------

@router.post("/email-scanner/run")
async def run_email_scanner():
    """
    Déclenche manuellement un scan Gmail pour les demandes PDA.

    Scanne la boîte info@piano-tek.com pour les emails de
    @placedesarts.com et @operademontreal.com, parse les demandes,
    les crée dans l'assistant et envoie un récapitulatif.
    """
    try:
        from modules.place_des_arts.services.email_processor import get_email_processor
        processor = get_email_processor()
        result = processor.run_scan()
        return {
            "success": True,
            **result
        }
    except Exception as e:
        logging.error(f"Erreur scan Gmail manuel: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/email-scanner/history")
async def email_scanner_history(limit: int = Query(default=20, le=100)):
    """
    Historique des emails PDA traités automatiquement.

    Retourne les derniers emails scannés avec leur statut,
    nombre de demandes créées, etc.
    """
    try:
        from modules.place_des_arts.services.email_processor import get_email_processor
        processor = get_email_processor()
        history = processor.get_scan_history(limit=limit)
        return {
            "success": True,
            "history": history,
            "count": len(history)
        }
    except Exception as e:
        logging.error(f"Erreur lecture historique scanner: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/email-scanner/status")
async def email_scanner_status():
    """
    Statut du scanner Gmail (connecté, dernière exécution, etc.).
    """
    try:
        from core.gmail_scanner import get_gmail_scanner, OAUTH_CREDENTIALS_PATH, TOKEN_PATH
        scanner = get_gmail_scanner()

        status = {
            "credentials_configured": os.path.exists(OAUTH_CREDENTIALS_PATH),
            "token_exists": os.path.exists(TOKEN_PATH),
            "gmail_connected": False,
            "last_scan": None,
        }

        # Tester la connexion
        if scanner.initialize():
            status["gmail_connected"] = True

        # Dernier scan
        from modules.place_des_arts.services.email_processor import get_email_processor
        processor = get_email_processor()
        history = processor.get_scan_history(limit=1)
        if history:
            status["last_scan"] = {
                "time": history[0].get("processed_at"),
                "emails_found": history[0].get("requests_created", 0),
                "status": history[0].get("status"),
            }

        return {"success": True, **status}
    except Exception as e:
        logging.error(f"Erreur statut scanner: {e}", exc_info=True)
        return {
            "success": False,
            "credentials_configured": False,
            "token_exists": False,
            "gmail_connected": False,
            "error": str(e)
        }
