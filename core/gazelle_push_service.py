#!/usr/bin/env python3
"""
Service de Push Intelligent vers Gazelle API.

Ce service gère:
- Identification des pianos prêts pour push (completed + work_completed + sync pending/modified/error)
- Push via push_technician_service_with_measurements (service note + measurements automatiques)
- Gestion des erreurs avec retry logic
- Mise à jour du sync_status dans Supabase

Usage:
    service = GazellePushService()
    result = service.push_batch(piano_ids=["ins_abc123", "ins_def456"])
"""

import time
from datetime import datetime
from typing import List, Dict, Any, Optional
from core.gazelle_api_client import GazelleAPIClient
from core.supabase_storage import SupabaseStorage


class GazellePushService:
    """Service pour push intelligent de pianos vers Gazelle."""

    def __init__(self):
        """Initialise le service avec clients API."""
        self.api_client = GazelleAPIClient()
        self.supabase = SupabaseStorage()

    def get_pianos_ready_for_push(
        self,
        tournee_id: Optional[str] = None,
        piano_ids: Optional[List[str]] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Récupère les pianos prêts à être envoyés vers Gazelle.

        Args:
            tournee_id: Filtrer par tournée spécifique
            piano_ids: Liste explicite de piano IDs (prioritaire sur tournee_id)
            limit: Nombre maximum de pianos à retourner

        Returns:
            Liste de dicts avec piano_id, travail, observations, etc.

        Critères:
            - status = 'completed'
            - is_work_completed = true
            - sync_status IN ('pending', 'modified', 'error')
            - travail OR observations non NULL
        """
        # Construire la requête REST API Supabase
        import requests

        url = f"{self.supabase.api_url}/vincent_dindy_piano_updates"

        # Filtres de base (communs à tous les cas)
        params = {
            'status': 'eq.completed',
            'is_work_completed': 'eq.true',
            'sync_status': 'in.(pending,modified,error)',
            'select': 'piano_id,travail,observations,completed_in_tournee_id,sync_status,updated_at,a_faire',
            'limit': limit,
            'order': 'updated_at.desc'
        }

        # Filtrer par piano_ids si fourni
        if piano_ids:
            # Convertir la liste en format Supabase: (id1,id2,id3)
            ids_str = ','.join([f'"{pid}"' for pid in piano_ids])
            params['piano_id'] = f'in.({ids_str})'
        elif tournee_id:
            # Filtrer par tournée
            params['completed_in_tournee_id'] = f'eq.{tournee_id}'

        # Filtrer: au moins travail OU observations doit être non-null
        # Utiliser 'or' filter: https://postgrest.org/en/stable/api.html#operators
        params['or'] = '(travail.not.is.null,observations.not.is.null)'

        try:
            response = requests.get(url, headers=self.supabase._get_headers(), params=params)

            if response.status_code == 200:
                return response.json()
            else:
                print(f"⚠️ Erreur lors de la récupération des pianos prêts: {response.status_code} - {response.text}")
                return []
        except Exception as e:
            print(f"⚠️ Exception lors de la récupération des pianos prêts: {e}")
            return []

    def push_piano_to_gazelle(
        self,
        piano_data: Dict[str, Any],
        technician_id: str = "usr_HcCiFk7o0vZ9xAI0",  # Nick par défaut
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Push un piano vers Gazelle via push_technician_service_with_measurements.

        Args:
            piano_data: Dict contenant piano_id, travail, observations, etc.
            technician_id: ID du technicien qui a effectué le travail
            dry_run: Si True, simule le push sans l'exécuter

        Returns:
            Dict avec status (success/error), gazelle_event_id, measurement_created, error

        Process:
            1. Récupérer client_id du piano depuis Gazelle
            2. Créer note de service avec push_technician_service_with_measurements
            3. Parser température/humidité automatiquement
            4. Créer measurement si détecté
            5. Mettre à jour sync_status dans Supabase
        """
        piano_id = piano_data['piano_id']
        travail = piano_data.get('travail', '')
        observations = piano_data.get('observations', '')
        a_faire = piano_data.get('a_faire', '')
        completed_at = piano_data.get('completed_at')  # Date de complétion (si disponible)

        # Construire le message de service note
        # Fusionner toutes les notes : a_faire (Nick) + travail + observations (technicien)
        note_parts = []
        if a_faire:
            note_parts.append(f"📋 Note de Nick: {a_faire}")
        if travail:
            note_parts.append(f"🔧 Travail effectué: {travail}")
        if observations:
            note_parts.append(f"📝 Observations: {observations}")

        service_note = "\n\n".join(note_parts) if note_parts else "Service effectué"

        # Utiliser la date de complétion si disponible, sinon maintenant
        from datetime import datetime
        if completed_at:
            # Si completed_at est une string ISO, la convertir
            if isinstance(completed_at, str):
                event_date = completed_at
            else:
                event_date = completed_at.isoformat() if hasattr(completed_at, 'isoformat') else datetime.now().isoformat()
        else:
            # Fallback: utiliser updated_at si disponible, sinon maintenant
            updated_at = piano_data.get('updated_at')
            if updated_at:
                if isinstance(updated_at, str):
                    event_date = updated_at
                else:
                    event_date = updated_at.isoformat() if hasattr(updated_at, 'isoformat') else datetime.now().isoformat()
            else:
                event_date = datetime.now().isoformat()

        if dry_run:
            return {
                'status': 'success',
                'piano_id': piano_id,
                'message': 'Dry run - aucune action effectuée',
                'service_note': service_note
            }

        try:
            # 1. Récupérer client_id du piano
            piano_query = """
            query GetPianoClient($pianoId: String!) {
                piano(id: $pianoId) {
                    id
                    client {
                        id
                    }
                }
            }
            """
            piano_result = self.api_client._execute_query(piano_query, {"pianoId": piano_id})
            piano_gql_data = piano_result.get("data", {}).get("piano", {})

            if not piano_gql_data:
                raise ValueError(f"Piano {piano_id} non trouvé dans Gazelle")

            client_id = piano_gql_data.get("client", {}).get("id")
            if not client_id:
                raise ValueError(f"Piano {piano_id} n'a pas de client associé")

            # 2. Push service note + measurements avec la date de complétion
            result = self.api_client.push_technician_service_with_measurements(
                piano_id=piano_id,
                technician_note=service_note,
                service_type="TUNING",
                technician_id=technician_id,
                client_id=client_id,
                event_date=event_date  # Utiliser la date de complétion au lieu de maintenant
            )

            service_note_event = result['service_note']
            measurement = result.get('measurement')
            parsed_values = result.get('parsed_values')

            # 3. Mettre à jour sync_status dans Supabase
            self.supabase.client.rpc(
                'mark_piano_as_pushed',
                {
                    'p_piano_id': piano_id,
                    'p_gazelle_event_id': service_note_event['id']
                }
            ).execute()

            return {
                'status': 'success',
                'piano_id': piano_id,
                'gazelle_event_id': service_note_event['id'],
                'measurement_created': measurement is not None,
                'parsed_values': parsed_values,
                'service_note': service_note
            }

        except Exception as e:
            # Marquer comme erreur dans Supabase
            error_message = str(e)
            self.supabase.client.rpc(
                'mark_piano_push_error',
                {
                    'p_piano_id': piano_id,
                    'p_error_message': error_message
                }
            ).execute()

            return {
                'status': 'error',
                'piano_id': piano_id,
                'error': error_message
            }

    def push_batch(
        self,
        piano_ids: Optional[List[str]] = None,
        tournee_id: Optional[str] = None,
        technician_id: str = "usr_HcCiFk7o0vZ9xAI0",
        dry_run: bool = False,
        max_retries: int = 3,
        retry_delay: float = 1.0
    ) -> Dict[str, Any]:
        """
        Push multiple pianos vers Gazelle avec retry logic.

        Args:
            piano_ids: Liste de piano IDs à pusher (prioritaire)
            tournee_id: ID de tournée (si piano_ids non fourni)
            technician_id: ID du technicien
            dry_run: Si True, simule le push
            max_retries: Nombre de tentatives en cas d'erreur
            retry_delay: Délai entre tentatives (secondes)

        Returns:
            Dict avec:
                - success: bool
                - pushed_count: int
                - error_count: int
                - results: List[Dict]
                - summary: str
        """
        # 1. Récupérer pianos prêts pour push
        pianos_to_push = self.get_pianos_ready_for_push(
            tournee_id=tournee_id,
            piano_ids=piano_ids
        )

        if not pianos_to_push:
            return {
                'success': True,
                'pushed_count': 0,
                'error_count': 0,
                'results': [],
                'summary': 'Aucun piano prêt pour push'
            }

        results = []
        pushed_count = 0
        error_count = 0

        # 2. Push chaque piano
        for piano_data in pianos_to_push:
            piano_id = piano_data['piano_id']
            print(f"\n{'='*70}")
            print(f"Push piano: {piano_id}")
            print(f"{'='*70}")

            # Retry logic
            last_error = None
            for attempt in range(1, max_retries + 1):
                try:
                    result = self.push_piano_to_gazelle(
                        piano_data=piano_data,
                        technician_id=technician_id,
                        dry_run=dry_run
                    )

                    if result['status'] == 'success':
                        print(f"✅ Push réussi (tentative {attempt}/{max_retries})")
                        if result.get('gazelle_event_id'):
                            print(f"   Événement Gazelle: {result['gazelle_event_id']}")
                        if result.get('measurement_created'):
                            print(f"   Measurement créé: {result.get('parsed_values')}")

                        results.append(result)
                        pushed_count += 1
                        break  # Succès, passer au piano suivant

                    else:
                        # Erreur API, retry
                        last_error = result.get('error', 'Unknown error')
                        print(f"⚠️  Erreur (tentative {attempt}/{max_retries}): {last_error}")

                        if attempt < max_retries:
                            # Backoff exponentiel
                            delay = retry_delay * (2 ** (attempt - 1))
                            print(f"   Retry dans {delay}s...")
                            time.sleep(delay)
                        else:
                            # Max retries atteint
                            print(f"❌ Échec après {max_retries} tentatives")
                            results.append(result)
                            error_count += 1

                except Exception as e:
                    last_error = str(e)
                    print(f"❌ Exception (tentative {attempt}/{max_retries}): {last_error}")

                    if attempt < max_retries:
                        delay = retry_delay * (2 ** (attempt - 1))
                        print(f"   Retry dans {delay}s...")
                        time.sleep(delay)
                    else:
                        results.append({
                            'status': 'error',
                            'piano_id': piano_id,
                            'error': last_error
                        })
                        error_count += 1

        # 3. Résumé
        summary = f"{pushed_count}/{len(pianos_to_push)} pianos pushés avec succès"
        if error_count > 0:
            summary += f", {error_count} erreurs"

        print(f"\n{'='*70}")
        print(f"RÉSUMÉ: {summary}")
        print(f"{'='*70}\n")

        return {
            'success': error_count == 0,
            'pushed_count': pushed_count,
            'error_count': error_count,
            'total_pianos': len(pianos_to_push),
            'results': results,
            'summary': summary
        }

    def schedule_daily_push(
        self,
        tournee_id: Optional[str] = None,
        technician_id: str = "usr_HcCiFk7o0vZ9xAI0"
    ) -> Dict[str, Any]:
        """
        Exécute le push automatique quotidien (appelé par cron).

        Args:
            tournee_id: ID de tournée (optionnel)
            technician_id: ID du technicien

        Returns:
            Dict avec résultats du push

        Usage via cron:
            0 1 * * * /usr/bin/python3 /path/to/scripts/scheduled_push_to_gazelle.py
        """
        print(f"\n{'='*70}")
        print(f"PUSH AUTOMATIQUE QUOTIDIEN - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*70}\n")

        result = self.push_batch(
            tournee_id=tournee_id,
            technician_id=technician_id,
            dry_run=False
        )

        # Log résultats
        log_file = "/var/log/gazelle_push.log"  # Adapter selon environnement
        try:
            with open(log_file, 'a') as f:
                f.write(f"\n{datetime.now().isoformat()} - {result['summary']}\n")
                if result['error_count'] > 0:
                    f.write("Erreurs:\n")
                    for r in result['results']:
                        if r['status'] == 'error':
                            f.write(f"  - {r['piano_id']}: {r['error']}\n")
        except Exception as e:
            print(f"⚠️  Impossible d'écrire dans {log_file}: {e}")

        return result


def main():
    """Fonction principale pour tests manuels."""
    import argparse

    parser = argparse.ArgumentParser(description="Push pianos vers Gazelle")
    parser.add_argument('--piano-ids', nargs='+', help='IDs des pianos à pusher')
    parser.add_argument('--tournee-id', help='ID de la tournée')
    parser.add_argument('--technician-id', default='usr_HcCiFk7o0vZ9xAI0', help='ID du technicien')
    parser.add_argument('--dry-run', action='store_true', help='Simulation sans push réel')
    parser.add_argument('--scheduled', action='store_true', help='Mode scheduled (cron)')

    args = parser.parse_args()

    service = GazellePushService()

    if args.scheduled:
        result = service.schedule_daily_push(
            tournee_id=args.tournee_id,
            technician_id=args.technician_id
        )
    else:
        result = service.push_batch(
            piano_ids=args.piano_ids,
            tournee_id=args.tournee_id,
            technician_id=args.technician_id,
            dry_run=args.dry_run
        )

    print(f"\n{'='*70}")
    print("RÉSULTATS FINAUX")
    print(f"{'='*70}")
    print(f"Succès:  {result['pushed_count']}/{result.get('total_pianos', 0)}")
    print(f"Erreurs: {result['error_count']}")
    print(f"{'='*70}\n")


if __name__ == '__main__':
    main()
