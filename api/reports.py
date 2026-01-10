#!/usr/bin/env python3
"""
Endpoints pour générer le rapport Timeline v5 (Google Sheets).
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import APIRouter, HTTPException

from modules.reports.service_reports import ServiceReports

router = APIRouter(prefix="/api/reports", tags=["reports"])

# Scheduler unique pour éviter les doublons au redémarrage
scheduler = None  # Lazy init dans startup
JOB_ID = "reports_timeline_generate"


def _run_job(full_refresh: bool = False) -> dict:
    """Exécute la génération (utilisé par l'endpoint et le scheduler)."""
    service = ServiceReports()

    # since = dernière exécution si append, sinon None (full refresh)
    since: Optional[datetime] = None
    append = not full_refresh
    if append:
        since = service.get_last_run()

    counts = service.generate_reports(since=since, append=append)
    return {"append": append, "counts": counts}


@router.post("/timeline/generate")
async def generate_reports(full_refresh: bool = False) -> dict:
    """
    Déclenche la génération manuelle.
    - full_refresh=False (défaut): append uniquement les nouvelles entrées (depuis last_run)
    - full_refresh=True: nettoie les onglets puis réécrit
    """
    try:
        return _run_job(full_refresh=full_refresh)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.on_event("startup")
def start_scheduler():
    """Démarre la tâche planifiée 02:00 Montréal."""
    global scheduler
    try:
        print("📊 Démarrage du Scheduler reports...")

        # Initialisation lazy du scheduler
        if scheduler is None:
            print("   → Création du BackgroundScheduler (timezone=America/Montreal)")
            scheduler = BackgroundScheduler(timezone="America/Montreal")

        if not scheduler.running:
            print("   → Démarrage du scheduler en mode pausé")
            scheduler.start(paused=True)

        if not scheduler.get_job(JOB_ID):
            print(f"   → Ajout job timeline {JOB_ID} (2h)")
            scheduler.add_job(
                _run_job,
                trigger="cron",
                hour=2,
                minute=0,
                id=JOB_ID,
                kwargs={"full_refresh": False},
                replace_existing=True,
            )

        if scheduler.state == 2:  # 2 = STATE_PAUSED
            print("   → Reprise du scheduler")
            scheduler.resume()

        print("✅ Scheduler reports démarré avec succès")
    except Exception as e:
        print(f"⚠️ Scheduler reports non démarré: {e}")
        import traceback
        traceback.print_exc()


@router.on_event("shutdown")
def shutdown_scheduler():
    """Arrête proprement le scheduler."""
    try:
        print("🛑 Arrêt du Scheduler reports...")
        if scheduler and scheduler.running:
            scheduler.shutdown(wait=False)
            print("✅ Scheduler reports arrêté")
    except Exception as e:
        print(f"⚠️ Erreur arrêt scheduler: {e}")




