#!/usr/bin/env python3
"""
Extensions du GazelleAPIClient pour mode incrémental rapide.

Optimisations basées sur spécifications GraphQL Gazelle:
1. Timeline: occurredAtGet avec date UTC (déjà implémenté)
2. Clients/Pianos: sortBy UPDATED_AT_DESC + early exit
3. Events: allEventsBatched avec sortBy DATE_DESC + filtre date

Objectif: <50 items/jour au lieu de 5000
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from .gazelle_api_client import GazelleAPIClient


def _ensure_tz_aware(dt: Optional[datetime]) -> Optional[datetime]:
    """Rend une datetime timezone-aware (UTC) si elle ne l'est pas."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        # Si naive, assumer UTC
        return dt.replace(tzinfo=ZoneInfo('UTC'))
    # Si déjà aware, s'assurer qu'elle est en UTC
    if dt.tzinfo != ZoneInfo('UTC'):
        return dt.astimezone(ZoneInfo('UTC'))
    return dt


class GazelleAPIClientIncremental(GazelleAPIClient):
    """Extension du client API avec mode incrémental optimisé."""

    def get_clients_incremental(
        self,
        last_sync_date: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Récupère les clients modifiés depuis last_sync_date.

        Mode incrémental avec early exit:
        - Trie par UPDATED_AT_DESC
        - Stop dès qu'on atteint un client plus vieux que last_sync_date

        Args:
            last_sync_date: Date de dernière sync (None = tous les clients)
            limit: Limite maximale (sécurité)

        Returns:
            Liste des clients modifiés depuis last_sync_date
        """
        # Convertir en ISO-8601 UTC si fourni
        min_date_iso = None
        if last_sync_date:
            min_date_iso = last_sync_date.isoformat()

        query = """
        query GetClientsIncremental($first: Int, $after: String, $sortBy: [ClientSort!]) {
            allClients(first: $first, after: $after, sortBy: $sortBy) {
                edges {
                    node {
                        id
                        companyName
                        personalNotes
                        preferenceNotes
                        status
                        tags
                        createdAt
                        updatedAt
                        defaultContact {
                            id
                            firstName
                            lastName
                            defaultEmail {
                                email
                            }
                            defaultPhone {
                                phoneNumber
                            }
                            defaultLocation {
                                street1
                                street2
                                municipality
                                postalCode
                                region
                            }
                        }
                    }
                }
                pageInfo {
                    hasNextPage
                    endCursor
                }
            }
        }
        """

        all_clients = []
        cursor = None
        page_count = 0
        early_exit = False

        while True:
            variables = {
                "first": 100,
                "sortBy": ["CREATED_AT_DESC"]  # Tri par date de création (plus récent d'abord)
            }
            if cursor:
                variables["after"] = cursor

            result = self._execute_query(query, variables)

            batch_data = result.get('data', {}).get('allClients', {})
            edges = batch_data.get('edges', [])
            page_info = batch_data.get('pageInfo', {})

            # Extraire nodes et vérifier early exit
            for edge in edges:
                node = edge.get('node')
                if not node:
                    continue

                # Early exit: Si createdAt < last_sync_date, on arrête
                # (les clients sont triés par CREATED_AT_DESC)
                if last_sync_date and node.get('createdAt'):
                    try:
                        # Parser createdAt et s'assurer qu'il est timezone-aware
                        created_at_str = node['createdAt']
                        if not created_at_str:
                            continue
                        
                        # Normaliser le format (Z → +00:00 pour fromisoformat)
                        if created_at_str.endswith('Z'):
                            created_at_str = created_at_str.replace('Z', '+00:00')
                        elif '+' not in created_at_str and '-' not in created_at_str[-6:]:
                            # Pas de timezone dans le string, ajouter UTC
                            created_at_str = created_at_str + '+00:00'
                        
                        created_at = datetime.fromisoformat(created_at_str)
                        # S'assurer que created_at est aware (UTC)
                        created_at = _ensure_tz_aware(created_at)
                        last_sync_aware = _ensure_tz_aware(last_sync_date)
                        
                        if created_at and last_sync_aware:
                            # Vérifier que les deux sont aware avant comparaison
                            if created_at.tzinfo is None or last_sync_aware.tzinfo is None:
                                print(f"⚠️ Datetime naive détecté: created_at.tzinfo={created_at.tzinfo}, last_sync_aware.tzinfo={last_sync_aware.tzinfo}")
                                # Forcer à être aware
                                if created_at.tzinfo is None:
                                    created_at = created_at.replace(tzinfo=ZoneInfo('UTC'))
                                if last_sync_aware.tzinfo is None:
                                    last_sync_aware = last_sync_aware.replace(tzinfo=ZoneInfo('UTC'))
                            
                            if created_at < last_sync_aware:
                                print(f"⏩ Early exit: Client {node['id']} plus vieux que last_sync ({created_at} < {last_sync_aware})")
                                early_exit = True
                                break
                    except Exception as e:
                        print(f"⚠️ Erreur parsing createdAt: {e}")
                        import traceback
                        traceback.print_exc()

                all_clients.append(node)

                # Limite de sécurité
                if limit and len(all_clients) >= limit:
                    print(f"⚠️ Limite {limit} atteinte")
                    early_exit = True
                    break

            page_count += 1
            print(f"📄 Page {page_count}: {len(edges)} clients récupérés (total: {len(all_clients)})")

            if early_exit:
                print(f"🛑 Arrêt early exit après {len(all_clients)} clients")
                break

            # Vérifier s'il y a une page suivante
            if not page_info.get('hasNextPage'):
                print("✅ Toutes les pages récupérées")
                break

            cursor = page_info.get('endCursor')

        print(f"✅ {len(all_clients)} clients modifiés récupérés (mode incrémental)")
        return all_clients

    def get_pianos_incremental(
        self,
        last_sync_date: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Récupère les pianos modifiés depuis last_sync_date.

        Mode incrémental avec early exit:
        - Trie par UPDATED_AT_DESC
        - Stop dès qu'on atteint un piano plus vieux que last_sync_date

        Args:
            last_sync_date: Date de dernière sync (None = tous les pianos)
            limit: Limite maximale (sécurité)

        Returns:
            Liste des pianos modifiés depuis last_sync_date
        """
        query = """
        query GetPianosIncremental($first: Int, $after: String, $sortBy: [PianoSort!]) {
            allPianos(first: $first, after: $after, sortBy: $sortBy) {
                edges {
                    node {
                        id
                        make
                        model
                        size
                        type
                        serialNumber
                        year
                        status
                        createdAt
                        updatedAt
                        client {
                            id
                            companyName
                        }
                    }
                }
                pageInfo {
                    hasNextPage
                    endCursor
                }
            }
        }
        """

        all_pianos = []
        cursor = None
        page_count = 0
        early_exit = False

        while True:
            variables = {
                "first": 100,
                "sortBy": ["CREATED_AT_DESC"]  # Tri par date de création (plus récent d'abord)
            }
            if cursor:
                variables["after"] = cursor

            result = self._execute_query(query, variables)

            batch_data = result.get('data', {}).get('allPianos', {})
            edges = batch_data.get('edges', [])
            page_info = batch_data.get('pageInfo', {})

            # Extraire nodes et vérifier early exit
            for edge in edges:
                node = edge.get('node')
                if not node:
                    continue

                # Early exit: Si createdAt < last_sync_date, on arrête
                # (les pianos sont triés par CREATED_AT_DESC)
                if last_sync_date and node.get('createdAt'):
                    try:
                        # Parser createdAt et s'assurer qu'il est timezone-aware
                        created_at_str = node['createdAt']
                        if not created_at_str:
                            continue
                        
                        # Normaliser le format (Z → +00:00 pour fromisoformat)
                        if created_at_str.endswith('Z'):
                            created_at_str = created_at_str.replace('Z', '+00:00')
                        elif '+' not in created_at_str and '-' not in created_at_str[-6:]:
                            # Pas de timezone dans le string, ajouter UTC
                            created_at_str = created_at_str + '+00:00'
                        
                        created_at = datetime.fromisoformat(created_at_str)
                        # S'assurer que created_at est aware (UTC)
                        created_at = _ensure_tz_aware(created_at)
                        last_sync_aware = _ensure_tz_aware(last_sync_date)
                        
                        if created_at and last_sync_aware:
                            # Vérifier que les deux sont aware avant comparaison
                            if created_at.tzinfo is None or last_sync_aware.tzinfo is None:
                                print(f"⚠️ Datetime naive détecté: created_at.tzinfo={created_at.tzinfo}, last_sync_aware.tzinfo={last_sync_aware.tzinfo}")
                                # Forcer à être aware
                                if created_at.tzinfo is None:
                                    created_at = created_at.replace(tzinfo=ZoneInfo('UTC'))
                                if last_sync_aware.tzinfo is None:
                                    last_sync_aware = last_sync_aware.replace(tzinfo=ZoneInfo('UTC'))
                            
                            if created_at < last_sync_aware:
                                print(f"⏩ Early exit: Piano {node['id']} plus vieux que last_sync ({created_at} < {last_sync_aware})")
                                early_exit = True
                                break
                    except Exception as e:
                        print(f"⚠️ Erreur parsing createdAt: {e}")
                        import traceback
                        traceback.print_exc()

                all_pianos.append(node)

                # Limite de sécurité
                if limit and len(all_pianos) >= limit:
                    print(f"⚠️ Limite {limit} atteinte")
                    early_exit = True
                    break

            page_count += 1
            print(f"📄 Page {page_count}: {len(edges)} pianos récupérés (total: {len(all_pianos)})")

            if early_exit:
                print(f"🛑 Arrêt early exit après {len(all_pianos)} pianos")
                break

            # Vérifier s'il y a une page suivante
            if not page_info.get('hasNextPage'):
                print("✅ Toutes les pages récupérées")
                break

            cursor = page_info.get('endCursor')

        print(f"✅ {len(all_pianos)} pianos modifiés récupérés (mode incrémental)")
        return all_pianos

    def get_appointments_incremental(
        self,
        last_sync_date: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Récupère les RV depuis last_sync_date avec allEventsBatched optimisé.

        Optimisations:
        - sortBy: [DATE_DESC] (plus récents d'abord)
        - Filtre: start >= last_sync_date - 7 jours (fenêtre glissante)
        - Early exit si RV trop vieux

        Args:
            last_sync_date: Date de dernière sync (défaut: now - 7 jours)
            limit: Limite maximale

        Returns:
            Liste des RV récents/modifiés
        """
        from core.timezone_utils import format_for_gazelle_filter

        # Date minimale: last_sync - 7 jours OU now - 7 jours
        if last_sync_date:
            min_date = last_sync_date - timedelta(days=7)
        else:
            min_date = datetime.now() - timedelta(days=7)

        # Convertir en date seule (YYYY-MM-DD) pour filtre Gazelle CoreDate
        start_date_filter = min_date.strftime('%Y-%m-%d')

        print(f"📅 Mode incrémental: RV depuis {start_date_filter}")

        query = """
        query GetAppointmentsIncremental($first: Int, $after: String, $filters: PrivateAllEventsFilter, $sortBy: [EventSort!]) {
            allEventsBatched(first: $first, after: $after, filters: $filters, sortBy: $sortBy) {
                edges {
                    node {
                        id
                        title
                        start
                        duration
                        status
                        notes
                        type
                        isAllDay
                        confirmedByClient
                        source
                        travelMode
                        createdAt
                        updatedAt
                        client {
                            id
                        }
                        user {
                            id
                        }
                        createdBy {
                            id
                        }
                        allEventPianos {
                            nodes {
                                piano {
                                    id
                                }
                            }
                        }
                    }
                }
                pageInfo {
                    hasNextPage
                    endCursor
                }
            }
        }
        """

        all_appointments = []
        cursor = None
        page_count = 0

        while True:
            variables = {
                "first": 100,
                "filters": {
                    "dateGet": start_date_filter  # Filtre par date >= min_date (CoreDate format)
                },
                "sortBy": ["START_DESC"]  # Plus récents d'abord (EventSort enum)
            }
            if cursor:
                variables["after"] = cursor

            result = self._execute_query(query, variables)

            batch_data = result.get('data', {}).get('allEventsBatched', {})
            edges = batch_data.get('edges', [])
            page_info = batch_data.get('pageInfo', {})

            # Extraire nodes
            nodes = [edge['node'] for edge in edges if 'node' in edge]
            all_appointments.extend(nodes)

            page_count += 1
            print(f"📄 Page {page_count}: {len(nodes)} RV récupérés (total: {len(all_appointments)})")

            # Limite de sécurité
            if limit and len(all_appointments) >= limit:
                print(f"⚠️ Limite {limit} atteinte")
                all_appointments = all_appointments[:limit]
                break

            # Vérifier s'il y a une page suivante
            if not page_info.get('hasNextPage'):
                print("✅ Toutes les pages récupérées")
                break

            cursor = page_info.get('endCursor')

        print(f"✅ {len(all_appointments)} RV récupérés (mode incrémental)")
        return all_appointments
