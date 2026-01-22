#!/usr/bin/env python3
"""
Endpoints API pour le Tableau de Bord unifié.

Fournit les données pour:
- Alertes (RV non confirmés + Maintenance pianos)
- Historique Pianos (modifications techniques)
- État du Système (derniers imports)
"""

import sys
import json
from pathlib import Path
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any, Optional

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.supabase_storage import SupabaseStorage

# Créer 3 routers séparés pour éviter les conflits de préfixes
router_alertes = APIRouter(prefix="/alertes", tags=["tableau-de-bord"])
router_pianos = APIRouter(prefix="/pianos", tags=["tableau-de-bord"])
router_system = APIRouter(prefix="/system", tags=["tableau-de-bord"])

# Singletons
_storage = None


def get_storage() -> SupabaseStorage:
    """Retourne l'instance Supabase (singleton)."""
    global _storage
    if _storage is None:
        _storage = SupabaseStorage()
    return _storage


# ============================================================
# ENDPOINTS - ALERTES
# ============================================================

@router_alertes.get("/rv-non-confirmes")
async def get_unconfirmed_appointments() -> Dict[str, Any]:
    """
    Récupère les rendez-vous non confirmés nécessitant attention.

    Critères:
    - Créés il y a plus de 4 mois (120 jours)
    - Pour une date dans 14 jours
    - Statut ACTIVE (pas confirmés)
    - Exclut les types Admin/Memo/Personal
    - Avec un vrai client associé

    Returns:
        {
            "appointments": [...],
            "count": int,
            "target_date": str,
            "creation_cutoff": str
        }
    """
    try:
        storage = get_storage()
        from core.timezone_utils import MONTREAL_TZ

        # Date cible: dans 14 jours (utiliser heure Montréal)
        now_mtl = datetime.now(MONTREAL_TZ)
        today = now_mtl.date()
        target_date = today + timedelta(days=14)

        # Date limite de création: il y a 120 jours
        creation_cutoff = now_mtl - timedelta(days=120)

        # Récupérer les RV qui correspondent aux critères
        response = storage.client.table('gazelle_appointments').select(
            '*'
        ).eq(
            'appointment_date', target_date.isoformat()
        ).eq(
            'status', 'ACTIVE'  # Pas encore confirmés
        ).lte(
            'created_at', creation_cutoff.isoformat()
        ).not_.is_(
            'client_external_id', 'null'  # Doit avoir un vrai client
        ).order(
            'appointment_time', desc=False
        ).limit(50).execute()

        appointments = response.data or []

        # Filtrer les types Admin/Memo/Personal
        EXCLUDE_TITLES = ['admin', 'memo', 'personal', 'mise à jour', 'personnel']
        filtered = []

        for apt in appointments:
            title = (apt.get('title') or '').lower()

            # Exclure si le titre contient un mot-clé d'exclusion
            if any(exclude in title for exclude in EXCLUDE_TITLES):
                continue

            # Enrichir avec le nom du client
            if apt.get('client_external_id'):
                try:
                    client_resp = storage.client.table('gazelle_clients').select(
                        'company_name'
                    ).eq(
                        'external_id', apt['client_external_id']
                    ).limit(1).execute()

                    if client_resp.data and len(client_resp.data) > 0:
                        apt['client_name'] = client_resp.data[0]['company_name']
                    else:
                        apt['client_name'] = 'Client inconnu'
                except:
                    apt['client_name'] = 'Client inconnu'
            else:
                apt['client_name'] = 'Sans client'

            # Enrichir avec le nom du technicien
            if apt.get('technicien'):
                try:
                    tech_resp = storage.client.table('gazelle_users').select(
                        'first_name, last_name'
                    ).eq(
                        'external_id', apt['technicien']
                    ).limit(1).execute()

                    if tech_resp.data and len(tech_resp.data) > 0:
                        tech = tech_resp.data[0]
                        apt['technician_name'] = f"{tech.get('first_name', '')} {tech.get('last_name', '')}".strip()
                    else:
                        apt['technician_name'] = 'Non assigné'
                except:
                    apt['technician_name'] = 'Non assigné'
            else:
                apt['technician_name'] = 'Non assigné'

            # Calculer l'ancienneté du RV
            if apt.get('created_at'):
                try:
                    created = datetime.fromisoformat(apt['created_at'].replace('Z', '+00:00'))
                    age_days = (datetime.now(created.tzinfo) - created).days
                    apt['age_days'] = age_days
                except:
                    apt['age_days'] = 0

            filtered.append(apt)

        return {
            "appointments": filtered,
            "count": len(filtered),
            "target_date": target_date.isoformat(),
            "creation_cutoff": creation_cutoff.date().isoformat()
        }

    except Exception as e:
        print(f"[TableauDeBord] Erreur get_unconfirmed_appointments: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router_alertes.get("/maintenance")
async def get_maintenance_alerts() -> Dict[str, Any]:
    """
    Récupère les alertes de maintenance pour les pianos en retard.

    Returns:
        {
            "alerts": [...],
            "count": int
        }
    """
    try:
        # Pour l'instant, retourner une liste vide
        # TODO: Implémenter une fois que les colonnes service_interval_months et last_service_date sont disponibles
        return {
            "alerts": [],
            "count": 0
        }

    except Exception as e:
        print(f"[TableauDeBord] Erreur get_maintenance_alerts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# ENDPOINTS - HISTORIQUE PIANOS
# ============================================================

@router_pianos.get("/history")
async def get_piano_history(days: int = 7, type: str = 'technical') -> Dict[str, Any]:
    """
    Récupère l'historique des modifications de pianos (modifications techniques uniquement).

    Args:
        days: Nombre de jours d'historique (défaut: 7)
        type: Type de modifications ('technical', 'all')

    Returns:
        {
            "history": [...],
            "count": int
        }
    """
    try:
        # Pour l'instant, retourner une liste vide
        # TODO: Vérifier le nom exact de la table (gazelle_timeline_entries?) et implémenter
        return {
            "history": [],
            "count": 0
        }

    except Exception as e:
        print(f"[TableauDeBord] Erreur get_piano_history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# ENDPOINTS - ÉTAT SYSTÈME
# ============================================================

@router_system.get("/status")
async def get_system_status() -> Dict[str, Any]:
    """
    Récupère l'état du système (derniers imports Gazelle).

    Returns:
        {
            "last_sync_date": str,
            "last_sync_status": str,
            "last_sync_items": int,
            ...
        }
    """
    try:
        storage = get_storage()

        # Récupérer le dernier log de synchronisation
        response = storage.client.table('sync_logs').select(
            '*'
        ).order(
            'created_at', desc=True
        ).limit(1).execute()

        if not response.data:
            return {
                "last_sync_date": None,
                "last_sync_status": "unknown",
                "last_sync_items": 0,
                "last_sync_job": None,
                "last_sync_error": None,
                "execution_time": None
            }

        log = response.data[0]

        # Calculer le nombre total d'items synchronisés
        total_items = 0
        tables_updated = log.get('tables_updated')
        if tables_updated:
            try:
                if isinstance(tables_updated, str):
                    tables_data = json.loads(tables_updated)
                else:
                    tables_data = tables_updated

                if isinstance(tables_data, dict):
                    total_items = sum(tables_data.values())
            except:
                pass

        return {
            "last_sync_date": log.get('created_at'),
            "last_sync_status": log.get('status', 'unknown'),
            "last_sync_items": total_items,
            "last_sync_job": log.get('script_name'),
            "last_sync_error": log.get('error_message'),
            "execution_time": log.get('execution_time_seconds'),
            "tables_updated": log.get('tables_updated')
        }

    except Exception as e:
        print(f"[TableauDeBord] Erreur get_system_status: {e}")
        raise HTTPException(status_code=500, detail=str(e))
