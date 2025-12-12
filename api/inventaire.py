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

        # Récupérer les produits
        produits = storage.get_data("produits_catalogue", filters=filters)
        
        # Trier par display_order (les produits sans display_order à la fin)
        produits.sort(key=lambda p: (p.get("display_order") is None, p.get("display_order") or 0))

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
    Détecte les doublons potentiels entre le catalogue local et Gazelle.

    Query params:
        - threshold: Seuil de similarité (0.0-1.0, défaut 0.80)

    Returns:
        - success: bool
        - duplicates: Liste des paires de doublons potentiels
        - count: Nombre de doublons détectés
    """
    try:
        storage = get_supabase_storage()
        gazelle = GazelleAPIClient()

        # Récupérer les produits locaux
        local_products = storage.get_data("produits_catalogue")

        # Récupérer les produits Gazelle
        gazelle_products = gazelle.get_products(limit=1000)

        duplicates = []

        # Comparer chaque produit local avec chaque produit Gazelle
        for local in local_products:
            local_name = local.get('nom', '').lower()

            for gazelle_p in gazelle_products:
                gazelle_name = gazelle_p.get('name', '').lower()

                # Calculer similarité
                similarity = fuzzy_similarity(local_name, gazelle_name)

                if similarity >= threshold:
                    duplicates.append({
                        "local_code": local.get('code_produit'),
                        "local_nom": local.get('nom'),
                        "gazelle_id": gazelle_p.get('id'),
                        "gazelle_sku": gazelle_p.get('sku'),
                        "gazelle_nom": gazelle_p.get('name'),
                        "similarity": round(similarity * 100, 1),
                        "price_diff": abs(
                            float(local.get('prix_unitaire', 0)) -
                            float(gazelle_p.get('unitPrice', 0))
                        )
                    })

        # Trier par similarité décroissante
        duplicates.sort(key=lambda x: x['similarity'], reverse=True)

        return {
            "success": True,
            "duplicates": duplicates,
            "count": len(duplicates),
            "threshold": threshold
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
    gazelle_product_id: int
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

        # Récupérer les données Gazelle
        gazelle_products = gazelle.get_products(limit=1000, active_only=False)
        gazelle_product = next((p for p in gazelle_products if p.get('id') == mapping.gazelle_product_id), None)

        if not gazelle_product:
            raise HTTPException(status_code=404, detail=f"Produit Gazelle ID {mapping.gazelle_product_id} introuvable")

        # Préparer les données de mise à jour
        update_data = {
            **local_product,
            "gazelle_product_id": mapping.gazelle_product_id,
            "last_sync_at": "NOW()"
        }

        # Mettre à jour les prix si demandé
        if mapping.update_prices:
            update_data["prix_unitaire"] = gazelle_product.get('unitPrice', local_product.get('prix_unitaire'))

        # Sauvegarder
        success = storage.update_data(
            "produits_catalogue",
            update_data,
            id_field="code_produit",
            upsert=True
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
                    "prix_unitaire": float(gazelle_prod.get("amount", 0)),
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
