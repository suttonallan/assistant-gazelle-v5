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
        answer = _format_response(query_type, results)
        
        # 6. Préparer les données structurées pour l'interactivité frontend
        structured_data = None
        if query_type == QueryType.APPOINTMENTS:
            # Enrichir les appointments avec les IDs clients pour permettre les clics
            appointments_data = results.get('data', [])
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
                        'technicien': appt.get('technicien', '')
                    }
                    for appt in appointments_data
                ]
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
    
    # Fuseau horaire de Toronto
    toronto_tz = ZoneInfo('America/Toronto')
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
            
            # Convertir en heure de Toronto
            dt_toronto = dt.astimezone(toronto_tz)
            return dt_toronto.strftime('%H:%M')
        
        # Si c'est juste une heure au format HH:MM ou HH:MM:SS (sans date)
        # ASSUMER QUE C'EST EN UTC et créer un datetime complet pour convertir
        if ':' in time_str and 'T' not in time_str and '+' not in time_str and 'Z' not in time_str:
            parts = time_str.split(':')
            if len(parts) >= 2:
                try:
                    hour_utc = int(parts[0])
                    minute_utc = int(parts[1][:2])  # Ignorer les secondes
                    
                    # Si on a une date, l'utiliser; sinon utiliser aujourd'hui
                    if date_str:
                        try:
                            # Parser la date (format YYYY-MM-DD)
                            date_parts = date_str.split('-')
                            if len(date_parts) == 3:
                                year = int(date_parts[0])
                                month = int(date_parts[1])
                                day = int(date_parts[2])
                                
                                # Créer un datetime en UTC avec la date du rendez-vous
                                dt_utc = datetime(year, month, day, hour_utc, minute_utc, tzinfo=utc_tz)
                            else:
                                # Date invalide, utiliser aujourd'hui
                                today = datetime.now(utc_tz)
                                dt_utc = datetime(today.year, today.month, today.day, hour_utc, minute_utc, tzinfo=utc_tz)
                        except (ValueError, IndexError):
                            # Date invalide, utiliser aujourd'hui
                            today = datetime.now(utc_tz)
                            dt_utc = datetime(today.year, today.month, today.day, hour_utc, minute_utc, tzinfo=utc_tz)
                    else:
                        # Pas de date fournie, utiliser aujourd'hui
                        today = datetime.now(utc_tz)
                        dt_utc = datetime(today.year, today.month, today.day, hour_utc, minute_utc, tzinfo=utc_tz)
                    
                    # Convertir en heure de Toronto
                    dt_toronto = dt_utc.astimezone(toronto_tz)
                    return dt_toronto.strftime('%H:%M')
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


def _format_response(query_type: QueryType, results: Dict[str, Any]) -> str:
    """
    Formate la réponse selon le type de requête.

    Args:
        query_type: Type de requête
        results: Résultats de la requête

    Returns:
        Réponse formatée en texte
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
        count = results.get('count', 0)
        search_terms = results.get('search_terms', [])
        data = results.get('data', [])

        entity_type = "clients" if query_type == QueryType.SEARCH_CLIENT else "pianos"

        if count == 0:
            return f"Aucun {entity_type[:-1]} trouvé pour: {' '.join(search_terms)}"

        response = f"🔍 **{count} {entity_type} trouvés:**\n\n"

        for item in data[:10]:
            if query_type == QueryType.SEARCH_CLIENT:
                name = item.get('name', 'N/A')
                first_name = item.get('first_name', '')
                city = item.get('city', '')
                response += f"- **{first_name} {name}**"
                if city:
                    response += f" ({city})"
            else:  # Piano
                brand = item.get('brand', 'N/A')
                model = item.get('model', '')
                serial = item.get('serial_number', '')
                response += f"- **{brand} {model}**"
                if serial:
                    response += f" (S/N: {serial})"

            response += "\n"

        if count > 10:
            response += f"\n... et {count - 10} autres résultats."

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
        count = results.get('count', 0)
        entity_id = results.get('entity_id', '')

        if count == 0:
            return f"Aucun événement trouvé pour l'entité: {entity_id}"

        data = results.get('data', [])
        response = f"📜 **Historique ({count} événements):**\n\n"

        for entry in data[:10]:
            date = entry.get('created_at', 'N/A')[:10]
            event_type = entry.get('event_type', 'N/A')
            description = entry.get('description', '')

            response += f"- **{date}** [{event_type}]: {description}\n"

        if count > 10:
            response += f"\n... et {count - 10} autres événements."

        return response

    else:
        return "Type de requête non supporté."


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
