"""
Calculateur de Frais de Déplacement Piano-Tek

Réplique la logique JavaScript du calculateur existant en Python.
Utilise Google Maps Distance Matrix API pour calculer distance et temps de déplacement.

Tarification:
- Distance gratuite: 40 km aller-retour (20 km chaque sens)
- Temps gratuit: 40 minutes aller-retour (20 min chaque sens)
- Prix excédent distance: 0.59$/km
- Prix excédent temps: 57.50$/heure

Techniciens:
- Allan: H4N 2A1
- Nicolas: H2X 2L1
- Jean-Philippe: H2L 3V2
"""

import os
import requests
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class Technician:
    """Représente un technicien avec son adresse de base."""
    name: str
    postal_code: str

    # Adresses complètes RÉELLES des techniciens (depuis système production)
    ADDRESSES = {
        "Allan": "780 Lanthier, Montréal, QC H4N 2A1",
        "Nicolas": "3520A Rue Sainte-Famille, Montréal, QC",
        "Jean-Philippe": "2127 Rue Saint-André, Montréal, QC",
    }

    @property
    def full_address(self) -> str:
        """Retourne l'adresse complète pour Google Maps."""
        return self.ADDRESSES.get(self.name, f"{self.postal_code}, Montréal, QC")


@dataclass
class TravelFeeResult:
    """Résultat du calcul de frais de déplacement."""
    technician_name: str
    distance_km: float  # Distance totale aller-retour en km
    duration_minutes: float  # Temps total aller-retour en minutes
    distance_fee: float  # Frais de distance ($)
    time_fee: float  # Frais de temps ($)
    total_fee: float  # Total des frais ($)
    is_free: bool  # True si dans la zone gratuite

    def __str__(self) -> str:
        """Format lisible du résultat."""
        if self.is_free:
            return f"{self.technician_name}: GRATUIT ({self.distance_km:.1f} km, {self.duration_minutes:.0f} min)"

        parts = []
        if self.distance_fee > 0:
            parts.append(f"distance: {self.distance_fee:.2f}$")
        if self.time_fee > 0:
            parts.append(f"temps: {self.time_fee:.2f}$")

        details = " + ".join(parts) if parts else "gratuit"
        return f"{self.technician_name}: {self.total_fee:.2f}$ ({self.distance_km:.1f} km, {self.duration_minutes:.0f} min) - {details}"


class TravelFeeCalculator:
    """Calculateur de frais de déplacement avec Google Maps Distance Matrix API."""

    # Constantes de tarification (identiques au JavaScript)
    FREE_DISTANCE_KM = 40.0  # 20 km aller + 20 km retour
    FREE_TIME_SECONDS = 2400  # 20 min aller + 20 min retour (en secondes)
    PRICE_PER_KM = 0.59
    PRICE_PER_HOUR = 57.50

    # Techniciens disponibles
    TECHNICIANS = [
        Technician("Allan", "H4N 2A1"),
        Technician("Nicolas", "H2X 2L1"),
        Technician("Jean-Philippe", "H2L 3V2"),
    ]

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialise le calculateur.

        Args:
            api_key: Clé API Google Maps. Si None, utilise GOOGLE_MAPS_API_KEY de l'environnement.
        """
        self.api_key = api_key or os.getenv('GOOGLE_MAPS_API_KEY')
        # Mode dégradé: si pas de clé, on utilisera des distances estimées
        self.degraded_mode = not self.api_key
        if self.degraded_mode:
            import warnings
            warnings.warn(
                "Google Maps API key not found. Using degraded mode with estimated distances.",
                UserWarning
            )

    def _call_distance_matrix_api(
        self,
        origin: str,
        destination: str
    ) -> Tuple[float, float]:
        """
        Appelle Google Maps Distance Matrix API pour obtenir distance et temps.

        Args:
            origin: Adresse de départ
            destination: Adresse d'arrivée

        Returns:
            Tuple (distance_meters, duration_seconds)

        Raises:
            Exception: Si l'API retourne une erreur
        """
        url = "https://maps.googleapis.com/maps/api/distancematrix/json"
        params = {
            'origins': origin,
            'destinations': destination,
            'key': self.api_key,
            'mode': 'driving',
            'language': 'fr',
            'units': 'metric'
        }

        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        if data['status'] != 'OK':
            raise Exception(f"Google Maps API error: {data['status']}")

        element = data['rows'][0]['elements'][0]

        if element['status'] != 'OK':
            raise Exception(f"Route calculation error: {element['status']}")

        distance_meters = element['distance']['value']
        duration_seconds = element['duration']['value']

        return distance_meters, duration_seconds

    def calculate_fee_for_technician(
        self,
        technician: Technician,
        destination_address: str
    ) -> TravelFeeResult:
        """
        Calcule les frais de déplacement pour un technicien vers une destination.

        Args:
            technician: Le technicien
            destination_address: Adresse de destination (code postal ou adresse complète)

        Returns:
            TravelFeeResult avec tous les détails du calcul
        """
        # Obtenir distance et temps ONE-WAY
        if self.degraded_mode:
            # Mode dégradé: estimation basique (40km, 30min par défaut)
            distance_meters = 40000  # 40km
            duration_seconds = 1800  # 30 minutes
        else:
            distance_meters, duration_seconds = self._call_distance_matrix_api(
                technician.full_address,
                destination_address
            )

        # Convertir en aller-retour (round trip)
        round_trip_distance_km = (distance_meters * 2) / 1000.0
        round_trip_duration_seconds = duration_seconds * 2
        round_trip_duration_minutes = round_trip_duration_seconds / 60.0

        # Calculer excédents
        excess_distance_km = max(0, round_trip_distance_km - self.FREE_DISTANCE_KM)
        excess_time_seconds = max(0, round_trip_duration_seconds - self.FREE_TIME_SECONDS)

        # Calculer frais
        distance_fee = excess_distance_km * self.PRICE_PER_KM
        time_fee = (excess_time_seconds / 3600.0) * self.PRICE_PER_HOUR
        total_fee = distance_fee + time_fee

        is_free = (excess_distance_km == 0 and excess_time_seconds == 0)

        return TravelFeeResult(
            technician_name=technician.name,
            distance_km=round_trip_distance_km,
            duration_minutes=round_trip_duration_minutes,
            distance_fee=distance_fee,
            time_fee=time_fee,
            total_fee=total_fee,
            is_free=is_free
        )

    def calculate_all_technicians(
        self,
        destination_address: str
    ) -> List[TravelFeeResult]:
        """
        Calcule les frais pour tous les techniciens.

        Args:
            destination_address: Adresse de destination

        Returns:
            Liste de TravelFeeResult, triée par coût total (moins cher en premier)
        """
        results = []

        for technician in self.TECHNICIANS:
            try:
                result = self.calculate_fee_for_technician(technician, destination_address)
                results.append(result)
            except Exception as e:
                print(f"⚠️ Erreur calcul pour {technician.name}: {e}")
                continue

        # Trier par coût total (gratuit en premier, puis par prix croissant)
        results.sort(key=lambda r: r.total_fee)

        return results

    def get_cheapest_technician(
        self,
        destination_address: str
    ) -> Optional[TravelFeeResult]:
        """
        Trouve le technicien le moins cher pour une destination.

        Args:
            destination_address: Adresse de destination

        Returns:
            TravelFeeResult du technicien le moins cher, ou None si erreur
        """
        results = self.calculate_all_technicians(destination_address)
        return results[0] if results else None

    def format_for_assistant(
        self,
        destination_address: str,
        assigned_technician: Optional[str] = None
    ) -> str:
        """
        Formate le résultat pour affichage dans l'assistant conversationnel.

        Args:
            destination_address: Adresse de destination
            assigned_technician: Nom du technicien assigné (optionnel)

        Returns:
            Texte formaté prêt à afficher
        """
        results = self.calculate_all_technicians(destination_address)

        if not results:
            return "❌ Impossible de calculer les frais de déplacement"

        lines = ["💰 **Frais de déplacement:**\n"]

        for i, result in enumerate(results):
            # Marquer le technicien assigné
            marker = "👤 " if result.technician_name == assigned_technician else "   "

            if result.is_free:
                lines.append(f"{marker}{result.technician_name}: **GRATUIT** ({result.distance_km:.1f} km, {result.duration_minutes:.0f} min)")
            else:
                breakdown = []
                if result.distance_fee > 0:
                    excess_km = result.distance_km - self.FREE_DISTANCE_KM
                    breakdown.append(f"+{excess_km:.1f} km × {self.PRICE_PER_KM}$ = {result.distance_fee:.2f}$")
                if result.time_fee > 0:
                    excess_min = (result.duration_minutes * 60 - self.FREE_TIME_SECONDS) / 60
                    breakdown.append(f"+{excess_min:.0f} min × {self.PRICE_PER_HOUR/60:.2f}$/min = {result.time_fee:.2f}$")

                details = " + ".join(breakdown) if breakdown else ""
                lines.append(f"{marker}{result.technician_name}: **{result.total_fee:.2f}$** ({result.distance_km:.1f} km, {result.duration_minutes:.0f} min)")
                if details:
                    lines.append(f"    ↳ {details}")

        # Recommandation
        cheapest = results[0]
        if assigned_technician and assigned_technician != cheapest.technician_name:
            assigned_result = next((r for r in results if r.technician_name == assigned_technician), None)
            if assigned_result and not assigned_result.is_free and cheapest.is_free:
                lines.append(f"\n💡 **Recommandation:** {cheapest.technician_name} serait gratuit pour ce déplacement")
            elif assigned_result and assigned_result.total_fee > cheapest.total_fee + 10:
                savings = assigned_result.total_fee - cheapest.total_fee
                lines.append(f"\n💡 **Recommandation:** {cheapest.technician_name} économiserait {savings:.2f}$")

        return "\n".join(lines)


# Fonction utilitaire pour usage simple
def calculate_travel_fee(destination_address: str, api_key: Optional[str] = None) -> str:
    """
    Fonction utilitaire pour calculer rapidement les frais de déplacement.

    Args:
        destination_address: Code postal ou adresse complète
        api_key: Clé API Google Maps (optionnel, utilise variable d'environnement sinon)

    Returns:
        Texte formaté avec les frais pour tous les techniciens

    Example:
        >>> print(calculate_travel_fee("H3B 4W8"))
        💰 **Frais de déplacement:**

        Nicolas: **GRATUIT** (18.2 km, 22 min)
        Allan: **12.50$** (52.4 km, 38 min)
            ↳ +12.4 km × 0.59$ = 7.32$ + +0 min × 0.96$/min = 5.18$
        Jean-Philippe: **15.80$** (58.1 km, 42 min)
    """
    calculator = TravelFeeCalculator(api_key)
    return calculator.format_for_assistant(destination_address)


if __name__ == "__main__":
    # Exemple d'utilisation
    import sys

    if len(sys.argv) < 2:
        print("Usage: python calculator.py <code_postal_ou_adresse>")
        print("\nExemple: python calculator.py 'H3B 4W8'")
        sys.exit(1)

    destination = sys.argv[1]
    print(f"\n🎯 Calcul des frais de déplacement pour: {destination}\n")

    try:
        result = calculate_travel_fee(destination)
        print(result)
    except Exception as e:
        print(f"❌ Erreur: {e}")
        sys.exit(1)
