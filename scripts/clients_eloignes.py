#!/usr/bin/env python3
"""Clients éloignés : repérage pour le cycle de rappel « Clients éloignés ».

Étape 1 (ce script, lecture seule dans Gazelle) : distance à vol d'oiseau entre le
piano (adresse par défaut du client) et le point de référence de PTM (métro
Outremont). Comptes par tranche et par cycle dans les annotations (aucune donnée
personnelle) ; la liste détaillée va dans Supabase (system_settings, privé).
"""
import json, math, sys
from collections import Counter
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dotenv import load_dotenv; load_dotenv()
from core.gazelle_api_client import GazelleAPIClient
from core.supabase_storage import SupabaseStorage

REF = (45.5200, -73.6150)  # métro Outremont, point de référence du calculateur de frais
TRANCHES = [(0, 15), (15, 20), (20, 30), (30, 45), (45, 80), (80, 10_000)]

def km(a, b):
    la1, lo1, la2, lo2 = map(math.radians, (*a, *b))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 6371 * 2 * math.asin(math.sqrt(h))

api = GazelleAPIClient()
Q = """query($after: String) { allClients(first: 100, after: $after, filters: {status: ACTIVE}) {
  nodes { id lifecycle { id name } defaultContact { defaultLocation { latitude longitude } } }
  pageInfo { hasNextPage endCursor } } }"""
clients, apres = [], None
while True:
    r = api._execute_query(Q, {"after": apres})
    bloc = r["data"]["allClients"]
    clients += bloc["nodes"]
    if not bloc["pageInfo"]["hasNextPage"]:
        break
    apres = bloc["pageInfo"]["endCursor"]

comptes, sans_coord, liste = Counter(), Counter(), []
for c in clients:
    cycle = (c.get("lifecycle") or {}).get("name") or "—"
    loc = ((c.get("defaultContact") or {}).get("defaultLocation") or {})
    try:
        d = km(REF, (float(loc["latitude"]), float(loc["longitude"])))
    except (TypeError, ValueError, KeyError):
        sans_coord[cycle] += 1
        continue
    t = next(f"{a}-{b if b < 10_000 else '+'} km" for a, b in TRANCHES if a <= d < b)
    comptes[(cycle, t)] += 1
    if d >= 15:
        liste.append({"id": c["id"], "km": round(d, 1), "cycle": cycle, "cycle_id": (c.get("lifecycle") or {}).get("id")})

SupabaseStorage(silent=True).save_system_setting("clients_eloignes_candidats", liste)
print(f"::notice title=Total::{len(clients)} clients actifs ; {len(liste)} a 15 km ou plus (liste dans Supabase)")
for cycle in sorted({k[0] for k in comptes}):
    lignes = ", ".join(f"{t}: {comptes[(cycle, t)]}" for t in [f"{a}-{b if b < 10_000 else '+'} km" for a, b in TRANCHES] if comptes[(cycle, t)])
    print(f"::notice title=Cycle {cycle}::{lignes} ; sans coordonnees: {sans_coord[cycle]}")
