#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de vérification et d'alerte des stocks d'inventaire - V5
Piano Technique Montréal - Assistant Gazelle V5

Adapté pour utiliser core/supabase_storage.py avec les tables V5:
- produits_catalogue
- inventaire_techniciens
- transactions_inventaire

Fonctionnalités:
- Vérifie les stocks bas (quantite_stock <= seuil personnalisable)
- Génère des alertes pour chaque produit en rupture ou sous le seuil
- Compatible avec l'API FastAPI
"""

import os
import sys
from datetime import datetime
from typing import Dict, List, Optional, Any
import logging
from pathlib import Path

# Ajouter le répertoire parent au path pour importer les modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.supabase_storage import SupabaseStorage

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def check_low_stock(
    technicien: Optional[str] = None,
    seuil_critique: float = 5.0
) -> List[Dict[str, Any]]:
    """
    Vérifie les stocks bas (quantite_stock <= seuil)

    Args:
        technicien: Nom du technicien (None = tous les techniciens)
        seuil_critique: Seuil en dessous duquel générer une alerte (défaut: 5.0)

    Returns:
        Liste de dicts avec les alertes de stock bas
    """
    try:
        storage = SupabaseStorage()
        logger.info("Connexion à Supabase réussie")

        # Récupérer l'inventaire
        if technicien:
            inventaire = storage.get_inventaire_technicien(technicien)
            logger.info(f"Vérification du stock pour technicien: {technicien}")
        else:
            # Tous les techniciens
            inventaire = storage.get_data("inventaire_techniciens")
            logger.info("Vérification du stock pour tous les techniciens")

        # Récupérer le catalogue pour enrichir les infos
        catalogue = storage.get_produits_catalogue()
        catalogue_map = {p["code_produit"]: p for p in catalogue}

        # Filtrer les stocks bas
        alertes = []
        for item in inventaire:
            quantite = float(item.get("quantite_stock", 0))
            code_produit = item.get("code_produit")

            if quantite <= seuil_critique:
                produit_info = catalogue_map.get(code_produit, {})

                alerte = {
                    "code_produit": code_produit,
                    "technicien": item.get("technicien"),
                    "emplacement": item.get("emplacement", "Non spécifié"),
                    "quantite_actuelle": quantite,
                    "seuil_critique": seuil_critique,
                    "nom_produit": produit_info.get("nom", "Inconnu"),
                    "categorie": produit_info.get("categorie", "Non catégorisé"),
                    "unite_mesure": produit_info.get("unite_mesure", "unité"),
                    "prix_unitaire": produit_info.get("prix_unitaire", 0),
                    "derniere_verification": item.get("derniere_verification"),
                    "severity": "critique" if quantite == 0 else "bas"
                }

                alertes.append(alerte)

                if quantite == 0:
                    logger.warning(f"⚠️ RUPTURE: {code_produit} - {produit_info.get('nom')} pour {item.get('technicien')}")
                else:
                    logger.info(f"📉 Stock bas: {code_produit} - {quantite} restant(s)")

        logger.info(f"✅ Vérification terminée: {len(alertes)} alerte(s) détectée(s)")
        return alertes

    except Exception as e:
        logger.error(f"❌ Erreur lors de la vérification du stock: {e}")
        import traceback
        traceback.print_exc()
        return []


def generate_stock_report(
    technicien: Optional[str] = None,
    seuil_critique: float = 5.0
) -> Dict[str, Any]:
    """
    Génère un rapport complet de l'état des stocks

    Args:
        technicien: Nom du technicien (None = tous)
        seuil_critique: Seuil pour alertes

    Returns:
        Dict avec statistiques et alertes
    """
    try:
        storage = SupabaseStorage()

        # Récupérer l'inventaire
        if technicien:
            inventaire = storage.get_inventaire_technicien(technicien)
        else:
            inventaire = storage.get_data("inventaire_techniciens")

        # Vérifier les stocks bas
        alertes = check_low_stock(technicien=technicien, seuil_critique=seuil_critique)

        # Calculer les statistiques
        total_produits = len(inventaire)
        total_alertes = len(alertes)
        alertes_critiques = len([a for a in alertes if a["severity"] == "critique"])
        alertes_bas = len([a for a in alertes if a["severity"] == "bas"])

        # Valeur totale du stock
        catalogue = storage.get_produits_catalogue()
        prix_map = {p["code_produit"]: p.get("prix_unitaire", 0) for p in catalogue}

        valeur_totale = sum(
            item.get("quantite_stock", 0) * prix_map.get(item["code_produit"], 0)
            for item in inventaire
        )

        # Répartition par catégorie
        categories = {}
        for item in inventaire:
            code = item["code_produit"]
            produit = next((p for p in catalogue if p["code_produit"] == code), None)
            if produit:
                cat = produit.get("categorie", "Autre")
                if cat not in categories:
                    categories[cat] = {"count": 0, "total_quantity": 0}
                categories[cat]["count"] += 1
                categories[cat]["total_quantity"] += item.get("quantite_stock", 0)

        rapport = {
            "generated_at": datetime.now().isoformat(),
            "technicien": technicien or "Tous les techniciens",
            "seuil_critique": seuil_critique,
            "statistiques": {
                "total_produits": total_produits,
                "total_alertes": total_alertes,
                "alertes_critiques": alertes_critiques,
                "alertes_bas_stock": alertes_bas,
                "valeur_totale_estimee": round(valeur_totale, 2),
                "categories": categories
            },
            "alertes": alertes,
            "summary": f"{total_alertes} alerte(s) détectée(s) ({alertes_critiques} critique(s), {alertes_bas} stock bas)"
        }

        logger.info(f"📊 Rapport généré: {rapport['summary']}")
        return rapport

    except Exception as e:
        logger.error(f"❌ Erreur lors de la génération du rapport: {e}")
        return {
            "generated_at": datetime.now().isoformat(),
            "error": str(e),
            "alertes": [],
            "summary": "Erreur lors de la génération du rapport"
        }


def run_stock_check(technicien: Optional[str] = None, seuil_critique: float = 5.0) -> Dict[str, Any]:
    """
    Point d'entrée principal pour la vérification automatique de stock
    Compatible avec les endpoints API FastAPI

    Args:
        technicien: Nom du technicien (None = tous)
        seuil_critique: Seuil pour alertes

    Returns:
        Rapport complet de l'état des stocks
    """
    logger.info("=" * 60)
    logger.info("🔍 Démarrage de la vérification automatique des stocks")
    logger.info(f"Technicien: {technicien or 'Tous'}")
    logger.info(f"Seuil critique: {seuil_critique}")
    logger.info("=" * 60)

    rapport = generate_stock_report(technicien=technicien, seuil_critique=seuil_critique)

    logger.info("=" * 60)
    logger.info(f"✅ Vérification terminée: {rapport.get('summary', 'N/A')}")
    logger.info("=" * 60)

    return rapport


if __name__ == "__main__":
    # Test en local
    import argparse

    parser = argparse.ArgumentParser(description="Vérification des stocks d'inventaire")
    parser.add_argument("--technicien", type=str, help="Nom du technicien (défaut: tous)")
    parser.add_argument("--seuil", type=float, default=5.0, help="Seuil critique (défaut: 5.0)")
    parser.add_argument("--json", action="store_true", help="Sortie en JSON")

    args = parser.parse_args()

    rapport = run_stock_check(technicien=args.technicien, seuil_critique=args.seuil)

    if args.json:
        import json
        print(json.dumps(rapport, indent=2, ensure_ascii=False))
    else:
        print(f"\n📊 RAPPORT DE STOCK - {rapport['generated_at']}")
        print("=" * 60)
        print(f"Technicien: {rapport['technicien']}")
        print(f"Seuil critique: {rapport['seuil_critique']}")
        print("\n📈 STATISTIQUES:")
        stats = rapport['statistiques']
        print(f"  - Total produits: {stats['total_produits']}")
        print(f"  - Alertes totales: {stats['total_alertes']}")
        print(f"  - Alertes critiques (rupture): {stats['alertes_critiques']}")
        print(f"  - Alertes stock bas: {stats['alertes_bas_stock']}")
        print(f"  - Valeur totale estimée: {stats['valeur_totale_estimee']} $")

        if rapport['alertes']:
            print("\n⚠️ ALERTES:")
            for alerte in rapport['alertes']:
                severity_icon = "🔴" if alerte['severity'] == 'critique' else "🟡"
                print(f"  {severity_icon} {alerte['code_produit']} - {alerte['nom_produit']}")
                print(f"     Technicien: {alerte['technicien']} | Emplacement: {alerte['emplacement']}")
                print(f"     Stock actuel: {alerte['quantite_actuelle']} {alerte['unite_mesure']}")
        else:
            print("\n✅ Aucune alerte détectée. Tous les stocks sont OK.")
