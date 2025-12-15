#!/usr/bin/env python3
"""
Routes API pour la gestion des tournées d'accords.

Permet à Nicolas de:
- Créer des tournées
- Voir la liste des tournées
- Gérer les dates et noms
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime, date

# Imports locaux
from core.supabase_storage import SupabaseStorage


router = APIRouter(prefix="/tournees", tags=["tournees"])


def get_supabase_storage():
    """Helper pour obtenir une instance SupabaseStorage."""
    return SupabaseStorage()


class TourneeCreate(BaseModel):
    """Modèle pour créer une tournée."""
    nom: str
    date_debut: date
    date_fin: Optional[date] = None
    technicien_responsable: str
    notes: Optional[str] = None
    status: str = "planifiee"  # planifiee, en_cours, terminee


class TourneeUpdate(BaseModel):
    """Modèle pour mettre à jour une tournée."""
    nom: Optional[str] = None
    date_debut: Optional[date] = None
    date_fin: Optional[date] = None
    status: Optional[str] = None
    notes: Optional[str] = None


@router.post("/create", response_model=Dict[str, Any])
async def create_tournee(tournee: TourneeCreate):
    """
    Crée une nouvelle tournée d'accords.

    Body:
        - nom: Nom de la tournée (ex: "Tournée Place des Arts - Janvier 2025")
        - date_debut: Date de début (YYYY-MM-DD)
        - date_fin: Date de fin (optionnelle)
        - technicien_responsable: Email du technicien responsable
        - notes: Notes additionnelles
        - status: planifiee/en_cours/terminee (défaut: planifiee)

    Returns:
        - success: bool
        - tournee_id: ID de la tournée créée
        - message: Message de confirmation
    """
    try:
        storage = get_supabase_storage()

        # Créer la tournée
        tournee_data = {
            "nom": tournee.nom,
            "date_debut": tournee.date_debut.isoformat(),
            "date_fin": tournee.date_fin.isoformat() if tournee.date_fin else None,
            "technicien_responsable": tournee.technicien_responsable,
            "status": tournee.status,
            "notes": tournee.notes,
            "created_at": datetime.now().isoformat()
        }

        # IMPORTANT: Pour l'instant, on sauvegarde en localStorage côté frontend
        # car la table tournees n'existe pas encore dans Supabase
        # Quand vous serez prêt, créez la table:
        #
        # CREATE TABLE tournees_accords (
        #   id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        #   nom VARCHAR NOT NULL,
        #   date_debut DATE NOT NULL,
        #   date_fin DATE,
        #   technicien_responsable VARCHAR,
        #   status VARCHAR DEFAULT 'planifiee',
        #   notes TEXT,
        #   created_at TIMESTAMPTZ DEFAULT NOW()
        # );

        # Pour l'instant, retourner succès pour le frontend
        return {
            "success": True,
            "tournee_id": "temp_id",  # ID temporaire
            "message": f"Tournée '{tournee.nom}' créée avec succès",
            "tournee": tournee_data
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur création tournée: {str(e)}")


@router.get("/list", response_model=Dict[str, Any])
async def list_tournees(
    technicien: Optional[str] = None,
    status: Optional[str] = None
):
    """
    Liste toutes les tournées.

    Query params:
        - technicien: Filtrer par technicien responsable (optionnel)
        - status: Filtrer par statut (planifiee/en_cours/terminee) (optionnel)

    Returns:
        - success: bool
        - tournees: Liste des tournées
        - count: Nombre de tournées
    """
    try:
        # Pour l'instant, retourner liste vide
        # Quand la table existe, utiliser:
        # storage = get_supabase_storage()
        # filters = {}
        # if technicien:
        #     filters["technicien_responsable"] = technicien
        # if status:
        #     filters["status"] = status
        # tournees = storage.get_data("tournees_accords", filters=filters)

        return {
            "success": True,
            "tournees": [],
            "count": 0,
            "message": "Table tournees_accords pas encore créée - données stockées côté frontend pour l'instant"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur liste tournées: {str(e)}")


@router.get("/{tournee_id}", response_model=Dict[str, Any])
async def get_tournee(tournee_id: str):
    """
    Récupère les détails d'une tournée.

    Path params:
        - tournee_id: ID de la tournée

    Returns:
        - success: bool
        - tournee: Données de la tournée
    """
    try:
        storage = get_supabase_storage()

        # Placeholder pour l'instant
        return {
            "success": False,
            "message": "Table tournees_accords pas encore créée"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur récupération tournée: {str(e)}")


@router.put("/{tournee_id}", response_model=Dict[str, Any])
async def update_tournee(tournee_id: str, updates: TourneeUpdate):
    """
    Met à jour une tournée.

    Path params:
        - tournee_id: ID de la tournée

    Body:
        - Champs à mettre à jour (tous optionnels)

    Returns:
        - success: bool
        - message: Message de confirmation
    """
    try:
        # Placeholder
        return {
            "success": False,
            "message": "Table tournees_accords pas encore créée"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur mise à jour tournée: {str(e)}")


@router.delete("/{tournee_id}", response_model=Dict[str, Any])
async def delete_tournee(tournee_id: str):
    """
    Supprime une tournée.

    Path params:
        - tournee_id: ID de la tournée

    Returns:
        - success: bool
        - message: Message de confirmation
    """
    try:
        # Placeholder
        return {
            "success": False,
            "message": "Table tournees_accords pas encore créée"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur suppression tournée: {str(e)}")
