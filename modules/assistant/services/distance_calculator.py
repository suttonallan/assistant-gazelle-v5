"""
Calcul distances et trajets techniciens
Adapté de: calcul_kilometres_trimestre.py (production)

Calcule les kilomètres parcourus par un technicien pour une journée complète:
Maison → RV1 → RV2 → ... → Maison
"""

import os
import time
import requests
from typing import List, Dict, Optional
from datetime import datetime, timedelta


# Charger clé Google Maps depuis .env
# Note: Chargé au runtime dans les fonctions pour éviter erreurs d'import
def get_google_maps_api_key() -> str:
    """Récupère la clé Google Maps API depuis les variables d'environnement."""
    key = os.getenv('GOOGLE_MAPS_API_KEY')
    if not key:
        raise ValueError("GOOGLE_MAPS_API_KEY non configurée dans les variables d'environnement")
    return key

# Adresses maison techniciens (IDs Supabase → adresses)
HOME_ADDRESSES = {
    'usr_HcCiFk7o0vZ9xAI0': '3520A Rue Sainte-Famille, Montréal, QC',  # Nicolas
    'usr_ofYggsCDt2JAVeNP': '780 Lanthier, Montréal, QC H4N 2A1',  # Allan
    'usr_ReUSmIJmBF86ilY1': '2127 Rue Saint-André, Montréal, QC',  # Jean-Philippe
    # Louise n'est pas technicienne
}


def google_distance_with_duration(
    origin: str, 
    destination: str,
    departure_time: Optional[datetime] = None
) -> Dict:
    """
    Calcule distance ET durée entre 2 adresses avec Google Maps.

    Args:
        origin: Adresse départ
        destination: Adresse arrivée
        departure_time: Heure départ (pour trafic temps réel)

    Returns:
        {
            'distance_km': float,
            'distance_text': str,
            'duration_seconds': int,
            'duration_text': str
        }

    Raises:
        ValueError: Si calcul échoue
    """
    api_key = get_google_maps_api_key()

    url = "https://maps.googleapis.com/maps/api/distancematrix/json"
    params = {
        "origins": origin,
        "destinations": destination,
        "mode": "driving",
        "units": "metric",
        "language": "fr",
        "key": api_key
    }

    # Ajouter heure départ si fournie (pour trafic temps réel)
    if departure_time:
        params["departure_time"] = int(departure_time.timestamp())

    try:
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()

        if data["status"] != "OK":
            raise ValueError(f"Google Maps API error: {data.get('status')}")

        element = data["rows"][0]["elements"][0]
        if element["status"] != "OK":
            raise ValueError(f"No route found: {element.get('status')}")

        return {
            'distance_km': element["distance"]["value"] / 1000.0,
            'distance_text': element["distance"]["text"],
            'duration_seconds': element["duration"]["value"],
            'duration_text': element["duration"]["text"]
        }

    except requests.exceptions.RequestException as e:
        raise ValueError(f"Request failed: {e}")


def calculate_day_route(
    appointments: List[Dict], 
    technician_id: str
) -> Dict:
    """
    Calcule trajet complet d'une journée pour un technicien.

    Args:
        appointments: Liste RV triés par heure (chaque RV doit avoir 'start_time', 'client_address', 'duration')
        technician_id: ID du technicien (ex: 'usr_HcCiFk7o0vZ9xAI0')

    Returns:
        {
            'total_km': float,
            'total_duration_seconds': int,
            'total_duration_text': str,
            'departure_from_home': datetime,
            'return_to_home': datetime,
            'route_text': str,
            'segments': [
                {'from': str, 'to': str, 'distance_km': float, 'duration_text': str},
                ...
            ]
        }
    """
    home_address = HOME_ADDRESSES.get(technician_id, '')
    if not home_address:
        raise ValueError(f"Home address not configured for {technician_id}")

    if not appointments:
        return {
            'total_km': 0.0,
            'total_duration_seconds': 0,
            'total_duration_text': '0 min',
            'departure_from_home': None,
            'return_to_home': None,
            'route_text': 'Aucun rendez-vous',
            'segments': []
        }

    # Construire liste de stops (adresses clients)
    stops = [appt['client_address'] for appt in appointments if appt.get('client_address')]

    # Dédupliquer stops consécutifs identiques
    stops_dedup = []
    for s in stops:
        if s and s.strip():
            s_norm = s.strip().lower()
            if not stops_dedup or stops_dedup[-1].strip().lower() != s_norm:
                stops_dedup.append(s)

    # Trajet complet: Maison → RV1 → RV2 → ... → Maison
    waypoints = [home_address] + stops_dedup + [home_address]

    # Calculer chaque segment
    segments = []
    total_km = 0.0
    total_duration = 0

    for i in range(len(waypoints) - 1):
        origin = waypoints[i]
        destination = waypoints[i + 1]

        # Utiliser heure du RV pour trafic temps réel (si disponible)
        departure_time = None
        if i > 0 and i <= len(appointments):  # Pas pour le premier segment (maison → RV1)
            # Utiliser l'heure du RV précédent + sa durée
            prev_idx = i - 1
            if prev_idx < len(appointments):
                prev_appt = appointments[prev_idx]
                if 'start_time' in prev_appt and 'duration' in prev_appt:
                    departure_time = prev_appt['start_time'] + timedelta(minutes=prev_appt['duration'])
        elif i == 0 and appointments:  # Premier segment: utiliser heure premier RV
            first_appt = appointments[0]
            if 'start_time' in first_appt:
                # Départ maison = heure premier RV - durée trajet estimée - buffer
                departure_time = first_appt['start_time'] - timedelta(minutes=30)

        try:
            route_info = google_distance_with_duration(origin, destination, departure_time)

            segments.append({
                'from': origin[:50] + '...' if len(origin) > 50 else origin,
                'to': destination[:50] + '...' if len(destination) > 50 else destination,
                'distance_km': round(route_info['distance_km'], 2),
                'distance_text': route_info['distance_text'],
                'duration_seconds': route_info['duration_seconds'],
                'duration_text': route_info['duration_text']
            })

            total_km += route_info['distance_km']
            total_duration += route_info['duration_seconds']

            # Rate limiting (Google Maps: 100 req/sec max)
            time.sleep(0.1)

        except Exception as e:
            print(f"[WARN] Distance calculation failed {origin[:30]} → {destination[:30]}: {e}")
            # Continuer même si un segment échoue

    # Construire texte trajet
    route_parts = ["🏠 Maison"]
    for i, stop in enumerate(stops_dedup, 1):
        route_parts.append(f"📍 RV{i}: {stop[:40]}")
    route_parts.append("🏠 Maison")
    route_text = " → ".join(route_parts)

    # Calculer heures départ/retour
    departure_from_home = None
    return_to_home = None
    
    if appointments and segments:
        first_appt = appointments[0]
        last_appt = appointments[-1]
        
        if 'start_time' in first_appt:
            # Départ maison = heure premier RV - durée trajet - buffer 5 min
            first_segment_duration = segments[0]['duration_seconds'] if segments else 0
            departure_from_home = first_appt['start_time'] - timedelta(seconds=first_segment_duration + 300)
        
        if 'start_time' in last_appt:
            # Retour maison = heure dernier RV + durée RV + durée trajet retour
            last_appt_duration = last_appt.get('duration', 60)  # minutes
            last_segment_duration = segments[-1]['duration_seconds'] if segments else 0
            return_to_home = last_appt['start_time'] + timedelta(minutes=last_appt_duration, seconds=last_segment_duration)

    return {
        'total_km': round(total_km, 1),
        'total_duration_seconds': total_duration,
        'total_duration_text': f"{total_duration // 60} min",
        'departure_from_home': departure_from_home,
        'return_to_home': return_to_home,
        'route_text': route_text,
        'segments': segments
    }

