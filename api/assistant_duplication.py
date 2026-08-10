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
            type isTuning duration educationDescription masterServiceItem { id }
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

# Catalogue Gazelle : source de vérité du prix courant de chaque service.
_MSL_PRICE_QUERY = "query { allMasterServiceItems { id amount } }"


def _fetch_msl_prices(gz) -> Dict[str, Any]:
    """Retourne {masterServiceItemId: prix_courant_cents} depuis le catalogue."""
    data = gz._execute_query(_MSL_PRICE_QUERY)
    items = (((data or {}).get("data") or {}).get("allMasterServiceItems") or [])
    return {it["id"]: it.get("amount") for it in items if it.get("id")}


# Taxes Québec. Validé empiriquement sur #11983 (2026-08-10) :
#  - OMETTRE `taxes` -> 0 $ de taxe.
#  - Envoyer `taxes` SANS le champ `name` -> Gazelle jette les lignes par item :
#    le total se calcule mais les cases TPS/TVQ restent DÉCOCHÉES dans l'UI.
#  - Il faut envoyer chaque taxe avec `name` ("tps"/"tvq") comme dans une
#    soumission native (#11766), et créer en 2 étapes (createEstimate minimal
#    puis updateEstimate) — sinon le calcul des taxes ne se déclenche pas.
_TPS_TAX_ID, _TPS_NAME, _TPS_RATE = "tax_JeCfY4wfbXtN6J28", "tps", 5000   # 5,000 %
_TVQ_TAX_ID, _TVQ_NAME, _TVQ_RATE = "tax_xe9FEApq94zI7kXD", "tvq", 9975   # 9,975 %


def _build_taxes(amount_cents, is_taxable) -> List[Dict[str, Any]]:
    """Bloc TPS+TVQ (avec `name`, requis pour cocher les cases) ; [] sinon."""
    if not is_taxable or not amount_cents:
        return []
    return [
        {"taxId": _TPS_TAX_ID, "name": _TPS_NAME, "rate": _TPS_RATE,
         "total": round(amount_cents * _TPS_RATE / 100000)},
        {"taxId": _TVQ_TAX_ID, "name": _TVQ_NAME, "rate": _TVQ_RATE,
         "total": round(amount_cents * _TVQ_RATE / 100000)},
    ]


def _estimate_item_input(it: Dict[str, Any],
                         catalog: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Construit l'input d'un item. Si `catalog` est fourni (mode reprice), le
    montant est remplacé par le prix courant du MasterServiceItem lié ; les
    lignes sans MSL (custom) gardent leur montant d'origine."""
    amount = it.get("amount")
    msi = it.get("masterServiceItem") or {}
    msi_id = msi.get("id")
    # Reprice AVANT le calcul des taxes (les taxes portent sur le montant final).
    if msi_id and catalog is not None:
        current = catalog.get(msi_id)
        if current is not None:
            amount = current
    is_taxable = it.get("isTaxable", True)
    r = {
        "name": it.get("name"),
        "quantity": it.get("quantity"),
        "amount": amount,
        "duration": it.get("duration") or 0,
        "type": it.get("type") or "LABOR_FIXED_RATE",
        "isTaxable": is_taxable,
        "isTuning": it.get("isTuning", False),
        "sequenceNumber": it.get("sequenceNumber", 0),
        "photos": [],
        "taxes": _build_taxes(amount, is_taxable),
    }
    if it.get("description") is not None:
        r["description"] = it["description"]
    if it.get("educationDescription") is not None:
        r["educationDescription"] = it["educationDescription"]
    if msi_id:
        r["masterServiceItemId"] = msi_id
    return r


def _reprice_changes(src: Dict[str, Any], catalog: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Liste les lignes dont le prix change au tarif courant (pour le rapport)."""
    changes = []
    for t in (src.get("allEstimateTiers") or []):
        grouped = [i for grp in (t.get("allEstimateTierGroups") or [])
                   for i in (grp.get("allEstimateTierItems") or [])]
        for i in grouped + (t.get("allUngroupedEstimateTierItems") or []):
            msi = (i.get("masterServiceItem") or {}).get("id")
            old = i.get("amount") or 0
            new = catalog.get(msi) if msi else None
            if new is not None and new != old:
                changes.append({"name": i.get("name"), "old_cents": old, "new_cents": new})
    return changes


def duplicate_estimate(number: int, dry_run: bool = False,
                       archived: bool = False, reprice: bool = False) -> Dict[str, Any]:
    """Copie une soumission (tiers/groupes/items) en une nouvelle soumission.

    Date d'émission = aujourd'hui, expiration = +30 jours. Rien n'est envoyé.
    `archived=True` crée la copie archivée (utile pour un test).
    `reprice=True` remplace chaque montant par le prix courant du catalogue
    (MasterServiceItem) — pour « réactiver avec le prix à jour ». Les lignes
    custom (sans MSL) gardent leur montant d'origine.
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

    catalog = _fetch_msl_prices(gz) if reprice else None
    changes = _reprice_changes(src, catalog) if reprice else []

    tiers: List[Dict[str, Any]] = []
    for t in (src.get("allEstimateTiers") or []):
        groups = []
        for grp in (t.get("allEstimateTierGroups") or []):
            groups.append({
                "name": grp.get("name"),
                "sequenceNumber": grp.get("sequenceNumber", 0),
                "estimateTierItems": [_estimate_item_input(i, catalog)
                                      for i in (grp.get("allEstimateTierItems") or [])],
            })
        tiers.append({
            "sequenceNumber": t.get("sequenceNumber", 0),
            "isPrimary": t.get("isPrimary", False),
            "notes": t.get("notes"),
            "estimateTierGroups": groups,
            "ungroupedEstimateTierItems": [_estimate_item_input(i, catalog)
                                           for i in (t.get("allUngroupedEstimateTierItems") or [])],
        })

    today = date.today()
    # Étape 1 : createEstimate MINIMAL — jamais les tiers ici (ne déclenche pas
    # le calcul des taxes ; l'ancienne note "crash Ruby" pointe la même règle).
    create_input = {
        "clientId": client.get("id"),
        "pianoId": piano.get("id"),
        "locale": src.get("locale") or "fr",
        "estimatedOn": today.isoformat(),
        "expiresOn": (today + timedelta(days=30)).isoformat(),
    }
    if src.get("notes"):
        create_input["notes"] = src.get("notes")
    if archived:
        create_input["isArchived"] = True

    if dry_run:
        return {"success": True, "dry_run": True,
                "create_input": create_input,
                "update_input": {"estimateTiers": tiers},
                "reprice": reprice, "reprice_changes": changes}

    res = gz._execute_query(_CREATE_ESTIMATE, {"input": create_input})
    payload = ((res or {}).get("data") or {}).get("createEstimate") or {}
    est = payload.get("estimate")
    if not est:
        return {"success": False,
                "error": f"Gazelle a refusé la création ({_mutation_error_detail(payload)})."}

    # Étape 2 : updateEstimate avec les tiers complets + taxes explicites.
    gz.update_estimate(est["id"], {"estimateTiers": tiers})

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
        "reprice": reprice,
        "reprice_changes": changes,
    }
