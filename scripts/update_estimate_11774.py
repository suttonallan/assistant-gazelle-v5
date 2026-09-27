#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Met a jour la soumission #11774 (Genevieve Cotton, Wagner G-175) :
remplace le poste 'tetes de marteaux' (2600$) par l'assemblage complet des
marteaux aligne sur les soumissions recentes (#11941) a 3800$.

updateEstimate REMPLACE tous les tiers -> on reconstruit fidelement la structure
et on n'echange que le poste marteaux. Taxes par poste (TPS+TVQ).

Usage :
  python scripts/update_estimate_11774.py            # APERCU (rien ecrit)
  python scripts/update_estimate_11774.py --execute  # pousse
"""
import sys
import argparse
import re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.gazelle_api_client import GazelleAPIClient  # noqa: E402

NUMBER = 11774
EXPECT_CLIENT = "cli_rkeekEA9hQPFoOIe"     # Genevieve Cotton
EXPECT_PIANO_MAKE = "Wagner"

TPS_TAX_ID, TPS_RATE = "tax_JeCfY4wfbXtN6J28", 5000
TVQ_TAX_ID, TVQ_RATE = "tax_xe9FEApq94zI7kXD", 9975

# Nouveau poste, copie exacte de #11941 (assemblage complet, piano a queue)
NEW_ITEM = {
    "name": "Assemblage complet des marteaux (Abel, manches bambou)",
    "amount": 380000,
    "masterServiceItemId": "mit_bHJzHuiI28Gz6EqF",
    "description": (
        "Inclut pour votre piano :\n\n"
        "  • Retrait de l'ancien assemblage des marteaux\n"
        "  • Pose de manches neufs en bambou (écologique, plus stable que le bois traditionnel)\n"
        "  • Pose de têtes Abel (feutre naturel)\n"
        "  • Pose de rouleaux neufs\n"
        "  • Ajustement de l'ensemble au gabarit du piano\n"
        "  • Alignement des marteaux aux cordes\n"
        "  • Harmonisation initiale pour équilibrer le timbre\n"
        "  • Accord final après remplacement\n"
        "  • Réglages de suivi après l'installation (feutres rodés)"
    ),
}

FULL_QUERY = """
query($s:String!){ allEstimates(first:5, filters:{search:$s}){ nodes{
  number id notes
  client{ id defaultContact{ firstName lastName } }
  piano{ id make model }
  allEstimateTiers{ sequenceNumber isPrimary notes allowSelfSchedule targetPerformanceLevel
    allEstimateTierGroups{ name sequenceNumber
      allEstimateTierItems{ id name sequenceNumber amount quantity duration type isTaxable isTuning description educationDescription masterServiceItem{ id } } }
    allUngroupedEstimateTierItems{ id name sequenceNumber amount quantity duration type isTaxable isTuning description educationDescription masterServiceItem{ id } } } }}}
"""


def build_taxes(amount, is_taxable):
    if not is_taxable or not amount:
        return []
    return [
        {"taxId": TPS_TAX_ID, "rate": TPS_RATE, "total": round(amount * TPS_RATE / 100000)},
        {"taxId": TVQ_TAX_ID, "rate": TVQ_RATE, "total": round(amount * TVQ_RATE / 100000)},
    ]


def item_input(it):
    """Echo fidele d'un item ; swap si c'est le poste marteaux."""
    is_marteaux = "marteau" in (it.get("name") or "").lower()
    name = NEW_ITEM["name"] if is_marteaux else it.get("name", "")
    amount = NEW_ITEM["amount"] if is_marteaux else it.get("amount", 0)
    desc = NEW_ITEM["description"] if is_marteaux else it.get("description")
    msi = NEW_ITEM["masterServiceItemId"] if is_marteaux else ((it.get("masterServiceItem") or {}).get("id"))
    out = {
        "name": name,
        "sequenceNumber": it.get("sequenceNumber", 0),
        "amount": amount,
        "quantity": it.get("quantity", 100),
        "duration": it.get("duration") or 0,
        "type": it.get("type", "LABOR_FIXED_RATE"),
        "isTaxable": it.get("isTaxable", True),
        "isTuning": it.get("isTuning", False),
        "photos": [],
        "taxes": build_taxes(amount, it.get("isTaxable", True)),
    }
    if desc is not None:
        out["description"] = desc
    if it.get("educationDescription") is not None:
        out["educationDescription"] = it["educationDescription"]
    if msi:
        out["masterServiceItemId"] = msi
    return out, is_marteaux


def build_tiers(est):
    tiers, swapped = [], 0
    for t in est["allEstimateTiers"]:
        ti = {
            "sequenceNumber": t.get("sequenceNumber", 0),
            "isPrimary": t.get("isPrimary", True),
            "notes": t.get("notes"),
            "allowSelfSchedule": t.get("allowSelfSchedule", False),
            "estimateTierGroups": [],
            "ungroupedEstimateTierItems": [],
        }
        if t.get("targetPerformanceLevel") is not None:
            ti["targetPerformanceLevel"] = t["targetPerformanceLevel"]
        for g in t.get("allEstimateTierGroups", []):
            gi = {"name": g.get("name", ""), "sequenceNumber": g.get("sequenceNumber", 0), "estimateTierItems": []}
            for it in g.get("allEstimateTierItems", []):
                inp, sw = item_input(it)
                swapped += sw
                gi["estimateTierItems"].append(inp)
            ti["estimateTierGroups"].append(gi)
        for it in t.get("allUngroupedEstimateTierItems", []):
            inp, sw = item_input(it)
            swapped += sw
            ti["ungroupedEstimateTierItems"].append(inp)
        tiers.append(ti)
    return tiers, swapped


def audit(tiers):
    """Garde-fous : pas de 'depose', pas de signature, pas d'emoji."""
    problems = []
    blob = ""
    for t in tiers:
        items = list(t["ungroupedEstimateTierItems"])
        for g in t["estimateTierGroups"]:
            items += g["estimateTierItems"]
        for it in items:
            blob += (it.get("name", "") + " " + (it.get("description") or "")) + "\n"
    if re.search(r"d[ée]pose", blob, re.I):
        problems.append("contient 'depose' (utiliser 'retrait')")
    if re.search(r"piano[ -]?tek|piano tek musique|— Piano", blob, re.I):
        problems.append("contient une signature")
    if re.search(r"[\U0001F300-\U0001FAFF✀-➿]", blob):
        problems.append("contient un emoji")
    return problems


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--execute", action="store_true")
    args = ap.parse_args()
    dry = not args.execute

    g = GazelleAPIClient()
    r = g._execute_query(FULL_QUERY, {"s": str(NUMBER)})
    est = next((n for n in (r.get("data", {}).get("allEstimates", {}) or {}).get("nodes", [])
                if n.get("number") == NUMBER), None)
    if not est:
        print("Soumission introuvable."); return

    cl = (est.get("client") or {})
    ct = cl.get("defaultContact") or {}
    pi = est.get("piano") or {}
    print(f"#{NUMBER}  id={est['id']}")
    print(f"Client : {ct.get('firstName','')} {ct.get('lastName','')}  ({cl.get('id')})")
    print(f"Piano  : {pi.get('make','')} {pi.get('model','')}  ({pi.get('id')})")

    # Garde-fou identite
    if cl.get("id") != EXPECT_CLIENT or EXPECT_PIANO_MAKE.lower() not in (pi.get("make", "").lower()):
        print(f"\nARRET : client/piano ne correspond pas a l'attendu ({EXPECT_CLIENT} / {EXPECT_PIANO_MAKE}). Rien fait.")
        return

    tiers, swapped = build_tiers(est)
    if swapped != 1:
        print(f"\nARRET : {swapped} poste(s) marteaux trouve(s) (attendu 1). Verifie a la main. Rien fait.")
        return

    problems = audit(tiers)
    print("\nAUDIT :", "OK" if not problems else "PROBLEMES -> " + "; ".join(problems))
    if problems:
        print("ARRET : audit echoue. Rien fait.")
        return

    sub = NEW_ITEM["amount"]
    tps = round(sub * TPS_RATE / 100000)
    tvq = round(sub * TVQ_RATE / 100000)
    print("\n--- APRES MISE A JOUR ---")
    print(f"  Poste : {NEW_ITEM['name']}")
    print(f"  Sous-total : {sub/100:.2f}$  | TPS {tps/100:.2f}$  | TVQ {tvq/100:.2f}$  | TOTAL {(sub+tps+tvq)/100:.2f}$")
    print(f"  (avant : tetes de marteaux 2600.00$ + taxes = 2989.35$)")

    if dry:
        print("\n[APERCU] rien ecrit. Relancer avec --execute pour pousser.")
        return

    res = g.update_estimate(est["id"], {"estimateTiers": tiers})
    new_total = max((t.get("total", 0) for t in res.get("allEstimateTiers", [])), default=0)
    print(f"\nMIS A JOUR. Nouveau total Gazelle : {new_total/100:.2f}$")


if __name__ == "__main__":
    main()
