#!/usr/bin/env python3
"""Lecture seule : mutations d'envoi de messages, et fiche client d'Allan (id seulement)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dotenv import load_dotenv; load_dotenv()
from core.gazelle_api_client import GazelleAPIClient
api = GazelleAPIClient()
r = api._execute_query('{ __schema { mutationType { fields { name args { name type { name ofType { name } } } } } } }')
for f in r["data"]["__schema"]["mutationType"]["fields"]:
    n = f["name"].lower()
    if any(k in n for k in ("send", "message", "email", "scheduled", "test", "notify")):
        args = ", ".join(f"{a['name']}:{a['type']['name'] or (a['type']['ofType'] or {}).get('name')}" for a in f["args"])
        print(f"::notice title=M {f['name']}::{args}")
c = api._execute_query('{ allClients(first: 5, filters: {search: "asutton@piano-tek.com"}) { nodes { id custom2 status lifecycle { name } } } }')
print(f"::notice title=Fiche Allan::{c}")
