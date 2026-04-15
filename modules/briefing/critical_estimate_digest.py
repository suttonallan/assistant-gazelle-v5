#!/usr/bin/env python3
"""Digest quotidien à Louise des RV avec soumissions critiques non confirmées.

Scannée par le scheduler à 7h chaque matin :
1. Pour chaque RV dans les N prochains jours (défaut 7)
2. Fetch live des soumissions Gazelle du client
3. Filtre celles qui sont "critiques" (mots-clés de travail majeur OU total ≥ 500 $)
4. Déduplication via table critical_estimate_notifications (pas re-notifier si déjà
   envoyé dans les 7 derniers jours pour le même (client, soumission))
5. Envoi d'un email digest à Louise (+ Allan en copie)

Contexte : demandé par Allan le 2026-04-15 suite au cas Francesca Trop —
elle avait un RV ce matin et une soumission #11547 de janvier 2024 à 1 214 $
(pivotage + étouffoirs) qu'on n'avait jamais validée comme réalisée ou non.
Allan : "si un client prend rv alors qu'il a une soumission critique faite
lors de la dernière visite (même il y a pas mal longtemps), ça serait flaggé
et un avis envoyé à Louise."
"""

import os
from datetime import datetime, timedelta, date as date_type
from typing import Dict, List, Optional
from urllib.parse import quote

import requests as http_requests

from core.supabase_storage import SupabaseStorage
from core.email_notifier import EmailNotifier
from modules.briefing.client_intelligence_service import NarrativeBriefingService


DAYS_AHEAD = 7  # Fenêtre des RV à scanner
DEDUP_WINDOW_DAYS = 7  # On ne re-notifie pas si déjà envoyé dans les 7 derniers jours


def _fetch_upcoming_appointments(storage: SupabaseStorage, days_ahead: int) -> List[Dict]:
    """Liste les RV ACTIVE dans les N prochains jours depuis la cache Supabase."""
    today = date_type.today()
    end = today + timedelta(days=days_ahead)
    url = (
        f"{storage.api_url}/gazelle_appointments"
        f"?select=external_id,client_external_id,piano_external_id,"
        f"appointment_date,appointment_time,title,description,technicien,status"
        f"&appointment_date=gte.{today.isoformat()}"
        f"&appointment_date=lte.{end.isoformat()}"
        f"&status=in.(ACTIVE,CONFIRMED,UNCONFIRMED)"
        f"&order=appointment_date.asc"
    )
    try:
        r = http_requests.get(url, headers=storage._get_headers(), timeout=15)
        if r.status_code != 200:
            print(f"⚠️ Fetch appointments HTTP {r.status_code}: {r.text[:200]}")
            return []
        return r.json() or []
    except Exception as exc:
        print(f"⚠️ Fetch appointments erreur : {exc}")
        return []


def _fetch_client_info(storage: SupabaseStorage, client_ids: List[str]) -> Dict[str, Dict]:
    """Retourne {client_id: {first_name, last_name, company_name}}."""
    if not client_ids:
        return {}
    ids_csv = ",".join(quote(cid) for cid in client_ids)
    url = (
        f"{storage.api_url}/gazelle_clients"
        f"?select=external_id,first_name,last_name,company_name"
        f"&external_id=in.({ids_csv})"
    )
    try:
        r = http_requests.get(url, headers=storage._get_headers(), timeout=15)
        if r.status_code == 200:
            return {c["external_id"]: c for c in r.json() if c.get("external_id")}
    except Exception:
        pass
    return {}


def _already_notified_recently(
    storage: SupabaseStorage,
    client_id: str,
    estimate_number: int,
) -> bool:
    """Check dedup table — return True if we already sent a notice for this
    (client, estimate) within DEDUP_WINDOW_DAYS."""
    cutoff = (datetime.now() - timedelta(days=DEDUP_WINDOW_DAYS)).isoformat()
    url = (
        f"{storage.api_url}/critical_estimate_notifications"
        f"?client_external_id=eq.{client_id}"
        f"&estimate_number=eq.{estimate_number}"
        f"&sent_at=gte.{cutoff}"
        f"&select=id&limit=1"
    )
    try:
        r = http_requests.get(url, headers=storage._get_headers(), timeout=10)
        if r.status_code == 200:
            return len(r.json()) > 0
    except Exception:
        pass
    return False


def _record_notification(
    storage: SupabaseStorage,
    client_id: str,
    estimate_number: int,
    appointment_id: Optional[str],
    estimate_summary: Dict,
) -> None:
    """Insert a row in critical_estimate_notifications to avoid re-sending."""
    row = {
        "client_external_id": client_id,
        "estimate_number": estimate_number,
        "appointment_external_id": appointment_id,
        "estimate_total_cents": estimate_summary.get("total_cents", 0),
        "estimate_date": estimate_summary.get("estimated_on"),
        "estimate_is_archived": estimate_summary.get("is_archived", False),
        "sent_at": datetime.now().isoformat(),
    }
    url = f"{storage.api_url}/critical_estimate_notifications"
    try:
        headers = {**storage._get_headers(), "Prefer": "return=minimal"}
        http_requests.post(url, headers=headers, json=row, timeout=10)
    except Exception as exc:
        print(f"⚠️ Impossible de logger notification : {exc}")


def _build_html_body(items: List[Dict], today_str: str) -> str:
    """Compose HTML email body for the digest."""
    rows_html = []
    for it in items:
        client_name = it["client_name"]
        appt_date = it["appointment_date"]
        appt_time = it.get("appointment_time") or ""
        tech_name = it.get("technician_name") or "?"
        for est in it["critical_estimates"]:
            est_number = est.get("number", "?")
            est_date = est.get("estimated_on") or "?"
            est_total = est.get("total_dollars") or "?"
            main_items = est.get("main_items") or []
            items_str = " + ".join(main_items[:3]) if main_items else "contenu non détaillé"
            status = "archivée" if est.get("is_archived") else "active"
            rows_html.append(
                f"<tr>"
                f"<td style='padding:10px 8px;border-bottom:1px solid #eee;'>"
                f"<strong>{client_name}</strong><br/>"
                f"<small style='color:#666;'>RV {appt_date} {appt_time} · {tech_name}</small>"
                f"</td>"
                f"<td style='padding:10px 8px;border-bottom:1px solid #eee;'>"
                f"<strong>Soumission #{est_number}</strong> ({est_date}, {status})<br/>"
                f"<span style='color:#c00;font-weight:600;'>{est_total}$</span> — "
                f"{items_str}"
                f"</td>"
                f"</tr>"
            )
    rows = "\n".join(rows_html)
    total_items = sum(len(it["critical_estimates"]) for it in items)
    total_clients = len(items)
    return f"""<!DOCTYPE html>
<html><body style="font-family:-apple-system,Helvetica,Arial,sans-serif;color:#333;max-width:680px;margin:0 auto;padding:20px;">
<h2 style="color:#c00;">⚠️ Soumissions critiques à vérifier</h2>
<p>Bonjour Louise,</p>
<p>
  Voici les clients qui ont un RV dans les 7 prochains jours <strong>et</strong>
  une ou plusieurs soumissions critiques dont on n'a pas confirmé si les
  travaux ont été faits. À toi de décider si tu les rappelles pour vérifier
  ou si on laisse le tech soulever la question sur place.
</p>
<p style="color:#666;font-size:13px;">
  Généré le {today_str} — {total_clients} client(s), {total_items} soumission(s).
</p>
<table style="width:100%;border-collapse:collapse;margin-top:15px;">
  <thead>
    <tr style="background:#f5f5f5;">
      <th style="text-align:left;padding:10px 8px;border-bottom:2px solid #ccc;">Client / RV</th>
      <th style="text-align:left;padding:10px 8px;border-bottom:2px solid #ccc;">Soumission</th>
    </tr>
  </thead>
  <tbody>{rows}</tbody>
</table>
<p style="color:#666;font-size:12px;margin-top:20px;">
  <em>Une soumission est considérée « critique » si son total est ≥ 500 $ ou si
  elle contient des travaux majeurs (pivotage, marteaux, cordes, sommier, mortaises,
  étouffoirs, restauration, etc.). On notifie une fois par (client, soumission)
  tous les 7 jours maximum.</em>
</p>
</body></html>"""


async def run_critical_estimate_digest() -> Dict:
    """Entry point appelée par le scheduler. Retourne un rapport.

    Retourne :
        {
            "success": bool,
            "clients_checked": int,
            "critical_found": int,
            "after_dedup": int,
            "email_sent": bool,
            "error": Optional[str],
        }
    """
    storage = SupabaseStorage(silent=True)
    service = NarrativeBriefingService()

    today = date_type.today()
    today_str = today.strftime("%Y-%m-%d")

    # 1. RV à venir
    appts = _fetch_upcoming_appointments(storage, DAYS_AHEAD)
    if not appts:
        print(f"📭 Aucun RV actif dans les {DAYS_AHEAD} prochains jours")
        return {
            "success": True,
            "clients_checked": 0,
            "critical_found": 0,
            "after_dedup": 0,
            "email_sent": False,
        }

    # 2. Client names
    client_ids = list({a.get("client_external_id") for a in appts if a.get("client_external_id")})
    client_info = _fetch_client_info(storage, client_ids)

    # 3. Pour chaque client, fetch les soumissions Gazelle live
    estimates_by_client = service._batch_fetch_gazelle_estimates(client_ids)

    # 4. Construire la liste des items à notifier
    to_notify = []
    total_critical_found = 0
    for appt in appts:
        cid = appt.get("client_external_id")
        if not cid:
            continue
        ests = estimates_by_client.get(cid, [])
        criticals = [e for e in ests if e.get("is_critical")]
        if not criticals:
            continue
        total_critical_found += len(criticals)

        # Filtrer celles déjà notifiées récemment
        fresh = [
            e for e in criticals
            if not _already_notified_recently(storage, cid, e.get("number"))
        ]
        if not fresh:
            continue

        # Composer client_name
        c_info = client_info.get(cid, {})
        client_name = (
            c_info.get("company_name")
            or f"{c_info.get('first_name', '')} {c_info.get('last_name', '')}".strip()
            or "Client inconnu"
        )

        # Technicien — mapping id→nom
        tech_id = appt.get("technicien") or ""
        tech_name_map = {
            "usr_ofYggsCDt2JAVeNP": "Allan Sutton",
            "usr_HcCiFk7o0vZ9xAI0": "Nicolas Lessard",
            "usr_ReUSmIJmBF86ilY1": "Jean-Philippe Reny",
            "usr_bbt59aCUqUaDWA8n": "Margot Charignon",
        }
        tech_name = tech_name_map.get(tech_id, tech_id[:12] if tech_id else "?")

        to_notify.append({
            "client_id": cid,
            "client_name": client_name,
            "appointment_date": appt.get("appointment_date"),
            "appointment_time": (appt.get("appointment_time") or "")[:5],
            "appointment_id": appt.get("external_id"),
            "technician_name": tech_name,
            "critical_estimates": fresh,
        })

    after_dedup = sum(len(it["critical_estimates"]) for it in to_notify)
    print(f"📊 {len(appts)} RV scannés, {total_critical_found} soumissions critiques trouvées, "
          f"{after_dedup} après déduplication")

    if not to_notify:
        return {
            "success": True,
            "clients_checked": len(client_ids),
            "critical_found": total_critical_found,
            "after_dedup": 0,
            "email_sent": False,
        }

    # 5. Envoyer l'email digest
    html = _build_html_body(to_notify, today_str)
    plain = (
        f"Digest quotidien des soumissions critiques à vérifier.\n\n"
        f"{len(to_notify)} client(s), {after_dedup} soumission(s).\n"
        f"Détails dans la version HTML de l'email."
    )

    notifier = EmailNotifier()
    recipients = []
    louise = os.getenv("EMAIL_LOUISE") or "info@piano-tek.com"
    recipients.append(louise)
    allan = os.getenv("EMAIL_ALLAN") or "asutton@piano-tek.com"
    if allan and allan != louise:
        recipients.append(allan)

    subject = f"⚠️ {len(to_notify)} soumission(s) critique(s) à vérifier"
    sent = notifier.send_email(
        to_emails=recipients,
        subject=subject,
        html_content=html,
        plain_content=plain,
    )

    if sent:
        # 6. Logger chaque notification pour déduplication future
        for it in to_notify:
            for est in it["critical_estimates"]:
                _record_notification(
                    storage,
                    it["client_id"],
                    est.get("number"),
                    it.get("appointment_id"),
                    est,
                )
        print(f"✅ Email envoyé à {recipients}")
    else:
        print(f"❌ Envoi email échoué")

    return {
        "success": True,
        "clients_checked": len(client_ids),
        "critical_found": total_critical_found,
        "after_dedup": after_dedup,
        "email_sent": sent,
    }
