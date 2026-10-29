#!/usr/bin/env python3
"""
Routes API pour le Scheduler et le Journal des Tâches.

Endpoints:
- GET /scheduler/logs: Récupérer les logs récents
- POST /scheduler/run/{task_name}: Exécuter une tâche manuellement
"""

import sys
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
import threading

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.scheduler_logger import get_logger

router = APIRouter(prefix="/scheduler", tags=["scheduler"])


# ============================================================
# MODÈLES PYDANTIC
# ============================================================

class SchedulerLog(BaseModel):
    """Modèle pour un log de tâche planifiée."""
    id: str
    task_name: str
    task_label: str
    started_at: str
    completed_at: Optional[str]
    duration_seconds: Optional[int]
    status: str  # 'success', 'error', 'running'
    message: Optional[str]
    stats: Dict[str, Any]
    triggered_by: str
    triggered_by_user: Optional[str]
    created_at: str


class RunTaskRequest(BaseModel):
    """Requête pour exécuter une tâche manuellement."""
    user_email: Optional[str] = None


class RunTaskResponse(BaseModel):
    """Réponse après exécution d'une tâche."""
    success: bool
    message: str
    task_name: str
    started_at: str


# ============================================================
# ENDPOINTS
# ============================================================

@router.get("/logs", response_model=List[SchedulerLog])
async def get_logs(limit: int = 20):
    """
    Récupère les logs récents des tâches planifiées.

    Args:
        limit: Nombre de logs à récupérer (défaut: 20)

    Returns:
        Liste des logs récents
    """
    try:
        logger = get_logger()
        logs = logger.get_recent_logs(limit=limit)

        # Convertir les logs en modèles Pydantic
        return [SchedulerLog(**log) for log in logs]

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la récupération des logs: {str(e)}"
        )


@router.post("/run/sync", response_model=RunTaskResponse)
async def run_sync_gazelle(request: RunTaskRequest):
    """
    Exécute la tâche de synchronisation Gazelle manuellement.

    Returns:
        Confirmation de démarrage de la tâche
    """
    try:
        from core.scheduler import task_sync_gazelle_totale

        # Exécuter dans un thread séparé pour ne pas bloquer l'API
        def run_task():
            task_sync_gazelle_totale(
                triggered_by='manual',
                user_email=request.user_email
            )

        thread = threading.Thread(target=run_task, daemon=True)
        thread.start()

        return RunTaskResponse(
            success=True,
            message="Synchronisation Gazelle démarrée en arrière-plan",
            task_name="sync_gazelle",
            started_at=datetime.now().isoformat()
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors du démarrage de la synchronisation: {str(e)}"
        )


@router.post("/run/rapport", response_model=RunTaskResponse)
async def run_rapport_timeline(request: RunTaskRequest):
    """
    Exécute la tâche de génération du rapport Timeline manuellement.

    Returns:
        Confirmation de démarrage de la tâche
    """
    try:
        from core.scheduler import task_generate_rapport_timeline

        # Exécuter dans un thread séparé
        def run_task():
            task_generate_rapport_timeline(
                triggered_by='manual',
                user_email=request.user_email
            )

        thread = threading.Thread(target=run_task, daemon=True)
        thread.start()

        return RunTaskResponse(
            success=True,
            message="Génération du rapport Timeline démarrée en arrière-plan",
            task_name="rapport_timeline",
            started_at=datetime.now().isoformat()
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors du démarrage du rapport: {str(e)}"
        )


@router.post("/run/backup", response_model=RunTaskResponse)
async def run_backup(request: RunTaskRequest):
    """
    Exécute la tâche de backup de la base de données manuellement.

    Returns:
        Confirmation de démarrage de la tâche
    """
    try:
        from core.scheduler import task_backup_database

        # Exécuter dans un thread séparé
        def run_task():
            task_backup_database(
                triggered_by='manual',
                user_email=request.user_email
            )

        thread = threading.Thread(target=run_task, daemon=True)
        thread.start()

        return RunTaskResponse(
            success=True,
            message="Backup de la base de données démarré en arrière-plan",
            task_name="backup",
            started_at=datetime.now().isoformat()
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors du démarrage du backup: {str(e)}"
        )


@router.post("/run/alerts", response_model=RunTaskResponse)
async def run_rv_alerts(request: RunTaskRequest):
    """
    Exécute la tâche de synchronisation RV et alertes manuellement.

    Returns:
        Confirmation de démarrage de la tâche
    """
    try:
        from core.scheduler import task_sync_rv_and_alerts

        # Exécuter dans un thread séparé
        def run_task():
            task_sync_rv_and_alerts(
                triggered_by='manual',
                user_email=request.user_email
            )

        thread = threading.Thread(target=run_task, daemon=True)
        thread.start()

        return RunTaskResponse(
            success=True,
            message="Synchronisation RV & Alertes démarrée en arrière-plan",
            task_name="rv_alerts",
            started_at=datetime.now().isoformat()
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors du démarrage des alertes: {str(e)}"
        )


@router.post("/run/messages-rv")
async def run_messages_rv():
    """Vérifie tout de suite les messages Front ouverts contre les RV Gazelle."""
    from modules.alerts.messages_rv_existant import verifier_messages
    try:
        return {"success": True, "stats": verifier_messages()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur messages/RV : {e}")


@router.get("/diag/zoom-file-messagerie")
async def diag_zoom_file_messagerie():
    """TEMPORAIRE (lecture seule) : réglages de la file d'appels 804 et avis
    courriel de messagerie de ses membres, pour savoir qui reçoit les avis."""
    import requests as rq
    from core.zoom_sms import get_zoom_access_token
    base = "https://api.zoom.us/v2"
    h = {"Authorization": f"Bearer {get_zoom_access_token()}"}
    def g(c):
        r = rq.get(base + c, headers=h, timeout=20)
        return r.status_code, (r.json() if r.text else {})
    out = {}
    code, files = g("/phone/call_queues?page_size=100")
    out["files"] = [{k: f.get(k) for k in ("id", "name", "extension_number")}
                    for f in (files.get("call_queues") or [])] or {"code": code, "rep": files}
    for f in files.get("call_queues") or []:
        if str(f.get("extension_number")) != "804":
            continue
        code, d = g(f"/phone/call_queues/{f['id']}")
        out["file_804"] = {"code": code, "policy": d.get("policy"), "cles": list(d.keys())}
        code, m = g(f"/phone/call_queues/{f['id']}/members?page_size=100")
        out["membres"] = []
        for u in (m.get("call_queue_members") or []):
            info = {"nom": (u.get("name") or "").split(" ")[0], "niveau": u.get("level"), "type": u.get("type")}
            if u.get("id") and u.get("level") == "user" or u.get("type") == "user":
                c2, st = g(f"/phone/users/{u['id']}/settings")
                info["settings_code"] = c2
                info["voicemail"] = {k: v for k, v in (st or {}).items() if "voice" in k.lower() or "notif" in k.lower()}
            out["membres"].append(info)
    return out


@router.post("/run/factures-doublons")
async def run_factures_doublons(envoyer: bool = False):
    """Cherche les factures en double. Par défaut, affiche seulement (n'envoie rien)."""
    from modules.alerts.factures_doublons import verifier_doublons
    try:
        return {"success": True, "stats": verifier_doublons(envoyer=envoyer)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur factures en double : {e}")


# ============================================================
# IMPORTS INDIVIDUELS GAZELLE
# ============================================================

@router.post("/run/import/{import_type}", response_model=RunTaskResponse)
async def run_import(import_type: str, request: RunTaskRequest):
    """
    Exécute un import Gazelle spécifique manuellement.

    Args:
        import_type: Type d'import ('clients', 'contacts', 'pianos', 'timeline', 'appointments')
        request: Requête avec email utilisateur

    Returns:
        Confirmation de démarrage de l'import
    """
    valid_imports = ['clients', 'contacts', 'pianos', 'timeline', 'appointments']

    if import_type not in valid_imports:
        raise HTTPException(
            status_code=400,
            detail=f"Type d'import invalide. Valeurs autorisées: {', '.join(valid_imports)}"
        )

    try:
        from modules.sync_gazelle.sync_to_supabase import GazelleToSupabaseSync
        from core.scheduler_logger import get_logger

        # Mapper le type d'import vers le label et la méthode
        import_config = {
            'clients': {
                'label': 'Import Clients',
                'method': 'sync_clients',
                'icon': '👥'
            },
            'contacts': {
                'label': 'Import Contacts',
                'method': 'sync_contacts',
                'icon': '📇'
            },
            'pianos': {
                'label': 'Import Pianos',
                'method': 'sync_pianos',
                'icon': '🎹'
            },
            'timeline': {
                'label': 'Import Timeline',
                'method': 'sync_timeline',
                'icon': '📅'
            },
            'appointments': {
                'label': 'Import Rendez-vous',
                'method': 'sync_appointments',
                'icon': '📆'
            }
        }

        config = import_config[import_type]

        # Exécuter dans un thread séparé
        def run_task():
            logger = get_logger()
            log_id = logger.start_task(
                task_name=f'import_{import_type}',
                task_label=config['label'],
                triggered_by='manual',
                triggered_by_user=request.user_email
            )

            try:
                print(f"\n{'='*70}")
                print(f"{config['icon']} {config['label'].upper()} - Démarrage")
                print(f"   Heure: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"   Utilisateur: {request.user_email or 'Système'}")
                print(f"{'='*70}")

                syncer = GazelleToSupabaseSync()
                method = getattr(syncer, config['method'])
                count = method()

                print(f"\n✅ {config['label']} terminé: {count} items synchronisés")
                print(f"{'='*70}\n")

                logger.complete_task(
                    log_id=log_id,
                    status='success',
                    message=f'{count} items synchronisés',
                    stats={import_type: count}
                )

            except Exception as e:
                print(f"\n❌ Erreur lors de {config['label']}: {e}")
                import traceback
                traceback.print_exc()

                logger.complete_task(
                    log_id=log_id,
                    status='error',
                    message=str(e)
                )

        thread = threading.Thread(target=run_task, daemon=True)
        thread.start()

        return RunTaskResponse(
            success=True,
            message=f"{config['label']} démarré en arrière-plan",
            task_name=f"import_{import_type}",
            started_at=datetime.now().isoformat()
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors du démarrage de l'import: {str(e)}"
        )
