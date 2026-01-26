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
# Basés sur core/humidity_alert_detector.py - Filtrage strict pour alertes réelles
MAINTENANCE_KEYWORDS = [
    # Housse retirée (cover_removed)
    "housse retirée",
    "housse retiree",
    "housse enlevée",
    "housse enlevee",
    "sans housse",
    "pas de housse",
    
    # Dampp-Chaser / Alimentation (dampp_chaser)
    "dampp chaser débranché",
    "dampp-chaser débranché",
    "dampp chaser off",
    "dampp chaser éteint",
    "dampp chaser ne fonctionne",
    "dampp-chaser ne fonctionne",
    "pls débranché",
    "système débranché",
    "systeme debranche",
    "débranché",
    "debranche",
    "rebranché",
    "rebranche",
    "rallonge",
    "besoin rallonge",
    
    # Réservoir (reservoir)
    "réservoir vide",
    "reservoir vide",
    "tank empty",
    "réservoir à remplir",
    
    # Environnement critique (environment) - SPÉCIFIQUE
    "fenêtre ouverte",
    "fenetre ouverte",
    "température trop basse",
    "trop froid",
    "humidité trop élevée",
    "humidité très basse",
    "conditions inadéquates",
    
    # Humidité extrême (high/low_humidity)
    "humidité haute",
    "humidité élevée",
    "très humide",
    "trop humide",
    "humidité basse",
    "humidité faible",
    "très sec",
    "trop sec",
]

# Clients institutionnels pour les Alertes Maintenance
INSTITUTIONAL_CLIENTS = ["uqam", "vincent", "place des arts"]

MAINTENANCE_TABLES_CANDIDATES = [
    "maintenance_alerts",
    "gazelle_maintenance_alerts",
]

# Colonnes pour l'onglet Demandes PdA
PDA_REQUESTS_HEADERS = [
    "DateDemande",
    "DateRV",
    "Heure",
    "Salle",
    "Piano",
    "Artiste",
    "Service",
    "Demandeur",
    "Statut",
    "Notes"
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
        
        # v6: Utiliser IdentityManager pour charger depuis Supabase ou fallback v5
        if credentials_path:
            # Si un chemin est fourni explicitement, l'utiliser
            self.credentials_path = credentials_path
        else:
            # Sinon, utiliser IdentityManager (v6) avec fallback v5
            try:
                from v6_foundation.identity_manager import IdentityManager
                identity_manager = IdentityManager(storage=self.storage)
                self.credentials_path = identity_manager.get_google_credentials_path()
                # Garder une référence pour le nettoyage si nécessaire
                self._identity_manager = identity_manager
            except (ImportError, FileNotFoundError) as e:
                # Fallback v5: Variable d'environnement
                print(f"⚠️  IdentityManager non disponible, utilisation du fallback v5: {e}")
                self.credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
                self._identity_manager = None
        
        if not self.credentials_path:
            raise FileNotFoundError(
                "GOOGLE_APPLICATION_CREDENTIALS manquant. "
                "Vérifiez Supabase system_settings['GOOGLE_SHEETS_JSON'] "
                "ou la variable d'environnement GOOGLE_APPLICATION_CREDENTIALS"
            )
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
        """Récupère les timeline entries avec infos piano et user (avec pagination)."""
        from supabase import create_client

        supabase = create_client(self.storage.supabase_url, self.storage.supabase_key)

        all_entries = []
        page_size = 1000
        offset = 0
        
        print(f"📥 Récupération des timeline entries (pagination {page_size})...")

        while True:
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
            .order('occurred_at', desc=True) \
            .range(offset, offset + page_size - 1)

            if since:
                query = query.gte('occurred_at', since.isoformat())

            result = query.execute()
            batch = result.data or []
            
            if not batch:
                break
            
            all_entries.extend(batch)
            print(f"   Page {offset//page_size + 1}: {len(batch)} entrées (total: {len(all_entries)})")
            
            if len(batch) < page_size:
                break
            
            offset += page_size

        print(f"✅ Total récupéré: {len(all_entries)} entrées\n")
        return all_entries

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

    def _fetch_pda_requests(self) -> List[Dict]:
        """Récupère les demandes Place des Arts depuis Supabase."""
        from supabase import create_client

        try:
            supabase = create_client(self.storage.supabase_url, self.storage.supabase_key)
            result = supabase.table('place_des_arts_requests').select('*').order('appointment_date', desc=True).execute()
            data = result.data or []
            print(f"📥 {len(data)} demandes Place des Arts récupérées")
            return data
        except Exception as e:
            print(f"⚠️ Erreur récupération demandes PdA: {e}")
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
    
    @staticmethod
    def _format_piano_info(make: str, model: str, serial: str, piano_type: str, year: str) -> str:
        """
        Formate les infos du piano en une seule description lisible.
        Exemple: "Steinway Model D #123456 (Grand, 1995)"
        """
        parts = []
        
        # Marque et modèle
        if make and model:
            parts.append(f"{make} {model}")
        elif make:
            parts.append(make)
        elif model:
            parts.append(model)
        
        # Numéro de série
        if serial:
            parts.append(f"#{serial}")
        
        # Type et année entre parenthèses
        extras = []
        if piano_type:
            extras.append(piano_type)
        if year:
            extras.append(year)
        
        if extras:
            parts.append(f"({', '.join(extras)})")
        
        return " ".join(parts) if parts else ""

    def _categories_for_entry(self, client_name: str, description: str) -> List[str]:
        """Détermine les onglets cibles pour une entrée."""
        target_tabs: List[str] = []
        text = self._normalize_text(client_name, description)

        for tab, keywords in CLIENT_KEYWORDS.items():
            if any(keyword in text for keyword in keywords):
                target_tabs.append(tab)

        # Alertes Maintenance: SEULEMENT pour clients institutionnels avec mots-clés spécifiques
        is_institutional = any(inst_keyword in text for inst_keyword in INSTITUTIONAL_CLIENTS)
        has_maintenance_issue = any(keyword in text for keyword in MAINTENANCE_KEYWORDS)
        
        if is_institutional and has_maintenance_issue:
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
    def _ensure_headers(ws, headers: Optional[List[str]] = None):
        """Ajoute l'en-tête si la feuille est vide."""
        try:
            if not ws.acell("A1").value:
                if headers is None:
                    headers = [
                        "DateEvenement",
                        "TypeEvenement",
                        "Description",
                        "Piano",  # Colonne unique regroupant marque, modèle, série, type, année
                        "Local",
                        "Technicien",
                        "MesureHumidite"
                    ]
                # Construire la plage dynamiquement (A1:X1 où X dépend du nombre de colonnes)
                end_col = chr(ord('A') + len(headers) - 1)
                ws.update(f"A1:{end_col}1", [headers])
        except Exception as e:
            print(f"⚠️ Impossible d'écrire l'en-tête sur {ws.title}: {e}")

    @staticmethod
    def _create_row_signature(row: List[str]) -> str:
        """
        Crée une signature unique pour une ligne basée sur DateEvenement + Description.
        Utilisé pour détecter les doublons.
        """
        date_event = (row[0] if len(row) > 0 else "").strip()
        description = (row[2] if len(row) > 2 else "").strip()
        # Tronquer la description à 200 caractères pour éviter les problèmes de comparaison
        description_truncated = description[:200]
        return f"{date_event}|||{description_truncated}"

    @staticmethod
    def _get_existing_row_signatures(ws) -> set:
        """
        Récupère les signatures des lignes existantes dans le Google Sheet.
        Retourne un set de signatures pour la détection de doublons.
        """
        try:
            all_values = ws.get_all_values()
            if len(all_values) <= 1:  # Seulement l'en-tête ou vide
                return set()

            # Ignorer l'en-tête (première ligne)
            existing_signatures = set()
            for row in all_values[1:]:  # Skip header
                if row and any(cell.strip() for cell in row):  # Ignorer les lignes vides
                    signature = ServiceReports._create_row_signature(row)
                    existing_signatures.add(signature)

            return existing_signatures
        except Exception as e:
            print(f"⚠️ Erreur lecture signatures existantes pour {ws.title}: {e}")
            return set()

    @staticmethod
    def _filter_duplicate_rows(rows: List[List[str]], existing_signatures: set) -> List[List[str]]:
        """
        Filtre les lignes en double en comparant avec les signatures existantes.
        Retourne uniquement les nouvelles lignes qui n'existent pas déjà.
        """
        new_rows = []
        duplicate_count = 0

        for row in rows:
            signature = ServiceReports._create_row_signature(row)
            if signature not in existing_signatures:
                new_rows.append(row)
            else:
                duplicate_count += 1

        if duplicate_count > 0:
            print(f"   ⚠️ {duplicate_count} ligne(s) en double ignorée(s)")

        return new_rows

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
        """
        Extrait température et humidité d'un texte avec détection intelligente de toutes les variantes.

        Formats détectés:
        - 20C, 33% | 20c, 33% | 20°C, 33% | 20°, 33% | 20 C, 33%
        - Température ambiante 23° Celsius, humidité relative 35%
        - 68F, 40% (Fahrenheit)

        Retourne format normalisé: "20°, 33%" ou "33%" si seulement humidité
        """
        import re

        if not text:
            return ""

        # PATTERN 1: Détecter format compact direct "20C, 33%" ou "20°, 33%"
        # Cherche: nombre + [C|c|°|° C|°C|F|f] + optionnel(virgule|espace) + nombre + %
        compact_pattern = r'(\d+)\s*([CcFf°](?:\s*[CcFf])?)\s*,?\s*(\d+)\s*%'
        compact_match = re.search(compact_pattern, text)

        if compact_match:
            temp_value = compact_match.group(1)
            temp_unit = compact_match.group(2).strip().upper()
            humidity_value = compact_match.group(3)

            # Normaliser l'unité (tout convertir en °)
            return f"{temp_value}°, {humidity_value}%"

        # PATTERN 2: Chercher température seule avec différentes variantes
        # 23°, 23° Celsius, 23°C, 23C, 23c, 23 C, 23 degrés, 68F, etc.
        temp_patterns = [
            r'(\d+)\s*°\s*(?:Celsius|C)?',  # 23°, 23° Celsius, 23°C
            r'(\d+)\s*[CcFf](?:\s|,|$)',     # 23C, 23c, 23F (suivi d'espace, virgule ou fin)
            r'(\d+)\s+degrés?\s*(?:Celsius)?', # 23 degrés, 23 degré Celsius
        ]

        temp_match = None
        for pattern in temp_patterns:
            temp_match = re.search(pattern, text, re.IGNORECASE)
            if temp_match:
                break

        # PATTERN 3: Chercher humidité
        # Priorité 1: Avec mot-clé "humidité/humidity"
        humidity_match = re.search(r'(?:humidité|humidity)[^0-9]*(\d+)\s*%', text, re.IGNORECASE)

        # Priorité 2: Juste un nombre suivi de %
        if not humidity_match:
            all_percent = re.findall(r'(\d+)\s*%', text)
            if all_percent:
                # Prendre le premier % trouvé
                humidity_match = type('obj', (object,), {'group': lambda self, x: all_percent[0]})()

        # COMBINER les résultats
        if temp_match and humidity_match:
            temp = temp_match.group(1)
            humidity = humidity_match.group(1) if hasattr(humidity_match, 'group') else all_percent[0]
            return f"{temp}°, {humidity}%"
        elif temp_match:
            return f"{temp_match.group(1)}°"
        elif humidity_match:
            humidity = humidity_match.group(1) if hasattr(humidity_match, 'group') else (all_percent[0] if 'all_percent' in locals() else "")
            return f"{humidity}%" if humidity else ""

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

        # Dédupliquer les entrées : certaines ont été importées avec tle_ ET tme_ (deux IDs différents)
        # Stratégie : Garder tme_ (préfixe plus récent) et éliminer tle_ si doublon
        # NOTE: On utilise SEULEMENT (date, description) sans piano_id car les doublons peuvent avoir des piano_id différents
        from collections import defaultdict
        
        # Grouper par signature (date, description SEULEMENT)
        by_signature = defaultdict(list)
        for entry in entries:
            occurred_at = entry.get("occurred_at") or entry.get("entry_date") or ""
            desc = entry.get("description") or entry.get("title") or ""
            date_str = occurred_at[:10] if occurred_at and len(occurred_at) >= 10 else "no_date"
            signature = f"{date_str}|||{desc[:200]}"
            by_signature[signature].append(entry)
        
        # Pour chaque signature, garder SEULEMENT l'entrée tme_ si elle existe, sinon garder la première
        deduplicated_entries = []
        for signature, group in by_signature.items():
            if len(group) == 1:
                # Pas de doublon
                deduplicated_entries.append(group[0])
            else:
                # Doublon : prioriser tme_ sur tle_
                tme_entries = [e for e in group if e.get("external_id", "").startswith("tme_")]
                if tme_entries:
                    deduplicated_entries.append(tme_entries[0])  # Garder le premier tme_
                else:
                    deduplicated_entries.append(group[0])  # Fallback : garder le premier
        
        print(f"🔧 Déduplication: {len(entries)} → {len(deduplicated_entries)} entrées ({len(entries) - len(deduplicated_entries)} doublons éliminés)")

        # Séparer services et mesures
        services = []
        measurements = []

        for entry in deduplicated_entries:
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

                # 3. Combiner intelligemment (éviter doublons)
                # Priorité: mesure complète (temp + humidité) > humidité seule
                all_measures = []

                if extracted_from_text:
                    all_measures.append(extracted_from_text)
                if measures:
                    all_measures.extend(measures)

                # Dédupliquer et prioriser les mesures complètes
                if all_measures:
                    # Séparer mesures complètes (avec °) et humidité seule (juste %)
                    complete_measures = [m for m in all_measures if "°" in m]
                    humidity_only = [m for m in all_measures if "°" not in m and "%" in m]

                    # Priorité 1: Si on a une mesure complète, l'utiliser (prendre la première)
                    if complete_measures:
                        mesure_humidite = complete_measures[0]
                    # Priorité 2: Sinon, prendre l'humidité seule
                    elif humidity_only:
                        mesure_humidite = humidity_only[0]

            # Formater la description du piano en une seule colonne
            piano_info = self._format_piano_info(marque, modele, numero_serie, type_piano, annee)
            
            row = [
                entry_date,          # DateEvenement
                "Service",           # TypeEvenement
                description,         # Description
                piano_info,          # Piano (regroupé)
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

            # Dédupliquer et prioriser les mesures complètes (même logique que services)
            complete_measures = [m for m in measures if "°" in m]
            humidity_only = [m for m in measures if "°" not in m and "%" in m]

            if complete_measures:
                mesure_humidite = complete_measures[0]
            elif humidity_only:
                mesure_humidite = humidity_only[0]
            else:
                mesure_humidite = ""

            # Formater la description du piano en une seule colonne
            piano_info = self._format_piano_info(marque, modele, numero_serie, type_piano, annee)
            
            row = [
                entry_date,          # DateEvenement
                "Mesure",            # TypeEvenement (orpheline)
                "",                  # Description vide
                piano_info,          # Piano (regroupé)
                local,               # Local
                technicien,          # Technicien
                mesure_humidite      # MesureHumidite
            ]

            for tab in self._categories_for_entry(client_name, ""):
                rows_by_tab[tab].append(row)

        return rows_by_tab

    @staticmethod
    def _extract_date_only(date_str: str) -> str:
        """Extrait la date (YYYY-MM-DD) sans conversion de timezone.

        Pour les demandes PdA, les dates sont des dates calendrier,
        pas des instants précis - donc on ne convertit pas la timezone.
        """
        if not date_str:
            return ""
        # Prendre juste les 10 premiers caractères (YYYY-MM-DD)
        return date_str[:10] if len(date_str) >= 10 else date_str

    def _build_rows_from_pda_requests(self, requests: List[Dict]) -> List[List[str]]:
        """Construit les lignes pour l'onglet Demandes PdA."""
        rows: List[List[str]] = []

        for req in requests:
            # Extraire les dates SANS conversion timezone (dates calendrier)
            request_date = self._extract_date_only(req.get("request_date") or req.get("created_at") or "")
            appointment_date = self._extract_date_only(req.get("appointment_date") or "")

            row = [
                request_date,                           # DateDemande
                appointment_date,                       # DateRV
                req.get("time") or "",                  # Heure
                req.get("room") or "",                  # Salle
                req.get("piano") or "",                 # Piano
                req.get("for_who") or "",               # Artiste
                req.get("service") or "",               # Service
                req.get("requester") or "",             # Demandeur
                req.get("status") or "",                # Statut
                (req.get("notes") or "")[:200]          # Notes (tronquées)
            ]
            rows.append(row)

        return rows

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

            # Filtrer: seulement clients institutionnels avec mots-clés de maintenance
            text = self._normalize_text(client_name, description)
            is_institutional = any(inst_keyword in text for inst_keyword in INSTITUTIONAL_CLIENTS)
            has_maintenance_issue = any(keyword in text for keyword in MAINTENANCE_KEYWORDS)
            
            if not (is_institutional and has_maintenance_issue):
                continue  # Skip cette alerte

            # Construire ligne avec 7 colonnes (alertes n'ont pas d'infos piano)
            row = [
                self._to_montreal_date(date_str),  # DateEvenement
                "Alerte",                          # TypeEvenement
                description,                       # Description
                "",                                # Piano (vide pour les alertes)
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

        # NOTE: On n'utilise PLUS la table humidity_alerts pour éviter les doublons.
        # Les alertes sont déjà détectées depuis les timeline entries via les mots-clés.
        # alerts = self._fetch_maintenance_alerts()

        rows_by_tab = self._build_rows_from_timeline(timeline_entries, clients_map)

        # DÉSACTIVÉ: Évite les doublons car les alertes sont déjà dans timeline entries
        # alert_rows = self._build_rows_from_alerts(alerts, clients_map) if alerts else []
        # if alert_rows:
        #     rows_by_tab["Alertes Maintenance"].extend(alert_rows)

        # Récupérer les demandes Place des Arts
        pda_requests = self._fetch_pda_requests()
        pda_rows = self._build_rows_from_pda_requests(pda_requests)

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
                # Filtrer les doublons si append=True
                if append:
                    existing_signatures = self._get_existing_row_signatures(ws)
                    rows = self._filter_duplicate_rows(rows, existing_signatures)

                if rows:
                    try:
                        # Trier par date décroissante (plus récentes en premier)
                        # La colonne 0 est DateEvenement (format YYYY-MM-DD)
                        rows_sorted = sorted(rows, key=lambda r: r[0] if r[0] else "", reverse=True)

                        # Insérer après l'en-tête (ligne 2) pour garder les plus récentes en haut
                        ws.insert_rows(rows_sorted, row=2, value_input_option="RAW")
                        counts[tab] = len(rows_sorted)
                    except Exception as e:
                        print(f"❌ Erreur insert {tab}: {e}")
                        counts[tab] = 0
                else:
                    counts[tab] = 0
            else:
                counts[tab] = 0

        # === ONGLET DEMANDES PDA ===
        pda_tab = "Demandes PdA"
        ws_pda = self._get_or_create_ws(workbook, pda_tab)
        if not append:
            try:
                ws_pda.clear()
            except Exception as e:
                print(f"⚠️ Impossible de nettoyer l'onglet {pda_tab}: {e}")

        # En-têtes spécifiques pour les demandes PdA
        self._ensure_headers(ws_pda, PDA_REQUESTS_HEADERS)

        if pda_rows:
            # Filtrer les doublons si append=True
            if append:
                existing_signatures = self._get_existing_row_signatures(ws_pda)
                # Pour PdA, la signature est DateRV + Salle + Artiste (colonnes 1, 3, 5)
                pda_rows_filtered = []
                for row in pda_rows:
                    sig = f"{row[1]}|||{row[3]}|||{row[5]}"  # DateRV + Salle + Artiste
                    if sig not in existing_signatures:
                        pda_rows_filtered.append(row)
                    existing_signatures.add(sig)
                pda_rows = pda_rows_filtered

            if pda_rows:
                try:
                    # Trier par DateRV décroissante (colonne 1)
                    rows_sorted = sorted(pda_rows, key=lambda r: r[1] if r[1] else "", reverse=True)
                    ws_pda.insert_rows(rows_sorted, row=2, value_input_option="RAW")
                    counts[pda_tab] = len(rows_sorted)
                    print(f"✅ {len(rows_sorted)} demandes PdA ajoutées à l'onglet '{pda_tab}'")
                except Exception as e:
                    print(f"❌ Erreur insert {pda_tab}: {e}")
                    counts[pda_tab] = 0
            else:
                counts[pda_tab] = 0
        else:
            counts[pda_tab] = 0

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
