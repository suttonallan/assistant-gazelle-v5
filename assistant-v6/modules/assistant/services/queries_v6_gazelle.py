#!/usr/bin/env python3
"""
Queries v6 - Version FINALE avec Vues SQL Gazelle

Cette version reproduit exactement la logique de l'API GraphQL Gazelle
dans Supabase pour une performance optimale.

Architecture:
- Supabase = Cache local (rapide)
- Vues SQL = Réplication de la logique Gazelle
- GraphQL Schema = Source de vérité pour les relations

Basé sur: https://gazelleapp.io/docs/graphql/private/schema/privatequery.doc.html
"""

import os
import sys
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import requests

# Ajouter le parent au path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
from modules.storage.supabase import SupabaseStorage

from .parser_v6 import QueryType, parse_query, extract_entity_name


class QueriesServiceV6Gazelle:
    """
    Service de requêtes v6 - Réplication logique Gazelle

    Reproduit les queries GraphQL:
    - allClients(filters) → gazelle_client_search
    - allTimelineEntries(clientId, pianoId) → gazelle_client_timeline
    - allPianos(filters) → gazelle_piano_list
    """

    def __init__(self):
        """Initialise le service avec connexion Supabase"""
        self.storage = SupabaseStorage()
        print("✅ QueriesServiceV6Gazelle initialisé (logique Gazelle reproduite)")

    # =========================================================================
    # Reproduction de allClients(filters)
    # =========================================================================

    def search_clients(
        self,
        search_term: str,
        limit: int = 10,
        debug: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Reproduit: allClients(filters: {search: "..."})

        Vue utilisée: gazelle_client_search
        """
        try:
            url = f"{self.storage.api_url}/gazelle_client_search"
            url += "?select=*"
            url += f"&search_name=ilike.*{search_term}*"
            url += f"&limit={limit}"

            if debug:
                print(f"🔍 [Gazelle] allClients(search: '{search_term}')")

            response = requests.get(url, headers=self.storage._get_headers())

            if response.status_code == 200:
                results = response.json()
                if debug:
                    print(f"  ✅ Trouvé {len(results)} clients/contacts")
                    if results:
                        first = results[0]
                        print(f"     Premier: {first.get('display_name')} ({first.get('source_type')})")
                        print(f"     Pianos: {first.get('piano_count', 0)}, Timeline: {first.get('timeline_count', 0)}")
                return results
            else:
                if debug:
                    print(f"  ❌ Erreur {response.status_code}: {response.text}")
                return []

        except Exception as e:
            print(f"⚠️ Erreur search_clients: {e}")
            import traceback
            traceback.print_exc()
            return []

    # =========================================================================
    # Reproduction de allTimelineEntries(clientId, pianoId)
    # =========================================================================

    def get_timeline(
        self,
        client_id: str,
        limit: int = 100,
        entry_types: Optional[List[str]] = None,
        debug: bool = False
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Reproduit: allTimelineEntries(clientId: ID, types: [TimelineEntryType])

        Vue utilisée: gazelle_client_timeline

        Args:
            client_id: ID du client (comme clientId dans GraphQL)
            limit: Nombre max d'entrées (comme first dans GraphQL)
            entry_types: Types à filtrer (comme types dans GraphQL)
            debug: Mode debug

        Returns:
            Tuple (entries, total_count)
        """
        try:
            url = f"{self.storage.api_url}/gazelle_client_timeline"
            url += "?select=*"
            url += f"&client_id=eq.{client_id}"

            # Filter par types si spécifié (comme types: [TimelineEntryType])
            if entry_types:
                types_str = ",".join(entry_types)
                url += f"&entry_type=in.({types_str})"

            url += "&order=created_at.desc"
            url += f"&limit={limit}"

            if debug:
                print(f"🔍 [Gazelle] allTimelineEntries(clientId: '{client_id}', first: {limit})")
                if entry_types:
                    print(f"     types: {entry_types}")

            # Header pour compter le total (comme totalCount dans GraphQL)
            headers = self.storage._get_headers()
            headers["Prefer"] = "count=exact"

            response = requests.get(url, headers=headers)

            if response.status_code == 200:
                entries = response.json()

                # Extraire le total du header
                total = 0
                content_range = response.headers.get('Content-Range')
                if content_range:
                    total = int(content_range.split('/')[-1])

                if debug:
                    print(f"  ✅ Trouvé {len(entries)} entrées (total: {total})")
                    if entries:
                        first = entries[0]
                        print(f"     Dernière: {first.get('created_at')[:10]} - {first.get('title', 'N/A')}")
                        print(f"     Piano: {first.get('piano_make')} {first.get('piano_model')}")  # VERIFIED: piano_make

                return entries, total
            else:
                if debug:
                    print(f"  ❌ Erreur {response.status_code}: {response.text}")
                return [], 0

        except Exception as e:
            print(f"⚠️ Erreur get_timeline: {e}")
            import traceback
            traceback.print_exc()
            return [], 0

    # =========================================================================
    # Reproduction de allPianos(filters: {clientId})
    # =========================================================================

    def get_pianos(
        self,
        client_id: str,
        debug: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Reproduit: allPianos(filters: {clientId: ID})

        Vue utilisée: gazelle_piano_list
        """
        try:
            url = f"{self.storage.api_url}/gazelle_piano_list"
            url += "?select=*"
            url += f"&client_id=eq.{client_id}"

            if debug:
                print(f"🔍 [Gazelle] allPianos(clientId: '{client_id}')")

            response = requests.get(url, headers=self.storage._get_headers())

            if response.status_code == 200:
                pianos = response.json()
                if debug:
                    print(f"  ✅ Trouvé {len(pianos)} pianos")
                    for piano in pianos[:3]:  # Montrer les 3 premiers
                        print(f"     - {piano.get('make')} {piano.get('model')} ({piano.get('timeline_count', 0)} notes)")  # VERIFIED: make
                return pianos
            else:
                if debug:
                    print(f"  ❌ Erreur {response.status_code}: {response.text}")
                return []

        except Exception as e:
            print(f"⚠️ Erreur get_pianos: {e}")
            import traceback
            traceback.print_exc()
            return []

    # =========================================================================
    # Exécution de requêtes
    # =========================================================================

    def execute_query(self, question: str, debug: bool = True) -> Dict[str, Any]:
        """Point d'entrée principal: parse et exécute la requête."""
        print(f"\n{'='*80}")
        print(f"📝 Question: {question}")
        print(f"{'='*80}")

        # Parser la question
        query_type, confidence = parse_query(question)
        entity_name = extract_entity_name(question, query_type)

        if debug:
            print(f"🎯 Type: {query_type.value} (confiance: {confidence:.0%})")
            print(f"👤 Entité: '{entity_name}'")

        # Router
        if query_type == QueryType.TIMELINE:
            return self._execute_timeline_query(entity_name, debug=debug)
        elif query_type == QueryType.SEARCH_CLIENT:
            return self._execute_search_query(entity_name, debug=debug)
        elif query_type == QueryType.APPOINTMENTS:
            return {'type': 'appointments', 'message': 'En développement'}
        else:
            return {
                'type': 'unknown',
                'message': f'Type détecté: {query_type.value}',
                'confidence': confidence
            }

    def _execute_timeline_query(self, entity_name: str, debug: bool = False) -> Dict[str, Any]:
        """
        Exécute une requête TIMELINE.

        Reproduit la logique Gazelle:
        1. allClients(search) → Trouver le client
        2. allTimelineEntries(clientId) → Récupérer l'historique
        """
        # 1. Chercher client/contact (comme allClients)
        results = self.search_clients(entity_name, limit=1, debug=debug)

        if not results:
            return {
                'type': 'timeline',
                'error': f'Aucun client/contact trouvé pour: {entity_name}',
                'count': 0
            }

        result = results[0]
        source_type = result.get('source_type')
        display_name = result.get('display_name')
        client_id = result.get('client_id')
        piano_count = result.get('piano_count', 0)

        # Construire le nom d'affichage
        if source_type == 'contact':
            company = result.get('company_name')
            if company:
                display_name = f"{display_name} ({company})"
            print(f"\n👤 Contact trouvé: {display_name}")
        else:
            print(f"\n🏢 Client trouvé: {display_name}")

        print(f"🎹 {piano_count} piano{'s' if piano_count > 1 else ''}")

        # 2. Récupérer timeline (comme allTimelineEntries)
        entries, total = self.get_timeline(client_id, limit=100, debug=debug)

        # 3. Filtrer le bruit
        filtered_entries = self._filter_timeline_noise(entries)

        print(f"✅ Timeline: {len(filtered_entries)} entrées pertinentes (sur {total} total)")

        return {
            'type': 'timeline',
            'client_name': display_name,
            'client_id': client_id,
            'piano_count': piano_count,
            'count': len(filtered_entries),
            'total': total,
            'entries': filtered_entries[:20],
        }

    def _execute_search_query(self, entity_name: str, debug: bool = False) -> Dict[str, Any]:
        """Exécute une requête SEARCH_CLIENT (comme allClients)"""
        results = self.search_clients(entity_name, limit=10, debug=debug)

        return {
            'type': 'search_client',
            'count': len(results),
            'clients': results
        }

    def _filter_timeline_noise(self, entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filtre les entrées non pertinentes."""
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

        filtered = []
        for entry in entries:
            desc = (entry.get('description') or '').lower()
            is_noise = any(pattern in desc for pattern in exclude_patterns)
            if not is_noise:
                filtered.append(entry)

        return filtered


# Tests
if __name__ == "__main__":
    print("="*80)
    print("Assistant v6 - Logique Gazelle dans Supabase")
    print("="*80)

    service = QueriesServiceV6Gazelle()

    # Test
    print("\n🧪 Test: Timeline de Monique Hallé")
    result = service.execute_query(
        "montre-moi l'historique complet de Monique Hallé avec toutes les notes de service",
        debug=True
    )

    print(f"\n📊 Résultat:")
    print(f"   Type: {result.get('type')}")
    print(f"   Client: {result.get('client_name')}")
    print(f"   Pianos: {result.get('piano_count')}")
    print(f"   Entrées: {result.get('count')} / {result.get('total')}")

    if result.get('error'):
        print(f"   ⚠️  Erreur: {result.get('error')}")

    print("\n" + "="*80)
