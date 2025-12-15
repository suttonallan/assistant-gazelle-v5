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
            'nlessard@piano-tek.com': 'Nick',
            'jpreny@gmail.com': 'Jean-Philippe',
            'asutton@piano-tek.com': None,  # Admin voit tous les RV
            'info@piano-tek.com': None  # Louise (assistante) voit tous les RV
        }
        
        # Mapping ID utilisateur Supabase -> nom technicien
        # Source: docs/REFERENCE_COMPLETE.md
        self.technicien_id_mapping = {
            'usr_ofYggsCDt2JAVeNP': 'Allan',
            'usr_HcCiFk7o0vZ9xAI0': 'Nicolas',  # Nick
            'usr_ReUSmIJmBF86ilY1': 'Jean-Philippe'
        }
        
        # Mapping inverse: nom -> ID (pour les requêtes)
        self.technicien_name_to_id = {
            'Nick': 'usr_HcCiFk7o0vZ9xAI0',
            'Nicolas': 'usr_HcCiFk7o0vZ9xAI0',
            'Jean-Philippe': 'usr_ReUSmIJmBF86ilY1',
            'Allan': 'usr_ofYggsCDt2JAVeNP'
        }
        
        # Mapping ID utilisateur Supabase -> nom technicien
        # Source: docs/REFERENCE_COMPLETE.md
        self.technicien_id_mapping = {
            'usr_ofYggsCDt2JAVeNP': 'Allan',
            'usr_HcCiFk7o0vZ9xAI0': 'Nicolas',  # Nick
            'usr_ReUSmIJmBF86ilY1': 'Jean-Philippe'
        }
        
        # Mapping inverse: nom -> ID (pour les requêtes)
        self.technicien_name_to_id = {
            'Nick': 'usr_HcCiFk7o0vZ9xAI0',
            'Nicolas': 'usr_HcCiFk7o0vZ9xAI0',
            'Jean-Philippe': 'usr_ReUSmIJmBF86ilY1',
            'Allan': 'usr_ofYggsCDt2JAVeNP'
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
            # Requête via REST API Supabase
            # Note: Table dans schéma public avec préfixe gazelle_ (pas gazelle.appointments)
            # Pour les clients, on utilisera title si client_external_id est None
            url = f"{self.storage.api_url}/gazelle_appointments"
            url += f"?select=*"

            # Plage de dates ou date exacte
            # Note: La colonne s'appelle appointment_date (pas date)
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

            # Filtrer par technicien si spécifié
            # Note: technicien peut être un nom (Nick) ou un ID (usr_xxx)
            if technicien:
                # Mapper le nom vers l'ID si nécessaire
                technicien_filter = self.technicien_name_to_id.get(technicien, technicien)
                url += f"&technicien=eq.{technicien_filter}"

            url += f"&limit={limit}"
            url += "&order=appointment_date.asc,appointment_time.asc"

            import requests
            response = requests.get(url, headers=self.storage._get_headers())

            if response.status_code == 200:
                appointments = response.json()
                # Enrichir avec les noms de clients si client_external_id est présent
                # Note: Pour l'instant, on utilise title comme nom de client
                return appointments
            elif response.status_code == 404:
                # Table n'existe pas encore - c'est normal, les RV ne sont pas encore synchronisés
                print(f"⚠️ Table gazelle_appointments n'existe pas encore (404). Les rendez-vous ne sont pas encore synchronisés.")
                return []
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
        Recherche des clients dans Supabase.

        Args:
            search_terms: Termes de recherche
            limit: Nombre maximum de résultats

        Returns:
            Liste de clients correspondants
        """
        if not search_terms:
            return []

        try:
            # Construire la requête de recherche
            # Supabase REST API supporte ilike pour recherche insensible à la casse
            # Note: Table dans schéma public avec préfixe gazelle_ (pas gazelle.clients)
            url = f"{self.storage.api_url}/gazelle_clients"
            url += "?select=*"

            # Rechercher dans nom, prénom, ville
            search_query = search_terms[0] if search_terms else ""
            url += f"&or=(name.ilike.*{search_query}*,first_name.ilike.*{search_query}*,city.ilike.*{search_query}*)"

            url += f"&limit={limit}"

            import requests
            response = requests.get(url, headers=self.storage._get_headers())

            if response.status_code == 200:
                return response.json()
            else:
                print(f"❌ Erreur Supabase: {response.status_code} - {response.text}")
                return []

        except Exception as e:
            print(f"❌ Erreur lors de la recherche clients: {e}")
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
            # Note: Table dans schéma public avec préfixe gazelle_ (pas gazelle.pianos)
            url = f"{self.storage.api_url}/gazelle_pianos"
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
            # Note: Table dans schéma public avec préfixe gazelle_ (pas gazelle.timeline_entries)
            url = f"{self.storage.api_url}/gazelle_timeline_entries"
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
            # Note: Table dans schéma public avec préfixe gazelle_ (pas gazelle.appointments)
            # Note: La colonne s'appelle appointment_date (pas date)
            url = f"{self.storage.api_url}/gazelle_appointments"
            url += "?select=id"
            url += f"&appointment_date=gte.{start_str}"
            url += f"&appointment_date=lte.{end_str}"

            # Filtrer par technicien si spécifié
            # Note: technicien peut être un nom (Nick) ou un ID (usr_xxx)
            if technicien:
                # Mapper le nom vers l'ID si nécessaire
                technicien_filter = self.technicien_name_to_id.get(technicien, technicien)
                url += f"&technicien=eq.{technicien_filter}"

            import requests
            response = requests.get(url, headers=self.storage._get_headers())

            if response.status_code == 200:
                summary['appointments_count'] = len(response.json())
            elif response.status_code == 404:
                # Table n'existe pas encore - c'est normal
                summary['appointments_count'] = 0

            # Compter les entrées timeline
            # Note: Table dans schéma public avec préfixe gazelle_ (pas gazelle.timeline_entries)
            url = f"{self.storage.api_url}/gazelle_timeline_entries"
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
