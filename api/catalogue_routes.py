#!/usr/bin/env python3
"""
Routes API pour le catalogue de produits.

Endpoint simplifié: /api/catalogue/add
Utilise la validation Pydantic pour garantir l'intégrité des données.
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field, field_validator
from core.supabase_storage import SupabaseStorage

router = APIRouter(prefix="/api/catalogue", tags=["catalogue"])


# ============================================================
# Modèle Pydantic pour validation des données
# ============================================================

class CatalogueAddRequest(BaseModel):
    """
    Modèle de validation pour l'ajout d'un produit au catalogue.
    
    Utilise Pydantic pour valider automatiquement:
    - Types de données
    - Champs requis vs optionnels
    - Contraintes de valeurs
    """
    code_produit: str = Field(
        ...,
        description="Code unique du produit (ex: CORD-001)",
        min_length=1,
        max_length=50
    )
    nom: str = Field(
        ...,
        description="Nom du produit",
        min_length=1,
        max_length=200
    )
    categorie: str = Field(
        ...,
        description="Catégorie du produit (ex: Cordes, Feutres, Outils)",
        min_length=1,
        max_length=100
    )
    description: Optional[str] = Field(
        None,
        description="Description détaillée du produit",
        max_length=1000
    )
    unite_mesure: Optional[str] = Field(
        "unité",
        description="Unité de mesure (ex: unité, kg, m, L)",
        max_length=20
    )
    prix_unitaire: Optional[float] = Field(
        None,
        description="Prix unitaire en dollars",
        ge=0,
        examples=[12.50, 0.0]
    )
    fournisseur: Optional[str] = Field(
        None,
        description="Nom du fournisseur",
        max_length=100
    )

    @field_validator('code_produit')
    @classmethod
    def validate_code_produit(cls, v: str) -> str:
        """Valide que le code produit n'est pas vide et est nettoyé."""
        v = v.strip()
        if not v:
            raise ValueError("Le code produit ne peut pas être vide")
        return v.upper()  # Normaliser en majuscules

    @field_validator('nom')
    @classmethod
    def validate_nom(cls, v: str) -> str:
        """Valide et nettoie le nom du produit."""
        v = v.strip()
        if not v:
            raise ValueError("Le nom du produit ne peut pas être vide")
        return v

    @field_validator('categorie')
    @classmethod
    def validate_categorie(cls, v: str) -> str:
        """Valide et nettoie la catégorie."""
        v = v.strip()
        if not v:
            raise ValueError("La catégorie ne peut pas être vide")
        return v

    @field_validator('prix_unitaire')
    @classmethod
    def validate_prix(cls, v: Optional[float]) -> Optional[float]:
        """Valide que le prix est positif si fourni."""
        if v is not None and v < 0:
            raise ValueError("Le prix unitaire ne peut pas être négatif")
        return v

    class Config:
        """Configuration Pydantic."""
        json_schema_extra = {
            "example": {
                "code_produit": "CORD-001",
                "nom": "Corde de piano #1",
                "categorie": "Cordes",
                "description": "Corde de piano standard pour piano droit",
                "unite_mesure": "unité",
                "prix_unitaire": 12.50,
                "fournisseur": "Fournisseur ABC"
            }
        }


# ============================================================
# Fonction helper pour récupérer le client Supabase
# ============================================================

def get_supabase_storage() -> SupabaseStorage:
    """Retourne une instance du client Supabase."""
    try:
        return SupabaseStorage()
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# Endpoint: POST /api/catalogue/add
# ============================================================

@router.post("/add", response_model=Dict[str, Any])
async def add_to_catalogue(produit: CatalogueAddRequest) -> Dict[str, Any]:
    """
    Ajoute un nouveau produit au catalogue avec validation Pydantic.
    
    **Validation automatique**:
    - Types de données vérifiés (str, float, etc.)
    - Champs requis validés (code_produit, nom, categorie)
    - Contraintes respectées (longueurs min/max, prix positif)
    - Normalisation automatique (code_produit en majuscules)
    
    **Exemple de requête**:
    ```json
    {
        "code_produit": "CORD-001",
        "nom": "Corde de piano #1",
        "categorie": "Cordes",
        "description": "Corde standard",
        "unite_mesure": "unité",
        "prix_unitaire": 12.50,
        "fournisseur": "Fournisseur ABC"
    }
    ```
    
    **Réponse en cas de succès**:
    ```json
    {
        "success": true,
        "message": "Produit CORD-001 ajouté au catalogue",
        "produit": {
            "code_produit": "CORD-001",
            "nom": "Corde de piano #1",
            ...
        }
    }
    ```
    
    **Erreurs possibles**:
    - `422`: Données invalides (validation Pydantic échouée)
    - `500`: Erreur serveur (Supabase, configuration)
    """
    try:
        storage = get_supabase_storage()
        
        # Convertir le modèle Pydantic en dictionnaire
        # Pydantic garantit que toutes les validations sont passées
        produit_data = produit.model_dump()
        
        # Sauvegarder dans Supabase (mode UPSERT)
        success = storage.update_data(
            "produits_catalogue",
            produit_data,
            id_field="code_produit",
            upsert=True  # Insert ou Update si existe déjà
        )
        
        if success:
            # Récupérer le produit créé pour le retourner
            produits = storage.get_data(
                "produits_catalogue",
                filters={"code_produit": produit.code_produit}
            )
            
            return {
                "success": True,
                "message": f"Produit {produit.code_produit} ajouté au catalogue",
                "produit": produits[0] if produits else produit_data
            }
        else:
            raise HTTPException(
                status_code=500,
                detail="Échec de l'ajout au catalogue. Vérifiez les logs du serveur."
            )
    
    except HTTPException:
        # Re-lancer les HTTPException telles quelles
        raise
    except ValueError as e:
        # Erreur de configuration (Supabase non configuré)
        raise HTTPException(
            status_code=500,
            detail=f"Configuration manquante: {str(e)}"
        )
    except Exception as e:
        # Erreur inattendue
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de l'ajout au catalogue: {str(e)}"
        )


# ============================================================
# Endpoint bonus: GET /api/catalogue (liste)
# ============================================================

@router.get("", response_model=Dict[str, Any])
async def get_catalogue(
    categorie: Optional[str] = None,
    limit: int = 100
) -> Dict[str, Any]:
    """
    Récupère la liste des produits du catalogue.
    
    **Query params**:
    - `categorie`: Filtrer par catégorie (optionnel)
    - `limit`: Nombre maximum de résultats (défaut: 100)
    
    **Exemple**:
    ```
    GET /api/catalogue?categorie=Cordes&limit=50
    ```
    """
    try:
        storage = get_supabase_storage()
        
        filters = {}
        if categorie:
            filters["categorie"] = categorie
        
        produits = storage.get_data(
            "produits_catalogue",
            filters=filters,
            order_by="nom.asc"
        )
        
        # Limiter les résultats
        produits = produits[:limit]
        
        return {
            "produits": produits,
            "count": len(produits),
            "filters": {
                "categorie": categorie,
                "limit": limit
            }
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la récupération: {str(e)}"
        )
