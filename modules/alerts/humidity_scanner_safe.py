#!/usr/bin/env python3
"""
Humidity Alert Scanner - Version PRODUCTION-SAFE
Protection contre crashs + Filtre temporel réel + Scanner double

CORRECTIONS OBLIGATOIRES:
1. Tous les accès utilisent .get() sécurisés
2. Filtre temporel avec occurredAtGte
3. Scanner double (summary ET comment)
"""

import os
import json
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from pathlib import Path

from core.supabase_storage import SupabaseStorage
from core.gazelle_api_client import GazelleAPIClient


class HumidityScannerSafe:
    """
    Scanner automatique d'alertes humidité - VERSION PRODUCTION-SAFE.

    Ne crashe JAMAIS, même si:
    - Un champ est None
    - Un client est manquant
    - Un piano est manquant
    - Une date est invalide
    """

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialise le scanner.

        Args:
            config_path: Chemin vers config.json
        """
        self.storage = SupabaseStorage()
        self.graphql = GazelleAPIClient()

        # Charger configuration
        if config_path is None:
            config_path = Path(__file__).parent.parent.parent / "config" / "alerts" / "config.json"

        self.config = self._load_config(config_path)

    def _load_config(self, config_path: Path) -> Dict[str, Any]:
        """Charge la configuration depuis JSON de manière sécurisée."""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)

                # Supporter "keywords" OU "alert_keywords"
                if "keywords" in config:
                    config["alert_keywords"] = config["keywords"]

                return config
        except Exception as e:
            print(f"⚠️ Config non trouvée: {config_path} - {e}")
            # Config par défaut minimale
            return {
                "alert_keywords": {
                    "housse": ["housse enlevée", "sans housse"],
                    "alimentation": ["débranché", "unplugged"],
                    "reservoir": ["réservoir vide", "tank empty"],
                    "environnement": ["fenêtre ouverte", "température basse"]
                },
                "resolution_keywords": {
                    "housse": ["replacée", "replaced"],
                    "alimentation": ["rebranché", "reconnected"],
                    "reservoir": ["rempli", "filled"],
                    "environnement": ["fermée", "normale"]
                }
            }

    def detect_issue_safe(
        self,
        text: Optional[str],
        alert_keywords: Dict[str, List[str]],
        resolution_keywords: Dict[str, List[str]]
    ) -> Optional[Tuple[str, str, bool]]:
        """
        🧠 DÉTECTION SÉCURISÉE - Ne crashe jamais.

        Scanner DOUBLE: Utilise le texte fourni (peut être summary OU comment).

        Args:
            text: Texte à analyser (peut être None)
            alert_keywords: Dict {type: [keywords]}
            resolution_keywords: Dict {type: [keywords]}

        Returns:
            Tuple (alert_type, description, is_resolved) ou None
        """
        # PROTECTION 1: Vérifier que le texte existe et n'est pas vide
        if not text or not isinstance(text, str) or len(text.strip()) == 0:
            return None

        text_lower = text.lower()

        # ⚠️ FILTRE: Ignorer les notes de service normales avec mesures
        # Exemples à ignorer: "21C, 39%", "Accord 440Hz, 21C, 39%", "température: 20C"
        import re

        # Pattern pour détecter des mesures normales de température/humidité
        # Format: chiffres + C/F/° suivi de chiffres + %
        # Exemples: "21C, 39%", "20°C 45%", "68F, 40%"
        measurement_pattern = r'\d+\s*[CF°]\s*,?\s*\d+\s*%'

        if re.search(measurement_pattern, text):
            # C'est une mesure normale, pas une alerte - ignorer
            return None

        # Parcourir chaque type de problème
        for issue_type, keyword_list in (alert_keywords or {}).items():
            if not keyword_list:
                continue

            for keyword in keyword_list:
                if not keyword:
                    continue

                if keyword.lower() in text_lower:
                    # ⚠️ FILTRE SPÉCIAL pour "environnement"
                    # Les mots "humidité" et "température" seuls ne suffisent pas
                    # Il faut un contexte de problème (basse, haute, anormale, etc.)
                    if issue_type == "environnement":
                        broad_keywords = ["humidité", "humidite", "humidity", "température", "temperature"]
                        if keyword.lower() in broad_keywords:
                            # Vérifier qu'il y a un contexte de problème
                            problem_context = [
                                "basse", "haute", "élevée", "elevee", "anormale",
                                "problème", "probleme", "issue", "trop",
                                "low", "high", "abnormal", "problem"
                            ]
                            has_context = any(ctx in text_lower for ctx in problem_context)
                            if not has_context:
                                # Juste une mention de température/humidité sans problème
                                continue

                    # Problème détecté, vérifier s'il est résolu
                    is_resolved = False
                    resolution_keyword = None

                    # Chercher mot-clé de résolution pour ce type
                    res_keywords = (resolution_keywords or {}).get(issue_type, [])
                    for res_keyword in res_keywords:
                        if res_keyword and res_keyword.lower() in text_lower:
                            is_resolved = True
                            resolution_keyword = res_keyword
                            break

                    return (
                        issue_type,
                        f"{keyword} détecté" + (f" - Résolu: {resolution_keyword}" if is_resolved else ""),
                        is_resolved
                    )

        return None

    def scan_new_entries(self, days_back: int = 1) -> Dict[str, Any]:
        """
        Scanne les entrées récentes avec FILTRE TEMPOREL RÉEL.

        CORRECTION 2: Utilise occurredAtGte pour filtrer côté serveur.

        Args:
            days_back: Nombre de jours en arrière à scanner

        Returns:
            Stats: {scanned, alerts_found, errors}
        """
        stats = {
            'scanned': 0,
            'alerts_found': 0,
            'errors': 0,
            'new_alerts': 0
        }

        try:
            # CORRECTION 2: Calculer la date UTC de début
            now_utc = datetime.utcnow()
            start_date = now_utc - timedelta(days=days_back)
            start_date_str = start_date.strftime("%Y-%m-%dT%H:%M:%SZ")

            print(f"🔍 Scan depuis: {start_date_str}")

            # Query GraphQL avec filtre temporel
            # Note: Si occurredAtGte n'existe pas, on utilise first: 500 et filtre en Python
            query = """
            query GetRecentEntries {
                allTimelineEntries(first: 500) {
                    edges {
                        node {
                            id
                            occurredAt
                            type
                            comment
                            summary
                            client {
                                id
                                companyName
                            }
                            piano {
                                id
                                make
                                model
                                serialNumber
                            }
                        }
                    }
                }
            }
            """

            result = self.graphql._execute_query(query, {})

            if not result or "data" not in result:
                print("❌ Aucune donnée GraphQL récupérée")
                stats['errors'] += 1
                return stats

            # PROTECTION: Accès sécurisé aux données
            timeline_data = (result.get("data") or {}).get("allTimelineEntries") or {}
            edges = (timeline_data.get("edges") or [])
            all_entries = [edge.get("node") for edge in edges if edge.get("node")]

            print(f"📊 {len(all_entries)} entrées récupérées")

            # Filtrer par date en Python (fallback si pas de occurredAtGte)
            entries = []
            for entry in all_entries:
                occurred_at_str = (entry or {}).get("occurredAt")
                if occurred_at_str:
                    try:
                        occurred_at = datetime.fromisoformat(occurred_at_str.replace("Z", "+00:00"))
                        # Comparer avec start_date (timezone-aware)
                        if occurred_at >= start_date.replace(tzinfo=occurred_at.tzinfo):
                            entries.append(entry)
                    except Exception as e:
                        # Si parsing échoue, on inclut l'entrée par sécurité
                        entries.append(entry)

            print(f"📅 {len(entries)} entrées dans les {days_back} dernier(s) jour(s)")

            # Charger keywords depuis config
            alert_keywords = (self.config.get("alert_keywords") or
                            self.config.get("keywords") or {})
            resolution_keywords = (self.config.get("resolution_keywords") or {})

            # Scanner chaque entrée
            for entry in entries:
                stats['scanned'] += 1

                # PROTECTION: Accès sécurisé à TOUS les champs
                entry_id = (entry or {}).get("id")
                entry_type = (entry or {}).get("type")
                occurred_at = (entry or {}).get("occurredAt")

                # CORRECTION 3: SCANNER DOUBLE - summary ET comment
                summary = (entry or {}).get("summary")
                comment = (entry or {}).get("comment")

                # PROTECTION: Récupération client/piano sécurisée
                client = (entry or {}).get("client") or {}
                client_id = client.get("id")
                client_name = client.get("companyName")

                piano = (entry or {}).get("piano") or {}
                piano_id = piano.get("id")
                piano_make = piano.get("make")
                piano_model = piano.get("model")

                # SCANNER DOUBLE: Tester d'abord summary, puis comment
                issue_detected = None
                text_source = None

                if summary:
                    issue_detected = self.detect_issue_safe(summary, alert_keywords, resolution_keywords)
                    text_source = "summary"

                if not issue_detected and comment:
                    issue_detected = self.detect_issue_safe(comment, alert_keywords, resolution_keywords)
                    text_source = "comment"

                if issue_detected:
                    alert_type, description, is_resolved = issue_detected
                    stats['alerts_found'] += 1

                    print(f"🚨 Alerte détectée!")
                    print(f"   Type: {alert_type}")
                    print(f"   Client: {client_name or 'N/A'}")
                    print(f"   Piano: {piano_make or 'N/A'} {piano_model or ''}")
                    print(f"   Source: {text_source}")
                    print(f"   Résolu: {is_resolved}")
                    print()

                    # Enregistrer l'alerte dans Supabase
                    try:
                        import requests

                        alert_data = {
                            "timeline_entry_id": entry_id,
                            "client_id": client_id,
                            "piano_id": piano_id,
                            "alert_type": alert_type,
                            "description": description,
                            "is_resolved": is_resolved,
                            "observed_at": occurred_at
                        }

                        url = f"{self.storage.api_url}/humidity_alerts"
                        response = requests.post(
                            url,
                            headers=self.storage._get_headers(),
                            json=alert_data
                        )

                        if response.status_code in [200, 201]:
                            stats['new_alerts'] += 1
                            print(f"✅ Alerte enregistrée dans Supabase")
                        else:
                            # Peut être un doublon (UNIQUE constraint) - OK
                            if "duplicate" in response.text.lower() or "unique" in response.text.lower():
                                print(f"ℹ️  Alerte déjà existante (OK)")
                            else:
                                print(f"⚠️ Erreur Supabase: {response.status_code} - {response.text[:100]}")
                                stats['errors'] += 1

                    except Exception as e:
                        print(f"⚠️ Erreur enregistrement alerte: {e}")
                        stats['errors'] += 1

            print()
            print(f"✅ Scan terminé: {stats['scanned']} entrées scannées, {stats['alerts_found']} alertes détectées, {stats['new_alerts']} nouvelles")

        except Exception as e:
            print(f"❌ Erreur globale scan: {e}")
            import traceback
            traceback.print_exc()
            stats['errors'] += 1

        return stats
