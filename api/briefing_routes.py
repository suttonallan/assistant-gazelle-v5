#!/usr/bin/env python3
"""
API Routes pour les Briefings Intelligents - "Ma Journée" V4

Endpoints:
- GET /briefing/daily - Briefings narratifs du jour
- GET /briefing/client/{id} - Briefing détaillé d'un client
- POST /briefing/feedback - Sauvegarder une correction (Allan only)
- POST /briefing/follow-up/resolve - Marquer un follow-up résolu
- POST /briefing/warm-cache - Pré-charger le cache
"""

import sys
from pathlib import Path
from datetime import datetime
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.briefing.client_intelligence_service import (
    NarrativeBriefingService,
    save_feedback
)

router = APIRouter(prefix="/briefing", tags=["briefing"])


# ═══════════════════════════════════════════════════════════════════════
# MODÈLES
# ═══════════════════════════════════════════════════════════════════════

class FeedbackRequest(BaseModel):
    """Requête pour sauvegarder une note libre sur un client"""
    client_id: str
    note: str
    created_by: str = "asutton@piano-tek.com"


class ResolveFollowUpRequest(BaseModel):
    """Requête pour marquer un follow-up comme résolu"""
    item_id: str
    resolved_by: Optional[str] = None
    resolution_note: Optional[str] = None


# ═══════════════════════════════════════════════════════════════════════
# ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════

@router.get("/health")
async def health_check():
    """Health check"""
    return {"status": "ok", "service": "briefing-v4"}


@router.post("/warm-cache", response_model=Dict[str, Any])
async def warm_cache():
    """
    Pré-charge le cache des briefings pour aujourd'hui et demain.
    Appelé automatiquement après chaque sync, ou manuellement.
    """
    try:
        from modules.briefing.briefing_cache import warm_briefing_cache_async
        stats = await warm_briefing_cache_async()
        return {
            "success": True,
            "message": "Cache pré-chargé",
            "stats": stats
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/daily", response_model=Dict[str, Any])
async def get_daily_briefings(
    technician_id: Optional[str] = Query(None, description="ID du technicien"),
    exclude_technician_id: Optional[str] = Query(None, description="Exclure ce technicien"),
    date: Optional[str] = Query(None, description="Date YYYY-MM-DD (défaut: aujourd'hui)"),
    skip_cache: bool = Query(False, description="Forcer le recalcul (ignorer le cache)")
):
    """
    Récupère les briefings narratifs pour les RV du jour.

    V4: Chaque briefing contient un paragraphe narratif généré par IA
    + des flags computés en Python (PLS, langue, piano).
    """
    target_date = date or datetime.now().strftime('%Y-%m-%d')

    try:
        briefings = None
        from_cache = False

        # Essayer le cache d'abord (sauf si skip_cache ou filtre technicien)
        if not skip_cache and not technician_id and not exclude_technician_id:
            try:
                from modules.briefing.briefing_cache import BriefingCache
                cache = BriefingCache()
                briefings = cache.get_cached_briefings(target_date)
                if briefings:
                    from_cache = True
                    print(f"⚡ Briefings servis depuis le cache ({len(briefings)})")
            except Exception as cache_err:
                print(f"⚠️ Cache non disponible: {cache_err}")

        # Fallback: générer à la demande (async!)
        if briefings is None:
            service = NarrativeBriefingService()
            briefings = await service.get_daily_briefings(
                technician_id=technician_id,
                exclude_technician_id=exclude_technician_id,
                target_date=target_date
            )

        # Filtrer par technicien si demandé (même avec cache)
        if from_cache and technician_id:
            briefings = [b for b in briefings
                        if b.get('appointment', {}).get('technician_id') == technician_id]
        elif from_cache and exclude_technician_id:
            briefings = [b for b in briefings
                        if b.get('appointment', {}).get('technician_id') != exclude_technician_id]

        return {
            "date": target_date,
            "technician_id": technician_id,
            "count": len(briefings),
            "from_cache": from_cache,
            "briefings": briefings,
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/client/{client_id}", response_model=Dict[str, Any])
async def get_client_briefing(client_id: str):
    """
    Génère un briefing narratif pour un client spécifique.
    """
    try:
        service = NarrativeBriefingService()
        briefing = await service.generate_single_briefing(client_id)

        if "error" in briefing:
            raise HTTPException(status_code=404, detail=briefing["error"])

        return briefing

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/feedback", response_model=Dict[str, Any])
async def submit_feedback(request: FeedbackRequest):
    """
    Sauvegarde une correction de briefing.
    ⚠️ SUPER-UTILISATEUR SEULEMENT (Allan)
    """
    if request.created_by != "asutton@piano-tek.com":
        raise HTTPException(
            status_code=403,
            detail="Seul asutton@piano-tek.com peut soumettre des corrections"
        )

    try:
        success = save_feedback(
            client_id=request.client_id,
            category='general',
            field_name='note_libre',
            original_value="",
            corrected_value=request.note,
            created_by=request.created_by
        )

        if success:
            return {
                "success": True,
                "message": "Note enregistrée",
                "client_id": request.client_id
            }
        else:
            raise HTTPException(status_code=500, detail="Erreur sauvegarde")

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/follow-up/resolve", response_model=Dict[str, Any])
async def resolve_follow_up(request: ResolveFollowUpRequest):
    """
    Marque un follow-up comme résolu.
    """
    try:
        service = NarrativeBriefingService()
        success = service.resolve_follow_up(
            item_id=request.item_id,
            resolved_by=request.resolved_by,
            resolution_note=request.resolution_note,
        )

        if success:
            return {
                "success": True,
                "message": "Suivi marqué comme résolu",
                "item_id": request.item_id,
            }
        else:
            raise HTTPException(status_code=500, detail="Erreur résolution")

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
