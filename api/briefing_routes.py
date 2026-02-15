#!/usr/bin/env python3
"""
API Routes pour les Briefings Intelligents - "Ma Journée" V2

Endpoints:
- GET /briefing/daily - Briefings du jour pour un technicien
- GET /briefing/client/{id} - Briefing détaillé d'un client
- POST /briefing/feedback - Sauvegarder une correction (Allan only)
"""

import sys
from pathlib import Path
from datetime import datetime
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.briefing.client_intelligence_service import (
    ClientIntelligenceService,
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


class BriefingCard(BaseModel):
    """Format simplifié pour affichage mobile"""
    time: str
    client_name: str
    client_since: Optional[str] = None
    icons: List[str]
    piano: str
    warnings: List[str]
    last_recommendation: Optional[str]
    follow_ups: List[Dict] = []
    payment_method: Optional[str] = None


# ═══════════════════════════════════════════════════════════════════════
# ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════

@router.get("/health")
async def health_check():
    """Health check"""
    return {"status": "ok", "service": "briefing"}


@router.post("/warm-cache", response_model=Dict[str, Any])
async def warm_cache():
    """
    Pré-charge le cache des briefings pour aujourd'hui et demain.
    Appelé automatiquement après chaque sync, ou manuellement.
    """
    try:
        from modules.briefing.briefing_cache import warm_briefing_cache
        stats = warm_briefing_cache()
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
    Récupère les briefings pour les RV du jour.

    Utilise le cache pré-calculé si disponible (plus rapide).
    Le cache est rafraîchi toutes les 4 heures par le sync.

    Retourne une liste de briefings avec les 3 piliers:
    - Profile: Langue, animaux, courtoisies
    - Technical: Recommandations des dernières visites
    - Piano: Fiche et avertissements
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

        # Fallback: générer à la demande
        if briefings is None:
            service = ClientIntelligenceService()
            briefings = service.get_daily_briefings(
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

        # Générer les cartes formatées
        cards = [_format_card(b) for b in briefings]

        return {
            "date": target_date,
            "technician_id": technician_id,
            "count": len(briefings),
            "from_cache": from_cache,
            "briefings": briefings,
            "cards": cards
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/client/{client_id}", response_model=Dict[str, Any])
async def get_client_briefing(client_id: str):
    """
    Génère un briefing détaillé pour un client spécifique.
    """
    try:
        service = ClientIntelligenceService()
        briefing = service.generate_briefing(client_id)

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
    Ces corrections sont utilisées pour améliorer l'IA.
    """
    # Vérifier que c'est Allan
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

    Appelé quand le technicien a complété un item "à faire"
    (ex: rondelle remplacée, harmonisation faite, buvards changés).
    """
    try:
        service = ClientIntelligenceService()
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


@router.get("/card/{client_id}", response_model=Dict[str, Any])
async def get_briefing_card(client_id: str):
    """
    Retourne un briefing au format carte (10 secondes de lecture).
    Optimisé pour affichage mobile.
    """
    try:
        service = ClientIntelligenceService()
        briefing = service.generate_briefing(client_id)

        if "error" in briefing:
            raise HTTPException(status_code=404, detail=briefing["error"])

        card = _format_card(briefing)
        text = service.format_briefing_card(briefing)

        return {
            "card": card,
            "text_format": text,
            "client_id": client_id
        }

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════

def _format_card(briefing: Dict) -> Dict:
    """Formate un briefing en carte simplifiée"""
    profile = briefing.get('profile', {})
    piano = briefing.get('piano', {})
    history = briefing.get('technical_history', [])
    appt = briefing.get('appointment', {})

    # Icônes
    icons = []
    lang = profile.get('language', 'FR')
    if lang == 'EN':
        icons.append('🇬🇧')
    elif lang == 'BI':
        icons.append('🇬🇧🇫🇷')

    if profile.get('pets'):
        icons.append('🐕')

    courtesies = profile.get('courtesies', [])
    if 'enlever chaussures' in courtesies:
        icons.append('👟❌')
    if 'offre café' in courtesies:
        icons.append('☕')
    if 'appeler avant' in courtesies:
        icons.append('📞')

    # Piano string
    piano_str = ""
    if piano:
        piano_str = f"{piano.get('make', '')} {piano.get('model', '')}"
        if piano.get('year'):
            piano_str += f" ({piano.get('year')})"

    # Last recommendation
    last_rec = None
    if history and history[0].get('recommendations'):
        last_rec = history[0]['recommendations'][0]

    return {
        "time": appt.get('time', ''),
        "client_name": briefing.get('client_name', 'Client'),
        "client_since": briefing.get('client_since'),
        "icons": icons,
        "piano": piano_str.strip(),
        "warnings": piano.get('warnings', []),
        "last_recommendation": last_rec,
        "follow_ups": briefing.get('follow_ups', []),
        "payment_method": (briefing.get('profile') or {}).get('payment_method'),
        "confidence": briefing.get('confidence_score', 0),
        "extraction_mode": briefing.get('extraction_mode', 'regex'),
    }
