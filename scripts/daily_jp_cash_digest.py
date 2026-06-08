#!/usr/bin/env python3
"""Daily digest 18h Montreal — paiements cash assignes a Jean-Philippe ou Margot.

Interroge Gazelle pour les factures ou :
  - assignedTo = JP Reny OU Margot Charignon
  - un paiement de type CASH existe
  - paymentDate = aujourd'hui (date Montreal)

Si >=1 facture trouvee, envoie un email resume a info@piano-tek.com (capte par Front),
avec la colonne Technicien pour savoir qui a recu le cash. Si 0, sort silencieusement.

Execution : tous les jours a 18h Montreal via GitHub Actions
(cron 22+23 UTC, script gate par heure locale pour gerer EST/EDT).
"""
import os
import sys
from pathlib import Path
from datetime import datetime
import pytz

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.gazelle_api_client import GazelleAPIClient  # noqa: E402
from core.email_notifier import get_email_notifier    # noqa: E402

# Techniciens dont le cash recu doit etre signale a info@ (facture a leur nom).
CASH_TECHS = {
    "usr_ReUSmIJmBF86ilY1": "Jean-Philippe Reny",
    "usr_bbt59aCUqUaDWA8n": "Margot Charignon",
}
RECIPIENT = "info@piano-tek.com"
MTL_TZ = pytz.timezone("America/Montreal")

INVOICES_QUERY = """
query DailyCash($filters: PrivateAllInvoicesFilter) {
  allInvoices(filters: $filters) {
    nodes {
      id
      number
      status
      total
      subTotal
      taxTotal
      client {
        id
        companyName
        defaultContact {
          firstName
          lastName
          defaultPhone { phoneNumber }
        }
      }
      assignedTo { id firstName lastName }
      allInvoicePayments {
        nodes { id type amount paidAt notes }
      }
    }
  }
}
"""


def format_amount(cents: int) -> str:
    return f"{cents/100:,.2f} $".replace(",", " ")


def client_label(invoice: dict) -> str:
    client = invoice.get("client") or {}
    if client.get("companyName"):
        return client["companyName"]
    contact = client.get("defaultContact") or {}
    parts = [contact.get("firstName"), contact.get("lastName")]
    name = " ".join(p for p in parts if p)
    return name or "Client inconnu"


def tech_label(invoice: dict) -> str:
    assigned = invoice.get("assignedTo") or {}
    name = CASH_TECHS.get(assigned.get("id"))
    if name:
        return name
    return " ".join(p for p in [assigned.get("firstName"), assigned.get("lastName")] if p) or "?"


def fetch_invoices(date_str: str) -> list[dict]:
    client = GazelleAPIClient()
    r = client._execute_query(
        INVOICES_QUERY,
        variables={
            "filters": {
                "assignedTo": list(CASH_TECHS.keys()),
                "paymentMethods": {"invoicePaymentType": ["CASH"]},
                "paymentDateGet": date_str,
                "paymentDateLet": date_str,
            }
        },
    )
    return (r.get("data", {}).get("allInvoices") or {}).get("nodes", []) or []


def _cash_total(inv: dict) -> int:
    return sum(p["amount"] for p in (inv.get("allInvoicePayments") or {}).get("nodes", [])
               if p.get("type") == "CASH")


def build_html(invoices: list[dict], date_str: str) -> str:
    rows = []
    total_cash = 0
    for inv in invoices:
        cash_payments = [p for p in (inv.get("allInvoicePayments") or {}).get("nodes", [])
                         if p.get("type") == "CASH"]
        cash_total = sum(p["amount"] for p in cash_payments)
        total_cash += cash_total
        paid_times = ", ".join(
            (datetime.fromisoformat(p["paidAt"].replace("Z", "+00:00"))
             .astimezone(MTL_TZ).strftime("%H:%M"))
            for p in cash_payments if p.get("paidAt")
        )
        rows.append(f"""
          <tr>
            <td style="padding:8px;border-bottom:1px solid #eee;"><strong>{tech_label(inv)}</strong></td>
            <td style="padding:8px;border-bottom:1px solid #eee;">#{inv['number']}</td>
            <td style="padding:8px;border-bottom:1px solid #eee;">{client_label(inv)}</td>
            <td style="padding:8px;border-bottom:1px solid #eee;text-align:right;">{format_amount(cash_total)}</td>
            <td style="padding:8px;border-bottom:1px solid #eee;color:#666;">{paid_times}</td>
            <td style="padding:8px;border-bottom:1px solid #eee;">{inv['status']}</td>
          </tr>
        """)
    n = len(invoices)
    plural = "s" if n > 1 else ""
    return f"""<html>
<body style="font-family:-apple-system,BlinkMacSystemFont,sans-serif;line-height:1.5;color:#111;">
  <div style="background:#fff8e1;border-left:4px solid #f59e0b;padding:16px;border-radius:6px;">
    <h2 style="margin:0 0 8px 0;">Digest cash recu (JP / Margot)</h2>
    <p style="margin:0;color:#666;">{date_str} - {n} facture{plural} payee{plural} en argent comptant</p>
  </div>
  <table style="border-collapse:collapse;width:100%;margin-top:20px;">
    <thead>
      <tr style="background:#f5f5f5;">
        <th style="padding:8px;text-align:left;">Technicien</th>
        <th style="padding:8px;text-align:left;">Facture</th>
        <th style="padding:8px;text-align:left;">Client</th>
        <th style="padding:8px;text-align:right;">Montant cash</th>
        <th style="padding:8px;text-align:left;">Heure paiement</th>
        <th style="padding:8px;text-align:left;">Statut</th>
      </tr>
    </thead>
    <tbody>
      {''.join(rows)}
      <tr style="background:#fffbeb;font-weight:bold;">
        <td colspan="3" style="padding:10px;">TOTAL CASH</td>
        <td style="padding:10px;text-align:right;">{format_amount(total_cash)}</td>
        <td colspan="2"></td>
      </tr>
    </tbody>
  </table>
  <p style="color:#888;font-size:12px;margin-top:20px;">
    Digest genere automatiquement a 18h Montreal - scripts/daily_jp_cash_digest.py
  </p>
</body>
</html>"""


def build_text(invoices: list[dict], date_str: str) -> str:
    lines = [f"Digest cash recu (JP / Margot) - {date_str}", "",
             f"{len(invoices)} facture(s) payee(s) en argent comptant aujourd'hui :", ""]
    total = 0
    for inv in invoices:
        cash_total = _cash_total(inv)
        total += cash_total
        lines.append(f"  {tech_label(inv)} - #{inv['number']} - {client_label(inv)} - {format_amount(cash_total)} ({inv['status']})")
    lines.append("")
    lines.append(f"TOTAL CASH : {format_amount(total)}")
    return "\n".join(lines)


def main() -> int:
    now_mtl = datetime.now(MTL_TZ)
    today_str = os.getenv("TARGET_DATE") or now_mtl.date().isoformat()
    current_hour = now_mtl.hour
    skip_hour_gate = os.getenv("SKIP_HOUR_GATE", "").lower() in ("1", "true", "yes")
    dry_run = os.getenv("DRY_RUN", "").lower() in ("1", "true", "yes")

    print(f"Heure Montreal : {now_mtl.strftime('%Y-%m-%d %H:%M %Z')}")
    print(f"Date cible : {today_str}")

    if not skip_hour_gate and current_hour != 18:
        print(f"Pas 18h Montreal (actuel: {current_hour}h), digest ignore")
        return 0

    print(f"Requete Gazelle : factures cash assignees a JP/Margot, payees aujourd'hui")
    invoices = fetch_invoices(today_str)
    print(f"   -> {len(invoices)} facture(s) trouvee(s)")

    if not invoices:
        print("Rien a signaler - digest non envoye")
        return 0

    html = build_html(invoices, today_str)
    text = build_text(invoices, today_str)
    subject = f"Digest cash JP/Margot - {len(invoices)} paiement(s) le {today_str}"

    if dry_run:
        print("\n--- DRY RUN ---")
        print(f"A : {RECIPIENT}")
        print(f"Sujet : {subject}")
        print()
        print(text)
        return 0

    notifier = get_email_notifier()
    ok = notifier.send_email(
        to_emails=[RECIPIENT],
        subject=subject,
        html_content=html,
        plain_content=text,
    )
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
