#!/usr/bin/env python3
"""
Assistant v6 API Endpoint

Endpoint FastAPI pour tester le chat v6 en parallèle avec v5.

Usage:
- v5: POST http://localhost:8000/assistant/chat
- v6: POST http://localhost:8000/v6/assistant/chat
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any

# Charger les variables d'environnement depuis le .env du projet parent
env_path = Path(__file__).parent.parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

# Validation stricte des variables critiques
REQUIRED_ENV_VARS = ['SUPABASE_URL', 'SUPABASE_KEY']
missing_vars = [var for var in REQUIRED_ENV_VARS if not os.getenv(var) and not os.getenv(var.replace('KEY', 'SERVICE_ROLE_KEY'))]

if missing_vars:
    print("="*80)
    print("❌ ERREUR: Variables d'environnement manquantes")
    print("="*80)
    for var in missing_vars:
        print(f"   - {var}")
    print("\n💡 Solution:")
    print(f"   1. Créez un fichier .env dans: {env_path.parent}")
    print("   2. Ajoutez ces variables:")
    print("      SUPABASE_URL=https://xxx.supabase.co")
    print("      SUPABASE_KEY=xxx")
    print("="*80)
    sys.exit(1)

print("✅ Variables d'environnement chargées depuis:", env_path)
print(f"   SUPABASE_URL: {os.getenv('SUPABASE_URL')[:30]}...")
print(f"   SUPABASE_KEY: {'✓ défini' if os.getenv('SUPABASE_KEY') or os.getenv('SUPABASE_SERVICE_ROLE_KEY') else '✗ manquant'}")

# Ajouter le parent au path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from modules.assistant.services.queries_v6 import QueriesServiceV6

router = APIRouter()

# Instance globale du service (utilise les tables Gazelle directement)
service = QueriesServiceV6()


class ChatRequest(BaseModel):
    """Requête de chat (compatible avec v5)"""
    question: str
    context: Dict[str, Any] = {}


class ChatResponse(BaseModel):
    """Réponse de chat"""
    response: str
    data: Dict[str, Any] = {}
    version: str = "v6"


@router.post("/assistant/chat", response_model=ChatResponse)
async def chat_v6(request: ChatRequest):
    """
    Endpoint de chat v6.

    Compatible avec l'interface v5, mais utilise la nouvelle architecture.

    Args:
        request: Question de l'utilisateur

    Returns:
        Réponse formatée

    Exemple:
        POST /v6/assistant/chat
        {
            "question": "montre-moi l'historique complet de Monique Hallé avec toutes les notes de service"
        }

        Réponse:
        {
            "response": "📜 Historique de Monique Hallé (153 événements):\\n\\n- 2024-01-15: Accordage...",
            "data": {
                "type": "timeline",
                "client_name": "Monique Hallé",
                "piano_count": 2,
                "count": 153,
                ...
            },
            "version": "v6"
        }
    """
    try:
        # Exécuter la requête
        result = service.execute_query(request.question, debug=True)

        # Formater la réponse selon le type
        response_text = format_response(result)

        return ChatResponse(
            response=response_text,
            data=result,
            version="v6"
        )

    except Exception as e:
        print(f"❌ Erreur chat v6: {e}")
        import traceback
        traceback.print_exc()

        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors du traitement de la requête: {str(e)}"
        )


def format_response(result: Dict[str, Any]) -> str:
    """
    Formate les résultats en texte lisible.

    Args:
        result: Résultats de la requête

    Returns:
        Texte formaté pour l'utilisateur
    """
    result_type = result.get('type', 'unknown')

    # TIMELINE
    if result_type == 'timeline':
        if 'error' in result:
            return f"❌ {result['error']}"

        client_name = result.get('client_name', 'Client')
        piano_count = result.get('piano_count', 0)
        count = result.get('count', 0)
        total = result.get('total', 0)
        entries = result.get('entries', [])

        if count == 0:
            return f"Aucun événement trouvé dans l'historique de **{client_name}**."

        response = f"📜 **Historique de {client_name}**\n\n"
        response += f"🎹 {piano_count} piano{'s' if piano_count > 1 else ''} trouvé{'s' if piano_count > 1 else ''}\n"
        response += f"📊 {count} événements pertinents (sur {total} total)\n\n"

        # Afficher les 20 premières entrées
        for entry in entries[:20]:
            # Utiliser entry_date au lieu de created_at (qui est NULL)
            date_raw = entry.get('entry_date') or entry.get('created_at') or 'N/A'
            date = date_raw[:10] if date_raw != 'N/A' else 'N/A'
            title = entry.get('title', '')
            description = entry.get('description', '')

            # Utiliser titre ou description
            text = title or description or 'Note'
            if len(text) > 100:
                text = text[:97] + '...'

            response += f"- **{date}**: {text}\n"

        if count > 20:
            response += f"\n... et {count - 20} autres événements.\n"

        return response

    # SEARCH_CLIENT
    elif result_type == 'search_client':
        count = result.get('count', 0)
        clients = result.get('clients', [])

        if count == 0:
            return "Aucun client trouvé."

        response = f"🔍 **{count} client{'s' if count > 1 else ''} trouvé{'s' if count > 1 else ''}:**\n\n"

        for client in clients:
            # Utiliser display_name de la vue SQL
            name = client.get('display_name') or client.get('company_name', 'N/A')
            client_id = client.get('client_external_id') or client.get('external_id') or client.get('id')
            source_type = client.get('source_type', 'client')
            source = 'Contact' if source_type == 'contact' else 'Client'
            piano_count = client.get('piano_count', 0)
            city = client.get('client_city', '')

            response += f"- **{name}**"
            if city:
                response += f" ({city})"
            if source == 'Contact':
                response += f" [Contact]"
            if piano_count > 0:
                response += f" - {piano_count} piano{'s' if piano_count > 1 else ''}"
            response += "\n"

        return response

    # APPOINTMENTS
    elif result_type == 'appointments':
        count = result.get('count', 0)
        period = result.get('period', '')
        appointments = result.get('appointments', [])

        if count == 0:
            return f"Aucun rendez-vous {period}."

        response = f"📅 **{count} rendez-vous {period}:**\n\n"

        for appt in appointments[:20]:
            date = appt.get('appointment_date', 'N/A')
            time = appt.get('appointment_time', '')
            title = appt.get('title', '')
            description = appt.get('description', '')
            technicien = appt.get('technicien', '')

            # Afficher date + heure + titre
            response += f"- **{date} {time}**"
            if title:
                response += f": {title}"
            if technicien:
                response += f" ({technicien})"
            response += "\n"

            # Ajouter description si présente
            if description and description != title:
                desc_short = description[:80].replace('\n', ' ')
                response += f"  _{desc_short}_\n"

        if count > 20:
            response += f"\n... et {count - 20} autres rendez-vous."

        return response

    # CLIENT_INFO
    elif result_type == 'client_info':
        if 'error' in result:
            return f"❌ {result['error']}"

        client = result.get('client', {})
        name = client.get('display_name', 'N/A')
        is_contact = client.get('is_contact', False)
        is_active = client.get('is_active', True)
        piano_count = client.get('piano_count', 0)

        address = client.get('address', '')
        city = client.get('city', '')
        postal_code = client.get('postal_code', '')
        phone = client.get('phone', '')
        email = client.get('email', '')

        response = f"📋 **Détails - {name}**\n\n"

        if is_contact:
            response += "👤 Type: Contact\n"
        else:
            response += "🏢 Type: Client\n"

        if not is_active:
            response += "⚠️  **DÉSACTIVÉ**\n"

        response += f"🎹 {piano_count} piano{'s' if piano_count > 1 else ''}\n\n"

        if address or city:
            response += "📍 **Adresse:**\n"
            if address:
                response += f"   {address}\n"
            if city or postal_code:
                response += f"   {city} {postal_code}\n"
            response += "\n"

        if phone:
            response += f"📞 {phone}\n"
        if email:
            response += f"📧 {email}\n"

        # Frais de déplacement
        travel_fees = client.get('travel_fees')
        if travel_fees and travel_fees.get('results'):
            response += "\n🚗 **Frais de déplacement:**\n\n"
            for fee in travel_fees['results']:
                tech = fee['technician_name']
                distance = fee['distance_km']
                duration = fee['duration_minutes']
                total = fee['total_fee']
                is_free = fee['is_free']

                response += f"  • **{tech}**: {distance:.1f} km, {duration} min"
                if is_free:
                    response += " - **GRATUIT** ✅\n"
                else:
                    response += f" - **{total:.2f}$**\n"

        return response

    # DEDUCTIONS
    elif result_type == 'deductions':
        return result.get('message', 'Fonctionnalité en cours de développement')

    # UNKNOWN
    else:
        return result.get('message', 'Je n\'ai pas compris votre question.')


@router.get("/assistant/health")
async def health_v6():
    """Endpoint de santé pour vérifier que v6 fonctionne"""
    return {
        "status": "ok",
        "version": "v6",
        "service": "Assistant v6 - Architecture Instrument-Centric"
    }


# Pour tester directement
if __name__ == "__main__":
    import uvicorn
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware

    app = FastAPI(title="Assistant v6")

    # CORS - Permet au frontend (fichier HTML local) d'appeler l'API
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Permet toutes les origines (y compris file://)
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(router, prefix="/v6")

    print("="*80)
    print("🚀 Démarrage serveur Assistant v6")
    print("="*80)
    print("   URL: http://localhost:8002")
    print("   Endpoint: POST http://localhost:8002/v6/assistant/chat")
    print("   Health: GET http://localhost:8002/v6/assistant/health")
    print("="*80)

    uvicorn.run(app, host="0.0.0.0", port=8002)
