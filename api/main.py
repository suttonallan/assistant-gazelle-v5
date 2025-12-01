#!/usr/bin/env python3
"""
API principale pour Assistant Gazelle V5.

Point d'entrée unique pour toutes les fonctionnalités.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any

# Import des routes des modules
from api.vincent_dindy import router as vincent_dindy_router

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


@app.get("/")
async def root() -> Dict[str, Any]:
    """Endpoint racine de l'API."""
    return {
        "name": "Assistant Gazelle V5",
        "version": "1.0.0",
        "modules": [
            "vincent-dindy",
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

