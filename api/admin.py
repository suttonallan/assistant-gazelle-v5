"""
Routes Admin - Calculateurs de Frais et Kilomètres
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime, date
import sys
from pathlib import Path

# Ajouter le chemin parent pour les imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.travel_fees.calculator import TravelFeeCalculator, TravelFeeResult

router = APIRouter(prefix="/api/admin", tags=["admin"])


# ============================================================
# MODÈLES PYDANTIC
# ============================================================

class TravelFeeRequest(BaseModel):
    """Requête pour calculer les frais de déplacement."""
    destination: str  # Adresse ou code postal (partiel ou complet)
    client_name: Optional[str] = None  # Nom du client (optionnel)


class TravelFeeResponse(BaseModel):
    """Réponse avec les frais calculés."""
    destination: str
    client_name: Optional[str]
    results: List[Dict[str, Any]]
    cheapest_technician: Optional[str]
    recommendation: Optional[str]


class KilometersRequest(BaseModel):
    """Requête pour calculer les kilomètres parcourus."""
    technician_id: str
    date: str  # Format: YYYY-MM-DD
    appointments: Optional[List[Dict[str, Any]]] = None  # Optionnel: si fourni, utilise ces RV


class KilometersResponse(BaseModel):
    """Réponse avec les kilomètres calculés."""
    technician_id: str
    technician_name: str
    date: str
    total_km: float
    total_duration_minutes: float
    route_text: str
    segments: List[Dict[str, Any]]
    reimbursement: float  # Remboursement à 0.72$/km


# ============================================================
# ENDPOINTS
# ============================================================

@router.post("/travel-fees/calculate", response_model=TravelFeeResponse)
async def calculate_travel_fees(request: TravelFeeRequest) -> TravelFeeResponse:
    """
    Calcule les frais de déplacement pour tous les techniciens.
    
    Accepte:
    - Code postal (partiel ou complet): "H3B 4W8" ou "H3B"
    - Adresse partielle: "123 Rue Example"
    - Adresse complète: "123 Rue Example, Montréal, QC H3B 4W8"
    - Nom de client: cherche l'adresse dans Supabase
    """
    try:
        calculator = TravelFeeCalculator()
        
        # Si un nom de client est fourni, chercher son adresse
        destination_address = request.destination
        if request.client_name:
            try:
                from modules.assistant.services.queries import GazelleQueries
                from core.supabase_storage import SupabaseStorage
                
                storage = SupabaseStorage()
                queries = GazelleQueries(storage)
                
                # Chercher le client
                client_results = queries.search_clients([request.client_name])
                if client_results:
                    client = client_results[0]
                    # Construire l'adresse complète
                    address_parts = []
                    if client.get('address'):
                        address_parts.append(client['address'])
                    if client.get('city'):
                        address_parts.append(client['city'])
                    if client.get('postal_code'):
                        address_parts.append(client['postal_code'])
                    
                    if address_parts:
                        destination_address = ', '.join(address_parts)
            except Exception as e:
                # Si erreur, utiliser la destination fournie
                print(f"⚠️ Erreur recherche client {request.client_name}: {e}")
        
        # Calculer pour tous les techniciens
        results = calculator.calculate_all_technicians(destination_address)
        
        # Formater les résultats
        formatted_results = []
        for result in results:
            formatted_results.append({
                "technician_name": result.technician_name,
                "distance_km": round(result.distance_km, 2),
                "duration_minutes": round(result.duration_minutes, 2),
                "total_fee": round(result.total_fee, 2),
                "is_free": result.is_free,
                "breakdown": {
                    "distance_fee": round(result.distance_fee, 2),
                    "time_fee": round(result.time_fee, 2)
                }
            })
        
        # Déterminer le moins cher
        cheapest = results[0].technician_name if results else None
        
        # Générer une recommandation
        recommendation = None
        if results and len(results) > 1:
            cheapest_result = results[0]
            if cheapest_result.is_free:
                recommendation = f"💡 {cheapest_result.technician_name} est GRATUIT pour ce déplacement"
            elif cheapest_result.total_fee < results[1].total_fee:
                savings = round(results[1].total_fee - cheapest_result.total_fee, 2)
                recommendation = f"💡 {cheapest_result.technician_name} économiserait {savings}$ par rapport à {results[1].technician_name}"
        
        return TravelFeeResponse(
            destination=destination_address,
            client_name=request.client_name,
            results=formatted_results,
            cheapest_technician=cheapest,
            recommendation=recommendation
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur calcul frais: {str(e)}")


@router.post("/kilometers/calculate", response_model=KilometersResponse)
async def calculate_kilometers(request: KilometersRequest) -> KilometersResponse:
    """
    Calcule les kilomètres parcourus par un technicien pour une journée.
    
    Calcule le trajet complet: Maison → RV1 → RV2 → ... → Maison
    """
    try:
        from modules.assistant.services.distance_calculator import calculate_day_route
        from modules.assistant.services.queries import GazelleQueries
        from core.supabase_storage import SupabaseStorage
        from zoneinfo import ZoneInfo
        
        # Si les rendez-vous ne sont pas fournis, les récupérer depuis Supabase
        if not request.appointments:
            storage = SupabaseStorage()
            queries = GazelleQueries(storage)
            
            # Convertir la date string en datetime
            appointment_date = datetime.fromisoformat(request.date).date()
            appointment_datetime = datetime.combine(appointment_date, datetime.min.time())
            appointment_datetime = appointment_datetime.replace(tzinfo=ZoneInfo('America/Toronto'))
            
            # Récupérer les rendez-vous du technicien pour cette date
            all_appointments = queries.get_appointments(
                date=appointment_datetime,
                technicien=request.technician_id
            )
            
            # Enrichir les rendez-vous avec les adresses client (comme dans train_summaries.py)
            # Pour chaque rendez-vous, enrichir avec l'adresse du client
            for apt in all_appointments:
                entity_id = apt.get('client_external_id')
                if entity_id:
                    # Chercher le client pour obtenir son adresse
                    client_results = queries.search_clients([entity_id])
                    if client_results:
                        client = client_results[0]
                        apt['client_address'] = client.get('address', '')
                        apt['client_city'] = client.get('city', '')
                        apt['client_postal_code'] = client.get('postal_code', '')
                        apt['client_name'] = client.get('company_name') or f"{client.get('first_name', '')} {client.get('last_name', '')}".strip()
            
            # Convertir en format attendu par calculate_day_route
            appointments = []
            for apt in all_appointments:
                # Construire l'adresse complète
                address_parts = []
                if apt.get('client_address'):
                    address_parts.append(apt['client_address'])
                if apt.get('client_city'):
                    address_parts.append(apt['client_city'])
                if apt.get('client_postal_code'):
                    address_parts.append(apt['client_postal_code'])
                
                full_address = ', '.join(address_parts) if address_parts else ''
                
                if full_address:
                    # Parser l'heure du rendez-vous
                    appointment_time = apt.get('appointment_time', '09:00')
                    if isinstance(appointment_time, str):
                        time_parts = appointment_time.split(':')
                        hour = int(time_parts[0])
                        minute = int(time_parts[1]) if len(time_parts) > 1 else 0
                    else:
                        hour, minute = 9, 0
                    
                    start_time = appointment_datetime.replace(hour=hour, minute=minute)
                    
                    appointments.append({
                        'start_time': start_time,
                        'duration': apt.get('duration_minutes', 60),
                        'client_address': full_address,
                        'client_name': apt.get('client_name', 'N/A')
                    })
        else:
            # Utiliser les rendez-vous fournis
            appointments = request.appointments
        
        # Calculer le trajet
        route = calculate_day_route(appointments, request.technician_id)
        
        # Mapper l'ID technicien vers le nom
        technician_names = {
            'usr_HcCiFk7o0vZ9xAI0': 'Nicolas',
            'usr_ofYggsCDt2JAVeNP': 'Allan',
            'usr_ReUSmIJmBF86ilY1': 'Jean-Philippe'
        }
        technician_name = technician_names.get(request.technician_id, request.technician_id)
        
        return KilometersResponse(
            technician_id=request.technician_id,
            technician_name=technician_name,
            date=request.date,
            total_km=route['total_km'],
            total_duration_minutes=round(route['total_duration_seconds'] / 60, 1),
            route_text=route['route_text'],
            segments=route['segments'],
            reimbursement=round(route['total_km'] * 0.72, 2)
        )
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Erreur calcul kilomètres: {str(e)}")


@router.get("/travel-fees/search-client")
async def search_client_for_address(client_name: str) -> Dict[str, Any]:
    """
    Recherche des clients par nom et retourne une liste de résultats.
    Utilisé pour pré-remplir l'adresse dans le calculateur de frais.
    """
    try:
        from modules.assistant.services.queries import GazelleQueries
        from core.supabase_storage import SupabaseStorage
        
        storage = SupabaseStorage()
        queries = GazelleQueries(storage)
        
        # Chercher les clients (peut retourner plusieurs résultats)
        results = queries.search_clients([client_name])
        
        if not results:
            return {"results": []}
        
        # Formater les résultats avec TOUS les détails disponibles
        formatted_results = []
        for client in results:
            # Construire l'adresse complète
            address_parts = []
            if client.get('address'):
                address_parts.append(client['address'])
            if client.get('city'):
                address_parts.append(client['city'])
            if client.get('postal_code'):
                address_parts.append(client['postal_code'])
            
            full_address = ', '.join(address_parts) if address_parts else None
            
            # Déterminer le nom complet
            client_name_full = client.get('company_name') or f"{client.get('first_name', '')} {client.get('last_name', '')}".strip()
            
            # Récupérer les notes du client si disponibles
            notes = client.get('notes') or client.get('note') or client.get('description') or ''
            
            # Récupérer le téléphone (peut être dans plusieurs colonnes)
            phone = client.get('phone') or client.get('telephone') or client.get('phone_number') or ''
            
            # Construire l'objet résultat avec TOUS les détails
            result = {
                "client_id": client.get('external_id', ''),
                "client_name": client_name_full,
                "company_name": client.get('company_name', ''),
                "first_name": client.get('first_name', ''),
                "last_name": client.get('last_name', ''),
                "address": client.get('address', ''),
                "address_full": full_address,
                "postal_code": client.get('postal_code', ''),
                "city": client.get('city', ''),
                "province": client.get('province', ''),
                "country": client.get('country', ''),
                "phone": phone,
                "email": client.get('email', ''),
                "notes": notes[:200] if notes else '',  # Limiter à 200 caractères pour l'affichage
                "type": "client" if client.get('external_id', '').startswith('cli_') else "contact",
                # Ajouter tous les autres champs disponibles
                "all_fields": {k: v for k, v in client.items() if k not in ['notes', 'note', 'description']}
            }
            
            formatted_results.append(result)
        
        return {
            "results": formatted_results,
            "count": len(formatted_results)
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur recherche client: {str(e)}")

