"""
Service Chat Intelligent - Bridge V5/V6.

Architecture modulaire pour faciliter migration V6.
"""

from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta, time
import re
import pytz

from core.supabase_storage import SupabaseStorage
from .schemas import (
    ChatRequest,
    ChatResponse,
    DayOverview,
    AppointmentOverview,
    AppointmentDetail,
    ComfortInfo,
    TimelineEntry,
)
from .geo_mapping import get_neighborhood_from_postal_code


class ChatService:
    """
    Service principal du chat intelligent.

    Design Pattern: Strategy Pattern pour supporter V5 et V6.
    """

    def __init__(self, data_source: str = "v5"):
        """
        Args:
            data_source: 'v5' ou 'v6' (futur)
        """
        self.data_source = data_source
        self.storage = SupabaseStorage()

        # Strategy: Choisir le provider de données
        if data_source == "v5":
            self.data_provider = V5DataProvider(self.storage)
        else:
            # TODO V6: Implémenter V6DataProvider avec Reconciler
            raise NotImplementedError("V6 data provider not yet implemented")

    def process_query(self, request: ChatRequest) -> ChatResponse:
        """
        Point d'entrée principal: traite une requête naturelle.
        """
        # 1. Interpréter la requête
        query_type, parsed_params = self._interpret_query(request.query, request.date)

        # 2. Récupérer les données selon le type
        if query_type == "day_overview":
            # Si la requête mentionne un technicien spécifique, l'utiliser
            target_technician = parsed_params.get("requested_technician") or request.technician_id

            day_overview = self.data_provider.get_day_overview(
                date=parsed_params["date"],
                technician_id=target_technician,
                user_role=request.user_role
            )

            return ChatResponse(
                interpreted_query=f"Journée du {parsed_params['date']}",
                query_type="day_overview",
                day_overview=day_overview,
                data_source=self.data_source
            )

        elif query_type == "appointment_detail":
            appointment_detail = self.data_provider.get_appointment_detail(
                appointment_id=parsed_params["appointment_id"]
            )

            return ChatResponse(
                interpreted_query=f"Détails du rendez-vous {parsed_params['appointment_id']}",
                query_type="appointment_detail",
                appointment_detail=appointment_detail,
                data_source=self.data_source
            )

        else:
            # Fallback: retourner journée d'aujourd'hui
            today = datetime.now().strftime("%Y-%m-%d")
            target_technician = request.technician_id

            day_overview = self.data_provider.get_day_overview(
                date=today,
                technician_id=target_technician,
                user_role=request.user_role
            )

            return ChatResponse(
                interpreted_query="Requête non reconnue, affichage de la journée en cours",
                query_type="day_overview",
                day_overview=day_overview,
                data_source=self.data_source
            )

    def _interpret_query(self, query: str, date_override: Optional[str] = None) -> Tuple[str, Dict[str, Any]]:
        """
        NLP simple pour interpréter la requête.

        Returns:
            (query_type, parsed_params)
        """
        query_lower = query.lower()

        # Détecter si la requête concerne un autre technicien
        requested_technician = self._detect_technician_in_query(query_lower)

        # Patterns pour les dates
        if any(word in query_lower for word in ["demain", "tomorrow"]):
            target_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
            return ("day_overview", {"date": target_date, "requested_technician": requested_technician})

        if any(word in query_lower for word in ["aujourd'hui", "today", "ma journée"]):
            target_date = datetime.now().strftime("%Y-%m-%d")
            return ("day_overview", {"date": target_date, "requested_technician": requested_technician})

        if "après-demain" in query_lower:
            target_date = (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d")
            return ("day_overview", {"date": target_date, "requested_technician": requested_technician})

        # Pattern pour date spécifique (ex: "le 30 décembre")
        # TODO: Améliorer avec dateparser ou spacy

        # Pattern pour détail d'un RDV
        # Ex: "détails du rendez-vous apt_123"
        if "rendez-vous" in query_lower or "rdv" in query_lower or "appointment" in query_lower:
            # Extraire ID si présent
            id_match = re.search(r'(apt_[a-zA-Z0-9]+)', query)
            if id_match:
                return ("appointment_detail", {"appointment_id": id_match.group(1)})

        # Default: journée du jour
        target_date = date_override or datetime.now().strftime("%Y-%m-%d")
        return ("day_overview", {"date": target_date, "requested_technician": requested_technician})

    def _detect_technician_in_query(self, query_lower: str) -> Optional[str]:
        """
        Détecte si la requête mentionne un technicien spécifique.

        Returns:
            ID Gazelle du technicien détecté ou None
        """
        # Mapping nom/alias → ID Gazelle (source de vérité)
        # Voir docs/REGLE_IDS_GAZELLE.md
        # CORRIGÉ 2025-12-29: IDs étaient inversés (Allan ↔ JP)
        technician_patterns = {
            "usr_HcCiFk7o0vZ9xAI0": ["nicolas", "nick", "nic"],  # Nicolas
            "usr_ReUSmIJmBF86ilY1": ["jp", "jean-philippe", "jeanphilippe", "jean philippe"],  # JP
            "usr_ofYggsCDt2JAVeNP": ["allan", "al"],  # Allan
        }

        for gazelle_id, patterns in technician_patterns.items():
            for pattern in patterns:
                # Chercher "de nicolas", "pour jp", "la journée de jean-philippe"
                if f" de {pattern}" in query_lower or \
                   f" {pattern} " in query_lower or \
                   query_lower.startswith(pattern) or \
                   query_lower.endswith(pattern):
                    return gazelle_id  # Retourner ID Gazelle

        return None


# ============================================================
# DATA PROVIDER V5 (Supabase direct)
# ============================================================

class V5DataProvider:
    """
    Récupère les données depuis la V5 (Supabase gazelle_* tables).

    Isolé dans sa propre classe pour faciliter remplacement par V6.
    """

    def __init__(self, storage: SupabaseStorage):
        self.storage = storage

    def get_day_overview(self, date: str, technician_id: Optional[str] = None, user_role: Optional[str] = None) -> DayOverview:
        """
        Récupère tous les rendez-vous d'une journée.

        Args:
            date: Date au format YYYY-MM-DD
            technician_id: ID Gazelle du technicien (ex: "usr_HcCiFk7o0vZ9xAI0")
            user_role: Rôle de l'utilisateur ("admin", "assistant", "technicien")
        """
        import requests

        # Requête Supabase: appointments de la journée
        url = f"{self.storage.api_url}/gazelle_appointments"
        headers = self.storage._get_headers()

        params = {
            "select": """
                external_id,
                appointment_date,
                appointment_time,
                notes,
                technicien,
                title,
                description,
                location,
                is_personal_event,
                client:client_external_id(
                    external_id,
                    company_name,
                    email,
                    phone,
                    address,
                    city,
                    postal_code,
                    province
                ),
                piano:piano_external_id(
                    external_id,
                    make,
                    model,
                    type,
                    serial_number
                )
            """,
            "appointment_date": f"eq.{date}",
            "order": "appointment_time.asc"
        }

        # Filtrage selon rôle ET technicien demandé
        if technician_id:
            # Si un technicien spécifique est demandé, filtrer par ce technicien
            # (même pour admin/assistant qui veulent voir "les rv de nicolas")
            params["technicien"] = f"eq.{technician_id}"
        elif user_role == "admin" or user_role == "assistant":
            # Admin/Louise sans technicien spécifié → voient TOUT
            pass
        else:
            # Cas problématique: technicien sans technician_id
            # Ne devrait jamais arriver, mais retourner vide par sécurité
            return DayOverview(
                date=date,
                technician_name="Inconnu",
                total_appointments=0,
                total_pianos=0,
                estimated_duration_hours=0,
                neighborhoods=[],
                appointments=[]
            )

        response = requests.get(url, headers=headers, params=params)

        if response.status_code != 200:
            # Fallback: retourner journée vide
            return DayOverview(
                date=date,
                technician_name="Inconnu",
                total_appointments=0,
                total_pianos=0,
                estimated_duration_hours=0,
                neighborhoods=[],
                appointments=[]
            )

        appointments_raw = response.json()

        # Transformer en AppointmentOverview
        appointments = []
        neighborhoods = set()

        for apt_raw in appointments_raw:
            # Filtrer événements selon type
            client = apt_raw.get("client")
            is_personal_event = client is None  # Pas de client = événement personnel

            # Si c'est un rendez-vous client → toujours afficher
            if not is_personal_event:
                overview = self._map_to_overview(apt_raw, date)
                appointments.append(overview)
                if overview.neighborhood:
                    neighborhoods.add(overview.neighborhood)
                continue

            # C'est un événement personnel → appliquer filtrage
            title = apt_raw.get("title", "").lower()
            description = apt_raw.get("description", "").lower()

            # LISTE BLANCHE: Événements liés au TRAVAIL (à afficher)
            work_keywords = ["vd", "commande", "bolduc", "westend", "piano"]
            is_work_event = any(keyword in title or keyword in description for keyword in work_keywords)

            # LISTE NOIRE: Événements PRIVÉS (à filtrer)
            private_keywords = ["admin", "épicerie", "boaz", "enfants", "médical", "suivi", "personnel"]
            is_private_event = any(keyword in title or keyword in description for keyword in private_keywords)

            # Logique de décision:
            # - Si événement de travail détecté → afficher
            # - Si événement privé détecté → filtrer
            # - Sinon (ambigu) → filtrer par sécurité
            if is_work_event and not is_private_event:
                # Événement de travail → afficher
                overview = self._map_to_overview(apt_raw, date)
                appointments.append(overview)
                if overview.neighborhood:
                    neighborhoods.add(overview.neighborhood)
            # Sinon filtrer (privé ou ambigu)

        # Calculer stats
        total_appointments = len(appointments)
        total_pianos = sum(1 for a in appointments if a.piano_id)
        estimated_duration_hours = total_appointments * 1.5  # Estimation: 1.5h par RDV

        # Technicien (prendre le premier si disponible)
        technician_name = appointments[0].client_name if appointments else "Technicien"
        if appointments and appointments_raw:
            tech = appointments_raw[0].get("technicien")
            if tech:
                technician_name = tech

        return DayOverview(
            date=date,
            technician_name=technician_name,
            total_appointments=total_appointments,
            total_pianos=total_pianos,
            estimated_duration_hours=estimated_duration_hours,
            neighborhoods=list(neighborhoods),
            appointments=appointments
        )

    def get_appointment_detail(self, appointment_id: str) -> AppointmentDetail:
        """
        Récupère les détails complets d'un rendez-vous.
        """
        import requests

        # 1. Récupérer l'appointment avec tous les détails
        url = f"{self.storage.api_url}/gazelle_appointments"
        headers = self.storage._get_headers()

        params = {
            "select": """
                *,
                client:client_external_id(*),
                piano:piano_external_id(*)
            """,
            "external_id": f"eq.{appointment_id}"
        }

        response = requests.get(url, headers=headers, params=params)

        if response.status_code != 200 or not response.json():
            raise ValueError(f"Appointment {appointment_id} not found")

        apt_raw = response.json()[0]

        # 2. Récupérer timeline entries du piano
        piano_id = apt_raw.get("piano_id")
        timeline_entries = []

        if piano_id:
            timeline_url = f"{self.storage.api_url}/gazelle_timeline_entries"
            timeline_params = {
                "select": "occurred_at,entry_type,title,details,user:user_id(first_name,last_name)",
                "piano_id": f"eq.{piano_id}",
                "order": "occurred_at.desc",
                "limit": 10
            }

            timeline_response = requests.get(timeline_url, headers=headers, params=timeline_params)

            if timeline_response.status_code == 200:
                timeline_raw = timeline_response.json()
                timeline_entries = [
                    self._map_to_timeline_entry(entry) for entry in timeline_raw
                ]

        # 3. Construire les objets
        overview = self._map_to_overview(apt_raw, apt_raw.get("appointment_date"))
        comfort = self._map_to_comfort_info(apt_raw)
        timeline_summary = self._generate_timeline_summary(timeline_entries)

        return AppointmentDetail(
            overview=overview,
            comfort=comfort,
            timeline_summary=timeline_summary,
            timeline_entries=timeline_entries,
            photos=[]  # TODO: Ajouter si photos disponibles
        )

    # ============================================================
    # MAPPING FUNCTIONS (V5 → Standard Schema)
    # ============================================================

    def _convert_utc_to_montreal(self, time_utc_str: str) -> str:
        """
        Convertit une heure UTC en heure de Montréal (America/Montreal).

        Args:
            time_utc_str: Heure au format "HH:MM:SS" en UTC

        Returns:
            Heure au format "HH:MM" en heure de Montréal

        Exemple:
            "05:00:00" UTC → "00:00" Montréal (UTC-5)
        """
        if not time_utc_str:
            return "Non spécifié"

        try:
            # Parser l'heure UTC
            hour, minute = time_utc_str.split(":")[:2]
            utc_time = time(int(hour), int(minute))

            # Créer un datetime UTC pour aujourd'hui
            utc_tz = pytz.UTC
            montreal_tz = pytz.timezone('America/Montreal')

            # Utiliser une date arbitraire (juste pour la conversion)
            today = datetime.now().date()
            utc_datetime = datetime.combine(today, utc_time)
            utc_datetime = utc_tz.localize(utc_datetime)

            # Convertir en heure de Montréal
            montreal_datetime = utc_datetime.astimezone(montreal_tz)

            return montreal_datetime.strftime("%H:%M")
        except Exception as e:
            # Fallback: retourner l'heure brute
            return time_utc_str[:5]  # "HH:MM"

    def _map_to_overview(self, apt_raw: Dict[str, Any], date: str) -> AppointmentOverview:
        """
        Transforme données V5 brutes en AppointmentOverview.

        FONCTION CRITIQUE pour bridge V5→V6.
        """
        client = apt_raw.get("client") or {}
        piano = apt_raw.get("piano") or {}

        # Time slot - IMPORTANT: Convertir UTC → Montréal
        time_raw = apt_raw.get("appointment_time")
        time_slot = self._convert_utc_to_montreal(time_raw)

        # Client info (ou titre si événement personnel)
        title = apt_raw.get("title") or ""
        description = apt_raw.get("description") or ""

        # Priorité: 1) Nom client (company_name), 2) Titre événement, 3) Fallback
        if client:
            client_name = client.get("company_name")
        else:
            client_name = None

        if not client_name:
            # Événement personnel: utiliser titre
            client_name = title if title else "Événement personnel"

        # Localisation AMÉLIORÉE avec mapping géographique
        location_text = apt_raw.get("location") or ""  # Pour événements personnels

        if client:
            # Rendez-vous client: utiliser adresse du client
            postal_code = client.get("postal_code") or ""
            municipality = client.get("city") or ""
            province = client.get("province") or ""

            # Utiliser le mapping postal pour identifier le quartier
            fallback_city = municipality if municipality else province
            neighborhood = get_neighborhood_from_postal_code(postal_code, fallback_city)

            address_street = client.get("address") or ""
            address_short = address_street[:50] if address_street else municipality
        else:
            # Événement personnel: utiliser champ location ou vide
            neighborhood = ""
            address_short = location_text[:50] if location_text else ""

        # Piano
        piano_brand = piano.get("make")
        piano_model = piano.get("model")
        piano_type = piano.get("type")

        # Action items (extraire des notes)
        notes = apt_raw.get("notes") or ""
        action_items = self._extract_action_items(notes)

        # TODO: Calculer last_visit_date depuis timeline
        last_visit_date = None
        days_since_last_visit = None

        return AppointmentOverview(
            appointment_id=apt_raw.get("external_id"),
            client_id=client.get("external_id"),
            piano_id=piano.get("external_id"),
            time_slot=time_slot,
            date=date,
            client_name=client_name,
            neighborhood=neighborhood,
            address_short=address_short,
            piano_brand=piano_brand,
            piano_model=piano_model,
            piano_type=piano_type,
            last_visit_date=last_visit_date,
            days_since_last_visit=days_since_last_visit,
            action_items=action_items,
            is_new_client=False,  # TODO: Calculer
            has_alerts=False,  # TODO: Vérifier alertes
            priority="normal"
        )

    def _map_to_comfort_info(self, apt_raw: Dict[str, Any]) -> ComfortInfo:
        """
        Extrait informations "confort" depuis les notes et métadata.
        """
        client = apt_raw.get("client") or {}
        notes = apt_raw.get("notes") or ""

        # Parser les notes pour extraire infos confort
        # TODO: Améliorer avec NLP ou structure dédiée

        return ComfortInfo(
            access_code=None,  # TODO: Parser notes
            parking_info=None,
            floor_number=None,
            dog_name=None,  # TODO: Parser notes (regex pour "chien: X")
            cat_name=None,
            special_notes=notes if notes else None,
            preferred_tuning_hz=None,
            climate_sensitive=False,
            contact_phone=None,  # TODO: Ajouter depuis client
            contact_email=None
        )

    def _map_to_timeline_entry(self, entry_raw: Dict[str, Any]) -> TimelineEntry:
        """
        Transforme timeline entry V5 en schéma standard.
        """
        user = entry_raw.get("user") or {}
        first_name = user.get("first_name") or ""
        last_name = user.get("last_name") or ""
        technician = f"{first_name} {last_name}".strip() if (first_name or last_name) else None

        # Extraire température/humidité depuis details
        details = entry_raw.get("details") or ""
        temperature = self._extract_temperature(details)
        humidity = self._extract_humidity(details)

        return TimelineEntry(
            date=entry_raw.get("occurred_at", "")[:10],
            type=self._map_entry_type(entry_raw.get("entry_type")),
            technician=technician,
            summary=entry_raw.get("title") or "",
            details=details,
            temperature=temperature,
            humidity=humidity
        )

    def _generate_timeline_summary(self, entries: List[TimelineEntry]) -> str:
        """
        Génère un résumé textuel de l'historique.
        """
        if not entries:
            return "Aucun historique disponible pour ce piano."

        latest = entries[0]

        summary_parts = []

        # Dernière visite
        if latest.technician:
            summary_parts.append(f"Dernière visite le {latest.date} par {latest.technician}.")
        else:
            summary_parts.append(f"Dernière visite le {latest.date}.")

        # Mesures si disponibles
        if latest.temperature or latest.humidity:
            measures = []
            if latest.temperature:
                measures.append(f"{latest.temperature}°C")
            if latest.humidity:
                measures.append(f"{latest.humidity}%")
            summary_parts.append(f"Conditions: {', '.join(measures)}.")

        # Résumé du service
        if latest.summary:
            summary_parts.append(latest.summary)

        # Nombre total de services
        service_count = sum(1 for e in entries if e.type == "service")
        summary_parts.append(f"{service_count} services enregistrés.")

        return " ".join(summary_parts)

    # ============================================================
    # HELPER FUNCTIONS
    # ============================================================

    def _extract_action_items(self, notes: str) -> List[str]:
        """
        Extrait les action items depuis les notes.

        Cherche patterns comme:
        - "À apporter: X, Y, Z"
        - "TODO: X"
        - Liste à puces
        """
        if not notes:
            return []

        action_items = []

        # Pattern "À apporter:"
        match = re.search(r'à apporter[:\s]+([^\n]+)', notes, re.IGNORECASE)
        if match:
            items = match.group(1).split(',')
            action_items.extend([item.strip() for item in items if item.strip()])

        # Pattern "TODO:"
        todos = re.findall(r'todo[:\s]+([^\n]+)', notes, re.IGNORECASE)
        action_items.extend([todo.strip() for todo in todos])

        return action_items[:5]  # Limiter à 5 items

    def _extract_temperature(self, text: str) -> Optional[float]:
        """Extrait température depuis texte."""
        match = re.search(r'(\d+(?:\.\d+)?)\s*°\s*(?:C|Celsius)?', text, re.IGNORECASE)
        return float(match.group(1)) if match else None

    def _extract_humidity(self, text: str) -> Optional[float]:
        """Extrait humidité depuis texte."""
        match = re.search(r'(?:humidité|humidity)[^0-9]*(\d+(?:\.\d+)?)\s*%', text, re.IGNORECASE)
        if not match:
            # Fallback: chercher juste un nombre suivi de %
            match = re.search(r'(\d+(?:\.\d+)?)\s*%', text)
        return float(match.group(1)) if match else None

    def _map_entry_type(self, entry_type: str) -> str:
        """Map entry_type V5 vers type simplifié."""
        if not entry_type:
            return "note"

        type_lower = entry_type.lower()

        if "service" in type_lower:
            return "service"
        elif "measurement" in type_lower or "measure" in type_lower:
            return "measurement"
        else:
            return "note"
