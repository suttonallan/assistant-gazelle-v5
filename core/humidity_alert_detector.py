#!/usr/bin/env python3
"""
Détecteur d'alertes d'humidité depuis les notes de techniciens.
Cherche des mots-clés indiquant des problèmes d'humidité dans les rapports.
"""

import re
from typing import Optional, Dict, Any
from datetime import datetime


# Mots-clés indicateurs de problèmes d'humidité
HUMIDITY_KEYWORDS = {
    "high_humidity": [
        "humidité.*haute",
        "humidité.*élevée",
        "très humide",
        "trop.*humide",
        "humidité.*[78][0-9]%",  # 70-89%
        "humidité.*9[0-9]%",      # 90-99%
    ],
    "low_humidity": [
        "humidité.*basse",
        "humidité.*faible",
        "très sec",
        "trop.*sec",
        "humidité.*[12][0-9]%",   # 10-29%
        "humidité.*3[0-5]%",      # 30-35%
    ],
    "dampp_chaser": [
        "dampp.*chaser.*débranché",
        "dampp.*chaser.*off",
        "dampp.*chaser.*éteint",
        "dampp.*chaser.*ne.*fonctionne",
    ],
    "cover_removed": [
        "housse.*retirée",
        "housse.*enlevée",
        "sans.*housse",
        "pas.*de.*housse",
    ]
}


def detect_humidity_issue(notes: str) -> Optional[Dict[str, Any]]:
    """
    Détecte si les notes du technicien mentionnent un problème d'humidité.

    Args:
        notes: Notes du technicien (service_history_notes)

    Returns:
        Dict avec type d'alerte et description si problème détecté, None sinon
        {
            "alert_type": "high_humidity" | "low_humidity" | "dampp_chaser" | "cover_removed",
            "matched_pattern": "humidité trop haute à 78%",
            "severity": "warning" | "critical"
        }
    """
    if not notes:
        return None

    notes_lower = notes.lower()

    # Vérifier chaque catégorie de mots-clés
    for alert_type, patterns in HUMIDITY_KEYWORDS.items():
        for pattern in patterns:
            match = re.search(pattern, notes_lower, re.IGNORECASE)
            if match:
                # Déterminer la sévérité
                severity = "warning"
                if alert_type in ["dampp_chaser", "cover_removed"]:
                    severity = "critical"  # Problèmes structurels plus graves
                elif "9[0-9]%" in pattern or "[12][0-9]%" in pattern:
                    severity = "critical"  # Humidité extrême

                return {
                    "alert_type": alert_type,
                    "matched_pattern": match.group(0),
                    "severity": severity,
                    "detected_at": datetime.utcnow().isoformat()
                }

    return None


def create_humidity_alert(
    piano_id: str,
    client_name: str,
    notes: str,
    piano_info: Optional[Dict[str, str]] = None,
    detection_result: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Crée une alerte d'humidité formatée pour insertion dans Supabase.

    Args:
        piano_id: ID Gazelle du piano
        client_name: Nom du client (institution)
        notes: Notes complètes du technicien
        piano_info: Info du piano (make, model, location, etc.)
        detection_result: Résultat de detect_humidity_issue()

    Returns:
        Dict formaté pour insertion dans humidity_alerts_active
    """
    if not detection_result:
        detection_result = detect_humidity_issue(notes)

    if not detection_result:
        return None

    alert_type = detection_result['alert_type']

    # Mapper les types vers des descriptions lisibles
    alert_descriptions = {
        "high_humidity": "Humidité élevée détectée",
        "low_humidity": "Humidité basse détectée",
        "dampp_chaser": "Dampp-Chaser débranché ou défectueux",
        "cover_removed": "Housse de piano retirée"
    }

    alert = {
        "piano_id": piano_id,
        "client_name": client_name,
        "alert_type": alert_type,
        "description": alert_descriptions.get(alert_type, "Problème d'humidité détecté"),
        "technician_notes": notes,  # Notes complètes du technicien
        "severity": detection_result['severity'],
        "is_resolved": False,
        "observed_at": detection_result['detected_at'],
        "detected_pattern": detection_result['matched_pattern']
    }

    # Ajouter les infos du piano si disponibles
    if piano_info:
        alert["piano_make"] = piano_info.get("make")
        alert["piano_model"] = piano_info.get("model")
        alert["piano_location"] = piano_info.get("location")
        alert["serial_number"] = piano_info.get("serial")

    return alert
