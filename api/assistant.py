#!/usr/bin/env python3
"""
Routes API pour l'Assistant Conversationnel Gazelle V5.

Endpoints:
- POST /assistant/chat - Poser une question à l'assistant
- GET /assistant/health - Vérifier l'état de l'assistant
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from modules.assistant.services.parser import get_parser, QueryType
from modules.assistant.services.queries import get_queries
from modules.assistant.services.vector_search import get_vector_search


router = APIRouter(prefix="/assistant", tags=["assistant"])


# ============================================================
# Modèles Pydantic
# ============================================================

class ChatRequest(BaseModel):
    """Requête de chat avec l'assistant."""
    question: str
    user_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None


class ChatResponse(BaseModel):
    """Réponse de l'assistant."""
    question: str
    answer: str
    query_type: str
    confidence: float
    data: Optional[Dict[str, Any]] = None
    vector_search_used: bool = False
    vector_results: Optional[list] = None
    # Données structurées pour l'interactivité frontend
    structured_data: Optional[Dict[str, Any]] = None


class AdminFeedbackPayload(BaseModel):
    """Payload pour ajouter une note interne admin."""
    note: str
    user_email: str


class HealthResponse(BaseModel):
    """État de santé de l'assistant."""
    status: str
    parser_loaded: bool
    queries_loaded: bool
    vector_search_loaded: bool
    vector_index_size: int


# ============================================================
# Routes
# ============================================================

@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Endpoint principal de l'assistant conversationnel.

    Args:
        request: Question de l'utilisateur

    Returns:
        Réponse formatée avec données et contexte
    """
    try:
        question = request.question.strip()

        if not question:
            raise HTTPException(status_code=400, detail="Question vide")

        # 1. Parser la question
        parser = get_parser()
        parsed = parser.parse(question)

        query_type = parsed['query_type']
        params = parsed['params']
        confidence = parsed['confidence']

        # 2. Cas spécial: Aide
        if query_type == QueryType.HELP:
            return ChatResponse(
                question=question,
                answer=parser.format_help_response(),
                query_type="help",
                confidence=1.0,
                vector_search_used=False
            )

        # 3. Cas spécial: Requête inconnue -> Utiliser vector search
        # Seuil réduit à 0.1 pour accepter plus de requêtes en langage naturel
        if query_type == QueryType.UNKNOWN or confidence < 0.1:
            vector_search = get_vector_search()
            results = vector_search.search(question, top_k=3)

            if results:
                # Formater la réponse avec les résultats vectoriels
                answer = _format_vector_response(results)

                return ChatResponse(
                    question=question,
                    answer=answer,
                    query_type="vector_search",
                    confidence=results[0]['similarity'] if results else 0.0,
                    vector_search_used=True,
                    vector_results=[
                        {
                            'text': r['text'][:200] + '...' if len(r['text']) > 200 else r['text'],
                            'source': r['source'],
                            'similarity': r['similarity']
                        }
                        for r in results
                    ] if results else []
                )
            else:
                return ChatResponse(
                    question=question,
                    answer="Je n'ai pas trouvé d'information pertinente. Essayez de reformuler votre question ou utilisez `.aide` pour voir les commandes disponibles.",
                    query_type="unknown",
                    confidence=0.0,
                    vector_search_used=True,
                    vector_results=[]
                )

        # 4. Exécuter la requête
        queries = get_queries()
        results = queries.execute_query(query_type, params, user_id=request.user_id)

        # 5. Formater la réponse
        formatted_response = _format_response(query_type, results)

        # Gérer le cas où _format_response retourne un dict (avec entities cliquables)
        if isinstance(formatted_response, dict):
            answer = formatted_response.get('text', '')
            entities = formatted_response.get('entities', [])
        else:
            answer = formatted_response
            entities = []

        # 6. Préparer les données structurées pour l'interactivité frontend
        structured_data = None
        if query_type == QueryType.APPOINTMENTS:
            # Enrichir les appointments avec TOUS les détails (comme dans train_summaries.py)
            appointments_data = results.get('data', [])
            enriched_appointments = _enrich_appointments(appointments_data, queries)
            
            structured_data = {
                'appointments': [
                    {
                        'id': appt.get('id'),
                        'external_id': appt.get('external_id'),
                        'client_external_id': appt.get('client_external_id'),
                        'client_name': _extract_client_name(appt),
                        'appointment_date': appt.get('appointment_date'),
                        'appointment_time': _format_time(
                            appt.get('appointment_time', 'N/A'),
                            appt.get('appointment_date', '')
                        ),
                        'location': appt.get('location', ''),
                        'description': appt.get('description', ''),
                        'technicien': appt.get('technicien', ''),
                        # Détails enrichis
                        'client_address': appt.get('client_address', ''),
                        'client_city': appt.get('client_city', ''),
                        'client_phone': appt.get('client_phone', ''),
                        'client_notes': appt.get('client_notes', ''),
                        'associated_contacts': appt.get('associated_contacts', []),
                        'service_history_notes': appt.get('service_history_notes', []),
                        'pianos': appt.get('pianos', [])
                    }
                    for appt in enriched_appointments
                ]
            }
        elif query_type == QueryType.SEARCH_CLIENT and entities:
            # Ajouter les entités cliquables dans structured_data
            structured_data = {
                'clickable_entities': entities
            }

        return ChatResponse(
            question=question,
            answer=answer,
            query_type=query_type.value,
            confidence=confidence,
            data=results,
            vector_search_used=False,
            structured_data=structured_data
        )

    except Exception as e:
        print(f"❌ Erreur dans /assistant/chat: {e}")
        import traceback
        traceback.print_exc()

        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors du traitement de la question: {str(e)}"
        )


@router.get("/client/{client_id}")
async def get_client_details(client_id: str):
    """
    Récupère les détails complets d'un client/contact pour affichage dans le modal.
    
    Utilise le même format que train_summaries.py (le plus fourni).
    Inclut: contacts associés, pianos avec notes, service history, prochains RV.
    """
    try:
        import requests
        queries = get_queries()
        print(f"🔍 /assistant/client -> lookup id: {client_id}")
        
        from typing import Optional, List

        def build_timeline_summary(entity_id: str, contact_ids: Optional[List[str]] = None) -> dict:
            """
            Récupère et résume les entrées timeline depuis Supabase.
            Retourne un dict avec compte total, bornes de dates et extraits récents.

            IMPORTANT: Les notes de service sont souvent liées aux pianos, pas au client.
            On cherche donc:
            1. Les timeline entries du client
            2. Les timeline entries de tous les pianos appartenant au client
            3. Les timeline entries des contacts associés
            """
            contact_ids = contact_ids or []

            # 1. Récupérer tous les pianos du client
            piano_ids = []
            try:
                import requests
                # Chercher les pianos qui ont ce client_external_id
                pianos_url = f"{queries.storage.api_url}/gazelle_pianos"
                pianos_url += f"?select=external_id,id&client_external_id=eq.{entity_id}"
                pianos_response = requests.get(pianos_url, headers=queries.storage._get_headers())

                if pianos_response.status_code == 200:
                    pianos = pianos_response.json()
                    piano_ids = [p.get('external_id') or p.get('id') for p in pianos if p.get('external_id') or p.get('id')]
                    print(f"🎹 Trouvé {len(piano_ids)} pianos pour le client {entity_id}")
            except Exception as e:
                print(f"⚠️ Erreur récupération pianos du client: {e}")

            # 2. Construire la liste complète des IDs à chercher
            # Inclure: client + contacts + tous les pianos
            ids_union = [entity_id] + contact_ids + piano_ids

            print(f"🔍 Recherche timeline pour {len(ids_union)} entités (1 client + {len(contact_ids)} contacts + {len(piano_ids)} pianos)")

            entries_client, total_client = queries.get_timeline_entries(
                entity_type=None,  # pas de filtre, car entity_type souvent vide
                entity_ids=ids_union,
                client_ids=[entity_id] + contact_ids,  # garder aussi le filtre client_external_id
                limit=500,
                include_count=True,
                debug=True
            )

            all_entries = list(entries_client or [])

            # Séparer les entrées non pertinentes (bruit administratif)
            # Liste des patterns à exclure
            exclude_patterns = [
                "inactivating this piano record",
                "moved piano to",
                "exporté vers mailchimp",
                "exported to mailchimp",
                "courriel envoyé",
                "email sent",
                "rendez-vous complété",
                "appointment completed",
                "rv complété",
                "reminder sent",
                "rappel envoyé",
                "synced to",
                "synchronisé",
            ]

            flagged_entries_raw = []
            kept_entries = []
            for e in all_entries or []:
                desc = (e.get("description") or "").lower()
                # Vérifier si l'entrée contient un pattern à exclure
                is_flagged = any(pattern in desc for pattern in exclude_patterns)
                if is_flagged:
                    flagged_entries_raw.append(e)
                else:
                    kept_entries.append(e)

            # Exclure les entrées d'aujourd'hui et futures (pas encore de l'historique)
            today_str = datetime.now().strftime('%Y-%m-%d')
            entries = [
                e for e in kept_entries
                if not (e.get("entry_date") or "")[:10] or (e.get("entry_date") or "")[:10] < today_str
            ]

            if not entries:
                return {
                    "total_entries": (total_client or 0),
                    "recent_entries": [],
                    "top_messages": [],
                    "by_year": {},
                    "null_descriptions": 0,
                    "first_entry_date": None,
                    "last_entry_date": None,
                    "flagged_entries": [],
                    "flagged_count": len(flagged_entries_raw),
                }

            from collections import Counter
            from datetime import datetime

            def safe_date(d):
                try:
                    return datetime.fromisoformat(d.replace("Z", "+00:00"))
                except Exception:
                    return None

            dates = [safe_date(e.get("entry_date", "")) for e in entries if e.get("entry_date")]
            dates_clean = [d for d in dates if d]
            first_entry = min(dates_clean).date().isoformat() if dates_clean else None
            last_entry = max(dates_clean).date().isoformat() if dates_clean else None

            # Comptes par année
            by_year = Counter()
            for d in dates_clean:
                by_year[str(d.year)] += 1

            # Messages (description ou titre)
            descriptions = []
            null_descriptions = 0
            for e in entries:
                desc = e.get("description")
                if desc is None:
                    null_descriptions += 1
                else:
                    descriptions.append(desc)

            top_messages = Counter(descriptions).most_common(5)

            def render_entry(e):
                text = e.get("description") or e.get("title") or e.get("event_type") or "Note"
                date_str = (e.get("entry_date") or "")[:10]
                return {"date": date_str, "text": text}

            recent_entries = [render_entry(e) for e in entries[:20]]
            flagged_entries = [render_entry(e) for e in flagged_entries_raw[:20]]

            return {
                "total_entries": max(total_client or 0, len(entries)),
                "recent_entries": recent_entries,
                "top_messages": [{"text": msg, "count": cnt} for msg, cnt in top_messages],
                "by_year": dict(by_year),
                "null_descriptions": null_descriptions,
                "first_entry_date": first_entry,
                "last_entry_date": last_entry,
                "flagged_entries": flagged_entries,
                "flagged_count": len(flagged_entries_raw),
            }

        # Rechercher le client/contact (voie principale)
        results = queries.search_clients([client_id])
        
        # Fallback: requêtes directes sur plusieurs endpoints + ilike
        if not results:
            endpoints_clients = ["gazelle_clients", "gazelle.clients", "clients"]
            endpoints_contacts = ["gazelle_contacts", "gazelle.contacts", "contacts"]
            found = []
            is_numeric_id = client_id.isdigit()

            def fetch_endpoint(endpoint_list, entity_type):
                for ep in endpoint_list:
                    try:
                        # eq sur external_id (et id si numérique uniquement)
                        eq_filters = [f"external_id=eq.{client_id}"]
                        if is_numeric_id:
                            eq_filters.append(f"id=eq.{client_id}")
                        eq_filters_str = "&".join(eq_filters)

                        url_eq = (
                            f"{queries.storage.api_url}/{ep}"
                            f"?select=*"
                            f"&{eq_filters_str}"
                            f"&limit=5"
                        )
                        resp_eq = requests.get(url_eq, headers=queries.storage._get_headers())
                        print(f"   ↳ {ep} eq status {resp_eq.status_code}")
                        if resp_eq.status_code == 200 and resp_eq.json():
                            for item in resp_eq.json():
                                item["_source"] = entity_type
                                found.append(item)
                            return

                        # ilike si eq vide
                        ilike_filters = [f"external_id.ilike.*{client_id}*"]
                        ilike_filters_str = "&".join(ilike_filters)
                        url_ilike = (
                            f"{queries.storage.api_url}/{ep}"
                            f"?select=*"
                            f"&{ilike_filters_str}"
                            f"&limit=5"
                        )
                        resp_ilike = requests.get(url_ilike, headers=queries.storage._get_headers())
                        print(f"   ↳ {ep} ilike status {resp_ilike.status_code}")
                        if resp_ilike.status_code == 200 and resp_ilike.json():
                            for item in resp_ilike.json():
                                item["_source"] = entity_type
                                found.append(item)
                            return
                    except Exception as e:
                        print(f"⚠️ Fallback fetch error {ep}: {e}")

            fetch_endpoint(endpoints_clients, "client")
            fetch_endpoint(endpoints_contacts, "contact")

            if found:
                results = found
        
        if not results or len(results) == 0:
            print(f"❌ Aucun résultat pour {client_id}")
            raise HTTPException(status_code=404, detail="Client non trouvé")
        
        entity = results[0]
        entity_id = entity.get('external_id') or entity.get('id') or client_id
        
        # Détecter par préfixe
        is_client = entity_id.startswith('cli_')
        is_contact = entity_id.startswith('con_')
        
        # Informations de base
        if is_contact:
            first = entity.get('first_name', '')
            last = entity.get('last_name', '')
            name = f"{first} {last}".strip() or entity.get('name', 'N/A')
        else:
            name = entity.get('company_name', 'N/A')
        
        details = {
            'id': entity_id,
            'type': 'client' if is_client else 'contact',
            'name': name,
            'address': entity.get('address', ''),
            'city': entity.get('city', ''),
            'postal_code': entity.get('postal_code', ''),
            'phone': entity.get('phone', '') or entity.get('telephone', ''),
            'email': entity.get('email', '')
        }
        
        # Pour les clients uniquement: enrichissement complet
        if is_client:
            # Notes client
            details['client_notes'] = entity.get('notes', '') or entity.get('note', '') or entity.get('description', '')
            
            # Pianos avec leurs notes
            try:
                pianos_url = f"{queries.storage.api_url}/gazelle_pianos?client_external_id=eq.{entity_id}&select=external_id,notes,make,model,serial_number,type,year,location&limit=10"
                pianos_response = requests.get(pianos_url, headers=queries.storage._get_headers())
                if pianos_response.status_code == 200:
                    pianos = pianos_response.json()
                    details['pianos'] = []
                    for piano in pianos:
                        piano_info = {
                            'external_id': piano.get('external_id', ''),
                            'make': piano.get('make', ''),
                            'model': piano.get('model', ''),
                            'serial_number': piano.get('serial_number', ''),
                            'type': piano.get('type', ''),
                            'year': piano.get('year', ''),
                            'location': piano.get('location', ''),
                            'notes': piano.get('notes', '')
                        }
                        if piano_info['make'] or piano_info['model'] or piano_info['notes']:
                            details['pianos'].append(piano_info)
            except Exception as e:
                print(f"⚠️ Erreur récupération pianos pour {entity_id}: {e}")
                details['pianos'] = []
            
            details['admin_feedback'] = []
            contact_ids = []
            service_notes = []

            # Contacts associés
            try:
                contacts_url = f"{queries.storage.api_url}/gazelle_contacts?client_external_id=eq.{entity_id}&limit=10"
                contacts_response = requests.get(contacts_url, headers=queries.storage._get_headers())
                if contacts_response.status_code == 200:
                    contacts = contacts_response.json()
                    if contacts:
                        details['associated_contacts'] = []
                        for c in contacts[:10]:
                            cid = c.get('external_id') or c.get('id')
                            if cid:
                                contact_ids.append(cid)
                            details['associated_contacts'].append({
                                'name': f"{c.get('first_name', '')} {c.get('last_name', '')}".strip() or c.get('name', 'N/A'),
                                'role': c.get('role') or c.get('title') or '',
                                'phone': c.get('phone') or c.get('telephone') or '',
                                'email': c.get('email', '')
                            })
                    else:
                        details['associated_contacts'] = []

                    # Ajouter les notes de service des contacts associés
                    for cid in contact_ids[:5]:
                        try:
                            contact_entries = queries.get_timeline_entries(
                                cid,
                                entity_type="contact",
                                limit=10,
                                include_count=False
                            )
                            for e in contact_entries or []:
                                note = (
                                    e.get('notes') or e.get('description') or e.get('content')
                                    or e.get('note') or e.get('text') or e.get('summary')
                                )
                                if note:
                                    service_notes.append(str(note))
                        except Exception as err:
                            print(f"⚠️ Erreur timeline contact {cid}: {err}")
                else:
                    details['associated_contacts'] = []
            except Exception as e:
                print(f"⚠️ Erreur contacts associés pour {entity_id}: {e}")
                details['associated_contacts'] = []
            
            # Prochains rendez-vous
            try:
                from datetime import date
                today = date.today()
                appointments = queries.get_appointments(date=today, technicien=None)
                upcoming = []
                for appt in appointments:
                    if appt.get('client_external_id') == entity_id:
                        upcoming.append({
                            'date': appt.get('appointment_date', ''),
                            'time': appt.get('appointment_time', 'N/A'),
                            'title': appt.get('title', ''),
                            'description': appt.get('description', ''),
                            'assigned_to': appt.get('technicien', '')
                        })
                details['upcoming_appointments'] = upcoming[:10]  # Limiter à 10
            except Exception as e:
                print(f"⚠️ Erreur prochains RV pour {entity_id}: {e}")
                details['upcoming_appointments'] = []

            # Timeline summary (client + contacts, fenêtre large)
            timeline_summary = build_timeline_summary(entity_id, contact_ids)
            details['timeline_summary'] = timeline_summary

            def _note_from_entry(entry: dict) -> str:
                return str(entry.get('text') or '').strip()

            service_notes_from_timeline = [
                f"{entry.get('date', '')}: {_note_from_entry(entry)}".strip(': ')
                for entry in (timeline_summary.get('recent_entries') or [])
                if _note_from_entry(entry)
            ]

            # Fusionner notes timeline + notes contacts (si ajoutées plus haut)
            details['service_history'] = service_notes_from_timeline + service_notes

            # NOUVEAU: Calculer les frais de déplacement pour ce client
            try:
                from modules.travel_fees.calculator import TravelFeeCalculator

                # Construire l'adresse complète du client
                address_parts = []
                if details.get('address'):
                    address_parts.append(details['address'])
                if details.get('city'):
                    address_parts.append(details['city'])
                if details.get('postal_code'):
                    address_parts.append(details['postal_code'])

                full_address = ', '.join(address_parts) if address_parts else None

                if full_address:
                    calculator = TravelFeeCalculator()
                    results = calculator.calculate_all_technicians(full_address)

                    # Trier par coût croissant
                    results_sorted = sorted(results, key=lambda x: x.total_fee)

                    # Formater pour le frontend
                    details['travel_fees'] = {
                        'destination': full_address,
                        'cheapest_technician': results_sorted[0].technician_name if results_sorted else None,
                        'results': [
                            {
                                'technician_name': r.technician_name,
                                'distance_km': r.distance_km,
                                'duration_minutes': r.duration_minutes,
                                'distance_fee': r.distance_fee,
                                'time_fee': r.time_fee,
                                'total_fee': r.total_fee,
                                'is_free': r.is_free
                            }
                            for r in results_sorted
                        ]
                    }
                else:
                    details['travel_fees'] = None
            except Exception as e:
                print(f"⚠️ Erreur calcul frais déplacement pour {entity_id}: {e}")
                details['travel_fees'] = None
        else:
            # Pour les contacts: pas d'enrichissement
            details['client_notes'] = ''
            details['pianos'] = []
            details['service_history'] = []
            details['associated_contacts'] = []
            details['upcoming_appointments'] = []
            details['timeline_summary'] = None
            details['travel_fees'] = None

        return details
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Erreur dans /assistant/client/{client_id}: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/client/{client_id}/feedback")
async def add_client_feedback(client_id: str, payload: AdminFeedbackPayload):
    """
    Ajoute une note interne (admin) pour un client.
    Ces notes peuvent être utilisées pour affiner les résumés.
    """
    try:
        if not payload.note or not payload.note.strip():
            raise HTTPException(status_code=400, detail="Note vide")

        queries = get_queries()
        ok = queries.add_admin_feedback(
            client_id=client_id,
            user_email=payload.user_email or "unknown",
            note=payload.note.strip()
        )
        if not ok:
            raise HTTPException(status_code=500, detail="Impossible d'enregistrer la note")

        return {"status": "ok"}

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Erreur add_client_feedback {client_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health", response_model=HealthResponse)
async def health():
    """
    Vérifie l'état de santé de l'assistant.

    Returns:
        État des composants
    """
    try:
        # Vérifier parser
        parser = get_parser()
        parser_loaded = parser is not None

        # Vérifier queries
        queries = get_queries()
        queries_loaded = queries is not None

        # Vérifier vector search
        try:
            vector_search = get_vector_search()
            vector_search_loaded = True
            vector_index_size = len(vector_search.index_data.get('texts', []))
        except Exception as e:
            print(f"⚠️ Vector search non chargé: {e}")
            vector_search_loaded = False
            vector_index_size = 0

        # Déterminer le statut global
        status = "healthy" if (parser_loaded and queries_loaded and vector_search_loaded) else "degraded"

        return HealthResponse(
            status=status,
            parser_loaded=parser_loaded,
            queries_loaded=queries_loaded,
            vector_search_loaded=vector_search_loaded,
            vector_index_size=vector_index_size
        )

    except Exception as e:
        print(f"❌ Erreur dans /assistant/health: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# Helpers pour formater les réponses
# ============================================================

def _format_time(time_str: str, date_str: str = '') -> str:
    """
    Formate une heure depuis différents formats possibles et convertit en heure de Toronto.
    
    Args:
        time_str: Heure au format string (peut être TIME, TIMESTAMP, ISO, etc.)
        date_str: Date au format string (optionnel, pour créer un datetime complet)
        
    Returns:
        Heure formatée en HH:MM (24h) en heure de Toronto, ou 'N/A' si invalide
    """
    if not time_str or time_str == 'N/A':
        return 'N/A'
    
    # Fuseau horaire de Montréal
    montreal_tz = ZoneInfo('America/Montreal')
    utc_tz = timezone.utc
    
    # Log pour déboguer (à retirer après vérification)
    print(f"🔍 Formatage heure: '{time_str}' (type: {type(time_str)})")
    
    try:
        # Si c'est un timestamp ISO avec fuseau horaire (format Supabase)
        if 'T' in time_str or '+' in time_str or 'Z' in time_str:
            # Nettoyer le format (remplacer Z par +00:00 pour UTC)
            clean_str = time_str.replace('Z', '+00:00')
            
            # Parser la date/heure ISO
            try:
                # Essayer de parser avec fromisoformat (gère les fuseaux horaires)
                dt = datetime.fromisoformat(clean_str)
                # Si pas de fuseau horaire, assumer UTC
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=utc_tz)
                else:
                    # Convertir d'abord en UTC pour normaliser
                    dt = dt.astimezone(utc_tz)
            except ValueError:
                # Si fromisoformat échoue, essayer sans le fuseau horaire
                clean_str_no_tz = clean_str.split('+')[0].split('-')[0].split('Z')[0]
                dt = datetime.fromisoformat(clean_str_no_tz)
                dt = dt.replace(tzinfo=utc_tz)
            
            # Convertir en heure de Montréal
            dt_montreal = dt.astimezone(montreal_tz)
            return dt_montreal.strftime('%H:%M')
        
        # Si c'est juste une heure au format HH:MM ou HH:MM:SS (sans date)
        # Les heures sont DÉJÀ converties en heure de Toronto dans queries.py
        # Ne PAS reconvertir - juste formater
        if ':' in time_str and 'T' not in time_str and '+' not in time_str and 'Z' not in time_str:
            parts = time_str.split(':')
            if len(parts) >= 2:
                try:
                    hour = int(parts[0])
                    minute = int(parts[1][:2])  # Ignorer les secondes
                    # Les heures sont déjà en heure locale, juste formater
                    return f"{hour:02d}:{minute:02d}"
                except ValueError:
                    # Fallback: retourner tel quel si on ne peut pas parser
                    return f"{parts[0].zfill(2)}:{parts[1][:2]}"
        
        # Si c'est un timestamp numérique
        if time_str.replace('.', '').replace('-', '').isdigit():
            dt = datetime.fromtimestamp(float(time_str), tz=utc_tz)
            dt_toronto = dt.astimezone(toronto_tz)
            return dt_toronto.strftime('%H:%M')
            
    except (ValueError, AttributeError, TypeError) as e:
        print(f"⚠️ Erreur formatage heure '{time_str}': {e}")
        # Fallback: essayer d'extraire HH:MM manuellement
        if ':' in time_str:
            parts = time_str.split(':')
            if len(parts) >= 2:
                return f"{parts[0].zfill(2)}:{parts[1][:2]}"
    
    return 'N/A'


def _format_response(query_type: QueryType, results: Dict[str, Any]):
    """
    Formate la réponse selon le type de requête.

    Args:
        query_type: Type de requête
        results: Résultats de la requête

    Returns:
        Réponse formatée en texte, ou dict avec 'text' et données structurées
    """
    if query_type == QueryType.APPOINTMENTS:
        # Vérifier s'il y a un message d'erreur (ex: non-technicien demandant "mes rv")
        if 'message' in results:
            return results['message']

        count = results.get('count', 0)
        date = results.get('date', '')
        date_range = results.get('date_range')
        data = results.get('data', [])

        # Message pour plage de dates ou date unique
        if date_range:
            period_str = f"du {date_range['start']} au {date_range['end']}"
            if count == 0:
                return f"Aucun rendez-vous trouvé {period_str}."
            response = f"📅 **{count} rendez-vous {period_str}:**\n\n"
        else:
            if count == 0:
                return f"Aucun rendez-vous trouvé pour le {date}."
            response = f"📅 **{count} rendez-vous le {date}:**\n\n"

        for appt in data[:10]:  # Limiter à 10 pour éviter les réponses trop longues
            # Extraire les données de l'appointment
            appointment_date = appt.get('appointment_date', '')
            appointment_time_raw = appt.get('appointment_time', 'N/A')
            # Passer aussi la date pour créer un datetime complet si nécessaire
            appointment_time = _format_time(appointment_time_raw, appointment_date)
            
            # Extraire le nom du client
            client_name = _extract_client_name(appt)
            client_external_id = appt.get('client_external_id', '')
            
            # Extraire la ville depuis la jointure (si présente)
            client_data = appt.get('gazelle_clients', {})
            if isinstance(client_data, list) and len(client_data) > 0:
                client_data = client_data[0]
            client_city = client_data.get('city', '') if isinstance(client_data, dict) else ''
            
            location = appt.get('location', '')
            description = appt.get('description', '')

            # Afficher la date seulement si c'est une plage
            if date_range:
                response += f"- **{appointment_date} {appointment_time}** : {client_name}"
            else:
                response += f"- **{appointment_time}** : {client_name}"

            # Ajouter la ville ou l'adresse si disponible
            if client_city:
                response += f" ({client_city})"
            elif location:
                response += f" ({location})"
            
            # Ajouter description si disponible et différente du titre
            if description and description != client_name:
                desc_short = description[:50].replace('\n', ' ')
                response += f" - {desc_short}"
            
            response += "\n"

        if count > 10:
            response += f"\n... et {count - 10} autres rendez-vous."

        return response

    elif query_type in [QueryType.SEARCH_CLIENT, QueryType.SEARCH_PIANO]:
        search_terms = results.get('search_terms', [])
        data = results.get('data', []) or []
        entity_type = "clients" if query_type == QueryType.SEARCH_CLIENT else "pianos"

        if not data:
            return f"Aucun {entity_type[:-1]} trouvé pour: {' '.join(search_terms)}"

        # ======================================
        # Recherche de clients (déduplication)
        # ======================================
        if query_type == QueryType.SEARCH_CLIENT:
            deduped_entities = {}

            def _normalize_client(item):
                source = item.get('_source', 'client')
                city = item.get('city', '')

                if source == 'contact':
                    first_name = item.get('first_name', '')
                    last_name = item.get('last_name', '')
                    display_name = f"{first_name} {last_name}".strip()
                    base_id = item.get('client_external_id') or item.get('external_id') or item.get('id')
                    # Si on a un client_external_id, considérer que l'entité pointe vers le client
                    if item.get('client_external_id'):
                        source = 'client'
                        base_id = item.get('client_external_id')
                else:
                    display_name = item.get('company_name') or item.get('name') or 'N/A'
                    base_id = item.get('external_id') or item.get('id')

                # Clé de déduplication: nom normalisé (en minuscules, sans espaces multiples)
                normalized_name = ' '.join(display_name.lower().split())
                dedupe_key = normalized_name if normalized_name and normalized_name != 'n/a' else base_id

                return {
                    'id': base_id or item.get('external_id') or item.get('id'),
                    'name': display_name,
                    'city': city,
                    'source': source,
                    'dedupe_key': dedupe_key
                }

            # Garder l'ordre d'apparition, préférer les fiches client aux contacts
            for item in data[:20]:
                normalized = _normalize_client(item)
                if not normalized['dedupe_key']:
                    continue

                # Debug: afficher la clé de déduplication
                print(f"🔍 Déduplication: '{normalized['name']}' -> clé='{normalized['dedupe_key']}' source={normalized['source']} id={normalized['id']}")

                existing = deduped_entities.get(normalized['dedupe_key'])
                if existing is None:
                    # Première occurrence de ce nom
                    deduped_entities[normalized['dedupe_key']] = normalized
                    print(f"  ✅ Ajouté (première occurrence)")
                elif normalized['source'] == 'client' and existing['source'] != 'client':
                    # Remplacer un contact par un client avec le même nom
                    deduped_entities[normalized['dedupe_key']] = normalized
                    print(f"  🔄 Remplacé contact par client")
                else:
                    # Doublon ignoré
                    print(f"  ⏭️  Ignoré (doublon)")

            unique_entities = list(deduped_entities.values())
            unique_count = len(unique_entities)

            response = f"🔍 **{unique_count} {entity_type} trouvés:**\n\n"
            clickable_entities = []

            for entity in unique_entities[:10]:
                response += f"- **{entity['name']}**"
                if entity['city']:
                    response += f" ({entity['city']})"
                # Ne pas tagger [Contact] si on a basculé sur l'ID client
                if entity['source'] == 'contact' and not (entity['id'] or "").startswith('cli_'):
                    response += " [Contact]"
                response += "\n"

                if entity['id']:
                    clickable_entities.append({
                        'id': entity['id'],
                        'name': entity['name'],
                        # Si l'ID pointe vers un client, considérer type=client pour le modal
                        'type': 'client' if (entity['id'] or "").startswith('cli_') else entity['source'],
                        'city': entity['city']
                    })

            # Indiquer s'il reste des résultats après déduplication
            extra_results = results.get('count', 0) - unique_count
            if extra_results > 0:
                response += f"\n... et {extra_results} autres résultats."

            return {
                'text': response,
                'entities': clickable_entities
            }

        # ======================================
        # Recherche de pianos (pas d'entités cliquables)
        # ======================================
        response = f"🔍 **{len(data)} {entity_type} trouvés:**\n\n"
        for piano in data[:10]:
            brand = piano.get('brand', 'N/A')
            model = piano.get('model', '')
            serial = piano.get('serial_number', '')

            response += f"- **{brand} {model}**"
            if serial:
                response += f" (S/N: {serial})"
            response += "\n"

        if len(data) > 10:
            response += f"\n... et {len(data) - 10} autres résultats."

        return response

    elif query_type == QueryType.SUMMARY:
        summary_data = results.get('data', {})
        period = summary_data.get('period', {})
        appt_count = summary_data.get('appointments_count', 0)
        timeline_count = summary_data.get('timeline_entries_count', 0)

        response = f"📊 **Résumé d'activité**\n\n"
        response += f"**Période:** {period.get('start')} → {period.get('end')}\n\n"
        response += f"- **Rendez-vous:** {appt_count}\n"
        response += f"- **Événements timeline:** {timeline_count}\n"

        return response

    elif query_type == QueryType.STATS:
        return _format_response(QueryType.SUMMARY, results)

    elif query_type == QueryType.TIMELINE:
        # Vérifier s'il y a une erreur
        if 'error' in results:
            return f"❌ {results['error']}"

        count = results.get('count', 0)
        entity_name = results.get('entity_name', results.get('entity_id', ''))

        if count == 0:
            return f"Aucun événement trouvé dans l'historique de **{entity_name}**."

        data = results.get('data', [])
        response = f"📜 **Historique de {entity_name}** ({count} événements au total):\n\n"

        # Afficher jusqu'à 20 entrées (limit=20 dans queries.py)
        for entry in data[:20]:
            date = entry.get('created_at', 'N/A')[:10]
            event_type = entry.get('event_type', 'N/A')
            description = entry.get('description', '')

            response += f"- **{date}** [{event_type}]: {description}\n"

        if count > 20:
            response += f"\n... et {count - 20} autres événements plus anciens."

        return response

    else:
        return "Type de requête non supporté."


def _enrich_appointments(appointments: list, queries) -> list:
    """
    Enrichit les rendez-vous avec les détails complets des clients.
    Même logique que dans train_summaries.py.
    """
    import requests
    
    for appt in appointments:
        entity_id = appt.get('client_external_id')
        if not entity_id:
            continue
        
        is_client = entity_id.startswith('cli_')
        is_contact = entity_id.startswith('con_')
        
        # Chercher l'entité (client ou contact)
        results = queries.search_clients([entity_id])
        if not results:
            continue
        
        entity = results[0]
        
        if is_contact:
            # Pour les contacts, juste les infos de base
            appt['client_name'] = f"{entity.get('first_name', '')} {entity.get('last_name', '')}".strip() or entity.get('name', 'N/A')
            appt['client_address'] = entity.get('address', '')
            appt['client_city'] = entity.get('city', '')
            appt['client_phone'] = entity.get('phone', '')
            continue
        
        if is_client:
            # Pour les clients, enrichissement complet
            appt['client_name'] = entity.get('company_name', 'N/A')
            appt['client_address'] = entity.get('address', '')
            appt['client_city'] = entity.get('city', '')
            appt['client_phone'] = entity.get('phone', '')
            appt['client_notes'] = entity.get('notes', '') or entity.get('note', '') or entity.get('description', '')
            
            # Récupérer les pianos avec leurs notes
            try:
                pianos_url = f"{queries.storage.api_url}/gazelle_pianos?client_external_id=eq.{entity_id}&select=external_id,notes,make,model,serial_number,type,year,location&limit=10"
                pianos_response = requests.get(pianos_url, headers=queries.storage._get_headers())
                if pianos_response.status_code == 200:
                    pianos = pianos_response.json()
                    appt['pianos'] = []
                    for piano in pianos:
                        piano_info = {
                            'external_id': piano.get('external_id', ''),
                            'make': piano.get('make', ''),
                            'model': piano.get('model', ''),
                            'serial_number': piano.get('serial_number', ''),
                            'type': piano.get('type', ''),
                            'year': piano.get('year', ''),
                            'location': piano.get('location', ''),
                            'notes': piano.get('notes', '')
                        }
                        if piano_info['make'] or piano_info['model'] or piano_info['notes']:
                            appt['pianos'].append(piano_info)
            except Exception as e:
                print(f"⚠️ Erreur récupération pianos: {e}")
            
            # Récupérer l'historique de service (timeline)
            try:
                service_notes = []
                timeline_entries_client = queries.get_timeline_entries(entity_id, entity_type='client', limit=20)
                
                # Chercher aussi les timeline des pianos
                if appt.get('pianos'):
                    for piano in appt['pianos']:
                        piano_id = piano.get('external_id')
                        if piano_id:
                            piano_timeline = queries.get_timeline_entries(piano_id, entity_type='piano', limit=10)
                            timeline_entries_client.extend(piano_timeline)
                
                # Extraire les notes
                for e in timeline_entries_client:
                    note = e.get('notes') or e.get('description') or e.get('content') or e.get('note') or e.get('text') or e.get('summary')
                    if note:
                        service_notes.append(str(note))
                
                if service_notes:
                    appt['service_history_notes'] = service_notes[:10]
            except Exception as e:
                print(f"⚠️ Erreur timeline {entity_id}: {e}")
            
            # Récupérer les contacts associés
            try:
                contacts_url = f"{queries.storage.api_url}/gazelle_contacts?client_external_id=eq.{entity_id}&limit=10"
                contacts_response = requests.get(contacts_url, headers=queries.storage._get_headers())
                if contacts_response.status_code == 200:
                    contacts = contacts_response.json()
                    if contacts:
                        appt['associated_contacts'] = [
                            {
                                'name': f"{c.get('first_name', '')} {c.get('last_name', '')}".strip() or c.get('name', 'N/A'),
                                'role': c.get('role') or c.get('title') or '',
                                'phone': c.get('phone') or c.get('telephone') or '',
                                'email': c.get('email', '')
                            }
                            for c in contacts[:5]
                        ]
            except Exception as e:
                print(f"⚠️ Erreur contacts associés {entity_id}: {e}")
    
    return appointments


def _extract_client_name(appt: Dict[str, Any]) -> str:
    """
    Extrait le nom du client depuis un appointment.
    
    Args:
        appt: Dictionnaire appointment
        
    Returns:
        Nom du client ou 'Client inconnu'
    """
    # 1. Essayer depuis la jointure gazelle_clients (si présente)
    client_data = appt.get('gazelle_clients', {})
    if isinstance(client_data, list) and len(client_data) > 0:
        client_data = client_data[0]
    
    if client_data and isinstance(client_data, dict):
        name = client_data.get('company_name')
        if name:
            return name
    
    # 2. Fallback: utiliser title (contient souvent le nom du client)
    title = appt.get('title', '')
    if title and title.strip():
        return title.strip()
    
    # 3. Dernier recours: description
    description = appt.get('description', '')
    if description and description.strip():
        # Prendre les premiers mots de la description
        return description.strip().split('\n')[0].split('.')[0][:50]
    
    return 'Client inconnu'


def _format_vector_response(results: list) -> str:
    """
    Formate la réponse depuis la recherche vectorielle.

    Args:
        results: Résultats de vector_search

    Returns:
        Réponse formatée
    """
    if not results:
        return "Aucun résultat pertinent trouvé."

    response = "🔍 **Voici ce que j'ai trouvé:**\n\n"

    for i, result in enumerate(results[:3], 1):
        text = result['text']
        source = result['source']
        similarity = result['similarity']

        # Limiter la longueur du texte
        if len(text) > 300:
            text = text[:297] + "..."

        response += f"**{i}. [{source}]** (Pertinence: {similarity:.0%})\n"
        response += f"{text}\n\n"

    return response
