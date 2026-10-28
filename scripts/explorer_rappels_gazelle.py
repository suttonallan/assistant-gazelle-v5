#!/usr/bin/env python3
"""Lecture seule : quel code de fusion Gazelle insère le « Numéro client » (custom2) ?
Utilise l'aperçu de Gazelle (lifecycleMessagePreview). Aucune écriture."""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dotenv import load_dotenv; load_dotenv()
from core.gazelle_api_client import GazelleAPIClient
api = GazelleAPIClient()
def q(t, v=None): return api._execute_query(t, v or {})
def note(titre, txt): print(f"::notice title={titre}::" + str(txt)[:6000].replace("%", "%25").replace("\n", "%0A"))

enum = q('{ __type(name:"ReminderType"){ enumValues { name } } }')["data"]["__type"]["enumValues"]
champs = q('{ __type(name:"PrivateTemplatePreview"){ fields { name } } }')["data"]["__type"]["fields"]
note("ReminderType", [e["name"] for e in enum]); note("Preview fields", [f["name"] for f in champs])
sel = " ".join(f["name"] for f in champs if f["name"] in ("subject", "message", "html", "text", "body", "errors", "error"))
msg = ("A=[{{client.custom2}}] B=[{{client.custom_2}}] C=[{{client.custom_field_2}}] "
       "D=[{{client.custom_fields.custom2}}] E=[{{client.first_name}}] F=[{{scheduling_link}}] G=[{{client.id}}]")
for kind in [e["name"] for e in enum][:3]:
    r = q(f"query($m:String!,$k:ReminderType!){{ lifecycleMessagePreview(message:$m, subject:\"s\", reminderKind:$k){{ {sel} }} }}",
          {"m": msg, "k": kind})
    note("Apercu " + kind, json.dumps(r, ensure_ascii=False)[:3000])
