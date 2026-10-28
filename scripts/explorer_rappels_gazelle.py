#!/usr/bin/env python3
"""Lecture seule : champs de structure (aucune donnée client affichée)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dotenv import load_dotenv; load_dotenv()
from core.gazelle_api_client import GazelleAPIClient
api = GazelleAPIClient()
def champs(t):
    r = api._execute_query('query($n:String!){ __type(name:$n){ fields { name type { name ofType { name ofType { name } } } } inputFields { name } } }', {"n": t})
    ty = (r.get("data") or {}).get("__type") or {}
    nom = lambda x: x.get("name") or (x.get("ofType") or {}).get("name") or ((x.get("ofType") or {}).get("ofType") or {}).get("name")
    return [f"{f['name']}:{nom(f['type'])}" for f in ty.get("fields") or []] or [f["name"] for f in ty.get("inputFields") or []]
for t in ["PrivateClient", "PrivateContact", "PrivateContactLocation", "PrivateContactAddress", "PrivateLocation",
          "PrivateCreateBulkReminderReassignmentInput", "PrivateSelectionInput", "PrivateBulkReminderReassignmentJob"]:
    c = champs(t)
    if c:
        print(f"::notice title={t}::{', '.join(x for x in c if any(k in x.lower() for k in ('lifecycle','loc','lat','lng','long','geo','address','postal','status','id','base','ids','job','state','error','count')))[:3000]}")
r = api._execute_query('{ __schema { mutationType { fields { name args { name } type { name } } } } }')
for f in r["data"]["__schema"]["mutationType"]["fields"]:
    if "Reminder" in f["name"] or "ifecycle" in f["name"]:
        print(f"::notice title=M {f['name']}::{[a['name'] for a in f['args']]} -> {f['type']['name']}")
