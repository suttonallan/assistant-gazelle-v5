#!/usr/bin/env python3
"""Facture automatique des versements du contrat Vincent-d'Indy.

Contrat de prestation de service (article 7) : 4 versements égaux, échéances
1er août, 15 octobre, 15 janvier, 15 avril. Le contrat est reconduit chaque
année avec une hausse de 5 % (article 3) — les montants s'indexent seuls.

Chaque matin (GitHub Actions), le script regarde si un versement arrive à
échéance dans les 21 prochains jours (versement de janvier : déclenché le
18 décembre, avant les Fêtes). Si oui et qu'aucune facture n'existe déjà pour
ce versement dans Gazelle :
  1. il crée la facture en BROUILLON dans Gazelle (jamais envoyée) ;
  2. il écrit à Louise (info@) et Allan : la facture se synchronise dans
     QuickBooks, Louise l'envoie de là à Julio Gonzalo et à finances@emvi.qc.ca.

Idempotent : la vérification se fait dans Gazelle même, donc rien n'est créé en
double, et un jour manqué est rattrapé le lendemain.

Options : --date AAAA-MM-JJ (simuler un jour), --essai (n'écrit rien).
"""
import argparse
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

CLIENT_ID = "cli_9UMLkteep8EsISbG"          # École de musique Vincent-d'Indy
CONTACT_ID = "con_KmsWlmBgVcsZACb5"          # contact des factures du contrat
ASSIGNE_A = "usr_ofYggsCDt2JAVeNP"           # Allan
DESTINATAIRES = ["info@piano-tek.com", "asutton@piano-tek.com"]
NOTES = ("TPS:   717203723 RT0001\r\nTVQ:   1224695230TQ0001\r\n"
         "Pour un paiement par virement Interac: info@infopiano.com\r\n\r\nMerci !")

# Montants annuels du contrat 2026-2027 (cents), base de l'indexation de 5 %/an.
ANNEE_BASE = 2026
BASE_CENTS = {"accords": 2458050, "concert": 390075, "humidite": 231420}

# (mois, jour, rang) — rang 1 = 1er de quatre
ECHEANCES = [(8, 1, 1), (10, 15, 2), (1, 15, 3), (4, 15, 4)]
RANGS = {1: "1er", 2: "2e", 3: "3e", 4: "4e"}
JOURS_AVANCE = 21


def annee_contrat(echeance: date) -> int:
    """Année de début du contrat (juillet à juin) auquel appartient l'échéance."""
    return echeance.year if echeance.month >= 7 else echeance.year - 1


def montants_annuels(debut: int) -> dict:
    m = dict(BASE_CENTS)
    for _ in range(max(0, debut - ANNEE_BASE)):
        m = {k: round(v * 1.05) for k, v in m.items()}
    return m


def dollars_fr(cents: int) -> str:
    s = f"{cents / 100:,.2f}".replace(",", " ").replace(".", ",")
    return f"{s} $"


def date_declenchement(echeance: date) -> date:
    d = echeance - timedelta(days=JOURS_AVANCE)
    if (d.month == 12 and d.day >= 19) or (d.month == 1 and d.day <= 3):
        d = date(echeance.year - 1 if echeance.month == 1 else echeance.year, 12, 18)
    return d


def versement_a_faire(aujourdhui: date):
    """Le versement dont la fenêtre [déclenchement, échéance] contient aujourd'hui."""
    for annee in (aujourdhui.year, aujourdhui.year + 1):
        for mois, jour, rang in ECHEANCES:
            ech = date(annee, mois, jour)
            if date_declenchement(ech) <= aujourdhui <= ech:
                return ech, rang
    return None


def lignes_facture(ech: date, rang: int):
    debut = annee_contrat(ech)
    m = montants_annuels(debut)
    periode = f"{debut}-{debut + 1}"
    return periode, [
        (f"Contrat d'entretien régulier {periode} (accords). {RANGS[rang]} de quatre.",
         round(m["accords"] / 4)),
        (f"Pianos de concert : entretien avancé. ({dollars_fr(m['concert'])} / 4)",
         round(m["concert"] / 4)),
        (f"Remplissage périodique des systèmes d'humidité ({dollars_fr(m['humidite'])} / 4)",
         round(m["humidite"] / 4)),
    ]


def facture_existante(gz, periode: str, rang: int):
    q = """query($c: String) { allInvoices(first: 40, filters: {clientId: $c}) {
      nodes { number status allInvoiceItems { nodes { description } } } } }"""
    res = gz._execute_query(q, {"c": CLIENT_ID})
    if res.get("errors"):
        raise RuntimeError(f"Gazelle (lecture factures) : {res['errors']}")
    cle_periode = f"régulier {periode}"
    cle_rang = f"{RANGS[rang]} de quatre"
    for n in ((res.get("data") or {}).get("allInvoices") or {}).get("nodes") or []:
        for it in (n.get("allInvoiceItems") or {}).get("nodes") or []:
            d = it.get("description") or ""
            if cle_periode in d and cle_rang in d:
                return n.get("number")
    return None


def creer_facture(gz, ech: date, lignes):
    from api.assistant_duplication import _CREATE_INVOICE, _build_taxes, _mutation_error_detail
    items = [{"description": desc, "type": "LABOR_FIXED_RATE", "quantity": 100, "amount": cents,
              "taxable": True, "billable": True, "sequenceNumber": i,
              "taxes": _build_taxes(cents, True)} for i, (desc, cents) in enumerate(lignes)]
    inp = {"clientId": CLIENT_ID, "contactId": CONTACT_ID, "assignedToId": ASSIGNE_A,
           "status": "DRAFT", "taxPricingMode": "EXCLUSIVE", "dueOn": ech.isoformat(),
           "notes": NOTES, "invoiceItems": items}
    res = gz._execute_query(_CREATE_INVOICE, {"input": inp})
    payload = ((res or {}).get("data") or {}).get("createInvoice") or {}
    inv = payload.get("invoice")
    if not inv:
        raise RuntimeError(f"Gazelle a refusé la création ({_mutation_error_detail(payload)}) {res.get('errors')}")
    return inv


def courriel(sujet: str, texte: str):
    from core.email_notifier import get_email_notifier
    html = "<p>" + texte.replace("\n\n", "</p><p>").replace("\n", "<br>") + "</p>"
    ok = get_email_notifier().send_email(DESTINATAIRES, sujet, html, texte)
    if not ok:
        raise RuntimeError("Courriel non envoyé")


def main():
    from core.timezone_utils import aujourdhui_montreal
    ap = argparse.ArgumentParser()
    ap.add_argument("--date")
    ap.add_argument("--essai", action="store_true")
    a = ap.parse_args()
    auj = date.fromisoformat(a.date) if a.date else aujourdhui_montreal()

    v = versement_a_faire(auj)
    if not v:
        print(f"{auj} : aucun versement Vincent-d'Indy à préparer.")
        return
    ech, rang = v
    periode, lignes = lignes_facture(ech, rang)
    sous_total = sum(c for _, c in lignes)
    print(f"{auj} : versement {RANGS[rang]} de quatre {periode}, échéance {ech}, {dollars_fr(sous_total)} avant taxes")
    for d, c in lignes:
        print(f"   {d} — {dollars_fr(c)}")

    from core.gazelle_api_client import GazelleAPIClient
    gz = GazelleAPIClient()
    deja = facture_existante(gz, periode, rang)
    if deja:
        print(f"Déjà facturé : facture #{deja}. Rien à faire.")
        return
    if a.essai:
        print("Mode essai : rien créé, rien envoyé.")
        return

    try:
        inv = creer_facture(gz, ech, lignes)
    except Exception as e:
        courriel(f"⚠️ Facture Vincent-d'Indy ({RANGS[rang]} versement) NON créée",
                 f"La facture automatique du {RANGS[rang]} versement {periode} (échéance {ech:%d/%m/%Y}) "
                 f"n'a pas pu être créée dans Gazelle.\n\nErreur : {e}\n\n"
                 f"À faire à la main, ou demander à Claude.")
        raise
    numero = inv.get("number")
    total = inv.get("total") or 0
    nouveau_contrat = "\n\nNouveau contrat : les montants ont été indexés de 5 % (article 3). Vérifier qu'ils concordent avec le contrat signé." if rang == 1 else ""
    courriel(
        f"Facture Vincent-d'Indy #{numero} à envoyer — {RANGS[rang]} versement (échéance {ech:%d/%m/%Y})",
        f"Bonjour Louise,\n\n"
        f"La facture du {RANGS[rang]} versement du contrat Vincent-d'Indy {periode} est prête en brouillon "
        f"dans Gazelle : #{numero}, échéance {ech:%d/%m/%Y}, {dollars_fr(sous_total)} avant taxes "
        f"({dollars_fr(total)} taxes incluses).\n\n"
        f"Quand elle sera synchronisée dans QuickBooks, envoie-la à partir de QuickBooks en ajoutant "
        f"deux destinataires : Julio Gonzalo (jgonzalo@emvi.qc.ca) et la comptabilité (finances@emvi.qc.ca)."
        f"{nouveau_contrat}\n\nMerci !\n\n— Assistant Gazelle (message automatique)")
    print(f"Facture #{numero} créée et courriel envoyé.")


if __name__ == "__main__":
    main()
