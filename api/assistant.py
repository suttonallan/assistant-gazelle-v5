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

        return ChatResponse(
            question=question,
            answer=answer,
            query_type=query_type.value,
            confidence=confidence,
            data=results,
            vector_search_used=False
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
            date_str = appt.get('date', '')
            time = appt.get('time', 'N/A')
            client = appt.get('client_name', 'Client inconnu')
            address = appt.get('address', '')

            # Afficher la date seulement si c'est une plage
            if date_range:
                response += f"- **{date_str} {time}** : {client}"
            else:
                response += f"- **{time}** : {client}"

            if address:
                response += f" ({address})"
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
