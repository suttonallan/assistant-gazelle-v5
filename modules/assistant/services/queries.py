#!/usr/bin/env python3
"""
Service de requêtes pour l'assistant conversationnel.

Génère et exécute les requêtes vers Supabase selon le type de question parsée.
Utilise SupabaseStorage (REST API) au lieu de connexion PostgreSQL directe.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from core.supabase_storage import SupabaseStorage
from modules.assistant.services.parser import QueryType


class GazelleQueries:
    """Gestionnaire de requêtes vers la base Gazelle dans Supabase."""

    def __init__(self, storage: Optional[SupabaseStorage] = None):
        """
        Initialise le service de requêtes.

        Args:
            storage: Instance de SupabaseStorage (crée si None)
        """
        self.storage = storage or SupabaseStorage()

        # Mapping email -> nom technicien dans Gazelle
        self.technicien_mapping = {
            'nicolas@pianotekinc.com': 'Nick',
            'jp@pianotekinc.com': 'Jean-Philippe',
            'asutton@piano-tek.com': 'Allan',  # Allan est admin ET technicien
            'allan@pianotekinc.com': 'Allan'
        }

    def _get_technicien_from_email(self, email: str) -> Optional[str]:
        """
        Retourne le nom du technicien depuis son email.

        Args:
            email: Email de l'utilisateur

        Returns:
            Nom du technicien ou None (pour admin)
        """
        return self.technicien_mapping.get(email.lower())

    def get_appointments(
        self,
        date: Optional[datetime] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        technicien: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Récupère les rendez-vous depuis Supabase.

        Args:
            date: Date exacte des RV (défaut: aujourd'hui si pas de plage)
            start_date: Date de début pour une plage (optionnel)
            end_date: Date de fin pour une plage (optionnel)
            technicien: Nom du technicien (None = tous)
            limit: Nombre maximum de résultats

        Returns:
            Liste de rendez-vous
        """
        try:
            # Requête via REST API Supabase (table gazelle_appointments)
            url = f"{self.storage.api_url}/gazelle_appointments"
            url += "?select=*"

            # Plage de dates ou date exacte
            if start_date and end_date:
                start_str = start_date.strftime('%Y-%m-%d')
                end_str = end_date.strftime('%Y-%m-%d')
                url += f"&appointment_date=gte.{start_str}"
                url += f"&appointment_date=lte.{end_str}"
            else:
                if date is None:
                    date = datetime.now()
                date_str = date.strftime('%Y-%m-%d')
                url += f"&appointment_date=eq.{date_str}"

            # Note: on ne filtre plus par technicien ici, pour éviter les 0 résultat
            # en cas de mismatch de mapping. Le frontend peut filtrer au besoin.

            url += f"&limit={limit}"
            url += "&order=appointment_date.asc,appointment_time.asc"

            import requests
            response = requests.get(url, headers=self.storage._get_headers())

            if response.status_code == 200:
                return response.json()
            else:
                print(f"❌ Erreur Supabase: {response.status_code} - {response.text}")
                return []

        except Exception as e:
            print(f"❌ Erreur lors de la récupération des RV: {e}")
            return []

    def search_clients(
        self,
        search_terms: List[str],
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Recherche des clients et contacts dans Supabase.

        Args:
            search_terms: Termes de recherche
            limit: Nombre maximum de résultats

        Returns:
            Liste de clients/contacts correspondants
        """
        if not search_terms:
            return []

        try:
            import requests
            from urllib.parse import quote
            
            search_query = search_terms[0] if search_terms else ""
            encoded_query = quote(search_query)
            
            all_results = []

            # Cas 1: recherche directe par ID externe (cli_..., con_...), avec fallback multi-endpoints
            if search_query.lower().startswith(("cli_", "con_")):
                import requests
                client_endpoints = ["gazelle_clients", "gazelle.clients", "clients"]
                contact_endpoints = ["gazelle_contacts", "gazelle.contacts", "contacts"]

                # Clients par external_id ou id
                for endpoint in client_endpoints:
                    try:
                        client_url = (
                            f"{self.storage.api_url}/{endpoint}"
                            f"?select=*"
                            f"&external_id=eq.{encoded_query}"
                            f"&or=(id.eq.{encoded_query},external_id.eq.{encoded_query})"
                            f"&limit={limit}"
                        )
                        resp = requests.get(client_url, headers=self.storage._get_headers())
                        if resp.status_code == 200:
                            for client in resp.json():
                                client["_source"] = "client"
                                all_results.append(client)
                        # Fallback ilike si rien trouvé sur eq
                        if resp.status_code == 200 and not resp.json():
                            ilike_url = (
                                f"{self.storage.api_url}/{endpoint}"
                                f"?select=*"
                                f"&or=(external_id.ilike.*{encoded_query}*,id.ilike.*{encoded_query}*)"
                                f"&limit={limit}"
                            )
                            ilike_resp = requests.get(ilike_url, headers=self.storage._get_headers())
                            if ilike_resp.status_code == 200:
                                for client in ilike_resp.json():
                                    client["_source"] = "client"
                                    all_results.append(client)
                    except Exception as e:
                        print(f"⚠️ Erreur recherche par ID client ({endpoint}): {e}")

                # Contacts par external_id ou id
                for endpoint in contact_endpoints:
                    try:
                        contact_url = (
                            f"{self.storage.api_url}/{endpoint}"
                            f"?select=*"
                            f"&external_id=eq.{encoded_query}"
                            f"&or=(id.eq.{encoded_query},external_id.eq.{encoded_query})"
                            f"&limit={limit}"
                        )
                        resp = requests.get(contact_url, headers=self.storage._get_headers())
                        if resp.status_code == 200:
                            for contact in resp.json():
                                contact["_source"] = "contact"
                                all_results.append(contact)
                        # Fallback ilike si rien trouvé sur eq
                        if resp.status_code == 200 and not resp.json():
                            ilike_url = (
                                f"{self.storage.api_url}/{endpoint}"
                                f"?select=*"
                                f"&or=(external_id.ilike.*{encoded_query}*,id.ilike.*{encoded_query}*)"
                                f"&limit={limit}"
                            )
                            ilike_resp = requests.get(ilike_url, headers=self.storage._get_headers())
                            if ilike_resp.status_code == 200:
                                for contact in ilike_resp.json():
                                    contact["_source"] = "contact"
                                    all_results.append(contact)
                    except Exception as e:
                        print(f"⚠️ Erreur recherche par ID contact ({endpoint}): {e}")

                # Retour anticipé si on a trouvé quelque chose
                if all_results:
                    return all_results[:limit]
            
            # Rechercher dans clients (plusieurs endpoints) sur company_name/city
            client_endpoints = ["gazelle_clients", "gazelle.clients", "clients"]
            for endpoint in client_endpoints:
                try:
                    for field in ['company_name', 'city', 'name']:
                        try:
                            field_url = f"{self.storage.api_url}/{endpoint}?select=*&{field}=ilike.*{encoded_query}*&limit={limit}"
                            field_response = requests.get(field_url, headers=self.storage._get_headers())
                            if field_response.status_code == 200:
                                clients = field_response.json()
                                for client in clients:
                                    client['_source'] = 'client'
                                    if not any(
                                        c.get('external_id') == client.get('external_id')
                                        or c.get('id') == client.get('id')
                                        for c in all_results
                                    ):
                                        all_results.append(client)
                        except Exception as e:
                            print(f"⚠️ Erreur recherche {field} dans clients ({endpoint}): {e}")
                except Exception as e:
                    print(f"⚠️ Erreur recherche clients ({endpoint}): {e}")
            
            # Rechercher dans contacts (plusieurs endpoints) sur first_name/last_name/email/city
            contact_endpoints = ["gazelle_contacts", "gazelle.contacts", "contacts"]
            for endpoint in contact_endpoints:
                try:
                    for field in ['first_name', 'last_name', 'email', 'city']:
                        try:
                            field_url = f"{self.storage.api_url}/{endpoint}?select=*&{field}=ilike.*{encoded_query}*&limit={limit}"
                            field_response = requests.get(field_url, headers=self.storage._get_headers())
                            if field_response.status_code == 200:
                                contacts = field_response.json()
                                for contact in contacts:
                                    contact['_source'] = 'contact'
                                    if not any(
                                        c.get('external_id') == contact.get('external_id')
                                        or c.get('id') == contact.get('id')
                                        for c in all_results
                                    ):
                                        all_results.append(contact)
                        except Exception as e:
                            print(f"⚠️ Erreur recherche {field} dans contacts ({endpoint}): {e}")
                except Exception as e:
                    print(f"⚠️ Erreur recherche contacts ({endpoint}): {e}")
            
            # Limiter les résultats
            return all_results[:limit]
            
        except Exception as e:
            print(f"❌ Erreur lors de la recherche clients: {e}")
            import traceback
            traceback.print_exc()
            return []

    def search_pianos(
        self,
        search_terms: List[str],
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Recherche des pianos dans Supabase.

        Args:
            search_terms: Termes de recherche
            limit: Nombre maximum de résultats

        Returns:
            Liste de pianos correspondants
        """
        if not search_terms:
            return []

        try:
            url = f"{self.storage.api_url}/gazelle.pianos"
            url += "?select=*"

            # Rechercher dans marque, modèle, numéro de série, ville
            search_query = search_terms[0] if search_terms else ""
            url += f"&or=(brand.ilike.*{search_query}*,model.ilike.*{search_query}*,serial_number.ilike.*{search_query}*,city.ilike.*{search_query}*)"

            url += f"&limit={limit}"

            import requests
            response = requests.get(url, headers=self.storage._get_headers())

            if response.status_code == 200:
                return response.json()
            else:
                print(f"❌ Erreur Supabase: {response.status_code} - {response.text}")
                return []

        except Exception as e:
            print(f"❌ Erreur lors de la recherche pianos: {e}")
            return []

    def get_timeline_entries(
        self,
        entity_id: str,
        entity_type: str = "piano",
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Récupère l'historique d'un piano ou client.

        Args:
            entity_id: ID de l'entité
            entity_type: Type (piano, client, contact)
            limit: Nombre maximum d'entrées

        Returns:
            Liste d'événements timeline
        """
        try:
            url = f"{self.storage.api_url}/gazelle.timeline_entries"
            url += "?select=*"
            url += f"&entity_id=eq.{entity_id}"
            url += f"&entity_type=eq.{entity_type}"
            url += f"&limit={limit}"
            url += "&order=created_at.desc"

            import requests
            response = requests.get(url, headers=self.storage._get_headers())

            if response.status_code == 200:
                return response.json()
            else:
                print(f"❌ Erreur Supabase: {response.status_code} - {response.text}")
                return []

        except Exception as e:
            print(f"❌ Erreur lors de la récupération timeline: {e}")
            return []

    def get_summary(
        self,
        start_date: datetime,
        end_date: datetime,
        technicien: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Génère un résumé d'activité pour une période.

        Args:
            start_date: Date de début
            end_date: Date de fin
            technicien: Nom du technicien (None = tous)

        Returns:
            Dictionnaire de statistiques
        """
        start_str = start_date.strftime('%Y-%m-%d')
        end_str = end_date.strftime('%Y-%m-%d')

        summary = {
            'period': {
                'start': start_str,
                'end': end_str
            },
            'appointments_count': 0,
            'timeline_entries_count': 0
        }

        try:
            # Compter les RV dans la période
            url = f"{self.storage.api_url}/gazelle.appointments"
            url += "?select=id"
            url += f"&date=gte.{start_str}"
            url += f"&date=lte.{end_str}"

            if technicien:
                url += f"&technicien=eq.{technicien}"

            import requests
            response = requests.get(url, headers=self.storage._get_headers())

            if response.status_code == 200:
                summary['appointments_count'] = len(response.json())

            # Compter les entrées timeline
            url = f"{self.storage.api_url}/gazelle.timeline_entries"
            url += "?select=id"
            url += f"&created_at=gte.{start_date.isoformat()}"
            url += f"&created_at=lte.{end_date.isoformat()}"

            response = requests.get(url, headers=self.storage._get_headers())

            if response.status_code == 200:
                summary['timeline_entries_count'] = len(response.json())

        except Exception as e:
            print(f"❌ Erreur lors de la génération du résumé: {e}")

        return summary

    def execute_query(
        self,
        query_type: QueryType,
        params: Dict[str, Any],
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute une requête selon le type et les paramètres.

        Args:
            query_type: Type de requête (QueryType)
            params: Paramètres extraits par le parser
            user_id: Email de l'utilisateur (pour filtrer ses RV)

        Returns:
            Résultats de la requête
        """
        if query_type == QueryType.APPOINTMENTS:
            # Mapper email -> nom technicien pour le filtre
            technicien = self._get_technicien_from_email(user_id) if user_id else None

            # Vérifier s'il y a une période (ex: "cette semaine")
            period = params.get('period')

            if period:
                # Plage de dates
                start_date = period['start_date']
                end_date = period['end_date']
                appointments = self.get_appointments(
                    start_date=start_date,
                    end_date=end_date,
                    technicien=technicien
                )

                return {
                    'type': 'appointments',
                    'date_range': {
                        'start': start_date.strftime('%Y-%m-%d'),
                        'end': end_date.strftime('%Y-%m-%d')
                    },
                    'count': len(appointments),
                    'data': appointments
                }
            else:
                # Date unique
                dates = params.get('dates', [])
                date = dates[0] if dates else datetime.now()
                appointments = self.get_appointments(date=date, technicien=technicien)

                return {
                    'type': 'appointments',
                    'date': date.strftime('%Y-%m-%d'),
                    'count': len(appointments),
                    'data': appointments
                }

        elif query_type == QueryType.SEARCH_CLIENT:
            search_terms = params.get('search_terms', [])
            clients = self.search_clients(search_terms)

            return {
                'type': 'search_client',
                'search_terms': search_terms,
                'count': len(clients),
                'data': clients
            }

        elif query_type == QueryType.SEARCH_PIANO:
            search_terms = params.get('search_terms', [])
            pianos = self.search_pianos(search_terms)

            return {
                'type': 'search_piano',
                'search_terms': search_terms,
                'count': len(pianos),
                'data': pianos
            }

        elif query_type == QueryType.SUMMARY:
            period = params.get('period')

            if period:
                start_date = period['start_date']
                end_date = period['end_date']
            else:
                # Par défaut: 7 derniers jours
                end_date = datetime.now()
                start_date = end_date - timedelta(days=7)

            summary = self.get_summary(start_date, end_date)

            return {
                'type': 'summary',
                'data': summary
            }

        elif query_type == QueryType.TIMELINE:
            # Nécessite un ID d'entité (extraire depuis search_terms)
            search_terms = params.get('search_terms', [])

            if not search_terms:
                return {
                    'type': 'timeline',
                    'error': 'ID d\'entité requis pour l\'historique'
                }

            entity_id = search_terms[0]
            timeline = self.get_timeline_entries(entity_id)

            return {
                'type': 'timeline',
                'entity_id': entity_id,
                'count': len(timeline),
                'data': timeline
            }

        elif query_type == QueryType.STATS:
            # Similar to SUMMARY
            period = params.get('period')

            if period:
                start_date = period['start_date']
                end_date = period['end_date']
            else:
                end_date = datetime.now()
                start_date = end_date - timedelta(days=30)

            stats = self.get_summary(start_date, end_date)

            return {
                'type': 'stats',
                'data': stats
            }

        else:
            return {
                'type': 'unknown',
                'error': 'Type de requête non supporté'
            }


# Instance singleton
_queries_instance: Optional[GazelleQueries] = None


def get_queries(storage: Optional[SupabaseStorage] = None) -> GazelleQueries:
    """
    Retourne l'instance singleton de GazelleQueries.

    Args:
        storage: Instance de SupabaseStorage (optionnel)

    Returns:
        Instance de GazelleQueries
    """
    global _queries_instance

    if _queries_instance is None:
        _queries_instance = GazelleQueries(storage=storage)

    return _queries_instance
