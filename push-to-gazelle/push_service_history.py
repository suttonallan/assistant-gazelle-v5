#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script condensé pour pousser l'historique de service Place des Arts vers Gazelle
Piano Technique Montréal - V5 (Supabase)

⚠️ PREMIÈRE FOIS - MODE SÉCURISÉ ⚠️

Étapes:
1. Test connexion Gazelle
2. Identification demandes à pousser
3. Test sur UNE demande
4. Poussée du reste (si validé)
"""

import os
import sys
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Ajouter le répertoire parent au path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.gazelle_api_client import GazelleAPIClient

# Configuration Supabase
USE_SUPABASE = bool(os.getenv("SUPABASE_HOST") or os.getenv("SUPABASE_URL"))


def get_db_connection():
    """Connexion Supabase PostgreSQL"""
    if not USE_SUPABASE:
        raise ValueError("Supabase non configuré. Définissez SUPABASE_URL dans .env")
    
    import psycopg2
    from dotenv import load_dotenv
    load_dotenv()
    
    supabase_url = os.getenv('SUPABASE_URL')
    if supabase_url:
        from urllib.parse import urlparse
        parsed = urlparse(supabase_url)
        host = parsed.hostname
        database = os.getenv('SUPABASE_DATABASE', 'postgres')
        user = os.getenv('SUPABASE_USER', 'postgres')
        password = os.getenv('SUPABASE_PASSWORD')
        port = os.getenv('SUPABASE_PORT', '5432')
    else:
        host = os.getenv('SUPABASE_HOST')
        database = os.getenv('SUPABASE_DATABASE', 'postgres')
        user = os.getenv('SUPABASE_USER', 'postgres')
        password = os.getenv('SUPABASE_PASSWORD')
        port = int(os.getenv('SUPABASE_PORT', '5432'))
    
    if not password:
        raise ValueError("SUPABASE_PASSWORD non défini")
    
    return psycopg2.connect(f"postgresql://{user}:{password}@{host}:{port}/{database}")


def get_requests_to_push() -> List[Dict]:
    """Récupère les demandes Place des Arts à pousser"""
    print("\n🔍 Identification des demandes à pousser...")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            pda."Id", pda."AppointmentId", pda."Piano", pda."Room",
            pda."ForWho", pda."Diapason", pda."AppointmentDate",
            pda."TechnicianId", pda."Notes", a."PianoId", a."StartAt"
        FROM "PlaceDesArtsRequests" pda
        INNER JOIN "Appointments" a ON pda."AppointmentId" = a."Id"
        WHERE pda."AppointmentId" IS NOT NULL
          AND pda."ServiceHistoryId" IS NULL
          AND pda."Status" IN ('ASSIGN_OK', 'COMPLETED')
        ORDER BY pda."AppointmentDate" DESC
    """)
    
    requests = []
    for row in cursor.fetchall():
        requests.append({
            'id': row[0], 'appointment_id': row[1], 'piano_name': row[2],
            'room': row[3], 'for_who': row[4], 'diapason': row[5],
            'appointment_date': row[6], 'technician_id': row[7],
            'notes': row[8], 'piano_id': row[9], 'start_at': row[10]
        })
    
    conn.close()
    print(f"✅ {len(requests)} demande(s) trouvée(s)")
    return requests


def create_timeline_entry_mutation(piano_id: str, occurred_at: datetime, title: str, details: str) -> str:
    """Crée la mutation GraphQL pour créer une entrée timeline"""
    occurred_at_iso = occurred_at.strftime("%Y-%m-%dT%H:%M:%SZ")
    title_escaped = title.replace('"', '\\"')
    details_escaped = details.replace('"', '\\"').replace('\n', '\\n')
    
    return f"""
    mutation CreateTimelineEntry {{
      createTimelineEntry(input: {{
        pianoId: "{piano_id}"
        occurredAt: "{occurred_at_iso}"
        entryType: SERVICE_ENTRY_MANUAL
        title: "{title_escaped}"
        details: "{details_escaped}"
      }}) {{
        id
        occurredAt
        entryType
        title
      }}
    }}
    """


def format_details(request: Dict) -> Tuple[str, str]:
    """Formate titre et détails"""
    title = f"Place des Arts - {request['room']}"
    details = f"Pour: {request['for_who']}\nSalle: {request['room']}\nDiapason: {request['diapason']} Hz"
    if request.get('notes'):
        details += f"\n\nNotes: {request['notes']}"
    return title, details


def push_request(request: Dict, api_client: GazelleAPIClient) -> Optional[str]:
    """Pousse une demande vers Gazelle"""
    if not request.get('piano_id'):
        print(f"   ⚠️  Pas de PianoId pour {request['piano_name']}")
        return None
    
    occurred_at = request['start_at'] or request['appointment_date']
    if isinstance(occurred_at, str):
        try:
            occurred_at = datetime.fromisoformat(occurred_at.replace('Z', '+00:00'))
        except:
            occurred_at = datetime.now()
    
    title, details = format_details(request)
    mutation = create_timeline_entry_mutation(request['piano_id'], occurred_at, title, details)
    
    try:
        result = api_client._execute_query(mutation)
        if result and "data" in result and "createTimelineEntry" in result["data"]:
            return result["data"]["createTimelineEntry"].get("id")
    except Exception as e:
        print(f"   ❌ Erreur: {e}")
        return None


def update_db(request_id: str, service_history_id: str) -> bool:
    """Met à jour ServiceHistoryId dans Supabase"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            'UPDATE "PlaceDesArtsRequests" SET "ServiceHistoryId" = %s, "UpdatedAt" = CURRENT_TIMESTAMP WHERE "Id" = %s',
            (service_history_id, request_id)
        )
        conn.commit()
        conn.close()
        return True
    except:
        return False


def main():
    print("\n" + "="*60)
    print("🦌 PUSH SERVICE HISTORY VERS GAZELLE")
    print("   V5 (Supabase) - PREMIÈRE FOIS")
    print("="*60)
    
    # Initialiser client API
    try:
        api_client = GazelleAPIClient()
        print("✅ Client API initialisé")
    except Exception as e:
        print(f"❌ Erreur client API: {e}")
        return
    
    # Test connexion
    try:
        api_client.get_clients(limit=1)
        print("✅ Connexion Gazelle OK")
    except Exception as e:
        print(f"❌ Connexion échouée: {e}")
        return
    
    # Récupérer demandes
    requests = get_requests_to_push()
    if not requests:
        print("✅ Aucune demande à pousser")
        return
    
    # Test sur première demande
    print(f"\n🧪 TEST sur: {requests[0]['piano_name']} - {requests[0]['room']}")
    response = input("❓ Continuer? (oui/non): ").strip().lower()
    if response not in ['oui', 'o', 'yes', 'y']:
        print("❌ Annulé")
        return
    
    timeline_id = push_request(requests[0], api_client)
    if not timeline_id:
        print("❌ Test échoué")
        return
    
    print(f"✅ TimelineEntry créée: {timeline_id}")
    if update_db(requests[0]['id'], timeline_id):
        print("✅ Base de données mise à jour")
    
    # Pousser le reste
    if len(requests) > 1:
        response = input(f"\n❓ Pousser les {len(requests)-1} autres? (oui/non): ").strip().lower()
        if response in ['oui', 'o', 'yes', 'y']:
            success = 0
            failed = 0
            for req in requests[1:]:
                tid = push_request(req, api_client)
                if tid:
                    if update_db(req['id'], tid):
                        success += 1
                        print(f"   ✅ {req['piano_name']}")
                    else:
                        failed += 1
                else:
                    failed += 1
            print(f"\n📊 Résultats: {success} succès, {failed} échecs")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Annulé")
    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        import traceback
        traceback.print_exc()


