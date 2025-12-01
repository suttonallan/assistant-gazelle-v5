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

# Chemin vers le dossier de configuration
CONFIG_DIR = os.path.join(os.path.dirname(__file__), 'config')

# Charger les variables d'environnement depuis config/.env
env_path = os.path.join(CONFIG_DIR, '.env')
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
        self.client_id = os.getenv('GAZELLE_CLIENT_ID')
        self.client_secret = os.getenv('GAZELLE_CLIENT_SECRET')
        
        if not self.client_id or not self.client_secret:
            raise ValueError(
                f"GAZELLE_CLIENT_ID et GAZELLE_CLIENT_SECRET doivent être définis dans {env_path}"
            )
        
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
            
            # Vérifier que le token n'est pas expiré
            if self._is_token_expired(token_data):
                print("⚠️ Token expiré, rafraîchissement...")
                self._refresh_token()
                token_data = self._load_token()
            
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
        # S'assurer que le token est valide
        if self._is_token_expired(self.token_data):
            self._refresh_token()
        
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
            
            # Si 401 (Unauthorized), rafraîchir le token et réessayer
            if response.status_code == 401:
                print("⚠️ Token invalide, rafraîchissement...")
                self._refresh_token()
                headers['Authorization'] = f"Bearer {self.token_data['access_token']}"
                response = requests.post(API_URL, json=payload, headers=headers)
            
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
                    clientId
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

