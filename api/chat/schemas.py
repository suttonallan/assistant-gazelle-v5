"""
Schémas de données pour le Chat Intelligent.

Bridge V5 → V6: Ces schémas seront utilisables avec les deux architectures.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


# ============================================================
# NIVEAU 1: APERÇU (Cards compactes)
# ============================================================

class AppointmentOverview(BaseModel):
    """
    Carte d'aperçu d'un rendez-vous - Orientation logistique terrain.

    Optimisé pour mobile, affichage compact.
    """
    # Identifiants
    appointment_id: str = Field(..., description="ID du rendez-vous")
    client_id: Optional[str] = Field(None, description="ID du client")
    piano_id: Optional[str] = Field(None, description="ID du piano principal")

    # Timing (CRITIQUE pour la logistique)
    time_slot: str = Field(..., description="Ex: '09:00 - 11:00'", example="09:00 - 11:00")
    date: str = Field(..., description="Date ISO", example="2025-12-29")

    # Localisation (PRIORITÉ #1 pour le terrain)
    client_name: str = Field(..., description="Nom du contact (personne physique)")
    billing_client: Optional[str] = Field(None, description="Institution qui paie (si différent du contact)")
    neighborhood: str = Field(..., description="Quartier/Ville", example="Plateau Mont-Royal")
    address_short: str = Field(..., description="Adresse courte", example="4520 rue St-Denis")

    # Piano (Info rapide)
    piano_brand: Optional[str] = Field(None, description="Marque", example="Yamaha")
    piano_model: Optional[str] = Field(None, description="Modèle", example="U1")
    piano_type: Optional[str] = Field(None, description="Type", example="Droit")
    has_dampp_chaser: bool = Field(default=False, description="Piano Life Saver (système humidité)")

    # Contexte historique (QUICK REFERENCE)
    last_visit_date: Optional[str] = Field(None, description="Dernière visite", example="2024-11-15")
    days_since_last_visit: Optional[int] = Field(None, description="Jours depuis dernière visite")

    # Action items (🎯 Ce qu'il faut faire/apporter)
    action_items: List[str] = Field(
        default_factory=list,
        description="Liste à apporter/faire",
        example=["Apporter cordes #3", "Vérifier humidité", "Accord 442Hz"]
    )

    # Flags visuels
    is_new_client: bool = Field(default=False, description="Nouveau client (badge)")
    has_alerts: bool = Field(default=False, description="Alertes actives (⚠️)")
    priority: str = Field(default="normal", description="normal|high|urgent")


class DayOverview(BaseModel):
    """
    Vue d'ensemble de la journée complète.
    """
    date: str = Field(..., description="Date de la journée", example="2025-12-29")
    technician_name: str = Field(..., description="Nom du technicien")

    # Statistiques rapides
    total_appointments: int = Field(..., description="Nombre total de RDV")
    total_pianos: int = Field(..., description="Nombre de pianos")
    estimated_duration_hours: float = Field(..., description="Durée estimée totale (heures)")

    # Zones géographiques (pour optimisation trajet)
    neighborhoods: List[str] = Field(..., description="Liste des quartiers")

    # Les rendez-vous (triés par heure)
    appointments: List[AppointmentOverview] = Field(..., description="Rendez-vous du jour")


# ============================================================
# NIVEAU 2: DEEP DIVE (Détails confort)
# ============================================================

class ComfortInfo(BaseModel):
    """
    Informations "SUR PLACE" pour le technicien.

    IMPORTANT: Ces infos concernent le CONTACT (personne physique rencontrée),
    pas nécessairement le CLIENT (entité qui paie).

    Tout ce qui rend la visite plus agréable et professionnelle.
    """
    # Contact (personne physique)
    contact_name: Optional[str] = Field(None, description="Nom du contact sur place")
    contact_phone: Optional[str] = Field(None, description="Téléphone contact direct")
    contact_email: Optional[str] = Field(None, description="Email contact")

    # Accès (liés à l'ADRESSE physique, PAS au client)
    access_code: Optional[str] = Field(None, description="Code porte/interphone")
    access_instructions: Optional[str] = Field(None, description="Instructions d'accès détaillées")
    parking_info: Optional[str] = Field(None, description="Où se garer")
    floor_number: Optional[str] = Field(None, description="Étage")

    # Contexte humain (lié au CONTACT)
    dog_name: Optional[str] = Field(None, description="Nom du chien 🦴")
    dog_breed: Optional[str] = Field(None, description="Race du chien")
    cat_name: Optional[str] = Field(None, description="Nom du chat 🐱")
    special_notes: Optional[str] = Field(None, description="Notes spéciales sur place")

    # Préférences techniques
    preferred_tuning_hz: Optional[int] = Field(None, description="Préférence accordage", example=442)
    climate_sensitive: bool = Field(default=False, description="Piano sensible climat")
    
    # Préférences client (Notes Client)
    preferred_language: Optional[str] = Field(None, description="Langue préférée (Français/Anglais/Bilingue)")
    temperament: Optional[str] = Field(None, description="Tempérament du client (Sympathique/Exigeant/Réservé)")


class BillingInfo(BaseModel):
    """
    Informations de FACTURATION.

    IMPORTANT: Afficher SEULEMENT si le client est différent du contact.
    Exemples: École, Université, Entreprise.
    """
    client_name: str = Field(..., description="Nom du client facturé (entreprise/institution)")
    client_id: Optional[str] = Field(None, description="ID client")

    # Infos financières
    balance_due: Optional[float] = Field(None, description="Solde impayé")
    last_payment_date: Optional[str] = Field(None, description="Date dernier paiement")
    payment_terms: Optional[str] = Field(None, description="Conditions de paiement")

    # Contact facturation (si différent du contact sur place)
    billing_contact_name: Optional[str] = Field(None, description="Contact pour facturation")
    billing_phone: Optional[str] = Field(None, description="Téléphone facturation")
    billing_email: Optional[str] = Field(None, description="Email facturation")


class TimelineEntry(BaseModel):
    """
    Entrée de timeline (historique).
    """
    date: str = Field(..., description="Date de l'entrée")
    type: str = Field(..., description="Type: service|measurement|note")
    technician: Optional[str] = Field(None, description="Technicien")
    summary: str = Field(..., description="Résumé court")
    details: Optional[str] = Field(None, description="Détails complets")

    # Mesures (si applicable)
    temperature: Optional[float] = Field(None, description="Température °C")
    humidity: Optional[float] = Field(None, description="Humidité %")


class AppointmentDetail(BaseModel):
    """
    Vue détaillée d'un rendez-vous (Drawer/Modal).

    STRUCTURE EN 3 SECTIONS:
    1. SUR PLACE (comfort) - Infos du contact physique
    2. FACTURATION (billing) - Infos du client payeur (si différent)
    3. HISTORIQUE (timeline) - Historique des interventions
    """
    # Overview (niveau 1)
    overview: AppointmentOverview = Field(..., description="Infos de base")

    # Section 1: SUR PLACE (niveau 2)
    comfort: ComfortInfo = Field(..., description="Infos contact sur place")

    # Section 2: FACTURATION (niveau 2 - optionnel)
    billing: Optional[BillingInfo] = Field(
        None,
        description="Infos facturation (NULL si contact == client)"
    )

    # Section 3: HISTORIQUE (niveau 2)
    timeline_summary: str = Field(
        ...,
        description="Résumé textuel de l'historique",
        example="Dernière visite le 15 nov 2024 par Nicolas. Accord 442Hz, humidité 45%. "
                "Piano en bon état, client satisfait. Prochaine visite suggérée: avril 2025."
    )
    timeline_entries: List[TimelineEntry] = Field(
        default_factory=list,
        description="Entrées timeline complètes (limitées aux 10 dernières)"
    )

    # Section 4: RÉSUMÉS INTELLIGENTS IA (nouveauté v6)
    client_smart_summary: Optional[str] = Field(
        None,
        description="Résumé intelligent du client généré par IA",
        example="Client depuis 2018 (6 ans), fait accorder son piano chaque année en septembre. "
                "⚠️ Présence de chien nerveux. Préfère être contacté par email."
    )
    piano_smart_summary: Optional[str] = Field(
        None,
        description="Résumé intelligent du piano généré par IA",
        example="Steinway D de 1968 (56 ans), accordé 3x/an, équipé Life Saver System. "
                "Climat très stable. Dernière réparation majeure: changement cordes (2023)."
    )

    # Photos (si disponibles)
    photos: List[str] = Field(
        default_factory=list,
        description="URLs des photos du piano"
    )


# ============================================================
# REQUÊTE & RÉPONSE API
# ============================================================

class ChatRequest(BaseModel):
    """
    Requête naturelle du chat.
    """
    query: str = Field(..., description="Requête naturelle", example="Ma journée de demain")
    technician_id: Optional[str] = Field(None, description="Nom du technicien", example="Nicolas")
    user_role: Optional[str] = Field(None, description="Rôle utilisateur (admin|assistant|technicien)", example="technicien")
    date: Optional[str] = Field(None, description="Date spécifique (override)")


class ChatResponse(BaseModel):
    """
    Réponse structurée du chat.
    """
    # Interprétation de la requête
    interpreted_query: str = Field(..., description="Comment on a compris la requête")
    query_type: str = Field(..., description="Type: day_overview|appointment_detail|search")

    # Données
    day_overview: Optional[DayOverview] = Field(None, description="Vue journée (si applicable)")
    appointment_detail: Optional[AppointmentDetail] = Field(None, description="Détail RDV (si applicable)")
    text_response: Optional[str] = Field(None, description="Réponse textuelle (questions de suivi)")
    knowledge_results: Optional[List[Dict[str, Any]]] = Field(None, description="Résultats du Cerveau PTM")

    # Métadata
    data_source: str = Field(default="v5", description="v5|v6 (pour debugging)")
    generated_at: datetime = Field(default_factory=datetime.now, description="Timestamp génération")


# ============================================================
# MAPPING V5 → Standard (Bridge vers V6)
# ============================================================

class V5RawAppointment(BaseModel):
    """
    Schéma brut V5 (ce qui vient de Supabase gazelle_appointments).

    Utilisé comme input pour la transformation.
    """
    external_id: str
    appointment_date: str
    appointment_time: Optional[str]
    client_id: Optional[str]
    piano_id: Optional[str]
    notes: Optional[str]
    technicien: Optional[str]

    # Données jointes
    client: Optional[Dict[str, Any]] = None
    piano: Optional[Dict[str, Any]] = None
    timeline_entries: List[Dict[str, Any]] = Field(default_factory=list)


class V6ReconciledAppointment(BaseModel):
    """
    Schéma V6 futur (après réconciliation).

    PLACEHOLDER - sera implémenté avec le Reconciler V6.
    """
    # TODO V6: Define reconciled schema
    pass
