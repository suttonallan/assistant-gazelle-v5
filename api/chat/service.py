"""
Service Chat Intelligent - Bridge V5/V6.

Architecture modulaire pour faciliter migration V6.
"""

from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta, time
import re
import pytz
import asyncio

from core.supabase_storage import SupabaseStorage
from modules.assistant import ConversationHandler
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

        # Conversation Handler pour questions avancées (Phase 1: Core handlers)
        self.conversation_handler = ConversationHandler(supabase_storage=self.storage)

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

        elif query_type == "departure_time":
            # Calculer heure de départ recommandée
            target_technician = parsed_params.get("requested_technician") or request.technician_id

            day_overview = self.data_provider.get_day_overview(
                date=parsed_params["date"],
                technician_id=target_technician,
                user_role=request.user_role
            )

            # Calculer heure de départ (premier RDV - temps trajet - préparation)
            recommended_time = self._calculate_departure_time(day_overview)

            return ChatResponse(
                interpreted_query=f"Heure de départ recommandée pour le {parsed_params['date']}",
                query_type="text_response",
                text_response=recommended_time,
                day_overview=day_overview,
                data_source=self.data_source
            )

        elif query_type == "total_distance":
            # Calculer distance totale de la journée
            target_technician = parsed_params.get("requested_technician") or request.technician_id

            day_overview = self.data_provider.get_day_overview(
                date=parsed_params["date"],
                technician_id=target_technician,
                user_role=request.user_role
            )

            # Calculer distance totale
            total_km = self._calculate_total_distance(day_overview)

            return ChatResponse(
                interpreted_query=f"Distance totale pour le {parsed_params['date']}",
                query_type="text_response",
                text_response=total_km,
                day_overview=day_overview,
                data_source=self.data_source
            )

        elif query_type == "search_client":
            # Recherche de client/contact
            search_results = self.data_provider.search_clients(
                search_term=parsed_params["search_term"]
            )

            return ChatResponse(
                interpreted_query=f"Recherche: {parsed_params['search_term']}",
                query_type="search_client",
                text_response=search_results,
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

        # Essayer de parser une date depuis la requête avec dateparser
        # Supporte: "demain", "la semaine prochaine", "le 15 janvier", "dans 3 jours", etc.
        try:
            import dateparser
            parsed_date = dateparser.parse(
                query,
                languages=['fr', 'en'],
                settings={
                    'PREFER_DATES_FROM': 'future',
                    'RELATIVE_BASE': datetime.now()
                }
            )
            if parsed_date:
                target_date = parsed_date.strftime("%Y-%m-%d")
                # Vérifier si la date parsée n'est pas trop loin dans le passé/futur (validation)
                days_diff = (parsed_date - datetime.now()).days
                if -7 <= days_diff <= 365:  # Entre 7 jours passés et 1 an futur
                    return ("day_overview", {"date": target_date, "requested_technician": requested_technician})
        except:
            pass  # Si dateparser n'est pas installé ou échoue, continuer avec patterns manuels

        # Fallback: Patterns manuels pour dates courantes
        if any(word in query_lower for word in ["demain", "tomorrow"]):
            target_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
            return ("day_overview", {"date": target_date, "requested_technician": requested_technician})

        if any(word in query_lower for word in ["aujourd'hui", "today", "ma journée"]):
            target_date = datetime.now().strftime("%Y-%m-%d")
            return ("day_overview", {"date": target_date, "requested_technician": requested_technician})

        # Questions de suivi (nécessitent contexte de la journée)
        if any(word in query_lower for word in ["heure de départ", "quand partir", "partir à quelle heure"]):
            target_date = date_override or datetime.now().strftime("%Y-%m-%d")
            return ("departure_time", {"date": target_date, "requested_technician": requested_technician})

        if any(word in query_lower for word in ["distance totale", "combien de km", "kilométrage"]):
            target_date = date_override or datetime.now().strftime("%Y-%m-%d")
            return ("total_distance", {"date": target_date, "requested_technician": requested_technician})

        # Recherche de client/contact
        # Ex: "client michelle", "cherche Yamaha", "contact sophie lambert"
        if any(word in query_lower for word in ["client", "contact", "cherche", "trouve", "recherche"]):
            # Extraire le terme de recherche (tout sauf les mots-clés)
            search_term = re.sub(r'\b(client|contact|cherche|trouve|recherche)\b', '', query_lower, flags=re.IGNORECASE).strip()
            if search_term:
                return ("search_client", {"search_term": search_term, "requested_technician": requested_technician})

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
        # Construire la requête avec le client Supabase (gère correctement les JOINs)
        query = self.storage.client.table('gazelle_appointments')\
            .select("""
                external_id,
                appointment_date,
                appointment_time,
                notes,
                technicien,
                title,
                description,
                location,
                client_external_id,
                client:client_external_id(
                    external_id,
                    company_name,
                    email,
                    phone,
                    city,
                    postal_code
                )
            """)\
            .eq('appointment_date', date)\
            .eq('status', 'ACTIVE')\
            .order('appointment_time')

        # Filtrage selon rôle ET technicien demandé
        if technician_id:
            # Si un technicien spécifique est demandé, filtrer par ce technicien
            # (même pour admin/assistant qui veulent voir "les rv de nicolas")
            query = query.eq('technicien', technician_id)
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

        # Exécuter la requête
        try:
            response = query.execute()
            appointments_raw = response.data
        except Exception as e:
            print(f"❌ Erreur requête appointments: {e}")
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

        # Transformer en AppointmentOverview
        appointments = []
        neighborhoods = set()

        for apt_raw in appointments_raw:
            # Filtrer événements selon type
            client = apt_raw.get("client")
            client_id = apt_raw.get("client_external_id")

            # Si client_external_id existe → c'est un RDV client (même si JOIN échoue)
            is_personal_event = client_id is None

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
            "select": "*,client:client_external_id(*)",
            "external_id": f"eq.{appointment_id}"
        }

        response = requests.get(url, headers=headers, params=params)

        if response.status_code != 200 or not response.json():
            raise ValueError(f"Appointment {appointment_id} not found")

        apt_raw = response.json()[0]

        # 2. Récupérer les pianos du CLIENT et leur timeline
        timeline_entries = []
        client = apt_raw.get("client")

        if client:
            client_id = client.get("external_id")

            # Récupérer les pianos de ce client
            pianos_url = f"{self.storage.api_url}/gazelle_pianos"
            pianos_params = {
                "select": "external_id,make,model,serial_number",
                "client_external_id": f"eq.{client_id}"
            }

            pianos_response = requests.get(pianos_url, headers=headers, params=pianos_params)

            # Récupérer la timeline du CLIENT (pas par piano individuel)
            # La plupart des timeline entries sont liées au client directement
            # Augmenter limite à 50 pour capturer vrais services (pas seulement emails)
            timeline_url = f"{self.storage.api_url}/gazelle_timeline_entries"

            # PostgREST: Filtrer pour garder SEULEMENT les vrais services
            # (pas les emails automatiques de type NOTE)
            timeline_params = {
                "select": "occurred_at,entry_type,title,description,entry_date,event_type,metadata",
                "client_external_id": f"eq.{client_id}",
                # Filtrer: garder SERVICE_ENTRY_MANUAL, APPOINTMENT, PIANO_MEASUREMENT
                "entry_type": "in.(SERVICE_ENTRY_MANUAL,APPOINTMENT,PIANO_MEASUREMENT)",
                "order": "occurred_at.desc",  # Utiliser occurred_at au lieu de entry_date
                "limit": 50
            }

            timeline_response = requests.get(timeline_url, headers=headers, params=timeline_params)

            if timeline_response.status_code == 200:
                timeline_raw = timeline_response.json()
                # Mapper toutes les entrées
                all_entries = [self._map_to_timeline_entry(entry) for entry in timeline_raw]

                # Filtrer les entrées inutiles (garder si summary OU details utiles)
                timeline_entries = [
                    entry for entry in all_entries
                    if self._is_useful_note(entry.summary) or self._is_useful_note(entry.details)
                ]

        # 3. Construire les objets
        overview = self._map_to_overview(apt_raw, apt_raw.get("appointment_date"))
        comfort = self._map_to_comfort_info(apt_raw)

        # Différencier événement personnel vs client
        is_personal_event = client is None
        event_data = {
            'title': apt_raw.get('title', ''),
            'location': apt_raw.get('location', ''),
            'description': apt_raw.get('description', '')
        } if is_personal_event else None

        timeline_summary = self._generate_timeline_summary(
            timeline_entries,
            is_personal_event=is_personal_event,
            event_data=event_data
        )

        # 4. Générer les résumés intelligents IA
        client_smart_summary = None
        piano_smart_summary = None

        if client and not is_personal_event:
            from .smart_summaries import SmartSummaryGenerator

            summary_generator = SmartSummaryGenerator(self.storage)

            # Résumé client
            comfort_dict = comfort.model_dump() if hasattr(comfort, 'model_dump') else comfort.dict()
            timeline_dict = [entry.model_dump() if hasattr(entry, 'model_dump') else entry.dict() for entry in timeline_entries]

            client_smart_summary = summary_generator.generate_client_summary(
                client_id=client.get("external_id"),
                timeline_entries=timeline_dict,
                comfort_info=comfort_dict
            )

            # Résumé piano (si piano principal dans appointment)
            piano_id = apt_raw.get("piano_external_id") or overview.piano_id
            if piano_id:
                # Récupérer infos piano
                piano_url = f"{self.storage.api_url}/gazelle_pianos"
                piano_params = {
                    "select": "make,model,year,has_dampp_chaser,type",
                    "external_id": f"eq.{piano_id}"
                }
                piano_response = requests.get(piano_url, headers=headers, params=piano_params)

                if piano_response.status_code == 200 and piano_response.json():
                    piano_info = piano_response.json()[0]

                    piano_smart_summary = summary_generator.generate_piano_summary(
                        piano_id=piano_id,
                        timeline_entries=timeline_dict,
                        piano_info=piano_info
                    )

        return AppointmentDetail(
            overview=overview,
            comfort=comfort,
            timeline_summary=timeline_summary,
            timeline_entries=timeline_entries,
            client_smart_summary=client_smart_summary,
            piano_smart_summary=piano_smart_summary,
            photos=[]  # TODO: Ajouter si photos disponibles
        )

    def search_clients(self, search_term: str, limit: int = 20) -> str:
        """
        Recherche des clients et contacts dans Supabase.

        Args:
            search_term: Terme de recherche
            limit: Nombre maximum de résultats

        Returns:
            Résumé textuel des résultats
        """
        import requests
        from urllib.parse import quote

        if not search_term:
            return "Aucun terme de recherche fourni."

        search_query = search_term.strip()
        search_pattern = f"*{search_query}*"

        try:
            headers = self.storage._get_headers()
            all_results = []
            seen_ids = set()

            # Recherche dans gazelle_clients sur plusieurs champs
            search_fields = ['name', 'company_name', 'full_name', 'email', 'city', 'postal_code']
            for field in search_fields:
                try:
                    clients_url = (
                        f"{self.storage.api_url}/gazelle_clients"
                        f"?select=external_id,name,company_name,full_name,email,phone,city,postal_code"
                        f"&{field}=ilike.{search_pattern}"
                        f"&limit={limit}"
                    )
                    clients_resp = requests.get(clients_url, headers=headers)
                    if clients_resp.status_code == 200:
                        for client in clients_resp.json():
                            client_id = client.get("external_id")
                            if client_id and client_id not in seen_ids:
                                client["_source"] = "client"
                                all_results.append(client)
                                seen_ids.add(client_id)
                except:
                    pass  # Ignore field errors

            # Recherche dans gazelle_contacts
            for field in ['name', 'full_name', 'email', 'city']:
                try:
                    contacts_url = (
                        f"{self.storage.api_url}/gazelle_contacts"
                        f"?select=external_id,name,full_name,email,phone,city,postal_code,client_external_id"
                        f"&{field}=ilike.{search_pattern}"
                        f"&limit={limit}"
                    )
                    contacts_resp = requests.get(contacts_url, headers=headers)
                    if contacts_resp.status_code == 200:
                        for contact in contacts_resp.json():
                            contact_id = contact.get("external_id")
                            if contact_id and contact_id not in seen_ids:
                                contact["_source"] = "contact"
                                all_results.append(contact)
                                seen_ids.add(contact_id)
                except:
                    pass  # Ignore field errors

            # Formatter les résultats
            if not all_results:
                return f"Aucun résultat trouvé pour '{search_term}'."

            # Compter rendez-vous pour chaque résultat
            result_lines = [f"Trouvé {len(all_results)} résultat(s) pour '{search_term}':\n"]

            for idx, result in enumerate(all_results[:10], 1):  # Limiter à 10 affichés
                name = result.get("full_name") or result.get("name", "Sans nom")
                source_type = result["_source"]
                external_id = result.get("external_id", "N/A")
                city = result.get("city", "")
                postal_code = result.get("postal_code", "")

                # Chercher le nombre de RDV
                appointments_url = (
                    f"{self.storage.api_url}/gazelle_appointments"
                    f"?select=external_id"
                )

                if source_type == "client":
                    appointments_url += f"&client_id=eq.{external_id}"
                else:
                    # Pour contact, chercher via client_external_id
                    client_id = result.get("client_external_id")
                    if client_id:
                        appointments_url += f"&client_id=eq.{client_id}"
                    else:
                        continue  # Skip si pas de client lié

                appointments_resp = requests.get(appointments_url, headers=headers)
                rdv_count = len(appointments_resp.json()) if appointments_resp.status_code == 200 else 0

                location = f"{city} {postal_code}".strip() if city or postal_code else "Lieu inconnu"
                result_lines.append(
                    f"{idx}. {name} ({source_type}) - {location} - {rdv_count} RDV"
                )

            return "\n".join(result_lines)

        except Exception as e:
            return f"Erreur lors de la recherche: {str(e)}"

    # ============================================================
    # MAPPING FUNCTIONS (V5 → Standard Schema)
    # ============================================================

    def _is_useful_note(self, text: str) -> bool:
        """
        Détermine si une note est utile à afficher.

        Filtre les notes automatiques Gazelle sans valeur pour le technicien.

        Args:
            text: Texte de la note

        Returns:
            True si la note est utile, False sinon
        """
        if not text or not text.strip():
            return False

        text_lower = text.lower().strip()

        # Patterns de notes inutiles (auto-générées par Gazelle)
        useless_patterns = [
            "note gazelle",
            "an appointment was created",
            "a new appointment was created",
            "appointment was completed",
            "appointment for this client was completed"
        ]

        # Si la note contient un de ces patterns, elle est inutile
        for pattern in useless_patterns:
            if pattern in text_lower:
                return False

        # Si la note est très courte (< 10 chars), probablement inutile
        if len(text.strip()) < 10:
            return False

        return True

    def _extract_contact_name(self, notes: str, location: str) -> Optional[str]:
        """
        Extrait le nom du contact (personne physique) depuis notes ou location.

        Pattern: Cherche "Prénom Nom" au début des notes ou dans location.
        Exemples:
            "Sophie Lambert, Piano Kawai..." → "Sophie Lambert"
            "Contact: Jean Tremblay" → "Jean Tremblay"

        Args:
            notes: Champ notes du rendez-vous
            location: Champ location du rendez-vous

        Returns:
            Nom du contact ou None si non trouvé
        """
        import re

        # Pattern: Prénom Nom (2 mots capitalisés)
        # Ex: "Sophie Lambert", "Jean-Pierre Tremblay"
        contact_pattern = r'\b([A-Z][a-zé]+(?:-[A-Z][a-zé]+)?)\s+([A-Z][a-zé]+(?:-[A-Z][a-zé]+)?)\b'

        # Chercher dans notes en premier
        text_to_search = notes or location or ""

        match = re.search(contact_pattern, text_to_search)
        if match:
            first_name = match.group(1)
            last_name = match.group(2)
            return f"{first_name} {last_name}"

        return None

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

        # Piano: récupérer depuis le client (pas de piano_external_id dans appointments)
        piano = {}
        if client and client.get("external_id"):
            # Récupérer le(s) piano(s) du client
            try:
                client_id = client.get("external_id")
                pianos_result = self.storage.client.table('gazelle_pianos')\
                    .select('external_id,make,model,type,dampp_chaser_installed')\
                    .eq('client_external_id', client_id)\
                    .limit(1)\
                    .execute()

                if pianos_result.data:
                    piano = pianos_result.data[0]
                    # Debug log pour vérifier
                    if piano.get('dampp_chaser_installed'):
                        print(f"✅ PLS détecté pour client {client_id}: {piano.get('make')} {piano.get('model')}")
                else:
                    print(f"⚠️  Aucun piano trouvé pour client {client_id}")
            except Exception as e:
                print(f"❌ Erreur récupération piano pour client {client.get('external_id')}: {e}")
                import traceback
                traceback.print_exc()
                piano = {}
        else:
            # Debug: pourquoi pas de client?
            if not client:
                print(f"⚠️  Pas de client pour appointment {apt_raw.get('external_id')}")
            elif not client.get("external_id"):
                print(f"⚠️  Client sans external_id: {client}")
            piano = apt_raw.get("piano") or {}

        # Time slot - Les données sont maintenant stockées en Eastern Time (pas UTC)
        time_raw = apt_raw.get("appointment_time")
        if time_raw:
            # Extraire juste HH:MM
            hour, minute = time_raw.split(":")[:2]
            time_slot = f"{hour}:{minute}"
        else:
            time_slot = "Non spécifié"

        # Client info (ou titre si événement personnel)
        title = apt_raw.get("title") or ""
        description = apt_raw.get("description") or ""
        notes = apt_raw.get("notes") or ""
        location = apt_raw.get("location") or ""

        # Extraction du nom du contact (personne physique) depuis notes/location
        # Pattern: Chercher un nom propre (Prénom Nom) au début des notes ou location
        contact_name = self._extract_contact_name(notes, location)

        # Client name (institution/entreprise)
        institution_name = client.get("company_name") if client else None

        # Logique d'affichage:
        # 1. Si contact trouvé: afficher contact (institution en secondaire)
        # 2. Sinon: afficher institution ou titre
        if contact_name and institution_name and contact_name != institution_name:
            # Cas: Contact différent du client (ex: Sophie Lambert chez SEC-Cibèle)
            client_name = contact_name
        elif institution_name:
            # Cas: Pas de contact trouvé, afficher institution
            client_name = institution_name
        else:
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
        has_dampp_chaser = piano.get("dampp_chaser_installed", False)

        # Action items (extraire des notes)
        notes = apt_raw.get("notes") or ""
        action_items = self._extract_action_items(notes)

        # TODO: Calculer last_visit_date depuis timeline
        last_visit_date = None
        days_since_last_visit = None

        # Billing client: afficher seulement si différent du contact
        billing_client = None
        if contact_name and institution_name and contact_name != institution_name:
            billing_client = institution_name

        return AppointmentOverview(
            appointment_id=apt_raw.get("external_id"),
            client_id=client.get("external_id") if client else None,
            piano_id=piano.get("external_id") if piano else None,
            time_slot=time_slot,
            date=date,
            client_name=client_name,
            billing_client=billing_client,
            neighborhood=neighborhood,
            address_short=address_short,
            piano_brand=piano_brand,
            piano_model=piano_model,
            piano_type=piano_type,
            has_dampp_chaser=has_dampp_chaser,
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

        Parsing intelligent pour:
        - Animaux (chien, chat)
        - Codes d'accès
        - Stationnement
        - Étage
        - Langue du client
        - Préférences accordage
        - Choses à surveiller
        """
        client = apt_raw.get("client") or {}
        notes = apt_raw.get("notes") or ""
        notes_lower = notes.lower()

        # === ANIMAUX ===
        dog_name = self._extract_dog_name(notes)
        dog_breed = self._extract_dog_breed(notes)
        cat_name = self._extract_cat_name(notes)

        # === CODE D'ACCÈS ===
        access_code = self._extract_access_code(notes)

        # === INSTRUCTIONS D'ACCÈS DÉTAILLÉES ===
        access_instructions = self._extract_access_instructions(notes)

        # === STATIONNEMENT ===
        parking_info = self._extract_parking_info(notes)

        # === ÉTAGE ===
        floor_number = self._extract_floor_number(notes)

        # === TÉLÉPHONE ===
        contact_phone = client.get("phone")

        # === EMAIL ===
        contact_email = client.get("email")

        # === PRÉFÉRENCES ACCORDAGE ===
        preferred_tuning_hz = self._extract_tuning_preference(notes)

        # === PIANO SENSIBLE CLIMAT ===
        climate_sensitive = any(kw in notes_lower for kw in [
            "sensible", "humidité", "température", "dampp", "pls", "piano life saver"
        ])

        # === NOTES SPÉCIALES (Choses à surveiller) ===
        # Filtrer et extraire seulement les infos importantes
        special_notes = self._extract_special_notes(notes)
        
        # === PRÉFÉRENCE LINGUISTIQUE ===
        preferred_language = self._extract_language_preference(notes)
        
        # === TEMPÉRAMENT ===
        temperament = self._extract_temperament(notes)

        return ComfortInfo(
            contact_name=client.get("first_name") or client.get("company_name"),
            contact_phone=contact_phone,
            contact_email=contact_email,
            access_code=access_code,
            access_instructions=access_instructions,
            parking_info=parking_info,
            floor_number=floor_number,
            dog_name=dog_name,
            dog_breed=dog_breed,
            cat_name=cat_name,
            special_notes=special_notes,
            preferred_tuning_hz=preferred_tuning_hz,
            climate_sensitive=climate_sensitive,
            preferred_language=preferred_language,
            temperament=temperament
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

        # Utiliser entry_date si disponible, sinon occurred_at
        date_field = entry_raw.get("entry_date") or entry_raw.get("occurred_at", "")
        date_str = date_field[:10] if date_field else ""

        # Utiliser description si disponible, sinon details
        details = entry_raw.get("description") or entry_raw.get("details") or ""

        return TimelineEntry(
            date=date_str,
            type=self._map_entry_type(entry_raw.get("entry_type") or entry_raw.get("event_type")),
            technician=technician,
            summary=entry_raw.get("title") or "",
            details=details,
            temperature=self._extract_temperature(details),
            humidity=self._extract_humidity(details)
        )

    def _generate_timeline_summary(self, entries: List[TimelineEntry], client_data: Dict[str, Any] = None, is_personal_event: bool = False, event_data: Dict[str, Any] = None) -> str:
        """
        Génère un résumé SIMPLIFIÉ de l'historique.

        NOTE: L'ancienneté et la fréquence sont maintenant dans le "Résumé Intelligent IA",
        donc on se concentre ici sur:
        - Dernière visite avec détails importants
        - ALERTES: Paiements lents, conditions anormales, problèmes récurrents

        Format: Texte narratif pour le technicien, pas une liste.
        """
        if not entries:
            if is_personal_event and event_data:
                # Détecter événements spéciaux (Vincent d'Indy, etc.)
                title = event_data.get('title', '').lower()
                location = event_data.get('location', '').lower()
                description = event_data.get('description', '').lower()

                # Vincent d'Indy
                if 'vd' in title or 'vincent' in title or 'indy' in title or \
                   'vincent' in location or 'indy' in location or \
                   'vincent' in description or 'indy' in description:
                    return "📍 Événement à Vincent d'Indy. Consultez le volet Vincent d'Indy pour voir les demandes en cours."

                # Autres événements de travail
                return "Événement personnel (pas de client associé)"
            return "Aucun historique disponible pour ce client."

        from datetime import datetime
        from dateutil import parser

        latest = entries[0]
        summary_parts = []
        alerts = []  # Alertes importantes à afficher EN PREMIER

        # DERNIÈRE VISITE - Infos importantes
        if latest.technician:
            summary_parts.append(f"Dernière visite: {latest.date} par {latest.technician}.")
        else:
            summary_parts.append(f"Dernière visite: {latest.date}.")

        # 3. ALERTES ENVIRONNEMENTALES - Conditions anormales
        if latest.temperature or latest.humidity:
            measures = []
            temp_alert = False
            humidity_alert = False

            if latest.temperature:
                temp = latest.temperature
                measures.append(f"{temp}°C")
                # Alerte si température anormale (< 18°C ou > 26°C)
                if temp < 18 or temp > 26:
                    temp_alert = True

            if latest.humidity:
                hum = latest.humidity
                measures.append(f"{hum}%")
                # Alerte si humidité anormale (< 30% ou > 60%)
                if hum < 30 or hum > 60:
                    humidity_alert = True

            if temp_alert or humidity_alert:
                alerts.append(f"🌡️ ALERTE CLIMAT: {', '.join(measures)} - Conditions hors norme!")
            else:
                summary_parts.append(f"Conditions: {', '.join(measures)}.")

        # 4. ALERTES PAIEMENT - Analyser les notes de paiement
        payment_keywords = ["paiement", "payer", "facture", "impayé", "solde", "argent", "chèque"]
        slow_payment_keywords = ["lent à payer", "retard", "relance", "rappel", "pas encore payé"]

        for entry in entries[:5]:  # Chercher dans les 5 dernières entrées
            details_lower = (entry.details or "").lower()
            summary_lower = (entry.summary or "").lower()
            text_lower = details_lower + " " + summary_lower

            # Chercher mentions de paiement lent
            if any(kw in text_lower for kw in slow_payment_keywords):
                alerts.append("💰 ALERTE PAIEMENT: Client lent à payer - Demander paiement sur le champ!")
                break

        # 5. NOTES IMPORTANTES - Chercher "à faire", "prochaine fois", "apporter"
        action_keywords = ["à faire", "prochaine fois", "apporter", "prévoir", "rappel"]
        for entry in entries[:3]:  # Chercher dans les 3 dernières entrées
            details_lower = (entry.details or "").lower()
            summary_lower = (entry.summary or "").lower()

            # Chercher si contient un keyword d'action
            for keyword in action_keywords:
                if keyword in details_lower or keyword in summary_lower:
                    # Extraire SEULEMENT la phrase pertinente (pas tout le texte)
                    text = entry.details or entry.summary or ""

                    # Chercher phrase entre parenthèses ou après keyword
                    import re

                    # Pattern 1: Texte entre parenthèses contenant keyword
                    paren_pattern = r'\([^)]*(?:' + '|'.join(action_keywords) + r')[^)]*\)'
                    paren_matches = re.findall(paren_pattern, text, re.IGNORECASE)
                    if paren_matches:
                        clean_note = paren_matches[0].strip('()').strip()
                        summary_parts.append(f"📝 {clean_note}")
                        break

                    # Pattern 2: Phrase complète contenant keyword (jusqu'au point)
                    for sentence in text.split('.'):
                        if any(kw in sentence.lower() for kw in action_keywords):
                            # Nettoyer la phrase
                            clean_sentence = sentence.strip('- ').strip()
                            # Limiter à 100 caractères
                            if 10 < len(clean_sentence) <= 100:
                                summary_parts.append(f"📝 {clean_sentence}")
                                break
                    break  # Une seule note importante

        # 6. ALERTES TECHNIQUES - Problèmes récurrents
        problem_keywords = ["problème", "casse", "défaut", "attention", "fragile", "sensible", "urgent"]
        for entry in entries[:3]:
            details_lower = (entry.details or "").lower()
            summary_lower = (entry.summary or "").lower()
            text_lower = details_lower + " " + summary_lower

            if any(kw in text_lower for kw in problem_keywords):
                # Extraire la phrase de problème
                text = entry.details or entry.summary or ""
                for line in text.split('\n'):
                    if any(kw in line.lower() for kw in problem_keywords):
                        clean_line = line.strip('- ').strip()
                        if len(clean_line) > 10:
                            alerts.append(f"⚠️ ATTENTION: {clean_line}")
                            break
                break

        # 7. RÉSUMÉ TECHNIQUE - Si pertinent
        if latest.summary and len(latest.summary) > 20:
            # Tronquer si trop long (garder essentiel)
            summary_text = latest.summary[:150] + "..." if len(latest.summary) > 150 else latest.summary
            summary_parts.append(f"Travail: {summary_text}")

        # ASSEMBLAGE FINAL: Alertes EN PREMIER, puis résumé normal
        final_parts = alerts + summary_parts
        return " ".join(final_parts)

    # ============================================================
    # HELPER FUNCTIONS
    # ============================================================

    def _extract_action_items(self, notes: str) -> List[str]:
        """
        Extrait les action items depuis les notes.

        Cherche patterns comme:
        - "À apporter: X, Y, Z"
        - "Buvards bouteille" (nom d'objet à la fin)
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

        # Pattern: dernière ligne (objets à apporter)
        # Ex: "Buvards bouteille", "Cordes #3", etc.
        lines = notes.strip().split('\n')
        if lines:
            last_line = lines[-1].strip()
            # Si la dernière ligne est courte (< 30 chars) et pas une phrase complète
            if last_line and len(last_line) < 30 and not last_line.endswith('.'):
                # Vérifier que ce n'est pas déjà capturé
                if last_line not in action_items:
                    action_items.append(f"À apporter: {last_line}")

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

    def _calculate_departure_time(self, day_overview: DayOverview) -> str:
        """
        Calcule l'heure de départ recommandée.

        Formule: Premier RDV - Temps de trajet - Temps de préparation

        Assumptions:
        - Base: Montréal (coordonnées Piano-Tek)
        - Temps de préparation: 15 minutes
        - Temps de trajet: estimation basée sur le premier quartier
        """
        if not day_overview.appointments:
            return "Aucun rendez-vous pour cette journée."

        first_apt = day_overview.appointments[0]
        first_time_str = first_apt.time_slot  # Format "HH:MM"

        try:
            # Parser l'heure du premier RDV
            hour, minute = map(int, first_time_str.split(":"))
            from datetime import datetime, timedelta

            # Créer un datetime pour aujourd'hui à cette heure
            first_apt_time = datetime.now().replace(hour=hour, minute=minute, second=0, microsecond=0)

            # Estimer temps de trajet basé sur le quartier
            # TODO: Utiliser l'API de distance réelle
            neighborhood = first_apt.neighborhood.lower()
            if any(word in neighborhood for word in ["plateau", "mile-end", "rosemont"]):
                travel_minutes = 20
            elif any(word in neighborhood for word in ["laval", "longueuil", "brossard"]):
                travel_minutes = 30
            elif any(word in neighborhood for word in ["rive-sud", "rive-nord"]):
                travel_minutes = 40
            else:
                travel_minutes = 25  # Défaut: 25 minutes

            # Ajouter temps de préparation
            prep_minutes = 15

            # Calculer heure de départ
            departure_time = first_apt_time - timedelta(minutes=travel_minutes + prep_minutes)

            return (
                f"Heure de départ recommandée: {departure_time.strftime('%H:%M')}\n\n"
                f"Premier rendez-vous à {first_time_str} ({first_apt.client_name} - {first_apt.neighborhood})\n"
                f"Temps de trajet estimé: {travel_minutes} min\n"
                f"Temps de préparation: {prep_minutes} min"
            )

        except Exception as e:
            return f"Impossible de calculer l'heure de départ: {str(e)}"

    def _calculate_total_distance(self, day_overview: DayOverview) -> str:
        """
        Calcule la distance totale de la journée.

        TODO: Intégrer avec l'API Google Maps pour distances réelles.
        Pour l'instant, estimation basée sur le nombre de quartiers différents.
        """
        if not day_overview.appointments:
            return "Aucun rendez-vous pour cette journée."

        # Compter les quartiers uniques
        neighborhoods_set = set()
        for apt in day_overview.appointments:
            if apt.neighborhood:
                neighborhoods_set.add(apt.neighborhood)

        num_neighborhoods = len(neighborhoods_set)
        num_appointments = len(day_overview.appointments)

        # Estimation grossière:
        # - Base → Premier quartier: ~20km
        # - Entre quartiers: ~15km par quartier
        # - Retour à la base: ~20km

        if num_neighborhoods == 1:
            # Tous les RDV dans le même quartier
            estimated_km = 20 + (num_appointments * 2) + 20  # Base + déplacements locaux + retour
        else:
            # Plusieurs quartiers
            estimated_km = 20 + (num_neighborhoods * 15) + (num_appointments * 3) + 20

        return (
            f"Distance totale estimée: ~{estimated_km} km\n\n"
            f"Rendez-vous: {num_appointments}\n"
            f"Quartiers différents: {num_neighborhoods}\n"
            f"Quartiers: {', '.join(sorted(neighborhoods_set))}\n\n"
            f"⚠️ Note: Estimation basée sur le nombre de quartiers. "
            f"Pour une distance précise, utiliser Google Maps."
        )

    # ============================================================
    # PARSING INFOS CONFORT (Extraction intelligente des notes)
    # ============================================================

    def _extract_dog_name(self, notes: str) -> Optional[str]:
        """Extrait le nom du chien depuis les notes."""
        import re
        patterns = [
            r'chien[:\s]+([A-Z][a-zéèêàâ]+)',
            r'dog[:\s]+([A-Z][a-z]+)',
            r'🐕[:\s]*([A-Z][a-zéèêàâ]+)',
        ]
        for pattern in patterns:
            match = re.search(pattern, notes, re.IGNORECASE)
            if match:
                return match.group(1).capitalize()
        return None

    def _extract_dog_breed(self, notes: str) -> Optional[str]:
        """Extrait la race du chien."""
        import re
        # Pattern: "(Labrador)", "(Golden Retriever)"
        match = re.search(r'chien[:\s]+[A-Z][a-zéèêàâ]+\s*\(([^)]+)\)', notes, re.IGNORECASE)
        if match:
            return match.group(1)
        return None

    def _extract_cat_name(self, notes: str) -> Optional[str]:
        """Extrait le nom du chat."""
        import re
        patterns = [
            r'chat[:\s]+([A-Z][a-zéèêàâ]+)',
            r'cat[:\s]+([A-Z][a-z]+)',
            r'🐱[:\s]*([A-Z][a-zéèêàâ]+)',
        ]
        for pattern in patterns:
            match = re.search(pattern, notes, re.IGNORECASE)
            if match:
                return match.group(1).capitalize()
        return None

    def _extract_access_code(self, notes: str) -> Optional[str]:
        """Extrait le code d'accès (porte, interphone)."""
        import re
        patterns = [
            r'code[:\s]+([0-9#*]+)',
            r'interphone[:\s]+([0-9#*]+)',
            r'porte[:\s]+([0-9#*]+)',
            r'accès[:\s]+([0-9#*]+)',
            r'#([0-9]{3,6})',  # Code seul (ex: #1234)
        ]
        for pattern in patterns:
            match = re.search(pattern, notes, re.IGNORECASE)
            if match:
                return match.group(1)
        return None

    def _extract_access_instructions(self, notes: str) -> Optional[str]:
        """Extrait instructions d'accès détaillées."""
        import re
        # Chercher lignes avec "accès", "entrer", "porte", etc.
        lines = notes.split('\n')
        instructions = []
        keywords = ['accès', 'entrer', 'porte', 'escalier', 'ascenseur', 'sonner', 'code']

        for line in lines:
            if any(kw in line.lower() for kw in keywords) and len(line.strip()) > 15:
                clean = line.strip('- ').strip()
                if clean not in instructions:
                    instructions.append(clean)

        return ' '.join(instructions[:3]) if instructions else None  # Max 3 lignes

    def _extract_parking_info(self, notes: str) -> Optional[str]:
        """Extrait infos de stationnement."""
        import re
        # Chercher lignes avec "parking", "stationner", "garer"
        lines = notes.split('\n')
        for line in lines:
            if any(kw in line.lower() for kw in ['parking', 'stationner', 'garer', 'stationnement']):
                return line.strip('- ').strip()
        return None

    def _extract_floor_number(self, notes: str) -> Optional[str]:
        """Extrait le numéro d'étage."""
        import re
        patterns = [
            r'étage[:\s]+([0-9]+)',
            r'([0-9]+)e?\s+étage',
            r'floor[:\s]+([0-9]+)',
        ]
        for pattern in patterns:
            match = re.search(pattern, notes, re.IGNORECASE)
            if match:
                return match.group(1)
        return None

    def _extract_tuning_preference(self, notes: str) -> Optional[int]:
        """Extrait préférence d'accordage (Hz)."""
        import re
        patterns = [
            r'accord[:\s]+([0-9]{3})\s*hz',
            r'([0-9]{3})\s*hz',
            r'préf[éeè]rence[:\s]+([0-9]{3})',
        ]
        for pattern in patterns:
            match = re.search(pattern, notes, re.IGNORECASE)
            if match:
                hz = int(match.group(1))
                if 435 <= hz <= 445:  # Validation range
                    return hz
        return None

    def _extract_special_notes(self, notes: str) -> Optional[str]:
        """
        Extrait notes spéciales (choses à surveiller).

        Filtre pour garder seulement:
        - Alertes (attention, fragile, problème)
        - Instructions techniques importantes
        - Préférences spéciales du client
        """
        import re
        # Filtrer d'abord si note utile
        if not self._is_useful_note(notes):
            return None

        # Chercher lignes avec keywords importants
        lines = notes.split('\n')
        important_lines = []
        keywords = [
            'attention', 'fragile', 'problème', 'surveiller', 'important',
            'préférence', 'langue', 'anglais', 'français', 'sensible'
        ]

        for line in lines:
            line_clean = line.strip('- ').strip()
            if len(line_clean) < 10:  # Trop court
                continue

            if any(kw in line.lower() for kw in keywords):
                important_lines.append(line_clean)

        # Si aucune ligne importante, retourner toute la note (déjà filtrée)
        if not important_lines:
            return notes if len(notes) < 200 else notes[:200] + "..."

        # Sinon retourner les lignes importantes
        result = ' | '.join(important_lines[:3])  # Max 3 lignes
        return result if len(result) < 250 else result[:250] + "..."

    def _extract_language_preference(self, notes: str) -> Optional[str]:
        """Extrait la langue préférée du client."""
        import re
        notes_lower = notes.lower()

        # Patterns explicites
        if re.search(r'anglais\s+(seulement|uniquement|only)', notes_lower):
            return "Anglais"
        if re.search(r'fran[cç]ais\s+(seulement|uniquement|only)', notes_lower):
            return "Français"
        if 'bilingue' in notes_lower:
            return "Bilingue"

        # Patterns implicites
        if 'english' in notes_lower or 'speaks english' in notes_lower:
            return "Anglais"
        if 'parle français' in notes_lower or 'francophone' in notes_lower:
            return "Français"

        return None

    def _extract_temperament(self, notes: str) -> Optional[str]:
        """Extrait le tempérament du client depuis les notes."""
        import re
        notes_lower = notes.lower()

        # Patterns pour différents tempéraments
        if any(kw in notes_lower for kw in ['sympathique', 'gentil', 'agréable', 'chaleureux']):
            return "Sympathique"
        if any(kw in notes_lower for kw in ['exigeant', 'difficile', 'pointilleux', 'perfectionniste']):
            return "Exigeant"
        if any(kw in notes_lower for kw in ['réservé', 'discret', 'calme', 'timide']):
            return "Réservé"

        return None
