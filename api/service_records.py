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
# Calendrier "À attribuer" (non assigné)
# ============================================================
# Certaines institutions ne doivent PAS auto-assigner un technicien lors du
# push : le RV est cree dans le calendrier "poubelle" non utilise, et un humain
# assigne ensuite le vrai technicien dans Gazelle. Ex. Orford (accords collectifs).
# NB: ce user doit rester isSchedulable=True cote Gazelle, sinon createEvent le
# rejette ("Le technicien selectionne ne peut pas etre planifie"). Il avait ete
# desactive par erreur (2026-08-01), remis planifiable manuellement par Allan.
CALENDRIER_NON_ASSIGNE_USER_ID = "usr_naFcjSiNRcnqU5mF"  # "Avis système inutiles Piano"
INSTITUTIONS_PUSH_NON_ASSIGNE = {"orford"}

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
        .is_("closed_at", "null")  # uniquement la fiche active (non figée)
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

    # Chercher une fiche active existante (draft ou completed, pas validated/pushed).
    # closed_at IS NULL → on ne touche jamais une fiche figée (« Nouveau service »).
    existing = (
        sb.table(TABLE)
        .select("id,status")
        .eq("piano_id", piano_id)
        .eq("institution_slug", institution)
        .in_("status", ["draft", "completed"])
        .is_("closed_at", "null")
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

    # Trouver la fiche active (non figée)
    existing = (
        sb.table(TABLE)
        .select("id,status")
        .eq("piano_id", piano_id)
        .eq("institution_slug", institution)
        .in_("status", ["draft", "completed"])
        .is_("closed_at", "null")
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


@router.post("/{institution}/piano/{piano_id}/close-and-new")
async def close_and_start_new(
    institution: str = PathParam(...),
    piano_id: str = PathParam(...),
    body: ServiceRecordComplete = ServiceRecordComplete()
):
    """
    Fige la fiche active du piano et libère la place pour une NOUVELLE fiche.

    Permet de consigner plusieurs services distincts le même jour sans devoir
    passer par la validation de Nicolas entre les deux.

    La fiche courante passe à 'completed' + closed_at = maintenant : elle suit
    le cycle normal (validation → push) mais sort du périmètre d'unicité, donc
    la prochaine sauvegarde de notes crée automatiquement une fiche vierge.
    """
    sb = _get_supabase()
    now = datetime.utcnow().isoformat()

    # Fiche active éditable (non figée)
    existing = (
        sb.table(TABLE)
        .select("id,status,travail,completed_at")
        .eq("piano_id", piano_id)
        .eq("institution_slug", institution)
        .in_("status", ["draft", "completed"])
        .is_("closed_at", "null")
        .limit(1)
        .execute()
    )

    if not existing.data:
        raise HTTPException(status_code=404, detail="Aucune fiche active pour ce piano")

    record = existing.data[0]
    record_id = record["id"]

    # Refuser de figer une fiche vide (rien à consigner)
    if not (record.get("travail") or "").strip():
        raise HTTPException(status_code=400, detail="Fiche vide — rien à figer")

    sb.table(TABLE).update({
        "status": "completed",
        "completed_at": record.get("completed_at") or now,
        "completed_by": body.completed_by or "",
        "closed_at": now,
        "updated_at": now,
    }).eq("id", record_id).execute()

    logging.info(f"Fiche {record_id} figée (close-and-new) — piano {piano_id} / {institution}")

    return {
        "success": True,
        "closed_record_id": record_id,
        "action": "closed",
        "message": "Service figé — nouvelle fiche disponible"
    }


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

    # Le gestionnaire peut valider des fiches draft OU completed
    query = (
        sb.table(TABLE)
        .select("id,piano_id")
        .eq("institution_slug", institution)
        .in_("status", ["draft", "completed"])
    )

    if body.piano_ids:
        query = query.in_("piano_id", body.piano_ids)

    to_validate = query.execute()

    if not to_validate.data:
        return {"success": True, "validated_count": 0, "message": "Aucune fiche à valider"}

    record_ids = [r["id"] for r in to_validate.data]

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
    from core.timezone_utils import MONTREAL_TZ, utc_to_montreal
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

    now_iso = datetime.utcnow().isoformat()

    # Date de service d'une fiche : completed_at (moment « Terminé »), sinon
    # started_at, sinon created_at — jamais la date du push.
    def _service_dt(r):
        """Instant du service, ramené en heure de Montréal (datetime aware).

        Les horodatages Supabase sont en UTC. Les manipuler en UTC pour dater un
        service décale le travail du soir d'un jour entier — tout ce qui est fait
        après 20 h à Montréal est déjà le lendemain en UTC.
        """
        raw = r.get("completed_at") or r.get("started_at") or r.get("created_at")
        if not raw:
            return None
        try:
            return utc_to_montreal(raw)
        except Exception:
            return None

    def _service_day(r):
        """Jour CALENDAIRE MONTRÉALAIS du service.

        ⚠️ Ne JAMAIS revenir à `raw[:10]` : ça tranche la date UTC. Cas réel
        (2026-08-19) : un accord fait le 5 août à 14 h 01 est ressorti dans Gazelle
        daté du 6 août à 00 h 02. Convention imposée par CLAUDE.md — toujours
        convertir en America/Montreal avant comparaison ou affichage.
        """
        d = _service_dt(r)
        return d.date().isoformat() if d else None

    # Regrouper les fiches par JOUR de service : UN événement par jour, daté de
    # son vrai jour. Les services du 31 juillet restent au 31 juillet même s'ils
    # sont poussés le 1er août. Le regroupement par jour (et non par fiche) garde
    # l'accord collectif d'une même journée en un seul RV.
    from collections import defaultdict
    groups = defaultdict(list)
    for r in records:
        groups[_service_day(r)].append(r)

    # Mode skip : marquer pushed sans écrire dans Gazelle
    if body.skip_gazelle:
        for record in records:
            sb.table(TABLE).update({
                "status": "pushed",
                "pushed_at": now_iso,
                "gazelle_event_id": "SKIPPED",
                "updated_at": now_iso,
            }).eq("id", record["id"]).execute()

        # Nettoyer overlays (même en mode skip)
        try:
            from core.supabase_storage import SupabaseStorage
            storage = SupabaseStorage(silent=True)
            for pid in piano_ids:
                storage.update_piano(pid, {
                    "travail": "",
                    "service_status": None,
                    "is_work_completed": False,
                }, institution_slug=institution)
            logging.info(f"🧹 Overlays nettoyés (skip) pour {len(piano_ids)} piano(s)")
        except Exception as e:
            logging.warning(f"⚠️ Nettoyage overlays skip: {e}")

        return {
            "success": True,
            "pushed_count": len(records),
            "skip_gazelle": True,
            "message": f"{len(records)} fiche(s) marquée(s) pushed (Gazelle ignoré)"
        }

    # 3. Push réel vers Gazelle — un événement par jour de service
    try:
        from core.gazelle_api_client import GazelleAPIClient
        from api.institutions import get_institution_config

        api_client = GazelleAPIClient()
        config = get_institution_config(institution)
        client_id = config.get("gazelle_client_id")

        # Calendrier cible : calendrier non assigné pour les institutions
        # concernées (ex. Orford), sinon le technicien fourni.
        push_user_id = (
            CALENDRIER_NON_ASSIGNE_USER_ID
            if institution.strip().lower() in INSTITUTIONS_PUSH_NON_ASSIGNE
            else body.technician_id
        )

        create_mutation = """
        mutation CreateBundleEvent($input: PrivateEventInput!) {
            createEvent(input: $input) {
                event { id title start type status }
                mutationErrors { fieldName messages }
            }
        }
        """
        complete_mutation = """
        mutation CompleteBundleEvent($eventId: String!, $input: PrivateCompleteEventInput!) {
            completeEvent(eventId: $eventId, input: $input) {
                event { id status }
                mutationErrors { fieldName messages }
            }
        }
        """

        logging.info(f"Push lot: {len(records)} fiches, {len(groups)} jour(s) ({institution})")

        created_events = []
        pushed_total = 0
        pushed_piano_ids = set()
        errors = []

        # Un événement par jour : chaque groupe garde sa vraie date de service.
        for day, group in sorted(groups.items(), key=lambda kv: kv[0] or ""):
            group_piano_ids = list({r["piano_id"] for r in group})
            # _service_dt rend des datetimes AWARE en heure de Montréal : le max
            # compare donc des instants réels, et l'ISO produit porte le décalage
            # explicite (-04:00 / -05:00). Gazelle n'a plus à deviner le fuseau.
            group_dts = [d for r in group if (d := _service_dt(r))]
            event_dt = max(group_dts) if group_dts else datetime.now(MONTREAL_TZ)
            event_date = event_dt.isoformat()

            try:
                # Activer pianos INACTIVE -> ACTIVE
                activated = []
                for pid in group_piano_ids:
                    try:
                        sr = api_client._execute_query(
                            'query($id:String!){piano(id:$id){id status}}', {"id": pid}
                        )
                        if sr.get("data", {}).get("piano", {}).get("status") == "INACTIVE":
                            api_client._execute_query(
                                'mutation($id:String!,$input:PrivatePianoInput!){updatePiano(id:$id,input:$input){piano{id status}}}',
                                {"id": pid, "input": {"status": "ACTIVE"}}
                            )
                            activated.append(pid)
                    except Exception as e:
                        logging.warning(f"Activation {pid}: {e}")

                # Notes par fiche
                combined_lines = []
                service_notes = []
                for record in group:
                    pid = record["piano_id"]
                    # ⚠️ Le « à faire » N'EST JAMAIS POUSSÉ DANS GAZELLE (décision
                    # d'Allan, 2026-08-19). C'est une note de relais interne, laissée
                    # à l'intention du PROCHAIN technicien. Gazelle est l'historique du
                    # travail EFFECTUÉ, vu par le client. Voir le commentaire détaillé
                    # dans core/gazelle_push_service.py (_build_service_note).
                    parts = []
                    if record.get("travail"):
                        parts.append(record["travail"])
                    if record.get("observations"):
                        parts.append(f"Observations: {record['observations']}")
                    note_text = "\n".join(parts) if parts else "Service effectue"
                    combined_lines.append(f"{pid}: {note_text}")
                    service_notes.append({"pianoId": pid, "notes": note_text})

                event_input = {
                    "title": f"Accord collectif ({len(group_piano_ids)} pianos)",
                    "start": event_date,
                    "duration": 60 * len(group_piano_ids),
                    "type": "APPOINTMENT",
                    "notes": "\n".join(combined_lines),
                    "pianos": [{"pianoId": pid, "isTuning": True} for pid in group_piano_ids],
                    "userId": push_user_id,
                }
                if client_id:
                    event_input["clientId"] = client_id

                create_result = api_client._execute_query(create_mutation, {"input": event_input})
                event = create_result.get("data", {}).get("createEvent", {}).get("event")
                if not event:
                    errs = create_result.get("data", {}).get("createEvent", {}).get("mutationErrors", [])
                    raise Exception(f"Erreur createEvent: {errs}")
                event_id = event["id"]

                # Compléter avec notes par piano
                api_client._execute_query(complete_mutation, {
                    "eventId": event_id,
                    "input": {"resultType": "COMPLETE", "serviceHistoryNotes": service_notes}
                })

                # Remettre pianos INACTIVE
                for pid in activated:
                    try:
                        api_client._execute_query(
                            'mutation($id:String!,$input:PrivatePianoInput!){updatePiano(id:$id,input:$input){piano{id status}}}',
                            {"id": pid, "input": {"status": "INACTIVE"}}
                        )
                    except Exception as e:
                        logging.warning(f"Desactivation {pid}: {e}")

                # Marquer les fiches de CE jour comme pushed
                for record in group:
                    sb.table(TABLE).update({
                        "status": "pushed",
                        "pushed_at": now_iso,
                        "gazelle_event_id": event_id,
                        "updated_at": now_iso,
                    }).eq("id", record["id"]).execute()

                pushed_total += len(group)
                pushed_piano_ids.update(group_piano_ids)
                created_events.append({
                    "event_id": event_id, "event_date": event_date, "day": day,
                    "pianos": len(group_piano_ids), "fiches": len(group),
                })
                logging.info(f"Evenement cree {event_id} (jour {day}, date {event_date}, {len(group)} fiche(s))")

            except Exception as ge:
                # Erreur sur CE jour : marquer seulement ce groupe en erreur,
                # continuer avec les autres jours (les jours déjà poussés restent poussés).
                msg = str(ge)
                for record in group:
                    sb.table(TABLE).update({
                        "status": "error",
                        "push_error": msg,
                        "updated_at": now_iso,
                    }).eq("id", record["id"]).execute()
                errors.append({"day": day, "error": msg})
                logging.error(f"Erreur push jour {day} ({institution}): {ge}")

        # Nettoyer les overlays legacy des pianos effectivement poussés
        # NOTE: a_faire n'est PAS vidé — Nicolas le vide manuellement.
        try:
            from core.supabase_storage import SupabaseStorage
            storage = SupabaseStorage(silent=True)
            for pid in pushed_piano_ids:
                storage.update_piano(pid, {
                    "travail": "",
                    "service_status": None,
                    "is_work_completed": False,
                }, institution_slug=institution)
        except Exception as e:
            logging.warning(f"Nettoyage overlays apres push: {e}")

        # Si rien n'est passé et il y a des erreurs -> échec dur
        if pushed_total == 0 and errors:
            raise HTTPException(status_code=500, detail=f"Erreur push: {errors}")

        msg = f"{pushed_total} fiche(s) poussee(s) dans {len(created_events)} evenement(s) (1 par jour)"
        if errors:
            msg += f" — {len(errors)} jour(s) en erreur"
        logging.info(f"Push lot termine: {msg}")

        return {
            "success": True,
            "pushed_count": pushed_total,
            "events": created_events,
            "errors": errors,
            "gazelle_event_id": created_events[0]["event_id"] if created_events else None,
            "message": msg,
        }

    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        logging.error(f"Erreur push lot {institution}: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Erreur push: {error_msg}")


# ============================================================
# HISTORIQUE — Fiches poussées
# ============================================================

@router.get("/{institution}/history")
async def get_push_history(
    institution: str = PathParam(...),
    limit: int = Query(200, description="Nombre max de fiches")
):
    """
    Historique unifié : fiches poussées (piano_service_records)
    + entrées legacy (vdi_service_history).
    Triées par date décroissante.
    """
    sb = _get_supabase()

    # 1. Nouveau système : piano_service_records pushed
    new_resp = (
        sb.table(TABLE)
        .select("*")
        .eq("institution_slug", institution)
        .eq("status", "pushed")
        .order("pushed_at", desc=True)
        .limit(limit)
        .execute()
    )
    new_records = new_resp.data or []

    # 2. Ancien système : vdi_service_history (validated + pushed)
    legacy_records = []
    try:
        legacy_resp = (
            sb.table("vdi_service_history")
            .select("*")
            .eq("institution_slug", institution)
            .in_("status", ["validated", "pushed"])
            .order("validated_at", desc=True)
            .limit(limit)
            .execute()
        )
        # Convertir au format piano_service_records pour le frontend
        for rec in (legacy_resp.data or []):
            legacy_records.append({
                "id": rec.get("id"),
                "piano_id": rec.get("piano_id"),
                "institution_slug": rec.get("institution_slug"),
                "piano_local": rec.get("piano_local", ""),
                "piano_name": rec.get("piano_name", ""),
                "status": rec.get("status", "pushed"),
                "travail": rec.get("travail", ""),
                "a_faire": rec.get("a_faire", ""),
                "observations": rec.get("observations", ""),
                "completed_at": rec.get("service_date") or rec.get("validated_at"),
                "validated_at": rec.get("validated_at"),
                "validated_by": rec.get("validated_by"),
                "pushed_at": rec.get("pushed_at"),
                "gazelle_event_id": rec.get("gazelle_event_id"),
                "source": "legacy",
            })
    except Exception as e:
        logging.warning(f"⚠️ Chargement historique legacy: {e}")

    # 3. Dédoublonner par piano_id + date (éviter doublons si migré)
    seen = set()
    merged = []
    for rec in new_records:
        key = f"{rec.get('piano_id')}_{rec.get('pushed_at', '')[:10]}"
        if key not in seen:
            seen.add(key)
            merged.append(rec)
    for rec in legacy_records:
        key = f"{rec.get('piano_id')}_{(rec.get('pushed_at') or rec.get('validated_at', ''))[:10]}"
        if key not in seen:
            seen.add(key)
            merged.append(rec)

    # 4. Trier par date décroissante
    def sort_key(r):
        return r.get("pushed_at") or r.get("validated_at") or r.get("completed_at") or ""
    merged.sort(key=sort_key, reverse=True)

    return {
        "records": merged[:limit],
        "count": len(merged[:limit])
    }


@router.patch("/{institution}/record/{record_id}/soft-delete")
async def soft_delete_record(
    institution: str = PathParam(...),
    record_id: str = PathParam(...)
):
    """
    Marque une fiche comme 'deleted' (soft delete).
    Le filtre du GET /api/{inst}/pianos exclut déjà 'deleted',
    donc la fiche disparaît du dashboard sans perdre l'historique en DB.
    Permet à un admin (Allan/Nicolas) de retirer une note avant qu'elle
    soit poussée vers Gazelle.
    """
    sb = _get_supabase()
    now_iso = datetime.utcnow().isoformat() + "+00:00"

    existing = (
        sb.table(TABLE)
        .select("id,status,institution_slug")
        .eq("id", record_id)
        .eq("institution_slug", institution)
        .limit(1)
        .execute()
    )
    if not existing.data:
        raise HTTPException(status_code=404, detail="Fiche non trouvée")

    current_status = existing.data[0].get("status")
    if current_status == "pushed":
        raise HTTPException(
            status_code=400,
            detail="Impossible de supprimer une fiche déjà poussée vers Gazelle"
        )

    sb.table(TABLE).update({
        "status": "deleted",
        "updated_at": now_iso,
    }).eq("id", record_id).execute()

    return {"success": True, "record_id": record_id, "previous_status": current_status}


@router.patch("/{institution}/record/{record_id}/clear-a-faire")
async def clear_a_faire(
    institution: str = PathParam(...),
    record_id: str = PathParam(...)
):
    """
    Efface le champ a_faire d'une fiche de service (y compris les fiches poussées).
    Permet à Nicolas de nettoyer ses notes après le push.
    """
    sb = _get_supabase()

    # Vérifier que la fiche existe et appartient à cette institution
    existing = (
        sb.table(TABLE)
        .select("id,institution_slug,piano_id")
        .eq("id", record_id)
        .eq("institution_slug", institution)
        .limit(1)
        .execute()
    )

    if not existing.data:
        # Essayer dans vdi_service_history (legacy)
        try:
            legacy = (
                sb.table("vdi_service_history")
                .select("id,institution_slug")
                .eq("id", record_id)
                .eq("institution_slug", institution)
                .limit(1)
                .execute()
            )
            if legacy.data:
                sb.table("vdi_service_history").update({"a_faire": ""}).eq("id", record_id).execute()
                return {"success": True, "source": "legacy"}
        except Exception:
            pass
        raise HTTPException(status_code=404, detail="Fiche non trouvée")

    sb.table(TABLE).update({"a_faire": ""}).eq("id", record_id).execute()

    # Sync bidirectionnelle : vider aussi a_faire dans l'overlay
    try:
        piano_id = existing.data[0].get("piano_id")
        if piano_id:
            from core.supabase_storage import SupabaseStorage
            storage = SupabaseStorage(silent=True)
            storage.update_piano(piano_id, {"a_faire": ""}, institution_slug=institution)
    except Exception as e:
        logging.warning(f"Sync a_faire vers overlay échouée: {e}")

    return {"success": True, "source": "piano_service_records"}


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
