#!/usr/bin/env python3
"""
Module pour envoyer des SMS via l'API Zoom Phone.

Utilise l'endpoint /phone/users/{userId}/sms avec authentification OAuth 2.0.
Le scope phone:write:sms doit être activé sur Zoom.
"""

import os
import re
import requests
from typing import Optional, Dict, Any
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

# Configuration Zoom API
ZOOM_API_BASE_URL = "https://api.zoom.us/v2"
ZOOM_OAUTH_TOKEN_URL = "https://zoom.us/oauth/token"


def format_phone_number(phone_number: str) -> str:
    """
    Formate un numéro de téléphone au format E.164 (ex: +15551234567).
    
    Args:
        phone_number: Numéro de téléphone (peut être avec ou sans formatage)
    
    Returns:
        Numéro formaté en E.164
    
    Raises:
        ValueError: Si le numéro ne peut pas être formaté
    """
    # Retirer tous les caractères non numériques sauf le +
    cleaned = re.sub(r'[^\d+]', '', phone_number)
    
    # Si le numéro commence par +, le garder
    if cleaned.startswith('+'):
        formatted = cleaned
    # Si le numéro commence par 1 (code pays US/Canada), ajouter +
    elif cleaned.startswith('1') and len(cleaned) == 11:
        formatted = '+' + cleaned
    # Si le numéro a 10 chiffres (sans code pays), ajouter +1
    elif len(cleaned) == 10:
        formatted = '+1' + cleaned
    # Si le numéro a 11 chiffres et commence par 1, ajouter +
    elif len(cleaned) == 11 and cleaned[0] == '1':
        formatted = '+' + cleaned
    else:
        raise ValueError(
            f"Impossible de formater le numéro '{phone_number}'. "
            f"Format attendu: 10 chiffres (US/Canada) ou format E.164 (+1XXXXXXXXXX)"
        )
    
    # Vérifier que le format E.164 est correct (commence par + suivi de 1-15 chiffres)
    if not re.match(r'^\+\d{1,15}$', formatted):
        raise ValueError(
            f"Numéro formaté invalide: '{formatted}'. "
            f"Format E.164 attendu: +[code pays][numéro] (max 15 chiffres après le +)"
        )
    
    return formatted


def get_zoom_access_token() -> str:
    """
    Récupère un access token Zoom via OAuth 2.0.
    
    Utilise les credentials depuis les variables d'environnement:
    - ZOOM_CLIENT_ID
    - ZOOM_CLIENT_SECRET
    - ZOOM_ACCOUNT_ID (optionnel, pour Server-to-Server OAuth)
    
    Returns:
        Access token Zoom
    
    Raises:
        ValueError: Si les credentials ne sont pas configurés
        requests.RequestException: Si la requête OAuth échoue
    """
    client_id = os.getenv('ZOOM_CLIENT_ID')
    client_secret = os.getenv('ZOOM_CLIENT_SECRET')
    account_id = os.getenv('ZOOM_ACCOUNT_ID')  # Optionnel pour Server-to-Server OAuth
    
    if not client_id or not client_secret:
        raise ValueError(
            "ZOOM_CLIENT_ID et ZOOM_CLIENT_SECRET doivent être configurés dans .env"
        )
    
    # Si ZOOM_ACCOUNT_ID est fourni, utiliser Server-to-Server OAuth
    if account_id:
        # Server-to-Server OAuth (recommandé pour les applications)
        auth_string = f"{client_id}:{client_secret}"
        import base64
        encoded_auth = base64.b64encode(auth_string.encode()).decode()
        
        response = requests.post(
            ZOOM_OAUTH_TOKEN_URL,
            headers={
                'Authorization': f'Basic {encoded_auth}',
                'Content-Type': 'application/x-www-form-urlencoded'
            },
            data={
                'grant_type': 'account_credentials',
                'account_id': account_id
            },
            timeout=10
        )
    else:
        # OAuth standard (nécessite un refresh token)
        # Pour l'instant, on utilise les credentials directement
        # TODO: Implémenter le flow OAuth complet si nécessaire
        raise ValueError(
            "ZOOM_ACCOUNT_ID requis pour Server-to-Server OAuth. "
            "Ajoutez-le dans votre .env ou implémentez le flow OAuth standard."
        )
    
    if response.status_code != 200:
        error_detail = response.text
        raise requests.RequestException(
            f"Erreur OAuth Zoom {response.status_code}: {error_detail}"
        )
    
    token_data = response.json()
    access_token = token_data.get('access_token')
    
    if not access_token:
        raise ValueError(f"Access token non trouvé dans la réponse: {token_data}")
    
    return access_token


def get_zoom_user_id(access_token: str) -> str:
    """
    Récupère l'ID de l'utilisateur Zoom actuel.
    
    Args:
        access_token: Token d'accès Zoom
    
    Returns:
        User ID Zoom
    
    Raises:
        requests.RequestException: Si la requête échoue
    """
    response = requests.get(
        f"{ZOOM_API_BASE_URL}/users/me",
        headers={
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        },
        timeout=10
    )
    
    if response.status_code != 200:
        error_detail = response.text
        raise requests.RequestException(
            f"Erreur récupération user ID {response.status_code}: {error_detail}"
        )
    
    user_data = response.json()
    user_id = user_data.get('id')
    
    if not user_id:
        raise ValueError(f"User ID non trouvé dans la réponse: {user_data}")
    
    return user_id


def send_zoom_sms(to_number: str, message: str, user_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Envoie un SMS via l'API Zoom Phone.
    
    Args:
        to_number: Numéro de téléphone destinataire (format E.164 ou format local)
        message: Contenu du message SMS
        user_id: ID de l'utilisateur Zoom (optionnel, récupéré automatiquement si non fourni)
    
    Returns:
        Dict contenant la réponse de l'API Zoom:
        {
            'success': bool,
            'message_id': str (si succès),
            'error': str (si erreur)
        }
    
    Raises:
        ValueError: Si les paramètres sont invalides
        requests.RequestException: Si la requête API échoue
    """
    # Valider le message
    if not message or not message.strip():
        raise ValueError("Le message SMS ne peut pas être vide")
    
    if len(message) > 1600:  # Limite Zoom SMS
        raise ValueError(f"Le message est trop long ({len(message)} caractères). Maximum: 1600")
    
    # Formater le numéro de téléphone en E.164
    try:
        formatted_number = format_phone_number(to_number)
    except ValueError as e:
        return {
            'success': False,
            'error': str(e)
        }
    
    # Récupérer l'access token
    try:
        access_token = get_zoom_access_token()
    except (ValueError, requests.RequestException) as e:
        return {
            'success': False,
            'error': f"Erreur authentification Zoom: {str(e)}"
        }
    
    # Récupérer l'user ID si non fourni
    if not user_id:
        try:
            user_id = get_zoom_user_id(access_token)
        except (ValueError, requests.RequestException) as e:
            return {
                'success': False,
                'error': f"Erreur récupération user ID: {str(e)}"
            }
    
    # Envoyer le SMS
    url = f"{ZOOM_API_BASE_URL}/phone/users/{user_id}/sms"
    
    payload = {
        'to': formatted_number,
        'message': message.strip()
    }
    
    try:
        response = requests.post(
            url,
            headers={
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            },
            json=payload,
            timeout=30
        )
        
        if response.status_code in [200, 201, 204]:
            response_data = response.json() if response.content else {}
            return {
                'success': True,
                'message_id': response_data.get('id') or response_data.get('message_id'),
                'to': formatted_number,
                'response': response_data
            }
        else:
            error_detail = response.text
            return {
                'success': False,
                'error': f"Erreur API Zoom {response.status_code}: {error_detail}",
                'status_code': response.status_code
            }
            
    except requests.RequestException as e:
        return {
            'success': False,
            'error': f"Erreur requête API: {str(e)}"
        }
