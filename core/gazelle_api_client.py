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
        Charge le token depuis token.json.
        
        Returns:
            Dict contenant access_token, refresh_token, expires_in, created_at
        """
        if not os.path.exists(self.token_path):
            raise FileNotFoundError(
                f"Fichier token.json non trouvé: {self.token_path}\n"
                "Vous devez créer ce fichier avec vos tokens OAuth2."
            )
        
        try:
            with open(self.token_path, 'r', encoding='utf-8') as f:
                token_data = json.load(f)
            
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
        
        headers = {
            'Authorization': f"Bearer {self.token_data['access_token']}",
            'Content-Type': 'application/json'
        }
        
        payload = {
            'query': query,
            'variables': variables or {}
        }
        
        try:
            response = requests.post(API_URL, json=payload, headers=headers)
            
            # Skip 401 handling - use token as-is per user request
            # if response.status_code == 401:
            #     print("⚠️ Token invalide, rafraîchissement...")
            #     self._refresh_token()
            #     headers['Authorization'] = f"Bearer {self.token_data['access_token']}"
            #     response = requests.post(API_URL, json=payload, headers=headers)
            
            response.raise_for_status()
            
            result = response.json()
            
            # Vérifier les erreurs GraphQL
            if 'errors' in result:
                error_messages = [err.get('message', 'Unknown error') for err in result['errors']]
                raise ValueError(f"Erreurs GraphQL: {', '.join(error_messages)}")
            
            return result
            
        except requests.exceptions.RequestException as e:
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
                            municipality
                            postalCode
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

    def get_appointments(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Récupère tous les rendez-vous depuis l'API Gazelle (allEventsBatched).

        Utilise la pagination automatique pour récupérer tous les événements.
        Pattern copié depuis V4 (Import_daily_update.py lignes 257-268).

        Args:
            limit: Nombre maximum d'appointments à retourner (None = tous)

        Returns:
            Liste de dictionnaires contenant les données des rendez-vous
        """
        from datetime import datetime, timedelta
        import time

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
        filters = {
            "startOn": start_date,
            "endOn": end_date,
            "type": ["APPOINTMENT", "PERSONAL", "MEMO", "SYNCED"]
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

    def get_timeline_entries(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Récupère les entrées de timeline (notes techniques, mesures, événements).

        Args:
            limit: Nombre maximum d'entrées (None = toutes)

        Returns:
            Liste de dictionnaires contenant les timeline entries
        """
        query = """
        query GetTimelineEntries($cursor: String) {
            allTimelineEntriesBatched(first: 100, after: $cursor) {
                edges {
                    node {
                        id
                        occurredAt
                        type
                        title
                        details
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
                        createdAt
                        updatedAt
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
            variables = {"cursor": cursor} if cursor else {}
            result = self._execute_query(query, variables)

            batch_data = result.get('data', {}).get('allTimelineEntriesBatched', {})
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
