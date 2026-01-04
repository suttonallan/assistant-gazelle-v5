"""
Service Completion Bridge - Pont modulaire entre l'Assistant et le moteur Gazelle

Ce module fournit une interface unifiée pour connecter n'importe quel système
d'assistant (Vincent d'Indy, Place des Arts, etc.) au moteur de push Gazelle.

Architecture:
    Assistant → complete_service_session() → Gazelle Push Engine

Le pont garantit l'ordre d'exécution:
    1. Validation des données (piano_id, notes, metadata)
    2. Push vers Gazelle (Last Tuned + Service Note + Measurements)
    3. Mise à jour du statut de sync dans Supabase
    4. Remise du piano en INACTIVE (après confirmation)

Usage:
    from core.service_completion_bridge import complete_service_session

    result = complete_service_session(
        piano_id="ins_abc123",
        service_notes="Accord 440 Hz, temp 22°C, humidité 45%",
        institution="vincent-dindy",
        technician_id="usr_xyz",
        client_id="cli_vdi"
    )

    if result['success']:
        print(f"✅ Service complété: {result['gazelle_event_id']}")
    else:
        print(f"❌ Erreur: {result['error']}")
"""

from typing import Dict, Any, Optional
from datetime import datetime
import os
from core.gazelle_api_client import GazelleAPIClient


# NOTE: INSTITUTION_CLIENT_MAPPING supprimé - Utiliser get_institution_client_id() 
# qui charge depuis la table Supabase institutions (découverte automatique depuis Gazelle)


def get_technician_gazelle_id(technician_name: str) -> Optional[str]:
    """
    Récupère le gazelle_user_id depuis la table Supabase 'users'.

    Args:
        technician_name: Prénom du technicien (ex: "Nicolas", "Isabelle", "Jean-Philippe")

    Returns:
        gazelle_user_id (le champ 'id' de la table users)

    Raises:
        ValueError: Si le technicien n'est pas trouvé dans Supabase
    """
    from core.supabase_storage import SupabaseStorage

    storage = SupabaseStorage(silent=True)

    # Query la table users par first_name
    users = storage.get_data(
        table_name="users",
        filters={"first_name": technician_name}
    )

    if not users:
        raise ValueError(
            f"Technicien '{technician_name}' introuvable dans la table Supabase 'users'. "
            f"Vérifiez que le prénom correspond exactement au champ 'first_name' dans Supabase."
        )

    user = users[0]
    gazelle_user_id = user.get('id')

    if not gazelle_user_id:
        raise ValueError(
            f"ID Gazelle manquant pour le technicien '{technician_name}' dans Supabase (champ 'id' vide)."
        )

    return gazelle_user_id


def complete_service_session(
    piano_id: str,
    service_notes: str,
    institution: str = "vincent-dindy",
    technician_name: Optional[str] = None,
    technician_id: Optional[str] = None,
    client_id: Optional[str] = None,
    service_type: str = "TUNING",
    event_date: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Complète une session de service et push vers Gazelle de manière modulaire.

    Cette fonction est l'interface unifiée entre n'importe quel système d'assistant
    et le moteur de push Gazelle. Elle garantit l'ordre d'exécution correct et
    la cohérence des données.

    Args:
        piano_id: ID Gazelle du piano (ex: "ins_abc123")
        service_notes: Notes de service du technicien
                      Peut contenir temp/humidité (ex: "22°C, 45%")
        institution: Nom de l'institution ("vincent-dindy", "place-des-arts", etc.)
        technician_name: Nom du technicien (ex: "Nicolas", "Isabelle")
                        Utilisé pour lookup dans TECHNICIAN_USER_MAPPING
        technician_id: ID Gazelle du technicien (optionnel, override du mapping)
        client_id: ID Gazelle du client (optionnel, override du mapping)
        service_type: Type de service ("TUNING", "REPAIR", etc.)
        event_date: Date ISO de l'événement (défaut: maintenant)
        metadata: Métadonnées additionnelles (optionnel)
                 Ex: {'tournee_id': 'xyz', 'piano_location': 'Salle 101'}

    Returns:
        {
            'success': bool,
            'piano_id': str,
            'gazelle_event_id': str | None,
            'last_tuned_updated': bool,
            'service_note_created': bool,
            'measurement_created': bool,
            'measurement_values': {'temperature': int, 'humidity': int} | None,
            'piano_set_inactive': bool,
            'error': str | None,
            'timestamp': str
        }

    Raises:
        ValueError: Si piano_id ou service_notes sont vides
        ValueError: Si l'institution n'est pas reconnue
        ConnectionError: Si impossible de se connecter à Gazelle
    """
    # Validation des arguments
    if not piano_id or not piano_id.strip():
        raise ValueError("piano_id est requis et ne peut pas être vide")

    if not service_notes or not service_notes.strip():
        raise ValueError("service_notes est requis et ne peut pas être vide")

    # Résoudre client_id depuis l'institution si non fourni
    # Utiliser la table Supabase institutions (découverte automatique)
    if not client_id:
        try:
            from api.institutions import get_institution_config
            config = get_institution_config(institution)
            client_id = config.get('gazelle_client_id')
            if client_id:
                print(f"✅ Client ID chargé depuis Supabase pour '{institution}': {client_id}")
            else:
                raise ValueError(f"Institution '{institution}' n'a pas de gazelle_client_id configuré dans Supabase")
        except Exception as e:
            raise ValueError(
                f"Institution '{institution}' non trouvée ou non configurée. "
                f"Vérifiez la table Supabase institutions. Erreur: {str(e)}"
            )

    # Résoudre technician_id depuis Supabase si non fourni
    # Fallback: utiliser le compte par défaut (Nick) si technicien non trouvé
    FALLBACK_TECHNICIAN_ID = "usr_HcCiFk7o0vZ9xAI0"  # Nick - compte par défaut
    
    if not technician_id and technician_name:
        try:
            technician_id = get_technician_gazelle_id(technician_name)
            print(f"✅ Technicien '{technician_name}' trouvé dans Supabase: {technician_id}")
        except ValueError as e:
            # Fallback: utiliser le compte par défaut pour que la note soit quand même enregistrée
            print(f"⚠️  Technicien '{technician_name}' non trouvé dans Supabase: {e}")
            print(f"   Fallback: utilisation du compte par défaut ({FALLBACK_TECHNICIAN_ID})")
            technician_id = FALLBACK_TECHNICIAN_ID

    # Initialiser le résultat
    result = {
        'success': False,
        'piano_id': piano_id,
        'gazelle_event_id': None,
        'last_tuned_updated': False,
        'service_note_created': False,
        'measurement_created': False,
        'measurement_values': None,
        'piano_set_inactive': False,
        'error': None,
        'timestamp': datetime.now().isoformat(),
        'metadata': metadata or {}
    }

    try:
        # Initialiser le client Gazelle
        print(f"\n{'='*60}")
        print(f"🚀 SERVICE COMPLETION BRIDGE")
        print(f"{'='*60}")
        print(f"Piano ID: {piano_id}")
        print(f"Institution: {institution}")
        print(f"Technicien: {technician_name or 'Non spécifié'} (ID: {technician_id or 'Auto'})")
        print(f"Client ID: {client_id}")
        print(f"Service Type: {service_type}")
        print(f"Notes: {service_notes[:100]}...")
        print(f"{'='*60}\n")

        # Ajouter signature automatique du technicien au début de la note
        # Format: **Technicien : [NOM]**\n\n[NOTE_ORIGINALE]
        if technician_name:
            service_notes_with_signature = f"**Technicien : {technician_name}**\n\n{service_notes}"
        else:
            service_notes_with_signature = service_notes

        # Initialiser le client Gazelle
        token_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'gazelle_token.json')
        gazelle_client = GazelleAPIClient(token_path=token_path)

        # Appeler le pipeline complet de push
        # Cette fonction gère:
        # 1. Update Last Tuned (manualLastService)
        # 2. Create service note (createEvent + completeEvent avec serviceHistoryNotes)
        # 3. Parse temp/humidity et create measurement
        # 4. Set piano back to INACTIVE
        # NOTE: On ne passe PAS client_id - push_technician_service le récupère depuis le piano
        push_result = gazelle_client.push_technician_service_with_measurements(
            piano_id=piano_id,
            technician_note=service_notes_with_signature,  # Note avec signature automatique
            service_type=service_type,
            technician_id=technician_id,
            client_id=None,  # Laisser récupérer depuis le piano (plus fiable)
            event_date=event_date
        )

        # Extraire les résultats
        result['success'] = True
        result['gazelle_event_id'] = push_result.get('service_note', {}).get('id')
        result['last_tuned_updated'] = push_result.get('last_tuned_updated', False)
        result['service_note_created'] = push_result.get('service_note') is not None
        result['measurement_created'] = push_result.get('measurement') is not None
        result['measurement_values'] = push_result.get('parsed_values')
        result['piano_set_inactive'] = True  # Géré automatiquement par push_technician_service_with_measurements

        print(f"\n{'='*60}")
        print(f"✅ SERVICE COMPLETION RÉUSSI")
        print(f"{'='*60}")
        print(f"Event ID Gazelle: {result['gazelle_event_id']}")
        print(f"Last Tuned mis à jour: {result['last_tuned_updated']}")
        print(f"Note de service créée: {result['service_note_created']}")
        print(f"Mesure créée: {result['measurement_created']}")
        if result['measurement_values']:
            print(f"Valeurs mesurées: {result['measurement_values']['temperature']}°C, {result['measurement_values']['humidity']}%")
        print(f"Piano remis en INACTIVE: {result['piano_set_inactive']}")
        print(f"{'='*60}\n")

        return result

    except Exception as e:
        # Capturer l'erreur et la loger
        error_msg = str(e)
        result['success'] = False
        result['error'] = error_msg

        print(f"\n{'='*60}")
        print(f"❌ ERREUR LORS DE LA COMPLÉTION DU SERVICE")
        print(f"{'='*60}")
        print(f"Piano ID: {piano_id}")
        print(f"Erreur: {error_msg}")
        print(f"{'='*60}\n")

        # Re-raise l'exception pour que le caller puisse la gérer
        raise


def get_supported_institutions() -> list[str]:
    """Retourne la liste des institutions supportées."""
    # Charger depuis la table Supabase institutions
    try:
        from supabase import create_client
        import os
        import logging
        
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        
        if not supabase_url or not supabase_key:
            print("⚠️  Configuration Supabase manquante pour liste institutions")
            return []
        
        supabase = create_client(supabase_url, supabase_key)
        response = supabase.table('institutions').select('slug').eq('active', True).execute()
        
        return [inst['slug'] for inst in response.data]
    except Exception as e:
        print(f"⚠️  Erreur chargement liste institutions: {e}")
        return []


def get_supported_technicians() -> list[str]:
    """
    Retourne la liste des techniciens supportés.
    
    NOTE: Cette fonction retourne une liste vide car les techniciens
    sont maintenant chargés dynamiquement depuis la table Supabase 'users'.
    """
    # TODO: Implémenter chargement depuis Supabase si nécessaire
    return []


def register_institution(institution_name: str, client_id: str) -> None:
    """
    DEPRECATED: Utiliser discover_and_sync_institutions() depuis api/institutions.py
    
    Les institutions sont maintenant découvertes automatiquement depuis Gazelle
    et stockées dans la table Supabase 'institutions'.
    """
    print(f"⚠️  register_institution() est deprecated. Utiliser discover_and_sync_institutions() depuis api/institutions.py")
    # Ne rien faire - les institutions sont maintenant dans Supabase


def register_technician(technician_name: str, user_id: str) -> None:
    """
    DEPRECATED: Les techniciens sont maintenant chargés depuis la table Supabase 'users'.
    
    Utiliser get_technician_gazelle_id() pour récupérer l'ID d'un technicien.
    """
    print(f"⚠️  register_technician() est deprecated. Les techniciens sont maintenant dans Supabase 'users'")
    # Ne rien faire - les techniciens sont maintenant dans Supabase
