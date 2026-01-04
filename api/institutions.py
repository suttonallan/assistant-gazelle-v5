#!/usr/bin/env python3
"""
Routes dynamiques pour TOUTES les institutions - Architecture professionnelle.

Backend 100% agnostique:
- Reçoit /api/{slug}/pianos
- Charge config depuis Supabase institutions table
- Exécute avec le bon client_id Gazelle
- ZÉRO hardcoded credentials

Ajouter une institution:
1. INSERT INTO institutions (slug, name, gazelle_client_id) VALUES ('orford', 'Orford', 'cli_xxx');
2. C'est tout! Routes disponibles immédiatement.
"""

import ast
import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Query, Path as PathParam
from core.supabase_storage import SupabaseStorage
from core.gazelle_api_client import GazelleAPIClient

router = APIRouter(tags=["institutions"])

# Singletons
_supabase_storage = None
_api_client = None
_institutions_cache = {}
_cache_timestamp = 0


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


def get_institution_config(slug: str) -> Dict[str, Any]:
    """
    Charge la config d'une institution depuis Supabase.

    Cache de 60 secondes pour éviter des requêtes DB à chaque appel.

    Args:
        slug: Identifiant de l'institution (vincent-dindy, orford, etc.)

    Returns:
        Dict avec: name, gazelle_client_id, options

    Raises:
        HTTPException 404: Institution non trouvée
        HTTPException 500: Erreur DB
    """
    import time
    global _institutions_cache, _cache_timestamp

    # Cache de 60 secondes
    current_time = time.time()
    if current_time - _cache_timestamp > 60:
        _institutions_cache = {}
        _cache_timestamp = current_time

    # Vérifier le cache
    if slug in _institutions_cache:
        return _institutions_cache[slug]

    # Charger depuis Supabase
    try:
        from supabase import create_client
        import os

        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

        if not supabase_url or not supabase_key:
            raise HTTPException(
                status_code=500,
                detail="Configuration Supabase manquante (SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)"
            )

        supabase = create_client(supabase_url, supabase_key)

        # Query institutions table
        response = supabase.table('institutions').select('*').eq('slug', slug).eq('active', True).execute()

        if not response.data or len(response.data) == 0:
            raise HTTPException(
                status_code=404,
                detail=f"Institution '{slug}' non trouvée. Vérifier la table institutions dans Supabase."
            )

        config = response.data[0]

        # Valider que le client_id existe
        if not config.get('gazelle_client_id'):
            raise HTTPException(
                status_code=500,
                detail=f"Institution '{slug}' n'a pas de gazelle_client_id configuré"
            )

        # Mettre en cache
        _institutions_cache[slug] = config

        logging.info(f"✅ Config chargée pour {slug}: {config['name']}")

        return config

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"❌ Erreur chargement config {slug}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors du chargement de la configuration: {str(e)}"
        )


@router.get("/{institution}/pianos", response_model=Dict[str, Any])
async def get_institution_pianos(
    institution: str = PathParam(..., description="Institution slug (ex: vincent-dindy, orford)"),
    include_inactive: bool = Query(False, description="Inclure les pianos masqués")
) -> Dict[str, Any]:
    """
    Route DYNAMIQUE 100% agnostique pour charger les pianos.

    Backend agnostique:
    1. Reçoit /{institution}/pianos
    2. SELECT * FROM institutions WHERE slug = {institution}
    3. Utilise le gazelle_client_id de la DB
    4. Charge les pianos Gazelle
    5. Fusionne avec Supabase overlays

    Ajouter une institution (10 secondes):
        INSERT INTO institutions (slug, name, gazelle_client_id)
        VALUES ('orford', 'Orford', 'cli_xxxxx');

    Returns:
        {
            "pianos": [...],
            "count": 42,
            "institution": "Vincent d'Indy"
        }
    """
    # Charger config depuis Supabase
    config = get_institution_config(institution)
    client_id = config['gazelle_client_id']

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
            "institution": config['name']
        }

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"❌ Erreur chargement pianos {institution}: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")


@router.get("/{institution}/activity", response_model=Dict[str, Any])
async def get_institution_activity(
    institution: str = PathParam(..., description="Institution slug"),
    limit: int = Query(20, description="Nombre max d'activités")
) -> Dict[str, Any]:
    """Route dynamique pour l'historique d'activité."""
    config = get_institution_config(institution)

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
            "institution": config['name']
        }

    except Exception as e:
        logging.error(f"❌ Erreur activité {institution}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{institution}/stats", response_model=Dict[str, Any])
async def get_institution_stats(
    institution: str = PathParam(..., description="Institution slug")
) -> Dict[str, Any]:
    """Route dynamique pour les statistiques."""
    config = get_institution_config(institution)

    try:
        data = await get_institution_pianos(institution, include_inactive=True)
        all_pianos = data["pianos"]

        pianos_actifs = sum(1 for p in all_pianos if not p.get("hasNonTag", False))
        pianos_masques = sum(1 for p in all_pianos if p.get("hasNonTag", False))

        return {
            "total_pianos": len(all_pianos),
            "pianos_actifs": pianos_actifs,
            "pianos_masques": pianos_masques,
            "institution": config['name']
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/institutions/list", response_model=Dict[str, Any])
async def list_institutions() -> Dict[str, Any]:
    """
    Liste toutes les institutions actives disponibles.

    Utile pour générer dynamiquement les menus frontend.

    Returns:
        {
            "institutions": [
                {"slug": "vincent-dindy", "name": "Vincent d'Indy"},
                {"slug": "orford", "name": "Orford"}
            ],
            "count": 2
        }
    """
    try:
        from supabase import create_client
        import os

        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

        if not supabase_url or not supabase_key:
            raise HTTPException(status_code=500, detail="Configuration Supabase manquante")

        supabase = create_client(supabase_url, supabase_key)

        response = supabase.table('institutions').select('slug, name, options').eq('active', True).execute()

        institutions = [
            {
                "slug": inst['slug'],
                "name": inst['name'],
                "options": inst.get('options', {})
            }
            for inst in response.data
        ]

        return {
            "institutions": institutions,
            "count": len(institutions)
        }

    except Exception as e:
        logging.error(f"❌ Erreur liste institutions: {e}")
        raise HTTPException(status_code=500, detail=str(e))
