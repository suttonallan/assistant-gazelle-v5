#!/usr/bin/env python3
"""
API pour les fiches de service (piano_service_records).

Cycle de vie : draft → completed → validated → pushed
Une seule fiche active par piano/institution à la fois.

Remplace la fragmentation entre:
  - vincent_dindy_piano_updates.travail
  - vdi_service_history
  - vdi_notes_buffer
"""

import logging
import os
from datetime import datetime
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, HTTPException, Query, Path as PathParam
from pydantic import BaseModel

router = APIRouter(prefix="/service-records", tags=["service-records"])

# ============================================================
# Helpers Supabase
# ============================================================

_supabase = None

def _get_supabase():
    global _supabase
    if _supabase is None:
        from supabase import create_client
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        if not url or not key:
            raise HTTPException(status_code=500, detail="Configuration Supabase manquante")
        _supabase = create_client(url, key)
    return _supabase


TABLE = "piano_service_records"


# ============================================================
# Pydantic models
# ============================================================

class ServiceRecordUpdate(BaseModel):
    """Mise à jour partielle d'une fiche de service."""
    travail: Optional[str] = None
    observations: Optional[str] = None
    technician_email: Optional[str] = None


class ServiceRecordComplete(BaseModel):
    """Marquer une fiche comme terminée."""
    completed_by: Optional[str] = None


class ServiceRecordValidate(BaseModel):
    """Valider une fiche (Nicolas)."""
    validated_by: Optional[str] = None
    piano_ids: Optional[List[str]] = None  # Pour validation en lot


# ============================================================
# CRUD Endpoints
# ============================================================

@router.get("/{institution}/active")
async def get_active_records(
    institution: str = PathParam(..., description="Institution slug"),
    status_filter: Optional[str] = Query(None, description="Filtrer par status (draft,completed,validated)")
):
    """
    Récupère toutes les fiches actives (non pushées) pour une institution.
    Utilisé par la vue technicien et la vue gestionnaire.
    """
    sb = _get_supabase()

    query = sb.table(TABLE).select("*").eq("institution_slug", institution)

    if status_filter:
        statuses = [s.strip() for s in status_filter.split(",")]
        query = query.in_("status", statuses)
    else:
        # Par défaut : tout sauf pushed
        query = query.in_("status", ["draft", "completed", "validated"])

    query = query.order("updated_at", desc=True)
    response = query.execute()

    # Indexer par piano_id pour accès rapide côté frontend
    records_by_piano = {}
    for record in (response.data or []):
        pid = record["piano_id"]
        # Garder la fiche la plus récente par piano (normalement une seule active)
        if pid not in records_by_piano:
            records_by_piano[pid] = record

    return {
        "records": response.data or [],
        "by_piano": records_by_piano,
        "count": len(response.data or [])
    }


@router.get("/{institution}/piano/{piano_id}")
async def get_piano_active_record(
    institution: str = PathParam(...),
    piano_id: str = PathParam(...)
):
    """Récupère la fiche active d'un piano (draft ou completed)."""
    sb = _get_supabase()

    response = (
        sb.table(TABLE)
        .select("*")
        .eq("piano_id", piano_id)
        .eq("institution_slug", institution)
        .in_("status", ["draft", "completed", "validated"])
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )

    record = response.data[0] if response.data else None
    return {"record": record}


@router.get("/{institution}/piano/{piano_id}/last-pushed")
async def get_last_pushed_record(
    institution: str = PathParam(...),
    piano_id: str = PathParam(...)
):
    """
    Récupère la dernière fiche poussée d'un piano.
    Utilisé pour afficher 'Dernier' = completed_at de la dernière visite.
    """
    sb = _get_supabase()

    response = (
        sb.table(TABLE)
        .select("id,completed_at,pushed_at,completed_by,technician_email,travail")
        .eq("piano_id", piano_id)
        .eq("institution_slug", institution)
        .eq("status", "pushed")
        .order("completed_at", desc=True)
        .limit(1)
        .execute()
    )

    record = response.data[0] if response.data else None
    return {"record": record}


@router.put("/{institution}/piano/{piano_id}/notes")
async def upsert_service_notes(
    institution: str = PathParam(...),
    piano_id: str = PathParam(...),
    body: ServiceRecordUpdate = ServiceRecordUpdate()
):
    """
    Crée ou met à jour la fiche de service d'un piano.
    Auto-save du technicien — crée un draft si aucune fiche active n'existe.
    """
    sb = _get_supabase()
    now = datetime.utcnow().isoformat()

    # Chercher une fiche active existante (draft ou completed, pas validated/pushed)
    existing = (
        sb.table(TABLE)
        .select("id,status")
        .eq("piano_id", piano_id)
        .eq("institution_slug", institution)
        .in_("status", ["draft", "completed"])
        .limit(1)
        .execute()
    )

    update_data = {}
    if body.travail is not None:
        update_data["travail"] = body.travail
    if body.observations is not None:
        update_data["observations"] = body.observations
    if body.technician_email:
        update_data["technician_email"] = body.technician_email

    if existing.data:
        # Mettre à jour la fiche existante
        record_id = existing.data[0]["id"]
        update_data["updated_at"] = now

        # Si c'était completed et qu'on modifie le contenu, revenir à draft
        if existing.data[0]["status"] == "completed":
            update_data["status"] = "draft"

        sb.table(TABLE).update(update_data).eq("id", record_id).execute()

        return {"success": True, "record_id": record_id, "action": "updated"}
    else:
        # Créer une nouvelle fiche draft
        # Copier a_faire depuis l'overlay si disponible
        a_faire = ""
        try:
            from core.supabase_storage import SupabaseStorage
            storage = SupabaseStorage(silent=True)
            overlay = storage.get_piano_updates(piano_id)
            if overlay:
                a_faire = overlay.get("a_faire", "") or ""
        except Exception:
            pass

        # Nettoyer le champ travail de l'overlay legacy pour éviter qu'il réapparaisse
        try:
            storage.update_piano(piano_id, {"travail": ""}, institution_slug=institution)
        except Exception:
            pass

        new_record = {
            "piano_id": piano_id,
            "institution_slug": institution,
            "status": "draft",
            "travail": body.travail or "",
            "observations": body.observations or "",
            "a_faire": a_faire,
            "technician_email": body.technician_email or "",
            "started_at": now,
            "created_at": now,
            "updated_at": now,
        }

        result = sb.table(TABLE).insert(new_record).execute()
        record_id = result.data[0]["id"] if result.data else None

        return {"success": True, "record_id": record_id, "action": "created"}


@router.post("/{institution}/piano/{piano_id}/complete")
async def complete_service_record(
    institution: str = PathParam(...),
    piano_id: str = PathParam(...),
    body: ServiceRecordComplete = ServiceRecordComplete()
):
    """
    Marquer la fiche d'un piano comme terminée (technicien clique Terminé).
    """
    sb = _get_supabase()
    now = datetime.utcnow().isoformat()

    # Trouver la fiche active
    existing = (
        sb.table(TABLE)
        .select("id,status")
        .eq("piano_id", piano_id)
        .eq("institution_slug", institution)
        .in_("status", ["draft", "completed"])
        .limit(1)
        .execute()
    )

    if not existing.data:
        raise HTTPException(status_code=404, detail="Aucune fiche active pour ce piano")

    record = existing.data[0]
    record_id = record["id"]

    # Toggle : si déjà completed, revenir à draft
    if record["status"] == "completed":
        sb.table(TABLE).update({
            "status": "draft",
            "completed_at": None,
            "completed_by": None,
            "updated_at": now,
        }).eq("id", record_id).execute()

        return {"success": True, "record_id": record_id, "status": "draft", "action": "reopened"}

    # Marquer comme completed
    sb.table(TABLE).update({
        "status": "completed",
        "completed_at": now,
        "completed_by": body.completed_by or "",
        "updated_at": now,
    }).eq("id", record_id).execute()

    return {"success": True, "record_id": record_id, "status": "completed", "action": "completed"}


@router.post("/{institution}/validate")
async def validate_service_records(
    institution: str = PathParam(...),
    body: ServiceRecordValidate = ServiceRecordValidate()
):
    """
    Nicolas valide des fiches (par lot ou toutes les completed).
    """
    sb = _get_supabase()
    now = datetime.utcnow().isoformat()

    query = (
        sb.table(TABLE)
        .select("id,piano_id")
        .eq("institution_slug", institution)
        .eq("status", "completed")
    )

    if body.piano_ids:
        query = query.in_("piano_id", body.piano_ids)

    completed = query.execute()

    if not completed.data:
        return {"success": True, "validated_count": 0, "message": "Aucune fiche à valider"}

    record_ids = [r["id"] for r in completed.data]

    # Valider toutes les fiches en lot
    for rid in record_ids:
        sb.table(TABLE).update({
            "status": "validated",
            "validated_at": now,
            "validated_by": body.validated_by or "",
            "updated_at": now,
        }).eq("id", rid).execute()

    logging.info(f"✅ {len(record_ids)} fiches validées pour {institution}")

    return {
        "success": True,
        "validated_count": len(record_ids),
        "record_ids": record_ids
    }


# ============================================================
# PUSH EN LOT VERS GAZELLE — Point d'entrée UNIQUE
# ============================================================

class PushRequest(BaseModel):
    """Requête de push en lot vers Gazelle."""
    technician_id: str = "usr_HcCiFk7o0vZ9xAI0"  # Nick par défaut
    dry_run: bool = False
    skip_gazelle: bool = False


@router.post("/{institution}/push")
async def push_validated_to_gazelle(
    institution: str = PathParam(...),
    body: PushRequest = PushRequest()
):
    """
    Push en lot de toutes les fiches validées vers Gazelle.
    Crée UN SEUL rendez-vous avec tous les pianos.
    La date de service = completed_at le plus récent du lot.

    Après push réussi : les fiches passent à 'pushed', les pianos sont
    immédiatement disponibles pour de nouvelles fiches.
    """
    from core.timezone_utils import MONTREAL_TZ
    from collections import defaultdict

    sb = _get_supabase()

    # 1. Récupérer toutes les fiches validées
    validated = (
        sb.table(TABLE)
        .select("*")
        .eq("institution_slug", institution)
        .eq("status", "validated")
        .order("completed_at", desc=True)
        .execute()
    )

    records = validated.data or []
    if not records:
        return {"success": True, "pushed_count": 0, "message": "Aucune fiche validée à pousser"}

    piano_ids = list(set(r["piano_id"] for r in records))

    if body.dry_run:
        return {
            "success": True,
            "dry_run": True,
            "would_push": len(records),
            "pianos_count": len(piano_ids),
            "pianos": [{"piano_id": r["piano_id"], "travail": (r.get("travail") or "")[:50]} for r in records]
        }

    # 2. Déterminer la date de service = completed_at le plus récent
    completed_dates = [r["completed_at"] for r in records if r.get("completed_at")]
    if completed_dates:
        # Trier et prendre le plus récent
        event_date = max(completed_dates)
    else:
        event_date = datetime.now(MONTREAL_TZ).isoformat()

    now_iso = datetime.utcnow().isoformat()

    # Mode skip : marquer pushed sans écrire dans Gazelle
    if body.skip_gazelle:
        for record in records:
            sb.table(TABLE).update({
                "status": "pushed",
                "pushed_at": now_iso,
                "gazelle_event_id": "SKIPPED",
                "updated_at": now_iso,
            }).eq("id", record["id"]).execute()

        return {
            "success": True,
            "pushed_count": len(records),
            "skip_gazelle": True,
            "message": f"{len(records)} fiche(s) marquée(s) pushed (Gazelle ignoré)"
        }

    # 3. Push réel vers Gazelle
    try:
        from core.gazelle_api_client import GazelleAPIClient
        from api.institutions import get_institution_config

        api_client = GazelleAPIClient()
        config = get_institution_config(institution)
        client_id = config.get("gazelle_client_id")

        logging.info(f"🎹 Push lot: {len(records)} fiches pour {len(piano_ids)} pianos ({institution})")

        # 3a. Activer pianos INACTIVE → ACTIVE
        activated = []
        for pid in piano_ids:
            try:
                sr = api_client._execute_query(
                    'query($id:String!){piano(id:$id){id status}}',
                    {"id": pid}
                )
                if sr.get("data", {}).get("piano", {}).get("status") == "INACTIVE":
                    api_client._execute_query(
                        'mutation($id:String!,$input:PrivatePianoInput!){updatePiano(id:$id,input:$input){piano{id status}}}',
                        {"id": pid, "input": {"status": "ACTIVE"}}
                    )
                    activated.append(pid)
            except Exception as e:
                logging.warning(f"⚠️ Activation {pid}: {e}")

        # 3b. Construire les notes combinées
        combined_lines = []
        service_notes = []
        for record in records:
            pid = record["piano_id"]
            parts = []
            if record.get("a_faire"):
                parts.append(f"📋 {record['a_faire']}")
            if record.get("travail"):
                parts.append(f"🔧 {record['travail']}")
            if record.get("observations"):
                parts.append(f"📝 {record['observations']}")
            note_text = "\n".join(parts) if parts else "Service effectué"
            combined_lines.append(f"🎹 {pid}: {note_text}")
            service_notes.append({"pianoId": pid, "notes": note_text})

        # 3c. Créer UN SEUL événement multi-pianos avec date = completed_at
        create_mutation = """
        mutation CreateBundleEvent($input: PrivateEventInput!) {
            createEvent(input: $input) {
                event { id title start type status }
                mutationErrors { fieldName messages }
            }
        }
        """
        event_input = {
            "title": f"Accord collectif ({len(piano_ids)} pianos)",
            "start": event_date,
            "duration": 60 * len(piano_ids),
            "type": "APPOINTMENT",
            "notes": "\n".join(combined_lines),
            "pianos": [{"pianoId": pid, "isTuning": True} for pid in piano_ids],
            "userId": body.technician_id,
        }
        if client_id:
            event_input["clientId"] = client_id

        create_result = api_client._execute_query(create_mutation, {"input": event_input})
        event = create_result.get("data", {}).get("createEvent", {}).get("event")
        if not event:
            errors = create_result.get("data", {}).get("createEvent", {}).get("mutationErrors", [])
            raise Exception(f"Erreur createEvent: {errors}")

        event_id = event["id"]
        logging.info(f"✅ Événement créé: {event_id} (date: {event_date})")

        # 3d. Compléter avec notes par piano
        complete_mutation = """
        mutation CompleteBundleEvent($eventId: String!, $input: PrivateCompleteEventInput!) {
            completeEvent(eventId: $eventId, input: $input) {
                event { id status }
                mutationErrors { fieldName messages }
            }
        }
        """
        api_client._execute_query(complete_mutation, {
            "eventId": event_id,
            "input": {"resultType": "COMPLETE", "serviceHistoryNotes": service_notes}
        })

        # 3e. Remettre pianos INACTIVE
        for pid in activated:
            try:
                api_client._execute_query(
                    'mutation($id:String!,$input:PrivatePianoInput!){updatePiano(id:$id,input:$input){piano{id status}}}',
                    {"id": pid, "input": {"status": "INACTIVE"}}
                )
            except Exception as e:
                logging.warning(f"⚠️ Désactivation {pid}: {e}")

        # 4. Marquer toutes les fiches comme pushed
        for record in records:
            sb.table(TABLE).update({
                "status": "pushed",
                "pushed_at": now_iso,
                "gazelle_event_id": event_id,
                "updated_at": now_iso,
            }).eq("id", record["id"]).execute()

        # 5. Nettoyer les overlays legacy (travail, service_status)
        # NOTE: a_faire n'est PAS vidé — Nicolas le vide manuellement quand il estime que c'est fait
        try:
            from core.supabase_storage import SupabaseStorage
            storage = SupabaseStorage(silent=True)
            for pid in piano_ids:
                storage.update_piano(pid, {
                    "travail": "",
                    "service_status": None,
                    "is_work_completed": False,
                }, institution_slug=institution)
            logging.info(f"🧹 Overlays nettoyés pour {len(piano_ids)} piano(s) après push")
        except Exception as e:
            logging.warning(f"⚠️ Nettoyage overlays après push: {e}")

        logging.info(f"✅ Push lot terminé: {len(records)} fiches, event {event_id}")

        return {
            "success": True,
            "pushed_count": len(records),
            "pianos_count": len(piano_ids),
            "gazelle_event_id": event_id,
            "event_date": event_date,
            "message": f"{len(records)} fiche(s) poussée(s) → événement {event_id}"
        }

    except HTTPException:
        raise
    except Exception as e:
        # Marquer les fiches en erreur
        error_msg = str(e)
        for record in records:
            sb.table(TABLE).update({
                "status": "error",
                "push_error": error_msg,
                "updated_at": now_iso,
            }).eq("id", record["id"]).execute()

        logging.error(f"❌ Erreur push lot {institution}: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Erreur push: {error_msg}")


# ============================================================
# HISTORIQUE — Fiches poussées
# ============================================================

@router.get("/{institution}/history")
async def get_push_history(
    institution: str = PathParam(...),
    limit: int = Query(50, description="Nombre max de fiches")
):
    """Historique des fiches poussées vers Gazelle."""
    sb = _get_supabase()

    response = (
        sb.table(TABLE)
        .select("*")
        .eq("institution_slug", institution)
        .eq("status", "pushed")
        .order("pushed_at", desc=True)
        .limit(limit)
        .execute()
    )

    return {
        "records": response.data or [],
        "count": len(response.data or [])
    }


# ============================================================
# STATS — Pour le rappel Nicolas
# ============================================================

@router.get("/{institution}/pending-validation")
async def get_pending_validation(
    institution: str = PathParam(...)
):
    """
    Compte les fiches en attente de validation.
    Utilisé pour le rappel email à Nicolas.
    """
    sb = _get_supabase()

    completed = (
        sb.table(TABLE)
        .select("id,piano_id,completed_at,completed_by,technician_email")
        .eq("institution_slug", institution)
        .eq("status", "completed")
        .order("completed_at", desc=True)
        .execute()
    )

    return {
        "pending_count": len(completed.data or []),
        "records": completed.data or []
    }
