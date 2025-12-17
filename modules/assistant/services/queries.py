#!/usr/bin/env python3
"""
Service de requêtes pour l'assistant conversationnel.

Génère et exécute les requêtes vers Supabase selon le type de question parsée.
Utilise SupabaseStorage (REST API) au lieu de connexion PostgreSQL directe.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from urllib.parse import quote
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
        # Note: Les techniciens voient leurs propres RV par défaut avec ".mes rv"
        # Pour voir tous les RV, demander "tous les rv" ou "les rv de tous"
        # Louise (assistante) n'est pas technicienne → doit utiliser "tous les rv"
        # Source: docs/REFERENCE_COMPLETE.md et frontend/src/config/roles.js
        self.technicien_mapping = {
            # Emails officiels (référence Supabase et frontend)
            'nlessard@piano-tek.com': 'Nick',
            'jpreny@gmail.com': 'Jean-Philippe',
            'asutton@piano-tek.com': 'Allan',  # Admin est aussi technicien
            'info@piano-tek.com': None  # Louise n'est PAS technicienne
        }

        # Mapping ID utilisateur Supabase -> nom technicien
        # Source: docs/REFERENCE_COMPLETE.md
        self.technicien_id_mapping = {
            'usr_ofYggsCDt2JAVeNP': 'Allan',
            'usr_HcCiFk7o0vZ9xAI0': 'Nicolas',  # Nick
            'usr_ReUSmIJmBF86ilY1': 'Jean-Philippe',
            # Louise n'a pas encore d'ID Supabase assigné
        }

        # Mapping inverse: nom -> ID (pour les requêtes)
        self.technicien_name_to_id = {
            'Nick': 'usr_HcCiFk7o0vZ9xAI0',
            'Nicolas': 'usr_HcCiFk7o0vZ9xAI0',
            'Jean-Philippe': 'usr_ReUSmIJmBF86ilY1',
            'Allan': 'usr_ofYggsCDt2JAVeNP'
            # Louise n'est pas technicienne, pas dans ce mapping
        }

    def _get_technicien_from_email(self, email: str) -> Optional[str]:
        """
        Retourne le nom du technicien depuis son email.

        Args:
            email: Email de l'utilisateur

        Returns:
            Nom du technicien ou None (pour admin)
        """
        if not email:
            return None
        email_lower = email.lower()
        technicien = self.technicien_mapping.get(email_lower)
        # Log de débogage pour diagnostiquer les problèmes de mapping
        if technicien is None and email_lower != 'anonymous':
            print(f"⚠️ Email non mappé: '{email_lower}' (emails disponibles: {list(self.technicien_mapping.keys())})")
        return technicien

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
                # SIMPLE: Toutes les heures viennent de l'API Gazelle en UTC
                # Convertir UTC → heure de Toronto (America/Toronto)
                from zoneinfo import ZoneInfo
                from datetime import datetime as dt, timezone as tz
                
                toronto_tz = ZoneInfo('America/Toronto')
                utc_tz = tz.utc
                
                for appt in appointments:
                    # Convertir appointment_time si présent
                    if 'appointment_time' in appt and appt['appointment_time']:
                        time_str = str(appt['appointment_time'])
                        
                        # Si c'est un TIMESTAMPTZ (format ISO avec fuseau horaire), c'est en UTC
                        if 'T' in time_str or '+' in time_str or 'Z' in time_str:
                            try:
                                # Parser le timestamp UTC
                                if time_str.endswith('Z'):
                                    time_str = time_str.replace('Z', '+00:00')
                                dt_obj = dt.fromisoformat(time_str)
                                if dt_obj.tzinfo is None:
                                    dt_obj = dt_obj.replace(tzinfo=utc_tz)
                                else:
                                    dt_obj = dt_obj.astimezone(utc_tz)
                                
                                # Convertir en heure de Toronto
                                dt_toronto = dt_obj.astimezone(toronto_tz)
                                # Extraire seulement l'heure (HH:MM)
                                appt['appointment_time'] = dt_toronto.strftime('%H:%M')
                            except (ValueError, AttributeError) as e:
                                print(f"⚠️ Erreur conversion heure '{time_str}': {e}")
                        # Si c'est juste une heure (HH:MM:SS), créer un datetime UTC avec la date et convertir
                        elif ':' in time_str:
                            try:
                                parts = time_str.split(':')
                                if len(parts) >= 2:
                                    hour_utc = int(parts[0])
                                    minute_utc = int(parts[1][:2])
                                    
                                    # Utiliser la date du rendez-vous pour créer un datetime complet
                                    if 'appointment_date' in appt and appt['appointment_date']:
                                        date_parts = appt['appointment_date'].split('-')
                                        if len(date_parts) == 3:
                                            year, month, day = int(date_parts[0]), int(date_parts[1]), int(date_parts[2])
                                            
                                            # Créer datetime en UTC (les heures viennent de l'API Gazelle en UTC)
                                            dt_utc = dt(year, month, day, hour_utc, minute_utc, tzinfo=utc_tz)
                                            
                                            # Convertir en heure de Toronto
                                            dt_toronto = dt_utc.astimezone(toronto_tz)
                                            appt['appointment_time'] = dt_toronto.strftime('%H:%M')
                            except (ValueError, IndexError) as e:
                                print(f"⚠️ Erreur conversion heure '{time_str}': {e}")
                
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

        Note: Cherche dans gazelle_clients ET gazelle_contacts car dans Gazelle:
        - clients = entités qui paient (compagnies, particuliers)
        - contacts = personnes associées aux clients

        Args:
            search_terms: Termes de recherche
            limit: Nombre maximum de résultats

        Returns:
            Liste de clients correspondants (clients + contacts combinés)
        """
        if not search_terms:
            return []

        try:
            import requests
            # Joindre tous les termes pour chercher le nom complet
            search_query = " ".join(search_terms) if search_terms else ""
            results = []

            # 1. Chercher dans gazelle_clients
            base_url = f"{self.storage.api_url}/gazelle_clients"

            if search_query.startswith('cli_'):
                url_clients = f"{base_url}?select=*&external_id=eq.{search_query}&limit={limit}"
                response_clients = requests.get(url_clients, headers=self.storage._get_headers())
            else:
                # Syntaxe PostgREST: faire plusieurs requêtes séparées et combiner
                # Plus fiable que or=(...) qui peut causer des erreurs 400
                encoded_query = quote(search_query, safe='')

                # Faire plusieurs requêtes séparées et combiner les résultats
                # Colonnes réelles: company_name, city (pas name, first_name)
                all_clients = []
                seen_ids = set()
                for field in ['company_name', 'city']:
                    try:
                        # Syntaxe PostgREST: ilike.*pattern* (comme dans search_pianos)
                        field_url = f"{base_url}?select=*&{field}=ilike.*{encoded_query}*&limit={limit}"
                        field_response = requests.get(field_url, headers=self.storage._get_headers())
                        if field_response.status_code == 200:
                            field_clients = field_response.json()
                            # Éviter les doublons par external_id
                            for client in field_clients:
                                client_id = client.get('external_id')
                                if client_id and client_id not in seen_ids:
                                    seen_ids.add(client_id)
                                    all_clients.append(client)
                        elif field_response.status_code != 404:
                            print(f"⚠️ Erreur recherche {field} ({field_response.status_code}): {field_response.text[:200]}")
                    except Exception as e:
                        print(f"⚠️ Erreur recherche {field}: {e}")
                
                # Créer un objet Response mock
                class MockResponse:
                    def __init__(self, status_code, data):
                        self.status_code = status_code
                        self._data = data
                    def json(self):
                        return self._data
                
                response_clients = MockResponse(200 if all_clients else 404, all_clients)

            if response_clients.status_code == 200:
                clients = response_clients.json()
                for client in clients:
                    client['_source'] = 'client'  # Marquer la source
                results.extend(clients)
            else:
                print(f"⚠️ Erreur gazelle_clients: {response_clients.status_code}")

            # 2. Chercher dans gazelle_contacts
            base_url_contacts = f"{self.storage.api_url}/gazelle_contacts"

            if search_query.startswith('con_'):
                url_contacts = f"{base_url_contacts}?select=*&external_id=eq.{search_query}&limit={limit}"
                response_contacts = requests.get(url_contacts, headers=self.storage._get_headers())
            else:
                # Syntaxe PostgREST: faire plusieurs requêtes séparées et combiner
                encoded_query = quote(search_query, safe='')
                
                # Faire plusieurs requêtes séparées et combiner les résultats
                # Colonnes réelles dans gazelle_contacts: first_name, last_name, email (pas name)
                all_contacts = []
                seen_ids = set()
                for field in ['first_name', 'last_name', 'email']:
                    try:
                        # Syntaxe PostgREST: ilike.*pattern* (comme dans search_pianos)
                        field_url = f"{base_url_contacts}?select=*&{field}=ilike.*{encoded_query}*&limit={limit}"
                        field_response = requests.get(field_url, headers=self.storage._get_headers())
                        if field_response.status_code == 200:
                            field_contacts = field_response.json()
                            # Éviter les doublons par external_id
                            for contact in field_contacts:
                                contact_id = contact.get('external_id')
                                if contact_id and contact_id not in seen_ids:
                                    seen_ids.add(contact_id)
                                    all_contacts.append(contact)
                        elif field_response.status_code != 404:
                            print(f"⚠️ Erreur recherche {field} ({field_response.status_code}): {field_response.text[:200]}")
                    except Exception as e:
                        print(f"⚠️ Erreur recherche {field}: {e}")
                
                # Créer un objet Response mock
                class MockResponse:
                    def __init__(self, status_code, data):
                        self.status_code = status_code
                        self._data = data
                    def json(self):
                        return self._data
                
                response_contacts = MockResponse(200 if all_contacts else 404, all_contacts)

            if response_contacts.status_code == 200:
                contacts = response_contacts.json()
                for contact in contacts:
                    contact['_source'] = 'contact'  # Marquer la source
                results.extend(contacts)
            else:
                print(f"⚠️ Erreur gazelle_contacts: {response_contacts.status_code}")

            return results[:limit]  # Limiter le nombre total de résultats

        except Exception as e:
            print(f"❌ Erreur lors de la recherche clients/contacts: {e}")
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

            search_query = search_terms[0] if search_terms else ""

            # Si c'est un ID Gazelle (pia_xxx), chercher par external_id exact
            if search_query.startswith('pia_'):
                url += f"&external_id=eq.{search_query}"
            else:
                # Sinon, recherche textuelle dans marque, modèle, numéro de série, ville
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
            print(f"🔍 DEBUG get_timeline_entries: URL = {url}")
            response = requests.get(url, headers=self.storage._get_headers())
            print(f"🔍 DEBUG get_timeline_entries: Status = {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                print(f"🔍 DEBUG get_timeline_entries: {len(data)} entrées retournées")
                if data:
                    print(f"🔍 DEBUG get_timeline_entries: Première entrée clés = {list(data[0].keys()) if data else 'vide'}")
                return data
            else:
                print(f"❌ Erreur Supabase timeline: {response.status_code} - {response.text[:500]}")
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
            # Vérifier si l'utilisateur demande explicitement TOUS les RV
            show_all = params.get('show_all', False)

            # Mapper email -> nom technicien pour le filtre (sauf si show_all)
            if show_all:
                technicien = None  # Pas de filtre technicien
            else:
                technicien = self._get_technicien_from_email(user_id) if user_id else None

                # Si l'utilisateur n'est pas un technicien (technicien == None après mapping)
                # et qu'il demande "mes rv", retourner un message d'erreur explicatif
                # Note: Ne pas afficher l'erreur si user_id est 'anonymous' (utilisateur non connecté)
                if user_id and user_id.lower() != 'anonymous' and technicien is None:
                    return {
                        'type': 'appointments',
                        'date': datetime.now().strftime('%Y-%m-%d'),
                        'count': 0,
                        'data': [],
                        'message': "Vous n'êtes pas technicien et n'avez donc pas de rendez-vous assignés. Utilisez 'tous les rv' ou 'tous les rv demain' pour voir l'agenda complet."
                    }

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
