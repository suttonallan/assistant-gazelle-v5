"""
Génération des rapports Timeline v5 depuis Supabase vers Google Sheets.

Principes:
- Lecture Supabase (tables gazelle_timeline_entries, gazelle_clients, maintenance_alerts*)
- Catégorisation par onglet (UQAM / Vincent / Place des Arts / Alertes Maintenance)
- Écriture dans le Google Sheet "Rapport Timeline v5" (append par défaut)
- Conversion horaire en America/Toronto (Montréal)

(*) La table des alertes peut être nommée maintenance_alerts ou gazelle_maintenance_alerts.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Dict, List, Optional
from zoneinfo import ZoneInfo

import gspread
import requests
from google.auth.exceptions import DefaultCredentialsError
from gspread.exceptions import SpreadsheetNotFound, WorksheetNotFound

from core.supabase_storage import SupabaseStorage

MONTREAL_TZ = ZoneInfo("America/Toronto")
SHEET_NAME = "Rapport Timeline v5"

CLIENT_KEYWORDS = {
    "UQAM": ["uqam"],
    "Vincent": ["vincent"],
    "Place des Arts": ["place des arts"],
}

# Mots-clés pour l'onglet Alertes Maintenance (notes ou description)
MAINTENANCE_KEYWORDS = [
    "prochain accord",
    "entretien",
    "rappel",
    "maintenance",
    "accordage",
    "follow-up",
    "suivi",
]

MAINTENANCE_TABLES_CANDIDATES = [
    "maintenance_alerts",
    "gazelle_maintenance_alerts",
]


class ServiceReports:
    """Service principal pour générer les rapports Timeline v5."""

    def __init__(
        self,
        storage: Optional[SupabaseStorage] = None,
        sheet_name: str = SHEET_NAME,
        credentials_path: Optional[str] = None,
    ) -> None:
        self.storage = storage or SupabaseStorage()
        self.sheet_name = sheet_name
        self.credentials_path = credentials_path or os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        if not self.credentials_path:
            raise FileNotFoundError("GOOGLE_APPLICATION_CREDENTIALS manquant dans l'environnement")
        if not os.path.exists(self.credentials_path):
            raise FileNotFoundError(f"Fichier de service account introuvable: {self.credentials_path}")
        self.gc = self._init_gspread_client(self.credentials_path)

    @staticmethod
    def _init_gspread_client(credentials_path: str) -> gspread.Client:
        """Initialise le client gspread via service account."""
        try:
            return gspread.service_account(filename=credentials_path)
        except DefaultCredentialsError as e:
            raise RuntimeError(f"Impossible d'initialiser le client Google: {e}")

    # ------------------------------------------------------------------
    # Récupération des données Supabase
    # ------------------------------------------------------------------
    def _fetch_clients_map(self) -> Dict[str, str]:
        """Retourne un mapping external_id -> company_name."""
        url = f"{self.storage.api_url}/gazelle_clients"
        params = {"select": "external_id,company_name"}
        resp = requests.get(url, headers=self.storage._get_headers(), params=params, timeout=20)
        if resp.status_code != 200:
            print(f"⚠️ Impossible de récupérer les clients ({resp.status_code}): {resp.text}")
            return {}
        data = resp.json() or []
        return {item.get("external_id"): item.get("company_name") for item in data if item.get("external_id")}

    def _fetch_timeline_entries(self, since: Optional[datetime]) -> List[Dict]:
        """Récupère les timeline entries (optionnellement depuis une date)."""
        url = f"{self.storage.api_url}/gazelle_timeline_entries"
        params = {
            "select": "external_id,description,entry_date,entity_id,entity_type,event_type",
            "order": "entry_date.asc",
        }
        if since:
            # Supabase filtre ISO 8601 via gte.
            params["entry_date"] = f"gte.{since.isoformat()}"
        resp = requests.get(url, headers=self.storage._get_headers(), params=params, timeout=30)
        if resp.status_code != 200:
            raise RuntimeError(f"Erreur Supabase timeline ({resp.status_code}): {resp.text}")
        return resp.json() or []

    def _fetch_maintenance_alerts(self) -> List[Dict]:
        """Tente de récupérer les alertes de maintenance depuis Supabase."""
        headers = self.storage._get_headers()
        for table_name in MAINTENANCE_TABLES_CANDIDATES:
            url = f"{self.storage.api_url}/{table_name}"
            params = {"select": "id,client_id,piano_id,date_observation,description,notes,is_resolved,created_at"}
            try:
                resp = requests.get(url, headers=headers, params=params, timeout=20)
            except Exception as e:
                print(f"⚠️ Erreur requête {table_name}: {e}")
                continue
            if resp.status_code == 200:
                data = resp.json() or []
                if data:
                    return data
        return []

    # ------------------------------------------------------------------
    # Utilitaires
    # ------------------------------------------------------------------
    def get_last_run(self) -> Optional[datetime]:
        """Retourne la dernière exécution stockée dans system_settings."""
        try:
            last_run_value = self.storage.get_system_setting("reports_timeline_last_run")
            if not last_run_value:
                return None
            return datetime.fromisoformat(str(last_run_value))
        except Exception:
            return None

    @staticmethod
    def _to_montreal_date(date_str: str) -> str:
        """Convertit une date ISO en AAAA-MM-JJ fuseau Montréal."""
        if not date_str:
            return ""
        try:
            cleaned = date_str.replace("Z", "+00:00")
            dt = datetime.fromisoformat(cleaned)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(MONTREAL_TZ).strftime("%Y-%m-%d")
        except Exception:
            return date_str

    @staticmethod
    def _normalize_text(*parts: Optional[str]) -> str:
        return " ".join([p or "" for p in parts]).lower()

    def _categories_for_entry(self, client_name: str, description: str) -> List[str]:
        """Détermine les onglets cibles pour une entrée."""
        target_tabs: List[str] = []
        text = self._normalize_text(client_name, description)

        for tab, keywords in CLIENT_KEYWORDS.items():
            if any(keyword in text for keyword in keywords):
                target_tabs.append(tab)

        if any(keyword in text for keyword in MAINTENANCE_KEYWORDS):
            target_tabs.append("Alertes Maintenance")

        return target_tabs

    # ------------------------------------------------------------------
    # Google Sheets helpers
    # ------------------------------------------------------------------
    def _get_workbook(self):
        """Ouvre le spreadsheet (le crée si besoin)."""
        try:
            return self.gc.open(self.sheet_name)
        except SpreadsheetNotFound:
            # Création si le compte a les droits Drive
            workbook = self.gc.create(self.sheet_name)
            return workbook

    @staticmethod
    def _get_or_create_ws(workbook, title: str):
        try:
            return workbook.worksheet(title)
        except WorksheetNotFound:
            return workbook.add_worksheet(title=title, rows=200, cols=10)

    @staticmethod
    def _ensure_headers(ws):
        """Ajoute l'en-tête si la feuille est vide."""
        try:
            if not ws.acell("A1").value:
                ws.update("A1:D1", [["Date", "Client", "Description", "Type"]])
        except Exception as e:
            print(f"⚠️ Impossible d'écrire l'en-tête sur {ws.title}: {e}")

    # ------------------------------------------------------------------
    # Construction et écriture des rapports
    # ------------------------------------------------------------------
    def _build_rows_from_timeline(
        self,
        entries: List[Dict],
        clients_map: Dict[str, str],
    ) -> Dict[str, List[List[str]]]:
        rows_by_tab = {tab: [] for tab in CLIENT_KEYWORDS.keys()}
        rows_by_tab["Alertes Maintenance"] = []

        for entry in entries:
            description = entry.get("description") or ""
            client_name = clients_map.get(entry.get("entity_id"), "Inconnu")
            entry_date = self._to_montreal_date(entry.get("entry_date", ""))
            entry_type = entry.get("event_type", "") or "timeline_event"

            for tab in self._categories_for_entry(client_name, description):
                rows_by_tab[tab].append([entry_date, client_name, description, entry_type])

        return rows_by_tab

    def _build_rows_from_alerts(
        self,
        alerts: List[Dict],
        clients_map: Dict[str, str],
    ) -> List[List[str]]:
        rows: List[List[str]] = []
        for alert in alerts:
            client_id = alert.get("client_id") or alert.get("clientId")
            client_name = clients_map.get(client_id, "Inconnu")
            date_str = (
                alert.get("date_observation")
                or alert.get("dateObservation")
                or alert.get("created_at")
                or alert.get("createdAt")
                or ""
            )
            description = alert.get("description") or alert.get("notes") or ""
            entry_type = "maintenance_alert"
            rows.append([self._to_montreal_date(date_str), client_name, description, entry_type])
        return rows

    def generate_reports(self, since: Optional[datetime] = None, append: bool = True) -> Dict[str, int]:
        """
        Génère/append les rapports vers Google Sheets.

        Args:
            since: datetime à partir de laquelle récupérer les timeline entries
            append: si False, efface et réécrit les onglets
        """
        clients_map = self._fetch_clients_map()
        timeline_entries = self._fetch_timeline_entries(since=since)
        alerts = self._fetch_maintenance_alerts()

        rows_by_tab = self._build_rows_from_timeline(timeline_entries, clients_map)
        alert_rows = self._build_rows_from_alerts(alerts, clients_map) if alerts else []
        if alert_rows:
            rows_by_tab["Alertes Maintenance"].extend(alert_rows)

        workbook = self._get_workbook()
        counts: Dict[str, int] = {}

        for tab, rows in rows_by_tab.items():
            ws = self._get_or_create_ws(workbook, tab)
            if not append:
                try:
                    ws.clear()
                except Exception as e:
                    print(f"⚠️ Impossible de nettoyer l'onglet {tab}: {e}")
            self._ensure_headers(ws)

            if rows:
                try:
                    ws.append_rows(rows, value_input_option="RAW")
                    counts[tab] = len(rows)
                except Exception as e:
                    print(f"❌ Erreur append {tab}: {e}")
                    counts[tab] = 0
            else:
                counts[tab] = 0

        # Sauvegarder la date de dernière génération pour éviter les doublons
        try:
            self.storage.save_system_setting(
                "reports_timeline_last_run",
                datetime.now(timezone.utc).isoformat(),
            )
        except Exception as e:
            print(f"⚠️ Impossible de sauvegarder reports_timeline_last_run: {e}")

        return counts


def run_reports(since: Optional[datetime] = None, append: bool = True) -> Dict[str, int]:
    """Entrypoint utilitaire."""
    service = ServiceReports()
    return service.generate_reports(since=since, append=append)
