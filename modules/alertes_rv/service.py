#!/usr/bin/env python3
"""
Service orchestration pour le job 16h00 des RV non confirmés.
"""

from __future__ import annotations

from datetime import datetime, timedelta, date, timezone
from typing import Dict, List, Optional

import requests

from core.supabase_storage import SupabaseStorage
from modules.alertes_rv.checker import AppointmentChecker
from modules.alertes_rv.email_sender import EmailSender
import os

SUPABASE_TIMEOUT = 25
ASSISTANTE_GAZELLE_ID = "usr_assistante"

# Configuration des emails des techniciens (depuis .env)
TECHNICIAN_EMAILS = {
    'nicolas': os.getenv('EMAIL_NICOLAS', 'nicolas@pianotekinc.com'),
    'allan': os.getenv('EMAIL_ALLAN', 'asutton@piano-tek.com'),
    'jp': os.getenv('EMAIL_JP', 'jp@pianotekinc.com'),
    'jean-philippe': os.getenv('EMAIL_JP', 'jp@pianotekinc.com'),
    'jean philippe': os.getenv('EMAIL_JP', 'jp@pianotekinc.com'),
}

# Email de Louise pour les alertes de relance de vieux rendez-vous
LOUISE_EMAIL = os.getenv('LOUISE_EMAIL', 'info@piano-tek.com')


class UnconfirmedAlertsService:
    """Coordonne la récupération, l'envoi des alertes et le logging."""

    def __init__(
        self,
        storage: Optional[SupabaseStorage] = None,
        checker: Optional[AppointmentChecker] = None,
        sender: Optional[EmailSender] = None,
    ) -> None:
        self.storage = storage or SupabaseStorage()
        self.checker = checker or AppointmentChecker(self.storage)
        self.sender = sender or EmailSender(method="sendgrid")

    def _identify_technician_and_route(
        self,
        tech_info: Optional[Dict[str, str]]
    ) -> tuple[str, str]:
        """
        Identifie le technicien par nom et route vers l'email approprié.
        
        Args:
            tech_info: Dict avec 'name' et 'email' du technicien
            
        Returns:
            tuple: (technician_name, email_address)
            Fallback: Si technicien non reconnu, retourne ('Nicolas', EMAIL_NICOLAS)
        """
        if not tech_info:
            # Fallback: Nicolas par défaut
            return ('Nicolas', TECHNICIAN_EMAILS.get('nicolas', 'nicolas@pianotekinc.com'))
        
        tech_name = tech_info.get("name", "").lower().strip()
        tech_email = tech_info.get("email", "")
        
        # Identification par nom
        if 'nicolas' in tech_name or 'nick' in tech_name:
            return ('Nicolas', TECHNICIAN_EMAILS.get('nicolas', tech_email))
        elif 'allan' in tech_name or 'asutton' in tech_email.lower():
            return ('Allan', TECHNICIAN_EMAILS.get('allan', tech_email))
        elif 'jean-philippe' in tech_name or 'jean philippe' in tech_name or 'jp' in tech_name.lower():
            return ('JP', TECHNICIAN_EMAILS.get('jp', tech_email))
        else:
            # Fallback: Nicolas par défaut si non reconnu
            print(f"⚠️ Technicien non reconnu: {tech_name} - routage vers Nicolas par défaut")
            return ('Nicolas', TECHNICIAN_EMAILS.get('nicolas', 'nicolas@pianotekinc.com'))

    def _format_urgence_message(
        self,
        technician_name: str,
        client_name: str
    ) -> str:
        """
        Formate le message d'urgence personnalisé J-1.
        
        Args:
            technician_name: Nom du technicien (Nicolas, Allan, JP)
            client_name: Nom du client
            
        Returns:
            str: Message HTML formaté
        """
        return f"""
        <html>
        <body style="font-family: Arial, sans-serif; padding: 20px;">
            <h2 style="color: #d9534f;">⚠️ Rendez-vous non confirmé</h2>
            <p>Salut {technician_name},</p>
            <p>Ton rendez-vous de demain chez <strong>{client_name}</strong> n'est toujours pas confirmé.</p>
            <p style="margin-top: 20px; color: #777;">
                Merci de contacter le client pour confirmer le rendez-vous.
            </p>
            <hr style="margin-top: 30px;">
            <p style="color: #777; font-size: 12px;">
                Cette alerte a été générée automatiquement par le système Assistant Gazelle V5.
            </p>
        </body>
        </html>
        """

    def _cleanup_ghost_appointments(self, target_date: date) -> int:
        """
        Nettoie les RV fantômes : supprime ou marque comme annulé les RV qui n'existent plus dans Gazelle.
        
        IMPORTANT: Ne nettoie QUE les RV qui n'existent vraiment plus dans Gazelle.
        Les RV sans technicien ou sans date dans Gazelle sont CONSERVÉS (ils existent toujours).
        
        Args:
            target_date: Date à vérifier
            
        Returns:
            Nombre de RV nettoyés
        """
        try:
            from core.gazelle_api_client import GazelleAPIClient
            gazelle_client = GazelleAPIClient()
            
            # Récupérer tous les RV de la date dans Supabase
            date_str = target_date.isoformat()
            supabase_appointments = (
                self.storage.client.table('gazelle_appointments')
                .select('id, external_id, title, status')
                .eq('appointment_date', date_str)
                .eq('status', 'ACTIVE')
                .execute()
            )
            
            if not supabase_appointments.data:
                return 0
            
            # Récupérer TOUS les RV depuis Gazelle (pas de filtre par date)
            # Car certains RV peuvent exister sans startDate
            # Limite augmentée à 500 pour être sûr de trouver tous les RV
            gazelle_appointments = gazelle_client.get_appointments(limit=500)
            gazelle_ids = {apt.get('id') for apt in gazelle_appointments if apt.get('id')}
            
            # Identifier les RV fantômes (dans Supabase mais vraiment absents de Gazelle)
            ghost_count = 0
            for supabase_apt in supabase_appointments.data:
                external_id = supabase_apt.get('external_id')
                if external_id and external_id not in gazelle_ids:
                    # Vérifier une dernière fois que le RV n'existe vraiment pas
                    # (même sans technicien ou date, s'il existe dans Gazelle, on le garde)
                    exists_in_gazelle = any(apt.get('id') == external_id for apt in gazelle_appointments)
                    
                    if not exists_in_gazelle:
                        # Le RV n'existe vraiment plus dans Gazelle - marquer comme annulé
                        apt_id = supabase_apt.get('id')
                        try:
                            self.storage.client.table('gazelle_appointments').update({
                                'status': 'CANCELLED'
                            }).eq('id', apt_id).execute()
                            ghost_count += 1
                            print(f"   🧹 RV fantôme nettoyé: {supabase_apt.get('title', 'N/A')[:50]} ({external_id})")
                        except Exception as e:
                            print(f"   ⚠️ Erreur nettoyage RV {external_id}: {e}")
                    else:
                        # Le RV existe dans Gazelle (même sans technicien/date) - on le garde
                        print(f"   ℹ️ RV {external_id} existe dans Gazelle (sans technicien/date) - conservé")
            
            if ghost_count > 0:
                print(f"✅ {ghost_count} RV fantôme(s) nettoyé(s) pour {date_str}")
            
            return ghost_count
            
        except Exception as e:
            print(f"⚠️ Erreur nettoyage RV fantômes: {e}")
            return 0

    def _verify_appointment_exists_in_gazelle(self, external_id: str) -> bool:
        """
        Vérifie une dernière fois si un RV existe dans Gazelle avant d'envoyer une alerte.
        
        Args:
            external_id: ID externe du rendez-vous
            
        Returns:
            True si le RV existe dans Gazelle, False sinon
        """
        try:
            from core.gazelle_api_client import GazelleAPIClient
            gazelle_client = GazelleAPIClient()
            
            # Limite augmentée à 500 pour être sûr de trouver tous les RV
            appointments = gazelle_client.get_appointments(limit=500)
            
            for apt in appointments:
                if apt.get('id') == external_id:
                    return True
            
            return False
            
        except Exception as e:
            print(f"⚠️ Erreur vérification finale pour {external_id}: {e}")
            # En cas d'erreur, on ne bloque pas l'envoi (mais on log l'erreur)
            return True  # Permettre l'envoi en cas d'erreur API

    def send_alerts(
        self,
        target_date: Optional[date] = None,
        technician_ids: Optional[List[str]] = None,
        triggered_by: str = "system@piano-tek.com",
    ) -> Dict[str, any]:
        """
        Envoie les alertes J-1 avec routage ciblé par technicien.
        - Nicolas → EMAIL_NICOLAS
        - Allan → EMAIL_ALLAN
        - JP → EMAIL_JP
        - Fallback → Nicolas
        
        NETTOYAGE: Supprime les RV fantômes avant de vérifier.
        FIABILITÉ: Vérifie une dernière fois dans Gazelle avant d'envoyer.
        """
        if target_date is None:
            from core.timezone_utils import MONTREAL_TZ
            target_date = (datetime.now(MONTREAL_TZ).date() + timedelta(days=1))

        # 1. NETTOYAGE: Supprimer les RV fantômes
        print(f"\n🧹 Nettoyage des RV fantômes pour {target_date.isoformat()}...")
        ghost_count = self._cleanup_ghost_appointments(target_date)

        # 2. Récupérer les RV non confirmés (après nettoyage)
        by_technician = self.checker.get_unconfirmed_appointments(target_date=target_date)
        if technician_ids:
            by_technician = {k: v for k, v in by_technician.items() if k in technician_ids}

        if not by_technician:
            return {
                "success": True,
                "message": "Aucun RV non confirmé",
                "sent_count": 0,
                "target_date": target_date.isoformat(),
                "ghost_cleaned": ghost_count,
                "details": [],
            }

        alerts_to_send: List[dict] = []
        dashboard_alerts_to_create: List[dict] = []
        
        for tech_id, appointments in by_technician.items():
            tech_info = self.checker.get_technician_info(tech_id)
            
            # Identification et routage ciblé
            technician_name, technician_email = self._identify_technician_and_route(tech_info)
            
            # Envoyer un email par RV (message personnalisé)
            for apt in appointments:
                external_id = apt.get('external_id')
                client_name = apt.get('client_name', 'Client inconnu')
                
                # 3. FIABILITÉ: Vérification finale dans Gazelle avant envoi
                if not self._verify_appointment_exists_in_gazelle(external_id):
                    print(f"   ⚠️ RV {external_id} n'existe plus dans Gazelle - alerte annulée")
                    continue
                
                # Message personnalisé pour chaque RV
                html_content = self._format_urgence_message(technician_name, client_name)
                subject = f"⚠️ RV non confirmé demain chez {client_name}"
                
                alerts_to_send.append(
                    {
                        "to_email": technician_email,
                        "to_name": technician_name,
                        "subject": subject,
                        "html_content": html_content,
                        "technician_id": tech_id,
                        "technician_name": technician_name,
                        "appointment_count": 1,  # Un email par RV
                        "appointments": [apt],  # Un seul RV par email
                        "client_name": client_name,
                    }
                )
                
                # Préparer l'entrée dashboard_alerts
                dashboard_alerts_to_create.append({
                    "type": "URGENCE_CONFIRMATION",
                    "severity": "warning",  # Rouge sur le Dashboard
                    "title": f"RV non confirmé - {client_name}",
                    "message": f"Rendez-vous de demain chez {client_name} non confirmé",
                    "technician_id": tech_id,
                    "technician_name": technician_name,
                    "appointment_id": apt.get("appointment_id") or apt.get("external_id"),
                    "client_name": client_name,
                    "appointment_date": target_date.isoformat(),
                    "appointment_time": apt.get("appointment_time", "00:00"),
                    "metadata": {
                        "appointment_external_id": apt.get("external_id"),
                        "triggered_by": triggered_by,
                    }
                })

        # Envoyer les emails
        send_results = self.sender.send_batch_alerts(alerts_to_send)
        
        # Logger dans alert_logs (comme avant)
        self._log_alerts(target_date, alerts_to_send, send_results, triggered_by)
        
        # Créer les entrées dashboard_alerts
        self._create_dashboard_alerts(dashboard_alerts_to_create, send_results)

        return {
            "success": True,
            "message": f"{len(alerts_to_send)} alerte(s) envoyée(s)",
            "sent_count": len(alerts_to_send),
            "target_date": target_date.isoformat(),
            "ghost_cleaned": ghost_count,
            "technicians": [
                {
                    "name": alert["technician_name"],
                    "email": alert["to_email"],
                    "appointment_count": alert["appointment_count"],
                }
                for alert in alerts_to_send
            ],
        }

    # ------------------------------------------------------------------
    # RELANCE LOUISE (J-7) : 7 jours avant un RV créé il y a plus de 3 mois
    # ------------------------------------------------------------------
    def check_relance_louise(self) -> Dict[str, any]:
        """
        RELANCE LOUISE (J-7) : 7 jours avant un RV, si celui-ci a été créé il y a plus de 3 mois,
        envoie une alerte à Louise (info@piano-tek.com).
        """
        from core.timezone_utils import MONTREAL_TZ
        now_mtl = datetime.now(MONTREAL_TZ)
        target_date = (now_mtl.date() + timedelta(days=7))
        cutoff_date = (now_mtl.date() - timedelta(days=90))  # 3 mois

        appointments = self._fetch_long_term_appointments(target_date, cutoff_date)
        if not appointments:
            return {"success": True, "count": 0, "message": "Aucun rendez-vous à relancer"}

        # Utiliser LOUISE_EMAIL depuis .env (info@piano-tek.com)
        assistant_email = LOUISE_EMAIL
        assistant_name = "Louise"

        if not assistant_email:
            return {"success": False, "message": "LOUISE_EMAIL non configuré dans .env"}

        subject = "⚠️ Relance : Rendez-vous dans 7 jours (créé il y a plus de 3 mois)"
        html_content = self._format_relance_email(assistant_name, appointments, target_date, cutoff_date)

        sent = self.sender.send_email(
            to_email=assistant_email,
            to_name=assistant_name,
            subject=subject,
            html_content=html_content,
        )

        return {
            "success": sent,
            "count": len(appointments),
            "target_date": target_date.isoformat(),
            "cutoff_date": cutoff_date.isoformat(),
        }

    def _fetch_long_term_appointments(self, target_date: date, cutoff_date: date) -> List[dict]:
        url = (
            f"{self.storage.api_url}/gazelle_appointments"
            f"?appointment_date=eq.{target_date.isoformat()}"
            f"&created_at=lte.{cutoff_date.isoformat()}"
            f"&status=neq.cancelled"
            f"&select=id,external_id,appointment_date,appointment_time,title,description,type,"
            f"created_at,client_name,technician_external_id"
        )
        try:
            resp = requests.get(url, headers=self.storage._get_headers(), timeout=SUPABASE_TIMEOUT)
            if resp.status_code != 200:
                print(f"⚠️ Erreur Supabase long term: {resp.status_code} {resp.text}")
                return []
            return resp.json() or []
        except Exception as e:
            print(f"⚠️ Erreur fetch long term: {e}")
            return []

    @staticmethod
    def _format_relance_email(
        assistant_name: str,
        appointments: List[dict],
        target_date: date,
        cutoff_date: date,
    ) -> str:
        intro = (
            f"Bonjour {assistant_name},<br><br>"
            f"Voici les rendez-vous planifiés il y a plus de 3 mois qui arrivent dans 7 jours "
            f"({target_date.isoformat()}). Une confirmation manuelle est suggérée.<br><br>"
        )

        rows = ""
        for apt in appointments:
            client = apt.get("client_name") or "N/A"
            service = apt.get("type") or apt.get("title") or ""
            created_at = apt.get("created_at", "")
            created_str = created_at.replace("T", " ").replace("Z", "") if created_at else ""
            apt_date = apt.get("appointment_date", target_date.isoformat())
            rows += (
                f"<tr>"
                f"<td style='border:1px solid #ddd;padding:8px;'>{client}</td>"
                f"<td style='border:1px solid #ddd;padding:8px;'>{apt_date}</td>"
                f"<td style='border:1px solid #ddd;padding:8px;'>{service}</td>"
                f"<td style='border:1px solid #ddd;padding:8px;'>{created_str}</td>"
                f"</tr>"
            )

        table = (
            "<table style='border-collapse:collapse;width:100%;'>"
            "<thead><tr style='background:#f2f2f2;'>"
            "<th style='border:1px solid #ddd;padding:8px;'>Client</th>"
            "<th style='border:1px solid #ddd;padding:8px;'>Date du RV</th>"
            "<th style='border:1px solid #ddd;padding:8px;'>Service</th>"
            "<th style='border:1px solid #ddd;padding:8px;'>Créé le</th>"
            "</tr></thead>"
            "<tbody>"
            f"{rows}"
            "</tbody></table>"
        )

        footer = (
            "<br><br>"
            "<p style='color:#777;font-size:12px;'>"
            "Cette alerte est générée automatiquement par Assistant Gazelle V5."
            "</p>"
        )

        return intro + table + footer

    # ------------------------------------------------------------------
    # Logging Supabase
    # ------------------------------------------------------------------
    def _log_alerts(
        self,
        target_date: date,
        alerts_to_send: List[dict],
        send_results: dict,
        triggered_by: str,
    ) -> None:
        for i, alert in enumerate(alerts_to_send):
            success = send_results["details"][i]["success"] if i < len(send_results.get("details", [])) else True
            for apt in alert.get("appointments", []):
                appointment_id = apt.get("appointment_id") or apt.get("id") or apt.get("external_id")
                if not appointment_id:
                    continue

                # Dédupliquer : si déjà non acknowledged pour ce RV/technicien, ne pas recréer
                if self._alert_exists(appointment_id, alert["technician_id"]):
                    continue

                payload = {
                    "appointment_id": appointment_id,
                    "technician_id": alert["technician_id"],
                    "technician_name": alert["to_name"],
                    "technician_email": alert["to_email"],
                    "appointment_date": target_date.isoformat(),
                    "appointment_time": apt.get("appointment_time", "00:00"),
                    "client_name": apt.get("client_name"),
                    "client_phone": apt.get("client_phone"),
                    "service_type": apt.get("service_type") or apt.get("title"),
                    "title": apt.get("title"),
                    "description": apt.get("description") or apt.get("title", ""),
                    "status": "sent" if success else "failed",
                    "acknowledged": False,
                    "sent_at": datetime.now(timezone.utc).isoformat(),
                    "triggered_by": triggered_by,
                }

                try:
                    url = f"{self.storage.api_url}/alert_logs"
                    headers = self.storage._get_headers()
                    headers["Prefer"] = "resolution=merge-duplicates"
                    resp = requests.post(url, headers=headers, json=payload, timeout=SUPABASE_TIMEOUT)
                    if resp.status_code not in [200, 201]:
                        print(f"⚠️ Log alert_logs status {resp.status_code}: {resp.text}")
                except Exception as e:
                    print(f"⚠️ Erreur log alert_logs: {e}")

    def _alert_exists(self, appointment_id: str, technician_id: str) -> bool:
        try:
            url = (
                f"{self.storage.api_url}/alert_logs"
                f"?appointment_id=eq.{appointment_id}"
                f"&technician_id=eq.{technician_id}"
                f"&acknowledged=eq.false"
                f"&limit=1"
            )
            resp = requests.get(url, headers=self.storage._get_headers(), timeout=SUPABASE_TIMEOUT)
            if resp.status_code != 200:
                return False
            data = resp.json() or []
            return len(data) > 0
        except Exception:
            return False

    def _create_dashboard_alerts(
        self,
        dashboard_alerts: List[dict],
        send_results: dict
    ) -> None:
        """
        Crée les entrées dans dashboard_alerts pour affichage sur le Dashboard.
        
        Args:
            dashboard_alerts: Liste de dicts avec les données des alertes
            send_results: Résultats de l'envoi des emails (pour marquer si échec)
        """
        if not dashboard_alerts:
            return
            
        for i, alert_data in enumerate(dashboard_alerts):
            # Vérifier si l'email a été envoyé avec succès
            email_success = True
            if i < len(send_results.get("details", [])):
                email_success = send_results["details"][i].get("success", True)
            
            # Ne créer l'alerte dashboard que si l'email a été envoyé
            if not email_success:
                continue
            
            # Vérifier si l'alerte existe déjà (éviter doublons)
            appointment_id = alert_data.get("appointment_id")
            technician_id = alert_data.get("technician_id")
            
            if appointment_id and technician_id:
                if self._dashboard_alert_exists(appointment_id, technician_id):
                    continue
            
            try:
                url = f"{self.storage.api_url}/dashboard_alerts"
                headers = self.storage._get_headers()
                headers["Prefer"] = "resolution=merge-duplicates"
                
                resp = requests.post(
                    url,
                    headers=headers,
                    json=alert_data,
                    timeout=SUPABASE_TIMEOUT
                )
                
                if resp.status_code not in [200, 201]:
                    print(f"⚠️ Erreur création dashboard_alert status {resp.status_code}: {resp.text}")
                else:
                    print(f"✅ Dashboard alert créée pour {alert_data.get('client_name')} - {alert_data.get('technician_name')}")
            except Exception as e:
                print(f"⚠️ Erreur création dashboard_alert: {e}")

    def _dashboard_alert_exists(self, appointment_id: str, technician_id: str) -> bool:
        """
        Vérifie si une alerte dashboard existe déjà pour ce RV/technicien.
        
        Args:
            appointment_id: ID du rendez-vous
            technician_id: ID du technicien
            
        Returns:
            bool: True si l'alerte existe déjà
        """
        try:
            url = (
                f"{self.storage.api_url}/dashboard_alerts"
                f"?appointment_id=eq.{appointment_id}"
                f"&technician_id=eq.{technician_id}"
                f"&type=eq.URGENCE_CONFIRMATION"
                f"&acknowledged=eq.false"
                f"&limit=1"
            )
            resp = requests.get(url, headers=self.storage._get_headers(), timeout=SUPABASE_TIMEOUT)
            if resp.status_code != 200:
                return False
            data = resp.json() or []
            return len(data) > 0
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Resolution / consultation
    # ------------------------------------------------------------------
    def list_pending(self, technician_id: Optional[str] = None) -> List[dict]:
        try:
            url = f"{self.storage.api_url}/alert_logs?acknowledged=eq.false&order=appointment_date.asc,appointment_time.asc"
            if technician_id:
                url += f"&technician_id=eq.{technician_id}"
            resp = requests.get(url, headers=self.storage._get_headers(), timeout=SUPABASE_TIMEOUT)
            if resp.status_code != 200:
                print(f"⚠️ Erreur fetch pending: {resp.status_code}")
                return []
            return resp.json() or []
        except Exception as e:
            print(f"⚠️ Erreur list_pending: {e}")
            return []

    def resolve_alert(self, alert_id: str, resolved_by: str) -> bool:
        try:
            url = f"{self.storage.api_url}/alert_logs?id=eq.{alert_id}"
            payload = {
                "acknowledged": True,
                "acknowledged_at": datetime.now(timezone.utc).isoformat(),
                "acknowledged_by": resolved_by,
            }
            resp = requests.patch(url, headers=self.storage._get_headers(), json=payload, timeout=SUPABASE_TIMEOUT)
            return resp.status_code in [200, 204]
        except Exception as e:
            print(f"⚠️ Erreur resolve_alert: {e}")
            return False
