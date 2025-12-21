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

SUPABASE_TIMEOUT = 25
ASSISTANTE_GAZELLE_ID = "usr_assistante"


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

    def send_alerts(
        self,
        target_date: Optional[date] = None,
        technician_ids: Optional[List[str]] = None,
        triggered_by: str = "system@piano-tek.com",
    ) -> Dict[str, any]:
        """
        Envoie les alertes et logge dans alert_logs.
        """
        if target_date is None:
            target_date = (datetime.now().date() + timedelta(days=1))

        by_technician = self.checker.get_unconfirmed_appointments(target_date=target_date)
        if technician_ids:
            by_technician = {k: v for k, v in by_technician.items() if k in technician_ids}

        if not by_technician:
            return {
                "success": True,
                "message": "Aucun RV non confirmé",
                "sent_count": 0,
                "target_date": target_date.isoformat(),
                "details": [],
            }

        alerts_to_send: List[dict] = []
        for tech_id, appointments in by_technician.items():
            tech_info = self.checker.get_technician_info(tech_id)
            if not tech_info:
                continue

            html_content = self.checker.format_alert_message(
                technician_name=tech_info["name"],
                appointments=appointments,
                target_date=target_date,
            )
            date_str = target_date.strftime("%d/%m/%Y")
            subject = f"⚠️ {len(appointments)} RV non confirmé(s) pour le {date_str}"

            alerts_to_send.append(
                {
                    "to_email": tech_info["email"],
                    "to_name": tech_info["name"],
                    "subject": subject,
                    "html_content": html_content,
                    "technician_id": tech_id,
                    "appointment_count": len(appointments),
                    "appointments": appointments,
                }
            )

        send_results = self.sender.send_batch_alerts(alerts_to_send)
        self._log_alerts(target_date, alerts_to_send, send_results, triggered_by)

        return {
            "success": True,
            "message": f"{len(alerts_to_send)} alerte(s) envoyée(s)",
            "sent_count": len(alerts_to_send),
            "target_date": target_date.isoformat(),
            "technicians": [
                {
                    "name": alert["to_name"],
                    "email": alert["to_email"],
                    "appointment_count": alert["appointment_count"],
                }
                for alert in alerts_to_send
            ],
        }

    # ------------------------------------------------------------------
    # Rendez-vous longue durée (14 jours à venir, créés il y a >= 4 mois)
    # ------------------------------------------------------------------
    def check_long_term_appointments(self) -> Dict[str, any]:
        """
        Repère les RV dans 14 jours créés il y a 4 mois ou plus, et notifie Louise.
        """
        target_date = (datetime.now(timezone.utc).date() + timedelta(days=14))
        cutoff_date = (datetime.now(timezone.utc).date() - timedelta(days=120))

        appointments = self._fetch_long_term_appointments(target_date, cutoff_date)
        if not appointments:
            return {"success": True, "count": 0, "message": "Aucun rendez-vous longue durée"}

        assistant_info = self.checker.get_technician_info(ASSISTANTE_GAZELLE_ID)
        assistant_email = assistant_info.get("email") if assistant_info else None
        assistant_name = assistant_info.get("name") if assistant_info else "Louise"

        if not assistant_email:
            return {"success": False, "message": "Email assistante introuvable dans users"}

        subject = "⚠️ Rappel : Rendez-vous longue durée dans 14 jours"
        html_content = self._format_long_term_email(assistant_name, appointments, target_date, cutoff_date)

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
    def _format_long_term_email(
        assistant_name: str,
        appointments: List[dict],
        target_date: date,
        cutoff_date: date,
    ) -> str:
        intro = (
            f"Bonjour {assistant_name},<br><br>"
            f"Voici les rendez-vous planifiés il y a plus de 4 mois qui arrivent dans 2 semaines "
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
