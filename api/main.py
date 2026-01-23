#!/usr/bin/env python3
"""
API principale pour Assistant Gazelle V5.

Point d'entrée unique pour toutes les fonctionnalités.
"""

import os
import json
import time
import hmac
import hashlib
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Charger les variables d'environnement depuis .env
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any, Optional
import requests

# Import des routes des modules
from api.institutions import router as institutions_router
from api.vincent_dindy import router as vincent_dindy_router
from api.alertes_rv import router as alertes_rv_router
from api.tableau_de_bord_routes import router_alertes, router_pianos, router_system  # 🆕 Tableau de Bord unifié (3 routers)
from api.inventaire import router as inventaire_router
from api.catalogue_routes import router as catalogue_router
from api.tournees import router as tournees_router
from api.assistant import router as assistant_router
from api.admin import router as admin_router
from api.place_des_arts import router as place_des_arts_router
from api.reports import router as reports_router
from api.chat_routes import router as chat_router
from api.conversation_routes import router as conversation_router  # Nouvel assistant conversationnel
from api.scheduler_routes import router as scheduler_router
from api.sync_logs_routes import router as sync_logs_router
from api.scheduler_logs_routes import router as scheduler_logs_router
from api.humidity_alerts_routes import router as humidity_alerts_router
from core.gazelle_api_client import GazelleAPIClient, OAUTH_TOKEN_URL, CONFIG_DIR

app = FastAPI(
    title="Assistant Gazelle V5 API",
    description="API unifiée pour tous les modules de l'assistant Gazelle",
    version="1.0.0"
)


@app.on_event("startup")
async def startup_event():
    """Validation des variables d'environnement critiques au démarrage."""
    print("\n" + "="*60)
    print("🚀 DÉMARRAGE API ASSISTANT GAZELLE V5")
    print("="*60)
    
    # Initialiser les singletons au démarrage pour éviter les réinitialisations
    try:
        from api.place_des_arts import get_storage, get_api_client
        print("\n🔧 Initialisation des singletons...")
        get_storage()  # Initialise SupabaseStorage (singleton)
        get_api_client()  # Initialise GazelleAPIClient (singleton)
        print("✅ Singletons initialisés")
    except Exception as e:
        print(f"⚠️  Erreur lors de l'initialisation des singletons: {e}")
    
    # Discovery automatique des institutions depuis Gazelle
    try:
        from api.institutions import discover_and_sync_institutions
        print("\n🔍 Discovery automatique des institutions...")
        result = discover_and_sync_institutions()
        if result.get("success"):
            print(f"✅ {result.get('synced_count', 0)} institutions synchronisées: {', '.join(result.get('institutions', []))}")
        else:
            print(f"⚠️  Discovery échoué: {result.get('error', 'Erreur inconnue')}")
    except Exception as e:
        print(f"⚠️  Erreur lors du discovery des institutions: {e}")
        # Ne pas bloquer le démarrage si le discovery échoue

    # Vérification des variables d'environnement critiques
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY', os.getenv('SUPABASE_KEY'))
    gazelle_client_id = os.getenv('GAZELLE_CLIENT_ID')
    gazelle_client_secret = os.getenv('GAZELLE_CLIENT_SECRET')

    print("\n📋 Variables d'environnement:")
    print(f"   SUPABASE_URL: {'✅ Défini' if supabase_url else '❌ MANQUANT'}")
    if supabase_url:
        print(f"      → {supabase_url}")

    print(f"   SUPABASE_KEY: {'✅ Défini' if os.getenv('SUPABASE_KEY') else '⚠️  Non défini'}")
    print(f"   SUPABASE_SERVICE_ROLE_KEY: {'✅ Défini' if os.getenv('SUPABASE_SERVICE_ROLE_KEY') else '⚠️  Non défini'}")
    print(f"   → Clé utilisée: {'✅ Défini' if supabase_key else '❌ MANQUANT'}")

    print(f"   GAZELLE_CLIENT_ID: {'✅ Défini' if gazelle_client_id else '⚠️  Non défini'}")
    print(f"   GAZELLE_CLIENT_SECRET: {'✅ Défini' if gazelle_client_secret else '⚠️  Non défini'}")

    # Variables critiques obligatoires
    if not supabase_url or not supabase_key:
        print("\n❌ ERREUR: Variables Supabase manquantes!")
        print("   L'API ne pourra pas se connecter à Supabase.")
        print("   Vérifiez SUPABASE_URL et SUPABASE_KEY/SUPABASE_SERVICE_ROLE_KEY")
    else:
        print("\n✅ Variables Supabase OK")

    print("\n" + "="*60)
    print("✅ API PRÊTE")
    print("="*60 + "\n")

    # Démarrer le scheduler pour les tâches planifiées
    try:
        from core.scheduler import start_scheduler
        start_scheduler()
    except Exception as e:
        print(f"⚠️  Erreur lors du démarrage du scheduler: {e}")
        print("   L'API continuera à fonctionner sans tâches planifiées.")


@app.on_event("shutdown")
async def shutdown_event():
    """Arrête le scheduler proprement lors de l'arrêt de l'API."""
    try:
        from core.scheduler import stop_scheduler
        stop_scheduler()
    except Exception as e:
        print(f"⚠️  Erreur lors de l'arrêt du scheduler: {e}")

# CORS - Permet au frontend d'appeler l'API
# Autoriser les ports de développement Vite (5173, 5174, 5175) et production
# NOTE: allow_credentials=True ne peut pas être utilisé avec "*", donc on liste explicitement
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5175",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://127.0.0.1:5175",
        "https://suttonallan.github.io",  # Production GitHub Pages
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Enregistrer les routes des modules
# IMPORTANT: Les routes sont enregistrées 2 fois pour supporter dev ET prod
#
# Développement (avec Vite proxy):
#   Frontend → /api/vincent-dindy/... → Vite proxy retire /api → Backend /vincent-dindy/...
#
# Production (GitHub Pages → Render direct):
#   Frontend → https://.../api/vincent-dindy/... → Backend /api/vincent-dindy/...
#
# Solution: Enregistrer les routes AVEC et SANS préfixe /api

# Routes SANS /api (pour développement avec proxy Vite)
# IMPORTANT: humidity_alerts_router AVANT institutions_router pour éviter les conflits de routes
app.include_router(humidity_alerts_router)
app.include_router(router_alertes)  # 🆕 Tableau de Bord - Alertes
app.include_router(router_pianos)   # 🆕 Tableau de Bord - Pianos
app.include_router(router_system)   # 🆕 Tableau de Bord - Système
app.include_router(vincent_dindy_router)
app.include_router(alertes_rv_router)
app.include_router(inventaire_router)
app.include_router(catalogue_router)
app.include_router(tournees_router)
app.include_router(assistant_router)
app.include_router(admin_router)
app.include_router(place_des_arts_router)
app.include_router(reports_router)
app.include_router(chat_router)
app.include_router(conversation_router)  # Assistant conversationnel intelligent
app.include_router(scheduler_router)
app.include_router(sync_logs_router)
app.include_router(scheduler_logs_router)
app.include_router(institutions_router)  # Route dynamique /{institution}/pianos - DOIT ÊTRE EN DERNIER

# Routes AVEC /api (pour production sans proxy)
# IMPORTANT: humidity_alerts_router AVANT institutions_router pour éviter les conflits de routes
app.include_router(humidity_alerts_router, prefix="/api")
app.include_router(router_alertes, prefix="/api")  # 🆕 Tableau de Bord - Alertes
app.include_router(router_pianos, prefix="/api")   # 🆕 Tableau de Bord - Pianos
app.include_router(router_system, prefix="/api")   # 🆕 Tableau de Bord - Système
app.include_router(vincent_dindy_router, prefix="/api")
app.include_router(alertes_rv_router, prefix="/api")
app.include_router(inventaire_router, prefix="/api")
app.include_router(catalogue_router, prefix="/api")
app.include_router(tournees_router, prefix="/api")
app.include_router(assistant_router, prefix="/api")
app.include_router(admin_router, prefix="/api")
app.include_router(place_des_arts_router, prefix="/api")
app.include_router(reports_router, prefix="/api")
app.include_router(chat_router, prefix="/api")
app.include_router(conversation_router, prefix="/api")  # Assistant conversationnel intelligent
app.include_router(scheduler_router, prefix="/api")
app.include_router(sync_logs_router, prefix="/api")
app.include_router(scheduler_logs_router, prefix="/api")
app.include_router(institutions_router, prefix="/api")  # Route dynamique /api/{institution}/pianos - DOIT ÊTRE EN DERNIER


# ============================================================
# Webhook Zoom pour SMS
# ============================================================

@app.post("/api/zoom/webhook")
async def zoom_webhook(request: Request):
    """
    Webhook Zoom pour recevoir des SMS et déclencher des actions (emails, notifications).
    
    Gère:
    - Validation de l'URL par Zoom (endpoint.url_validation) - OBLIGATOIRE
    - Réception des SMS
    - Envoi d'emails via SendGrid
    """
    try:
        data = await request.json()
        
        # DEBUG: Afficher le JSON complet pour comprendre la structure
        import json
        print("="*70)
        print("📥 WEBHOOK ZOOM - JSON COMPLET REÇU")
        print("="*70)
        print(json.dumps(data, indent=2, default=str))
        print("="*70)
        
        # 1. Validation de l'URL par Zoom (obligatoire)
        # Zoom envoie un défi (challenge) pour vérifier que le serveur vous appartient
        if data and data.get('event') == 'endpoint.url_validation':
            plain_token = data.get('payload', {}).get('plainToken')
            if not plain_token:
                raise HTTPException(status_code=400, detail="plainToken manquant dans le payload")
            
            # Récupérer le secret token depuis .env
            secret_token = os.environ.get('ZOOM_SECRET_TOKEN')
            if not secret_token:
                print("⚠️ ZOOM_SECRET_TOKEN non configuré dans .env")
                raise HTTPException(
                    status_code=500,
                    detail="ZOOM_SECRET_TOKEN non configuré. Ajoutez-le dans votre .env"
                )
            
            # Générer la signature HMAC SHA256
            mess = plain_token.encode('utf-8')
            sec = secret_token.encode('utf-8')
            hash_for_validate = hmac.new(sec, mess, hashlib.sha256).hexdigest()
            
            print(f"✅ Validation URL Zoom réussie pour token: {plain_token[:10]}...")
            
            return {
                "plainToken": plain_token,
                "encryptedToken": hash_for_validate
            }

        # 2. Traitement des SMS
        event = data.get('event', '').lower()
        if 'sms' in event:
            payload = data.get('payload', {})
            sms_object = payload.get('object', {})
            
            # DEBUG: Afficher la structure du payload SMS
            print("\n📋 STRUCTURE PAYLOAD SMS:")
            print(f"   payload keys: {list(payload.keys())}")
            print(f"   object keys: {list(sms_object.keys()) if sms_object else 'None'}")
            
            # Extraire le contenu du message (plusieurs chemins possibles)
            content = (
                sms_object.get('message') or 
                sms_object.get('text') or 
                sms_object.get('content') or 
                payload.get('message') or 
                payload.get('text') or 
                ''
            )
            
            # Extraire l'expéditeur (plusieurs chemins possibles selon structure Zoom)
            sender = (
                sms_object.get('sender_number') or
                sms_object.get('from_number') or
                sms_object.get('from') or
                sms_object.get('sender') or
                payload.get('sender_number') or
                payload.get('from_number') or
                payload.get('from') or
                payload.get('sender') or
                'Inconnu'
            )
            
            # Extraire le destinataire (plusieurs chemins possibles)
            recipient = (
                sms_object.get('recipient_number') or
                sms_object.get('receiver_number') or
                sms_object.get('to_number') or
                sms_object.get('to') or
                sms_object.get('recipient') or
                payload.get('recipient_number') or
                payload.get('receiver_number') or
                payload.get('to_number') or
                payload.get('to') or
                payload.get('recipient') or
                'Inconnu'
            )
            
            # Extraire le timestamp
            timestamp = (
                sms_object.get('timestamp') or
                sms_object.get('time') or
                sms_object.get('created_at') or
                payload.get('timestamp') or
                payload.get('time') or
                data.get('event_ts') or
                datetime.now().isoformat()
            )
            
            print(f"\n📩 SMS EXTRACTION:")
            print(f"   Expéditeur: {sender}")
            print(f"   Destinataire: {recipient}")
            print(f"   Message: {content[:100]}..." if len(content) > 100 else f"   Message: {content}")
            print(f"   Timestamp: {timestamp}")
            
            print(f"\n📩 SMS Reçu de {sender} → {recipient}: {content}")
            
            # Envoyer un email via SendGrid
            try:
                from core.email_notifier import EmailNotifier
                email_notifier = EmailNotifier()
                
                if email_notifier.client:
                    recipient_email = os.getenv('EMAIL_ALLAN', 'asutton@piano-tek.com')
                    
                    html_content = f"""
                    <h2>📩 SMS Reçu via Zoom</h2>
                    <div style="background: #f5f5f5; padding: 15px; border-radius: 5px; margin: 15px 0;">
                        <p><strong>De:</strong> {sender}</p>
                        <p><strong>À:</strong> {recipient}</p>
                        <p><strong>Date:</strong> {timestamp}</p>
                    </div>
                    <div style="background: #e8f4f8; padding: 15px; border-radius: 5px; margin: 15px 0;">
                        <p><strong>Message:</strong></p>
                        <p style="white-space: pre-wrap;">{content}</p>
                    </div>
                    <hr>
                    <p style="color: #666; font-size: 12px;">Reçu via Zoom Webhook - Assistant Gazelle V5</p>
                    """
                    
                    plain_content = f"SMS Reçu de {sender} → {recipient}\nDate: {timestamp}\n\nMessage:\n{content}"
                    
                    success = email_notifier.send_email(
                        to_emails=[recipient_email],
                        subject=f"📩 SMS Reçu de {sender}",
                        html_content=html_content,
                        plain_content=plain_content
                    )
                    
                    if success:
                        print(f"✅ Email envoyé avec succès à {recipient_email}")
                    else:
                        print(f"⚠️ Échec de l'envoi d'email à {recipient_email}")
                else:
                    print("⚠️ SendGrid non configuré - email non envoyé")
                    
            except Exception as e:
                print(f"❌ Erreur lors de l'envoi d'email: {e}")
                import traceback
                traceback.print_exc()
            
            return {"status": "received", "message": "SMS traité avec succès"}

        # Autres événements non gérés
        print(f"ℹ️ Événement Zoom reçu (non traité): {data.get('event', 'unknown')}")
        return {"status": "received", "message": "Événement reçu mais non traité"}

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Erreur lors du traitement du webhook Zoom: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Erreur serveur: {str(e)}")


@app.get("/api/zoom/webhook/health")
async def zoom_webhook_health():
    """Health check pour le webhook Zoom."""
    return {
        "status": "ok",
        "service": "zoom-webhook",
        "zoom_secret_token_configured": bool(os.getenv('ZOOM_SECRET_TOKEN')),
        "email_notifier_configured": bool(os.getenv('SENDGRID_API_KEY'))
    }


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
    """
    Échange le code OAuth contre des tokens (access + refresh).
    Sauvegarde les tokens dans Supabase system_settings pour persistance cloud.
    """
    from core.supabase_storage import SupabaseStorage

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

    print(f"🔄 Échange du code OAuth avec Gazelle...")
    resp = requests.post(OAUTH_TOKEN_URL, data=payload, timeout=15)

    if resp.status_code != 200:
        try:
            err = resp.json()
        except Exception:
            err = {"error": resp.text}
        print(f"❌ Erreur échange token: {resp.status_code} - {err}")
        raise HTTPException(status_code=resp.status_code, detail=err)

    data = resp.json()
    data.setdefault("created_at", int(time.time()))

    # Sauvegarder dans Supabase system_settings (persistant sur cloud)
    storage = SupabaseStorage()
    try:
        storage.save_system_setting("gazelle_oauth_token", data)
        print(f"✅ Token sauvegardé dans Supabase system_settings")
    except Exception as e:
        print(f"⚠️ Erreur sauvegarde Supabase: {e}")
        # Fallback: sauvegarder localement aussi
        os.makedirs(CONFIG_DIR, exist_ok=True)
        token_path = Path(CONFIG_DIR) / "token.json"
        with open(token_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        print(f"   → Token sauvegardé localement: {token_path}")

    return {
        "success": True,
        "token": data,
        "storage": "supabase",
        "expires_in_seconds": data.get("expires_in")
    }


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
        "message": "Token Gazelle sauvegardé dans Supabase",
        "redirect_uri": REDIRECT_URI_DEFAULT,
        "storage": result["storage"],
        "expires_in_seconds": result["expires_in_seconds"]
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

    from datetime import datetime, timedelta, timezone
    today = datetime.now(timezone.utc).date()
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
    # Utilise PORT de l'environnement (Render) ou 8000 par défaut
    port = int(os.getenv('PORT', 8000))
    print(f"🚀 Démarrage Uvicorn sur port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)

