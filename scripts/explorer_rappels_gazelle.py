#!/usr/bin/env python3
"""Lecture seule : Gazelle ajoute-t-il lui-même un lien de désabonnement aux rappels ?"""
import re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dotenv import load_dotenv; load_dotenv()
from core.gazelle_api_client import GazelleAPIClient
api = GazelleAPIClient()
r = api._execute_query('query{ lifecycleMessagePreview(message:"Dear {{client.first_name}}, test.", subject:"s", reminderKind: EMAIL){ message error } }')
h = (r.get("data") or {}).get("lifecycleMessagePreview", {}).get("message") or ""
texte = re.sub(r"<style.*?</style>|<!--.*?-->", " ", h, flags=re.S)
texte = re.sub(r"<[^>]+>", " ", texte); texte = re.sub(r"\s+", " ", texte)
liens = re.findall(r'href="([^"]+)"', h)
print(f"::notice title=Texte visible::{texte[:2500]}")
print(f"::notice title=Liens::{' | '.join(liens)[:2500]}")
