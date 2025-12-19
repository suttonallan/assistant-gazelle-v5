"""
Parser CSV Place des Arts.

Objectif : lire un CSV V4 et produire des dicts normalisés pour Supabase.
Les colonnes attendues correspondent au schéma V4 (voir handoff).
"""

from __future__ import annotations

import csv
from io import StringIO
from typing import List, Dict, Any, Optional
from datetime import datetime, date


class EventParser:
    """
    Parsing CSV pour Place des Arts.
    """

    # Mapping colonnes (case-insensitive) -> clés supabase
    COLUMN_MAP = {
        "id": "id",
        "requestdate": "request_date",
        "appointmentdate": "appointment_date",
        "datedelademande": "request_date",
        "datedurdv": "appointment_date",
        "room": "room",
        "salle": "room",
        "roomoriginal": "room_original",
        "forwho": "for_who",
        "pourqui": "for_who",
        "diapason": "diapason",
        "diapason": "diapason",
        "requester": "requester",
        "demandeur": "requester",
        "piano": "piano",
        "time": "time",
        "heure": "time",
        "technicianid": "technician_id",
        "quilefait": "technician_id",
        "appointmentid": "appointment_id",
        "invoiceid": "invoice_id",
        "billingamount": "billing_amount",
        "facturation(175$)": "billing_amount",
        "serviceaccount": "service_account",
        "parking": "parking",
        "status": "status",
        "servicehistoryid": "service_history_id",
        "billedat": "billed_at",
        "billedby": "billed_by",
        "originalrawtext": "original_raw_text",
        "notes": "notes",
        "createdat": "created_at",
        "updatedat": "updated_at",
        "createdby": "created_by",
    }

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

    def _parse_french_date(self, value: str) -> Optional[str]:
        """
        Convertit '5 décembre' en ISO (YYYY-MM-DD) en supposant l'année courante,
        et +1 an si la date est déjà passée.
        """
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
        month = self.MONTHS_FR.get(month_name)
        if not month:
            return None
        today = date.today()
        year = today.year
        candidate = date(year, month, day)
        if candidate < today:
            candidate = date(year + 1, month, day)
        return candidate.isoformat()

    def parse_csv_bytes(self, content: bytes, encoding: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Parse un CSV (bytes) et retourne une liste de dicts normalisés.

        - Détecte l'encodage simple : essaye utf-8 puis latin-1.
        - Normalise les noms de colonnes (strip + lower, supprime espaces/underscores).
        - Ignore les colonnes inconnues.
        """
        text = None
        errors: list[str] = []
        for enc in [encoding or "utf-8", "latin-1"]:
            try:
                text = content.decode(enc)
                break
            except UnicodeDecodeError as exc:
                errors.append(f"decode-{enc}: {exc}")
                continue

        if text is None:
            raise ValueError(f"Impossible de décoder le CSV ({'; '.join(errors)})")

        reader = csv.DictReader(StringIO(text))
        rows: List[Dict[str, Any]] = []

        # Préparer une map colonne source -> clé cible
        normalized_fieldnames = {
            (name or "").strip().replace(" ", "").replace("_", "").lower(): name
            for name in reader.fieldnames or []
        }

        for idx, raw in enumerate(reader, start=1):
            normalized_row: Dict[str, Any] = {}
            for norm_key, source_name in normalized_fieldnames.items():
                target_key = self.COLUMN_MAP.get(norm_key)
                if not target_key:
                    continue
                normalized_row[target_key] = (raw.get(source_name) or "").strip()

            # Générer un id si absent
            if not normalized_row.get("id"):
                normalized_row["id"] = f"pda_auto_{idx:04d}"

            # Dates FR → ISO si nécessaire
            for field in ("request_date", "appointment_date"):
                val = normalized_row.get(field)
                if val:
                    iso = self._parse_french_date(val)
                    if iso:
                        normalized_row[field] = iso

            # Montant par défaut si vide
            if not normalized_row.get("billing_amount"):
                normalized_row["billing_amount"] = "175.00"

            # Map technicien texte -> id connu
            tech = (normalized_row.get("technician_id") or "").lower()
            tech_map = {
                "nick": "usr_U9E5bLxrFiXqTbE8",
                "nicolas": "usr_U9E5bLxrFiXqTbE8",
            }
            if tech in tech_map:
                normalized_row["technician_id"] = tech_map[tech]

            # On ajoute uniquement les lignes non vides
            if any(v != "" for v in normalized_row.values()):
                rows.append(normalized_row)

        return rows
