"""
Gestionnaire Place des Arts.

Implémentation minimale pour importer un CSV dans Supabase.
"""

from __future__ import annotations

from datetime import datetime, date, timezone
from typing import List, Dict, Any, Tuple
import requests

# Statuts autorisés
ALLOWED_STATUS = {"PENDING", "CREATED_IN_GAZELLE", "ASSIGN_OK", "COMPLETED", "BILLED"}


MONTHS_FR = {
    "janvier": 1,
    "février": 2,
    "fevrier": 2,
    "mars": 3,
    "avril": 4,
    "mai": 5,
    "juin": 6,
    "juillet": 7,
    "août": 8,
    "aout": 8,
    "septembre": 9,
    "octobre": 10,
    "novembre": 11,
    "décembre": 12,
    "decembre": 12,
}


def _parse_french_date(value: str) -> str | None:
    if not value:
        return None
    parts = value.strip().split()
    if not parts:
        return None
    try:
        day = int(parts[0])
    except ValueError:
        return None
    month_name = (parts[1] if len(parts) > 1 else "").lower()
    month = MONTHS_FR.get(month_name)
    if not month:
        return None
    today = date.today()
    year = today.year
    candidate = date(year, month, day)
    if candidate < today:
        candidate = date(year + 1, month, day)
    return candidate.isoformat()


def _parse_datetime(value: str) -> str | None:
    """Essaie de parser une date/heure et renvoie en ISO 8601 ou None."""
    if not value:
        return None
    value = value.strip()

    # Dates FR type "5 décembre"
    fr = _parse_french_date(value)
    if fr:
        return fr
    fmt_candidates = [
        "%Y-%m-%d",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f",
    ]
    for fmt in fmt_candidates:
        try:
            return datetime.strptime(value, fmt).isoformat()
        except ValueError:
            continue
    # Laisser tel quel : Supabase tentera de parser, sinon erreur côté API
    return value


def _parse_decimal(value: str) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except ValueError:
        return None


class EventManager:
    """
    Logique Place des Arts (Supabase REST).
    """

    def __init__(self, storage):
        self.storage = storage

    # ------------------------------------------------------------
    # Validation / Normalisation
    # ------------------------------------------------------------
    def _normalize_row(self, row: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
        errors: List[str] = []

        def require(field: str):
            if not row.get(field):
                errors.append(f"champ requis manquant: {field}")

        require("id")
        require("request_date")
        require("appointment_date")
        require("room")
        # piano est optionnel (peut être vide si "à suivre")

        status = (row.get("status") or "PENDING").strip().upper()
        if status not in ALLOWED_STATUS:
            errors.append(f"status invalide: {status}")

        # Montant par défaut si vide
        billing = _parse_decimal(row.get("billing_amount"))
        if billing is None:
            billing = 175.0

        normalized = {
            "id": row.get("id"),
            "request_date": _parse_datetime(row.get("request_date", "")),
            "appointment_date": _parse_datetime(row.get("appointment_date", "")),
            "room": row.get("room"),
            "room_original": row.get("room_original") or None,
            "for_who": row.get("for_who") or "",
            "diapason": row.get("diapason") or "",
            "requester": row.get("requester") or None,
            "piano": row.get("piano"),
            "time": row.get("time") or "",
            "technician_id": row.get("technician_id") or None,
            "appointment_id": row.get("appointment_id") or None,
            "invoice_id": row.get("invoice_id") or None,
            "billing_amount": billing,
            "service_account": row.get("service_account") or None,
            "parking": row.get("parking") or None,
            "status": status,
            "service_history_id": row.get("service_history_id") or None,
            "billed_at": _parse_datetime(row.get("billed_at", "")),
            "billed_by": row.get("billed_by") or None,
            "original_raw_text": row.get("original_raw_text") or None,
            "notes": row.get("notes") or None,
            "created_at": _parse_datetime(row.get("created_at", "")),
            "updated_at": _parse_datetime(row.get("updated_at", "")),
            "created_by": row.get("created_by") or None,
        }
        return normalized, errors

    # ------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------
    def import_csv_preview(self, rows: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Valide sans écrire."""
        errors: List[str] = []
        normalized_rows: List[Dict[str, Any]] = []
        for idx, row in enumerate(rows, start=1):
            nrow, errs = self._normalize_row(row)
            if errs:
                errors.append(f"ligne {idx}: " + "; ".join(errs))
            normalized_rows.append(nrow)

        return {
            "dry_run": True,
            "received": len(rows),
            "inserted": 0,
            "updated": 0,
            "errors": errors,
            "message": "Validation uniquement (dry_run)."
        }

    def import_csv(self, rows: List[Dict[str, Any]], on_conflict: str = "update") -> Dict[str, Any]:
        """
        Import CSV avec UPSERT Supabase (REST).

        on_conflict: "update" (merge) ou "ignore".
        """
        errors: List[str] = []
        normalized_rows: List[Dict[str, Any]] = []

        for idx, row in enumerate(rows, start=1):
            nrow, errs = self._normalize_row(row)
            if errs:
                errors.append(f"ligne {idx}: " + "; ".join(errs))
            normalized_rows.append(nrow)

        if errors:
            return {
                "dry_run": False,
                "received": len(rows),
                "inserted": 0,
                "updated": 0,
                "errors": errors,
                "message": "Erreurs de validation, aucune écriture."
            }

        # Prépare l'UPSERT batch
        headers = self.storage._get_headers().copy()
        prefer_parts = []
        if on_conflict == "ignore":
            prefer_parts.append("resolution=ignore-duplicates")
        else:
            prefer_parts.append("resolution=merge-duplicates")
        prefer_parts.append("return=representation")
        headers["Prefer"] = ",".join(prefer_parts)

        url = f"{self.storage.api_url}/place_des_arts_requests"
        resp = requests.post(url, headers=headers, json=normalized_rows)

        if resp.status_code not in (200, 201):
            return {
                "dry_run": False,
                "received": len(rows),
                "inserted": 0,
                "updated": 0,
                "errors": [f"Supabase {resp.status_code}: {resp.text}"],
                "message": "Échec de l'UPSERT."
            }

        # Supabase renvoie les lignes écrites ; difficile de distinguer insert/update, on renvoie le total.
        written = len(resp.json()) if resp.content else len(normalized_rows)
        return {
            "dry_run": False,
            "received": len(rows),
            "inserted": written,
            "updated": 0,
            "errors": [],
            "message": f"UPSERT réussi ({written} lignes)."
        }

    # ------------------------------------------------------------
    # Lecture avec filtres / stats
    # ------------------------------------------------------------
    def get_requests(self, status: str | None = None, month: str | None = None,
                     technician_id: str | None = None, room: str | None = None,
                     limit: int = 200) -> List[Dict[str, Any]]:
        """
        Récupère les demandes avec filtres simples.
        Tri: appointment_date DESC.
        """
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
        params.append(f"limit={min(limit, 500)}")

        url = f"{self.storage.api_url}/place_des_arts_requests?{'&'.join(params)}"
        resp = requests.get(url, headers=self.storage._get_headers())
        if resp.status_code != 200:
            raise RuntimeError(f"Supabase {resp.status_code}: {resp.text}")
        return resp.json() or []

    def get_stats(self) -> Dict[str, int]:
        """
        Statistiques principales :
        - imported: status IN (PENDING, imported)
        - to_bill: status = COMPLETED and billed_at is null
        - this_month: appointment_date in current month
        """
        from datetime import datetime
        
        hdrs = self.storage._get_headers()
        base = f"{self.storage.api_url}/place_des_arts_requests"

        def count(q: str) -> int:
            r = requests.get(f"{base}?select=id&{q}", headers=hdrs)
            if r.status_code != 200:
                return 0
            if "content-range" in r.headers:
                range_value = r.headers.get("content-range", "0/0").split("/")[-1]
                return 0 if range_value == '*' else int(range_value)
            data = r.json()
            return len(data) if isinstance(data, list) else 0

        imported = count("status=in.(PENDING,imported)")
        to_bill = count("status=eq.COMPLETED&billed_at=is.null")
        
        # Calculer le premier et dernier jour du mois actuel (format ISO pour PostgREST)
        now = datetime.now()
        first_day = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if now.month == 12:
            last_day = now.replace(year=now.year + 1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        else:
            last_day = now.replace(month=now.month + 1, day=1, hour=0, minute=0, second=0, microsecond=0)
        
        this_month = count(f"appointment_date=gte.{first_day.isoformat()}&appointment_date=lt.{last_day.isoformat()}")

        return {"imported": imported, "to_bill": to_bill, "this_month": this_month}

    # ------------------------------------------------------------
    # Updates
    # ------------------------------------------------------------
    def update_cell(self, request_id: str, field: str, value: Any) -> Dict[str, Any]:
        """
        Mise à jour champ ciblé.
        """
        field_map = {
            "request_date": "request_date",
            "date": "appointment_date",
            "appointment_date": "appointment_date",
            "room": "room",
            "for_who": "for_who",
            "diapason": "diapason",
            "requester": "requester",
            "piano": "piano",
            "time": "time",
            "tech": "technician_id",
            "technician_id": "technician_id",
            "notes": "notes",
            "billing_amount": "billing_amount",
            "parking": "parking",
            "status": "status",
        }
        db_field = field_map.get(field)
        if not db_field:
            return {"ok": False, "error": f"Champ non supporté: {field}"}

        payload = {"updated_at": datetime.now(timezone.utc).isoformat()}
        if db_field in ("request_date", "appointment_date", "billed_at"):
            payload[db_field] = _parse_datetime(str(value))
        elif db_field == "billing_amount":
            payload[db_field] = _parse_decimal(str(value)) or 0
        else:
            payload[db_field] = value

        url = f"{self.storage.api_url}/place_des_arts_requests?id=eq.{request_id}"
        hdrs = self.storage._get_headers().copy()
        hdrs["Prefer"] = "return=representation"
        resp = requests.patch(url, headers=hdrs, json=payload)
        if resp.status_code not in (200, 204):
            return {"ok": False, "error": resp.text}
        return {"ok": True, "data": resp.json() if resp.content else {}}

    def update_status_batch(self, request_ids: List[str], status: str, billed_by: str | None = None) -> Dict[str, Any]:
        """
        Batch update status (and billed_at/billed_by if BILLED).
        """
        if status not in ALLOWED_STATUS:
            return {"ok": False, "error": f"status invalide: {status}"}
        payload = {
            "status": status,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        if status == "BILLED":
            payload["billed_at"] = datetime.now(timezone.utc).isoformat()
            payload["billed_by"] = billed_by or "system"

        hdrs = self.storage._get_headers().copy()
        hdrs["Prefer"] = "return=representation"
        # Pour PostgREST/Supabase, les IDs bigint doivent être sans guillemets dans le filtre in
        ids_str = ','.join(str(id) for id in request_ids)
        url = f"{self.storage.api_url}/place_des_arts_requests?id=in.({ids_str})"

        print(f"🔧 update_status_batch: {len(request_ids)} IDs → status={status}")
        print(f"   URL: {url}")
        print(f"   Payload: {payload}")

        resp = requests.patch(url, headers=hdrs, json=payload)
        if resp.status_code not in (200, 204):
            print(f"   ❌ Erreur: {resp.status_code} - {resp.text}")
            return {"ok": False, "error": resp.text}

        data = resp.json() if resp.content else []
        updated_count = len(data) if isinstance(data, list) else 0
        print(f"   ✓ Mis à jour: {updated_count} enregistrement(s)")

        return {"ok": True, "count": updated_count}

    def delete_requests(self, request_ids: List[str]) -> Dict[str, Any]:
        """
        Supprime les demandes par IDs.
        """
        hdrs = self.storage._get_headers()
        url = f"{self.storage.api_url}/place_des_arts_requests?id=in.({','.join(request_ids)})"
        resp = requests.delete(url, headers=hdrs)
        if resp.status_code not in (200, 204):
            return {"ok": False, "error": resp.text}
        return {"ok": True}

    def bill_requests(self, request_ids: List[str], billed_by: str) -> Dict[str, Any]:
        """
        Marque comme facturé (status BILLED) uniquement si status actuel COMPLETED.
        """
        hdrs = self.storage._get_headers().copy()
        hdrs["Prefer"] = "return=representation"
        url = f"{self.storage.api_url}/place_des_arts_requests?status=eq.COMPLETED&id=in.({','.join(request_ids)})"
        payload = {
            "status": "BILLED",
            "billed_at": datetime.now(timezone.utc).isoformat(),
            "billed_by": billed_by,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        resp = requests.patch(url, headers=hdrs, json=payload)
        if resp.status_code not in (200, 204):
            return {"ok": False, "error": resp.text}
        data = resp.json() if resp.content else []
        return {"ok": True, "count": len(data) if isinstance(data, list) else 0}

    def find_duplicates(self) -> List[Dict[str, Any]]:
        """
        Trouve les doublons (critères V4) : même appointment_date, room, for_who, time.
        Retourne la liste des enregistrements qui seraient supprimés (les IDs les plus grands).
        """
        all_rows = self.get_requests(limit=5000)
        to_delete_ids: List[str] = []
        seen = {}
        row_map = {row["id"]: row for row in all_rows}

        for row in all_rows:
            key = (
                (row.get("appointment_date") or "")[:10],
                row.get("room") or "",
                row.get("for_who") or "",
                row.get("time") or "",
            )
            existing = seen.get(key)
            if existing:
                # garder le plus petit id
                keep = min(existing, row["id"])
                drop = row["id"] if keep == existing else existing
                seen[key] = keep
                to_delete_ids.append(drop)
            else:
                seen[key] = row["id"]

        # Retourner les détails complets des doublons
        duplicates = [row_map[id] for id in to_delete_ids if id in row_map]
        return duplicates

    def delete_duplicates(self) -> Dict[str, Any]:
        """
        Supprime doublons (critères V4) : même appointment_date, room, for_who, time.
        On garde l'id le plus petit (on supprime les autres).
        """
        # Approche : récupérer, grouper côté Python, supprimer via REST
        all_rows = self.get_requests(limit=5000)
        to_delete: List[str] = []
        seen = {}
        for row in all_rows:
            key = (
                (row.get("appointment_date") or "")[:10],
                row.get("room") or "",
                row.get("for_who") or "",
                row.get("time") or "",
            )
            existing = seen.get(key)
            if existing:
                # garder le plus petit id
                keep = min(existing, row["id"])
                drop = row["id"] if keep == existing else existing
                seen[key] = keep
                to_delete.append(drop)
            else:
                seen[key] = row["id"]
        if not to_delete:
            return {"ok": True, "deleted": 0}
        return {**self.delete_requests(to_delete), "deleted": len(to_delete)}
