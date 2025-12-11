#!/usr/bin/env python3
"""
API principale pour Assistant Gazelle V5.

Point d'entrée unique pour toutes les fonctionnalités.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Charger les variables d'environnement depuis .env
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any

# Import des routes des modules
from api.vincent_dindy import router as vincent_dindy_router
from api.alertes_rv import router as alertes_rv_router
from api.inventaire import router as inventaire_router
from api.catalogue_routes import router as catalogue_router
from api.product_mapping import router as product_mapping_router

app = FastAPI(
    title="Assistant Gazelle V5 API",
    description="API unifiée pour tous les modules de l'assistant Gazelle",
    version="1.0.0"
)

# CORS - Permet au frontend d'appeler l'API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En production, remplace par ton domaine GitHub Pages
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Enregistrer les routes des modules
app.include_router(vincent_dindy_router)
app.include_router(alertes_rv_router)
app.include_router(inventaire_router)
app.include_router(catalogue_router)
app.include_router(product_mapping_router)


@app.get("/")
async def root() -> Dict[str, Any]:
    """Endpoint racine de l'API."""
    return {
        "name": "Assistant Gazelle V5",
        "version": "1.0.0",
        "modules": [
            "vincent-dindy",
            "alertes-rv",
            "humidity-alerts",
            "place-des-arts",
            "inventory"
        ],
        "endpoints": {
            "vincent-dindy": {
                "submit_report": "POST /vincent-dindy/reports",
                "list_reports": "GET /vincent-dindy/reports",
                "get_report": "GET /vincent-dindy/reports/{report_id}",
                "stats": "GET /vincent-dindy/stats"
            },
            "inventaire": {
                "catalogue": "GET /inventaire/catalogue",
                "create_produit": "POST /inventaire/catalogue",
                "update_produit": "PUT /inventaire/catalogue/{code_produit}",
                "delete_produit": "DELETE /inventaire/catalogue/{code_produit}",
                "stock_technicien": "GET /inventaire/stock/{technicien}",
                "ajuster_stock": "POST /inventaire/stock/ajuster",
                "transactions": "GET /inventaire/transactions",
                "stats_technicien": "GET /inventaire/stats/{technicien}"
            },
            "catalogue": {
                "add": "POST /api/catalogue/add",
                "list": "GET /api/catalogue"
            }
        }
    }


@app.get("/health")
async def health() -> Dict[str, str]:
    """Vérification de l'état de l'API."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

