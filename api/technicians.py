"""
Endpoint API pour récupérer les techniciens depuis Supabase users
Source unique de vérité pour les noms des techniciens
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, List, Any
from core.supabase_storage import SupabaseStorage

router = APIRouter(prefix="/api/technicians", tags=["technicians"])

@router.get("/profiles", response_model=Dict[str, Any])
async def get_technician_profiles():
    """
    Récupère tous les utilisateurs depuis la table Supabase users.
    PAS DE FILTRAGE - RENVOIE TOUT.
    """
    try:
        storage = SupabaseStorage()
        
        # LIRE LA TABLE users (la bonne table avec Nicolas, Allan, JP)
        users_data = storage.get_data("users", filters={})
        
        # PAS DE FILTRAGE - RENVOYER TOUT
        technicians = []
        for user in users_data:
            # Récupérer le nom depuis plusieurs champs possibles
            first_name = user.get("first_name") or user.get("name") or ""
            last_name = user.get("last_name") or ""
            name = first_name or user.get("name") or user.get("email", "").split("@")[0]
            email = user.get("email") or ""
            
            # Si on a au moins un nom ou un email, on inclut
            if name or email:
                technicians.append({
                    "id": user.get("id") or user.get("external_id"),
                    "gazelle_user_id": user.get("gazelle_user_id") or user.get("external_id") or user.get("id"),
                    "first_name": first_name,
                    "last_name": last_name,
                    "name": name,
                    "email": email,
                    "username": user.get("username") or (email.split("@")[0] if email else name.lower() if name else ""),
                })

        return {
            "technicians": technicians,
            "count": len(technicians)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la récupération des techniciens: {str(e)}")
