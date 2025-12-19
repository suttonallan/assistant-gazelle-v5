"""
Routes FastAPI - Place des Arts (stub migration V5).

Objectif : préparer l'import CSV sans écrire de données tant que
la logique V4 n'est pas portée.
"""

import sys
from pathlib import Path
from typing import List, Literal, Optional, Dict, Any
import requests
from datetime import datetime

from fastapi import APIRouter, UploadFile, File, HTTPException, Query, Response
from starlette.responses import StreamingResponse
from pydantic import BaseModel

# Ajouter le parent au path pour les imports locaux
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.supabase_storage import SupabaseStorage  # noqa: E402
from modules.place_des_arts.services.event_parser import EventParser  # noqa: E402
from modules.place_des_arts.services.event_manager import EventManager  # noqa: E402
from modules.place_des_arts.services.email_parser import parse_email_text  # noqa: E402

router = APIRouter(prefix="/place-des-arts", tags=["place-des-arts"])

# Singletons légers
_storage = None
_parser = None
_manager = None


def get_storage() -> SupabaseStorage:
    global _storage
    if _storage is None:
        _storage = SupabaseStorage()
    return _storage


def get_parser() -> EventParser:
    global _parser
    if _parser is None:
        _parser = EventParser()
    return _parser


def get_manager() -> EventManager:
    global _manager
    if _manager is None:
        _manager = EventManager(get_storage())
    return _manager


class ImportCSVResponse(BaseModel):
    dry_run: bool
    received: int
    inserted: int
    updated: int
    errors: List[str]
    message: str


class UpdateCellRequest(BaseModel):
    request_id: str
    field: str
    value: Any


class StatusBatchRequest(BaseModel):
    request_ids: List[str]
    status: str
    billed_by: Optional[str] = None


class DeleteRequest(BaseModel):
    request_ids: List[str]


class PreviewRequest(BaseModel):
    """Stub pour prévisualisation import email/texte."""
    raw_text: Optional[str] = None
    source: Optional[str] = None  # ex: "email"


class ImportRequest(BaseModel):
    """Stub pour import email/texte."""
    raw_text: str
    source: Optional[str] = None  # ex: "email"


@router.get("/health")
async def health_check():
    """Health check minimal du module Place des Arts."""
    return {"status": "ok", "module": "place-des-arts"}


@router.get("/requests")
async def list_requests(
    status: Optional[str] = Query(default=None),
    month: Optional[str] = Query(default=None, description="Format AAAA-MM"),
    technician_id: Optional[str] = Query(default=None),
    room: Optional[str] = Query(default=None),
    limit: int = Query(default=200, le=500),
):
    """
    Liste des demandes Place des Arts (limité à 500).
    Filtres simples: status, month (AAAA-MM), technician_id, room.
    """
    storage = get_storage()
    params = ["select=*"]
    if status:
        params.append(f"status=eq.{status}")
    if technician_id:
        params.append(f"technician_id=eq.{technician_id}")
    if room:
        params.append(f"room=eq.{room}")
    if month:
        params.append(f"appointment_date=gte.{month}-01")
        params.append(f"appointment_date=lt.{month}-32")
    params.append("order=appointment_date.desc")
    params.append(f"limit={limit}")

    url = f"{storage.api_url}/place_des_arts_requests?{'&'.join(params)}"
    resp = requests.get(url, headers=storage._get_headers())
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    return resp.json()


@router.get("/export")
async def export_csv():
    """
    Export CSV simple (toutes les demandes, limit 2000, tri date desc).
    """
    storage = get_storage()
    params = [
        "select=*",
        "order=appointment_date.desc",
        "limit=2000",
        "format=csv"
    ]
    url = f"{storage.api_url}/place_des_arts_requests?{'&'.join(params)}"
    hdrs = storage._get_headers().copy()
    hdrs["Accept"] = "text/csv"
    resp = requests.get(url, headers=hdrs, stream=True)
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    return StreamingResponse(resp.iter_content(chunk_size=8192),
                             media_type="text/csv",
                             headers={"Content-Disposition": "attachment; filename=place_des_arts.csv"})


@router.get("/stats")
async def stats():
    manager = get_manager()
    try:
        return manager.get_stats()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/requests/update-cell")
async def update_cell(payload: UpdateCellRequest):
    manager = get_manager()
    result = manager.update_cell(payload.request_id, payload.field, payload.value)
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error", "Erreur update"))
    return result


@router.post("/requests/update-status-batch")
async def update_status_batch(payload: StatusBatchRequest):
    manager = get_manager()
    result = manager.update_status_batch(payload.request_ids, payload.status, payload.billed_by)
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error", "Erreur batch status"))
    return result


@router.post("/requests/bill")
async def bill_requests(payload: StatusBatchRequest):
    manager = get_manager()
    result = manager.bill_requests(payload.request_ids, payload.billed_by or "system")
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error", "Erreur facturation"))
    return result


@router.post("/requests/delete")
async def delete_requests(payload: DeleteRequest):
    manager = get_manager()
    result = manager.delete_requests(payload.request_ids)
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error", "Erreur suppression"))
    return result


@router.post("/requests/delete-duplicates")
async def delete_duplicates():
    manager = get_manager()
    result = manager.delete_duplicates()
    if not result.get("ok", True):
        raise HTTPException(status_code=400, detail=result.get("error", "Erreur doublons"))
    return result


# ------------------------------------------------------------
# Stubs preview/import email + sync + diagnostic
# ------------------------------------------------------------

@router.post("/preview")
async def preview_email(payload: PreviewRequest):
    """
    Prévisualisation import email (parsing texte, sans écriture).
    """
    if not payload.raw_text:
        raise HTTPException(status_code=400, detail="raw_text requis")
    parsed = parse_email_text(payload.raw_text)
    # Map vers format normalisé (mais sans id)
    preview = []
    for idx, item in enumerate(parsed, start=1):
        row = {
            "appointment_date": item.get("date").isoformat() if isinstance(item.get("date"), (str, type(None))) is False else item.get("date"),
            "room": item.get("room"),
            "for_who": item.get("for_who"),
            "diapason": item.get("diapason"),
            "requester": item.get("requester"),
            "piano": item.get("piano"),
            "time": item.get("time"),
            "service": item.get("service"),
            "notes": item.get("notes"),
            "confidence": item.get("confidence"),
            "warnings": item.get("warnings"),
        }
        preview.append(row)
    return {"success": True, "preview": preview, "count": len(preview)}


@router.post("/import")
async def import_email(payload: ImportRequest):
    """
    Import email/texte : parse, normalise, UPSERT.
    """
    if not payload.raw_text:
        raise HTTPException(status_code=400, detail="raw_text requis")
    parsed = parse_email_text(payload.raw_text)
    if not parsed:
        return {"success": True, "imported": 0, "warnings": ["Aucune demande détectée"]}

    storage = get_storage()

    def exists_duplicate(row: Dict[str, Any]) -> bool:
        # Critère V4 : même date, salle, pour qui, heure
        params = [
            f"appointment_date=eq.{row.get('appointment_date')}",
            f"room=eq.{row.get('room') or ''}",
            f"for_who=eq.{row.get('for_who') or ''}",
            f"time=eq.{row.get('time') or ''}",
            "select=id",
            "limit=1"
        ]
        url = f"{storage.api_url}/place_des_arts_requests?{'&'.join(params)}"
        resp = requests.get(url, headers=storage._get_headers())
        return resp.status_code == 200 and resp.json()

    rows = []
    duplicates = []
    today_iso = datetime.utcnow().date().isoformat()
    for idx, item in enumerate(parsed, start=1):
        appointment_date = item.get("date")
        if isinstance(appointment_date, datetime):
            appointment_date = appointment_date.date().isoformat()
        elif not appointment_date:
            continue  # saute si pas de date

        row = {
            "id": f"pda_email_{idx:04d}_{int(datetime.utcnow().timestamp())}",
            "request_date": today_iso,
            "appointment_date": appointment_date,
            "room": item.get("room") or "",
            "room_original": item.get("room"),
            "for_who": item.get("for_who") or "",
            "diapason": item.get("diapason") or "",
            "requester": item.get("requester") or "",
            "piano": item.get("piano") or "",
            "time": item.get("time") or "",
            "technician_id": None,
            "status": "PENDING",
            "original_raw_text": payload.raw_text,
            "notes": item.get("notes") or "",
        }
        if exists_duplicate(row):
            duplicates.append(row)
        else:
            rows.append(row)

    if not rows:
        return {
            "success": True,
            "imported": 0,
            "warnings": ["Aucune ligne exploitable (dates manquantes ou doublons existants)"],
            "duplicates": duplicates
        }

    manager = get_manager()
    result = manager.import_csv(rows, on_conflict="update")
    if result.get("errors"):
        raise HTTPException(status_code=400, detail=result["errors"])
    return {
        "success": True,
        "imported": result.get("inserted", 0),
        "message": result.get("message", ""),
        "duplicates_skipped": len(duplicates),
        "duplicates": duplicates
    }


@router.post("/sync-manual")
async def sync_manual():
    """
    Synchronisation manuelle (stub).
    """
    return {"success": True, "message": "Sync manuelle non implémentée (stub)."}


@router.get("/diagnostic")
async def diagnostic():
    """
    Diagnostic rapide (stub).
    """
    return {"success": True, "message": "Diagnostic non implémenté (stub)."}


@router.post("/requests/import-csv", response_model=ImportCSVResponse)
async def import_requests_csv(
    file: UploadFile = File(...),
    dry_run: bool = True,
    on_conflict: Literal["ignore", "update"] = "update"
):
    """
    Stub d'import CSV Place des Arts.

    - Ne réalise aucune écriture tant que la migration n'est pas finalisée.
    - Vérifie simplement le format et retourne un accusé.
    """
    if file.content_type not in {"text/csv", "application/vnd.ms-excel", "application/csv"}:
        raise HTTPException(status_code=400, detail="Format CSV attendu (text/csv).")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Fichier CSV vide.")

    parser = get_parser()
    manager = get_manager()

    try:
        rows = parser.parse_csv_bytes(content)
    except Exception as exc:  # pragma: no cover - stub
        raise HTTPException(status_code=400, detail=f"CSV invalide: {exc}") from exc

    if dry_run:
        result = manager.import_csv_preview(rows)
    else:
        result = manager.import_csv(rows, on_conflict=on_conflict)

    return ImportCSVResponse(
        dry_run=dry_run,
        received=result.get("received", len(rows)),
        inserted=result.get("inserted", 0),
        updated=result.get("updated", 0),
        errors=result.get("errors", []),
        message=result.get("message", "Stub: aucune écriture tant que la migration n'est pas finalisée.")
    )
