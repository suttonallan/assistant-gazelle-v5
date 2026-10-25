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

    # ─── Règle client (oct. 2026, décision d'Allan) ───────────────────────────
    # Les frais des clients se mesurent depuis UN point fixe au centre du territoire
    # (station de métro Outremont, entre Allan et Nicolas), en auto selon Google.
    # Gratuit si l'aller fait 20 km ou moins (le temps ne compte pas dans la zone) ;
    # au-delà : km et temps excédentaires (aller-retour au-delà de 40 km / 40 min).
    # Source unique : page de réservation, Ma Journée et calculateur du site l'utilisent.
    POINT_REFERENCE = "Station Outremont, Avenue Van Horne, Outremont, QC"
    NOM_REFERENCE = "PTM (métro Outremont)"
    ZONE_GRATUITE_KM = 20.0  # aller simple

    # Techniciens disponibles (tournées partagées seulement — pas pour les frais client)
    TECHNICIANS = [
        Technician("Allan", "H4N 2A1"),
        Technician("Nicolas", "H2X 2L1"),
        Technician("Jean-Philippe", "H2L 3V2"),
    ]

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialise le calculateur.

        Args:
            api_key: Clé API Google Maps. Si None, charge depuis Supabase ou .env.
        """
        if api_key:
            self.api_key = api_key
        else:
            # Charger depuis Supabase en priorité, puis .env en fallback
            self.api_key = self._load_api_key_from_supabase()

        # Mode dégradé: si pas de clé, on utilisera des distances estimées
        self.degraded_mode = not self.api_key
        if self.degraded_mode:
            import warnings
            warnings.warn(
                "Google Maps API key not found. Using degraded mode with estimated distances.",
                UserWarning
            )

    def _load_api_key_from_supabase(self) -> Optional[str]:
        """Charge la clé Google Maps depuis Supabase system_settings."""
        try:
            from core.supabase_storage import SupabaseStorage
            from supabase import create_client

            storage = SupabaseStorage()
            supabase = create_client(storage.supabase_url, storage.supabase_key)

            result = supabase.table('system_settings').select('value').eq('key', 'google_maps_api_key').execute()

            if result.data and len(result.data) > 0:
                return result.data[0]['value']
            else:
                # Fallback: essayer .env
                return os.getenv('GOOGLE_MAPS_API_KEY')
        except Exception:
            # En cas d'erreur, essayer .env
            return os.getenv('GOOGLE_MAPS_API_KEY')

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

    def _fee_from_totals(self, distance_km: float, duration_seconds: float):
        """Applique la zone gratuite (une seule fois) et les tarifs à un trajet total."""
        excess_km = max(0, distance_km - self.FREE_DISTANCE_KM)
        excess_s = max(0, duration_seconds - self.FREE_TIME_SECONDS)
        distance_fee = excess_km * self.PRICE_PER_KM
        time_fee = (excess_s / 3600.0) * self.PRICE_PER_HOUR
        return distance_fee, time_fee, distance_fee + time_fee

    def _distance_matrix(self, points: List[str]):
        """Matrice complète distances (m) / durées (s) entre tous les points, en un appel."""
        n = len(points)
        if self.degraded_mode:
            return ([[0 if i == j else 20000 for j in range(n)] for i in range(n)],
                    [[0 if i == j else 1200 for j in range(n)] for i in range(n)])
        url = "https://maps.googleapis.com/maps/api/distancematrix/json"
        params = {
            'origins': '|'.join(points), 'destinations': '|'.join(points),
            'key': self.api_key, 'mode': 'driving', 'language': 'fr', 'units': 'metric',
        }
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        if data['status'] != 'OK':
            raise Exception(f"Google Maps API error: {data['status']}")
        dist = [[0] * n for _ in range(n)]
        dur = [[0] * n for _ in range(n)]
        for i, row in enumerate(data['rows']):
            for j, el in enumerate(row['elements']):
                if i == j:
                    continue
                if el['status'] != 'OK':
                    raise Exception(f"Adresse introuvable : {points[j] if i == 0 else points[i]}")
                dist[i][j] = el['distance']['value']
                dur[i][j] = el['duration']['value']
        return dist, dur

    def calculate_shared_route(
        self,
        technician_name: str,
        destinations: List[Dict[str, str]],
    ) -> Dict:
        """
        Frais d'une tournée avec plusieurs clients, partagés entre eux.

        L'ordre des visites est OPTIMISÉ (le moins cher possible) :
        domicile du technicien → clients dans le meilleur ordre → retour.
        La zone gratuite (40 km / 40 min) s'applique UNE fois à la tournée.
        Les frais totaux sont répartis au prorata de ce que chaque client
        paierait s'il était seul : chacun paie toujours moins que seul.
        """
        from itertools import permutations

        tech = next((t for t in self.TECHNICIANS if t.name == technician_name), None)
        if tech is None:
            raise ValueError(f"Technicien inconnu : {technician_name}")
        if len(destinations) < 2:
            raise ValueError("Il faut au moins deux clients pour partager les frais.")
        if len(destinations) > 9:
            raise ValueError("Maximum 9 clients par tournée.")

        points = [tech.full_address] + [d["address"] for d in destinations]
        dist, dur = self._distance_matrix(points)

        def route_totals(order):
            path = [0] + [i + 1 for i in order] + [0]
            m = sum(dist[a][b] for a, b in zip(path[:-1], path[1:]))
            sec = sum(dur[a][b] for a, b in zip(path[:-1], path[1:]))
            return m, sec

        def cost(order):
            m, sec = route_totals(order)
            return (round(self._fee_from_totals(m / 1000.0, sec)[2], 2), m)

        n = len(destinations)
        entered = tuple(range(n))
        best = min(permutations(range(n)), key=cost)  # ≤ 9! = 362 880 essais, instantané

        def summarize(order):
            m, sec = route_totals(order)
            d_fee, t_fee, fee = self._fee_from_totals(m / 1000.0, sec)
            path = [0] + [i + 1 for i in order] + [0]
            legs = [{"km": round(dist[a][b] / 1000.0, 1), "minutes": round(dur[a][b] / 60.0)}
                    for a, b in zip(path[:-1], path[1:])]
            return m / 1000.0, sec, d_fee, t_fee, fee, legs

        entered_fee = summarize(entered)[4]
        total_km, total_s, d_fee, t_fee, route_fee, legs = summarize(best)
        ordered = [destinations[i] for i in best]

        # Frais « seul » de chaque client = aller-retour domicile ↔ client
        solos = []
        for i in best:
            m = dist[0][i + 1] + dist[i + 1][0]
            sec = dur[0][i + 1] + dur[i + 1][0]
            solos.append(self._fee_from_totals(m / 1000.0, sec)[2])
        destinations = ordered
        sum_solo = sum(solos)
        to_share = min(route_fee, sum_solo)

        clients = []
        for d, solo in zip(destinations, solos):
            share = (to_share * solo / sum_solo) if sum_solo > 0 else 0.0
            clients.append({
                "label": d.get("label") or d["address"],
                "address": d["address"],
                "solo_fee": round(solo, 2),
                "share": round(share, 2),
            })
        # Ajuster l'arrondi pour que la somme des parts = total exact
        diff = round(to_share, 2) - sum(c["share"] for c in clients)
        if clients and abs(diff) >= 0.01:
            i = max(range(len(clients)), key=lambda k: clients[k]["share"])
            clients[i]["share"] = round(clients[i]["share"] + diff, 2)

        return {
            "technician_name": tech.name,
            "total_km": round(total_km, 1),
            "total_minutes": round(total_s / 60.0),
            "legs": legs,
            "distance_fee": round(d_fee, 2),
            "time_fee": round(t_fee, 2),
            "total_fee": round(to_share, 2),
            "optimized_order": [d.get("label") or d["address"] for d in ordered],
            "order_changed": list(best) != list(entered),
            "entered_order_fee": round(entered_fee, 2),
            "sum_solo_fees": round(sum_solo, 2),
            "savings": round(sum_solo - to_share, 2),
            "clients": clients,
            "degraded_mode": self.degraded_mode,
        }

    def calculer_frais_client(self, destination_address: str) -> TravelFeeResult:
        """Frais de déplacement d'un client selon la règle officielle (point de référence unique)."""
        if self.degraded_mode:
            raise Exception("Clé Google Maps absente : calcul impossible")
        distance_m, duree_s = self._call_distance_matrix_api(self.POINT_REFERENCE, destination_address)
        km_ar = distance_m * 2 / 1000.0
        s_ar = duree_s * 2
        if distance_m / 1000.0 <= self.ZONE_GRATUITE_KM:
            frais_km = frais_temps = 0.0
        else:
            frais_km, frais_temps, _ = self._fee_from_totals(km_ar, s_ar)
        total = frais_km + frais_temps
        return TravelFeeResult(
            technician_name=self.NOM_REFERENCE, distance_km=km_ar, duration_minutes=s_ar / 60.0,
            distance_fee=frais_km, time_fee=frais_temps, total_fee=total, is_free=total == 0,
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
        # Depuis oct. 2026 : une seule règle client, mesurée depuis le point de référence
        # (le même montant quel que soit le technicien). Conservé sous ce nom pour les appelants.
        try:
            return [self.calculer_frais_client(destination_address)]
        except Exception as e:
            print(f"⚠️ Erreur calcul frais client : {e}")
            return []

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
