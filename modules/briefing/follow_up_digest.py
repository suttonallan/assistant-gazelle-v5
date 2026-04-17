#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Digest quotidien 8h a info@ des soumissions actives sans relance.

Envoie chaque matin la liste des soumissions non archivees, creees il y a
7 a 90 jours, qui n'ont PAS le tag 'relance-faite' dans Gazelle.
La personne au bureau (Louise, Margot ou autre) appelle le client pour
faire le suivi, puis pose le tag 'relance-faite' sur la soumission dans
Gazelle -- elle disparait alors de la liste le lendemain.

Parametres valides par Allan le 2026-04-14 :
- Tag : relance-faite
- Fenetre : 7 a 90 jours depuis estimatedOn
- Destinataire : info@piano-tek.com (+ Allan en copie)
- Heure : 8h00 Montreal
- Deduplication : via table critical_estimate_notifications (kind='info_followup'),
  on ne re-notifie pas le meme (client, estimate) dans les 7 jours
"""

import os
from datetime import datetime, timedelta, date as date_type
from typing import Dict, List, Optional

import requests as http_requests

from core.supabase_storage import SupabaseStorage
from core.email_notifier import EmailNotifier


DEDUP_WINDOW_DAYS = 7
TAG_DONE = "relance-faite"


def _already_notified(storage, client_id, estimate_number):
    cutoff = (datetime.now() - timedelta(days=DEDUP_WINDOW_DAYS)).isoformat()
    url = (
        f"{storage.api_url}/critical_estimate_notifications"
        f"?kind=eq.info_followup"
        f"&client_external_id=eq.{client_id}"
        f"&estimate_number=eq.{estimate_number}"
        f"&sent_at=gte.{cutoff}"
        f"&select=id&limit=1"
    )
    try:
        r = http_requests.get(url, headers=storage._get_headers(), timeout=10)
        return r.status_code == 200 and len(r.json()) > 0
    except Exception:
        return False


def _record_notification(storage, client_id, estimate_number, estimate_summary):
    row = {
        "kind": "info_followup",
        "client_external_id": client_id,
        "estimate_number": estimate_number,
        "estimate_total_cents": estimate_summary.get("total_cents", 0),
        "estimate_date": estimate_summary.get("estimated_on"),
        "estimate_is_archived": False,
        "sent_at": datetime.now().isoformat(),
    }
    url = f"{storage.api_url}/critical_estimate_notifications"
    try:
        headers = {**storage._get_headers(), "Prefer": "return=minimal"}
        http_requests.post(url, headers=headers, json=row, timeout=10)
    except Exception as exc:
        print(f"  Log dedup echoue: {exc}")


def _build_html(items, today_str):
    rows = []
    for it in items:
        est = it["estimate"]
        main_items = est.get("main_items") or []
        items_str = " + ".join(main_items[:3]) if main_items else ""
        rows.append(
            f"<tr>"
            f"<td style='padding:10px 8px;border-bottom:1px solid #eee;'>"
            f"<strong>{it['client_name']}</strong></td>"
            f"<td style='padding:10px 8px;border-bottom:1px solid #eee;'>"
            f"#{est.get('number','?')}</td>"
            f"<td style='padding:10px 8px;border-bottom:1px solid #eee;'>"
            f"{est.get('estimated_on','?')}</td>"
            f"<td style='padding:10px 8px;border-bottom:1px solid #eee;'>"
            f"<strong>{est.get('total_dollars','?')} $</strong></td>"
            f"<td style='padding:10px 8px;border-bottom:1px solid #eee;'>"
            f"{items_str}</td>"
            f"</tr>"
        )
    rows_html = "\n".join(rows)
    return f"""<!DOCTYPE html>
<html><body style="font-family:-apple-system,Helvetica,Arial,sans-serif;color:#333;max-width:720px;margin:0 auto;padding:20px;">
<h2 style="color:#2d5a87;">Soumissions en attente de suivi</h2>
<p>Bonjour,</p>
<p>
  Voici les soumissions envoy\u00e9es il y a plus de 7 jours qui n'ont pas encore
  eu de suivi. Appelez le client pour v\u00e9rifier s'il a des questions ou s'il
  souhaite aller de l'avant.
</p>
<p style="color:#666;font-size:13px;">
  Une fois le suivi fait, ajoutez le tag <strong>relance-faite</strong> sur la
  soumission dans Gazelle pour qu'elle disparaisse de cette liste.
</p>
<p style="color:#666;font-size:13px;">G\u00e9n\u00e9r\u00e9 le {today_str} - {len(items)} soumission(s).</p>
<table style="width:100%;border-collapse:collapse;margin-top:15px;">
<thead><tr style="background:#f5f5f5;">
  <th style="text-align:left;padding:10px 8px;border-bottom:2px solid #ccc;">Client</th>
  <th style="text-align:left;padding:10px 8px;border-bottom:2px solid #ccc;">#</th>
  <th style="text-align:left;padding:10px 8px;border-bottom:2px solid #ccc;">Date</th>
  <th style="text-align:left;padding:10px 8px;border-bottom:2px solid #ccc;">Total</th>
  <th style="text-align:left;padding:10px 8px;border-bottom:2px solid #ccc;">Services</th>
</tr></thead>
<tbody>{rows_html}</tbody>
</table>
</body></html>"""


async def run_follow_up_digest() -> Dict:
    """Entry point appelee par le scheduler a 8h."""
    storage = SupabaseStorage(silent=True)
    today = date_type.today()
    today_str = today.strftime("%Y-%m-%d")

    # Bornes
    cutoff_old = (today - timedelta(days=90)).isoformat()
    cutoff_recent = (today - timedelta(days=7)).isoformat()

    # Fetch toutes les soumissions actives (non archivees) via Gazelle live
    try:
        from core.gazelle_api_client import GazelleAPIClient
        gz = GazelleAPIClient()
    except Exception as exc:
        print(f"Init Gazelle echoue: {exc}")
        return {"success": False, "error": str(exc)}

    # On utilise excludeTags pour filtrer cote Gazelle directement
    query = """
    query($f: PrivateAllEstimatesFilter) {
        allEstimates(first: 200, filters: $f) {
            nodes {
                id number estimatedOn recommendedTierTotal tags
                client { id defaultContact { firstName lastName } companyName }
                allEstimateTiers {
                    isPrimary
                    allEstimateTierGroups {
                        allEstimateTierItems { name amount }
                    }
                }
            }
        }
    }
    """
    try:
        r = gz._execute_query(query, {"f": {
            "archived": False,
            "excludeTags": [TAG_DONE],
        }})
    except Exception as exc:
        print(f"Query Gazelle echoue: {exc}")
        return {"success": False, "error": str(exc)}

    all_estimates = r.get("data", {}).get("allEstimates", {}).get("nodes", []) or []
    print(f"Fetch: {len(all_estimates)} soumissions actives sans tag '{TAG_DONE}'")

    # Filtrer par fenetre 7-90 jours
    in_window = []
    for est in all_estimates:
        est_date = (est.get("estimatedOn") or "")[:10]
        if not est_date:
            continue
        if est_date < cutoff_old or est_date > cutoff_recent:
            continue
        in_window.append(est)

    print(f"Fenetre 7-90 jours: {len(in_window)} soumissions")

    if not in_window:
        return {
            "success": True,
            "total_fetched": len(all_estimates),
            "in_window": 0,
            "after_dedup": 0,
            "email_sent": False,
        }

    # Summarize + dedup
    to_notify = []
    for est in in_window:
        number = est.get("number")
        client = est.get("client") or {}
        client_id = client.get("id")
        if not client_id or not number:
            continue

        if _already_notified(storage, client_id, number):
            continue

        # Extraire top 3 items du tier primary
        tiers = est.get("allEstimateTiers") or []
        primary = next((t for t in tiers if t.get("isPrimary")), tiers[0] if tiers else {})
        all_items = []
        for g in primary.get("allEstimateTierGroups") or []:
            for it in g.get("allEstimateTierItems") or []:
                if (it.get("amount") or 0) > 0:
                    all_items.append(it)
        all_items.sort(key=lambda i: i.get("amount", 0), reverse=True)
        top_items = [i["name"] for i in all_items[:3]]

        total_cents = est.get("recommendedTierTotal") or 0
        contact = client.get("defaultContact") or {}
        client_name = (
            client.get("companyName")
            or f"{contact.get('firstName', '')} {contact.get('lastName', '')}".strip()
            or "Client inconnu"
        )

        to_notify.append({
            "client_id": client_id,
            "client_name": client_name,
            "estimate": {
                "number": number,
                "estimated_on": (est.get("estimatedOn") or "")[:10],
                "total_cents": total_cents,
                "total_dollars": f"{total_cents/100:,.0f}".replace(",", " "),
                "main_items": top_items,
            },
        })

    after_dedup = len(to_notify)
    print(f"Apres dedup: {after_dedup} soumissions a notifier")

    if not to_notify:
        return {
            "success": True,
            "total_fetched": len(all_estimates),
            "in_window": len(in_window),
            "after_dedup": 0,
            "email_sent": False,
        }

    # Envoyer email
    html = _build_html(to_notify, today_str)
    notifier = EmailNotifier()
    recipients = [os.getenv("EMAIL_INFO", "info@piano-tek.com")]
    allan = os.getenv("EMAIL_ALLAN", "asutton@piano-tek.com")
    if allan and allan not in recipients:
        recipients.append(allan)

    subject = f"Suivi soumissions : {after_dedup} en attente de relance"
    sent = notifier.send_email(
        to_emails=recipients,
        subject=subject,
        html_content=html,
        plain_content=f"{after_dedup} soumissions en attente de suivi. Voir version HTML.",
    )

    if sent:
        for it in to_notify:
            _record_notification(storage, it["client_id"], it["estimate"]["number"], it["estimate"])
        print(f"Email envoye a {recipients}")
    else:
        print("Envoi echoue")

    return {
        "success": True,
        "total_fetched": len(all_estimates),
        "in_window": len(in_window),
        "after_dedup": after_dedup,
        "email_sent": sent,
    }
