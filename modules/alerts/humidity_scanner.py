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
from core.notification_service import get_notification_service


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
        self.notifier = get_notification_service()

        # Charger configuration
        if config_path is None:
            config_path = Path(__file__).parent.parent.parent / "config" / "alerts" / "config.json"

        self.config = self._load_config(config_path)

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

        # ⚠️ FILTRE: Ignorer les notes de service normales avec mesures
        # Exemples à ignorer: "21C, 39%", "Accord 440Hz, 21C, 39%", "température: 20C"
        import re

        # Pattern pour détecter des mesures normales de température/humidité
        # Format: chiffres + C/F/° suivi de chiffres + %
        # Exemples: "21C, 39%", "20°C 45%", "68F, 40%"
        measurement_pattern = r'\d+\s*[CF°]\s*,?\s*\d+\s*%'

        if re.search(measurement_pattern, description):
            # C'est une mesure normale, pas une alerte - ignorer
            return None

        # Parcourir chaque type de problème
        for issue_type, keyword_list in alert_keywords.items():
            for keyword in keyword_list:
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
        🤖 FALLBACK IA - Claude Haiku

        Analyse texte avec IA si pattern matching échoue.

        Adapté depuis: humidity_alert_system.py (PC Windows)

        Args:
            description: Texte de la timeline entry
            alert_keywords: Dict {type: [keywords]}
            resolution_keywords: Dict {type: [keywords]}

        Returns:
            Tuple (alert_type, description, is_resolved, confidence) ou None
            Nécessite: ANTHROPIC_API_KEY dans .env
        """
        if not description or (hasattr(description, '__len__') and len(str(description).strip()) == 0):
            return None

        # Vérifier si Anthropic est configuré
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            return None

        try:
            from anthropic import Anthropic
            client = Anthropic(api_key=api_key)

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

            response = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=200,
                temperature=0.1,
                messages=[{"role": "user", "content": prompt}]
            )

            result_text = response.content[0].text.strip()

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
                'scanned_at': datetime.now(timezone.utc).isoformat()
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
                'observed_at': observed_at or datetime.now(timezone.utc).isoformat()
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
        Envoie notification Email (Nicolas) + Slack (Louise + Nicolas).

        Seulement pour alertes NON RÉSOLUES.
        Utilise le nouveau NotificationService centralisé.
        """
        import requests

        # Enrichir les données avec les informations complètes du client et piano
        client_name = "N/A"
        client_id = entry.get('client_external_id')
        if client_id:
            try:
                url = f"{self.storage.api_url}/gazelle_clients"
                params = {"select": "company_name", "external_id": f"eq.{client_id}"}
                resp = requests.get(url, headers=self.storage._get_headers(), params=params)
                if resp.status_code == 200 and resp.json():
                    client_name = resp.json()[0].get('company_name', 'N/A')
            except Exception as e:
                print(f"⚠️ Erreur récupération client: {e}")

        # Récupérer détails du piano
        piano_info_name = "N/A"
        local_info = "N/A"
        piano_id = entry.get('piano_id')
        if piano_id:
            try:
                url = f"{self.storage.api_url}/gazelle_pianos"
                params = {"select": "make,model,location", "id": f"eq.{piano_id}"}
                resp = requests.get(url, headers=self.storage._get_headers(), params=params)
                if resp.status_code == 200 and resp.json():
                    piano_data = resp.json()[0]
                    make = piano_data.get('make', '')
                    model = piano_data.get('model', '')
                    piano_info_name = f"{make} {model}".strip() or "N/A"
                    local_info = piano_data.get('location') or "N/A"
            except Exception as e:
                print(f"⚠️ Erreur récupération piano: {e}")

        # Préparer les données pour le notifier
        piano_info = {
            'nom': piano_info_name,
            'client': client_name,
            'lieu': local_info
        }

        # Déterminer le type d'alerte et la valeur d'humidité (si disponible)
        humidity_value = 0  # Par défaut
        # Essayer d'extraire la valeur d'humidité de la description
        import re
        humidity_match = re.search(r'(\d+)%', description)
        if humidity_match:
            humidity_value = float(humidity_match.group(1))

        # Mapper le type d'alerte vers les valeurs attendues
        alert_type_mapped = 'TROP_SEC' if 'sec' in alert_type.lower() or 'housse' in description.lower() else 'TROP_HUMIDE'

        # Utiliser le service de notifications centralisé
        # Envoie Email (Nicolas) + Slack (Louise + Nicolas)
        results = self.notifier.notify_humidity_alert(
            piano_info=piano_info,
            humidity_value=humidity_value,
            alert_type=alert_type_mapped,
            send_email=True,  # Email à Nicolas
            send_slack=True   # Slack à Louise + Nicolas
        )

        # Envoi explicite à nlessard@piano-tek.com avec destinataire hardcodé,
        # en plus du chemin notifier (qui dépend d'EMAIL_NICOLAS / RECIPIENTS).
        # Garantit que Nicolas reçoit l'email même si l'env var est mal résolue.
        try:
            from core.email_notifier import get_email_notifier
            direct_notifier = get_email_notifier()
            emoji = "🏜️" if alert_type_mapped == "TROP_SEC" else "💧"
            subject = (
                f"{emoji} Alerte PLS — {piano_info['client']} — "
                f"{piano_info['nom']} ({piano_info['lieu']})"
            )
            html = (
                f"<html><body style='font-family:Arial,sans-serif;line-height:1.5;'>"
                f"<div style='background:#fef3c7;border-left:4px solid #f59e0b;padding:16px;'>"
                f"<h2 style='margin:0 0 8px 0;'>🚨 Alerte entretien PLS détectée</h2>"
                f"<p style='margin:0;color:#666;'>Type : <strong>{alert_type}</strong></p>"
                f"</div>"
                f"<table style='margin-top:16px;'>"
                f"<tr><td><strong>Piano :</strong></td><td>{piano_info['nom']}</td></tr>"
                f"<tr><td><strong>Client :</strong></td><td>{piano_info['client']}</td></tr>"
                f"<tr><td><strong>Lieu :</strong></td><td>{piano_info['lieu']}</td></tr>"
                f"<tr><td><strong>Description :</strong></td><td>{description}</td></tr>"
                f"</table>"
                f"<p style='color:#888;font-size:12px;margin-top:20px;'>"
                f"Détecté lors du scan automatique des notes de service. "
                f"Consultez le Dashboard humidité pour le détail."
                f"</p>"
                f"</body></html>"
            )
            ok = direct_notifier.send_email(
                to_emails=["nlessard@piano-tek.com"],
                subject=subject,
                html_content=html,
            )
            if ok:
                print(f"✅ Email PLS direct envoyé à nlessard@piano-tek.com")
                results['email_direct'] = True
            else:
                print(f"⚠️ Échec envoi email direct à nlessard@piano-tek.com")
                results['email_direct'] = False
        except Exception as e:
            print(f"❌ Erreur envoi email direct à nlessard: {e}")
            results['email_direct'] = False

        # Succès si au moins un canal a fonctionné
        return (
            results.get('email', False)
            or results.get('email_direct', False)
            or results.get('slack', False)
        )


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
