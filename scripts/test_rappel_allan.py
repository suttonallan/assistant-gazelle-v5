#!/usr/bin/env python3
"""Envoie à la fiche Gazelle d'Allan (et à elle seule) les rappels modifiés, en
message ponctuel Gazelle, pour tester les liens avec ses vraies données de fusion.
Objet préfixé [TEST]. Aucune autre fiche n'est touchée."""
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dotenv import load_dotenv; load_dotenv()
from core.gazelle_api_client import GazelleAPIClient

CLIENT_ALLAN = "cli_Wzmj2Va3ODoxDoQr"   # fiche d'Allan (asutton@piano-tek.com)
MESSAGES = [("lcy_VEOrJHKlyLhGaNa4", "lcm_oYKZhzjTW6WzXNH2", "Cycle Français — À accorder bientôt")]
api = GazelleAPIClient()
def q(t, v=None):
    r = api._execute_query(t, v or {})
    if r.get("errors"):
        print(f"::error title=Gazelle::{str(r['errors'])[:1500]}"); sys.exit(1)
    return r["data"]

c = q('query($id:String!){ client(id:$id){ id custom2 defaultContact { defaultEmail { email } } } }', {"id": CLIENT_ALLAN})["client"]
courriel = ((c.get("defaultContact") or {}).get("defaultEmail") or {}).get("email", "")
if courriel.lower() != "asutton@piano-tek.com":
    print("::error title=Securite::La fiche ne correspond pas au courriel d'Allan, rien envoye"); sys.exit(1)
types = [e["name"] for e in q('{ __type(name:"ScheduledMessageType"){ enumValues { name } } }')["__type"]["enumValues"]]
type_courriel = next(t for t in types if "EMAIL" in t.upper())

# Cycle « Clients éloignés » : son courriel « À accorder bientôt »
eloignes = next(l for l in q("{ allLifecycles(first: 50) { nodes { id name } } }")["allLifecycles"]["nodes"] if l["name"] == "Clients éloignés")
MESSAGES.append((eloignes["id"], None, "Cycle Clients éloignés — À accorder bientôt"))

envoi = (datetime.now(timezone.utc) + timedelta(minutes=2)).strftime("%Y-%m-%dT%H:%M:%SZ")
for lcy, lcm, nom in MESSAGES:
    msgs = q('query($id:String!){ lifecycle(id:$id){ lifecycleMessages { id state reminderKind recurringSubject recurringMessage } } }', {"id": lcy})["lifecycle"]["lifecycleMessages"]
    m = next(x for x in msgs if (x["id"] == lcm) if lcm) if lcm else next(x for x in msgs if x["state"] == "COMING_DUE" and x["reminderKind"] == "EMAIL")
    r = q("""mutation($i: PrivateScheduledMessageInput!) { createScheduledMessage(input: $i) {
            mutationErrors { fieldName messages } } }""",
          {"i": {"clientId": CLIENT_ALLAN, "type": type_courriel, "language": "fr_CA",
                 "subject": f"[TEST] {m['recurringSubject']}", "template": m["recurringMessage"], "sendAt": envoi}})
    err = r["createScheduledMessage"]["mutationErrors"]
    print(f"::{'error' if err else 'notice'} title={nom}::{err or 'Programme pour ' + envoi + ' (UTC)'}")
