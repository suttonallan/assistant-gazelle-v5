"""Duplication de factures et de soumissions Gazelle pour l'assistant.

Règle de sécurité (constitution PTM) :
- Les factures dupliquées sont créées en statut DRAFT — jamais envoyées.
- Créer une soumission n'envoie rien au client (objet brouillon par nature).
- Le seul geste irréversible (l'envoi) reste à l'utilisateur dans Gazelle.

Découverte du 2026-07-29 : Gazelle expose createInvoice / createEstimate
(type PrivateMutation). Échelles : quantity ×100, amount en cents,
tax rate ×1000. Voir mémoire reference-gazelle-invoice-api.
"""

import re
from datetime import date, timedelta
from typing import Any, Dict, List, Optional


def _gz():
    from core.gazelle_api_client import GazelleAPIClient
    return GazelleAPIClient()


# ─────────────────────────────────────────────────────────────────────
# Extraction des paramètres depuis le langage naturel (déterministe)
# ─────────────────────────────────────────────────────────────────────

_MOIS = {
    'janvier': 1, 'février': 2, 'fevrier': 2, 'mars': 3, 'avril': 4, 'mai': 5,
    'juin': 6, 'juillet': 7, 'août': 8, 'aout': 8, 'septembre': 9,
    'octobre': 10, 'novembre': 11, 'décembre': 12, 'decembre': 12,
}


def extract_doc_number(text: str) -> Optional[int]:
    """Numéro de document (facture/soumission) = premier entier de 4 à 6 chiffres.

    Évite de capter un jour (« 7 août ») ou un diapason (« 440 »).
    """
    if not text:
        return None
    m = re.search(r'#?\b(\d{4,6})\b', text)
    return int(m.group(1)) if m else None


def parse_due_date(text: str, today: Optional[date] = None) -> Optional[str]:
    """Extrait une date d'échéance et la retourne en ISO 'YYYY-MM-DD', sinon None.

    Gère : '2026-08-07', '7 août', 'le 7 août 2026', '7 aout'.
    Sans année : prend l'année courante, ou la suivante si la date est
    déjà passée de plus de 30 jours (échéance = future).
    """
    if not text:
        return None
    t = text.lower()
    m = re.search(r'(\d{4})-(\d{2})-(\d{2})', t)
    if m:
        return m.group(0)
    mois_alt = '|'.join(_MOIS.keys())
    m = re.search(r'(\d{1,2})\s+(' + mois_alt + r')(?:\s+(\d{4}))?', t)
    if not m:
        return None
    today = today or date.today()
    day = int(m.group(1))
    month = _MOIS[m.group(2)]
    year = int(m.group(3)) if m.group(3) else today.year
    try:
        cand = date(year, month, day)
    except ValueError:
        return None
    if not m.group(3) and (cand - today).days < -30:
        try:
            cand = date(year + 1, month, day)
        except ValueError:
            pass
    return cand.isoformat()


# ─────────────────────────────────────────────────────────────────────
# FACTURES
# ─────────────────────────────────────────────────────────────────────

_INVOICE_FETCH = """
query($s: String!) {
  allInvoices(first: 5, filters: {search: $s}) {
    nodes {
      id number status dueOn notes taxPricingMode
      client { id companyName }
      allInvoiceItems { nodes {
        description type quantity amount taxable billable sequenceNumber
        taxes { taxId name rate total }
      } }
    }
  }
}
"""

_CREATE_INVOICE = """
mutation($input: PrivateCreateInvoiceInput!) {
  createInvoice(input: $input) {
    invoice { id number status dueOn subTotal total }
    mutationErrors { fieldName messages }
  }
}
"""


def _mutation_error_detail(payload: Dict[str, Any]) -> str:
    errs = (payload or {}).get("mutationErrors") or []
    parts = [f"{e.get('fieldName')}: {', '.join(e.get('messages') or [])}" for e in errs]
    return "; ".join(p for p in parts if p) or "raison inconnue"


def duplicate_invoice(number: int, due_on: Optional[str] = None,
                      dry_run: bool = False) -> Dict[str, Any]:
    """Duplique une facture en DRAFT. `due_on` (ISO) remplace l'échéance si fourni."""
    gz = _gz()
    data = gz._execute_query(_INVOICE_FETCH, {"s": str(number)})
    nodes = (((data or {}).get("data") or {}).get("allInvoices") or {}).get("nodes") or []
    src = next((n for n in nodes if str(n.get("number")) == str(number)), None)
    if not src:
        return {"success": False, "error": f"Facture #{number} introuvable dans Gazelle."}

    items: List[Dict[str, Any]] = []
    for it in ((src.get("allInvoiceItems") or {}).get("nodes") or []):
        items.append({
            "description": it.get("description"),
            "type": it.get("type") or "LABOR_FIXED_RATE",
            "quantity": it.get("quantity"),
            "amount": it.get("amount"),
            "taxable": it.get("taxable", True),
            "billable": it.get("billable", True),
            "sequenceNumber": it.get("sequenceNumber", 0),
            "taxes": [
                {"taxId": t.get("taxId"), "name": t.get("name"),
                 "rate": t.get("rate"), "total": t.get("total")}
                for t in (it.get("taxes") or [])
            ],
        })

    client = src.get("client") or {}
    inp = {
        "clientId": client.get("id"),
        "status": "DRAFT",
        "taxPricingMode": src.get("taxPricingMode") or "EXCLUSIVE",
        "dueOn": due_on or src.get("dueOn"),
        "notes": src.get("notes"),
        "invoiceItems": items,
    }
    if dry_run:
        return {"success": True, "dry_run": True, "input": inp}

    res = gz._execute_query(_CREATE_INVOICE, {"input": inp})
    payload = ((res or {}).get("data") or {}).get("createInvoice") or {}
    inv = payload.get("invoice")
    if not inv:
        return {"success": False,
                "error": f"Gazelle a refusé la création ({_mutation_error_detail(payload)})."}
    return {
        "success": True,
        "kind": "invoice",
        "source_number": number,
        "invoice_number": inv.get("number"),
        "invoice_id": inv.get("id"),
        "status": inv.get("status"),
        "due_on": inv.get("dueOn"),
        "subtotal": round((inv.get("subTotal") or 0) / 100.0, 2),
        "total": round((inv.get("total") or 0) / 100.0, 2),
        "client_name": (client.get("companyName") or "").strip(),
    }


# ─────────────────────────────────────────────────────────────────────
# SOUMISSIONS
# ─────────────────────────────────────────────────────────────────────

_ESTIMATE_FETCH = """
query($s: String!) {
  allEstimates(first: 10, filters: {search: $s}) {
    nodes {
      id number notes estimatedOn expiresOn locale isArchived
      client { id companyName defaultContact { firstName lastName } }
      piano { id }
      allEstimateTiers {
        sequenceNumber isPrimary notes
        allEstimateTierGroups {
          name sequenceNumber
          allEstimateTierItems {
            name sequenceNumber amount quantity description isTaxable
            type isTuning masterServiceItem { id }
          }
        }
        allUngroupedEstimateTierItems {
          name sequenceNumber amount quantity description isTaxable
          type isTuning masterServiceItem { id }
        }
      }
    }
  }
}
"""

_CREATE_ESTIMATE = """
mutation($input: PrivateCreateEstimateInput!) {
  createEstimate(input: $input) {
    estimate { id number }
    mutationErrors { fieldName messages }
  }
}
"""


def _estimate_item_input(it: Dict[str, Any]) -> Dict[str, Any]:
    r = {
        "name": it.get("name"),
        "description": it.get("description"),
        "quantity": it.get("quantity"),
        "amount": it.get("amount"),
        "type": it.get("type") or "LABOR_FIXED_RATE",
        "isTaxable": it.get("isTaxable", True),
        "isTuning": it.get("isTuning", False),
        "sequenceNumber": it.get("sequenceNumber", 0),
    }
    msi = it.get("masterServiceItem") or {}
    if msi.get("id"):
        r["masterServiceItemId"] = msi["id"]
    return r


def duplicate_estimate(number: int, dry_run: bool = False,
                       archived: bool = False) -> Dict[str, Any]:
    """Copie une soumission (tiers/groupes/items) en une nouvelle soumission.

    Date d'émission = aujourd'hui, expiration = +30 jours. Rien n'est envoyé.
    `archived=True` crée la copie archivée (utile pour un test).
    """
    gz = _gz()
    data = gz._execute_query(_ESTIMATE_FETCH, {"s": str(number)})
    nodes = (((data or {}).get("data") or {}).get("allEstimates") or {}).get("nodes") or []
    src = next((n for n in nodes if str(n.get("number")) == str(number)), None)
    if not src:
        return {"success": False, "error": f"Soumission #{number} introuvable dans Gazelle."}

    client = src.get("client") or {}
    piano = src.get("piano") or {}
    if not piano.get("id"):
        return {"success": False,
                "error": f"Soumission #{number} sans piano associé — copie impossible (pianoId requis)."}

    tiers: List[Dict[str, Any]] = []
    for t in (src.get("allEstimateTiers") or []):
        groups = []
        for grp in (t.get("allEstimateTierGroups") or []):
            groups.append({
                "name": grp.get("name"),
                "sequenceNumber": grp.get("sequenceNumber", 0),
                "estimateTierItems": [_estimate_item_input(i)
                                      for i in (grp.get("allEstimateTierItems") or [])],
            })
        tiers.append({
            "sequenceNumber": t.get("sequenceNumber", 0),
            "isPrimary": t.get("isPrimary", False),
            "notes": t.get("notes"),
            "estimateTierGroups": groups,
            "ungroupedEstimateTierItems": [_estimate_item_input(i)
                                           for i in (t.get("allUngroupedEstimateTierItems") or [])],
        })

    today = date.today()
    inp = {
        "clientId": client.get("id"),
        "pianoId": piano.get("id"),
        "notes": src.get("notes"),
        "locale": src.get("locale") or "fr",
        "estimatedOn": today.isoformat(),
        "expiresOn": (today + timedelta(days=30)).isoformat(),
        "estimateTiers": tiers,
    }
    if archived:
        inp["isArchived"] = True
    if dry_run:
        return {"success": True, "dry_run": True, "input": inp}

    res = gz._execute_query(_CREATE_ESTIMATE, {"input": inp})
    payload = ((res or {}).get("data") or {}).get("createEstimate") or {}
    est = payload.get("estimate")
    if not est:
        return {"success": False,
                "error": f"Gazelle a refusé la création ({_mutation_error_detail(payload)})."}
    dc = client.get("defaultContact") or {}
    client_name = (client.get("companyName") or "").strip() or \
        " ".join(x for x in [dc.get("firstName"), dc.get("lastName")] if x).strip()
    return {
        "success": True,
        "kind": "estimate",
        "source_number": number,
        "estimate_number": est.get("number"),
        "estimate_id": est.get("id"),
        "client_name": client_name,
    }
