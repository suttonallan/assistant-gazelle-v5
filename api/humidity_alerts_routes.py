"""
Routes API pour les alertes d'humidité institutionnelles
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from apscheduler.schedulers.background import BackgroundScheduler
from core.supabase_storage import SupabaseStorage

router = APIRouter(prefix="/humidity-alerts", tags=["humidity-alerts"])

# Scheduler global
_scheduler = None
JOB_ID = "humidity_alerts_daily_scan"


class ResolveAlertRequest(BaseModel):
    """Requête pour marquer une alerte comme résolue."""
    resolution_notes: Optional[str] = None


@router.get("/institutional", response_model=Dict[str, Any])
async def get_institutional_alerts():
    """
    Récupère les alertes d'humidité pour les clients institutionnels.

    Clients surveillés:
    - Vincent d'Indy
    - Place des Arts
    - Orford

    Returns:
        {
            "alerts": [
                {
                    "alert_type": "housse",
                    "client_name": "Vincent d'Indy",
                    "piano_make": "Steinway",
                    "piano_model": "B",
                    "description": "Housse enlevée détecté",
                    "is_resolved": false,
                    "observed_at": "2026-01-07T10:30:00Z"
                },
                ...
            ],
            "stats": {
                "total": 5,
                "unresolved": 2,
                "resolved": 3
            }
        }
    """
    try:
        storage = SupabaseStorage()

        # Clients institutionnels à surveiller (external_id)
        # ⚠️ IMPORTANT: Utiliser client_id (external_id) PAS client_name !
        # 3 INSTITUTIONS UNIQUEMENT: Vincent-d'Indy, Place des Arts, Orford
        INSTITUTIONAL_CLIENT_IDS = [
            'cli_9UMLkteep8EsISbG',  # École de musique Vincent-d'Indy
            'cli_HbEwl9rN11pSuDEU',  # Place des Arts
            'cli_PmqPUBTbPFeCMGmz',  # Orford Musique
        ]

        # Requête UNIQUE avec IN clause sur client_id
        response = storage.client.table('humidity_alerts_active').select('*').in_('client_id', INSTITUTIONAL_CLIENT_IDS).order('observed_at', desc=True).execute()
        all_alerts = response.data if response.data else []

        # Calculer les statistiques
        total = len(all_alerts)
        unresolved = sum(1 for alert in all_alerts if not alert.get('is_resolved', False))
        resolved = sum(1 for alert in all_alerts if alert.get('is_resolved', False))

        return {
            "alerts": all_alerts,
            "stats": {
                "total": total,
                "unresolved": unresolved,
                "resolved": resolved
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")


@router.get("/all", response_model=Dict[str, Any])
async def get_all_alerts(limit: int = 100, resolved: bool = None):
    """
    Récupère toutes les alertes d'humidité.

    Args:
        limit: Nombre max d'alertes à récupérer (défaut: 100)
        resolved: Filtre par statut résolu (true/false/null pour tous)

    Returns:
        {
            "alerts": [...],
            "count": 45,
            "stats": {
                "total": 45,
                "unresolved": 12,
                "resolved": 33
            }
        }
    """
    try:
        storage = SupabaseStorage()

        # Construire l'URL avec filtres
        url = f"{storage.api_url}/humidity_alerts_active?select=*&order=observed_at.desc&limit={limit}"

        if resolved is not None:
            url += f"&is_resolved=eq.{str(resolved).lower()}"

        headers = storage._get_headers()

        import requests
        response = requests.get(url, headers=headers)

        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Erreur Supabase: {response.text}"
            )

        alerts = response.json()

        # Calculer les statistiques
        total = len(alerts)
        unresolved_count = sum(1 for alert in alerts if not alert.get('is_resolved', False))
        resolved_count = sum(1 for alert in alerts if alert.get('is_resolved', False))

        return {
            "alerts": alerts,
            "count": total,
            "stats": {
                "total": total,
                "unresolved": unresolved_count,
                "resolved": resolved_count
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")


@router.get("/stats", response_model=Dict[str, Any])
async def get_alerts_stats():
    """
    Statistiques globales des alertes d'humidité.

    Returns:
        {
            "total_alerts": 100,
            "unresolved": 15,
            "resolved": 85,
            "by_type": {
                "housse": 40,
                "alimentation": 35,
                "reservoir": 25
            },
            "institutional_unresolved": 3
        }
    """
    try:
        storage = SupabaseStorage()

        # Récupérer toutes les alertes actives
        url = f"{storage.api_url}/humidity_alerts_active?select=*"
        headers = storage._get_headers()

        import requests
        response = requests.get(url, headers=headers)

        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Erreur Supabase: {response.text}"
            )

        all_alerts = response.json()

        # Statistiques globales
        total_alerts = len(all_alerts)
        unresolved = sum(1 for alert in all_alerts if not alert.get('is_resolved', False))
        resolved = sum(1 for alert in all_alerts if alert.get('is_resolved', False))

        # Par type
        by_type = {}
        for alert in all_alerts:
            alert_type = alert.get('alert_type', 'unknown')
            by_type[alert_type] = by_type.get(alert_type, 0) + 1

        # Alertes institutionnelles non résolues
        INSTITUTIONAL_CLIENTS = ['Vincent d\'Indy', 'Place des Arts', 'Orford']
        institutional_unresolved = sum(
            1 for alert in all_alerts
            if alert.get('client_name') in INSTITUTIONAL_CLIENTS
            and not alert.get('is_resolved', False)
        )

        return {
            "total_alerts": total_alerts,
            "unresolved": unresolved,
            "resolved": resolved,
            "by_type": by_type,
            "institutional_unresolved": institutional_unresolved
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")


@router.get("/unresolved", response_model=Dict[str, Any])
async def get_unresolved_alerts(limit: int = 100):
    """
    Récupère les alertes non résolues (Liste 1).

    Args:
        limit: Nombre max d'alertes à récupérer

    Returns:
        {
            "alerts": [...],
            "count": 12
        }
    """
    try:
        storage = SupabaseStorage()

        url = f"{storage.api_url}/humidity_alerts_active?select=*&is_resolved=eq.false&archived=eq.false&order=observed_at.desc&limit={limit}"
        headers = storage._get_headers()

        import requests
        response = requests.get(url, headers=headers)

        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Erreur Supabase: {response.text}"
            )

        alerts = response.json()

        return {
            "alerts": alerts,
            "count": len(alerts)
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")


@router.get("/resolved", response_model=Dict[str, Any])
async def get_resolved_alerts(limit: int = 100):
    """
    Récupère les alertes résolues mais non archivées (Liste 2).

    Args:
        limit: Nombre max d'alertes à récupérer

    Returns:
        {
            "alerts": [...],
            "count": 33
        }
    """
    try:
        storage = SupabaseStorage()

        url = f"{storage.api_url}/humidity_alerts_active?select=*&is_resolved=eq.true&archived=eq.false&order=resolved_at.desc&limit={limit}"
        headers = storage._get_headers()

        import requests
        response = requests.get(url, headers=headers)

        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Erreur Supabase: {response.text}"
            )

        alerts = response.json()

        return {
            "alerts": alerts,
            "count": len(alerts)
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")


@router.get("/archived", response_model=Dict[str, Any])
async def get_archived_alerts(limit: int = 100):
    """
    Récupère les alertes archivées (Liste 3).

    Args:
        limit: Nombre max d'alertes à récupérer

    Returns:
        {
            "alerts": [...],
            "count": 200
        }
    """
    try:
        storage = SupabaseStorage()

        # Note: archived alerts ne sont PAS dans la vue active, on doit query la table directement
        url = f"{storage.api_url}/humidity_alerts?select=*,client_name:gazelle_clients(company_name),piano_make:gazelle_pianos(make),piano_model:gazelle_pianos(model)&archived=eq.true&order=updated_at.desc&limit={limit}"
        headers = storage._get_headers()

        import requests
        response = requests.get(url, headers=headers)

        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Erreur Supabase: {response.text}"
            )

        alerts = response.json()

        return {
            "alerts": alerts,
            "count": len(alerts)
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")


@router.post("/resolve/{alert_id}", response_model=Dict[str, Any])
async def resolve_alert(alert_id: str, request: ResolveAlertRequest):
    """
    Marque une alerte comme résolue.

    Args:
        alert_id: UUID de l'alerte
        request: Notes de résolution (optionnel)

    Returns:
        {"success": true, "id": "..."}
    """
    try:
        storage = SupabaseStorage()

        # Appeler la fonction Postgres
        import requests
        url = f"{storage.api_url}/rpc/resolve_humidity_alert"
        headers = storage._get_headers()
        payload = {
            "alert_id": alert_id,
            "notes": request.resolution_notes
        }

        response = requests.post(url, headers=headers, json=payload)

        if response.status_code not in [200, 204]:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Erreur Supabase: {response.text}"
            )

        return {"success": True, "id": alert_id}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")


@router.post("/archive/{alert_id}", response_model=Dict[str, Any])
async def archive_alert(alert_id: str):
    """
    Archive une alerte (masque de l'interface).

    Args:
        alert_id: UUID de l'alerte

    Returns:
        {"success": true, "id": "..."}
    """
    try:
        storage = SupabaseStorage()

        # Appeler la fonction Postgres
        import requests
        url = f"{storage.api_url}/rpc/archive_humidity_alert"
        headers = storage._get_headers()
        payload = {"alert_id": alert_id}

        response = requests.post(url, headers=headers, json=payload)

        if response.status_code not in [200, 204]:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Erreur Supabase: {response.text}"
            )

        return {"success": True, "id": alert_id}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")


# ---------------------------------------------------------------------------
# Scheduler Automatique
# ---------------------------------------------------------------------------


def _run_daily_scan():
    """
    Job exécuté quotidiennement à 16h pour scanner les nouvelles alertes humidité.
    """
    print("🔍 [Humidity Scanner] Démarrage du scan quotidien automatique...")

    try:
        # Importer le scanner
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent))

        from modules.alerts.humidity_scanner import HumidityAlertScanner

        # Initialiser et exécuter le scan
        scanner = HumidityAlertScanner()
        result = scanner.scan_new_entries(days_back=1)

        print(f"✅ [Humidity Scanner] Scan terminé: {result.get('new_alerts', 0)} nouvelles alertes détectées")

        return result

    except Exception as e:
        print(f"❌ [Humidity Scanner] Erreur lors du scan: {e}")
        import traceback
        traceback.print_exc()
        return {"error": str(e)}


@router.post("/scan")
async def trigger_manual_scan(days_back: int = 7) -> Dict[str, Any]:
    """
    Déclenche un scan manuel des alertes d'humidité.

    Ce endpoint permet de forcer un scan sans attendre le scheduler automatique.
    Utile pour tester ou forcer un scan immédiatement.

    Args:
        days_back: Nombre de jours à scanner en arrière (défaut: 7)

    Returns:
        {
            "status": "success",
            "scanned": 1577,
            "alerts_found": 5,
            "new_alerts": 3,
            "errors": 0,
            "execution_time_seconds": 2.5
        }
    """
    try:
        from modules.alerts.humidity_scanner_safe import HumidityScannerSafe
        import time

        print(f"🚀 [Humidity Alerts] Scan manuel déclenché (days_back={days_back})")
        start_time = time.time()

        scanner = HumidityScannerSafe()
        result = scanner.scan_new_entries(days_back=days_back)

        execution_time = time.time() - start_time

        print(f"✅ [Humidity Alerts] Scan terminé en {execution_time:.2f}s")
        print(f"   Scannées: {result.get('scanned', 0)}")
        print(f"   Alertes trouvées: {result.get('alerts_found', 0)}")
        print(f"   Nouvelles alertes: {result.get('new_alerts', 0)}")

        return {
            "status": "success",
            "scanned": result.get('scanned', 0),
            "alerts_found": result.get('alerts_found', 0),
            "new_alerts": result.get('new_alerts', 0),
            "errors": result.get('errors', 0),
            "execution_time_seconds": round(execution_time, 2),
            "days_back": days_back
        }

    except Exception as e:
        print(f"❌ [Humidity Alerts] Erreur scan manuel: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors du scan: {str(e)}"
        )


@router.on_event("startup")
def start_scheduler():
    """Démarre le scheduler APScheduler pour le scan automatique quotidien."""
    global _scheduler

    try:
        print("📅 [Humidity Alerts] Démarrage du Scheduler...")

        # Initialisation lazy du scheduler
        if _scheduler is None:
            print("   → Création du BackgroundScheduler (timezone=America/Montreal)")
            _scheduler = BackgroundScheduler(timezone="America/Montreal")

        if not _scheduler.running:
            print("   → Démarrage du scheduler en mode pausé")
            _scheduler.start(paused=True)

        # Ajouter le job de scan quotidien à 16h
        if not _scheduler.get_job(JOB_ID):
            print(f"   → Ajout job quotidien {JOB_ID} (16h)")
            _scheduler.add_job(
                _run_daily_scan,
                trigger="cron",
                hour=16,
                minute=0,
                id=JOB_ID,
                replace_existing=True,
            )

        # Reprendre le scheduler s'il est en pause
        if _scheduler.state == 2:  # paused
            print("   → Reprise du scheduler")
            _scheduler.resume()

        print("✅ [Humidity Alerts] Scheduler démarré avec succès")

    except Exception as e:
        print(f"⚠️ [Humidity Alerts] Scheduler non démarré: {e}")
        import traceback
        traceback.print_exc()


@router.on_event("shutdown")
def shutdown_scheduler():
    """Arrête le scheduler APScheduler."""
    try:
        print("🛑 [Humidity Alerts] Arrêt du Scheduler...")
        if _scheduler and _scheduler.running:
            _scheduler.shutdown(wait=False)
            print("✅ [Humidity Alerts] Scheduler arrêté")
    except Exception as e:
        print(f"⚠️ [Humidity Alerts] Erreur arrêt scheduler: {e}")
