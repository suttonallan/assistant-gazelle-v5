#!/usr/bin/env python3
"""
Humidity Alert Scanner - Détection automatique d'alertes humidité.

Porté depuis V4 (PC Windows) vers V5 (Mac).
Source: c:\\Allan Python projets\\humidity_alerts\\humidity_alert_system.py

Architecture:
1. Pattern Matching (lignes 139-170 du fichier source)
2. OpenAI Fallback (lignes 172-236 du fichier source)
3. Slack Notifications
4. Supabase Storage
"""

import os
import json
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from pathlib import Path

from core.supabase_storage import SupabaseStorage
from core.slack_notifier import SlackNotifier


class HumidityScanner:
    """
    Scanner automatique d'alertes humidité dans les timeline entries.

    Workflow:
    1. Charger config (mots-clés)
    2. Scanner timeline entries non traitées
    3. Détecter problèmes (pattern matching + IA)
    4. Enregistrer alertes Supabase
    5. Envoyer notifications Slack
    """

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialise le scanner.

        Args:
            config_path: Chemin vers config.json (défaut: config/alerts/config.json)
        """
        self.storage = SupabaseStorage()

        # Charger configuration
        if config_path is None:
            config_path = Path(__file__).parent.parent.parent / "config" / "alerts" / "config.json"

        self.config = self._load_config(config_path)

        # Webhooks Slack (Louise et Nicolas)
        self.slack_webhooks = {
            'louise': os.getenv('SLACK_WEBHOOK_LOUISE', 'https://hooks.slack.com/services/YOUR/WEBHOOK/URL_HERE'),
            'nicolas': os.getenv('SLACK_WEBHOOK_NICOLAS', 'https://hooks.slack.com/services/YOUR/WEBHOOK/URL_HERE')
        }

    def _load_config(self, config_path: Path) -> Dict[str, Any]:
        """Charge la configuration depuis JSON."""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"⚠️ Config non trouvée: {config_path}")
            # Config par défaut minimale
            return {
                "alert_keywords": {
                    "housse": ["housse enlevée", "sans housse", "cover removed"],
                    "alimentation": ["pls débranché", "unplugged", "déconnecté"]
                },
                "resolution_keywords": {
                    "housse": ["replacée", "replaced"],
                    "alimentation": ["rebranché", "reconnected"]
                }
            }

    def detect_issue(
        self,
        description: str,
        alert_keywords: Dict[str, List[str]],
        resolution_keywords: Dict[str, List[str]]
    ) -> Optional[Tuple[str, str, bool]]:
        """
        🧠 CERVEAU PRINCIPAL - Pattern Matching

        Détecte problèmes humidité par mots-clés.

        Adapté depuis: humidity_alert_system.py (PC Windows)

        Args:
            description: Texte de la timeline entry
            alert_keywords: Dict {type: [keywords]}
            resolution_keywords: Dict {type: [keywords]}

        Returns:
            Tuple (alert_type, description, is_resolved) ou None
        """
        if not description or (hasattr(description, '__len__') and len(str(description).strip()) == 0):
            return None

        text_lower = str(description).lower()

        # Parcourir chaque type de problème
        for issue_type, keyword_list in alert_keywords.items():
            for keyword in keyword_list:
                if keyword.lower() in text_lower:
                    # Problème détecté, vérifier s'il est résolu
                    is_resolved = False
                    resolution_keyword = None

                    # Chercher mot-clé de résolution pour ce type
                    if issue_type in resolution_keywords:
                        for res_keyword in resolution_keywords[issue_type]:
                            if res_keyword.lower() in text_lower:
                                is_resolved = True
                                resolution_keyword = res_keyword
                                break

                    return (
                        issue_type,
                        f"{keyword} détecté" + (f" - Résolu: {resolution_keyword}" if is_resolved else ""),
                        is_resolved
                    )

        return None

    def analyze_with_ai(
        self,
        description: str,
        alert_keywords: Dict[str, List[str]],
        resolution_keywords: Dict[str, List[str]]
    ) -> Optional[Tuple[str, str, bool, float]]:
        """
        🤖 FALLBACK IA - OpenAI GPT-4o-mini

        Analyse texte avec IA si pattern matching échoue.

        Adapté depuis: humidity_alert_system.py (PC Windows)

        Args:
            description: Texte de la timeline entry
            alert_keywords: Dict {type: [keywords]}
            resolution_keywords: Dict {type: [keywords]}

        Returns:
            Tuple (alert_type, description, is_resolved, confidence) ou None
            Nécessite: OPENAI_API_KEY dans .env
        """
        if not description or (hasattr(description, '__len__') and len(str(description).strip()) == 0):
            return None

        # Vérifier si OpenAI est configuré
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            return None

        try:
            from openai import OpenAI
            client = OpenAI(api_key=api_key)

            # Construire le prompt
            prompt = f"""Analyse cette note de service d'un technicien de piano.

Détermine s'il y a un problème d'entretien lié à l'humidité ET s'il a été résolu.

Problèmes recherchés:
- housse: housse enlevée, retirée, manquante, cover removed, etc.
- alimentation: PLS débranché, déconnecté, prise débranchée, unplugged, etc.
- reservoir: réservoir vide, tank empty, réservoir manquant, missing reservoir, etc.

Résolutions possibles:
- housse: replacée, remise, repositionnée, installée, replaced, etc.
- alimentation: rebranché, reconnecté, plugged back, reconnected, etc.
- reservoir: rempli, refilled, tank filled, réservoir remis, etc.

NOTE DU TECHNICIEN:
"{description}"

Réponds UNIQUEMENT avec un JSON valide (pas de markdown, pas de texte avant/après):
{{
  "has_issue": true/false,
  "issue_type": "housse" ou "alimentation" ou "reservoir" ou null,
  "issue_keyword": "le mot exact du problème trouvé" ou null,
  "is_resolved": true/false,
  "resolution_keyword": "le mot exact de la résolution" ou null,
  "confidence": 0.0 à 1.0
}}"""

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=200
            )

            result_text = response.choices[0].message.content.strip()

            # Retirer les balises markdown si présentes
            if result_text.startswith('```'):
                result_text = result_text.split('\n', 1)[1] if '\n' in result_text else result_text
            if result_text.endswith('```'):
                result_text = result_text.rsplit('\n', 1)[0] if '\n' in result_text else result_text
            result_text = result_text.strip()

            result = json.loads(result_text)

            # Valider le résultat
            if result.get('has_issue') and result.get('confidence', 0) > 0.6:
                return (
                    result['issue_type'],
                    f"{result.get('issue_keyword', 'détecté par IA')}" +
                    (f" - Résolu: {result.get('resolution_keyword')}" if result.get('is_resolved') else ""),
                    result.get('is_resolved', False),
                    result.get('confidence', 0)
                )

            return None

        except Exception as e:
            print(f"⚠️ Erreur analyse IA: {e}")
            return None

    def _get_institutional_client_ids(self) -> set:
        """
        Récupère les IDs externes des clients institutionnels à surveiller.
        
        Returns:
            Set des client_external_id pour Vincent d'Indy, Place des Arts et Orford
        """
        import requests
        
        INSTITUTIONAL_CLIENTS = [
            "Vincent d'Indy",
            "Place des Arts",
            "Orford"
        ]
        
        try:
            # Récupérer tous les clients
            url = f"{self.storage.api_url}/gazelle_clients"
            params = {"select": "external_id,company_name"}
            response = requests.get(url, headers=self.storage._get_headers(), params=params)
            
            if response.status_code != 200:
                print(f"⚠️ Impossible de récupérer les clients pour filtre institutionnel: {response.status_code}")
                return set()
            
            clients = response.json()
            institutional_ids = set()
            
            for client in clients:
                company_name = client.get('company_name', '').strip()
                if company_name in INSTITUTIONAL_CLIENTS:
                    external_id = client.get('external_id')
                    if external_id:
                        institutional_ids.add(external_id)
            
            print(f"🏛️ {len(institutional_ids)} clients institutionnels identifiés: {', '.join(INSTITUTIONAL_CLIENTS)}")
            return institutional_ids
            
        except Exception as e:
            print(f"⚠️ Erreur récupération clients institutionnels: {e}")
            return set()

    def scan_timeline_entries(self, limit: int = 100) -> Dict[str, Any]:
        """
        Scanne les timeline entries pour détecter alertes.

        Workflow (adapté du PC):
        1. Charger historique des entries déjà scannées
        2. Récupérer IDs clients institutionnels (Vincent, PDA, Orford)
        3. Récupérer entries récentes
        4. Pour chaque entry NON scannée ET pour client institutionnel:
           a. detect_issue() (pattern matching)
           b. analyze_with_ai() si aucun match
           c. Enregistrer alerte si détectée
           d. Marquer entry comme scannée
        5. Envoyer notifications Slack (seulement non résolues)

        Args:
            limit: Nombre max d'entries à scanner

        Returns:
            Stats: {scanned, alerts_found, notifications_sent, skipped}
        """
        import requests

        stats = {
            'scanned': 0,
            'alerts_found': 0,
            'notifications_sent': 0,
            'errors': 0,
            'skipped': 0
        }

        try:
            # 1. Charger historique (entries déjà scannées)
            history_url = f"{self.storage.api_url}/humidity_alerts_history"
            history_response = requests.get(
                history_url,
                headers=self.storage._get_headers(),
                params={"select": "timeline_entry_id"}
            )

            scanned_ids = set()
            if history_response.status_code == 200:
                scanned_ids = {item['timeline_entry_id'] for item in history_response.json()}
                print(f"📚 {len(scanned_ids)} entries déjà scannées dans l'historique")

            # 2. Récupérer IDs clients institutionnels
            institutional_client_ids = self._get_institutional_client_ids()
            if not institutional_client_ids:
                print("⚠️ Aucun client institutionnel trouvé, scan annulé")
                return stats

            # 3. Récupérer timeline entries récentes
            url = f"{self.storage.api_url}/gazelle_timeline_entries"
            params = {
                "select": "external_id,description,occurred_at,client_external_id,piano_id",
                "order": "occurred_at.desc",
                "limit": limit
            }

            response = requests.get(url, headers=self.storage._get_headers(), params=params)

            if response.status_code != 200:
                print(f"❌ Erreur Supabase: {response.status_code}")
                return stats

            entries = response.json()
            print(f"📥 {len(entries)} timeline entries récupérées")

            # 4. Scanner chaque entry (skip si déjà scannée OU si pas client institutionnel)
            for entry in entries:
                try:
                    entry_id = entry.get('external_id')
                    client_id = entry.get('client_external_id')

                    # Skip si déjà scannée
                    if entry_id in scanned_ids:
                        stats['skipped'] += 1
                        continue

                    # FILTRE INSTITUTIONNEL: Skip si pas un client institutionnel
                    if client_id not in institutional_client_ids:
                        stats['skipped'] += 1
                        continue

                    description = entry.get('description', '')
                    if not description:
                        # Marquer comme scannée même si vide
                        self._mark_as_scanned(entry_id, found_issue=False)
                        continue

                    stats['scanned'] += 1

                    # a. Pattern matching
                    result = self.detect_issue(
                        description,
                        self.config['alert_keywords'],
                        self.config['resolution_keywords']
                    )

                    # b. Fallback IA si aucun match
                    if result is None:
                        ai_result = self.analyze_with_ai(
                            description,
                            self.config['alert_keywords'],
                            self.config['resolution_keywords']
                        )
                        if ai_result and ai_result[3] > 0.6:  # confidence > 60%
                            result = ai_result[:3]

                    # c. Enregistrer alerte si détectée
                    if result:
                        alert_type, alert_desc, is_resolved = result

                        self._save_alert(
                            entry_id=entry_id,
                            client_id=entry.get('client_external_id'),
                            piano_id=entry.get('piano_id'),
                            alert_type=alert_type,
                            description=alert_desc,
                            is_resolved=is_resolved,
                            observed_at=entry.get('occurred_at')
                        )

                        stats['alerts_found'] += 1

                        # d. Notifier Slack (seulement non résolues)
                        if not is_resolved:
                            self._send_slack_notification(alert_type, alert_desc, entry)
                            stats['notifications_sent'] += 1

                        # Marquer comme scannée avec problème trouvé
                        self._mark_as_scanned(entry_id, found_issue=True)
                    else:
                        # Marquer comme scannée sans problème
                        self._mark_as_scanned(entry_id, found_issue=False)

                except Exception as e:
                    print(f"⚠️ Erreur entry {entry.get('external_id')}: {e}")
                    stats['errors'] += 1

            print(f"\n✅ Scan terminé: {stats}")
            return stats

        except Exception as e:
            print(f"❌ Erreur scan_timeline_entries: {e}")
            import traceback
            traceback.print_exc()
            return stats

    def _mark_as_scanned(self, entry_id: str, found_issue: bool) -> bool:
        """
        Marque une timeline entry comme scannée dans l'historique.

        Args:
            entry_id: ID de la timeline entry
            found_issue: True si problème détecté

        Returns:
            True si succès
        """
        import requests

        try:
            url = f"{self.storage.api_url}/humidity_alerts_history"

            data = {
                'timeline_entry_id': entry_id,
                'found_issues': found_issue,
                'scanned_at': datetime.utcnow().isoformat()
            }

            response = requests.post(
                url,
                headers=self.storage._get_headers(),
                json=data
            )

            if response.status_code in [200, 201]:
                return True
            else:
                # Ignorer erreur si duplicate (déjà dans historique)
                if 'duplicate' not in response.text.lower():
                    print(f"⚠️ Erreur mark_as_scanned {response.status_code}: {response.text}")
                return False

        except Exception as e:
            print(f"❌ Erreur _mark_as_scanned: {e}")
            return False

    def _save_alert(
        self,
        entry_id: str,
        client_id: Optional[str],
        piano_id: Optional[str],
        alert_type: str,
        description: str,
        is_resolved: bool,
        observed_at: Optional[str]
    ) -> bool:
        """Enregistre une alerte dans Supabase."""
        import requests

        try:
            url = f"{self.storage.api_url}/humidity_alerts"

            data = {
                'timeline_entry_id': entry_id,
                'client_id': client_id,
                'piano_id': piano_id,
                'alert_type': alert_type,
                'description': description,
                'is_resolved': is_resolved,
                'observed_at': observed_at or datetime.utcnow().isoformat()
            }

            response = requests.post(
                url,
                headers=self.storage._get_headers(),
                json=data
            )

            if response.status_code in [200, 201]:
                print(f"✅ Alerte enregistrée: {alert_type} - {'Résolu' if is_resolved else 'NON RÉSOLU'}")
                return True
            else:
                # Ignorer erreur si duplicate (UNIQUE constraint)
                if 'duplicate' not in response.text.lower() and 'unique' not in response.text.lower():
                    print(f"⚠️ Erreur save_alert {response.status_code}: {response.text}")
                return False

        except Exception as e:
            print(f"❌ Erreur _save_alert: {e}")
            return False

    def _send_slack_notification(
        self,
        alert_type: str,
        description: str,
        entry: Dict[str, Any]
    ) -> bool:
        """
        Envoie notification Slack (Louise + Nicolas).

        Seulement pour alertes NON RÉSOLUES.
        Mention "Provenant du Mac" ajoutée.
        """
        message = (
            f"🚨 *ALERTE HUMIDITÉ DÉTECTÉE*\n"
            f"*Provenant du Mac*\n\n"
            f"Type: {alert_type.upper()}\n"
            f"Description: {description}\n"
            f"Client: {entry.get('client_external_id', 'N/A')}\n"
            f"Piano: {entry.get('piano_id', 'N/A')}\n"
            f"Date: {entry.get('occurred_at', 'N/A')}"
        )

        success = True

        # Envoyer à Louise
        if not SlackNotifier.send_simple_message(self.slack_webhooks['louise'], message):
            success = False

        # Envoyer à Nicolas
        if not SlackNotifier.send_simple_message(self.slack_webhooks['nicolas'], message):
            success = False

        return success


# ============================================================
# SCRIPT DE TEST
# ============================================================

if __name__ == "__main__":
    print("🧪 Test HumidityScanner")
    print("="*70)

    scanner = HumidityScanner()

    # Tester avec un scan limité
    stats = scanner.scan_timeline_entries(limit=10)

    print("\n📊 Résultats:")
    print(f"  - Scannées: {stats['scanned']}")
    print(f"  - Alertes trouvées: {stats['alerts_found']}")
    print(f"  - Notifications envoyées: {stats['notifications_sent']}")
    print(f"  - Erreurs: {stats['errors']}")
