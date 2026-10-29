#!/usr/bin/env python3
"""Lecture seule : pourquoi un client a reçu un rappel « Due » le jour de son accord.
N'affiche que des dates, statuts et noms de champs (aucune donnée personnelle)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dotenv import load_dotenv; load_dotenv()
from core.gazelle_api_client import GazelleAPIClient
api = GazelleAPIClient()
def q(t, v=None):
    r = api._execute_query(t, v or {})
    if r.get("errors"): print(f"::warning title=Erreur::{str(r['errors'])[:800]}")
    return r.get("data") or {}
def note(t, m): print(f"::notice title={t}::" + str(m)[:3000].replace("%", "%25").replace("\n", "%0A"))
champs = [f["name"] for f in q('{ __type(name:"PrivatePiano"){ fields { name } } }')["__type"]["fields"]]
utiles = [c for c in champs if any(k in c.lower() for k in ("due", "service", "tun", "last", "next", "interval", "lifecycle", "state"))]
note("Champs piano utiles", ", ".join(utiles))
cid = q('{ allClients(first: 3, filters: {search: "ricardo.pascoe10@gmail.com"}) { nodes { id lifecycle { name } lifecycleState } } }')["allClients"]["nodes"]
note("Client", [{k: v for k, v in c.items() if k != "id"} for c in cid])
if cid:
    c = cid[0]["id"]
    simples = [u for u in utiles if u not in ("allServiceRecords",)]
    sel = []
    for u in simples:
        r = q('{ __type(name:"PrivatePiano"){ fields { name type { kind ofType { kind } } } } }')
        break
    kinds = {f["name"]: (f["type"]["kind"], (f["type"].get("ofType") or {}).get("kind")) for f in r["__type"]["fields"]}
    scal = [u for u in simples if kinds[u][0] in ("SCALAR", "ENUM") or kinds[u][1] in ("SCALAR", "ENUM")]
    p = q('query($c:String!){ allPianos(first: 10, filters: {clientId: $c}) { nodes { id type %s } } }' % " ".join(scal), {"c": c})
    note("Pianos", [{k: v for k, v in n.items() if k != "id"} for n in (p.get("allPianos") or {}).get("nodes") or []])
    e = q("""query($f: PrivateAllEventsFilter) { allEventsBatched(first: 50, filters: $f) { nodes {
      start status type confirmedByClient isAllDay client { id } user { firstName } } } }""",
      {"f": {"startOn": "2026-10-20", "endOn": "2026-11-05", "type": ["APPOINTMENT"]}})
    ev = [{k: v for k, v in n.items() if k != "client"} for n in (e.get("allEventsBatched") or {}).get("nodes") or [] if (n.get("client") or {}).get("id") == c]
    note("Rendez-vous 20 oct.-5 nov.", ev)
    f = q('query($c:String!){ allInvoices(first: 5, filters: {clientId: $c}) { nodes { createdAt status number } } }', {"c": c})
    note("Factures", [{k: v for k, v in n.items()} for n in (f.get("allInvoices") or {}).get("nodes") or []][:5])
