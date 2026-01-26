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
from core.slack_notifier import SlackNotifier
from core.gazelle_api_client import GazelleAPIClient
import difflib
from datetime import datetime, timedelta

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
    has_commission: Optional[bool] = None
    commission_rate: Optional[float] = None
    variant_group: Optional[str] = None
    variant_label: Optional[str] = None
    display_order: Optional[int] = None
    is_active: Optional[bool] = None


class AjustementStock(BaseModel):
    code_produit: str
    technicien: str
    quantite_ajustement: float
    emplacement: Optional[str] = "Atelier"
    motif: Optional[str] = ""
    created_by: Optional[str] = "system"


class MiseAJourStock(BaseModel):
    """Modèle pour mise à jour directe de quantité (format V4)."""
    code_produit: str
    technicien: str
    quantite_stock: int
    type_transaction: Optional[str] = "ajustement"
    motif: Optional[str] = "Ajustement manuel"


class CommentaireInventaire(BaseModel):
    """Modèle pour commentaire rapide (notification Slack admin)."""
    text: str
    username: str


class BatchTypeCommissionUpdate(BaseModel):
    """Modèle pour mise à jour batch du type et commission."""
    codes_produit: List[str]
    type_produit: Optional[str] = None  # 'produit', 'service', 'fourniture'
    has_commission: Optional[bool] = None


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
    is_active: Optional[bool] = None  # Changé: None au lieu de True (compatibilité avant migration 002)
):
    """
    Récupère le catalogue de produits avec filtres de classification.

    Query params:
        - categorie: Filtrer par catégorie (ex: "Cordes", "Feutres")
        - has_commission: Filtrer par commission (true/false)
        - variant_group: Filtrer par groupe de variantes (ex: "Cordes Piano")
        - is_active: Filtrer par statut actif (None = tous, avant migration 002)
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
        if is_active is not None:
            filters["is_active"] = is_active

        # Récupérer les produits (SANS filtre WHERE - tous les produits)
        produits = storage.get_data("produits_catalogue", filters=filters)
        
        # Vérifier que produits est une liste (get_data peut retourner [] en cas d'erreur silencieuse)
        if not isinstance(produits, list):
            raise ValueError(f"get_data a retourné un type inattendu: {type(produits)}")
        
        # Trier par display_order (source de vérité admin) avec COALESCE pour gérer les NULL
        # ORDER BY COALESCE(display_order, 999), nom
        # Les produits avec display_order NULL sont traités comme 999 (mis à la fin)
        produits.sort(key=lambda p: (
            p.get("display_order") if p.get("display_order") is not None else 999,  # COALESCE(display_order, 999)
            (p.get("nom", "") or "").lower()  # Tri secondaire par nom
        ))

        return {
            "produits": produits,
            "count": len(produits)
        }
    except HTTPException:
        # Re-propager les HTTPException telles quelles
        raise
    except ValueError as e:
        # Erreurs de validation (variables d'environnement, etc.)
        import traceback
        error_detail = f"Erreur de validation: {str(e)}\n\nTraceback:\n{traceback.format_exc()}"
        print(f"❌ Erreur dans get_catalogue (ValueError): {error_detail}")
        raise HTTPException(status_code=500, detail=error_detail)
    except Exception as e:
        # Toutes les autres exceptions
        import traceback
        error_detail = f"Erreur inattendue: {str(e)}\n\nType: {type(e).__name__}\nTraceback:\n{traceback.format_exc()}"
        print(f"❌ Erreur dans get_catalogue: {error_detail}")
        raise HTTPException(status_code=500, detail=error_detail)


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


@router.delete("/catalogue/{code_produit}", response_model=Dict[str, Any])
async def delete_produit(code_produit: str):
    """
    Supprime un produit du catalogue.
    """
    try:
        storage = get_supabase_storage()

        # Vérifier d'abord si le produit existe
        produits = storage.get_data("produits_catalogue", filters={"code_produit": code_produit})
        if not produits or len(produits) == 0:
            raise HTTPException(status_code=404, detail=f"Produit {code_produit} introuvable")

        # Supprimer le produit
        success = storage.delete_data("produits_catalogue", "code_produit", code_produit)

        if success:
            return {
                "success": True,
                "message": f"Produit {code_produit} supprimé"
            }
        else:
            raise HTTPException(status_code=500, detail=f"Échec de la suppression du produit {code_produit}")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")


# ============================================================
# Routes pour l'Inventaire par Technicien
# ============================================================

@router.get("/techniciens/all", response_model=Dict[str, Any])
async def get_all_techniciens_inventory():
    """
    Récupère l'inventaire de TOUS les techniciens.

    Utilisé par les dashboards de Nick, Louise et Jean-Philippe.

    Returns:
        - inventory: Liste de tous les items avec technicien, produit, quantité, emplacement
        - count: Nombre total d'items
    """
    try:
        storage = get_supabase_storage()

        # Récupérer toutes les entrées de la table inventaire_techniciens
        all_inventory = storage.get_data("inventaire_techniciens")

        # OPTIMISATION: Charger tout le catalogue une seule fois
        catalogue = storage.get_data("produits_catalogue")
        catalogue_map = {p['code_produit']: p for p in catalogue}

        # Enrichir avec les noms de produits depuis le catalogue
        for item in all_inventory:
            code_produit = item.get('code_produit')
            if code_produit and code_produit in catalogue_map:
                produit = catalogue_map[code_produit]
                item['nom_produit'] = produit.get('nom', code_produit)
                item['description'] = produit.get('description', '')
            else:
                item['nom_produit'] = code_produit

        return {
            "success": True,
            "inventory": all_inventory,
            "count": len(all_inventory)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur récupération inventaire: {str(e)}")


@router.get("/stock/{technicien}", response_model=Dict[str, Any])
async def get_stock_technicien(technicien: str):
    """
    Récupère l'inventaire complet d'un technicien.

    Path params:
        - technicien: Nom du technicien (ex: "Allan")
    """
    try:
        storage = get_supabase_storage()
        inventaire = storage.get_inventaire_technicien(technicien)

        return {
            "technicien": technicien,
            "inventaire": inventaire,
            "count": len(inventaire)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")


@router.post("/stock", response_model=Dict[str, Any])
async def mettre_a_jour_stock(maj: MiseAJourStock):
    """
    Met à jour directement le stock d'un produit (format V4).
    Calcule automatiquement l'ajustement nécessaire.

    Body:
        - code_produit: Code du produit
        - technicien: Nom du technicien
        - quantite_stock: Nouvelle quantité absolue
        - type_transaction: Type (défaut: "ajustement")
        - motif: Raison de l'ajustement
    """
    try:
        storage = get_supabase_storage()

        # Récupérer la quantité actuelle
        # IMPORTANT: Filtrer aussi par emplacement pour éviter les doublons
        inventaire = storage.get_data(
            "inventaire_techniciens",
            filters={
                "code_produit": maj.code_produit,
                "technicien": maj.technicien,
                "emplacement": "Atelier"  # Par défaut, utiliser "Atelier"
            }
        )
        
        # Si pas trouvé avec emplacement, chercher sans emplacement (compatibilité)
        if not inventaire:
            inventaire = storage.get_data(
                "inventaire_techniciens",
                filters={
                    "code_produit": maj.code_produit,
                    "technicien": maj.technicien
                }
            )

        quantite_actuelle = 0
        if inventaire:
            quantite_actuelle = int(inventaire[0].get("quantite_stock", 0))

        # Calculer l'ajustement
        quantite_ajustement = maj.quantite_stock - quantite_actuelle

        # Effectuer l'ajustement
        success = storage.update_stock(
            code_produit=maj.code_produit,
            technicien=maj.technicien,
            quantite_ajustement=quantite_ajustement,
            emplacement="Atelier",
            motif=maj.motif,
            created_by="interface"
        )

        if success:
            return {
                "success": True,
                "old_quantity": quantite_actuelle,
                "new_quantity": maj.quantite_stock,
                "message": f"Stock mis à jour pour {maj.technicien}"
            }
        else:
            raise HTTPException(status_code=500, detail="Échec de la mise à jour du stock")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")


@router.post("/stock/ajuster", response_model=Dict[str, Any])
async def ajuster_stock(ajustement: AjustementStock):
    """
    Ajuste le stock d'un produit pour un technicien (delta).

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


@router.post("/comment", response_model=Dict[str, Any])
async def envoyer_commentaire(commentaire: CommentaireInventaire):
    """
    Envoie un commentaire rapide sur l'inventaire (notification Slack admin).
    Format V4: Le technicien peut envoyer une demande/observation à l'admin via Slack.

    Body:
        - text: Texte du commentaire (ex: "Besoin urgent de coupelles brunes")
        - username: Nom de l'utilisateur (ex: "Allan")

    Returns:
        Confirmation d'envoi
    """
    try:
        # Envoyer notification Slack aux admins
        success = SlackNotifier.notify_inventory_comment(
            username=commentaire.username,
            comment=commentaire.text,
            notify_admin=True  # Notifier Allan (CTO)
        )

        if success:
            return {
                "success": True,
                "message": "Commentaire envoyé, Slack a été notifié."
            }
        else:
            # Ne pas bloquer si Slack échoue
            return {
                "success": True,
                "message": "Commentaire enregistré (notification Slack échouée)."
            }

    except Exception as e:
        print(f"⚠️ Erreur lors de l'envoi du commentaire: {e}")
        # Ne pas renvoyer d'erreur HTTP pour ne pas bloquer l'utilisateur
        return {
            "success": True,
            "message": "Commentaire enregistré (notification Slack échouée)."
        }


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
                # Récupérer le produit existant
                existing = storage.get_data(
                    "produits_catalogue",
                    filters={"code_produit": code_produit}
                )

                if not existing:
                    errors.append(f"{code_produit}: produit introuvable")
                    continue

                # Fusionner avec display_order
                product_data = {
                    **existing[0],
                    "display_order": display_order,
                    "updated_at": "NOW()"
                }

                success = storage.update_data(
                    "produits_catalogue",
                    product_data,
                    id_field="code_produit",
                    upsert=True
                )

                if success:
                    updated_count += 1
                else:
                    errors.append(f"{code_produit}: échec mise à jour")
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
        update_data = {"code_produit": code_produit}  # Inclure code_produit pour identifier l'enregistrement
        for field, value in produit.dict(exclude_unset=True).items():
            if value is not None:
                update_data[field] = value

        if len(update_data) <= 1:  # Seulement code_produit, rien à mettre à jour
            raise HTTPException(status_code=400, detail="Aucune donnée à mettre à jour")

        # Utiliser id_field="code_produit" et upsert=False pour UPDATE uniquement
        success = storage.update_data(
            "produits_catalogue",
            update_data,
            id_field="code_produit",
            upsert=False
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


# ============================================================
# Routes pour gestion des types et commissions (batch)
# ============================================================

@router.patch("/catalogue/batch-type-commission", response_model=Dict[str, Any])
async def batch_update_type_commission(update: BatchTypeCommissionUpdate):
    """
    Met à jour le type et/ou la commission de plusieurs produits en batch.

    Body:
        - codes_produit: Liste des codes produits à modifier
        - type_produit: 'produit', 'service', ou 'fourniture' (optionnel)
        - has_commission: true/false (optionnel)

    Logique:
        - Si type_produit = 'fourniture' → has_commission forcé à false
        - Si type_produit = 'produit' ou 'service' → has_commission optionnel
        - commission_rate automatiquement 10.00 si has_commission = true
    """
    try:
        storage = get_supabase_storage()

        if not update.codes_produit:
            raise HTTPException(status_code=400, detail="Aucun produit sélectionné")

        # Préparer les données de mise à jour
        update_data = {}

        # Gérer le type_produit
        if update.type_produit:
            if update.type_produit not in ['produit', 'service', 'fourniture']:
                raise HTTPException(
                    status_code=400,
                    detail="type_produit doit être 'produit', 'service' ou 'fourniture'"
                )
            update_data["type_produit"] = update.type_produit

            # Si fourniture, forcer has_commission à false
            if update.type_produit == 'fourniture':
                update_data["has_commission"] = False
                update_data["commission_rate"] = 0.00

        # Gérer has_commission (sauf si déjà forcé par fourniture)
        if update.has_commission is not None and update.type_produit != 'fourniture':
            update_data["has_commission"] = update.has_commission
            # Si commission activée, mettre le taux à 10%
            if update.has_commission:
                update_data["commission_rate"] = 10.00
            else:
                update_data["commission_rate"] = 0.00

        # Mettre à jour chaque produit
        updated_count = 0
        errors = []

        for code_produit in update.codes_produit:
            try:
                # Récupérer le produit existant
                existing_products = storage.get_data(
                    "produits_catalogue",
                    filters={"code_produit": code_produit}
                )

                if not existing_products:
                    errors.append(f"{code_produit}: produit introuvable")
                    continue

                # Fusionner les données existantes avec les modifications
                existing_product = existing_products[0]
                product_data = {
                    **existing_product,  # Garder toutes les données existantes
                    **update_data        # Écraser uniquement les champs modifiés
                }

                success = storage.update_data(
                    "produits_catalogue",
                    product_data,
                    id_field="code_produit",
                    upsert=True,
                    auto_timestamp=True
                )
                if success:
                    updated_count += 1
                else:
                    errors.append(f"{code_produit}: échec mise à jour")
            except Exception as e:
                errors.append(f"{code_produit}: {str(e)}")

        return {
            "success": True,
            "message": f"{updated_count}/{len(update.codes_produit)} produits mis à jour",
            "updated_count": updated_count,
            "total_count": len(update.codes_produit),
            "errors": errors if errors else None
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")


class ProductMergeRequest(BaseModel):
    """Modèle pour fusionner deux produits."""
    keep_code: str  # Code du produit à conserver
    merge_code: str  # Code du produit à supprimer (quantités transférées vers keep_code)


@router.post("/catalogue/merge", response_model=Dict[str, Any])
async def merge_products(request: ProductMergeRequest):
    """
    Fusionne deux produits en transférant les quantités.

    Processus:
    1. Récupère les stocks des deux produits pour tous les techniciens
    2. Additionne les quantités (keep_code += merge_code)
    3. Met à jour les stocks du produit conservé
    4. Archive le produit fusionné (is_active = false)

    Body:
        - keep_code: Code du produit à conserver
        - merge_code: Code du produit à supprimer

    Returns:
        - success: bool
        - message: Message de confirmation
        - technicians_updated: Nombre de techniciens mis à jour
    """
    try:
        storage = get_supabase_storage()

        # Validation
        if request.keep_code == request.merge_code:
            raise HTTPException(
                status_code=400,
                detail="Les deux produits doivent être différents"
            )

        # Vérifier que les deux produits existent
        keep_product = storage.get_data(
            "produits_catalogue",
            filters={"code_produit": request.keep_code}
        )
        merge_product = storage.get_data(
            "produits_catalogue",
            filters={"code_produit": request.merge_code}
        )

        if not keep_product:
            raise HTTPException(
                status_code=404,
                detail=f"Produit conservé introuvable: {request.keep_code}"
            )
        if not merge_product:
            raise HTTPException(
                status_code=404,
                detail=f"Produit à fusionner introuvable: {request.merge_code}"
            )

        # Récupérer les stocks pour tous les techniciens
        keep_stocks = storage.get_data(
            "inventaire_techniciens",
            filters={"code_produit": request.keep_code}
        )
        merge_stocks = storage.get_data(
            "inventaire_techniciens",
            filters={"code_produit": request.merge_code}
        )

        # Créer un mapping technicien -> quantités
        keep_map = {stock['technicien']: stock for stock in keep_stocks}
        merge_map = {stock['technicien']: stock for stock in merge_stocks}

        # Fusionner les quantités
        technicians_updated = 0
        all_technicians = set(list(keep_map.keys()) + list(merge_map.keys()))

        for tech in all_technicians:
            keep_qty = keep_map.get(tech, {}).get('quantite_stock', 0) or 0
            merge_qty = merge_map.get(tech, {}).get('quantite_stock', 0) or 0
            new_qty = keep_qty + merge_qty

            # Mettre à jour ou créer le stock pour le produit conservé
            stock_data = {
                'code_produit': request.keep_code,
                'technicien': tech,
                'quantite_stock': new_qty
            }

            success = storage.update_data(
                "inventaire_techniciens",
                stock_data,
                id_field="code_produit,technicien",
                upsert=True,
                auto_timestamp=True
            )

            if success:
                technicians_updated += 1

        # Supprimer les stocks du produit fusionné
        for tech in merge_map.keys():
            storage.client.table("inventaire_techniciens").delete().eq(
                "code_produit", request.merge_code
            ).eq("technicien", tech).execute()

        # Archiver le produit fusionné (is_active = false)
        merge_product_data = merge_product[0]
        merge_product_data['is_active'] = False
        storage.update_data(
            "produits_catalogue",
            merge_product_data,
            id_field="code_produit",
            upsert=True,
            auto_timestamp=True
        )

        return {
            "success": True,
            "message": f"Produits fusionnés: {request.merge_code} → {request.keep_code}",
            "technicians_updated": technicians_updated,
            "keep_product": keep_product[0]['nom'],
            "merged_product": merge_product[0]['nom']
        }

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Erreur fusion: {str(e)}")


# ============================================================
# Routes pour Synchronisation Gazelle
# ============================================================

def fuzzy_similarity(str1: str, str2: str) -> float:
    """
    Calcule la similarité entre deux chaînes (0.0 à 1.0).
    Utilise SequenceMatcher pour une comparaison fuzzy.
    """
    return difflib.SequenceMatcher(None, str1.lower(), str2.lower()).ratio()


@router.get("/gazelle/products", response_model=Dict[str, Any])
async def get_gazelle_products():
    """
    Récupère la liste des produits depuis Gazelle Master Service Items.

    Returns:
        - success: bool
        - products: Liste des produits Gazelle (avec noms FR et EN)
        - count: Nombre de produits
    """
    try:
        gazelle = GazelleAPIClient()
        products = gazelle.get_products(limit=1000)

        # Transformer pour frontend
        products_formatted = []
        for p in products:
            products_formatted.append({
                "gazelle_id": p.get('id'),
                "nom_fr": p.get('name_fr', ''),
                "nom_en": p.get('name_en', ''),
                "nom": p.get('name_fr', '') or p.get('name_en', ''),  # Priorité FR
                "description_fr": p.get('description_fr', ''),
                "description_en": p.get('description_en', ''),
                "description": p.get('description_fr', '') or p.get('description_en', ''),
                "groupe_fr": p.get('group_name_fr', ''),
                "groupe_en": p.get('group_name_en', ''),
                "prix_unitaire": float(p.get('amount', 0)) / 100 if p.get('amount') else 0,  # amount en cents
                "duree": p.get('duration', 0),
                "taxable": p.get('isTaxable', False),
                "archived": p.get('isArchived', False),
                "is_tuning": p.get('isTuning', False),
                "type": p.get('type', ''),
                "display_order": p.get('order', 0),
                "created_at": p.get('createdAt'),
                "updated_at": p.get('updatedAt')
            })

        return {
            "success": True,
            "products": products_formatted,
            "count": len(products_formatted)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur Gazelle API: {str(e)}")


@router.get("/gazelle/find-duplicates", response_model=Dict[str, Any])
async def find_duplicate_products(threshold: float = 0.80):
    """
    Détecte les doublons potentiels dans le catalogue local et/ou avec Gazelle.

    Query params:
        - threshold: Seuil de similarité (0.0-1.0, défaut 0.80)

    Returns:
        - success: bool
        - duplicates: Liste des paires de doublons potentiels
        - count: Nombre de doublons détectés
        - gazelle_available: bool - Indique si Gazelle est disponible
    """
    try:
        storage = get_supabase_storage()
        
        # Récupérer les produits locaux
        local_products = storage.get_data("produits_catalogue")
        
        duplicates = []
        gazelle_available = False
        gazelle_products = []

        # Essayer de se connecter à Gazelle (optionnel)
        try:
            gazelle = GazelleAPIClient()
            gazelle_products = gazelle.get_products(limit=1000)
            gazelle_available = True
        except (ValueError, FileNotFoundError) as e:
            # Gazelle non configuré, on continue sans
            gazelle_available = False
            print(f"⚠️ Gazelle non disponible: {str(e)}. Détection de doublons uniquement dans le catalogue local.")

        # Détecter les doublons dans le catalogue local
        for i, local1 in enumerate(local_products):
            local1_name = local1.get('nom', '').lower()
            local1_code = local1.get('code_produit', '')
            
            for j, local2 in enumerate(local_products[i+1:], start=i+1):
                local2_name = local2.get('nom', '').lower()
                local2_code = local2.get('code_produit', '')
                
                # Calculer similarité entre produits locaux
                similarity = fuzzy_similarity(local1_name, local2_name)
                
                if similarity >= threshold:
                    duplicates.append({
                        "local_code": local1_code,
                        "local_nom": local1.get('nom'),
                        "duplicate_code": local2_code,
                        "duplicate_nom": local2.get('nom'),
                        "similarity": round(similarity * 100, 1),
                        "type": "local"
                    })

        # Comparer avec Gazelle si disponible
        if gazelle_available and gazelle_products:
            for local in local_products:
                # ✅ EXCLUSION AUTOMATIQUE: Ignorer les produits déjà associés à Gazelle
                # Supporter les deux noms de colonne (legacy + nouveau)
                if local.get('gazelle_product_id') or local.get('gazelle_item_id'):
                    continue

                local_name = local.get('nom', '')
                if not local_name:
                    continue

                for gazelle_p in gazelle_products:
                    # Utiliser name_fr (déjà extrait dans get_products)
                    gazelle_name = gazelle_p.get('name_fr', '')
                    if not gazelle_name:
                        continue

                    # Calculer similarité
                    similarity = fuzzy_similarity(local_name, gazelle_name)

                    if similarity >= threshold:
                        duplicates.append({
                            "local_code": local.get('code_produit'),
                            "local_nom": local.get('nom'),
                            "local_price": local.get('prix_unitaire', 0),
                            "local_description": local.get('description', ''),
                            "gazelle_id": gazelle_p.get('id'),
                            "gazelle_nom": gazelle_p.get('name_fr', ''),
                            "gazelle_price": float(gazelle_p.get('amount', 0)) / 100,  # Convertir centimes → dollars
                            "gazelle_description": gazelle_p.get('description_fr', ''),
                            "similarity": round(similarity * 100, 1),
                            "price_diff": abs(
                                float(local.get('prix_unitaire', 0)) -
                                (float(gazelle_p.get('amount', 0)) / 100)  # Convertir centimes → dollars
                            ),
                            "type": "gazelle"
                        })

        # Trier par similarité décroissante
        duplicates.sort(key=lambda x: x['similarity'], reverse=True)

        return {
            "success": True,
            "duplicates": duplicates,
            "count": len(duplicates),
            "threshold": threshold,
            "gazelle_available": gazelle_available
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur détection doublons: {str(e)}")


class ProductMerge(BaseModel):
    """Modèle pour fusion de produits."""
    source_code: str  # Code produit à supprimer
    target_code: str  # Code produit à conserver
    update_prices: bool = True  # Mettre à jour les prix depuis Gazelle


@router.post("/catalogue/merge", response_model=Dict[str, Any])
async def merge_products(merge: ProductMerge):
    """
    Fusionne deux produits: transfère l'inventaire de source vers target, puis supprime source.

    Body:
        - source_code: Code du produit à supprimer
        - target_code: Code du produit à conserver
        - update_prices: Si True, met à jour les prix depuis Gazelle

    Returns:
        - success: bool
        - message: Message de confirmation
    """
    try:
        storage = get_supabase_storage()

        # Vérifier que les deux produits existent
        source = storage.get_data("produits_catalogue", filters={"code_produit": merge.source_code})
        target = storage.get_data("produits_catalogue", filters={"code_produit": merge.target_code})

        if not source:
            raise HTTPException(status_code=404, detail=f"Produit source {merge.source_code} introuvable")
        if not target:
            raise HTTPException(status_code=404, detail=f"Produit cible {merge.target_code} introuvable")

        source = source[0]
        target = target[0]

        # 1. Transférer l'inventaire de source vers target
        source_inventory = storage.get_data("inventaire_techniciens", filters={"code_produit": merge.source_code})

        for inv in source_inventory:
            technicien = inv.get('technicien')
            quantite_source = inv.get('quantite_stock', 0)

            # Récupérer l'inventaire existant pour target
            target_inventory = storage.get_data(
                "inventaire_techniciens",
                filters={"code_produit": merge.target_code, "technicien": technicien}
            )

            if target_inventory:
                # Additionner les quantités
                new_quantity = target_inventory[0].get('quantite_stock', 0) + quantite_source
                storage.update_data(
                    "inventaire_techniciens",
                    {
                        **target_inventory[0],
                        "quantite_stock": new_quantity,
                        "updated_at": "NOW()"
                    },
                    id_field="id",
                    upsert=True
                )
            else:
                # Créer nouvelle ligne pour target
                storage.update_data(
                    "inventaire_techniciens",
                    {
                        "code_produit": merge.target_code,
                        "technicien": technicien,
                        "quantite_stock": quantite_source,
                        "emplacement": inv.get('emplacement', 'Atelier'),
                        "created_at": "NOW()",
                        "updated_at": "NOW()"
                    },
                    id_field="id",
                    upsert=True
                )

        # 2. Supprimer l'inventaire source
        # Note: Supabase ne supporte pas DELETE directement via update_data
        # Il faudrait utiliser supabase.table().delete() si disponible
        # Pour l'instant, on marque comme inactif

        # 3. Marquer le produit source comme inactif
        storage.update_data(
            "produits_catalogue",
            {
                **source,
                "is_active": False,
                "nom": f"[FUSIONNÉ] {source.get('nom')}",
                "updated_at": "NOW()"
            },
            id_field="code_produit",
            upsert=True
        )

        return {
            "success": True,
            "message": f"Produit {merge.source_code} fusionné dans {merge.target_code}",
            "inventory_transferred": len(source_inventory)
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur fusion: {str(e)}")


class GazelleMapping(BaseModel):
    """Modèle pour mapping produit local <-> Gazelle."""
    code_produit: str
    gazelle_product_id: str  # ID Gazelle est une string (ex: "mit_CX6CvWXbjs08vg70")
    update_prices: bool = True


@router.post("/catalogue/map-gazelle", response_model=Dict[str, Any])
async def map_to_gazelle_product(mapping: GazelleMapping):
    """
    Associe un produit local à un produit Gazelle.

    Body:
        - code_produit: Code du produit local
        - gazelle_product_id: ID du produit Gazelle
        - update_prices: Si True, synchronise les prix depuis Gazelle

    Returns:
        - success: bool
        - message: Message de confirmation
    """
    try:
        storage = get_supabase_storage()
        gazelle = GazelleAPIClient()

        # Vérifier que le produit local existe
        local_product = storage.get_data("produits_catalogue", filters={"code_produit": mapping.code_produit})
        if not local_product:
            raise HTTPException(status_code=404, detail=f"Produit {mapping.code_produit} introuvable")

        local_product = local_product[0]

        # ✅ VALIDATION: Vérifier si le produit est déjà associé à un autre produit Gazelle
        existing_gazelle_id = local_product.get('gazelle_product_id') or local_product.get('gazelle_item_id')
        if existing_gazelle_id:
            if existing_gazelle_id == mapping.gazelle_product_id:
                # Déjà associé au même produit Gazelle, juste mettre à jour les prix
                pass
            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"⚠️ Produit {mapping.code_produit} est déjà associé à Gazelle ID {existing_gazelle_id}. Dissociez-le d'abord avant de le réassocier."
                )

        # Récupérer les données Gazelle
        gazelle_products = gazelle.get_products(limit=1000)
        gazelle_product = next((p for p in gazelle_products if p.get('id') == mapping.gazelle_product_id), None)

        if not gazelle_product:
            raise HTTPException(status_code=404, detail=f"Produit Gazelle ID {mapping.gazelle_product_id} introuvable")

        # Préparer les données de mise à jour
        update_data = {
            "code_produit": mapping.code_produit,
            "gazelle_product_id": mapping.gazelle_product_id,
            "last_sync_at": datetime.now().isoformat()
        }

        # Mettre à jour les prix et infos si demandé
        if mapping.update_prices:
            update_data["prix_unitaire"] = float(gazelle_product.get('amount', 0)) / 100  # Convertir centimes → dollars
            update_data["nom"] = gazelle_product.get('name_fr', local_product.get('nom'))
            update_data["description"] = gazelle_product.get('description_fr', local_product.get('description'))

        # Sauvegarder (UPDATE seulement, pas UPSERT car le produit doit déjà exister)
        success = storage.update_data(
            "produits_catalogue",
            update_data,
            id_field="code_produit",
            upsert=False  # Pas de création, juste mise à jour
        )

        if not success:
            raise HTTPException(status_code=500, detail="Échec de la mise à jour")

        return {
            "success": True,
            "message": f"Produit {mapping.code_produit} associé à Gazelle ID {mapping.gazelle_product_id}",
            "price_updated": mapping.update_prices
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur mapping: {str(e)}")


@router.delete("/catalogue/{code_produit}", response_model=Dict[str, Any])
async def delete_product(code_produit: str):
    """
    Supprime un produit (ou le marque comme inactif).

    Path params:
        - code_produit: Code du produit à supprimer

    Returns:
        - success: bool
        - message: Message de confirmation
    """
    try:
        storage = get_supabase_storage()

        # Vérifier que le produit existe
        product = storage.get_data("produits_catalogue", filters={"code_produit": code_produit})
        if not product:
            raise HTTPException(status_code=404, detail=f"Produit {code_produit} introuvable")

        product = product[0]

        # Marquer comme inactif au lieu de supprimer
        success = storage.update_data(
            "produits_catalogue",
            {
                **product,
                "is_active": False,
                "updated_at": "NOW()"
            },
            id_field="code_produit",
            upsert=True
        )

        if not success:
            raise HTTPException(status_code=500, detail="Échec de la suppression")

        return {
            "success": True,
            "message": f"Produit {code_produit} marqué comme inactif"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur suppression: {str(e)}")


class GazelleImportProduct(BaseModel):
    """Modèle pour import d'un produit Gazelle."""
    gazelle_product_id: str
    has_commission: bool = False
    commission_rate: float = 0.0
    categorie: str = "Services"  # Catégorie par défaut
    type_produit: str = "service"  # Par défaut: service (pas d'inventaire)


@router.post("/catalogue/import-gazelle", response_model=Dict[str, Any])
async def import_gazelle_product(import_data: GazelleImportProduct):
    """
    Importe un produit Gazelle dans le catalogue local.

    Utilise l'ID Gazelle comme code_produit.

    Body:
        - gazelle_product_id: ID du produit Gazelle (sera aussi le code_produit)
        - has_commission: Si le produit a une commission (défaut: False)
        - commission_rate: Taux de commission en % (défaut: 0)
        - categorie: Catégorie du produit (défaut: "Services")
        - type_produit: produit/service/fourniture (défaut: "service")

    Returns:
        - success: bool
        - message: Message de confirmation
        - product: Données du produit importé
    """
    try:
        storage = get_supabase_storage()

        # Vérifier si le produit existe déjà
        existing = storage.get_data("produits_catalogue", filters={"code_produit": import_data.gazelle_product_id})
        if existing:
            raise HTTPException(
                status_code=409,
                detail=f"Produit {import_data.gazelle_product_id} déjà importé"
            )

        # Récupérer les données depuis Gazelle
        gazelle_client = GazelleAPIClient()
        all_products = gazelle_client.get_products(limit=1000)

        gazelle_product = next(
            (p for p in all_products if p['id'] == import_data.gazelle_product_id),
            None
        )

        if not gazelle_product:
            raise HTTPException(
                status_code=404,
                detail=f"Produit Gazelle {import_data.gazelle_product_id} introuvable"
            )

        # Créer le produit local avec l'ID Gazelle comme code_produit
        new_product = {
            "code_produit": import_data.gazelle_product_id,  # ← ID Gazelle utilisé comme code
            "nom": gazelle_product.get('name_fr', ''),
            "description": gazelle_product.get('description_fr', ''),
            "prix_unitaire": float(gazelle_product.get('amount', 0)) / 100,  # Centimes → dollars
            "categorie": import_data.categorie,
            "type_produit": import_data.type_produit,
            "has_commission": import_data.has_commission,
            "commission_rate": import_data.commission_rate if import_data.has_commission else 0.0,
            "gazelle_product_id": import_data.gazelle_product_id,
            "last_sync_at": "NOW()",
            "is_active": True,
            "created_at": "NOW()",
            "updated_at": "NOW()"
        }

        success = storage.update_data(
            "produits_catalogue",
            new_product,
            id_field="code_produit",
            upsert=True
        )

        if not success:
            raise HTTPException(status_code=500, detail="Échec de l'import")

        return {
            "success": True,
            "message": f"Produit '{gazelle_product.get('name_fr')}' importé avec succès",
            "product": new_product
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur import: {str(e)}")


@router.post("/catalogue/sync-gazelle")
async def sync_all_gazelle_products():
    """
    Synchronise automatiquement tous les produits déjà associés à Gazelle.

    Met à jour les prix, noms et descriptions depuis Master Service Items.

    Returns:
        Statistiques de synchronisation (updated, errors)
    """
    try:
        storage = SupabaseStorage()

        # 1. Récupérer tous les produits locaux qui ont un gazelle_product_id
        local_products = storage.get_data(
            "produits_catalogue",
            filters={"is_active": True}
        )

        linked_products = [
            p for p in local_products
            if p.get("gazelle_product_id") is not None
        ]

        if not linked_products:
            return {
                "success": True,
                "message": "Aucun produit associé à synchroniser",
                "updated": 0,
                "total": 0,
                "errors": []
            }

        # 2. Récupérer TOUS les produits Gazelle
        gazelle_client = GazelleAPIClient()
        gazelle_products = gazelle_client.get_products(limit=1000)

        # Créer un index par ID pour recherche rapide
        gazelle_by_id = {p['id']: p for p in gazelle_products}

        # 3. Mettre à jour chaque produit local avec les données Gazelle
        updated_count = 0
        errors = []

        for local_prod in linked_products:
            gazelle_id = local_prod.get("gazelle_product_id")
            gazelle_prod = gazelle_by_id.get(gazelle_id)

            if not gazelle_prod:
                errors.append({
                    "code_produit": local_prod.get("code_produit"),
                    "error": f"Produit Gazelle ID {gazelle_id} introuvable"
                })
                continue

            try:
                # Préparer les données de mise à jour
                update_data = {
                    "code_produit": local_prod.get("code_produit"),
                    "nom": gazelle_prod.get("name_fr", local_prod.get("nom")),
                    "prix_unitaire": float(gazelle_prod.get("amount", 0)) / 100,  # Convertir centimes → dollars
                    "description": gazelle_prod.get("description_fr", local_prod.get("description")),
                    "last_sync_at": datetime.now().isoformat()
                }

                # Mettre à jour dans Supabase
                success = storage.update_data(
                    "produits_catalogue",
                    update_data,
                    id_field="code_produit",
                    upsert=False
                )

                if success:
                    updated_count += 1
                else:
                    errors.append({
                        "code_produit": local_prod.get("code_produit"),
                        "error": "Échec mise à jour DB"
                    })

            except Exception as e:
                errors.append({
                    "code_produit": local_prod.get("code_produit"),
                    "error": str(e)
                })

        return {
            "success": True,
            "message": f"{updated_count}/{len(linked_products)} produits synchronisés",
            "updated": updated_count,
            "total": len(linked_products),
            "errors": errors if errors else None
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur synchronisation: {str(e)}")


@router.post("/catalogue/sync-gazelle-smart")
async def sync_gazelle_products_smart(force: bool = False, max_age_hours: int = 24):
    """
    Synchronise intelligemment les produits Gazelle - seulement si nécessaire.
    
    Ne fait appel à l'API que si :
    - force=True (synchronisation forcée)
    - Le produit n'a jamais été synchronisé (last_sync_at est None)
    - La dernière synchronisation est plus ancienne que max_age_hours
    
    Args:
        force: Forcer la synchronisation même si récente (défaut: False)
        max_age_hours: Nombre d'heures avant de considérer une sync comme obsolète (défaut: 24)
    
    Returns:
        Statistiques de synchronisation (updated, skipped, errors)
    """
    try:
        storage = SupabaseStorage()
        
        # 1. Récupérer tous les produits locaux qui ont un gazelle_product_id
        local_products = storage.get_data(
            "produits_catalogue",
            filters={"is_active": True}
        )
        
        linked_products = [
            p for p in local_products
            if p.get("gazelle_product_id") is not None
        ]
        
        if not linked_products:
            return {
                "success": True,
                "message": "Aucun produit associé à synchroniser",
                "updated": 0,
                "skipped": 0,
                "total": 0,
                "errors": []
            }
        
        # 2. Filtrer les produits qui nécessitent une synchronisation
        now = datetime.now(timezone.utc)
        products_to_sync = []
        skipped_count = 0

        for local_prod in linked_products:
            if force:
                products_to_sync.append(local_prod)
            else:
                last_sync = local_prod.get("last_sync_at")
                if last_sync is None:
                    # Jamais synchronisé
                    products_to_sync.append(local_prod)
                else:
                    # Vérifier l'âge de la dernière synchronisation
                    try:
                        last_sync_dt = datetime.fromisoformat(last_sync.replace('Z', '+00:00'))
                        if isinstance(last_sync_dt, datetime):
                            age_hours = (now - last_sync_dt).total_seconds() / 3600
                            if age_hours >= max_age_hours:
                                products_to_sync.append(local_prod)
                            else:
                                skipped_count += 1
                        else:
                            products_to_sync.append(local_prod)
                    except (ValueError, AttributeError):
                        # Erreur de parsing, on synchronise pour être sûr
                        products_to_sync.append(local_prod)
        
        if not products_to_sync:
            return {
                "success": True,
                "message": f"Aucune synchronisation nécessaire ({skipped_count} produits déjà à jour)",
                "updated": 0,
                "skipped": skipped_count,
                "total": len(linked_products),
                "errors": []
            }
        
        # 3. Récupérer les produits Gazelle (seulement si nécessaire)
        try:
            gazelle_client = GazelleAPIClient()
            gazelle_products = gazelle_client.get_products(limit=1000)
            gazelle_by_id = {p['id']: p for p in gazelle_products}
        except (ValueError, FileNotFoundError) as e:
            return {
                "success": False,
                "message": f"Gazelle non configuré: {str(e)}",
                "updated": 0,
                "skipped": skipped_count,
                "total": len(linked_products),
                "errors": [{"error": "Gazelle API non disponible"}]
            }
        
        # 4. Mettre à jour seulement les produits qui nécessitent une sync
        updated_count = 0
        errors = []
        
        for local_prod in products_to_sync:
            gazelle_id = local_prod.get("gazelle_product_id")
            gazelle_prod = gazelle_by_id.get(gazelle_id)
            
            if not gazelle_prod:
                errors.append({
                    "code_produit": local_prod.get("code_produit"),
                    "error": f"Produit Gazelle ID {gazelle_id} introuvable"
                })
                continue
            
            try:
                # Vérifier si les données ont changé (comparer prix)
                local_price = float(local_prod.get("prix_unitaire", 0))
                gazelle_price = float(gazelle_prod.get("amount", 0)) / 100  # amount en cents
                
                # Préparer les données de mise à jour
                update_data = {
                    "code_produit": local_prod.get("code_produit"),
                    "nom": gazelle_prod.get("name_fr", local_prod.get("nom")),
                    "prix_unitaire": gazelle_price,
                    "description": gazelle_prod.get("description_fr", local_prod.get("description")),
                    "last_sync_at": now.isoformat()
                }
                
                # Mettre à jour dans Supabase
                success = storage.update_data(
                    "produits_catalogue",
                    update_data,
                    id_field="code_produit",
                    upsert=False
                )
                
                if success:
                    updated_count += 1
                else:
                    errors.append({
                        "code_produit": local_prod.get("code_produit"),
                        "error": "Échec mise à jour DB"
                    })
                    
            except Exception as e:
                errors.append({
                    "code_produit": local_prod.get("code_produit"),
                    "error": str(e)
                })
        
        return {
            "success": True,
            "message": f"{updated_count}/{len(products_to_sync)} produits synchronisés ({skipped_count} déjà à jour)",
            "updated": updated_count,
            "skipped": skipped_count,
            "total": len(linked_products),
            "errors": errors if errors else None
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur synchronisation intelligente: {str(e)}")


@router.post("/catalogue/import-all-msl")
async def import_all_msl_items():
    """
    Importe TOUS les items du Master Service List (MSL) de Gazelle.
    
    Nécessaire pour :
    - Calcul des commissions (besoin de tous les prix MSL)
    - Mise à jour automatique de l'inventaire
    - S'assurer que tous les items sont dans le système
    
    Crée ou met à jour les produits dans le catalogue local.
    Les produits existants sont mis à jour, les nouveaux sont créés.
    
    Returns:
        Statistiques d'import (created, updated, errors)
    """
    try:
        storage = SupabaseStorage()
        
        # 1. Récupérer TOUS les produits Gazelle MSL
        try:
            gazelle_client = GazelleAPIClient()
            gazelle_products = gazelle_client.get_products(limit=1000)
        except (ValueError, FileNotFoundError) as e:
            raise HTTPException(
                status_code=400,
                detail=f"Gazelle non configuré: {str(e)}. Impossible d'importer les items MSL."
            )
        
        # 2. Récupérer les produits locaux existants
        local_products = storage.get_data("produits_catalogue")
        local_by_gazelle_id = {
            p.get("gazelle_product_id"): p
            for p in local_products
            if p.get("gazelle_product_id") is not None
        }
        local_by_code = {p.get("code_produit"): p for p in local_products}
        
        # 3. Traiter chaque produit Gazelle
        created_count = 0
        updated_count = 0
        errors = []
        
        for gazelle_prod in gazelle_products:
            gazelle_id = gazelle_prod.get('id')
            if not gazelle_id:
                continue
            
            try:
                # Générer un code_produit si nécessaire
                sku = gazelle_prod.get('sku', '')
                if sku:
                    code_produit = sku
                else:
                    # Utiliser l'ID Gazelle comme code si pas de SKU
                    code_produit = f"GAZ-{gazelle_id}"
                
                # Vérifier si le produit existe déjà
                existing_prod = local_by_gazelle_id.get(gazelle_id) or local_by_code.get(code_produit)
                
                # Préparer les données
                product_data = {
                    "code_produit": code_produit,
                    "gazelle_product_id": gazelle_id,
                    "nom": gazelle_prod.get("name_fr", "") or gazelle_prod.get("name_en", ""),
                    "prix_unitaire": float(gazelle_prod.get("amount", 0)) / 100,  # amount en cents
                    "description": gazelle_prod.get("description_fr", "") or gazelle_prod.get("description_en", ""),
                    "categorie": gazelle_prod.get("group_name_fr", "") or gazelle_prod.get("group_name_en", ""),
                    "is_active": not gazelle_prod.get("isArchived", False),
                    "last_sync_at": datetime.now().isoformat()
                }
                
                if existing_prod:
                    # Mettre à jour le produit existant
                    product_data["code_produit"] = existing_prod.get("code_produit")
                    success = storage.update_data(
                        "produits_catalogue",
                        product_data,
                        id_field="code_produit",
                        upsert=False
                    )
                    if success:
                        updated_count += 1
                    else:
                        errors.append({
                            "code_produit": code_produit,
                            "error": "Échec mise à jour"
                        })
                else:
                    # Créer un nouveau produit
                    # Ajouter les champs requis pour la création
                    product_type = gazelle_prod.get("type", "").lower()
                    product_name = (gazelle_prod.get("name_fr", "") or gazelle_prod.get("name_en", "")).lower()
                    
                    # Déterminer l'usage par défaut selon le type et le nom
                    # Services = commission uniquement (ex: "Grand entretien", "Tuning")
                    is_service = (
                        "service" in product_type or 
                        "entretien" in product_name or 
                        "tuning" in product_name or
                        "réparation" in product_name or
                        "maintenance" in product_name
                    )
                    
                    # Matériaux = inventaire (peuvent aussi avoir commission si vendus)
                    is_material = (
                        "material" in product_type or 
                        "fourniture" in product_type.lower() or
                        "corde" in product_name or
                        "feutre" in product_name or
                        "buvard" in product_name or
                        "gaine" in product_name
                    )
                    
                    # Par défaut:
                    # - Services = commission uniquement (ex: "Grand entretien")
                    # - Matériaux = inventaire uniquement (ex: "Buvard", "Gaine")
                    # - Matériaux vendus = inventaire ET commission (à définir manuellement après import)
                    #   Exemple: une corde vendue au client = inventaire (tracking) + commission (vente)
                    
                    # Déterminer usage_type
                    if is_service and not is_material:
                        usage_type = "commission"
                    elif is_material and not is_service:
                        usage_type = "inventory"
                    elif is_service and is_material:
                        usage_type = "both"
                    else:
                        usage_type = "both"  # Par défaut si indéterminé
                    
                    product_data.update({
                        "type": gazelle_prod.get("type", ""),
                        "display_order": gazelle_prod.get("order", 0),
                        "has_commission": is_service,  # Services ont commission par défaut, matériaux à définir manuellement
                        "is_active": True,
                        # Usage: services = commission, matériaux = inventaire
                        # Peut être modifié manuellement après import pour combiner les deux
                        "is_commission_item": is_service,
                        "is_inventory_item": is_material,
                        "usage_type": usage_type
                    })
                    
                    # Utiliser upsert=True pour créer le produit
                    success = storage.update_data(
                        "produits_catalogue",
                        product_data,
                        id_field="code_produit",
                        upsert=True
                    )
                    if success:
                        created_count += 1
                    else:
                        errors.append({
                            "code_produit": code_produit,
                            "error": "Échec création"
                        })
                        
            except Exception as e:
                errors.append({
                    "gazelle_id": gazelle_id,
                    "error": str(e)
                })
        
        return {
            "success": True,
            "message": f"Import MSL terminé: {created_count} créés, {updated_count} mis à jour",
            "created": created_count,
            "updated": updated_count,
            "total_msl": len(gazelle_products),
            "errors": errors if errors else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur import MSL: {str(e)}")


# ============================================================
# Routes pour gestion des règles de consommation (Service → Matériel)
# ============================================================

class ServiceConsumptionRule(BaseModel):
    """Modèle pour une règle de consommation service → matériel."""
    service_gazelle_id: str
    service_code_produit: Optional[str] = None
    material_code_produit: str
    quantity: float = 1.0
    is_optional: bool = False
    notes: Optional[str] = None


@router.post("/service-consumption/rules")
async def create_consumption_rule(rule: ServiceConsumptionRule):
    """
    Crée une règle de consommation (service → matériel).
    
    Exemple: "Entretien annuel" → consomme 1 buvard, 1 gaine, parfois 1 doublure
    
    Note: Pour créer plusieurs règles en une fois, utilisez /service-consumption/rules/batch
    """
    try:
        storage = SupabaseStorage()
        
        rule_data = {
            "service_gazelle_id": rule.service_gazelle_id,
            "service_code_produit": rule.service_code_produit,
            "material_code_produit": rule.material_code_produit,
            "quantity": rule.quantity,
            "is_optional": rule.is_optional,
            "notes": rule.notes
        }
        
        success = storage.update_data(
            "service_inventory_consumption",
            rule_data,
            id_field="id",
            upsert=True
        )
        
        if success:
            return {
                "success": True,
                "message": "Règle de consommation créée/mise à jour"
            }
        else:
            raise HTTPException(status_code=500, detail="Échec création règle")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")


class BatchServiceConsumptionRules(BaseModel):
    """Modèle pour créer plusieurs règles de consommation en une fois."""
    service_gazelle_id: str
    service_code_produit: Optional[str] = None
    materials: List[Dict[str, Any]]  # Liste de {material_code_produit, quantity, is_optional, notes}


@router.post("/service-consumption/rules/batch")
async def create_consumption_rules_batch(batch: BatchServiceConsumptionRules):
    """
    Crée plusieurs règles de consommation pour un service en une fois.
    
    Utile quand un service utilise plusieurs produits (ex: "Entretien annuel" → buvard + gaine + doublure).
    
    Exemple de requête:
    {
        "service_gazelle_id": "12345",
        "service_code_produit": "ENT-ANN",
        "materials": [
            {"material_code_produit": "BUV-001", "quantity": 1.0, "is_optional": false},
            {"material_code_produit": "GAIN-001", "quantity": 1.0, "is_optional": false},
            {"material_code_produit": "DOUB-001", "quantity": 1.0, "is_optional": true, "notes": "Parfois utilisé"}
        ]
    }
    """
    try:
        storage = SupabaseStorage()
        
        created_count = 0
        errors = []
        
        for material in batch.materials:
            try:
                rule_data = {
                    "service_gazelle_id": batch.service_gazelle_id,
                    "service_code_produit": batch.service_code_produit,
                    "material_code_produit": material.get("material_code_produit"),
                    "quantity": float(material.get("quantity", 1.0)),
                    "is_optional": material.get("is_optional", False),
                    "notes": material.get("notes")
                }
                
                # Utiliser la contrainte UNIQUE pour éviter les doublons
                # (service_gazelle_id, material_code_produit)
                success = storage.update_data(
                    "service_inventory_consumption",
                    rule_data,
                    id_field="id",
                    upsert=True
                )
                
                if success:
                    created_count += 1
                else:
                    errors.append({
                        "material_code_produit": material.get("material_code_produit"),
                        "error": "Échec création"
                    })
                    
            except Exception as e:
                errors.append({
                    "material_code_produit": material.get("material_code_produit", "unknown"),
                    "error": str(e)
                })
        
        return {
            "success": True,
            "message": f"{created_count}/{len(batch.materials)} règles créées/mises à jour",
            "created": created_count,
            "total": len(batch.materials),
            "errors": errors if errors else None
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")


@router.get("/service-consumption/rules")
async def get_consumption_rules(
    service_gazelle_id: Optional[str] = None,
    group_by_service: bool = False
):
    """
    Récupère les règles de consommation.
    
    Query params:
        - service_gazelle_id: Filtrer par service (optionnel)
        - group_by_service: Si true, groupe les règles par service (défaut: false)
    
    Returns:
        - Si group_by_service=false: Liste plate de toutes les règles
        - Si group_by_service=true: Dict organisé par service avec liste de matériaux
    """
    try:
        storage = SupabaseStorage()
        
        filters = {}
        if service_gazelle_id:
            filters["service_gazelle_id"] = service_gazelle_id
        
        rules = storage.get_data("service_inventory_consumption", filters=filters)
        
        if group_by_service:
            # Grouper par service
            grouped = {}
            for rule in rules:
                service_id = rule.get("service_gazelle_id")
                if service_id not in grouped:
                    grouped[service_id] = {
                        "service_gazelle_id": service_id,
                        "service_code_produit": rule.get("service_code_produit"),
                        "materials": []
                    }
                grouped[service_id]["materials"].append({
                    "material_code_produit": rule.get("material_code_produit"),
                    "quantity": rule.get("quantity"),
                    "is_optional": rule.get("is_optional"),
                    "notes": rule.get("notes"),
                    "rule_id": rule.get("id")
                })
            
            return {
                "success": True,
                "services": list(grouped.values()),
                "count": len(rules),
                "services_count": len(grouped)
            }
        else:
            return {
                "success": True,
                "rules": rules,
                "count": len(rules)
            }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")


@router.delete("/service-consumption/rules/{rule_id}")
async def delete_consumption_rule(rule_id: str):
    """Supprime une règle de consommation."""
    try:
        storage = SupabaseStorage()
        
        success = storage.delete_data("service_inventory_consumption", rule_id)
        
        if success:
            return {
                "success": True,
                "message": "Règle supprimée"
            }
        else:
            raise HTTPException(status_code=404, detail="Règle non trouvée")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")


@router.post("/service-consumption/apply-from-invoice")
async def apply_consumption_from_invoice(
    invoice_id: str,
    invoice_item_id: str,
    service_gazelle_id: str,
    technicien: str,
    date_service: str
):
    """
    Applique les règles de consommation depuis un item de facture.
    
    Args:
        invoice_id: ID de la facture
        invoice_item_id: ID de l'item de facture
        service_gazelle_id: ID Gazelle du service facturé
        technicien: Nom du technicien
        date_service: Date du service (ISO format)
    
    Returns:
        Liste des consommations appliquées
    """
    try:
        storage = SupabaseStorage()
        
        # 1. Récupérer les règles de consommation pour ce service
        rules = storage.get_data(
            "service_inventory_consumption",
            filters={"service_gazelle_id": service_gazelle_id}
        )
        
        if not rules:
            return {
                "success": True,
                "message": "Aucune règle de consommation pour ce service",
                "consumptions": []
            }
        
        # 2. Appliquer chaque règle (créer une transaction d'inventaire)
        consumptions = []
        
        for rule in rules:
            material_code = rule.get("material_code_produit")
            quantity = float(rule.get("quantity", 1.0))
            is_optional = rule.get("is_optional", False)
            
            # Créer l'enregistrement d'impact
            impact_data = {
                "invoice_id": invoice_id,
                "invoice_item_id": invoice_item_id,
                "service_gazelle_id": service_gazelle_id,
                "service_code_produit": rule.get("service_code_produit"),
                "material_code_produit": material_code,
                "quantity_consumed": quantity,
                "technicien": technicien,
                "date_service": date_service,
                "processed": False
            }
            
            # Enregistrer l'impact (sera traité plus tard pour mettre à jour l'inventaire)
            storage.update_data(
                "invoice_item_inventory_impact",
                impact_data,
                id_field="id",
                upsert=True
            )
            
            consumptions.append({
                "material_code": material_code,
                "quantity": quantity,
                "is_optional": is_optional
            })
        
        return {
            "success": True,
            "message": f"{len(consumptions)} consommation(s) enregistrée(s)",
            "consumptions": consumptions
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")


# ============================================================
# Routes pour Logs de Déductions d'Inventaire
# ============================================================

@router.get("/deduction-logs", response_model=Dict[str, Any])
async def get_deduction_logs(limit: int = 100):
    """
    Récupère les logs de déductions d'inventaire automatiques depuis sync_logs.

    Les déductions sont créées quand un service consomme des consommables
    (ex: Entretien annuel → consomme 1 buvard, 1 gaine).

    Query params:
        - limit: Nombre maximum de logs (défaut: 100)

    Returns:
        - logs: Liste des déductions avec date, produits, quantités, technicien
        - count: Nombre total de logs
    """
    try:
        storage = get_supabase_storage()

        # Récupérer les logs depuis sync_logs où script_name = 'Deduction_Inventaire_Auto'
        all_logs = storage.get_data("sync_logs")

        # Filtrer les logs de déduction
        deduction_logs = [
            log for log in all_logs
            if log.get('script_name') == 'Deduction_Inventaire_Auto'
        ]

        # Trier par date décroissante (plus récents d'abord)
        deduction_logs.sort(key=lambda x: x.get('created_at', ''), reverse=True)

        # Limiter le nombre de résultats
        deduction_logs = deduction_logs[:limit]

        return {
            "success": True,
            "logs": deduction_logs,
            "count": len(deduction_logs)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur chargement logs déduction: {str(e)}")


@router.get("/deduction-summary", response_model=Dict[str, Any])
async def get_deduction_summary(days: int = 30):
    """
    Récupère un résumé des déductions d'inventaire sur les X derniers jours.

    Query params:
        - days: Nombre de jours à analyser (défaut: 30)

    Returns:
        - summary: Statistiques par produit (produit, quantité totale déduite, nombre de déductions)
        - total_deductions: Nombre total de déductions
        - period_start: Date de début de la période
        - period_end: Date de fin de la période
    """
    try:
        storage = get_supabase_storage()

        # Calculer les dates de début et fin
        now = datetime.now()
        period_start = now - timedelta(days=days)

        # Récupérer tous les logs de déduction
        all_logs = storage.get_data("sync_logs")

        deduction_logs = [
            log for log in all_logs
            if log.get('script_name') == 'Deduction_Inventaire_Auto' and
            datetime.fromisoformat(log.get('created_at', '').replace('Z', '+00:00')) >= period_start
        ]

        # Agréger par produit
        summary = {}
        for log in deduction_logs:
            tables_updated = log.get('tables_updated', {})
            if isinstance(tables_updated, str):
                import json
                try:
                    tables_updated = json.loads(tables_updated)
                except:
                    tables_updated = {}

            # tables_updated format: {"produits": {"code": "BUV-001", "quantite": 1}, "ventes": 1}
            produit_info = tables_updated.get('produits', {})
            if isinstance(produit_info, dict):
                code_produit = produit_info.get('code', 'unknown')
                quantite = produit_info.get('quantite', 1)

                if code_produit not in summary:
                    summary[code_produit] = {
                        "code_produit": code_produit,
                        "total_quantity": 0,
                        "deduction_count": 0
                    }

                summary[code_produit]["total_quantity"] += quantite
                summary[code_produit]["deduction_count"] += 1

        # Convertir en liste et trier par quantité décroissante
        summary_list = list(summary.values())
        summary_list.sort(key=lambda x: x["total_quantity"], reverse=True)

        return {
            "success": True,
            "summary": summary_list,
            "total_deductions": len(deduction_logs),
            "period_start": period_start.isoformat(),
            "period_end": now.isoformat(),
            "days": days
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur calcul résumé déductions: {str(e)}")


@router.post("/process-deductions", response_model=Dict[str, Any])
async def trigger_deduction_processing(days: int = 7):
    """
    Déclenche le traitement des déductions d'inventaire automatiques.

    Analyse les factures récentes et crée des logs de déduction pour les services
    qui consomment des consommables (selon les règles définies).

    Query params:
        - days: Nombre de jours à analyser (défaut: 7)

    Returns:
        - success: True si le traitement s'est terminé
        - stats: Statistiques (factures traitées, déductions créées, erreurs)
        - message: Message de résumé
    """
    try:
        print(f"🔄 Déclenchement traitement déductions (derniers {days} jours)...")

        # Importer le processeur
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from modules.inventory_deductions.process_deductions import InventoryDeductionProcessor

        # Exécuter le traitement
        processor = InventoryDeductionProcessor(days_lookback=days)
        stats = processor.process_recent_invoices()

        return {
            "success": True,
            "message": f"Traitement terminé: {stats['deductions_created']} déductions créées",
            "stats": stats
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Erreur traitement déductions: {str(e)}"
        )


# ============================================================
# Routes pour Configuration des Règles de Déduction
# ============================================================

@router.get("/deduction-config/global-rule", response_model=Dict[str, Any])
async def get_global_deduction_rule():
    """
    Récupère la configuration de la règle globale de déduction automatique.

    La règle globale permet de déduire automatiquement toutes les fournitures
    et accessoires présents sur une facture du stock du technicien.

    Returns:
        - enabled: True si la règle est activée
        - description: Description de la règle
        - item_types: Types d'items concernés (fournitures, accessoires)
    """
    try:
        storage = get_supabase_storage()

        # Récupérer la config depuis system_settings
        settings = storage.get_data("system_settings", filters={"key": "deduction_global_rule"})

        if settings:
            config = settings[0].get('value', {})
            if isinstance(config, str):
                import json
                config = json.loads(config)
        else:
            # Config par défaut
            config = {
                "enabled": False,
                "item_types": ["fourniture", "accessoire"],
                "description": "Toute fourniture ou accessoire sur facture déclenche déduction automatique"
            }

        return {
            "success": True,
            "config": config
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur récupération config: {str(e)}")


class GlobalDeductionRuleUpdate(BaseModel):
    """Modèle pour mise à jour de la règle globale."""
    enabled: bool
    item_types: Optional[List[str]] = ["fourniture", "accessoire"]


@router.put("/deduction-config/global-rule", response_model=Dict[str, Any])
async def update_global_deduction_rule(config: GlobalDeductionRuleUpdate):
    """
    Met à jour la règle globale de déduction automatique.

    Body:
        - enabled: True pour activer, False pour désactiver
        - item_types: Types d'items concernés (optionnel)

    Returns:
        - success: True si mise à jour réussie
        - config: Configuration mise à jour
    """
    try:
        storage = get_supabase_storage()

        # Préparer la config
        config_value = {
            "enabled": config.enabled,
            "item_types": config.item_types,
            "description": "Toute fourniture ou accessoire sur facture déclenche déduction automatique",
            "updated_at": datetime.now().isoformat()
        }

        # Sauvegarder dans system_settings
        import json
        setting_data = {
            "key": "deduction_global_rule",
            "value": json.dumps(config_value)
        }

        success = storage.update_data(
            "system_settings",
            setting_data,
            id_field="key",
            upsert=True
        )

        if not success:
            raise HTTPException(status_code=500, detail="Échec mise à jour config")

        return {
            "success": True,
            "message": f"Règle globale {'activée' if config.enabled else 'désactivée'}",
            "config": config_value
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur mise à jour config: {str(e)}")


class KeywordDeductionRule(BaseModel):
    """Modèle pour règle de déduction par mot-clé."""
    keyword: str
    material_code_produit: str
    quantity: float = 1.0
    case_sensitive: bool = False
    notes: Optional[str] = None


@router.get("/deduction-config/keyword-rules", response_model=Dict[str, Any])
async def get_keyword_deduction_rules():
    """
    Récupère toutes les règles de déduction par mots-clés.

    Ces règles scannent les notes des factures pour détecter des mots-clés
    et déclencher automatiquement des déductions.

    Exemple: "Buvard remplacé" → Déduire 1x Buvard

    Returns:
        - rules: Liste des règles avec keyword, material, quantity
        - count: Nombre de règles actives
    """
    try:
        storage = get_supabase_storage()

        # Récupérer depuis une table dédiée ou system_settings
        rules = storage.get_data("keyword_deduction_rules")

        return {
            "success": True,
            "rules": rules,
            "count": len(rules)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur récupération règles: {str(e)}")


@router.post("/deduction-config/keyword-rules", response_model=Dict[str, Any])
async def create_keyword_deduction_rule(rule: KeywordDeductionRule):
    """
    Crée une nouvelle règle de déduction par mot-clé.

    Body:
        - keyword: Mot-clé à détecter (ex: "Buvard remplacé")
        - material_code_produit: Code du matériel à déduire
        - quantity: Quantité (défaut: 1.0)
        - case_sensitive: Sensible à la casse (défaut: False)
        - notes: Notes explicatives

    Returns:
        - success: True si création réussie
        - rule: Règle créée
    """
    try:
        storage = get_supabase_storage()

        rule_data = {
            "keyword": rule.keyword,
            "material_code_produit": rule.material_code_produit,
            "quantity": rule.quantity,
            "case_sensitive": rule.case_sensitive,
            "notes": rule.notes,
            "created_at": datetime.now().isoformat()
        }

        success = storage.update_data(
            "keyword_deduction_rules",
            rule_data,
            id_field="id",
            upsert=True
        )

        if not success:
            raise HTTPException(status_code=500, detail="Échec création règle")

        return {
            "success": True,
            "message": f"Règle créée: '{rule.keyword}' → {rule.material_code_produit}",
            "rule": rule_data
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur création règle: {str(e)}")


@router.delete("/deduction-config/keyword-rules/{rule_id}", response_model=Dict[str, Any])
async def delete_keyword_deduction_rule(rule_id: int):
    """
    Supprime une règle de déduction par mot-clé.

    Path params:
        - rule_id: ID de la règle à supprimer

    Returns:
        - success: True si suppression réussie
    """
    try:
        storage = get_supabase_storage()

        success = storage.delete_data("keyword_deduction_rules", "id", rule_id)

        if not success:
            raise HTTPException(status_code=404, detail="Règle introuvable")

        return {
            "success": True,
            "message": "Règle supprimée"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur suppression règle: {str(e)}")


@router.post("/deduction-config/preview", response_model=Dict[str, Any])
async def preview_deductions(days: int = 7):
    """
    Génère un aperçu des déductions qui seraient créées SANS les appliquer.

    Permet de vérifier les déductions avant validation définitive.

    Query params:
        - days: Nombre de jours à analyser (défaut: 7)

    Returns:
        - success: True si preview généré
        - preview: Liste des déductions prévues avec détails
        - total_deductions: Nombre total de déductions
        - by_technician: Déductions groupées par technicien
        - warnings: Avertissements (stock négatif, items inconnus, etc.)
    """
    try:
        # Import du processeur
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from modules.inventory_deductions.process_deductions import InventoryDeductionProcessor

        # Créer le processeur en mode preview (ne pas appliquer)
        processor = InventoryDeductionProcessor(days_lookback=days)

        # TODO: Ajouter mode preview au processeur
        # Pour l'instant, on simule avec la même logique mais sans écrire

        storage = get_supabase_storage()

        # Récupérer les factures récentes
        from core.gazelle_api_client import GazelleAPIClient
        api_client = GazelleAPIClient()

        cutoff_date = datetime.now() - timedelta(days=days)
        all_invoices = api_client.get_invoices(limit=None)

        recent_invoices = [
            inv for inv in all_invoices
            if inv.get('createdAt') and
            datetime.fromisoformat(inv.get('createdAt').replace('Z', '+00:00')) >= cutoff_date
        ]

        # Simuler les déductions sans les créer
        preview_deductions = []
        warnings = []
        by_technician = {}

        # Récupérer les règles de consommation
        consumption_rules = storage.get_data("service_inventory_consumption")
        rules_by_service = {}
        for rule in consumption_rules:
            service_id = rule.get('service_gazelle_id')
            if service_id:
                if service_id not in rules_by_service:
                    rules_by_service[service_id] = []
                rules_by_service[service_id].append(rule)

        # Analyser chaque facture
        for invoice in recent_invoices[:10]:  # Limiter à 10 pour preview rapide
            invoice_id = invoice.get('id')
            invoice_number = invoice.get('number', 'N/A')

            user_obj = invoice.get('user', {})
            user_id = user_obj.get('id') if user_obj else None

            # Mapper technicien (simplifié)
            technicien = "Allan"  # TODO: mapping réel

            items_connection = invoice.get('allInvoiceItems', {})
            items = items_connection.get('nodes', [])

            for item in items:
                item_type = item.get('type')
                description = item.get('description', '')
                quantity = float(item.get('quantity', 1.0))

                # Vérifier si règle existe
                if item_type in rules_by_service:
                    for rule in rules_by_service[item_type]:
                        material_code = rule.get('material_code_produit')
                        qty_per_service = float(rule.get('quantity', 1.0))
                        total_qty = qty_per_service * quantity

                        deduction = {
                            "invoice_number": invoice_number,
                            "technicien": technicien,
                            "service": description,
                            "material_code": material_code,
                            "quantity": total_qty,
                            "source": "service_rule"
                        }

                        preview_deductions.append(deduction)

                        # Grouper par technicien
                        if technicien not in by_technician:
                            by_technician[technicien] = []
                        by_technician[technicien].append(deduction)

        return {
            "success": True,
            "preview": preview_deductions,
            "total_deductions": len(preview_deductions),
            "by_technician": by_technician,
            "warnings": warnings,
            "period": {
                "days": days,
                "invoices_analyzed": len(recent_invoices[:10])
            }
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Erreur génération preview: {str(e)}")
