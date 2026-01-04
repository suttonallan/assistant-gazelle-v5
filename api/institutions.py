#!/usr/bin/env python3
"""
Routes dynamiques pour TOUTES les institutions.

Une seule route /{institution}/pianos gère Vincent d'Indy, Orford, et toutes les futures écoles.
Configuration dans config/institutions.json - ajouter une école = ajouter 3 lignes JSON.
"""

import json
import os
import ast
import logging
from pathlib import Path
from fastapi import APIRouter, HTTPException, Query, Path as PathParam
from typing import Dict, Any
from core.supabase_storage import SupabaseStorage
from core.gazelle_api_client import GazelleAPIClient

router = APIRouter(tags=["institutions"])

# Charger la config des institutions
CONFIG_PATH = Path(__file__).parent.parent / "config" / "institutions.json"
INSTITUTIONS = {}

try:
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        INSTITUTIONS = json.load(f)
    logging.info(f"✅ {len(INSTITUTIONS)} institutions chargées: {list(INSTITUTIONS.keys())}")
except Exception as e:
    logging.error(f"❌ Erreur chargement config institutions: {e}")
    INSTITUTIONS = {
        "vincent-dindy": {
            "name": "Vincent d'Indy",
            "client_id": "cli_9UMLkteep8EsISbG"
        }
    }

# Singletons
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
            logging.warning(f"⚠️ Client API Gazelle non disponible: {e}")
            _api_client = None
    return _api_client


@router.get("/{institution}/pianos", response_model=Dict[str, Any])
async def get_institution_pianos(
    institution: str = PathParam(..., description="Institution key (ex: vincent-dindy, orford)"),
    include_inactive: bool = Query(False, description="Inclure les pianos masqués")
) -> Dict[str, Any]:
    """
    Route DYNAMIQUE pour charger les pianos de N'IMPORTE QUELLE institution.

    Path params:
        institution: Clé de l'institution (vincent-dindy, orford, etc.)

    Query params:
        include_inactive: Si True, inclut les pianos avec tag "non"

    Returns:
        {
            "pianos": [...],
            "count": 42,
            "institution": "Vincent d'Indy"
        }

    Ajouter une nouvelle école:
        1. Ouvrir config/institutions.json
        2. Ajouter 3 lignes:
           "nouvelle-ecole": {
             "name": "Nouvelle École",
             "client_id": "cli_xxxxx"
           }
        3. C'est tout! Pas besoin de toucher au code ni à Render.
    """
    # Vérifier que l'institution existe
    if institution not in INSTITUTIONS:
        raise HTTPException(
            status_code=404,
            detail=f"Institution '{institution}' inconnue. Institutions disponibles: {list(INSTITUTIONS.keys())}"
        )

    config = INSTITUTIONS[institution]
    client_id = config["client_id"]

    try:
        api_client = get_api_client()
        if not api_client:
            raise HTTPException(status_code=500, detail="Client API Gazelle non disponible")

        logging.info(f"🔍 Chargement pianos {institution} (client_id: {client_id})")

        # 1. Charger pianos depuis Gazelle
        query = """
        query AllPianos($clientId: ID!) {
          allPianos(clientId: $clientId) {
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

        result = api_client._execute_query(query, {"clientId": client_id})
        gazelle_pianos = result.get("data", {}).get("allPianos", {}).get("nodes", [])

        logging.info(f"📋 {len(gazelle_pianos)} pianos Gazelle pour {institution}")

        # 2. Charger modifications Supabase
        storage = get_supabase_storage()
        supabase_updates = storage.get_all_piano_updates()

        # 3. Fusion
        pianos = []
        for gz_piano in gazelle_pianos:
            gz_id = gz_piano['id']
            serial = gz_piano.get('serialNumber', gz_id)

            # Trouver updates Supabase
            updates = {}
            for piano_id, data in supabase_updates.items():
                if piano_id == gz_id or piano_id == serial:
                    updates = data
                    break

            # Parser tags
            tags_raw = gz_piano.get('tags', '')
            tags = []
            if tags_raw:
                try:
                    if isinstance(tags_raw, list):
                        tags = tags_raw
                    elif isinstance(tags_raw, str):
                        tags = ast.literal_eval(tags_raw)
                except:
                    tags = []

            has_non_tag = 'non' in [t.lower() for t in tags]

            # Filtrer pianos inactifs
            if not include_inactive and has_non_tag:
                continue

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
                "is_work_completed": updates.get('is_work_completed', False),
                "sync_status": updates.get('sync_status', 'pending'),
                "tags": tags,
                "hasNonTag": has_non_tag,
                "isInCsv": updates.get('is_in_csv', True),
                "gazelleStatus": gz_piano.get('status', 'UNKNOWN'),
                "institution": institution
            }

            pianos.append(piano)

        logging.info(f"✅ {len(pianos)} pianos retournés pour {institution}")

        return {
            "pianos": pianos,
            "count": len(pianos),
            "institution": config["name"]
        }

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"❌ Erreur chargement pianos {institution}: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")


@router.get("/{institution}/activity", response_model=Dict[str, Any])
async def get_institution_activity(
    institution: str = PathParam(..., description="Institution key"),
    limit: int = Query(20, description="Nombre max d'activités")
) -> Dict[str, Any]:
    """Route dynamique pour l'historique d'activité d'une institution."""
    if institution not in INSTITUTIONS:
        raise HTTPException(status_code=404, detail=f"Institution '{institution}' inconnue")

    try:
        storage = get_supabase_storage()
        all_updates = storage.get_all_piano_updates()

        activities = []
        for piano_id, update_data in all_updates.items():
            if update_data.get('updated_by') and update_data.get('updated_at'):
                activities.append({
                    "piano_id": piano_id,
                    "updated_by": update_data.get('updated_by'),
                    "updated_at": update_data.get('updated_at'),
                    "status": update_data.get('status'),
                    "observations": update_data.get('observations', ''),
                    "institution": institution
                })

        activities.sort(key=lambda x: x.get('updated_at', ''), reverse=True)

        return {
            "activities": activities[:limit],
            "total": len(activities),
            "institution": INSTITUTIONS[institution]["name"]
        }

    except Exception as e:
        logging.error(f"❌ Erreur activité {institution}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{institution}/stats", response_model=Dict[str, Any])
async def get_institution_stats(
    institution: str = PathParam(..., description="Institution key")
) -> Dict[str, Any]:
    """Route dynamique pour les statistiques d'une institution."""
    if institution not in INSTITUTIONS:
        raise HTTPException(status_code=404, detail=f"Institution '{institution}' inconnue")

    try:
        data = await get_institution_pianos(institution, include_inactive=True)
        all_pianos = data["pianos"]

        pianos_actifs = sum(1 for p in all_pianos if not p.get("hasNonTag", False))
        pianos_masques = sum(1 for p in all_pianos if p.get("hasNonTag", False))

        return {
            "total_pianos": len(all_pianos),
            "pianos_actifs": pianos_actifs,
            "pianos_masques": pianos_masques,
            "institution": INSTITUTIONS[institution]["name"]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
