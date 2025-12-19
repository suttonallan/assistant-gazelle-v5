#!/usr/bin/env python3
"""
API principale pour Assistant Gazelle V5.

Point d'entrée unique pour toutes les fonctionnalités.
"""

import os
import json
import time
from pathlib import Path
from dotenv import load_dotenv

# Charger les variables d'environnement depuis .env
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any, Optional
import requests

# Import des routes des modules
from api.vincent_dindy import router as vincent_dindy_router
from api.alertes_rv import router as alertes_rv_router
from api.inventaire import router as inventaire_router
from api.catalogue_routes import router as catalogue_router
from api.tournees import router as tournees_router
from api.assistant import router as assistant_router
from api.admin import router as admin_router
from api.place_des_arts import router as place_des_arts_router
from core.gazelle_api_client import GazelleAPIClient, OAUTH_TOKEN_URL, CONFIG_DIR

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
app.include_router(tournees_router)
app.include_router(assistant_router)
app.include_router(admin_router)
app.include_router(place_des_arts_router)


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
            "inventory",
            "assistant"
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
            },
            "assistant": {
                "chat": "POST /assistant/chat",
                "health": "GET /assistant/health"
            }
        }
    }


@app.get("/health")
async def health() -> Dict[str, str]:
    """Vérification de l'état de l'API."""
    return {"status": "healthy"}


# ============================================================
# OAuth Gazelle - Callback et diagnostic
# ============================================================

REDIRECT_URI_DEFAULT = os.getenv(
    "GAZELLE_REDIRECT_URI",
    "https://assistant-gazelle-v5-api.onrender.com/gazelle_oauth_callback"
)


def _exchange_code_for_token(code: str, redirect_uri: str) -> Dict[str, Any]:
    client_id = os.getenv("GAZELLE_CLIENT_ID")
    client_secret = os.getenv("GAZELLE_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise HTTPException(status_code=500, detail="GAZELLE_CLIENT_ID/SECRET manquants")

    payload = {
        "client_id": client_id,
        "client_secret": client_secret,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": redirect_uri,
    }
    resp = requests.post(OAUTH_TOKEN_URL, data=payload, timeout=15)
    if resp.status_code != 200:
        try:
            err = resp.json()
        except Exception:
            err = {"error": resp.text}
        raise HTTPException(status_code=resp.status_code, detail=err)
    data = resp.json()
    data.setdefault("created_at", int(time.time()))

    os.makedirs(CONFIG_DIR, exist_ok=True)
    token_path = Path(CONFIG_DIR) / "token.json"
    with open(token_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    return {"token_path": str(token_path), "token": data}


@app.get("/gazelle_oauth_callback")
async def gazelle_oauth_callback(code: Optional[str] = None, state: Optional[str] = None, request: Request = None):
    """
    Callback OAuth Gazelle.
    À configurer dans la console Gazelle : {REDIRECT_URI_DEFAULT}
    """
    if not code:
        raise HTTPException(status_code=400, detail="Paramètre code manquant")
    result = _exchange_code_for_token(code, REDIRECT_URI_DEFAULT)
    return {
        "success": True,
        "message": "Token Gazelle sauvegardé",
        "redirect_uri": REDIRECT_URI_DEFAULT,
        "token_path": result["token_path"]
    }


@app.get("/gazelle/check-appointments")
async def gazelle_check_appointments():
    """
    Vérifie les rendez-vous dans 14 jours créés il y a >= 4 mois.
    Retourne la liste pour notification Assistante.
    """
    try:
        client = GazelleAPIClient()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    query = """
    query UpcomingAppointments {
      appointments(last: 300) {
        nodes {
          id
          appointmentDate
          createdAt
          title
          status
        }
      }
    }
    """
    try:
        res = client._execute_query(query)
        nodes = res.get("data", {}).get("appointments", {}).get("nodes", [])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur API Gazelle: {e}")

    from datetime import datetime, timedelta
    today = datetime.utcnow().date()
    target_date = today + timedelta(days=14)
    cutoff = today - timedelta(days=120)

    matches = []
    for appt in nodes:
        appt_date_str = appt.get("appointmentDate")
        created_at_str = appt.get("createdAt")
        if not appt_date_str or not created_at_str:
            continue
        try:
            appt_date = datetime.fromisoformat(appt_date_str).date()
            created_at = datetime.fromisoformat(created_at_str).date()
        except Exception:
            continue
        if appt_date == target_date and created_at <= cutoff:
            matches.append({
                "id": appt.get("id"),
                "date": appt_date_str,
                "created_at": created_at_str,
                "title": appt.get("title"),
                "status": appt.get("status")
            })

    return {"target_date": str(target_date), "cutoff_created_at": str(cutoff), "matches": matches}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

