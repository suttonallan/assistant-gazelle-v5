#!/usr/bin/env python3
"""Lecture seule : champs d'un message ponctuel Gazelle, et fiche client d'Allan."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dotenv import load_dotenv; load_dotenv()
from core.gazelle_api_client import GazelleAPIClient
api = GazelleAPIClient()
def t(n):
    r = api._execute_query('query($n:String!){ __type(name:$n){ inputFields { name type { name kind ofType { name } } } enumValues { name } fields { name } } }', {"n": n})
    ty = (r.get("data") or {}).get("__type") or {}
    return ty
ty = t("PrivateScheduledMessageInput")
print("::notice title=Input message ponctuel::" + ", ".join(f"{f['name']}:{f['type']['name'] or (f['type']['ofType'] or {}).get('name')}" for f in ty.get("inputFields") or []))
r = api._execute_query('{ __schema { mutationType { fields { name type { name } } } } }')
pl = next(f["type"]["name"] for f in r["data"]["__schema"]["mutationType"]["fields"] if f["name"] == "createScheduledMessage")
print("::notice title=Retour::" + ", ".join(f["name"] for f in t(pl).get("fields") or []))
c = api._execute_query('{ allClients(first: 5, filters: {search: "asutton@piano-tek.com"}) { nodes { id custom2 status lifecycle { name } } } }')
print(f"::notice title=Fiche Allan::{str(c)[:1500]}")
