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

MONTREAL_TZ = ZoneInfo("America/Montreal")
# Google Sheet: https://docs.google.com/spreadsheets/d/1ZZsMrIT0BEwHKQ6-BKGzFoXR3k99zCEzixp0tsRKUj8
SHEET_NAME = "Rapport Timeline de l'assistant v5"

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
        """Récupère les timeline entries avec infos piano et user."""
        from supabase import create_client

        supabase = create_client(self.storage.supabase_url, self.storage.supabase_key)

        # Construire la requête avec relations
        query = supabase.table('gazelle_timeline_entries').select('''
            external_id,
            description,
            title,
            entry_date,
            occurred_at,
            entity_id,
            entity_type,
            event_type,
            entry_type,
            piano_id,
            user_id,
            piano:gazelle_pianos(
                make,
                model,
                serial_number,
                type,
                year,
                location,
                client_external_id
            ),
            user:users(
                first_name,
                last_name
            )
        ''') \
        .in_('entry_type', ['SERVICE_ENTRY_MANUAL', 'PIANO_MEASUREMENT']) \
        .order('occurred_at', desc=True)

        if since:
            query = query.gte('occurred_at', since.isoformat())

        result = query.execute()
        return result.data or []

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
                headers = [
                    "DateEvenement",
                    "TypeEvenement",
                    "Description",
                    "NomClient",
                    "Marque",
                    "Modele",
                    "NumeroSerie",
                    "TypePiano",
                    "Annee",
                    "Local",
                    "Technicien",
                    "MesureHumidite"
                ]
                ws.update("A1:L1", [headers])
        except Exception as e:
            print(f"⚠️ Impossible d'écrire l'en-tête sur {ws.title}: {e}")

    # ------------------------------------------------------------------
    # Construction et écriture des rapports
    # ------------------------------------------------------------------
    @staticmethod
    def _simplify_measurement(description: str) -> str:
        """Simplifie la description d'une mesure (ex: 'Piano measurement taken: 20°C, 42%' -> '20°C, 42%')."""
        if not description:
            return ""
        # Format anglais
        if "Piano measurement taken:" in description:
            return description.split(":", 1)[1].strip()
        # Format français
        elif "Mesure du piano prise :" in description or "Mesure du piano prise:" in description:
            return description.split(":", 1)[1].strip()
        # Déjà simplifié (contient ° et %)
        elif "°" in description and "%" in description:
            return description.strip()
        return ""

    @staticmethod
    def _extract_measurements_from_text(text: str) -> str:
        """Extrait température et humidité d'un texte (ex: 'Température ambiante 23° Celsius, humidité relative 35%' -> '23°, 35%')."""
        import re

        if not text:
            return ""

        # Chercher température (23°, 23° Celsius, 23 degrés, etc.)
        temp_match = re.search(r'(\d+)\s*°\s*(?:Celsius|C)?', text, re.IGNORECASE)

        # Chercher humidité (35%, humidité 35%, humidité relative 35%, etc.)
        humidity_match = re.search(r'(?:humidité|humidity)[^0-9]*(\d+)\s*%', text, re.IGNORECASE)

        # Si pas trouvé avec "humidité", chercher juste un nombre suivi de %
        if not humidity_match:
            # Chercher pattern: nombre + %
            all_percent = re.findall(r'(\d+)\s*%', text)
            if all_percent:
                humidity_match = type('obj', (object,), {'group': lambda self, x: all_percent[0]})()

        if temp_match and humidity_match:
            temp = temp_match.group(1)
            humidity = humidity_match.group(1) if hasattr(humidity_match, 'group') else humidity_match.group(0) if hasattr(humidity_match, 'group') else all_percent[0]
            return f"{temp}°, {humidity}%"
        elif temp_match:
            return f"{temp_match.group(1)}°"
        elif humidity_match:
            humidity = humidity_match.group(1) if hasattr(humidity_match, 'group') else all_percent[0]
            return f"{humidity}%"

        return ""

    def _build_rows_from_timeline(
        self,
        entries: List[Dict],
        clients_map: Dict[str, str],
    ) -> Dict[str, List[List[str]]]:
        from datetime import datetime
        import pytz

        rows_by_tab = {tab: [] for tab in CLIENT_KEYWORDS.keys()}
        rows_by_tab["Alertes Maintenance"] = []

        # Séparer services et mesures
        services = []
        measurements = []

        for entry in entries:
            entry_type = entry.get("entry_type") or ""
            if entry_type == "SERVICE_ENTRY_MANUAL":
                services.append(entry)
            elif entry_type == "PIANO_MEASUREMENT":
                measurements.append(entry)

        # Grouper les mesures par (piano_id, date_only)
        measurements_by_piano_date = {}
        for measurement in measurements:
            piano_id = measurement.get("piano_id")
            date_raw = measurement.get("occurred_at") or measurement.get("entry_date", "")

            if not piano_id or not date_raw:
                continue

            # Convertir en date Montreal (sans heure)
            try:
                cleaned = date_raw.replace("Z", "+00:00")
                dt = datetime.fromisoformat(cleaned)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=pytz.utc)
                date_only = dt.astimezone(MONTREAL_TZ).date()
            except:
                continue

            key = (piano_id, date_only)
            if key not in measurements_by_piano_date:
                measurements_by_piano_date[key] = []

            # Simplifier la description
            desc = measurement.get("title") or measurement.get("description") or ""
            simplified = self._simplify_measurement(desc)
            if simplified:
                measurements_by_piano_date[key].append(simplified)

        # Traiter les services
        service_keys = set()
        for service in services:
            piano = service.get("piano") or {}
            entity_id = service.get("entity_id")
            client_id = piano.get("client_external_id") or entity_id
            client_name = clients_map.get(client_id, "Inconnu")

            date_raw = service.get("occurred_at") or service.get("entry_date", "")
            entry_date = self._to_montreal_date(date_raw)

            # Date_only pour lookup mesures
            try:
                cleaned = date_raw.replace("Z", "+00:00")
                dt = datetime.fromisoformat(cleaned)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=pytz.utc)
                date_only = dt.astimezone(MONTREAL_TZ).date()
            except:
                date_only = None

            description = service.get("title") or service.get("description") or ""

            marque = piano.get("make") or ""
            modele = piano.get("model") or ""
            numero_serie = piano.get("serial_number") or ""
            type_piano = piano.get("type") or ""
            annee = str(piano.get("year") or "")
            local = piano.get("location") or ""

            user = service.get("user") or {}
            first_name = user.get("first_name") or ""
            last_name = user.get("last_name") or ""
            technicien = f"{first_name} {last_name}".strip() if (first_name or last_name) else ""

            # Récupérer mesures du même piano + même jour
            piano_id = service.get("piano_id")
            mesure_humidite = ""

            # 1. Parser mesures depuis la description du service
            extracted_from_text = self._extract_measurements_from_text(description)

            # 2. Récupérer mesures des PIANO_MEASUREMENT entries
            if piano_id and date_only:
                key = (piano_id, date_only)
                service_keys.add(key)
                measures = measurements_by_piano_date.get(key, [])

                # 3. Combiner les deux sources
                all_measures = []
                if extracted_from_text:
                    all_measures.append(extracted_from_text)
                if measures:
                    all_measures.extend(measures)

                if all_measures:
                    mesure_humidite = " | ".join(all_measures)

            row = [
                entry_date,          # DateEvenement
                "Service",           # TypeEvenement
                description,         # Description
                client_name,         # NomClient
                marque,              # Marque
                modele,              # Modele
                numero_serie,        # NumeroSerie
                type_piano,          # TypePiano
                annee,               # Annee
                local,               # Local
                technicien,          # Technicien
                mesure_humidite      # MesureHumidite
            ]

            for tab in self._categories_for_entry(client_name, description):
                rows_by_tab[tab].append(row)

        # Ajouter mesures orphelines (sans service le même jour)
        for (piano_id, date_only), measures in measurements_by_piano_date.items():
            key = (piano_id, date_only)
            if key in service_keys:
                continue  # Déjà associée à un service

            # Trouver l'entry pour récupérer les infos
            measurement_entry = None
            for m in measurements:
                if m.get("piano_id") == piano_id:
                    try:
                        date_raw = m.get("occurred_at") or m.get("entry_date", "")
                        cleaned = date_raw.replace("Z", "+00:00")
                        dt = datetime.fromisoformat(cleaned)
                        if dt.tzinfo is None:
                            dt = dt.replace(tzinfo=pytz.utc)
                        m_date_only = dt.astimezone(MONTREAL_TZ).date()
                        if m_date_only == date_only:
                            measurement_entry = m
                            break
                    except:
                        continue

            if not measurement_entry:
                continue

            piano = measurement_entry.get("piano") or {}
            entity_id = measurement_entry.get("entity_id")
            client_id = piano.get("client_external_id") or entity_id
            client_name = clients_map.get(client_id, "Inconnu")

            date_raw = measurement_entry.get("occurred_at") or measurement_entry.get("entry_date", "")
            entry_date = self._to_montreal_date(date_raw)

            marque = piano.get("make") or ""
            modele = piano.get("model") or ""
            numero_serie = piano.get("serial_number") or ""
            type_piano = piano.get("type") or ""
            annee = str(piano.get("year") or "")
            local = piano.get("location") or ""

            user = measurement_entry.get("user") or {}
            first_name = user.get("first_name") or ""
            last_name = user.get("last_name") or ""
            technicien = f"{first_name} {last_name}".strip() if (first_name or last_name) else ""

            mesure_humidite = " | ".join(measures)

            row = [
                entry_date,          # DateEvenement
                "Mesure",            # TypeEvenement (orpheline)
                "",                  # Description vide
                client_name,         # NomClient
                marque,              # Marque
                modele,              # Modele
                numero_serie,        # NumeroSerie
                type_piano,          # TypePiano
                annee,               # Annee
                local,               # Local
                technicien,          # Technicien
                mesure_humidite      # MesureHumidite
            ]

            for tab in self._categories_for_entry(client_name, ""):
                rows_by_tab[tab].append(row)

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

            # Construire ligne avec 12 colonnes (alertes n'ont pas d'infos piano)
            row = [
                self._to_montreal_date(date_str),  # DateEvenement
                "Alerte",                          # TypeEvenement
                description,                       # Description
                client_name,                       # NomClient
                "",                                # Marque
                "",                                # Modele
                "",                                # NumeroSerie
                "",                                # TypePiano
                "",                                # Annee
                "",                                # Local
                "",                                # Technicien
                ""                                 # MesureHumidite
            ]
            rows.append(row)
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
