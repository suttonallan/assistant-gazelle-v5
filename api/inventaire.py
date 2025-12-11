#!/usr/bin/env python3
"""
Routes API pour le module Inventaire.

Gestion du catalogue de produits, inventaire par technicien, et transactions.
Inclut vérification automatique des stocks bas.
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, List, Any, Optional
from pydantic import BaseModel
from core.supabase_storage import SupabaseStorage

# Import du script de vérification de stock
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts.inventory_checker_v5 import run_stock_check

router = APIRouter(prefix="/inventaire", tags=["inventaire"])


# ============================================================
# Modèles Pydantic pour validation des requêtes
# ============================================================

class ProduitCatalogueCreate(BaseModel):
    code_produit: str
    nom: str
    categorie: str
    description: Optional[str] = None
    unite_mesure: Optional[str] = "unité"
    prix_unitaire: Optional[float] = None
    fournisseur: Optional[str] = None


class ProduitCatalogueUpdate(BaseModel):
    nom: Optional[str] = None
    categorie: Optional[str] = None
    description: Optional[str] = None
    unite_mesure: Optional[str] = None
    prix_unitaire: Optional[float] = None
    fournisseur: Optional[str] = None


class AjustementStock(BaseModel):
    code_produit: str
    technicien: str
    quantite_ajustement: float
    emplacement: Optional[str] = "Atelier"
    motif: Optional[str] = ""
    created_by: Optional[str] = "system"


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
# Routes pour le Catalogue de Produits
# ============================================================

@router.get("/catalogue", response_model=Dict[str, Any])
async def get_catalogue(
    categorie: Optional[str] = None,
    has_commission: Optional[bool] = None,
    variant_group: Optional[str] = None,
    is_active: Optional[bool] = None  # None = tous les produits (pas de filtre)
):
    """
    Récupère le catalogue de produits avec filtres de classification.

    Query params:
        - categorie: Filtrer par catégorie (ex: "Cordes", "Feutres")
        - has_commission: Filtrer par commission (true/false)
        - variant_group: Filtrer par groupe de variantes (ex: "Cordes Piano")
        - is_active: Filtrer par statut actif (None = tous, true = actifs seulement, false = inactifs seulement)
    """
    try:
        storage = get_supabase_storage()

        # Construire les filtres
        filters = {}
        if categorie:
            filters["categorie"] = categorie
        if has_commission is not None:
            filters["has_commission"] = has_commission
        if variant_group:
            filters["variant_group"] = variant_group
        # Ne filtrer par is_active QUE si explicitement demandé
        # Si None, on récupère tous les produits (même ceux sans is_active)
        if is_active is not None:
            filters["is_active"] = is_active

        # Récupérer les produits
        produits = storage.get_data("produits_catalogue", filters=filters)

        return {
            "produits": produits,
            "count": len(produits)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")


@router.post("/catalogue", response_model=Dict[str, Any])
async def create_produit(produit: ProduitCatalogueCreate):
    """
    Ajoute un nouveau produit au catalogue.
    """
    try:
        storage = get_supabase_storage()

        success = storage.update_data(
            "produits_catalogue",
            produit.model_dump(),
            id_field="code_produit"
        )

        if success:
            return {
                "success": True,
                "message": f"Produit {produit.code_produit} ajouté au catalogue"
            }
        else:
            raise HTTPException(status_code=500, detail="Échec de l'ajout au catalogue")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")


@router.put("/catalogue/{code_produit}", response_model=Dict[str, Any])
async def update_produit(code_produit: str, updates: ProduitCatalogueUpdate):
    """
    Met à jour un produit du catalogue.
    """
    try:
        storage = get_supabase_storage()

        # Ne garder que les champs fournis (non-None)
        data = {k: v for k, v in updates.model_dump().items() if v is not None}
        data["code_produit"] = code_produit

        success = storage.update_data(
            "produits_catalogue",
            data,
            id_field="code_produit",
            upsert=False  # UPDATE uniquement
        )

        if success:
            return {
                "success": True,
                "message": f"Produit {code_produit} mis à jour"
            }
        else:
            raise HTTPException(status_code=404, detail=f"Produit {code_produit} introuvable")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")


@router.delete("/catalogue/{code_produit}", response_model=Dict[str, Any])
async def delete_produit(code_produit: str):
    """
    Supprime un produit du catalogue.
    """
    try:
        storage = get_supabase_storage()

        success = storage.delete_data("produits_catalogue", "code_produit", code_produit)

        if success:
            return {
                "success": True,
                "message": f"Produit {code_produit} supprimé"
            }
        else:
            raise HTTPException(status_code=404, detail=f"Produit {code_produit} introuvable")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")


# ============================================================
# Routes pour l'Inventaire par Technicien
# ============================================================

@router.get("/stock/{technicien}", response_model=Dict[str, Any])
async def get_stock_technicien(technicien: str):
    """
    Récupère l'inventaire complet d'un technicien avec les noms de produits.

    Path params:
        - technicien: Nom du technicien (ex: "Allan")
    """
    try:
        storage = get_supabase_storage()
        inventaire = storage.get_inventaire_technicien(technicien)
        
        # Enrichir avec les noms de produits depuis le catalogue
        catalogue = storage.get_data("produits_catalogue", filters={})
        catalogue_dict = {p.get("code_produit"): p for p in catalogue}
        
        inventaire_enrichi = []
        for item in inventaire:
            code_produit = item.get("code_produit")
            produit_catalogue = catalogue_dict.get(code_produit, {})
            
            # Ajouter les infos du catalogue
            item_enrichi = item.copy()
            item_enrichi["nom"] = produit_catalogue.get("nom", "-")
            item_enrichi["categorie"] = produit_catalogue.get("categorie")
            item_enrichi["unite_mesure"] = produit_catalogue.get("unite_mesure", "unité")
            
            inventaire_enrichi.append(item_enrichi)

        return {
            "technicien": technicien,
            "inventaire": inventaire_enrichi,
            "count": len(inventaire_enrichi)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")


@router.post("/stock/ajuster", response_model=Dict[str, Any])
async def ajuster_stock(ajustement: AjustementStock):
    """
    Ajuste le stock d'un produit pour un technicien.

    Body:
        - code_produit: Code du produit
        - technicien: Nom du technicien
        - quantite_ajustement: Quantité à ajouter (positif) ou retirer (négatif)
        - emplacement: Localisation (défaut: "Atelier")
        - motif: Raison de l'ajustement
        - created_by: Qui effectue l'ajustement
    """
    try:
        storage = get_supabase_storage()

        success = storage.update_stock(
            code_produit=ajustement.code_produit,
            technicien=ajustement.technicien,
            quantite_ajustement=ajustement.quantite_ajustement,
            emplacement=ajustement.emplacement,
            motif=ajustement.motif,
            created_by=ajustement.created_by
        )

        if success:
            action = "ajouté" if ajustement.quantite_ajustement > 0 else "retiré"
            return {
                "success": True,
                "message": f"{abs(ajustement.quantite_ajustement)} unités {action} pour {ajustement.technicien}"
            }
        else:
            raise HTTPException(status_code=500, detail="Échec de l'ajustement du stock")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")


# ============================================================
# Routes pour l'Historique des Transactions
# ============================================================

@router.get("/transactions", response_model=Dict[str, Any])
async def get_transactions(
    technicien: Optional[str] = None,
    code_produit: Optional[str] = None,
    limit: int = 100
):
    """
    Récupère l'historique des transactions d'inventaire.

    Query params:
        - technicien: Filtrer par technicien (optionnel)
        - code_produit: Filtrer par produit (optionnel)
        - limit: Nombre maximum de transactions (défaut: 100)
    """
    try:
        storage = get_supabase_storage()

        transactions = storage.get_transactions_inventaire(
            technicien=technicien,
            code_produit=code_produit,
            limit=limit
        )

        return {
            "transactions": transactions,
            "count": len(transactions),
            "filters": {
                "technicien": technicien,
                "code_produit": code_produit
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")


# ============================================================
# Routes pour l'Administration (Allan uniquement)
# ============================================================

class BatchOrderUpdate(BaseModel):
    products: List[Dict[str, Any]]


@router.patch("/catalogue/batch-order", response_model=Dict[str, Any])
async def update_batch_order(batch: BatchOrderUpdate):
    """
    Met à jour l'ordre d'affichage de plusieurs produits en batch.

    Body:
        products: Liste de {code_produit, display_order}
    """
    try:
        storage = get_supabase_storage()

        updated_count = 0
        errors = []

        for product in batch.products:
            code_produit = product.get("code_produit")
            display_order = product.get("display_order")

            if not code_produit:
                continue

            try:
                success = storage.update_data(
                    "produits_catalogue",
                    {"display_order": display_order},
                    filters={"code_produit": code_produit}
                )
                if success:
                    updated_count += 1
                else:
                    errors.append(f"{code_produit}: échec")
            except Exception as e:
                errors.append(f"{code_produit}: {str(e)}")

        return {
            "success": True,
            "updated_count": updated_count,
            "total": len(batch.products),
            "errors": errors if errors else None
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")


@router.put("/catalogue/{code_produit}", response_model=Dict[str, Any])
async def update_produit(code_produit: str, produit: ProduitCatalogueUpdate):
    """
    Met à jour un produit du catalogue.
    """
    try:
        storage = get_supabase_storage()

        # Préparer les données à mettre à jour (seulement les champs fournis)
        update_data = {}
        for field, value in produit.dict(exclude_unset=True).items():
            if value is not None:
                update_data[field] = value

        if not update_data:
            raise HTTPException(status_code=400, detail="Aucune donnée à mettre à jour")

        success = storage.update_data(
            "produits_catalogue",
            update_data,
            filters={"code_produit": code_produit}
        )

        if success:
            # Récupérer le produit mis à jour
            produits = storage.get_data("produits_catalogue", filters={"code_produit": code_produit})
            return {
                "success": True,
                "message": "Produit mis à jour",
                "produit": produits[0] if produits else None
            }
        else:
            raise HTTPException(status_code=500, detail="Échec de la mise à jour")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")


# ============================================================
# Routes pour les Statistiques
# ============================================================

@router.get("/stats/{technicien}", response_model=Dict[str, Any])
async def get_stats_technicien(technicien: str):
    """
    Récupère les statistiques d'inventaire pour un technicien.

    Retourne:
        - Nombre total de produits en stock
        - Valeur totale estimée
        - Répartition par catégorie
        - Répartition par emplacement
    """
    try:
        storage = get_supabase_storage()

        # Récupérer l'inventaire du technicien
        inventaire = storage.get_inventaire_technicien(technicien)

        # Récupérer le catalogue pour les prix
        catalogue = storage.get_produits_catalogue()
        prix_map = {p["code_produit"]: p.get("prix_unitaire", 0) for p in catalogue}

        # Calculer les stats
        total_produits = len(inventaire)
        valeur_totale = sum(
            item.get("quantite_stock", 0) * prix_map.get(item["code_produit"], 0)
            for item in inventaire
        )

        # Répartition par emplacement
        emplacements = {}
        for item in inventaire:
            loc = item.get("emplacement", "Non spécifié")
            emplacements[loc] = emplacements.get(loc, 0) + 1

        # Récupérer les transactions récentes
        transactions_recentes = storage.get_transactions_inventaire(
            technicien=technicien,
            limit=10
        )

        return {
            "technicien": technicien,
            "total_produits": total_produits,
            "valeur_totale_estimee": round(valeur_totale, 2),
            "repartition_emplacements": emplacements,
            "transactions_recentes": len(transactions_recentes)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")


# ============================================================
# Route pour Vérification Automatique des Stocks (Cron Jobs Render)
# ============================================================

@router.post("/check-stock", response_model=Dict[str, Any])
async def check_inventory_stock(
    technicien: Optional[str] = None,
    seuil_critique: float = 5.0
):
    """
    Vérifie les stocks bas et génère un rapport d'alertes.
    Endpoint appelé par les Cron Jobs de Render pour vérification automatique.

    Query params:
        - technicien: Nom du technicien (optionnel, None = tous)
        - seuil_critique: Seuil en dessous duquel générer une alerte (défaut: 5.0)

    Returns:
        Rapport complet avec alertes et statistiques

    Exemple d'appel:
        POST /inventaire/check-stock
        POST /inventaire/check-stock?technicien=Allan&seuil_critique=10
    """
    try:
        print(f"🔍 Déclenchement vérification stock - Technicien: {technicien or 'Tous'}, Seuil: {seuil_critique}")

        # Exécuter la vérification
        rapport = run_stock_check(technicien=technicien, seuil_critique=seuil_critique)

        # Retourner le rapport avec statut
        return {
            "status": "success",
            "message": "Vérification d'inventaire terminée",
            "alerts_detected": len(rapport.get("alertes", [])),
            "rapport": rapport
        }

    except Exception as e:
        print(f"❌ Erreur lors de la vérification d'inventaire: {e}")
        import traceback
        traceback.print_exc()

        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la vérification: {str(e)}"
        )
