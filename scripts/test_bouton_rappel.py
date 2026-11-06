#!/usr/bin/env python3
"""Test d'affichage : envoie à la fiche d'Allan SEULEMENT un courriel [TEST] avec 3 façons
de montrer le lien de réservation comme un bouton. Aucune autre fiche, aucun cycle touché."""

import sys, traceback
sys.excepthook = lambda t, e, tb: print("::error title=Plantage::" + "".join(traceback.format_exception(t, e, tb))[-1500:].replace("\n", " | "))
from datetime import datetime, timedelta, timezone
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dotenv import load_dotenv; load_dotenv()
from core.gazelle_api_client import GazelleAPIClient
import os
_k = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or ""
print("::notice title=Cle Supabase GitHub::" + ("ANCIENNE cle JWT (desactivee le 29 oct., a remplacer)" if _k.startswith("eyJ") else "nouvelle cle sb_secret" if _k.startswith("sb_secret_") else "vide ou inconnue"))

CLIENT_ALLAN = "cli_Wzmj2Va3ODoxDoQr"   # fiche d'Allan (asutton@piano-tek.com)
MESSAGES = [("lcy_VEOrJHKlyLhGaNa4", "lcm_oYKZhzjTW6WzXNH2", "Cycle Français — À accorder bientôt")]
api = GazelleAPIClient()
def q(t, v=None):
    r = api._execute_query(t, v or {})
    if r.get("errors"):
        print(f"::error title=Gazelle::{str(r['errors'])[:1500]}"); sys.exit(1)
    return r["data"]

# Fiche d'Allan : celle dont le courriel par défaut est une de ses adresses
ADRESSES_ALLAN = {"asutton@piano-tek.com", "suttonallan@gmail.com"}
noeuds = q('{ allClients(first: 10, filters: {search: "Sutton"}) { nodes { id custom2 status defaultContact { firstName lastName defaultEmail { email } } } } }')["allClients"]["nodes"]
masque = lambda e: (e[:2] + "***@" + e.split("@")[-1]) if "@" in (e or "") else "aucun"
for n in noeuds:
    ct = n.get("defaultContact") or {}
    print(f"Fiche {n['id'][-4:]} : {(ct.get('firstName') or '')[:1]}. {ct.get('lastName') or ''} | {masque((ct.get('defaultEmail') or {}).get('email'))} | numero client {'rempli' if n.get('custom2') else 'vide'} | {n['status']}")
cible = next((n for n in noeuds if ((((n.get("defaultContact") or {}).get("defaultEmail") or {}).get("email") or "").lower() in ADRESSES_ALLAN)
              and n.get("custom2") and n["status"] == "ACTIVE"), None)
if not cible:
    print("::error title=Securite::Aucune fiche active d'Allan avec numero client, rien envoye"); sys.exit(1)
CLIENT_ALLAN = cible["id"]
print(f"::notice title=Fiche retenue::{CLIENT_ALLAN[-4:]} ({masque(cible['defaultContact']['defaultEmail']['email'])})")
types = [e["name"] for e in q('{ __type(name:"ScheduledMessageType"){ enumValues { name } } }')["__type"]["enumValues"]]
type_courriel = next(t for t in types if "EMAIL" in t.upper())

TEXTE = r'''Bonjour {{client.first_name}},

Test d'affichage : trois façons de montrer le lien de réservation PTM comme un bouton. Dites à Claude laquelle s'affiche comme un vrai bouton.

**Option A**

<a href="https://reserver.pianotechniquemontreal.com/{{client.custom2}}" style="display:inline-block;background:#1C1C1C;color:#ffffff;padding:14px 28px;border-radius:6px;font-size:17px;font-weight:bold;text-decoration:none">Prendre rendez-vous</a>

**Option B**

<table role="presentation" cellspacing="0" cellpadding="0"><tr><td style="background:#B8860B;border-radius:6px"><a href="https://reserver.pianotechniquemontreal.com/{{client.custom2}}" style="display:inline-block;padding:14px 28px;color:#ffffff;font-size:17px;font-weight:bold;text-decoration:none">Prendre rendez-vous</a></td></tr></table>

**Option C**

## [Prendre rendez-vous](https://reserver.pianotechniquemontreal.com/{{client.custom2}})

Pour comparer, le bouton Gazelle actuel :

{{scheduling_link}}
'''

envoi = (datetime.now(timezone.utc) + timedelta(minutes=2)).strftime("%Y-%m-%dT%H:%M:%SZ")
r = q("""mutation($i: PrivateScheduledMessageInput!) { createScheduledMessage(input: $i) { mutationErrors { fieldName messages } } }""",
      {"i": {"clientId": CLIENT_ALLAN, "type": type_courriel, "language": "fr_CA",
             "subject": "[TEST] Bouton de réservation — 3 options", "template": TEXTE, "sendAt": envoi}})
err = r["createScheduledMessage"]["mutationErrors"]
print(f"::{'error' if err else 'notice'} title=Test bouton::{err or 'Programme pour ' + envoi + ' (UTC)'}")
