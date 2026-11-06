#!/usr/bin/env python3
"""Rappel Gazelle « Your piano will be due for a tuning » (cycle English) : ajoute le lien
personnel vers la page de réservation PTM, en anglais (?lang=en), en gardant le lien
Gazelle en second choix. Pendant anglais de rappel_lien_reservation.py (cycle Français).

Touche UN seul message (lcm_qNQnkXkbZj6Ev1Lz), vérifie le texte actuel avant d'écrire,
relit après. Idempotent. {{client.custom2}} = numéro client (rempli chaque nuit) ;
s'il est vide, le lien mène à la page générale, en anglais : jamais de lien brisé.
"""
import re
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dotenv import load_dotenv; load_dotenv()
from core.gazelle_api_client import GazelleAPIClient

CYCLE_ID = "lcy_bWUWxo81RTbyQc7x"   # « English »
MESSAGE_ID = "lcm_qNQnkXkbZj6Ev1Lz"  # COMING_DUE
ANCIENNE = re.compile(r"You can choose your next appointment by clicking on this button\s*:\s*\{\{scheduling_link\}\}")
NOUVELLE = ("You can book your appointment online here: "
            "**[Book an appointment](https://reserver.pianotechniquemontreal.com/{{client.custom2}}?lang=en)**\n\n"
            "Prefer our previous booking page? {{scheduling_link}}")
CHAMPS = ("recurringMessage recurringSubject firstMessage firstSubject specialMessage specialSubject "
          "frequencyCode frequencyFrom firstDelayCode limit")

api = GazelleAPIClient()
def lire():
    r = api._execute_query(f'{{ lifecycle(id: "{CYCLE_ID}") {{ lifecycleMessages {{ id {CHAMPS} }} }} }}')
    return next(m for m in r["data"]["lifecycle"]["lifecycleMessages"] if m["id"] == MESSAGE_ID)

m = lire()
texte = m["recurringMessage"] or ""
if "reserver.pianotechniquemontreal.com" in texte:
    print("::notice title=Rappel EN::Deja a jour, rien a faire"); sys.exit(0)
if len(ANCIENNE.findall(texte)) != 1:
    print("::error title=Rappel EN::Texte actuel inattendu, rien n'a ete modifie"); sys.exit(1)

entree = {k: m[k] for k in CHAMPS.split()}
entree["recurringMessage"] = ANCIENNE.sub(lambda _: NOUVELLE, texte)
r = api._execute_query(
    "mutation($id: String!, $input: PrivateUpdateLifecycleMessageInput!) { updateLifecycleMessage(id: $id, input: $input) { mutationErrors { fieldName messages } } }",
    {"id": MESSAGE_ID, "input": entree})
if r.get("errors") or ((r.get("data") or {}).get("updateLifecycleMessage") or {}).get("mutationErrors"):
    print(f"::error title=Rappel EN::Refus Gazelle : {str(r)[:1500]}"); sys.exit(1)
apres = lire()
ok = apres["recurringMessage"] == entree["recurringMessage"] and all(apres[k] == m[k] for k in CHAMPS.split() if k != "recurringMessage")
print(f"::notice title=Rappel EN::{'Mis a jour et verifie' if ok else 'ECART a la relecture'}")
sys.exit(0 if ok else 1)
