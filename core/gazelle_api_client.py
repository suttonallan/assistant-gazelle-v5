#!/usr/bin/env python3
"""
Client API pour Gazelle - Communication avec l'API GraphQL privée.

Gère l'authentification OAuth2, le refresh des tokens, et les requêtes GraphQL.
"""

import json
import os
import time
import requests
from dotenv import load_dotenv
from typing import Dict, List, Optional, Any

# Chemin vers le dossier racine du projet
PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))

# Chemin vers le dossier de configuration (pour token.json)
CONFIG_DIR = os.path.join(PROJECT_ROOT, 'config')

# Charger les variables d'environnement depuis .env à la racine
env_path = os.path.join(PROJECT_ROOT, '.env')
load_dotenv(env_path)

API_URL = "https://gazelleapp.io/graphql/private/"
OAUTH_TOKEN_URL = "https://gazelleapp.io/developer/oauth/token"


class GazelleAPIClient:
    """Client pour l'API GraphQL de Gazelle."""
    
    def __init__(self, token_path: Optional[str] = None):
        """
        Initialise le client API.
        
        Args:
            token_path: Chemin vers le fichier token.json (défaut: config/token.json)
        """
        if token_path is None:
            token_path = os.path.join(CONFIG_DIR, 'token.json')
        self.token_path = token_path

        # Force credentials from DEPLOY_NOW.md
        self.client_id = os.getenv('GAZELLE_CLIENT_ID') or 'yCLgIwBusPMX9bZHtbzePvcNUisBQ9PeA4R93OwKwNE'
        self.client_secret = os.getenv('GAZELLE_CLIENT_SECRET') or 'CHiMzcYZ2cVgBCjQ7vDCxr3jIE5xkLZ_9v4VkU-O9Qc'

        # Try to load token, if fails create a new one
        try:
            self.token_data = self._load_token()
        except:
            print("⚠️ Pas de token valide, génération d'un nouveau...")
            self._generate_new_token()
            self.token_data = self._load_token()
    
    def _load_token(self) -> Dict[str, Any]:
        """
        Charge le token depuis Supabase system_settings (prioritaire) ou token.json (fallback).

        Returns:
            Dict contenant access_token, refresh_token, expires_in, created_at
        """
        # Priorité 1: Charger depuis Supabase system_settings
        try:
            from core.supabase_storage import SupabaseStorage
            storage = SupabaseStorage()
            token_data = storage.get_system_setting("gazelle_oauth_token")
            if token_data:
                print("✅ Token chargé depuis Supabase system_settings")
                return token_data
        except Exception as e:
            print(f"⚠️ Impossible de charger token depuis Supabase: {e}")

        # Priorité 2: Fallback sur fichier local token.json
        if not os.path.exists(self.token_path):
            raise FileNotFoundError(
                f"Token OAuth non trouvé.\n"
                f"Fichier local: {self.token_path}\n"
                f"Supabase: gazelle_oauth_token non trouvé\n"
                f"Veuillez suivre le guide: docs/OAUTH_SETUP_GUIDE.md"
            )

        try:
            with open(self.token_path, 'r', encoding='utf-8') as f:
                token_data = json.load(f)

            print(f"✅ Token chargé depuis fichier local: {self.token_path}")
            # Skip expiration check - use token as-is
            return token_data
        except json.JSONDecodeError as e:
            raise ValueError(f"Erreur de format JSON dans {self.token_path}: {e}")
    
    def _is_token_expired(self, token_data: Dict[str, Any]) -> bool:
        """
        Vérifie si le token est expiré.
        
        Args:
            token_data: Données du token
            
        Returns:
            True si le token est expiré
        """
        if 'created_at' not in token_data or 'expires_in' not in token_data:
            return True
        
        expires_at = token_data['created_at'] + token_data['expires_in']
        return time.time() >= expires_at
    
    def _save_token(self, token_data: Dict[str, Any]) -> None:
        """
        Sauvegarde le token dans token.json.
        
        Args:
            token_data: Données du token à sauvegarder
        """
        # Ajouter timestamp si absent
        if 'created_at' not in token_data:
            token_data['created_at'] = int(time.time())
        
        with open(self.token_path, 'w', encoding='utf-8') as f:
            json.dump(token_data, f, indent=2)
        
        self.token_data = token_data
    
    def _refresh_token(self) -> None:
        """
        Rafraîchit le token OAuth2 en utilisant le refresh_token.
        
        Sauvegarde automatiquement le nouveau token.
        """
        if 'refresh_token' not in self.token_data:
            raise ValueError("refresh_token manquant dans token.json")
        
        print("🔄 Rafraîchissement du token OAuth2...")
        
        payload = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'refresh_token': self.token_data['refresh_token'],
            'grant_type': 'refresh_token'
        }
        
        try:
            response = requests.post(OAUTH_TOKEN_URL, data=payload)
            response.raise_for_status()
            
            new_token_data = response.json()

            # Préserver le refresh_token s'il n'est pas dans la réponse
            if 'refresh_token' not in new_token_data:
                new_token_data['refresh_token'] = self.token_data.get('refresh_token')

            # Ajouter created_at pour tracking
            new_token_data['created_at'] = int(time.time())

            self._save_token(new_token_data)
            print("✅ Token rafraîchi avec succès")
            
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"Erreur lors du rafraîchissement du token: {e}")
    
    def _execute_query(self, query: str, variables: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Exécute une requête GraphQL.

        Args:
            query: Requête GraphQL (string)
            variables: Variables pour la requête (dict optionnel)

        Returns:
            Réponse JSON de l'API

        Raises:
            ConnectionError: Si l'API retourne une erreur
        """
        # Skip expiration check - token is valid
        # if self._is_token_expired(self.token_data):
        #     self._refresh_token()

        access_token = self.token_data['access_token']
        
        # Si le token est court (< 50 chars), c'est probablement une API Key
        # Le navigateur l'envoie UNIQUEMENT via x-gazelle-api-key (pas de Bearer)
        if len(access_token) < 50:
            headers = {
                'x-gazelle-api-key': access_token,
                'Content-Type': 'application/json'
            }
            print(f"🔑 Utilisation de x-gazelle-api-key (API Key: {len(access_token)} chars)")
        else:
            # Token JWT standard (Bearer)
            headers = {
                'Authorization': f"Bearer {access_token}",
                'Content-Type': 'application/json'
            }

        payload = {
            'query': query,
            'variables': variables or {}
        }

        try:
            response = requests.post(API_URL, json=payload, headers=headers)

            # AUTO-REFRESH: Si 401, tenter de rafraîchir automatiquement
            if response.status_code == 401:
                print("⚠️  Token invalide (401), tentative de rafraîchissement automatique...")

                # Essayer de rafraîchir avec refresh_token
                try:
                    self._refresh_token()
                    print("✅ Token rafraîchi, nouvel essai...")

                    # Recharger le token depuis Supabase
                    self.token_data = self._load_token()
                    new_access_token = self.token_data['access_token']
                    
                    # Reconstruire les headers selon le type de token
                    if len(new_access_token) < 50:
                        headers = {
                            'x-gazelle-api-key': new_access_token,
                            'Content-Type': 'application/json'
                        }
                    else:
                        headers['Authorization'] = f"Bearer {new_access_token}"

                    # Retry la requête
                    response = requests.post(API_URL, json=payload, headers=headers)

                except Exception as refresh_error:
                    print(f"❌ Échec du refresh automatique: {refresh_error}")
                    print("💡 Essayez: python3 scripts/auto_refresh_token.py --force")

            # DETAILED ERROR LOGGING: Log response status and body for debugging
            if response.status_code != 200:
                print(f"❌ Gazelle API Error - Status {response.status_code}")
                print(f"   URL: {API_URL}")
                print(f"   Response Headers: {dict(response.headers)}")
                print(f"   Response Body: {response.text[:1000]}")  # First 1000 chars

            response.raise_for_status()

            result = response.json()

            # Vérifier les erreurs GraphQL
            if 'errors' in result:
                print(f"❌ GraphQL Errors detected:")
                for idx, err in enumerate(result['errors'], 1):
                    print(f"   Error {idx}: {err.get('message', 'Unknown error')}")
                    if 'locations' in err:
                        print(f"      Locations: {err['locations']}")
                    if 'path' in err:
                        print(f"      Path: {err['path']}")
                    if 'extensions' in err:
                        print(f"      Extensions: {err['extensions']}")

                error_messages = [err.get('message', 'Unknown error') for err in result['errors']]
                raise ValueError(f"Erreurs GraphQL: {', '.join(error_messages)}")

            return result

        except requests.exceptions.RequestException as e:
            print(f"❌ Request Exception during Gazelle API call:")
            print(f"   Exception type: {type(e).__name__}")
            print(f"   Exception message: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"   Response status: {e.response.status_code}")
                print(f"   Response body: {e.response.text[:1000]}")
            import traceback
            print(f"   Traceback: {traceback.format_exc()}")
            raise ConnectionError(f"Erreur lors de l'appel API: {e}")
    
    def get_clients(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Récupère tous les clients depuis l'API.
        
        Args:
            limit: Nombre maximum de clients par page (défaut: 100)
            
        Returns:
            Liste de dictionnaires contenant les données des clients
        """
        query = """
        query GetClients {
            allClients {
                nodes {
                    id
                    companyName
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
        }
        """
        
        result = self._execute_query(query)
        connection = result.get('data', {}).get('allClients', {})
        all_clients = connection.get('nodes', [])
        
        # Limiter le nombre de résultats si nécessaire
        if limit and len(all_clients) > limit:
            all_clients = all_clients[:limit]
        
        print(f"✅ {len(all_clients)} clients récupérés depuis l'API")
        return all_clients

    def get_contacts(self, limit: int = 1000) -> List[Dict[str, Any]]:
        """
        Récupère tous les contacts depuis l'API.

        Note: Dans Gazelle GraphQL API, les contacts sont accessibles via
        les clients (defaultContact). Chaque client a un contact principal.

        Args:
            limit: Nombre maximum de contacts (défaut: 1000)

        Returns:
            Liste de dictionnaires contenant les données des contacts
        """
        # Récupérer les clients avec leurs contacts par défaut
        clients = self.get_clients(limit=limit)

        # Extraire les defaultContact de chaque client
        all_contacts = []
        for client in clients:
            default_contact = client.get('defaultContact')
            if default_contact and default_contact.get('id'):
                # Ajouter les infos du client parent au contact
                default_contact['client'] = {
                    'id': client.get('id'),
                    'companyName': client.get('companyName')
                }
                # Utiliser les dates du client si le contact n'en a pas
                if not default_contact.get('createdAt'):
                    default_contact['createdAt'] = client.get('createdAt')
                if not default_contact.get('updatedAt'):
                    default_contact['updatedAt'] = client.get('updatedAt')

                all_contacts.append(default_contact)

        print(f"✅ {len(all_contacts)} contacts récupérés depuis l'API (defaultContact des clients)")
        return all_contacts

    def get_maintenance_alerts(self, limit: int = 100, is_resolved: Optional[bool] = None) -> List[Dict[str, Any]]:
        """
        Récupère les alertes de maintenance depuis l'API.
        
        Args:
            limit: Nombre maximum d'alertes par page (défaut: 100)
            is_resolved: Filtrer par statut de résolution (None = tous)
            
        Returns:
            Liste de dictionnaires contenant les données des alertes
        """
        query = """
        query GetMaintenanceAlerts {
            allMaintenanceAlerts {
                nodes {
                    id
                    clientId
                    pianoId
                    dateObservation
                    location
                    alertType
                    description
                    isResolved
                    resolvedDate
                    archived
                    notes
                    recipientEmail
                    createdBy
                    createdAt
                    updatedAt
                }
            }
        }
        """
        
        result = self._execute_query(query)
        connection = result.get('data', {}).get('allMaintenanceAlerts', {})
        all_alerts = connection.get('nodes', [])
        
        # Filtrer par isResolved si spécifié
        if is_resolved is not None:
            all_alerts = [alert for alert in all_alerts if alert.get('isResolved') == is_resolved]
        
        # Limiter le nombre de résultats si nécessaire
        if limit and len(all_alerts) > limit:
            all_alerts = all_alerts[:limit]
        
        print(f"✅ {len(all_alerts)} alertes récupérées depuis l'API")
        return all_alerts
    
    def get_pianos(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Récupère tous les pianos depuis l'API.
        
        Args:
            limit: Nombre maximum de pianos par page (défaut: 100)
            
        Returns:
            Liste de dictionnaires contenant les données des pianos
        """
        query = """
        query GetPianos {
            allPianos {
                nodes {
                    id
                    client {
                        id
                    }
                    make
                    model
                    serialNumber
                    type
                    year
                    location
                    notes
                    damppChaserInstalled
                    damppChaserHumidistatModel
                    damppChaserMfgDate
                }
            }
        }
        """
        
        result = self._execute_query(query)
        connection = result.get('data', {}).get('allPianos', {})
        all_pianos = connection.get('nodes', [])
        
        # Limiter le nombre de résultats si nécessaire
        if limit and len(all_pianos) > limit:
            all_pianos = all_pianos[:limit]
        
        print(f"✅ {len(all_pianos)} pianos récupérés depuis l'API")
        return all_pianos

    def get_appointments(self, limit: Optional[int] = None, start_date_override: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Récupère tous les rendez-vous depuis l'API Gazelle (allEventsBatched).

        Utilise la pagination automatique pour récupérer tous les événements.
        Pattern copié depuis V4 (Import_daily_update.py lignes 257-268).

        Args:
            limit: Nombre maximum d'appointments à retourner (None = tous)
            start_date_override: Date de début explicite (format YYYY-MM-DD). Si fourni, override le calcul automatique.

        Returns:
            Liste de dictionnaires contenant les données des rendez-vous
        """
        from datetime import datetime, timedelta
        import time

        # FIXED: Permettre override de la date de début pour récupérer historique
        if start_date_override:
            start_date = start_date_override
        else:
            # Période : 60 jours dans le passé → 90 jours dans le futur (config V4)
            start_date = (datetime.now() - timedelta(days=60)).strftime('%Y-%m-%d')

        end_date = (datetime.now() + timedelta(days=90)).strftime('%Y-%m-%d')

        # Requête GraphQL (copié de V4 - ligne 258)
        query = """
        query($first: Int, $after: String, $filters: PrivateAllEventsFilter) {
          allEventsBatched(first: $first, after: $after, filters: $filters) {
            nodes {
              id
              title
              start
              duration
              isAllDay
              notes
              client { id }
              type
              status
              user { id }
              createdBy { id }
              confirmedByClient
              source
              travelMode
              allEventPianos(first: 10) {
                nodes {
                  piano { id }
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

        # Filtres (copié de V4 - ligne 259)
        # FIXED: Inclure tous les statuts (ACTIVE, COMPLETED, etc.) pour récupérer l'historique complet
        filters = {
            "startOn": start_date,
            "endOn": end_date,
            "type": ["APPOINTMENT", "PERSONAL", "MEMO", "SYNCED"]
            # Note: Pas de filtre "status" → récupère TOUS les statuts (ACTIVE, COMPLETED, CANCELLED, etc.)
        }

        # Pagination automatique (pattern V4 - lignes 136-189)
        all_events = []
        cursor = None
        page_size = 100
        page_count = 0

        print(f"📅 Récupération appointments ({start_date} → {end_date})...")

        while True:
            page_count += 1
            time.sleep(0.2)  # Délai entre requêtes (V4)

            variables = {
                "first": page_size,
                "after": cursor,
                "filters": filters
            }

            result = self._execute_query(query, variables)

            if not result:
                break

            data_connection = result.get('data', {}).get('allEventsBatched', {})
            if not data_connection:
                break

            nodes = data_connection.get('nodes', [])
            all_events.extend(nodes)

            print(f"   Page {page_count}: {len(nodes)} appointments récupérés (total: {len(all_events)})")

            # Vérifier si page suivante
            page_info = data_connection.get('pageInfo', {})
            if not page_info.get('hasNextPage'):
                break

            cursor = page_info.get('endCursor')

        # Limiter si nécessaire
        if limit and len(all_events) > limit:
            all_events = all_events[:limit]

        print(f"✅ {len(all_events)} appointments récupérés depuis l'API")
        return all_events

    def get_invoices(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Récupère toutes les factures depuis l'API.

        Args:
            limit: Nombre maximum de factures par page (défaut: 100)

        Returns:
            Liste de dictionnaires contenant les données des factures
        """
        query = """
        query GetInvoices {
            allInvoices {
                nodes {
                    id
                    clientId
                    number
                    invoiceDate
                    status
                    subTotal
                    total
                    notes
                    createdAt
                    dueOn
                    allInvoiceItems {
                        nodes {
                            id
                            description
                            type
                            quantity
                            amount
                            subTotal
                            taxTotal
                            total
                            billable
                            taxable
                            sequenceNumber
                        }
                    }
                }
            }
        }
        """

        result = self._execute_query(query)
        connection = result.get('data', {}).get('allInvoices', {})
        all_invoices = connection.get('nodes', [])

        # Limiter le nombre de résultats si nécessaire
        if limit and len(all_invoices) > limit:
            all_invoices = all_invoices[:limit]

        print(f"✅ {len(all_invoices)} factures récupérées depuis l'API")
        return all_invoices

    def get_products(self, limit: int = 500) -> List[Dict[str, Any]]:
        """
        Récupère tous les produits depuis Master Service Items (catalogue de services).

        Args:
            limit: Nombre maximum de produits par page (défaut: 500)

        Returns:
            Liste de dictionnaires contenant les données des produits/services
        """
        query = """
        query GetMasterServiceItems {
            allMasterServiceItems {
                id
                name
                description
                educationDescription
                amount
                duration
                isTaxable
                isArchived
                isTuning
                type
                order
                masterServiceGroup {
                    id
                    name
                }
                createdAt
                updatedAt
            }
        }
        """

        result = self._execute_query(query)
        all_products = result.get('data', {}).get('allMasterServiceItems', [])

        # Transformer les données pour extraire les langues FR et EN
        products_transformed = []
        for p in all_products:
            # Extraire nom FR/EN depuis I18nString
            name_i18n = p.get('name', {})
            name_fr = name_i18n.get('fr_CA', name_i18n.get('fr', ''))
            name_en = name_i18n.get('en_US', name_i18n.get('en', ''))

            # Extraire description FR/EN
            desc_i18n = p.get('description', {})
            desc_fr = desc_i18n.get('fr_CA', desc_i18n.get('fr', ''))
            desc_en = desc_i18n.get('en_US', desc_i18n.get('en', ''))

            # Extraire groupe de service
            service_group = p.get('masterServiceGroup', {})
            group_name_i18n = service_group.get('name', {})
            group_name_fr = group_name_i18n.get('fr_CA', group_name_i18n.get('fr', ''))
            group_name_en = group_name_i18n.get('en_US', group_name_i18n.get('en', ''))

            products_transformed.append({
                **p,
                'name_fr': name_fr,
                'name_en': name_en,
                'description_fr': desc_fr,
                'description_en': desc_en,
                'group_name_fr': group_name_fr,
                'group_name_en': group_name_en,
                'group_id': service_group.get('id')
            })

        # Limiter le nombre de résultats si nécessaire
        if limit and len(products_transformed) > limit:
            products_transformed = products_transformed[:limit]

        print(f"✅ {len(products_transformed)} produits/services récupérés depuis Master Service Items")
        return products_transformed

    def get_timeline_entries(self, limit: Optional[int] = None, since_date: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Récupère les entrées de timeline (notes techniques, mesures, événements).

        Args:
            limit: Nombre maximum d'entrées (None = toutes)
            since_date: Date ISO depuis laquelle récupérer les entrées (mode incrémental)

        Returns:
            Liste de dictionnaires contenant les timeline entries
        """
        # Construire la query avec filtre de date optionnel
        # NOTE: occurredAtGet signifie >= (Greater Than or Equal), pas ==
        # TODO: Vérifier les VRAIS noms de champs avec NotebookLM
        query = """
        query GetTimelineEntries($cursor: String, $occurredAtGet: CoreDateTime) {
            allTimelineEntries(first: 100, after: $cursor, occurredAtGet: $occurredAtGet) {
                edges {
                    node {
                        id
                        occurredAt
                        type
                        summary
                        comment
                        client {
                            id
                        }
                        piano {
                            id
                        }
                        invoice {
                            id
                        }
                        estimate {
                            id
                        }
                        user {
                            id
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

        all_entries = []
        cursor = None
        page_count = 0

        while True:
            # Construire les variables avec filtre de date optionnel
            variables = {}
            if cursor:
                variables["cursor"] = cursor
            if since_date:
                variables["occurredAtGet"] = since_date  # occurredAtGet = filtre >= (confirmed par doc)

            result = self._execute_query(query, variables)

            batch_data = result.get('data', {}).get('allTimelineEntries', {})
            edges = batch_data.get('edges', [])
            page_info = batch_data.get('pageInfo', {})

            # Extraire les nodes
            nodes = [edge['node'] for edge in edges if 'node' in edge]
            all_entries.extend(nodes)

            page_count += 1
            print(f"📄 Page {page_count}: {len(nodes)} entrées timeline récupérées")

            # Vérifier si on a atteint la limite
            if limit and len(all_entries) >= limit:
                print(f"⚠️ Limite de {limit} entrées atteinte")
                all_entries = all_entries[:limit]
                break

            # Vérifier s'il y a une page suivante
            if not page_info.get('hasNextPage'):
                print("✅ Toutes les pages récupérées")
                break

            cursor = page_info.get('endCursor')

        print(f"✅ {len(all_entries)} entrées timeline récupérées depuis l'API")
        return all_entries

    def get_recent_timeline_entries_for_client(self, client_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Récupère les N dernières entrées timeline pour un client SANS filtre de date.

        LEÇON MARGOT (2026-01-11): La méthode brute est plus fiable pour les données récentes
        car elle évite les problèmes de:
        - Fuseaux horaires UTC vs local
        - Entrées attachées au piano plutôt qu'au client
        - Délais de propagation de l'API

        Args:
            client_id: ID du client Gazelle (ex: 'cli_9UMLkteep8EsISbG')
            limit: Nombre d'entrées à récupérer (défaut: 50)

        Returns:
            Liste des entrées timeline les plus récentes pour ce client
        """
        query = """
        query GetRecentEntriesForClient($clientId: String!, $limit: Int!) {
            allTimelineEntries(clientId: $clientId, first: $limit) {
                edges {
                    node {
                        id
                        occurredAt
                        type
                        summary
                        comment
                        client { id }
                        piano { id }
                        invoice { id }
                        estimate { id }
                        user { id }
                    }
                }
            }
        }
        """

        variables = {
            "clientId": client_id,
            "limit": limit
        }

        result = self._execute_query(query, variables)

        timeline_data = result.get('data', {}).get('allTimelineEntries', {})
        edges = timeline_data.get('edges', [])
        entries = [edge['node'] for edge in edges if 'node' in edge]

        print(f"✅ {len(entries)} entrées récentes récupérées pour client {client_id}")
        return entries

    def create_timeline_entry(
        self,
        piano_id: str,
        summary: str,
        comment: Optional[str] = None,
        technician_id: Optional[str] = None,
        occurred_at: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Crée une entrée de timeline (note de service) pour un piano dans Gazelle.

        Args:
            piano_id: ID du piano dans Gazelle
            summary: Résumé de l'entrée (ex: "Accord", "Humidité à faire")
            comment: Commentaire détaillé (ex: notes de travail)
            technician_id: ID du technicien qui a effectué le travail
            occurred_at: Date ISO de l'événement (défaut: maintenant)

        Returns:
            Dictionnaire contenant l'entrée créée
        """
        from datetime import datetime

        if not occurred_at:
            occurred_at = datetime.now().isoformat()

        mutation = """
        mutation CreateTimelineEntry(
            $pianoId: ID!
            $summary: String!
            $comment: String
            $userId: ID
            $occurredAt: CoreDateTime!
        ) {
            createTimelineEntry(
                input: {
                    pianoId: $pianoId
                    summary: $summary
                    comment: $comment
                    userId: $userId
                    occurredAt: $occurredAt
                }
            ) {
                timelineEntry {
                    id
                    occurredAt
                    type
                    summary
                    comment
                    piano {
                        id
                    }
                    user {
                        id
                    }
                }
                errors {
                    field
                    message
                }
            }
        }
        """

        variables = {
            "pianoId": piano_id,
            "summary": summary,
            "comment": comment,
            "userId": technician_id,
            "occurredAt": occurred_at
        }

        result = self._execute_query(mutation, variables)

        if not result:
            raise ValueError("Erreur lors de la création de l'entrée timeline")

        create_result = result.get("data", {}).get("createTimelineEntry", {})
        errors = create_result.get("errors", [])

        if errors:
            error_messages = [e.get("message", "Erreur inconnue") for e in errors]
            raise ValueError(f"Erreurs lors de la création: {', '.join(error_messages)}")

        timeline_entry = create_result.get("timelineEntry")
        if not timeline_entry:
            raise ValueError("Aucune entrée timeline retournée par l'API")

        print(f"✅ Timeline entry créée: {timeline_entry.get('id')}")
        return timeline_entry

    def update_piano_last_tuned_date(self, piano_id: str, last_tuned_date: Optional[str] = None) -> Dict[str, Any]:
        """
        Met à jour la date du dernier accord (manualLastService) d'un piano dans Gazelle.

        NOTE: Gazelle utilise 'manualLastService' pour la date du dernier accord manuel.
              Cette fonction met à jour ce champ dans le piano.

        Args:
            piano_id: ID du piano dans Gazelle
            last_tuned_date: Date ISO du dernier accord (défaut: aujourd'hui)

        Returns:
            Dictionnaire contenant le piano mis à jour
        """
        from datetime import datetime

        if not last_tuned_date:
            last_tuned_date = datetime.now().date().isoformat()

        # Correct mutation syntax per Gazelle schema:
        # updatePiano(id: String!, input: PrivatePianoInput!)
        # Field name is 'manualLastService' not 'lastTunedDate'
        mutation = """
        mutation UpdatePianoManualLastService(
            $pianoId: String!
            $manualLastService: CoreDate!
        ) {
            updatePiano(
                id: $pianoId
                input: {
                    manualLastService: $manualLastService
                }
            ) {
                piano {
                    id
                    manualLastService
                    eventLastService
                    calculatedLastService
                }
                mutationErrors {
                    fieldName
                    messages
                }
            }
        }
        """

        variables = {
            "pianoId": piano_id,
            "manualLastService": last_tuned_date
        }

        result = self._execute_query(mutation, variables)

        if not result:
            raise ValueError("Erreur lors de la mise à jour du piano")

        update_result = result.get("data", {}).get("updatePiano", {})
        mutation_errors = update_result.get("mutationErrors", [])

        if mutation_errors:
            error_messages = []
            for e in mutation_errors:
                field = e.get('fieldName', '')
                messages = e.get('messages', [])
                if messages:
                    error_messages.append(f"{field}: {', '.join(messages)}")
                else:
                    error_messages.append(f"{field}: Erreur inconnue")
            raise ValueError(f"Erreurs lors de la mise à jour: {', '.join(error_messages)}")

        piano = update_result.get("piano")
        if not piano:
            raise ValueError("Aucun piano retourné par l'API")

        print(f"✅ Piano mis à jour: {piano.get('id')} - manualLastService: {piano.get('manualLastService')}")
        return piano

    def push_technician_service(
        self,
        piano_id: str,
        technician_note: str,
        service_type: str = "TUNING",
        technician_id: Optional[str] = None,
        client_id: Optional[str] = None,
        event_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Crée un événement de service dans Gazelle pour enregistrer une note de technicien.
        
        Cette fonction crée un événement de type SERVICE qui apparaîtra dans l'historique
        du piano et créera automatiquement une timeline entry.
        
        Args:
            piano_id: ID du piano dans Gazelle
            technician_note: Note du technicien (sera placée dans le champ notes)
            service_type: Type de service (TUNING, REPAIR, etc.) - défaut: TUNING
            technician_id: ID du technicien qui a effectué le travail (défaut: utilisateur actuel)
            client_id: ID du client propriétaire du piano (optionnel, sera récupéré si non fourni)
            event_date: Date ISO de l'événement (défaut: maintenant)
        
        Returns:
            Dictionnaire contenant l'événement créé
        """
        from datetime import datetime
        
        if not event_date:
            event_date = datetime.now().isoformat()
        
        # Si client_id n'est pas fourni, récupérer celui du piano
        if not client_id:
            try:
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
                piano_result = self._execute_query(piano_query, {"pianoId": piano_id})
                piano_data = piano_result.get("data", {}).get("piano", {})
                client_id = piano_data.get("client", {}).get("id")
            except Exception as e:
                # Si erreur, on continue sans client_id - Gazelle utilisera celui du piano
                print(f"⚠️  Impossible de récupérer le client du piano: {e}")
                client_id = None
        
        # Créer le titre de l'événement
        title = f"Service: {service_type}"
        
        # Mutation pour créer l'événement
        # SIMPLIFIÉ: Ne pas inclure client/user dans la réponse - seulement les champs essentiels
        mutation = """
        mutation CreateServiceEvent(
            $input: PrivateEventInput!
        ) {
            createEvent(input: $input) {
                event {
                    id
                    title
                    start
                    type
                    status
                    notes
                    allEventPianos(first: 10) {
                        nodes {
                            piano {
                                id
                            }
                            isTuning
                        }
                    }
                }
                mutationErrors {
                    fieldName
                    messages
                }
            }
        }
        """
        
        # Construire l'input pour createEvent
        # ESSENTIEL: title, start, duration, type, notes, clientId (si disponible), pianos
        event_input = {
            "title": title,
            "start": event_date,
            "duration": 60,  # Durée par défaut: 1 heure
            "type": "APPOINTMENT",  # Type fixe: APPOINTMENT
            "notes": f"{service_type}: {technician_note}",  # Notes de service
            "pianos": [{"pianoId": piano_id, "isTuning": True}]  # isTuning: True = "Il s'agit d'un accord pour ce piano"
        }
        
        # Ajouter clientId si disponible (récupéré depuis le piano ou fourni)
        if client_id:
            event_input["clientId"] = client_id
        
        variables = {
            "input": event_input
        }
        
        try:
            result = self._execute_query(mutation, variables)
        except Exception as e:
            error_msg = str(e)
            # Si pianos cause une erreur, essayer sans
            if "pianos" in error_msg.lower() or "Field is not defined" in error_msg:
                print("⚠️  Tentative sans champ pianos...")
                event_input_no_pianos = {k: v for k, v in event_input.items() if k != "pianos"}
                variables = {"input": event_input_no_pianos}
                result = self._execute_query(mutation, variables)
            else:
                raise
        
        if not result:
            raise ValueError("Erreur lors de la création de l'événement")
        
        # Vérifier s'il y a des erreurs dans la réponse
        errors = result.get("errors", [])
        if errors:
            error_messages = [e.get("message", "Erreur inconnue") for e in errors]
            raise ValueError(f"Erreurs GraphQL: {', '.join(error_messages)}")
        
        create_result = result.get("data", {}).get("createEvent")
        
        if not create_result:
            raise ValueError(f"Aucune réponse de createEvent. Structure: {result}")
        
        # Vérifier les erreurs de mutation
        mutation_errors = create_result.get("mutationErrors", [])
        if mutation_errors:
            error_messages = []
            for e in mutation_errors:
                field = e.get('fieldName', '')
                messages = e.get('messages', [])
                if messages:
                    error_messages.append(f"{field}: {', '.join(messages)}")
                else:
                    error_messages.append(f"{field}: Erreur inconnue")
            raise ValueError(f"Erreurs de mutation: {', '.join(error_messages)}")
        
        # La réponse peut être directement l'événement ou dans un champ event
        event = create_result if isinstance(create_result, dict) and "id" in create_result else create_result.get("event")
        
        if not event:
            raise ValueError(f"Événement None retourné. Réponse complète: {result}. Vérifiez les champs requis.")
        
        event_id = event.get('id')
        print(f"✅ Événement de service créé: {event_id}")
        
        # Compléter l'événement via completeEvent avec serviceHistoryNotes pour créer l'entrée dans l'historique
        try:
            complete_mutation = """
            mutation CompleteEvent(
                $eventId: String!
                $input: PrivateCompleteEventInput!
            ) {
                completeEvent(eventId: $eventId, input: $input) {
                    event {
                        id
                        title
                        start
                        type
                        status
                        notes
                        allEventPianos(first: 10) {
                            nodes {
                                piano {
                                    id
                                }
                                isTuning
                            }
                        }
                    }
                    mutationErrors {
                        fieldName
                        messages
                    }
                }
            }
            """
            
            # Utiliser completeEvent avec serviceHistoryNotes pour créer l'entrée dans l'historique
            # serviceHistoryNotes est un tableau de PrivateCompletionServiceHistoryInput
            complete_input = {
                "resultType": "COMPLETE",
                "serviceHistoryNotes": [{
                    "pianoId": piano_id,
                    "notes": technician_note
                }]
            }
            
            complete_result = self._execute_query(complete_mutation, {
                "eventId": event_id,
                "input": complete_input
            })
            
            complete_data = complete_result.get("data", {}).get("completeEvent", {})
            mutation_errors = complete_data.get("mutationErrors", [])
            
            if mutation_errors:
                error_messages = []
                for e in mutation_errors:
                    field = e.get('fieldName', '')
                    messages = e.get('messages', [])
                    if messages:
                        error_messages.append(f"{field}: {', '.join(messages)}")
                    else:
                        error_messages.append(f"{field}: Erreur inconnue")
                print(f"⚠️  Erreurs lors de completeEvent: {', '.join(error_messages)}")
            else:
                completed_event = complete_data.get("event")
                if completed_event:
                    if completed_event.get("status") == "COMPLETE":
                        print(f"✅ Événement complété avec serviceHistoryNotes (historique créé)")
                    # Fusionner les données mises à jour avec l'événement initial
                    event = {**event, **completed_event}
                else:
                    print(f"⚠️  Note: Événement créé mais completeEvent échoué")
        except Exception as e:
            print(f"⚠️  Impossible de compléter l'événement: {e}")
            print(f"   L'événement a été créé mais doit être complété manuellement dans Gazelle")
        
        print(f"   Piano: {piano_id}")
        print(f"   Technicien: {technician_id}")
        print(f"   Note: {technician_note[:50]}...")
        
        return event

    def verify_inactive_history(self, piano_id: str, event_id: str) -> Dict[str, Any]:
        """
        Vérifie qu'un événement est bien présent dans l'historique même si le piano est inactif.
        
        Args:
            piano_id: ID du piano
            event_id: ID de l'événement à vérifier
        
        Returns:
            Dictionnaire avec les résultats de la vérification
        """
        try:
            # 1. Vérifier le statut du piano
            piano_query = """
            query GetPianoStatus($pianoId: String!) {
                piano(id: $pianoId) {
                    id
                    status
                }
            }
            """
            piano_result = self._execute_query(piano_query, {"pianoId": piano_id})
            piano_data = piano_result.get("data", {}).get("piano", {})
            piano_status = piano_data.get("status")
            
            # 2. Vérifier que l'événement existe et est complété
            event_query = """
            query GetEvent($eventId: String!) {
                event(eventId: $eventId) {
                    id
                    status
                    type
                    allEventPianos(first: 10) {
                        nodes {
                            piano {
                                id
                            }
                            isTuning
                        }
                    }
                }
            }
            """
            event_result = self._execute_query(event_query, {"eventId": event_id})
            event_data = event_result.get("data", {}).get("event", {})
            
            return {
                "piano_id": piano_id,
                "piano_status": piano_status,
                "event_id": event_id,
                "event_exists": event_data is not None,
                "event_status": event_data.get("status") if event_data else None,
                "piano_associated": any(
                    p.get("piano", {}).get("id") == piano_id 
                    for p in event_data.get("allEventPianos", {}).get("nodes", [])
                ) if event_data else False,
                "is_inactive_and_has_history": piano_status != "ACTIVE" and event_data is not None and event_data.get("status") == "COMPLETE"
            }
        except Exception as e:
            return {
                "error": str(e),
                "piano_id": piano_id,
                "event_id": event_id
            }

    def parse_temperature_humidity(self, text: str) -> Optional[Dict[str, int]]:
        """
        Parse temperature and humidity from service note text.

        Args:
            text: Service note text (e.g., "24c. 34%" or "Temperature: 22°C, humidity: 45%")

        Returns:
            Dict with 'temperature' (int, Celsius) and 'humidity' (int, percent)
            or None if both values not found

        Examples:
            >>> parse_temperature_humidity("24c. 34%")
            {'temperature': 24, 'humidity': 34}
        """
        import re

        if not text:
            return None

        # Extract temperature (22°C, 22c, 22 degrees) - require degree symbol or explicit temp keywords
        temp_match = re.search(r'(\d+)\s*(?:°\s*(?:Celsius|C)?|c(?:elsius)?(?:\s|\.|\b))', text, re.IGNORECASE)

        # Extract humidity - try with keyword first
        humidity_match = re.search(r'(?:humidité|humidity)[^0-9]*(\d+)\s*%', text, re.IGNORECASE)

        # Fallback: find all percentages, take first one
        if not humidity_match:
            all_percent = re.findall(r'(\d+)\s*%', text)
            if all_percent:
                humidity_value = int(all_percent[0])
            else:
                humidity_value = None
        else:
            humidity_value = int(humidity_match.group(1))

        # Only return if BOTH temperature AND humidity found
        if temp_match and humidity_value is not None:
            temp_value = int(temp_match.group(1))

            # Validate ranges
            if -20 <= temp_value <= 50 and 0 <= humidity_value <= 100:
                return {
                    'temperature': temp_value,
                    'humidity': humidity_value
                }

        return None

    def create_piano_measurement(
        self,
        piano_id: str,
        temperature: int,
        humidity: int,
        taken_on: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a piano measurement (temperature/humidity) in Gazelle.

        Args:
            piano_id: ID of the piano in Gazelle (e.g., "ins_hUTnjvtZc6I6cXxA")
            temperature: Temperature in Celsius (integer)
            humidity: Relative humidity percentage (integer)
            taken_on: ISO date when measurement was taken (default: today)

        Returns:
            Dict containing the created measurement with id, pianoId, temperature, humidity

        Raises:
            ValueError: If Gazelle API returns mutationErrors
        """
        from datetime import date

        if not taken_on:
            taken_on = date.today().isoformat()

        mutation = """
        mutation CreatePianoMeasurement($input: PrivatePianoMeasurementInput!) {
            createPianoMeasurement(input: $input) {
                pianoMeasurement {
                    id
                    pianoId
                    takenOn
                    temperature
                    humidity
                    createdAt
                }
                mutationErrors {
                    fieldName
                    messages
                }
            }
        }
        """

        variables = {
            "input": {
                "pianoId": piano_id,
                "temperature": temperature,
                "humidity": humidity,
                "takenOn": taken_on
            }
        }

        result = self._execute_query(mutation, variables)
        data = result.get("data", {}).get("createPianoMeasurement", {})

        # Check for errors
        mutation_errors = data.get("mutationErrors", [])
        if mutation_errors:
            error_msgs = [f"{e.get('fieldName')}: {', '.join(e.get('messages', []))}"
                         for e in mutation_errors]
            raise ValueError(f"Failed to create measurement: {'; '.join(error_msgs)}")

        measurement = data.get("pianoMeasurement")
        if not measurement:
            raise ValueError("No measurement returned from API")

        return measurement

    def push_technician_service_with_measurements(
        self,
        piano_id: str,
        technician_note: str,
        service_type: str = "TUNING",
        technician_id: Optional[str] = None,
        client_id: Optional[str] = None,
        event_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Push service note avec parsing automatique de température/humidité.

        CRITICAL: Cette fonction effectue le pipeline complet de push vers Gazelle:
        1. Met à jour le champ "Last Tuned" du piano dans Gazelle
        2. Crée une note de service dans l'historique Gazelle
        3. Parse température/humidité et crée une mesure si détectée

        Args:
            event_date: Date ISO de l'événement (utilisée pour l'historique Gazelle)
                       Si None, utilise maintenant. Si fournie, utilise cette date
                       (ex: date de complétion du piano, pas date du push).
            Autres args: Identiques à push_technician_service

        Returns:
            {
                "service_note": {...},      # Event from push_technician_service
                "measurement": {...} | None, # Created measurement or None
                "parsed_values": {...} | None, # Parsed temp/humidity or None
                "last_tuned_updated": bool # True if Last Tuned was updated
            }
        """
        from datetime import datetime

        # 1. Create service note in Gazelle history (Last Tuned sera mis à jour automatiquement par completeEvent)
        service_note = None
        try:
            print(f"🔄 Creating service note in Gazelle history...")
            service_note = self.push_technician_service(
                piano_id=piano_id,
                technician_note=technician_note,
                service_type=service_type,
                technician_id=technician_id,
                client_id=client_id,
                event_date=event_date
            )
            print(f"✅ Service note created: {service_note.get('id')}")
        except Exception as e:
            print(f"❌ CRITICAL: Failed to create service note: {e}")
            print(f"   Full error details: {str(e)}")
            import traceback
            print(f"   Traceback: {traceback.format_exc()}")
            raise  # Service note creation is critical - fail if it doesn't work

        # 3. Parse for measurements
        parsed = self.parse_temperature_humidity(technician_note)
        if parsed:
            print(f"🔍 Parsed temperature/humidity: {parsed['temperature']}°C, {parsed['humidity']}%")
        else:
            print(f"ℹ️  No temperature/humidity detected in notes")

        # 4. Create measurement if found
        measurement = None
        if parsed:
            try:
                # Use event_date if provided, otherwise today
                measurement_date = event_date.split('T')[0] if event_date else None

                print(f"🔄 Creating measurement in Gazelle...")
                measurement = self.create_piano_measurement(
                    piano_id=piano_id,
                    temperature=parsed['temperature'],
                    humidity=parsed['humidity'],
                    taken_on=measurement_date
                )
                print(f"✅ Measurement created: {measurement['id']} ({parsed['temperature']}°C, {parsed['humidity']}%)")
            except Exception as e:
                # Log warning but don't fail service note creation
                print(f"⚠️  Failed to create measurement: {e}")
                print(f"   Full error details: {str(e)}")
                import traceback
                print(f"   Traceback: {traceback.format_exc()}")

        # ÉTAPE FINALE: Remettre le piano en INACTIVE si nécessaire (après note ET mesures)
        # Gazelle peut avoir activé le piano automatiquement lors de createEvent ou createMeasurement
        try:
            # Vérifier d'abord le statut actuel
            piano_status_query = """
            query GetPianoStatus($pianoId: String!) {
                piano(id: $pianoId) {
                    id
                    status
                }
            }
            """
            status_result = self._execute_query(piano_status_query, {"pianoId": piano_id})
            current_status = status_result.get("data", {}).get("piano", {}).get("status")
            
            # Si le piano est ACTIVE, le remettre en INACTIVE
            if current_status == "ACTIVE":
                update_status_mutation = """
                mutation UpdatePianoStatus($pianoId: String!, $input: PrivatePianoInput!) {
                    updatePiano(id: $pianoId, input: $input) {
                        piano {
                            id
                            status
                        }
                        mutationErrors {
                            fieldName
                            messages
                        }
                    }
                }
                """
                update_status_result = self._execute_query(update_status_mutation, {
                    "pianoId": piano_id,
                    "input": {"status": "INACTIVE"}
                })
                
                update_status_data = update_status_result.get("data", {}).get("updatePiano", {})
                status_errors = update_status_data.get("mutationErrors", [])
                
                if status_errors:
                    error_messages = []
                    for e in status_errors:
                        field = e.get('fieldName', '')
                        messages = e.get('messages', [])
                        if messages:
                            error_messages.append(f"{field}: {', '.join(messages)}")
                        else:
                            error_messages.append(f"{field}: Erreur inconnue")
                    print(f"⚠️  Impossible de remettre le piano en INACTIVE: {', '.join(error_messages)}")
                else:
                    updated_piano = update_status_data.get("piano", {})
                    if updated_piano.get("status") == "INACTIVE":
                        print(f"✅ Piano remis en INACTIVE après toutes les opérations (note + mesures)")
            else:
                print(f"✅ Piano déjà {current_status}, pas de modification nécessaire")
        except Exception as e:
            print(f"⚠️  Impossible de vérifier/modifier le statut du piano: {e}")
            print(f"   Les opérations ont été créées mais le statut n'a pas pu être modifié")

        return {
            "service_note": service_note,
            "measurement": measurement,
            "parsed_values": parsed,
            "last_tuned_updated": True  # Toujours True car completeEvent met à jour automatiquement
        }

    def get_users(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Récupère tous les utilisateurs/techniciens depuis l'API.

        Args:
            limit: Nombre maximum d'utilisateurs par page (défaut: 100)

        Returns:
            Liste de dictionnaires contenant les données des utilisateurs
        """
        # Note: L'API Gazelle GraphQL utilise probablement allCompanyUsers ou similar
        # Essayons d'abord avec les users directement depuis timeline entries
        # Comme workaround, on va extraire les users uniques des timeline entries

        print("⚠️  Note: L'API Gazelle ne semble pas exposer allUsers directement")
        print("   Extraction des users depuis les timeline entries...")

        # Récupérer les timeline entries avec les users
        query = """
        query GetUsersFromTimeline($cursor: String) {
            allTimelineEntries(first: 100, after: $cursor) {
                edges {
                    node {
                        user {
                            id
                            firstName
                            lastName
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

        users_map = {}  # Utiliser un dict pour dédupliquer par ID
        cursor = None
        page_count = 0

        while True:
            variables = {}
            if cursor:
                variables["cursor"] = cursor

            result = self._execute_query(query, variables)
            batch_data = result.get('data', {}).get('allTimelineEntries', {})
            edges = batch_data.get('edges', [])
            page_info = batch_data.get('pageInfo', {})

            # Extraire les users uniques
            for edge in edges:
                node = edge.get('node', {})
                user = node.get('user')
                if user and user.get('id'):
                    user_id = user['id']
                    if user_id not in users_map:
                        users_map[user_id] = user

            page_count += 1
            print(f"📄 Page {page_count}: {len(users_map)} users uniques trouvés")

            # Limiter les pages pour ne pas tout scanner
            if page_count >= 10:  # Limiter à 10 pages (1000 entries)
                break

            if not page_info.get('hasNextPage'):
                break

            cursor = page_info.get('endCursor')

        all_users = list(users_map.values())

        print(f"✅ {len(all_users)} utilisateurs uniques récupérés depuis timeline entries")
        return all_users


if __name__ == '__main__':
    # Test basique du client
    try:
        client = GazelleAPIClient()
        print("✅ Client API initialisé avec succès")
        
        # Test: récupérer quelques clients
        clients = client.get_clients(limit=5)
        print(f"📋 Exemple de client: {clients[0] if clients else 'Aucun client trouvé'}")
        
    except Exception as e:
        print(f"❌ Erreur: {e}")

    
    def _generate_new_token(self) -> None:
        """Generate new token using client credentials."""
        print(f"🔑 Génération token avec client_id: {self.client_id[:20]}...")
        response = requests.post(
            OAUTH_TOKEN_URL,
            data={
                'grant_type': 'client_credentials',
                'client_id': self.client_id,
                'client_secret': self.client_secret
            }
        )
        
        if response.status_code == 200:
            token_data = response.json()
            token_data['created_at'] = int(time.time())
            self._save_token(token_data)
            print("✅ Token généré avec succès")
        else:
            print(f"❌ Erreur génération token: {response.status_code}")
            print(f"Response: {response.text}")
            raise ConnectionError(f"Impossible de générer un token: {response.status_code}")
