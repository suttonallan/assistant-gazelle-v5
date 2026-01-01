#!/usr/bin/env python3
"""
Queries v6 - Logique Instrument-Centric

Pilier #1: Mapping Instrument-Centric
- Client → Pianos → Timeline
- Les notes de service sont liées aux pianos, pas aux clients

Pilier #3: Déduplication Propre
- Clé = nom normalisé (minuscules, sans espaces multiples)
- Priorité: client > contact

Pilier #4: Connexion Supabase Directe
- Accès direct via PostgREST API
- Tri sur created_at (occurred_at souvent vide)
"""

import os
import sys
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import requests

# Ajouter le parent au path pour importer SupabaseStorage
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
from modules.storage.supabase import SupabaseStorage

from .parser_v6 import QueryType, parse_query, extract_entity_name


class QueriesServiceV6:
    """Service de requêtes v6 avec architecture instrument-centric"""

    def __init__(self):
        """Initialise le service avec connexion Supabase"""
        self.storage = SupabaseStorage()
        print("✅ QueriesServiceV6 initialisé")

    # =========================================================================
    # Pilier #1: Mapping Instrument-Centric
    # =========================================================================

    def get_client_pianos(self, client_external_id: str, debug: bool = False) -> List[str]:
        """
        Récupère tous les piano_ids d'un client.

        C'est la clé du mapping instrument-centric:
        Client → Pianos → Timeline

        Args:
            client_external_id: External ID du client (format: cli_xxx)
            debug: Mode debug

        Returns:
            Liste des piano IDs
        """
        try:
            # Essayer différents endpoints
            piano_endpoints = ["gazelle.pianos", "gazelle_pianos", "pianos"]

            for endpoint in piano_endpoints:
                try:
                    url = f"{self.storage.api_url}/{endpoint}"
                    # CRITICAL: Chercher par client_external_id (pas client_id numérique!)
                    # La table gazelle_pianos lie les pianos aux clients via external_id
                    url += f"?select=id&client_external_id=eq.{client_external_id}"

                    if debug:
                        print(f"🎹 Recherche pianos dans {endpoint} pour client_external_id: {client_external_id}")

                    response = requests.get(url, headers=self.storage._get_headers())

                    if response.status_code == 200:
                        pianos = response.json()
                        piano_ids = [p.get('id') for p in pianos if p.get('id')]

                        if debug:
                            print(f"  ✅ Trouvé {len(piano_ids)} pianos")
                            if piano_ids and len(piano_ids) <= 5:
                                print(f"     IDs: {piano_ids}")

                        return piano_ids

                except Exception as e:
                    if debug:
                        print(f"  ⏭️  Endpoint {endpoint} non disponible: {e}")
                    continue

            if debug:
                print(f"❌ Aucun endpoint piano ne fonctionne")

            return []

        except Exception as e:
            print(f"⚠️ Erreur get_client_pianos: {e}")
            import traceback
            traceback.print_exc()
            return []

    def get_timeline_for_client(
        self,
        client_external_id: str,
        limit: int = 100,
        debug: bool = False
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Récupère les timeline entries pour un client.

        IMPORTANT: Dans Gazelle, les timeline entries sont liées au CLIENT
        via entity_id = client_external_id et entity_type = 'CLIENT'

        Args:
            client_external_id: External ID du client (format: cli_xxx)
            limit: Nombre max d'entrées
            debug: Mode debug

        Returns:
            Tuple (entries, total_count)
        """
        try:
            # Essayer différents endpoints
            timeline_endpoints = ["gazelle.timeline_entries", "gazelle_timeline_entries", "timeline_entries"]

            for endpoint in timeline_endpoints:
                try:
                    url = f"{self.storage.api_url}/{endpoint}"
                    url += "?select=*"

                    # CRITICAL: Filtrer par entity_id (client_external_id) + entity_type = 'CLIENT'
                    url += f"&entity_id=eq.{client_external_id}"
                    url += "&entity_type=eq.CLIENT"

                    # Trier par entry_date desc (ou created_at si entry_date est null)
                    url += "&order=entry_date.desc.nullslast,created_at.desc"

                    # Limiter les résultats
                    url += f"&limit={limit}"

                    if debug:
                        print(f"🔍 Requête timeline pour client: {client_external_id}")

                    # Header pour compter le total
                    headers = self.storage._get_headers()
                    headers["Prefer"] = "count=exact"

                    response = requests.get(url, headers=headers)

                    if response.status_code == 200:
                        entries = response.json()

                        # Récupérer le total count depuis l'header Content-Range
                        total_count = len(entries)
                        content_range = response.headers.get('Content-Range')
                        if content_range and '/' in content_range:
                            total_count = int(content_range.split('/')[1])

                        if debug:
                            print(f"  ✅ Trouvé {len(entries)} entrées (total: {total_count})")

                        return entries, total_count

                except Exception as e:
                    if debug:
                        print(f"  ⏭️  Endpoint {endpoint} non disponible: {e}")
                    continue

            # Aucun endpoint fonctionnel
            if debug:
                print(f"⚠️  Aucun endpoint timeline disponible")
            return [], 0

        except Exception as e:
            print(f"❌ Erreur get_timeline_for_client: {e}")
            import traceback
            traceback.print_exc()
            return [], 0

    def get_timeline_for_entities(
        self,
        entity_ids: List[str],
        limit: int = 100,
        debug: bool = False
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Récupère les timeline entries pour une liste d'entités (piano IDs).

        CRITICAL: Timeline entries sont liées aux PIANOS via piano_id,
                  pas aux clients!

        Args:
            entity_ids: Liste des piano IDs
            limit: Nombre max d'entrées
            debug: Mode debug

        Returns:
            Tuple (entries, total_count)
        """
        try:
            if not entity_ids:
                return [], 0

            # Essayer différents endpoints
            timeline_endpoints = ["gazelle.timeline_entries", "gazelle_timeline_entries", "timeline_entries"]

            for endpoint in timeline_endpoints:
                try:
                    url = f"{self.storage.api_url}/{endpoint}"
                    url += "?select=*"

                    # CRITICAL: Filtrer par entity_id + entity_type (schema Gazelle)
                    # timeline_entries utilise entity_id (générique) + entity_type ('Piano', 'Client', etc.)
                    # Format: entity_id=in.(id1,id2,id3)&entity_type=eq.Piano
                    ids_str = ",".join(str(id) for id in entity_ids)
                    url += f"&entity_id=in.({ids_str})"
                    url += "&entity_type=eq.Piano"

                    # Trier par created_at desc (occurred_at souvent vide selon guide)
                    url += "&order=created_at.desc"

                    # Limiter les résultats
                    url += f"&limit={limit}"

                    if debug:
                        print(f"🔍 Requête timeline dans {endpoint} pour {len(entity_ids)} pianos")

                    # Header pour compter le total
                    headers = self.storage._get_headers()
                    headers["Prefer"] = "count=exact"

                    response = requests.get(url, headers=headers)

                    if response.status_code == 200:
                        entries = response.json()

                        # Extraire le total du header Content-Range
                        total = 0
                        content_range = response.headers.get('Content-Range')
                        if content_range:
                            # Format: "0-19/153509"
                            total = int(content_range.split('/')[-1])

                        if debug:
                            print(f"  ✅ Trouvé {len(entries)} entrées (total: {total})")

                        return entries, total

                except Exception as e:
                    if debug:
                        print(f"  ⏭️  Endpoint {endpoint} non disponible: {e}")
                    continue

            if debug:
                print(f"❌ Aucun endpoint timeline ne fonctionne")

            return [], 0

        except Exception as e:
            print(f"⚠️ Erreur get_timeline_for_entities: {e}")
            import traceback
            traceback.print_exc()
            return [], 0

    # =========================================================================
    # Pilier #3: Déduplication Propre
    # =========================================================================

    def normalize_name(self, name: str) -> str:
        """
        Normalise un nom pour la déduplication.

        Args:
            name: Nom brut

        Returns:
            Nom normalisé (minuscules, sans espaces multiples)
        """
        if not name:
            return ""
        return " ".join(name.lower().split())

    def deduplicate_clients(
        self,
        clients: List[Dict[str, Any]],
        debug: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Déduplique une liste de clients par nom normalisé.

        Règle de priorité: client > contact

        Args:
            clients: Liste de clients/contacts
            debug: Mode debug

        Returns:
            Liste dédupliquée
        """
        deduped = {}

        for client in clients:
            # Construire le nom d'affichage
            first = client.get('first_name') or ''
            last = client.get('last_name') or ''
            display_name = f"{first} {last}".strip() or client.get('name') or 'N/A'

            # Clé de déduplication = nom normalisé
            dedupe_key = self.normalize_name(display_name)
            if not dedupe_key or dedupe_key == 'n/a':
                # Fallback sur l'ID si pas de nom valide
                dedupe_key = client.get('external_id') or client.get('id')

            # Déterminer le type
            source = 'client' if client.get('type') == 'client' else 'contact'

            if debug:
                print(f"🔍 Dédup: '{display_name}' → clé='{dedupe_key}' source={source}")

            # Déduplication avec priorité client > contact
            if dedupe_key not in deduped:
                deduped[dedupe_key] = client
                if debug:
                    print(f"  ✅ Ajouté (première occurrence)")
            elif source == 'client' and deduped[dedupe_key].get('type') != 'client':
                # Remplacer contact par client
                deduped[dedupe_key] = client
                if debug:
                    print(f"  🔄 Remplacé contact par client")
            else:
                if debug:
                    print(f"  ⏭️  Ignoré (doublon)")

        result = list(deduped.values())
        if debug:
            print(f"📊 Déduplication: {len(clients)} → {len(result)} clients")

        return result

    # =========================================================================
    # Recherche de clients
    # =========================================================================

    def search_clients(
        self,
        search_term: str,
        limit: int = 10,
        debug: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Recherche des clients ET contacts par nom (fuzzy search).

        Supporte:
        - Prénom seul: "Michelle" → cherche dans first_name
        - Nom seul: "Alie" → cherche dans last_name
        - Prénom + Nom: "Michelle Alie" → cherche first_name=Michelle AND last_name=Alie
        - Nom d'entreprise: "École Vincent-d'Indy" → cherche dans company_name

        Args:
            search_term: Terme de recherche
            limit: Nombre max de résultats
            debug: Mode debug

        Returns:
            Liste de résultats (contacts avec info client incluse)
        """
        try:
            results = []

            # Essayer différents endpoints (avec et sans namespace gazelle.)
            client_endpoints = ["gazelle.clients", "gazelle_clients", "clients"]
            contact_endpoints = ["gazelle.contacts", "gazelle_contacts", "contacts"]

            # Détecter si c'est un nom complet (2+ mots) ou un seul mot
            words = search_term.strip().split()
            is_full_name = len(words) >= 2

            # 1. Chercher dans CONTACTS (personnes comme "Monique Hallé" ou "Michelle Alie")
            # Inclure les infos du client parent via jointure
            for endpoint in contact_endpoints:
                try:
                    url = f"{self.storage.api_url}/{endpoint}"
                    # Joindre le client parent pour avoir l'entreprise
                    url += "?select=*,client:gazelle_clients(*)"

                    if is_full_name:
                        # Nom complet: "Michelle Alie" → first_name=Michelle AND last_name=Alie
                        # SYNTAXE PostgREST: column=ilike.pattern (pas column.ilike.pattern!)
                        first_name = words[0]
                        last_name = " ".join(words[1:])  # Gérer les noms composés
                        url += f"&first_name=ilike.*{first_name}*"
                        url += f"&last_name=ilike.*{last_name}*"
                    else:
                        # Un seul mot: chercher dans first_name OU last_name
                        # SYNTAXE PostgREST: or=(column=ilike.pattern,...)
                        url += f"&or=(first_name=ilike.*{search_term}*,last_name=ilike.*{search_term}*)"

                    url += f"&limit={limit}"

                    if debug:
                        mode = "prénom+nom (AND)" if is_full_name else "mot unique (OR)"
                        print(f"🔍 Recherche contacts ({mode}) dans {endpoint}")

                    response = requests.get(url, headers=self.storage._get_headers())

                    if response.status_code == 200:
                        contacts = response.json()
                        for contact in contacts:
                            contact['_source'] = 'contact'
                            contact['_endpoint'] = endpoint
                        results.extend(contacts)

                        if debug:
                            print(f"  ✅ Trouvé {len(contacts)} contacts dans {endpoint}")
                        break  # Premier endpoint qui fonctionne

                except Exception as e:
                    if debug:
                        print(f"  ⏭️  Endpoint {endpoint} non disponible: {e}")
                    continue

            # 2. Chercher dans CLIENTS (entreprises comme "École Vincent-d'Indy")
            for endpoint in client_endpoints:
                try:
                    url = f"{self.storage.api_url}/{endpoint}"
                    url += "?select=*"
                    # Chercher par company_name ou name
                    # SYNTAXE PostgREST: or=(column=ilike.pattern,...)
                    url += f"&or=(company_name=ilike.*{search_term}*,name=ilike.*{search_term}*)"
                    url += f"&limit={limit}"

                    if debug:
                        print(f"🔍 Recherche clients dans {endpoint}: {url[:150]}...")

                    response = requests.get(url, headers=self.storage._get_headers())

                    if response.status_code == 200:
                        companies = response.json()
                        for company in companies:
                            company['_source'] = 'client'
                            company['_endpoint'] = endpoint
                        results.extend(companies)

                        if debug:
                            print(f"  ✅ Trouvé {len(companies)} clients dans {endpoint}")
                        break  # Premier endpoint qui fonctionne

                except Exception as e:
                    if debug:
                        print(f"  ⏭️  Endpoint {endpoint} non disponible: {e}")
                    continue

            if debug:
                print(f"📊 Total résultats bruts: {len(results)}")

            return results[:limit]

        except Exception as e:
            print(f"⚠️ Erreur search_clients: {e}")
            import traceback
            traceback.print_exc()
            return []

    # =========================================================================
    # Exécution de requêtes
    # =========================================================================

    def execute_query(self, question: str, debug: bool = True) -> Dict[str, Any]:
        """
        Point d'entrée principal: parse la question et exécute la requête.

        Args:
            question: Question de l'utilisateur
            debug: Mode debug

        Returns:
            Dictionnaire de résultats
        """
        print(f"\n{'='*80}")
        print(f"📝 Question: {question}")
        print(f"{'='*80}")

        # Parser la question
        query_type, confidence = parse_query(question)
        entity_name = extract_entity_name(question, query_type)

        if debug:
            print(f"🎯 Type: {query_type.value} (confiance: {confidence:.0%})")
            print(f"👤 Entité: '{entity_name}'")

        # Router vers la bonne fonction
        if query_type == QueryType.TIMELINE:
            return self._execute_timeline_query(entity_name, debug=debug)

        elif query_type == QueryType.APPOINTMENTS:
            return self._execute_appointments_query(entity_name, debug=debug)

        elif query_type == QueryType.SEARCH_CLIENT:
            return self._execute_search_query(entity_name, debug=debug)

        elif query_type == QueryType.CLIENT_INFO:
            return self._execute_client_info_query(entity_name, debug=debug)

        elif query_type == QueryType.DEDUCTIONS:
            return {
                'type': 'deductions',
                'message': 'Fonctionnalité DEDUCTIONS en cours de développement'
            }

        else:
            return {
                'type': 'unknown',
                'message': f'Je n\'ai pas compris votre question. Type détecté: {query_type.value}',
                'confidence': confidence
            }

    def _execute_timeline_query(self, entity_name: str, debug: bool = False) -> Dict[str, Any]:
        """
        Exécute une requête TIMELINE (historique de service).

        Logique instrument-centric CORRIGÉE:
        1. Chercher contact/client par nom
        2. Si CONTACT → Récupérer le CLIENT parent via client_id
        3. Récupérer tous les PIANOS du client
        4. Requête timeline pour pianos (timeline liée aux pianos, pas aux clients!)

        Args:
            entity_name: Nom du contact ou client
            debug: Mode debug

        Returns:
            Résultats timeline
        """
        # 1. Chercher contact/client
        results = self.search_clients(entity_name, limit=1, debug=debug)

        if not results:
            return {
                'type': 'timeline',
                'error': f'Aucun client/contact trouvé pour: {entity_name}',
                'count': 0
            }

        result = results[0]
        source = result.get('_source', 'unknown')

        # 2. Déterminer le CLIENT_EXTERNAL_ID
        # CRITICAL: Les pianos appartiennent au CLIENT via external_id, pas au contact!
        if source == 'contact':
            # C'est un CONTACT (personne) → Remonter au client parent
            contact_name = result.get('full_name') or f"{result.get('first_name', '')} {result.get('last_name', '')}".strip()
            contact_id = result.get('id')

            # Récupérer le client parent
            client_data = result.get('client')  # Jointure faite dans search_clients
            if client_data:
                client_id = client_data.get('id')
                client_external_id = client_data.get('external_id')
                company_name = client_data.get('company_name') or client_data.get('name')
                print(f"\n👤 Contact trouvé: {contact_name} (ID: {contact_id})")
                print(f"🏢 Client parent: {company_name} (ID: {client_id}, external_id: {client_external_id})")
            else:
                # Fallback: essayer client_external_id dans le contact
                client_external_id = result.get('client_external_id')
                if not client_external_id:
                    return {
                        'type': 'timeline',
                        'error': f'Contact {contact_name} n\'est lié à aucun client',
                        'count': 0
                    }
                print(f"\n👤 Contact trouvé: {contact_name} (client_external_id: {client_external_id})")
                company_name = None
                client_id = None

            display_name = contact_name
            if company_name:
                display_name += f" ({company_name})"

        else:
            # C'est un CLIENT (entreprise)
            client_id = result.get('id')
            client_external_id = result.get('external_id')
            company_name = result.get('company_name') or result.get('name')
            print(f"\n🏢 Client trouvé: {company_name} (ID: {client_id}, external_id: {client_external_id})")
            display_name = company_name

        # 3. Récupérer les PIANOS du client
        # IMPORTANT: Les pianos sont liés au CLIENT via client_external_id (pas id numérique)
        piano_ids = self.get_client_pianos(client_external_id, debug=debug)

        if not piano_ids:
            print(f"⚠️  Aucun piano trouvé pour ce client")
            return {
                'type': 'timeline',
                'client_name': display_name,
                'client_id': client_id,
                'piano_count': 0,
                'piano_ids': [],
                'count': 0,
                'total': 0,
                'entries': [],
                'message': 'Aucun piano trouvé pour ce client'
            }

        print(f"🎹 {len(piano_ids)} piano{'s' if len(piano_ids) > 1 else ''} trouvé{'s' if len(piano_ids) > 1 else ''}")

        # 4. Requête timeline pour le CLIENT
        # IMPORTANT: Dans Gazelle, timeline entries sont liées au CLIENT via client_external_id,
        # pas aux pianos individuels! entity_type = 'CLIENT'
        entries, total = self.get_timeline_for_client(client_external_id, limit=100, debug=debug)

        # 5. Filtrer les entrées non pertinentes (bruit administratif)
        filtered_entries = self._filter_timeline_noise(entries)

        print(f"✅ Timeline: {len(filtered_entries)} entrées pertinentes (sur {total} total)")

        return {
            'type': 'timeline',
            'client_name': display_name,
            'client_id': client_id,
            'piano_count': len(piano_ids),
            'piano_ids': piano_ids,
            'count': len(filtered_entries),
            'total': total,
            'entries': filtered_entries[:20],  # Limiter à 20 pour l'affichage
        }

    def _execute_appointments_query(self, entity_name: str, debug: bool = False) -> Dict[str, Any]:
        """Exécute une requête APPOINTMENTS (rendez-vous futurs)"""
        return {
            'type': 'appointments',
            'message': 'Fonctionnalité APPOINTMENTS en cours de développement'
        }

    def _execute_search_query(self, entity_name: str, debug: bool = False) -> Dict[str, Any]:
        """Exécute une requête SEARCH_CLIENT"""
        clients = self.search_clients(entity_name, limit=10, debug=debug)

        return {
            'type': 'search_client',
            'count': len(clients),
            'clients': clients
        }

    def _execute_client_info_query(self, entity_name: str, debug: bool = False) -> Dict[str, Any]:
        """
        Exécute une requête CLIENT_INFO - Récupère détails complets d'un client
        incluant frais de déplacement.
        """
        try:
            # 1. Rechercher le client
            clients = self.search_clients(entity_name, limit=1, debug=debug)

            if not clients:
                return {
                    'type': 'client_info',
                    'error': f"Client '{entity_name}' non trouvé"
                }

            client = clients[0]
            is_contact = client.get('_source') == 'contact'

            # 2. Déterminer l'external_id
            if is_contact:
                client_external_id = client.get('client_external_id')
                contact_name = f"{client.get('first_name', '')} {client.get('last_name', '')}".strip()
                display_name = contact_name
            else:
                client_external_id = client.get('external_id')
                display_name = client.get('company_name') or client.get('name', 'N/A')

            # 3. Récupérer les détails complets du client
            details = {
                'display_name': display_name,
                'is_contact': is_contact,
                'external_id': client_external_id,
                'address': client.get('address', ''),
                'city': client.get('city', ''),
                'postal_code': client.get('postal_code', ''),
                'phone': client.get('phone', ''),
                'email': client.get('email', ''),
                'is_active': client.get('is_active', True)
            }

            # 4. Récupérer les pianos
            piano_ids = self.get_client_pianos(client_external_id, debug=debug)
            details['piano_count'] = len(piano_ids)

            # 5. Calculer les frais de déplacement
            try:
                # Import du module travel_fees depuis le projet parent
                sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
                from modules.travel_fees.calculator import TravelFeeCalculator

                # Construire adresse complète
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
                if debug:
                    print(f"⚠️ Erreur calcul frais déplacement: {e}")
                details['travel_fees'] = None

            return {
                'type': 'client_info',
                'client': details
            }

        except Exception as e:
            print(f"❌ Erreur _execute_client_info_query: {e}")
            import traceback
            traceback.print_exc()
            return {
                'type': 'client_info',
                'error': str(e)
            }

    def _filter_timeline_noise(self, entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Filtre les entrées timeline non pertinentes (bruit administratif).

        Args:
            entries: Liste d'entrées timeline

        Returns:
            Liste filtrée
        """
        # Patterns à exclure (copié de v5)
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
    print("Tests QueriesServiceV6")
    print("="*80)

    service = QueriesServiceV6()

    # Test 1: Timeline
    print("\n\n" + "="*80)
    print("Test 1: TIMELINE")
    print("="*80)
    result = service.execute_query(
        "montre-moi l'historique complet de Monique Hallé avec toutes les notes de service",
        debug=True
    )
    print(f"\n📊 Résultat:")
    print(f"   Type: {result.get('type')}")
    print(f"   Client: {result.get('client_name')}")
    print(f"   Pianos: {result.get('piano_count')}")
    print(f"   Entrées: {result.get('count')} / {result.get('total')}")

    # Test 2: Search
    print("\n\n" + "="*80)
    print("Test 2: SEARCH_CLIENT")
    print("="*80)
    result = service.execute_query("trouve Michelle Alie", debug=True)
    print(f"\n📊 Résultat:")
    print(f"   Type: {result.get('type')}")
    print(f"   Clients trouvés: {result.get('count')}")
