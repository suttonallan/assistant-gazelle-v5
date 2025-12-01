#!/usr/bin/env python3
"""
API principale pour Assistant Gazelle V5.

Point d'entrée unique pour toutes les fonctionnalités.
"""

from fastapi import FastAPI
from typing import Dict, Any

app = FastAPI(
    title="Assistant Gazelle V5 API",
    description="API unifiée pour tous les modules de l'assistant Gazelle",
    version="1.0.0"
)


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
        ]
    }


@app.get("/health")
async def health() -> Dict[str, str]:
    """Vérification de l'état de l'API."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

