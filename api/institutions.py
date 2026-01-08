#!/usr/bin/env python3
"""
Routes dynamiques pour TOUTES les institutions - Architecture professionnelle.

Backend 100% agnostique:
- Reçoit /api/{slug}/pianos
- Charge config depuis Supabase institutions table
- Exécute avec le bon client_id Gazelle
- ZÉRO hardcoded credentials

DISCOVERY AUTOMATIQUE:
- Au démarrage, interroge l'API Gazelle pour découvrir les locations
- Mappe automatiquement les noms vers les slugs connus
- Met à jour la table Supabase institutions

Institutions reconnues par nom:
- "Vincent d'Indy" → slug "vincent-dindy"
- "Orford" → slug "orford"
- "Place des Arts" → slug "place-des-arts"
"""

import ast
import logging
import os
import re
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, HTTPException, Query, Path as PathParam
from core.supabase_storage import SupabaseStorage
from core.gazelle_api_client import GazelleAPIClient
from supabase import create_client

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


# Mapping nom → slug pour la reconnaissance automatique
INSTITUTION_NAME_MAPPING = {
    # Vincent d'Indy - règles prioritaires (ordre important pour matching)
    "École de musique Vincent-d'Indy": "vincent-dindy",  # Nom exact depuis Gazelle
    "école de musique vincent-d'indy": "vincent-dindy",  # Version minuscule
    "vincent d'indy": "vincent-dindy",
    "vincent-dindy": "vincent-dindy",
    # Autres institutions
    "orford": "orford",
    "centre d'arts orford": "orford",
    "place des arts": "place-des-arts",
    "place-des-arts": "place-des-arts",
}


def normalize_institution_name(name: str) -> str:
    """
    Normalise un nom d'institution pour la comparaison.
    
    Args:
        name: Nom brut de l'institution
        
    Returns:
        Nom normalisé (lowercase, accents normalisés, espaces normalisés)
    """
    if not name:
        return ""
    
    # Convertir en minuscules
    normalized = name.lower().strip()
    
    # Normaliser les espaces multiples
    normalized = re.sub(r'\s+', ' ', normalized)
    
    return normalized


def match_institution_slug(company_name: str) -> Optional[str]:
    """
    Essaie de matcher un nom d'entreprise avec un slug d'institution connu.
    
    Args:
        company_name: Nom de l'entreprise depuis Gazelle
        
    Returns:
        Slug de l'institution si match trouvé, None sinon
    """
    normalized = normalize_institution_name(company_name)
    
    # Chercher un match exact ou partiel
    for known_name, slug in INSTITUTION_NAME_MAPPING.items():
        if known_name in normalized or normalized in known_name:
            return slug
    
    return None


def discover_and_sync_institutions() -> Dict[str, Any]:
    """
    Discovery automatique: Interroge l'API Gazelle pour récupérer les locations
    et synchronise avec la table Supabase institutions.
    
    Cette fonction:
    1. Récupère tous les clients depuis l'API Gazelle
    2. Pour chaque client, essaie de matcher avec un slug connu
    3. Met à jour ou insère dans la table Supabase institutions
    
    Returns:
        Dict avec le résultat de la synchronisation
    """
    try:
        # 1. Initialiser clients Supabase et Gazelle
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        
        if not supabase_url or not supabase_key:
            logging.error("❌ Configuration Supabase manquante pour discovery")
            return {"success": False, "error": "Configuration Supabase manquante"}
        
        supabase = create_client(supabase_url, supabase_key)
        
        api_client = get_api_client()
        if not api_client:
            logging.error("❌ Client API Gazelle non disponible pour discovery")
            return {"success": False, "error": "Client API Gazelle non disponible"}
        
        logging.info("🔍 Discovery automatique des institutions depuis Gazelle...")
        
        # 2. Récupérer tous les clients depuis Gazelle
        clients = api_client.get_clients(limit=1000)
        logging.info(f"📋 {len(clients)} clients récupérés depuis Gazelle")
        
        # 3. Pour chaque client, essayer de matcher avec un slug connu
        synced_count = 0
        matched_clients = {}
        
        # Mapping forcé pour Vincent d'Indy (prioritaire)
        FORCED_MAPPINGS = {
            "vincent-dindy": {
                "slug": "vincent-dindy",
                "name": "École de musique Vincent-d'Indy",
                "gazelle_client_id": "cli_9UMLkteep8EsISbG"
            }
        }
        
        for client in clients:
            client_id = client.get('id')
            company_name = client.get('companyName', '')
            
            if not client_id or not company_name:
                continue
            
            # Essayer de matcher avec un slug connu
            slug = match_institution_slug(company_name)
            
            if slug:
                matched_clients[slug] = {
                    "slug": slug,
                    "name": company_name,
                    "gazelle_client_id": client_id
                }
                logging.info(f"✅ Match trouvé: '{company_name}' → slug '{slug}' (ID: {client_id})")
        
        # Appliquer les mappings forcés (priorité sur les matches automatiques)
        for slug, forced_data in FORCED_MAPPINGS.items():
            matched_clients[slug] = forced_data
            logging.info(f"✅ Mapping forcé: '{forced_data['name']}' → slug '{slug}' (ID: {forced_data['gazelle_client_id']})")
        
        # 4. Mettre à jour ou insérer dans Supabase
        for slug, institution_data in matched_clients.items():
            try:
                # Upsert dans la table institutions
                response = supabase.table('institutions').upsert({
                    "slug": slug,
                    "name": institution_data["name"],
                    "gazelle_client_id": institution_data["gazelle_client_id"],
                    "active": True
                }, on_conflict="slug").execute()
                
                synced_count += 1
                logging.info(f"✅ Institution '{slug}' synchronisée dans Supabase")
                
            except Exception as e:
                logging.error(f"❌ Erreur synchronisation {slug}: {e}")
        
        logging.info(f"✅ Discovery terminée: {synced_count} institutions synchronisées")
        
        return {
            "success": True,
            "synced_count": synced_count,
            "institutions": list(matched_clients.keys())
        }
        
    except Exception as e:
        logging.error(f"❌ Erreur lors du discovery: {e}")
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}


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

    # Normaliser le slug (strip + lowercase)
    slug = slug.strip().lower()
    
    # Mapping spécial pour place-des-arts (sans espace)
    if slug == "place des arts" or slug == "place-des-arts":
        slug = "place-des-arts"

    logging.info(f"🔍 get_institution_config appelé avec slug: '{slug}'")

    # Cache de 60 secondes
    current_time = time.time()
    if current_time - _cache_timestamp > 60:
        _institutions_cache = {}
        _cache_timestamp = current_time

    # Vérifier le cache
    if slug in _institutions_cache:
        logging.info(f"✅ Config trouvée dans le cache pour '{slug}'")
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
        query AllPianos($clientId: String!) {
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

        result = api_client._execute_query(query, {"clientId": str(client_id)})
        gazelle_pianos = result.get("data", {}).get("allPianos", {}).get("nodes", [])

        logging.info(f"📋 {len(gazelle_pianos)} pianos Gazelle pour {institution}")

        # 2. Charger modifications Supabase filtrées par institution
        storage = get_supabase_storage()
        supabase_updates = storage.get_all_piano_updates(institution_slug=institution)

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
                # Pour Orford: ne pas inclure les notes Gazelle dans aFaire et observations
                # Seulement afficher les notes créées dans l'Assistant (Supabase)
                "aFaire": updates.get('a_faire', '') if institution != 'orford' else (updates.get('a_faire', '') if updates.get('a_faire') else ''),
                "travail": updates.get('travail', ''),
                "observations": updates.get('observations', gz_piano.get('notes', '') if institution != 'orford' else ''),
                "is_work_completed": updates.get('is_work_completed', False),
                "sync_status": updates.get('sync_status', 'pending'),
                "tags": tags,
                "hasNonTag": has_non_tag,
                "is_hidden": updates.get('is_hidden', False),
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


@router.put("/{institution}/pianos/{piano_id}")
async def update_institution_piano(
    institution: str = PathParam(..., description="Institution slug"),
    piano_id: str = PathParam(..., description="ID du piano"),
    update: Dict[str, Any] = {}
):
    """
    Met à jour un piano pour une institution donnée.

    Stocke les modifications dans Supabase (overlays au-dessus de Gazelle).

    Args:
        institution: Slug de l'institution (vincent-dindy, orford, etc.)
        piano_id: ID Gazelle du piano (ex: ins_xxx)
        update: Dict avec les champs à mettre à jour

    Returns:
        {"success": true, "piano_id": "ins_xxx", "updates": {...}}
    """
    try:
        # 1. Valider que l'institution existe
        config = get_institution_config(institution)

        # 2. Sauvegarder dans Supabase
        storage = get_supabase_storage()

        # Convertir camelCase vers snake_case si nécessaire
        update_data = {}
        for key, value in update.items():
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
                update_data[key] = value

        # Logique de transition d'état automatique
        if ('travail' in update_data or 'observations' in update_data) and \
           update_data.get('is_work_completed') == False and \
           'status' not in update_data:
            update_data['status'] = 'work_in_progress'

        if update_data.get('is_work_completed') == True and 'status' not in update_data:
            update_data['status'] = 'completed'
            if 'completed_at' not in update_data:
                from datetime import datetime
                update_data['completed_at'] = datetime.now().isoformat()

        success = storage.update_piano(piano_id, update_data, institution_slug=institution)

        if not success:
            raise HTTPException(status_code=500, detail="Échec sauvegarde Supabase")

        return {
            "success": True,
            "message": "Piano mis à jour avec succès",
            "piano_id": piano_id,
            "updates": update_data
        }

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"❌ Erreur update piano {piano_id} pour {institution}: {e}")
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

        # Récupérer les profils utilisateurs pour mapper updated_by (email) vers first_name
        users_map = {}
        try:
            from supabase import create_client
            supabase_url = os.getenv("SUPABASE_URL")
            supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
            if supabase_url and supabase_key:
                supabase = create_client(supabase_url, supabase_key)
                users_response = supabase.table('users').select('email,first_name').execute()
                if users_response.data:
                    for user in users_response.data:
                        email_raw = user.get('email')
                        if email_raw:
                            email = email_raw.lower()
                            # Utiliser first_name
                            name = user.get('first_name') or ''
                            if email and name:
                                users_map[email] = name
        except Exception as e:
            logging.warning(f"⚠️ Impossible de charger les profils utilisateurs: {e}")
        
        activities = []
        for piano_id, update_data in all_updates.items():
            if update_data.get('updated_by') and update_data.get('updated_at'):
                updated_by_raw = update_data.get('updated_by', '')
                updated_by_email = updated_by_raw.lower() if updated_by_raw else ''
                # Mapper email vers first_name si disponible
                technician_name = users_map.get(updated_by_email, updated_by_email) if updated_by_email else updated_by_raw
                
                activities.append({
                    "piano_id": piano_id,
                    "updated_by": technician_name,  # Utiliser prenom au lieu de email
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


@router.get("/{institution}/tournees")
async def get_institution_tournees(
    institution: str = PathParam(..., description="Slug de l'institution (vincent-dindy, orford, etc.)")
):
    """
    Récupère toutes les tournées pour une institution depuis Supabase.

    Filtre par le champ 'etablissement' dans la table tournees.

    Args:
        institution: Slug de l'institution (vincent-dindy, orford, place-des-arts)

    Returns:
        {
            "tournees": [...],
            "count": 10,
            "institution": "Vincent d'Indy"
        }
    """
    try:
        # 1. Charger config institution (pour validation + nom)
        config = get_institution_config(institution)
        institution_name = config.get('name', institution)

        # 2. Charger tournées depuis Supabase avec filtre etablissement
        from supabase import create_client

        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

        if not supabase_url or not supabase_key:
            raise HTTPException(status_code=500, detail="Configuration Supabase manquante")

        supabase = create_client(supabase_url, supabase_key)

        # Filtre par etablissement
        response = supabase.table('tournees').select('*').eq('etablissement', institution).execute()

        tournees = response.data if response.data else []

        logging.info(f"✅ {len(tournees)} tournées récupérées pour {institution}")

        return {
            "tournees": tournees,
            "count": len(tournees),
            "institution": institution_name
        }

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"❌ Erreur chargement tournées {institution}: {e}")
        import traceback
        traceback.print_exc()
        return {"tournees": [], "count": 0, "error": str(e)}


@router.post("/{institution}/clean-orphan-statuses")
async def clean_orphan_statuses(
    institution: str = PathParam(..., description="Slug de l'institution (orford uniquement pour l'instant)")
):
    """
    Nettoie les statuts 'proposed' orphelins pour une institution.
    
    Un piano avec status='proposed' est considéré orphelin s'il n'est dans AUCUNE tournée
    (peu importe le statut de la tournée: en_cours, planifiee, terminee, etc.)
    
    Pour Orford, cela garantit qu'un piano ne peut avoir le statut 'À faire' que s'il est
    effectivement rattaché à une tournée.
    
    Args:
        institution: Slug de l'institution (ex: 'orford')
        
    Returns:
        {
            "success": True,
            "cleaned_count": 5,
            "message": "5 statuts orphelins nettoyés"
        }
    """
    try:
        storage = get_supabase_storage()
        from supabase import create_client
        import os
        
        # Charger config
        config = get_institution_config(institution)
        
        # Pour l'instant, on ne nettoie que Orford
        if institution != 'orford':
            return {
                "success": False,
                "message": f"Nettoyage des statuts orphelins non implémenté pour {institution}"
            }
        
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        
        if not supabase_url or not supabase_key:
            raise HTTPException(status_code=500, detail="Configuration Supabase manquante")
        
        supabase = create_client(supabase_url, supabase_key)
        
        # 1. Récupérer toutes les tournées de l'institution
        tournees_response = supabase.table('tournees').select('id,piano_ids').eq('etablissement', institution).execute()
        tournees = tournees_response.data if tournees_response.data else []
        
        # 2. Créer un set de tous les piano_ids présents dans les tournées
        piano_ids_in_tournees = set()
        for tournee in tournees:
            piano_ids = tournee.get('piano_ids', [])
            if piano_ids:
                if isinstance(piano_ids, str):
                    import json
                    piano_ids = json.loads(piano_ids)
                piano_ids_in_tournees.update(piano_ids)
        
        logging.info(f"📊 {len(piano_ids_in_tournees)} pianos trouvés dans les tournées de {institution}")
        
        # 3. Récupérer tous les piano_updates pour Orford avec status='proposed'
        supabase_updates = storage.get_all_piano_updates(institution_slug=institution)
        
        # 4. Identifier les orphelins (status=proposed mais pas dans une tournée)
        orphan_piano_ids = []
        for piano_id, update_data in supabase_updates.items():
            if update_data.get('status') == 'proposed':
                # Vérifier si le piano est dans une tournée
                if piano_id not in piano_ids_in_tournees:
                    orphan_piano_ids.append(piano_id)
        
        logging.info(f"🔍 {len(orphan_piano_ids)} pianos orphelins identifiés pour {institution}")
        
        # 5. Nettoyer les statuts orphelins (mettre à 'normal')
        cleaned_count = 0
        for piano_id in orphan_piano_ids:
            try:
                success = storage.update_piano(
                    piano_id,
                    {'status': 'normal'},
                    institution_slug=institution
                )
                if success:
                    cleaned_count += 1
                    logging.info(f"✅ Statut nettoyé pour piano {piano_id}")
            except Exception as e:
                logging.error(f"❌ Erreur nettoyage piano {piano_id}: {e}")
        
        return {
            "success": True,
            "cleaned_count": cleaned_count,
            "orphan_count": len(orphan_piano_ids),
            "message": f"{cleaned_count} statuts orphelins nettoyés pour {institution}"
        }
        
    except Exception as e:
        logging.error(f"❌ Erreur nettoyage statuts orphelins: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Erreur lors du nettoyage: {str(e)}")


@router.delete("/{institution}/tournees/{tournee_id}")
async def delete_institution_tournee(
    institution: str = PathParam(..., description="Slug de l'institution"),
    tournee_id: str = PathParam(..., description="ID de la tournée à supprimer")
):
    """
    Supprime une tournée pour une institution donnée.

    Args:
        institution: Slug de l'institution (vincent-dindy, orford, etc.)
        tournee_id: ID de la tournée à supprimer

    Returns:
        {
            "success": true,
            "message": "Tournée supprimée avec succès"
        }
    """
    try:
        # 1. Valider que l'institution existe
        config = get_institution_config(institution)

        # 2. Supprimer la tournée dans Supabase
        from supabase import create_client

        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

        if not supabase_url or not supabase_key:
            raise HTTPException(status_code=500, detail="Configuration Supabase manquante")

        supabase = create_client(supabase_url, supabase_key)

        # Vérifier que la tournée appartient à l'institution
        response = supabase.table('tournees').select('*').eq('id', tournee_id).execute()

        if not response.data or len(response.data) == 0:
            raise HTTPException(status_code=404, detail="Tournée non trouvée")

        tournee = response.data[0]
        if tournee.get('etablissement') != institution:
            raise HTTPException(
                status_code=403,
                detail=f"Cette tournée appartient à {tournee.get('etablissement')}, pas à {institution}"
            )

        # Supprimer la tournée
        delete_response = supabase.table('tournees').delete().eq('id', tournee_id).execute()

        logging.info(f"✅ Tournée {tournee_id} supprimée pour {institution}")

        return {
            "success": True,
            "message": "Tournée supprimée avec succès"
        }

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"❌ Erreur suppression tournée {tournee_id} pour {institution}: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{institution}/pianos-ready-for-push")
async def get_institution_pianos_ready_for_push(
    institution: str = PathParam(..., description="Slug de l'institution"),
    tournee_id: Optional[str] = Query(None, description="Filtrer par tournée"),
    limit: int = Query(100, description="Nombre max de pianos")
):
    """
    Récupère les pianos prêts à être pushés vers Gazelle pour une institution.

    Critères:
    - status = 'completed'
    - is_work_completed = true
    - sync_status IN ('pending', 'modified', 'error')
    - travail OR observations non NULL
    - institution_slug = {institution}

    Args:
        institution: Slug de l'institution
        tournee_id: Filtrer par tournée spécifique (optionnel)
        limit: Nombre maximum de pianos (défaut: 100)

    Returns:
        {
            "pianos": [...],
            "count": 5,
            "ready_for_push": true
        }
    """
    try:
        # 1. Valider que l'institution existe
        config = get_institution_config(institution)

        # 2. Construire la requête SQL avec filtre institution
        from supabase import create_client

        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

        if not supabase_url or not supabase_key:
            raise HTTPException(status_code=500, detail="Configuration Supabase manquante")

        supabase = create_client(supabase_url, supabase_key)

        logging.info(f"🔍 Recherche pianos prêts pour push - institution={institution}, tournee_id={tournee_id}, limit={limit}")

        # Construire les filtres
        query = supabase.table('vincent_dindy_piano_updates').select('*')

        # Filtrer par institution
        query = query.eq('institution_slug', institution)

        # Filtrer par critères de push
        query = query.eq('status', 'completed')
        query = query.eq('is_work_completed', True)
        query = query.in_('sync_status', ['pending', 'modified', 'error'])

        # Filtrer par tournée si spécifiée
        if tournee_id:
            query = query.eq('completed_in_tournee_id', tournee_id)

        # Limiter les résultats
        query = query.limit(limit)

        # Ordre: erreurs en premier, puis modifiés, puis pending
        query = query.order('sync_status')
        query = query.order('updated_at', desc=True)

        response = query.execute()
        pianos = response.data if response.data else []

        # Filtrer pour garder seulement ceux avec travail OU observations
        pianos = [
            p for p in pianos
            if (p.get('travail') and p.get('travail').strip()) or
               (p.get('observations') and p.get('observations').strip())
        ]

        logging.info(f"✅ {len(pianos)} pianos prêts pour push pour {institution}")

        return {
            "pianos": pianos,
            "count": len(pianos),
            "ready_for_push": len(pianos) > 0
        }

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"❌ Erreur récupération pianos prêts pour {institution}: {e}")
        import traceback
        traceback.print_exc()
        # Retourner une liste vide plutôt que de faire échouer l'endpoint
        return {
            "pianos": [],
            "count": 0,
            "ready_for_push": False,
            "error": str(e)
        }
