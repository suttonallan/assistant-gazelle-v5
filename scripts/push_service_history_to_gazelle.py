#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script sécurisé pour pousser l'historique de service Place des Arts vers Gazelle
Piano Technique Montréal - V5 (Supabase)

⚠️ PREMIÈRE FOIS - MODE SÉCURISÉ ⚠️
Ce script teste d'abord la connexion, puis teste sur UNE seule demande avant de pousser le reste.

Étapes:
1. Test de connexion (lecture seule)
2. Identification des demandes à pousser
3. Test sur UNE seule demande
4. Validation manuelle
5. Poussée du reste (si validé)

✅ Utilise le client API Gazelle existant (core/gazelle_api_client.py)
✅ Compatible Supabase (PostgreSQL) et Mac
"""

import os
import sys
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Ajouter le répertoire parent au path pour importer les modules core
sys.path.insert(0, str(Path(__file__).parent.parent))

# Importer le client API Gazelle existant
from core.gazelle_api_client import GazelleAPIClient

# Configuration Supabase
USE_SUPABASE = bool(os.getenv("SUPABASE_HOST") or os.getenv("SUPABASE_URL"))


def get_db_connection():
    """Crée une connexion à Supabase (PostgreSQL)"""
    if not USE_SUPABASE:
        raise ValueError(
            "Supabase non configuré. Définissez SUPABASE_HOST ou SUPABASE_URL dans .env"
        )
    
    import psycopg2
    from dotenv import load_dotenv
    load_dotenv()
    
    # Essayer SUPABASE_URL d'abord (format Supabase standard)
    supabase_url = os.getenv('SUPABASE_URL')
    if supabase_url:
        # Parser l'URL Supabase: https://xxx.supabase.co
        # Extraire host et construire connection string
        from urllib.parse import urlparse
        parsed = urlparse(supabase_url)
        host = parsed.hostname
        database = os.getenv('SUPABASE_DATABASE', 'postgres')
        user = os.getenv('SUPABASE_USER', 'postgres')
        password = os.getenv('SUPABASE_PASSWORD')
        port = os.getenv('SUPABASE_PORT', '5432')
    else:
        # Format classique avec variables séparées
        SUPABASE_CONFIG = {
            'host': os.getenv('SUPABASE_HOST'),
            'database': os.getenv('SUPABASE_DATABASE', 'postgres'),
            'user': os.getenv('SUPABASE_USER', 'postgres'),
            'password': os.getenv('SUPABASE_PASSWORD'),
            'port': int(os.getenv('SUPABASE_PORT', '5432'))
        }
        host = SUPABASE_CONFIG['host']
        database = SUPABASE_CONFIG['database']
        user = SUPABASE_CONFIG['user']
        password = SUPABASE_CONFIG['password']
        port = SUPABASE_CONFIG['port']
    
    if not password:
        raise ValueError("SUPABASE_PASSWORD non défini")
    
    conn_string = f"postgresql://{user}:{password}@{host}:{port}/{database}"
    return psycopg2.connect(conn_string)


def get_requests_to_push() -> List[Dict]:
    """Récupère les demandes Place des Arts à pousser vers Gazelle"""
    print("\n" + "="*60)
    print("🔍 ÉTAPE 2: IDENTIFICATION DES DEMANDES À POUSSER")
    print("="*60)
    
    print(f"📊 Base de données: Supabase (PostgreSQL)")
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Récupérer les demandes qui ont:
        # - Un AppointmentId (RV créé dans Gazelle)
        # - Pas de ServiceHistoryId (pas encore poussé)
        # - Status = ASSIGN_OK ou COMPLETED
        
        # Requête PostgreSQL avec guillemets doubles
        query = """
        SELECT 
            pda."Id",
            pda."AppointmentId",
            pda."Piano",
            pda."Room",
            pda."ForWho",
            pda."Diapason",
            pda."AppointmentDate",
            pda."TechnicianId",
            pda."Notes",
            a."PianoId",
            a."StartAt",
            a."TechnicianId" AS "AppointmentTechnicianId"
        FROM "PlaceDesArtsRequests" pda
        INNER JOIN "Appointments" a ON pda."AppointmentId" = a."Id"
        WHERE pda."AppointmentId" IS NOT NULL
          AND pda."ServiceHistoryId" IS NULL
          AND pda."Status" IN ('ASSIGN_OK', 'COMPLETED')
        ORDER BY pda."AppointmentDate" DESC
        """
        
        cursor.execute(query)
        rows = cursor.fetchall()
        
        requests = []
        for row in rows:
            requests.append({
                'id': row[0],
                'appointment_id': row[1],
                'piano_name': row[2],
                'room': row[3],
                'for_who': row[4],
                'diapason': row[5],
                'appointment_date': row[6],
                'technician_id': row[7],
                'notes': row[8],
                'piano_id': row[9],
                'start_at': row[10],
                'appointment_technician_id': row[11]
            })
        
        conn.close()
        
        print(f"✅ [INFO] {len(requests)} demande(s) trouvée(s) à pousser")
        for i, req in enumerate(requests[:5], 1):  # Afficher les 5 premières
            print(f"   {i}. {req['piano_name']} - {req['room']} - {req['appointment_date']}")
        if len(requests) > 5:
            print(f"   ... et {len(requests) - 5} autre(s)")
        
        return requests
        
    except Exception as e:
        print(f"❌ [ERREUR] Impossible de récupérer les demandes: {e}")
        import traceback
        traceback.print_exc()
        return []


def create_timeline_entry_mutation(
    piano_id: str,
    occurred_at: datetime,
    title: str,
    details: str,
    entry_type: str = "SERVICE_ENTRY_MANUAL"
) -> str:
    """
    Crée une mutation GraphQL pour créer une entrée timeline
    
    ⚠️ NOTE: La structure exacte de la mutation doit être vérifiée dans la doc Gazelle.
    Cette mutation est une estimation basée sur les patterns GraphQL standards.
    """
    # Format de date ISO 8601
    occurred_at_iso = occurred_at.strftime("%Y-%m-%dT%H:%M:%SZ")
    
    # Échapper les guillemets dans les strings
    title_escaped = title.replace('"', '\\"')
    details_escaped = details.replace('"', '\\"').replace('\n', '\\n')
    
    mutation = f"""
    mutation CreateTimelineEntry {{
      createTimelineEntry(input: {{
        pianoId: "{piano_id}"
        occurredAt: "{occurred_at_iso}"
        entryType: {entry_type}
        title: "{title_escaped}"
        details: "{details_escaped}"
      }}) {{
        id
        occurredAt
        entryType
        title
        details
      }}
    }}
    """
    
    return mutation


def format_service_history_details(request: Dict) -> Tuple[str, str]:
    """Formate le titre et les détails pour l'entrée timeline"""
    # Titre
    title = f"Place des Arts - {request['room']}"
    
    # Détails
    details_parts = []
    details_parts.append(f"Pour: {request['for_who']}")
    details_parts.append(f"Salle: {request['room']}")
    details_parts.append(f"Diapason: {request['diapason']} Hz")
    
    if request.get('notes'):
        details_parts.append(f"\nNotes: {request['notes']}")
    
    details = "\n".join(details_parts)
    
    return title, details


def test_push_single_request(request: Dict, api_client: GazelleAPIClient) -> Optional[str]:
    """Teste la poussée d'UNE seule demande vers Gazelle"""
    print("\n" + "="*60)
    print("🧪 ÉTAPE 3: TEST SUR UNE SEULE DEMANDE")
    print("="*60)
    
    print(f"\n📋 Demande de test:")
    print(f"   ID: {request['id']}")
    print(f"   Piano: {request['piano_name']}")
    print(f"   Salle: {request['room']}")
    print(f"   Date: {request['appointment_date']}")
    print(f"   PianoId Gazelle: {request['piano_id']}")
    
    if not request.get('piano_id'):
        print("❌ [ERREUR] Pas de PianoId Gazelle - impossible de créer l'entrée timeline")
        return None
    
    # Formater les données
    occurred_at = request['start_at'] if request.get('start_at') else request['appointment_date']
    if isinstance(occurred_at, str):
        # Parser la date si c'est une string
        try:
            occurred_at = datetime.fromisoformat(occurred_at.replace('Z', '+00:00'))
        except:
            occurred_at = datetime.now()
    
    title, details = format_service_history_details(request)
    
    print(f"\n📝 Données à pousser:")
    print(f"   Titre: {title}")
    print(f"   Détails: {details[:100]}...")
    print(f"   Date: {occurred_at}")
    
    # ⚠️ IMPORTANT: Demander confirmation avant de pousser
    print("\n⚠️  ATTENTION: Vous êtes sur le point de créer une entrée timeline dans Gazelle!")
    print("   C'est la PREMIÈRE FOIS que vous poussez des données vers Gazelle.")
    print("   Cette action créera une entrée dans l'historique de service du piano.")
    
    response = input("\n❓ Voulez-vous continuer? (oui/non): ").strip().lower()
    if response not in ['oui', 'o', 'yes', 'y']:
        print("❌ [ANNULÉ] Opération annulée par l'utilisateur")
        return None
    
    # Créer la mutation
    mutation = create_timeline_entry_mutation(
        piano_id=request['piano_id'],
        occurred_at=occurred_at,
        title=title,
        details=details
    )
    
    print("\n🚀 Envoi de la requête à Gazelle...")
    
    try:
        # Utiliser le client API existant pour exécuter la mutation
        result = api_client._execute_query(mutation)
        
        if result and "data" in result:
            if "createTimelineEntry" in result["data"]:
                timeline_entry = result["data"]["createTimelineEntry"]
                timeline_id = timeline_entry.get("id")
                print(f"\n✅ [SUCCÈS] Entrée timeline créée dans Gazelle!")
                print(f"   TimelineEntry ID: {timeline_id}")
                return timeline_id
            else:
                print("❌ [ERREUR] Mutation réussie mais pas de données retournées")
                print(f"   Réponse: {json.dumps(result, indent=2)}")
                return None
        else:
            print("❌ [ÉCHEC] Impossible de créer l'entrée timeline")
            if result:
                print(f"   Réponse: {json.dumps(result, indent=2)}")
            return None
    except Exception as e:
        print(f"❌ [ERREUR] Erreur lors de l'appel API: {e}")
        import traceback
        traceback.print_exc()
        return None


def update_request_service_history_id(request_id: str, service_history_id: str) -> bool:
    """Met à jour le ServiceHistoryId dans la base de données"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE "PlaceDesArtsRequests"
            SET "ServiceHistoryId" = %s,
                "UpdatedAt" = CURRENT_TIMESTAMP
            WHERE "Id" = %s
        """, (service_history_id, request_id))
        
        conn.commit()
        conn.close()
        
        return True
    except Exception as e:
        print(f"❌ [ERREUR] Impossible de mettre à jour ServiceHistoryId: {e}")
        import traceback
        traceback.print_exc()
        return False


def push_all_requests(requests: List[Dict], skip_first: bool, api_client: GazelleAPIClient) -> Dict:
    """Pousse toutes les demandes vers Gazelle"""
    print("\n" + "="*60)
    print("🚀 ÉTAPE 4: POUSSÉE DE TOUTES LES DEMANDES")
    print("="*60)
    
    if skip_first:
        print("⏭️  [INFO] Saut de la première demande (déjà testée)")
        requests = requests[1:]
    
    if not requests:
        print("✅ [INFO] Aucune autre demande à pousser")
        return {'success': 0, 'failed': 0, 'skipped': 0}
    
    print(f"\n📊 {len(requests)} demande(s) à pousser")
    
    # Demander confirmation
    print("\n⚠️  ATTENTION: Vous êtes sur le point de pousser TOUTES les demandes restantes!")
    response = input("❓ Voulez-vous continuer? (oui/non): ").strip().lower()
    if response not in ['oui', 'o', 'yes', 'y']:
        print("❌ [ANNULÉ] Opération annulée par l'utilisateur")
        return {'success': 0, 'failed': 0, 'skipped': len(requests)}
    
    results = {'success': 0, 'failed': 0, 'errors': []}
    
    for i, request in enumerate(requests, 1):
        print(f"\n[{i}/{len(requests)}] Traitement: {request['piano_name']} - {request['room']}")
        
        if not request.get('piano_id'):
            print(f"   ⚠️  [SKIP] Pas de PianoId Gazelle")
            results['failed'] += 1
            results['errors'].append(f"{request['id']}: Pas de PianoId")
            continue
        
        # Formater les données
        occurred_at = request['start_at'] if request.get('start_at') else request['appointment_date']
        if isinstance(occurred_at, str):
            try:
                occurred_at = datetime.fromisoformat(occurred_at.replace('Z', '+00:00'))
            except:
                occurred_at = datetime.now()
        
        title, details = format_service_history_details(request)
        
        # Créer la mutation
        mutation = create_timeline_entry_mutation(
            piano_id=request['piano_id'],
            occurred_at=occurred_at,
            title=title,
            details=details
        )
        
        try:
            result = api_client._execute_query(mutation)
            
            if result and "data" in result and "createTimelineEntry" in result["data"]:
                timeline_id = result["data"]["createTimelineEntry"].get("id")
                
                # Mettre à jour la base de données
                if update_request_service_history_id(request['id'], timeline_id):
                    print(f"   ✅ [SUCCÈS] TimelineEntry créée: {timeline_id}")
                    results['success'] += 1
                else:
                    print(f"   ⚠️  [WARNING] TimelineEntry créée mais DB non mise à jour")
                    results['success'] += 1  # On compte quand même comme succès
            else:
                print(f"   ❌ [ÉCHEC] Impossible de créer TimelineEntry")
                error_msg = json.dumps(result, indent=2) if result else "Pas de réponse"
                results['errors'].append(f"{request['id']}: {error_msg}")
                results['failed'] += 1
        except Exception as e:
            print(f"   ❌ [ERREUR] {e}")
            results['errors'].append(f"{request['id']}: {str(e)}")
            results['failed'] += 1
    
    return results


def main():
    """Fonction principale"""
    print("\n" + "="*60)
    print("🦌 PUSH SERVICE HISTORY VERS GAZELLE")
    print("   Piano Technique Montréal - V5 (Supabase)")
    print("   PREMIÈRE FOIS - MODE SÉCURISÉ")
    print("="*60)
    
    # Afficher le type de base de données détecté
    print(f"\n📊 Base de données: Supabase (PostgreSQL)")
    
    # Étape 0: Initialiser le client API Gazelle
    print("\n📂 Initialisation du client API Gazelle...")
    try:
        api_client = GazelleAPIClient()
        print("✅ Client API initialisé")
    except Exception as e:
        print(f"\n❌ [ERREUR] Impossible d'initialiser le client API: {e}")
        print("   Vérifiez que config/token.json existe et que config/.env contient")
        print("   GAZELLE_CLIENT_ID et GAZELLE_CLIENT_SECRET")
        return
    
    # Étape 1: Tester la connexion
    print("\n🔍 Test de connexion à Gazelle...")
    try:
        # Test simple: récupérer quelques clients
        clients = api_client.get_clients(limit=1)
        print("✅ [SUCCÈS] Connexion à Gazelle réussie!")
    except Exception as e:
        print(f"\n❌ [ERREUR] Test de connexion échoué: {e}")
        print("   Vérifiez vos tokens et votre connexion internet")
        return
    
    # Étape 2: Identifier les demandes à pousser
    requests = get_requests_to_push()
    
    if not requests:
        print("\n✅ [INFO] Aucune demande à pousser")
        return
    
    # Étape 3: Tester sur une seule demande
    test_request = requests[0]
    timeline_id = test_push_single_request(test_request, api_client)
    
    if not timeline_id:
        print("\n❌ [ERREUR] Test échoué - arrêt du script")
        return
    
    # Mettre à jour la base de données pour la demande testée
    print(f"\n💾 Mise à jour de la base de données...")
    if update_request_service_history_id(test_request['id'], timeline_id):
        print("✅ Base de données mise à jour")
    else:
        print("⚠️  [WARNING] TimelineEntry créée mais DB non mise à jour")
    
    # Demander si on continue avec le reste
    print("\n" + "="*60)
    print("✅ TEST RÉUSSI!")
    print("="*60)
    print(f"   TimelineEntry créée: {timeline_id}")
    print(f"   Demande: {test_request['piano_name']} - {test_request['room']}")
    
    response = input("\n❓ Voulez-vous pousser les autres demandes maintenant? (oui/non): ").strip().lower()
    
    if response in ['oui', 'o', 'yes', 'y']:
        # Étape 4: Pousser le reste
        results = push_all_requests(requests, skip_first=True, api_client=api_client)
        
        print("\n" + "="*60)
        print("📊 RÉSULTATS FINAUX")
        print("="*60)
        print(f"   ✅ Succès: {results['success']}")
        print(f"   ❌ Échecs: {results['failed']}")
        
        if results['errors']:
            print(f"\n   Erreurs détaillées:")
            for error in results['errors'][:5]:  # Afficher les 5 premières
                print(f"   - {error}")
            if len(results['errors']) > 5:
                print(f"   ... et {len(results['errors']) - 5} autre(s)")
    else:
        print("\n✅ [INFO] Opération terminée - test réussi, reste non poussé")
        print("   Vous pouvez relancer le script plus tard pour pousser le reste")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ [ANNULÉ] Opération interrompue par l'utilisateur")
    except Exception as e:
        print(f"\n❌ [ERREUR] Erreur inattendue: {e}")
        import traceback
        traceback.print_exc()


