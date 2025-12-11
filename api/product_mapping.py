#!/usr/bin/env python3
"""
API endpoints pour le mapping des produits entre Gazelle API et Supabase.

Permet de:
- Lister les produits Gazelle non mappés
- Lister les produits Supabase sans mapping
- Créer/modifier/supprimer des mappings
- Synchroniser les produits en utilisant les mappings existants
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, List, Any, Optional
from pydantic import BaseModel
from core.supabase_storage import SupabaseStorage
from core.gazelle_api_client import GazelleAPIClient

router = APIRouter(prefix="/inventaire/mapping", tags=["product-mapping"])


# ============================================================
# Modèles Pydantic
# ============================================================

class ProductMappingCreate(BaseModel):
    """Modèle pour créer un mapping."""
    gazelle_product_id: str
    code_produit: str
    mapped_by: Optional[str] = None


class ProductMappingUpdate(BaseModel):
    """Modèle pour mettre à jour un mapping."""
    code_produit: Optional[str] = None
    sync_status: Optional[str] = None
    sync_error: Optional[str] = None


# ============================================================
# Helpers
# ============================================================

def get_supabase_storage() -> SupabaseStorage:
    """Retourne une instance de SupabaseStorage."""
    return SupabaseStorage()


def get_api_client() -> GazelleAPIClient:
    """Retourne une instance de GazelleAPIClient."""
    try:
        return GazelleAPIClient()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur initialisation API Gazelle: {str(e)}")


# ============================================================
# Endpoints
# ============================================================

@router.get("/gazelle-products", response_model=Dict[str, Any])
async def get_gazelle_products():
    """
    Récupère tous les produits depuis l'API Gazelle.
    
    Returns:
        Liste des produits avec leurs informations complètes
    """
    try:
        api_client = get_api_client()
        products = api_client.get_products(limit=10000)
        
        return {
            "count": len(products),
            "products": products
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")


@router.get("/unmapped-gazelle", response_model=Dict[str, Any])
async def get_unmapped_gazelle_products():
    """
    Récupère les produits Gazelle qui n'ont pas encore de mapping.
    
    Returns:
        Liste des produits Gazelle non mappés
    """
    try:
        storage = get_supabase_storage()
        api_client = get_api_client()
        
        # Récupérer tous les produits Gazelle
        gazelle_products = api_client.get_products(limit=10000)
        
        # Récupérer tous les mappings existants
        mappings = storage.get_data("produits_mapping", filters={})
        mapped_gazelle_ids = {m.get("gazelle_product_id") for m in mappings if m.get("gazelle_product_id")}
        
        # Filtrer les produits non mappés
        unmapped = [
            p for p in gazelle_products 
            if p.get("id") not in mapped_gazelle_ids
        ]
        
        return {
            "count": len(unmapped),
            "products": unmapped
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")


@router.get("/unmapped-supabase", response_model=Dict[str, Any])
async def get_unmapped_supabase_products():
    """
    Récupère les produits Supabase qui n'ont pas encore de mapping.
    
    Returns:
        Liste des produits Supabase sans mapping
    """
    try:
        storage = get_supabase_storage()
        
        # Récupérer tous les produits Supabase
        supabase_products = storage.get_data("produits_catalogue", filters={})
        
        # Récupérer tous les mappings existants
        mappings = storage.get_data("produits_mapping", filters={})
        mapped_codes = {m.get("code_produit") for m in mappings if m.get("code_produit")}
        
        # Filtrer les produits non mappés
        unmapped = [
            p for p in supabase_products 
            if p.get("code_produit") not in mapped_codes
        ]
        
        return {
            "count": len(unmapped),
            "products": unmapped
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")


@router.get("/mappings", response_model=Dict[str, Any])
async def get_all_mappings():
    """
    Récupère tous les mappings existants.
    
    Returns:
        Liste de tous les mappings avec détails
    """
    try:
        storage = get_supabase_storage()
        mappings = storage.get_data("produits_mapping", filters={})
        
        # Enrichir avec les infos des produits
        enriched_mappings = []
        for mapping in mappings:
            code_produit = mapping.get("code_produit")
            produit = storage.get_data("produits_catalogue", filters={"code_produit": code_produit})
            
            mapping_enriched = mapping.copy()
            if produit:
                mapping_enriched["produit_nom"] = produit[0].get("nom")
                mapping_enriched["produit_categorie"] = produit[0].get("categorie")
            
            enriched_mappings.append(mapping_enriched)
        
        return {
            "count": len(enriched_mappings),
            "mappings": enriched_mappings
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")


@router.post("/mappings", response_model=Dict[str, Any])
async def create_mapping(mapping: ProductMappingCreate):
    """
    Crée un nouveau mapping entre un produit Gazelle et un produit Supabase.
    
    Body:
        - gazelle_product_id: ID du produit dans Gazelle
        - code_produit: Code du produit dans Supabase
        - mapped_by: Nom de l'utilisateur qui crée le mapping (optionnel)
    """
    try:
        storage = get_supabase_storage()
        
        # Vérifier que le produit Supabase existe
        produit = storage.get_data("produits_catalogue", filters={"code_produit": mapping.code_produit})
        if not produit:
            raise HTTPException(status_code=404, detail=f"Produit Supabase non trouvé: {mapping.code_produit}")
        
        # Récupérer les infos du produit Gazelle (pour stocker le nom/SKU)
        api_client = get_api_client()
        gazelle_products = api_client.get_products(limit=10000)
        gazelle_product = next((p for p in gazelle_products if p.get("id") == mapping.gazelle_product_id), None)
        
        if not gazelle_product:
            raise HTTPException(status_code=404, detail=f"Produit Gazelle non trouvé: {mapping.gazelle_product_id}")
        
        # Créer le mapping
        mapping_data = {
            "gazelle_product_id": mapping.gazelle_product_id,
            "gazelle_sku": gazelle_product.get("sku"),
            "gazelle_name": gazelle_product.get("name"),
            "code_produit": mapping.code_produit,
            "mapped_by": mapping.mapped_by or "system",
            "sync_status": "pending"
        }
        
        success = storage.update_data(
            "produits_mapping",
            mapping_data,
            id_field="gazelle_product_id",
            upsert=True
        )
        
        if success:
            return {
                "success": True,
                "message": f"Mapping créé: {mapping.gazelle_product_id} -> {mapping.code_produit}",
                "mapping": mapping_data
            }
        else:
            raise HTTPException(status_code=500, detail="Erreur lors de la création du mapping")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")


@router.delete("/mappings/{gazelle_product_id}", response_model=Dict[str, Any])
async def delete_mapping(gazelle_product_id: str):
    """
    Supprime un mapping existant.
    
    Path params:
        - gazelle_product_id: ID du produit Gazelle
    """
    try:
        storage = get_supabase_storage()
        
        # Trouver le mapping
        mappings = storage.get_data("produits_mapping", filters={"gazelle_product_id": gazelle_product_id})
        if not mappings:
            raise HTTPException(status_code=404, detail="Mapping non trouvé")
        
        mapping_id = mappings[0].get("id")
        
        # Supprimer via API Supabase
        import requests
        url = f"{storage.api_url}/produits_mapping?id=eq.{mapping_id}"
        headers = storage._get_headers()
        response = requests.delete(url, headers=headers)
        
        if response.status_code in [200, 204]:
            return {
                "success": True,
                "message": f"Mapping supprimé: {gazelle_product_id}"
            }
        else:
            raise HTTPException(status_code=500, detail=f"Erreur lors de la suppression: {response.text}")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")
