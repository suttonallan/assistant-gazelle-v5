"""
ConversationHandler - Gestion intelligente des questions de l'assistant conversationnel.

Architecture basée sur TYPES_QUESTIONS_ASSISTANT_CONVERSATIONNEL.md
Phase 1: Core handlers (client_search, client_summary, my_appointments, piano_search)
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import os
import json
import re
from anthropic import Anthropic
from supabase import Client

from core.supabase_storage import SupabaseStorage


class ConversationHandler:
    """
    Handler principal pour traiter les questions conversationnelles.

    Utilise Claude Haiku pour:
    1. Détecter l'intention de la requête
    2. Extraire les entités (noms, dates, numéros)
    3. Générer des réponses structurées
    """

    def __init__(self, supabase_storage: Optional[SupabaseStorage] = None):
        """
        Args:
            supabase_storage: Instance de SupabaseStorage. Si None, en crée une.
        """
        self.storage = supabase_storage or SupabaseStorage()
        self.supabase: Client = self.storage.client

        # Anthropic client (optionnel - le backend peut démarrer sans)
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if api_key:
            self.anthropic = Anthropic(api_key=api_key)
        else:
            self.anthropic = None
            print("⚠️  ANTHROPIC_API_KEY non trouvée - les fonctionnalités de chat IA seront désactivées")

    async def process_query(self, query: str, user_id: str, user_role: str = "technician") -> Dict[str, Any]:
        """
        Point d'entrée principal pour traiter une question.

        Args:
            query: Question de l'utilisateur (ex: "client Daniel Markwell")
            user_id: ID de l'utilisateur (pour contexte)
            user_role: Rôle de l'utilisateur (technician, admin, etc.)

        Returns:
            Dict avec type, data, et formatted_response
        """
        # 1. Détecter l'intention
        intent = await self.detect_intent(query)

        # 2. Router vers le bon handler
        handlers = {
            # Phase 1: Core
            'client_search': self.handle_client_search,
            'client_summary': self.handle_client_summary,
            'my_appointments': self.handle_my_appointments,
            'piano_search': self.handle_piano_search,
            # Phase 2: Advanced
            'client_history': self.handle_client_history,
            'search_notes': self.handle_search_notes,
            'humidity_readings': self.handle_humidity_readings,
            'unpaid_invoices': self.handle_unpaid_invoices,
        }

        handler = handlers.get(intent['type'], self.handle_generic)
        return await handler(query, intent, user_id, user_role)

    async def detect_intent(self, query: str) -> Dict[str, Any]:
        """
        Utilise OpenAI pour détecter l'intention de la requête.

        Returns:
            {
                "type": "client_search" | "client_summary" | "my_appointments" | "piano_search",
                "entities": {
                    "client_name": str,
                    "date_range": {"start": str, "end": str},
                    "piano_serial": str,
                    "technician_name": str
                }
            }
        """
        response = self.anthropic.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1000,
            system="""Tu es un système de détection d'intention pour un assistant de techniciens de piano.

Détecte l'intention et extrais les entités.

Types d'intention possibles (Phase 1 + 2):

Phase 1 - Core:
- client_search: Recherche d'un client par nom (ex: "client Daniel Markwell", "qui est Anne-Marie")
- client_summary: Résumé complet d'un client (ex: "résumé pour Vincent-d'Indy", "donne-moi tout sur ce client")
- my_appointments: Rendez-vous du technicien actuel (ex: "mes rendez-vous aujourd'hui", "qu'est-ce que j'ai demain")
- piano_search: Recherche de piano par numéro de série (ex: "piano 1234567", "info sur série 7654321")

Phase 2 - Advanced:
- client_history: Historique d'interventions (ex: "interventions 2024 pour Vincent-d'Indy", "historique récent")
- search_notes: Recherche dans notes (ex: "trouve 'faux battements'", "recherche 'pédale'")
- humidity_readings: Mesures d'humidité (ex: "taux d'humidité de ce piano", "mesures humidité 2024")
- unpaid_invoices: Factures impayées (ex: "factures non payées", "créances en souffrance")

Retourne UNIQUEMENT un JSON valide (pas de texte avant/après):
{
    "type": "client_search" | "client_summary" | "my_appointments" | "piano_search" | "client_history" | "search_notes" | "humidity_readings" | "unpaid_invoices",
    "entities": {
        "client_name": "nom du client si mentionné",
        "date_range": {"start": "YYYY-MM-DD", "end": "YYYY-MM-DD"} si dates mentionnées,
        "piano_serial": "numéro de série si mentionné",
        "technician_name": "nom du technicien si mentionné",
        "search_term": "terme de recherche pour search_notes (entre guillemets)"
    },
    "confidence": 0.0-1.0
}

Pour les dates relatives:
- "aujourd'hui" → date du jour
- "demain" → lendemain
- "cette semaine" → lundi à dimanche de la semaine actuelle""",
            messages=[
                {"role": "user", "content": query}
            ]
        )

        raw_content = response.content[0].text.strip()
        if raw_content.startswith("```"):
            raw_content = re.sub(r'^```(?:json)?\s*', '', raw_content)
            raw_content = re.sub(r'\s*```$', '', raw_content)
        return json.loads(raw_content)

    # ============================================================================
    # PHASE 1: CORE HANDLERS
    # ============================================================================

    async def handle_client_search(
        self,
        query: str,
        intent: Dict[str, Any],
        user_id: str,
        user_role: str
    ) -> Dict[str, Any]:
        """
        Recherche de client par nom.

        Query Supabase:
        1. Chercher dans gazelle_contacts (personnes)
        2. Chercher dans gazelle_clients (entreprises)
        3. Retourner client + contacts + pianos
        """
        client_name = intent['entities'].get('client_name', '')

        if not client_name:
            return {
                "type": "error",
                "message": "Aucun nom de client détecté dans la requête"
            }

        # 1. Chercher dans contacts (personnes)
        contacts_result = self.supabase.table('gazelle_contacts')\
            .select('*, client:gazelle_clients(*)')\
            .ilike('full_name', f'%{client_name}%')\
            .execute()

        # 2. Chercher dans clients (entreprises)
        clients_result = self.supabase.table('gazelle_clients')\
            .select('*, contacts:gazelle_contacts(*), pianos:gazelle_pianos(*)')\
            .ilike('company_name', f'%{client_name}%')\
            .execute()

        # Combiner résultats
        clients = clients_result.data if clients_result.data else []

        # Ajouter clients trouvés via contacts
        if contacts_result.data:
            for contact in contacts_result.data:
                if contact.get('client'):
                    client_id = contact['client']['id']
                    # Vérifier si déjà dans la liste
                    if not any(c['id'] == client_id for c in clients):
                        # Récupérer le client complet
                        full_client = self.supabase.table('gazelle_clients')\
                            .select('*, contacts:gazelle_contacts(*), pianos:gazelle_pianos(*)')\
                            .eq('id', client_id)\
                            .single()\
                            .execute()
                        if full_client.data:
                            clients.append(full_client.data)

        if not clients:
            return {
                "type": "not_found",
                "query": query,
                "message": f"Aucun client trouvé pour '{client_name}'"
            }

        # Formater la réponse
        formatted = await self._format_client_search_results(clients)

        return {
            "type": "client_search",
            "query": query,
            "clients": clients,
            "formatted_response": formatted
        }

    async def handle_client_summary(
        self,
        query: str,
        intent: Dict[str, Any],
        user_id: str,
        user_role: str
    ) -> Dict[str, Any]:
        """
        Génère un résumé complet d'un client.

        Données nécessaires:
        - Client + Contacts + Pianos
        - Timeline entries (50 dernières)
        - Prochain rendez-vous
        """
        client_name = intent['entities'].get('client_name', '')

        if not client_name:
            return {
                "type": "error",
                "message": "Aucun nom de client détecté"
            }

        # 1. Chercher le client
        client_result = self.supabase.table('gazelle_clients')\
            .select('''
                *,
                contacts:gazelle_contacts(*),
                pianos:gazelle_pianos(*)
            ''')\
            .ilike('company_name', f'%{client_name}%')\
            .limit(1)\
            .execute()

        if not client_result.data:
            return {
                "type": "not_found",
                "message": f"Client '{client_name}' non trouvé"
            }

        client = client_result.data[0]
        piano_ids = [p['id'] for p in client.get('pianos', [])]

        # 2. Récupérer timeline entries pour les pianos de ce client
        timeline_data = []
        if piano_ids:
            timeline_result = self.supabase.table('gazelle_timeline_entries')\
                .select('''
                    *,
                    piano:gazelle_pianos(make, model, serial_number),
                    user:users(full_name)
                ''')\
                .in_('piano_id', piano_ids)\
                .order('occurred_at', desc=True)\
                .limit(50)\
                .execute()

            timeline_data = timeline_result.data if timeline_result.data else []

        # 3. Prochain rendez-vous
        next_appointment = None
        if piano_ids:
            appt_result = self.supabase.table('gazelle_appointments')\
                .select('*, piano:gazelle_pianos(make, model)')\
                .in_('piano_id', piano_ids)\
                .eq('status', 'ACTIVE')\
                .gte('appointment_date', datetime.now().strftime('%Y-%m-%d'))\
                .order('appointment_date')\
                .limit(1)\
                .execute()

            if appt_result.data:
                next_appointment = appt_result.data[0]

        # 4. Générer résumé structuré avec OpenAI
        summary = await self._generate_client_summary(client, timeline_data, next_appointment)

        return {
            "type": "client_summary",
            "query": query,
            "client": client,
            "timeline_count": len(timeline_data),
            "next_appointment": next_appointment,
            "formatted_response": summary
        }

    async def handle_my_appointments(
        self,
        query: str,
        intent: Dict[str, Any],
        user_id: str,
        user_role: str
    ) -> Dict[str, Any]:
        """
        Récupère les rendez-vous du technicien actuel.

        Détecte la plage de dates depuis la requête:
        - "aujourd'hui" → date du jour
        - "demain" → lendemain
        - "cette semaine" → lundi à dimanche
        """
        # Parser la plage de dates
        date_range = intent['entities'].get('date_range', {})

        if not date_range:
            # Par défaut: aujourd'hui
            today = datetime.now().strftime('%Y-%m-%d')
            date_range = {"start": today, "end": today}

        start_date = date_range.get('start')
        end_date = date_range.get('end')

        # Récupérer l'utilisateur pour avoir son gazelle_user_id
        user_result = self.supabase.table('users')\
            .select('gazelle_user_id, full_name')\
            .eq('id', user_id)\
            .single()\
            .execute()

        if not user_result.data or not user_result.data.get('gazelle_user_id'):
            return {
                "type": "error",
                "message": "Impossible de récupérer votre ID technicien Gazelle"
            }

        gazelle_user_id = user_result.data['gazelle_user_id']

        # Récupérer les rendez-vous
        appointments_result = self.supabase.table('gazelle_appointments')\
            .select('''
                *,
                client:gazelle_clients(company_name, address),
                piano:gazelle_pianos(make, model, serial_number, location)
            ''')\
            .eq('technicien', gazelle_user_id)\
            .eq('status', 'ACTIVE')\
            .gte('appointment_date', start_date)\
            .lte('appointment_date', end_date)\
            .order('appointment_date, appointment_time')\
            .execute()

        appointments = appointments_result.data if appointments_result.data else []

        # Formater la réponse
        formatted = await self._format_my_appointments(appointments, start_date, end_date)

        return {
            "type": "my_appointments",
            "query": query,
            "date_range": {"start": start_date, "end": end_date},
            "appointments": appointments,
            "formatted_response": formatted
        }

    async def handle_piano_search(
        self,
        query: str,
        intent: Dict[str, Any],
        user_id: str,
        user_role: str
    ) -> Dict[str, Any]:
        """
        Recherche de piano par numéro de série.
        """
        piano_serial = intent['entities'].get('piano_serial', '')

        if not piano_serial:
            return {
                "type": "error",
                "message": "Aucun numéro de série détecté"
            }

        # Nettoyer le numéro de série (enlever espaces, tirets)
        piano_serial_clean = re.sub(r'[^0-9A-Za-z]', '', piano_serial)

        # Chercher le piano
        piano_result = self.supabase.table('gazelle_pianos')\
            .select('''
                *,
                client:gazelle_clients(company_name, address, phone),
                timeline:gazelle_timeline_entries(
                    occurred_at,
                    entry_type,
                    title,
                    description,
                    user:users(full_name)
                )
            ''')\
            .ilike('serial_number', f'%{piano_serial_clean}%')\
            .limit(1)\
            .execute()

        if not piano_result.data:
            return {
                "type": "not_found",
                "message": f"Piano avec série '{piano_serial}' non trouvé"
            }

        piano = piano_result.data[0]

        # Limiter timeline aux 10 dernières entrées
        timeline = piano.get('timeline', [])
        if len(timeline) > 10:
            timeline = sorted(timeline, key=lambda x: x['occurred_at'], reverse=True)[:10]
            piano['timeline'] = timeline

        # Formater la réponse
        formatted = await self._format_piano_search_result(piano)

        return {
            "type": "piano_search",
            "query": query,
            "piano": piano,
            "formatted_response": formatted
        }

    async def handle_generic(
        self,
        query: str,
        intent: Dict[str, Any],
        user_id: str,
        user_role: str
    ) -> Dict[str, Any]:
        """
        Handler générique pour les questions non reconnues.
        """
        return {
            "type": "generic",
            "query": query,
            "message": "Je n'ai pas compris votre question. Essayez:\n"
                      "- 'client [nom]' pour chercher un client\n"
                      "- 'résumé pour [nom]' pour un résumé complet\n"
                      "- 'mes rendez-vous [date]' pour vos rendez-vous\n"
                      "- 'piano [série]' pour chercher un piano"
        }

    # ============================================================================
    # FORMATTERS (génération de réponses avec OpenAI)
    # ============================================================================

    async def _format_client_search_results(self, clients: List[Dict]) -> str:
        """
        Formate les résultats de recherche de client.

        Format:
        🏢 École de musique Vincent-d'Indy
        📍 628 Chemin de la Côte-Sainte-Catherine
        📞 (514) 555-1234

        👥 Contacts:
          - Anne-Marie Denoncourt (anne-marie@vincentdindy.ca)

        🎹 Pianos (3):
          - Yamaha C3 (#1234567) - Studio A
        """
        if len(clients) == 1:
            client = clients[0]
            lines = []

            # Header
            lines.append(f"🏢 {client['company_name']}")
            if client.get('address'):
                lines.append(f"📍 {client['address']}")
            if client.get('phone'):
                lines.append(f"📞 {client['phone']}")

            # Contacts
            contacts = client.get('contacts', [])
            if contacts:
                lines.append("\n👥 Contacts:")
                for contact in contacts[:5]:  # Max 5 contacts
                    name = contact.get('full_name', 'N/A')
                    email = contact.get('email', '')
                    email_str = f" ({email})" if email else ""
                    lines.append(f"  - {name}{email_str}")

            # Pianos
            pianos = client.get('pianos', [])
            if pianos:
                lines.append(f"\n🎹 Pianos ({len(pianos)}):")
                for piano in pianos[:10]:  # Max 10 pianos
                    make = piano.get('make', 'N/A')
                    model = piano.get('model', 'N/A')
                    serial = piano.get('serial_number', 'N/A')
                    location = piano.get('location', '')
                    loc_str = f" - {location}" if location else ""
                    lines.append(f"  - {make} {model} (#{serial}){loc_str}")

            return "\n".join(lines)

        else:
            # Multiple clients found
            lines = [f"✅ {len(clients)} clients trouvés:\n"]
            for i, client in enumerate(clients[:5], 1):
                lines.append(f"{i}. {client['company_name']}")
                if client.get('address'):
                    lines.append(f"   📍 {client['address']}")

            if len(clients) > 5:
                lines.append(f"\n... et {len(clients) - 5} autres")

            return "\n".join(lines)

    async def _generate_client_summary(
        self,
        client: Dict,
        timeline: List[Dict],
        next_appointment: Optional[Dict]
    ) -> str:
        """
        Génère un résumé structuré avec OpenAI selon FORMAT_RESUME_CLIENT.md.
        """
        prompt = f"""Génère un résumé structuré pour ce client de piano selon ce format EXACT:

🎹 Piano
- [marque / modèle / série]
- [localisation précise]
- [particularités d'achat / historique]

🧰 État mécanique / sonore
- [SEULEMENT les problèmes signalés ou récurrents]
- [Si aucun problème: "Aucun problème signalé"]

💧 Humidité / entretien
- [SEULEMENT les anomalies d'humidité]
- [Si normal: "Aucune anomalie détectée"]

📅 Historique pertinent
- [2-3 interventions importantes seulement]
- Format: "date: type (technicien) - détails si pertinents"

🔜 Points à surveiller
- [Éléments à vérifier lors du prochain rendez-vous]
- [Si rien: "RAS"]

⏭️ Détails supplémentaires
- Pour plus de détails, demandez: "Montre-moi les interventions 2024"

RÈGLES IMPORTANTES:
- Maximum 10 lignes par section
- Sois concis et direct
- Ne mentionne QUE les anomalies / problèmes
- Pas de détails sur les accords de routine sauf si pertinent
- Utilise les emojis indiqués

Données client:
{json.dumps(client, indent=2, ensure_ascii=False)}

Timeline (50 dernières entrées):
{json.dumps(timeline[:20], indent=2, ensure_ascii=False)}

Prochain RDV:
{json.dumps(next_appointment, indent=2, ensure_ascii=False) if next_appointment else "Aucun"}
"""

        response = self.anthropic.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=2000,
            system="Tu es un assistant pour techniciens de piano. Génère des résumés CONCIS et STRUCTURÉS.",
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        return response.content[0].text

    async def _format_my_appointments(
        self,
        appointments: List[Dict],
        start_date: str,
        end_date: str
    ) -> str:
        """
        Formate la liste des rendez-vous.

        Format:
        📅 Vos rendez-vous pour demain (25 décembre):

        🕐 9h00 - 11h00
          🏢 École de musique Vincent-d'Indy
          🎹 Yamaha C3 (#1234567) - Studio A
          📍 628 Chemin de la Côte-Sainte-Catherine
          📝 Accord + mesure humidité
        """
        if not appointments:
            return f"Aucun rendez-vous pour la période {start_date} → {end_date}"

        # Header
        if start_date == end_date:
            date_label = start_date
        else:
            date_label = f"{start_date} → {end_date}"

        lines = [f"📅 Vos rendez-vous pour {date_label}:\n"]

        for appt in appointments:
            # Time
            time_str = appt.get('appointment_time', 'N/A')
            lines.append(f"🕐 {time_str}")

            # Client
            client = appt.get('client', {})
            if client:
                lines.append(f"  🏢 {client.get('company_name', 'N/A')}")

            # Piano
            piano = appt.get('piano', {})
            if piano:
                make = piano.get('make', 'N/A')
                model = piano.get('model', 'N/A')
                serial = piano.get('serial_number', 'N/A')
                location = piano.get('location', '')
                loc_str = f" - {location}" if location else ""
                lines.append(f"  🎹 {make} {model} (#{serial}){loc_str}")

            # Address
            if client and client.get('address'):
                lines.append(f"  📍 {client['address']}")

            # Notes
            notes = appt.get('notes', '')
            if notes:
                lines.append(f"  📝 {notes[:100]}")  # Truncate long notes

            lines.append("")  # Blank line between appointments

        return "\n".join(lines)

    async def _format_piano_search_result(self, piano: Dict) -> str:
        """
        Formate les résultats de recherche de piano.

        Format:
        🎹 Yamaha C3 (Série: 1234567)

        📍 Emplacement:
          🏢 École de musique Vincent-d'Indy
          📌 Studio A

        📊 Détails techniques:
          Année: 2015
          Type: Piano à queue

        📅 Dernières interventions (5):
          - 2024-12-15: Accord (Allan)
        """
        lines = []

        # Header
        make = piano.get('make', 'N/A')
        model = piano.get('model', 'N/A')
        serial = piano.get('serial_number', 'N/A')
        lines.append(f"🎹 {make} {model} (Série: {serial})\n")

        # Emplacement
        lines.append("📍 Emplacement:")
        client = piano.get('client', {})
        if client:
            lines.append(f"  🏢 {client.get('company_name', 'N/A')}")
        if piano.get('location'):
            lines.append(f"  📌 {piano['location']}")

        # Détails techniques
        lines.append("\n📊 Détails techniques:")
        if piano.get('year'):
            lines.append(f"  Année: {piano['year']}")
        if piano.get('piano_type'):
            lines.append(f"  Type: {piano['piano_type']}")

        # Timeline
        timeline = piano.get('timeline', [])
        if timeline:
            lines.append(f"\n📅 Dernières interventions ({len(timeline)}):")
            for entry in timeline[:5]:
                date = entry.get('occurred_at', 'N/A')[:10]  # YYYY-MM-DD
                title = entry.get('title', 'N/A')
                user = entry.get('user', {})
                user_name = user.get('full_name', 'N/A') if user else 'N/A'
                lines.append(f"  - {date}: {title} ({user_name})")

        return "\n".join(lines)

    # ============================================================================
    # PHASE 2: ADVANCED QUERIES
    # ============================================================================

    async def handle_client_history(
        self,
        query: str,
        intent: Dict[str, Any],
        user_id: str,
        user_role: str
    ) -> Dict[str, Any]:
        """
        Récupère l'historique des interventions d'un client avec filtres.

        Supporte filtres par:
        - Année (ex: "interventions 2024")
        - Type d'intervention
        - Technicien
        """
        client_name = intent['entities'].get('client_name', '')
        date_range = intent['entities'].get('date_range', {})

        if not client_name:
            return {
                "type": "error",
                "message": "Aucun nom de client détecté"
            }

        # 1. Trouver le client
        client_result = self.supabase.table('gazelle_clients')\
            .select('id, company_name, pianos:gazelle_pianos(id)')\
            .ilike('company_name', f'%{client_name}%')\
            .limit(1)\
            .execute()

        if not client_result.data:
            return {
                "type": "not_found",
                "message": f"Client '{client_name}' non trouvé"
            }

        client = client_result.data[0]
        piano_ids = [p['id'] for p in client.get('pianos', [])]

        if not piano_ids:
            return {
                "type": "not_found",
                "message": f"Aucun piano trouvé pour ce client"
            }

        # 2. Récupérer timeline avec filtres
        query_builder = self.supabase.table('gazelle_timeline_entries')\
            .select('''
                occurred_at,
                entry_type,
                title,
                description,
                piano:gazelle_pianos(make, model, serial_number, location),
                user:users(full_name)
            ''')\
            .in_('piano_id', piano_ids)\
            .order('occurred_at', desc=True)

        # Filtre par date si spécifié
        if date_range.get('start'):
            query_builder = query_builder.gte('occurred_at', date_range['start'])
        if date_range.get('end'):
            query_builder = query_builder.lte('occurred_at', date_range['end'])

        timeline_result = query_builder.limit(200).execute()
        timeline = timeline_result.data if timeline_result.data else []

        # Formater la réponse
        formatted = await self._format_client_history(client, timeline, date_range)

        return {
            "type": "client_history",
            "query": query,
            "client": client,
            "timeline": timeline,
            "formatted_response": formatted
        }

    async def handle_search_notes(
        self,
        query: str,
        intent: Dict[str, Any],
        user_id: str,
        user_role: str
    ) -> Dict[str, Any]:
        """
        Recherche dans les notes / timeline entries par mot-clé.

        Exemples: "trouve 'faux battements'", "recherche 'pédale'"
        """
        search_term = intent['entities'].get('search_term', '')
        client_name = intent['entities'].get('client_name', '')

        if not search_term:
            return {
                "type": "error",
                "message": "Aucun terme de recherche détecté"
            }

        # Construire la query
        query_builder = self.supabase.table('gazelle_timeline_entries')\
            .select('''
                occurred_at,
                entry_type,
                title,
                description,
                piano:gazelle_pianos(make, model, serial_number, location, client:gazelle_clients(company_name)),
                user:users(full_name)
            ''')

        # Filtre par client si spécifié
        if client_name:
            # Trouver le client d'abord
            client_result = self.supabase.table('gazelle_clients')\
                .select('id, pianos:gazelle_pianos(id)')\
                .ilike('company_name', f'%{client_name}%')\
                .limit(1)\
                .execute()

            if client_result.data:
                piano_ids = [p['id'] for p in client_result.data[0].get('pianos', [])]
                if piano_ids:
                    query_builder = query_builder.in_('piano_id', piano_ids)

        # Full-text search dans title et description
        query_builder = query_builder.or_(
            f'title.ilike.%{search_term}%,description.ilike.%{search_term}%'
        )

        results = query_builder.order('occurred_at', desc=True).limit(50).execute()
        entries = results.data if results.data else []

        # Formater la réponse
        formatted = await self._format_search_notes_results(search_term, entries, client_name)

        return {
            "type": "search_notes",
            "query": query,
            "search_term": search_term,
            "results_count": len(entries),
            "entries": entries,
            "formatted_response": formatted
        }

    async def handle_humidity_readings(
        self,
        query: str,
        intent: Dict[str, Any],
        user_id: str,
        user_role: str
    ) -> Dict[str, Any]:
        """
        Récupère les mesures d'humidité pour un piano ou client.

        Parse les mesures depuis description (format: "22°C, 37% humidité")
        """
        piano_serial = intent['entities'].get('piano_serial', '')
        client_name = intent['entities'].get('client_name', '')

        # Déterminer les piano_ids à chercher
        piano_ids = []

        if piano_serial:
            # Chercher par numéro de série
            piano_result = self.supabase.table('gazelle_pianos')\
                .select('id')\
                .ilike('serial_number', f'%{piano_serial}%')\
                .limit(1)\
                .execute()

            if piano_result.data:
                piano_ids = [piano_result.data[0]['id']]

        elif client_name:
            # Chercher par client
            client_result = self.supabase.table('gazelle_clients')\
                .select('pianos:gazelle_pianos(id)')\
                .ilike('company_name', f'%{client_name}%')\
                .limit(1)\
                .execute()

            if client_result.data:
                piano_ids = [p['id'] for p in client_result.data[0].get('pianos', [])]

        if not piano_ids:
            return {
                "type": "not_found",
                "message": "Aucun piano trouvé pour la recherche d'humidité"
            }

        # Récupérer les mesures (entry_type = PIANO_MEASUREMENT)
        measurements_result = self.supabase.table('gazelle_timeline_entries')\
            .select('''
                occurred_at,
                description,
                piano:gazelle_pianos(make, model, serial_number, location),
                user:users(full_name)
            ''')\
            .in_('piano_id', piano_ids)\
            .eq('entry_type', 'PIANO_MEASUREMENT')\
            .order('occurred_at', desc=True)\
            .limit(20)\
            .execute()

        measurements = measurements_result.data if measurements_result.data else []

        # Parser les mesures
        parsed_measurements = self._parse_humidity_measurements(measurements)

        # Formater la réponse
        formatted = await self._format_humidity_readings(parsed_measurements)

        return {
            "type": "humidity_readings",
            "query": query,
            "measurements": parsed_measurements,
            "formatted_response": formatted
        }

    async def handle_unpaid_invoices(
        self,
        query: str,
        intent: Dict[str, Any],
        user_id: str,
        user_role: str
    ) -> Dict[str, Any]:
        """
        Récupère les factures impayées.

        Peut filtrer par client si spécifié.
        """
        client_name = intent['entities'].get('client_name', '')

        # Construire la query
        query_builder = self.supabase.table('gazelle_invoices')\
            .select('''
                *,
                client:gazelle_clients(company_name, phone)
            ''')

        # Filtre par client si spécifié
        if client_name:
            client_result = self.supabase.table('gazelle_clients')\
                .select('id')\
                .ilike('company_name', f'%{client_name}%')\
                .limit(1)\
                .execute()

            if client_result.data:
                query_builder = query_builder.eq('client_id', client_result.data[0]['id'])

        # Filtrer les impayées
        invoices_result = query_builder\
            .eq('payment_status', 'UNPAID')\
            .order('issued_at')\
            .execute()

        invoices = invoices_result.data if invoices_result.data else []

        # Calculer total impayé
        total_unpaid = sum(inv.get('amount', 0) for inv in invoices)

        # Formater la réponse
        formatted = await self._format_unpaid_invoices(invoices, total_unpaid, client_name)

        return {
            "type": "unpaid_invoices",
            "query": query,
            "invoices": invoices,
            "total_unpaid": total_unpaid,
            "formatted_response": formatted
        }

    # ============================================================================
    # FORMATTERS PHASE 2
    # ============================================================================

    async def _format_client_history(
        self,
        client: Dict,
        timeline: List[Dict],
        date_range: Dict
    ) -> str:
        """
        Formate l'historique des interventions.
        """
        lines = []

        # Header
        client_name = client.get('company_name', 'N/A')
        count = len(timeline)

        if date_range.get('start') or date_range.get('end'):
            start = date_range.get('start', '...')
            end = date_range.get('end', '...')
            lines.append(f"📅 Interventions pour {client_name} ({start} → {end}):")
        else:
            lines.append(f"📅 Interventions pour {client_name} ({count} entrées):")

        lines.append("")

        # Grouper par piano pour meilleure lisibilité
        piano_groups = {}
        for entry in timeline:
            piano = entry.get('piano', {})
            piano_key = f"{piano.get('make', 'N/A')} {piano.get('model', 'N/A')} (#{piano.get('serial_number', 'N/A')})"

            if piano_key not in piano_groups:
                piano_groups[piano_key] = []
            piano_groups[piano_key].append(entry)

        # Afficher par piano
        for piano_name, entries in list(piano_groups.items())[:10]:  # Max 10 pianos
            lines.append(f"🎹 {piano_name}")

            for entry in entries[:5]:  # Max 5 entrées par piano
                date = entry.get('occurred_at', 'N/A')[:10]
                title = entry.get('title', 'N/A')
                user = entry.get('user', {})
                user_name = user.get('full_name', 'N/A') if user else 'N/A'

                lines.append(f"  • {date}: {title} ({user_name})")

            lines.append("")

        return "\n".join(lines)

    async def _format_search_notes_results(
        self,
        search_term: str,
        entries: List[Dict],
        client_name: str
    ) -> str:
        """
        Formate les résultats de recherche dans les notes.
        """
        if not entries:
            return f"Aucun résultat trouvé pour '{search_term}'"

        lines = []

        # Header
        header = f"🔍 Résultats pour '{search_term}'"
        if client_name:
            header += f" (client: {client_name})"
        header += f" ({len(entries)} résultat{'s' if len(entries) > 1 else ''}):\n"
        lines.append(header)

        # Résultats (max 10)
        for entry in entries[:10]:
            date = entry.get('occurred_at', 'N/A')[:10]
            title = entry.get('title', 'N/A')
            description = entry.get('description', '')

            piano = entry.get('piano', {})
            piano_str = f"{piano.get('make', 'N/A')} {piano.get('model', 'N/A')}"

            client = piano.get('client', {}) if piano else {}
            client_name_str = client.get('company_name', 'N/A') if client else 'N/A'

            user = entry.get('user', {})
            user_name = user.get('full_name', 'N/A') if user else 'N/A'

            lines.append(f"📌 {date} | {client_name_str}")
            lines.append(f"   🎹 {piano_str}")
            lines.append(f"   💬 {title}")

            # Afficher extrait de description si match
            if description and search_term.lower() in description.lower():
                # Trouver contexte autour du match
                idx = description.lower().find(search_term.lower())
                start = max(0, idx - 50)
                end = min(len(description), idx + len(search_term) + 50)
                excerpt = description[start:end]
                if start > 0:
                    excerpt = "..." + excerpt
                if end < len(description):
                    excerpt = excerpt + "..."
                lines.append(f"   📝 {excerpt}")

            lines.append(f"   👤 {user_name}\n")

        if len(entries) > 10:
            lines.append(f"... et {len(entries) - 10} autres résultats")

        return "\n".join(lines)

    def _parse_humidity_measurements(self, measurements: List[Dict]) -> List[Dict]:
        """
        Parse les mesures d'humidité depuis description.

        Format attendu: "22°C, 37% humidité" ou similaire
        """
        import re

        parsed = []

        for m in measurements:
            description = m.get('description', '')

            # Regex pour trouver température et humidité
            temp_match = re.search(r'(\d+)\s*°C', description)
            humidity_match = re.search(r'(\d+)\s*%', description)

            temperature = int(temp_match.group(1)) if temp_match else None
            humidity = int(humidity_match.group(1)) if humidity_match else None

            if temperature or humidity:
                parsed.append({
                    'date': m.get('occurred_at', 'N/A')[:10],
                    'temperature': temperature,
                    'humidity': humidity,
                    'piano': m.get('piano', {}),
                    'technician': m.get('user', {}).get('full_name', 'N/A')
                })

        return parsed

    async def _format_humidity_readings(self, measurements: List[Dict]) -> str:
        """
        Formate les mesures d'humidité.
        """
        if not measurements:
            return "Aucune mesure d'humidité trouvée"

        lines = []

        # Grouper par piano
        piano_groups = {}
        for m in measurements:
            piano = m.get('piano', {})
            piano_key = f"{piano.get('make', 'N/A')} {piano.get('model', 'N/A')} (#{piano.get('serial_number', 'N/A')})"

            if piano_key not in piano_groups:
                piano_groups[piano_key] = []
            piano_groups[piano_key].append(m)

        # Afficher par piano
        for piano_name, piano_measurements in piano_groups.items():
            lines.append(f"💧 Mesures d'humidité - {piano_name}:\n")

            for m in piano_measurements[:10]:  # Max 10 mesures
                date = m['date']
                temp = m['temperature']
                humidity = m['humidity']
                tech = m['technician']

                # Évaluation
                status = "✅ Normal"
                if humidity:
                    if humidity < 35:
                        status = "⚠️ Trop sec"
                    elif humidity > 55:
                        status = "⚠️ Trop humide"

                temp_str = f"🌡️ {temp}°C" if temp else ""
                humidity_str = f"💧 {humidity}%" if humidity else ""

                lines.append(f"📅 {date} ({tech})")
                lines.append(f"  {temp_str} | {humidity_str} | {status}\n")

            # Tendance
            if len(piano_measurements) >= 3:
                recent_humidities = [m['humidity'] for m in piano_measurements[:3] if m['humidity']]
                if recent_humidities:
                    avg = sum(recent_humidities) / len(recent_humidities)
                    lines.append(f"Tendance récente: {avg:.0f}% (moyenne 3 dernières)\n")

        return "\n".join(lines)

    async def _format_unpaid_invoices(
        self,
        invoices: List[Dict],
        total_unpaid: float,
        client_name: str
    ) -> str:
        """
        Formate la liste des factures impayées.
        """
        if not invoices:
            msg = "✅ Aucune facture impayée"
            if client_name:
                msg += f" pour {client_name}"
            return msg

        lines = []

        # Header
        header = f"💰 Factures impayées"
        if client_name:
            header += f" - {client_name}"
        header += f" ({len(invoices)} facture{'s' if len(invoices) > 1 else ''}):\n"
        lines.append(header)

        # Factures (max 20)
        for inv in invoices[:20]:
            invoice_number = inv.get('invoice_number', 'N/A')
            amount = inv.get('amount', 0)
            issued_date = inv.get('issued_at', 'N/A')[:10] if inv.get('issued_at') else 'N/A'
            client = inv.get('client', {})
            client_name_str = client.get('company_name', 'N/A') if client else 'N/A'

            # Calculer jours en retard
            if inv.get('due_date'):
                from datetime import datetime
                due_date = datetime.fromisoformat(inv['due_date'][:10])
                today = datetime.now()
                days_overdue = (today - due_date).days

                if days_overdue > 0:
                    overdue_str = f" ⚠️ {days_overdue} jours de retard"
                else:
                    overdue_str = ""
            else:
                overdue_str = ""

            lines.append(f"📄 #{invoice_number} - {amount}$ - {issued_date}")
            lines.append(f"   🏢 {client_name_str}{overdue_str}\n")

        # Total
        lines.append(f"💵 Total impayé: {total_unpaid}$")

        return "\n".join(lines)
