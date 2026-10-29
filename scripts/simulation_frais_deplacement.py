#!/usr/bin/env python3
"""Simulation (lecture seule) : tarif graduel de 4,50 $/km au-delà de 20 km (20 à 45 km),
comparé aux frais actuels ; et frais de déplacement réellement facturés aux clients
éloignés dans Gazelle (factures depuis 2023).

Aucune écriture dans Gazelle. Agrégats seulement dans les annotations (aucune donnée
client) ; le détail va dans Supabase (system_settings, privé).
"""
import math, re, statistics, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dotenv import load_dotenv; load_dotenv()
from core.gazelle_api_client import GazelleAPIClient
from core.supabase_storage import SupabaseStorage
from modules.travel_fees.calculator import TravelFeeCalculator

TAUX = 4.50
REF = (45.5200, -73.6150)
DEPUIS = "2023-01-01"
MOTIF = re.compile(r"d[ée]placement|travel|kilom|\bkm\b|mileage|trajet", re.I)
def vol(a, b):
    la1, lo1, la2, lo2 = map(math.radians, (*a, *b))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 6371 * 2 * math.asin(math.sqrt(h))
def note(t, m): print(f"::notice title={t}::" + str(m).replace("%", "%25").replace("\n", "%0A"))

api = GazelleAPIClient()
def q(t, v=None):
    r = api._execute_query(t, v or {})
    if r.get("errors"):
        raise RuntimeError(str(r["errors"])[:500])
    return r["data"]

# Champ « montant » d'une ligne de facture (nom variable selon le schéma)
champs_ligne = [f["name"] for f in q('{ __type(name:"PrivateInvoiceItem"){ fields { name } } }')["__type"]["fields"]]
montant = next((c for c in ("amount", "total", "subTotal", "subtotal", "price") if c in champs_ligne), None)
note("Schema ligne de facture", f"montant lu dans : {montant}")

Q = """query($after: String) { allClients(first: 100, after: $after, filters: {status: ACTIVE}) {
  nodes { id defaultContact { defaultLocation { latitude longitude } } }
  pageInfo { hasNextPage endCursor } } }"""
clients, apres = [], None
while True:
    b = q(Q, {"after": apres})["allClients"]
    for c in b["nodes"]:
        loc = (c.get("defaultContact") or {}).get("defaultLocation") or {}
        try:
            p = (float(loc["latitude"]), float(loc["longitude"]))
        except (TypeError, ValueError, KeyError):
            continue
        if vol(REF, p) >= 15:
            clients.append((c["id"], p))
    if not b["pageInfo"]["hasNextPage"]:
        break
    apres = b["pageInfo"]["endCursor"]

QF = """query($cid: String!, $after: String) { allInvoices(first: 50, after: $after, filters: {clientId: $cid}) {
  nodes { createdAt status allInvoiceItems { nodes { description %s } } } pageInfo { hasNextPage endCursor } } }""" % (montant or "")

calc = TravelFeeCalculator()
lignes = []
for cid, p in clients:
    try:
        r = calc.calculer_frais_client(f"{p[0]},{p[1]}")
    except Exception:  # noqa: BLE001
        continue
    if calc.secteur_exempte(getattr(calc, "_derniere_destination", "")):
        continue
    km = r.distance_km / 2
    if km <= 20:
        continue
    nb_fact = nb_avec_frais = 0
    factures_frais = []
    apres = None
    for _ in range(10):
        f = q(QF, {"cid": cid, "after": apres})["allInvoices"]
        for inv in f["nodes"]:
            if (inv.get("createdAt") or "") < DEPUIS or str(inv.get("status")).upper() in ("VOID", "DELETED", "DRAFT"):
                continue
            nb_fact += 1
            items = [i for i in (inv.get("allInvoiceItems") or {}).get("nodes") or [] if MOTIF.search(i.get("description") or "")]
            if items:
                nb_avec_frais += 1
                if montant:
                    factures_frais.append(sum((i.get(montant) or 0) for i in items) / 100)
        if not f["pageInfo"]["hasNextPage"]:
            break
        apres = f["pageInfo"]["endCursor"]
    nouveau = round((km - 20) * TAUX, 2) if km <= 45 else None
    lignes.append({"id": cid, "km": round(km, 1), "actuel": round(r.total_fee, 2), "nouveau": nouveau,
                   "factures": nb_fact, "factures_avec_frais": nb_avec_frais,
                   "frais_factures_moy": round(statistics.mean(factures_frais), 2) if factures_frais else None})

zone = [l for l in lignes if l["nouveau"] is not None]
loin = [l for l in lignes if l["nouveau"] is None]
ta, tn = sum(l["actuel"] for l in zone), sum(l["nouveau"] for l in zone)
plus = [l for l in zone if l["nouveau"] - l["actuel"] > 2]
moins = [l for l in zone if l["actuel"] - l["nouveau"] > 2]
note("20-45 km : tarif 4,50 $/km", f"{len(zone)} clients ; total par visite actuel {ta:.0f} $ -> nouveau {tn:.0f} $ ({(tn-ta)/ta*100:+.0f} %)")
note("Qui paie plus ou moins", f"paient plus : {len(plus)} (hausse moy {statistics.mean([l['nouveau']-l['actuel'] for l in plus]) if plus else 0:.0f} $, max {max([l['nouveau']-l['actuel'] for l in plus], default=0):.0f} $) ; pareil (+/-2 $) : {len(zone)-len(plus)-len(moins)} ; paient moins : {len(moins)} (baisse moy {statistics.mean([l['actuel']-l['nouveau'] for l in moins]) if moins else 0:.0f} $)")
for nom, g in (("20-45 km", zone), ("Plus de 45 km", loin)):
    avec = [l for l in g if l["factures"]]
    jamais = [l for l in avec if not l["factures_avec_frais"]]
    parfois = [l for l in avec if l["factures_avec_frais"] and l["factures_avec_frais"] < l["factures"]]
    toujours = [l for l in avec if l["factures"] and l["factures_avec_frais"] == l["factures"]]
    moy = [l["frais_factures_moy"] for l in avec if l["frais_factures_moy"]]
    note(f"Factures depuis 2023 - {nom}", f"{len(g)} clients, {len(avec)} factures au moins une fois ; JAMAIS de frais factures : {len(jamais)} ; parfois : {len(parfois)} ; toujours : {len(toujours)} ; frais factures moyens quand factures : {statistics.mean(moy) if moy else 0:.0f} $ (calcul actuel moyen : {statistics.mean([l['actuel'] for l in avec]) if avec else 0:.0f} $)")
SupabaseStorage(silent=True).save_system_setting("simulation_frais_deplacement", {"taux": TAUX, "lignes": lignes})
