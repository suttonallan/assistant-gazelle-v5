#!/usr/bin/env python3
"""Simulation (lecture seule) : frais de déplacement actuels vs options graduelles,
sur les vrais clients actifs à 15 km et plus (vol d'oiseau) du métro Outremont.

Aucune écriture dans Gazelle. Résultats agrégés seulement (aucune donnée client)
dans les annotations ; le détail anonymisé va dans Supabase (system_settings).
"""
import math, statistics, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dotenv import load_dotenv; load_dotenv()
from core.gazelle_api_client import GazelleAPIClient
from core.supabase_storage import SupabaseStorage
from modules.travel_fees.calculator import TravelFeeCalculator

REF = (45.5200, -73.6150)
def vol(a, b):
    la1, lo1, la2, lo2 = map(math.radians, (*a, *b))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 6371 * 2 * math.asin(math.sqrt(h))
def note(t, m): print(f"::notice title={t}::" + str(m).replace("%", "%25").replace("\n", "%0A"))

api = GazelleAPIClient()
Q = """query($after: String) { allClients(first: 100, after: $after, filters: {status: ACTIVE}) {
  nodes { id lifecycle { name } defaultContact { defaultLocation { latitude longitude } } }
  pageInfo { hasNextPage endCursor } } }"""
pts, apres = [], None
while True:
    b = api._execute_query(Q, {"after": apres})["data"]["allClients"]
    for c in b["nodes"]:
        loc = (c.get("defaultContact") or {}).get("defaultLocation") or {}
        try:
            p = (float(loc["latitude"]), float(loc["longitude"]))
        except (TypeError, ValueError, KeyError):
            continue
        if vol(REF, p) >= 15:
            pts.append(p)
    if not b["pageInfo"]["hasNextPage"]:
        break
    apres = b["pageInfo"]["endCursor"]

calc = TravelFeeCalculator()
lignes = []
for p in pts:
    try:
        r = calc.calculer_frais_client(f"{p[0]},{p[1]}")
    except Exception as e:  # noqa: BLE001
        continue
    km = r.distance_km / 2
    exempte = calc.secteur_exempte(getattr(calc, "_derniere_destination", ""))
    lignes.append({"km": round(km, 1), "min": round(r.duration_minutes / 2), "actuel": round(r.total_fee, 2),
                   "exempte": exempte})

payants = [l for l in lignes if l["km"] > 20 and not l["exempte"]]
total_actuel = sum(l["actuel"] for l in payants)
km_exc = sum(l["km"] - 20 for l in payants)
taux = total_actuel / km_exc if km_exc else 0
note("Echantillon", f"{len(lignes)} clients calcules ; {len(payants)} au-dela de 20 km par la route (hors secteurs exemptes) ; total actuel par visite {total_actuel:.0f} $")
note("Option 1 - tarif au km", f"Taux neutre pour les revenus : {taux:.2f} $ par km au-dela de 20 km (aller simple)")

TRANCHES = [(20, 25), (25, 30), (30, 35), (35, 45), (45, 60), (60, 1000)]
rangs = []
for a, b in TRANCHES:
    g = [l for l in payants if a < l["km"] <= b]
    if not g:
        continue
    act = [l["actuel"] for l in g]
    opt1 = [(l["km"] - 20) * taux for l in g]
    rangs.append(f"{a}-{b if b < 1000 else '+'} km : {len(g)} clients | actuel moy {statistics.mean(act):.0f} $ (min {min(act):.0f}, max {max(act):.0f}) | option 1 moy {statistics.mean(opt1):.0f} $ | palier neutre {statistics.mean(act):.0f} $")
note("Par tranche (km route, aller)", "\n".join(rangs))

ecarts = [((l["km"] - 20) * taux) - l["actuel"] for l in payants]
note("Option 1 vs actuel", f"paient plus : {sum(e > 2 for e in ecarts)} ; a peu pres pareil (+/-2 $) : {sum(abs(e) <= 2 for e in ecarts)} ; paient moins : {sum(e < -2 for e in ecarts)} ; ecart max +{max(ecarts):.0f} / {min(ecarts):.0f} $")
# Saut a la frontiere : clients entre 20 et 23 km
bord = [l for l in payants if l["km"] <= 23]
if bord:
    note("Frontiere 20-23 km", f"{len(bord)} clients : actuel moy {statistics.mean(l['actuel'] for l in bord):.0f} $ ; option 1 moy {statistics.mean((l['km']-20)*taux for l in bord):.0f} $")
# Instabilite du temps Google : part des frais actuels venant du temps
note("Part du temps", f"Temps aller moyen des clients payants : {statistics.mean(l['min'] for l in payants):.0f} min")
SupabaseStorage(silent=True).save_system_setting("simulation_frais_deplacement", {"taux_neutre": round(taux, 3), "lignes": lignes})
