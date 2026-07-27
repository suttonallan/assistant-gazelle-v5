#!/usr/bin/env python3
"""
Validation « tout cloud » — vérifie en LECTURE SEULE que l'environnement nuage
peut joindre et s'authentifier auprès de tous les services externes utilisés par
l'application, afin de confirmer que les tâches habituellement lancées depuis le
PC peuvent tourner sans lui.

Services testés :
  1. Variables d'environnement (SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
  2. Supabase        — lecture d'une table
  3. Gazelle         — chargement du token (Supabase) + requête de lecture
  4. Gmail (scan PDA)— authentification OAuth via token Supabase (gmail_oauth_token)
  5. Google Sheets   — credentials service account via Supabase (GOOGLE_SHEETS_JSON)

N'écrit rien, n'envoie aucun email, n'exécute aucune mutation. Le seul effet de
bord possible est le rafraîchissement automatique d'un token OAuth expiré, ce que
l'application fait déjà dans son fonctionnement normal.

Usage :
    python3 scripts/validate_tout_cloud.py
"""

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    from dotenv import load_dotenv
    load_dotenv(PROJECT_ROOT / ".env")
except ImportError:
    pass  # python-dotenv absent : on lit les variables d'environnement directement

results = []


def check(name, fn):
    """Exécute une vérification et enregistre PASS/FAIL sans interrompre les autres."""
    try:
        detail = fn()
        results.append((name, True, detail))
        print(f"✅ {name} — {detail}")
    except Exception as e:  # noqa: BLE001 - on veut capturer tout échec de service
        results.append((name, False, f"{type(e).__name__}: {e}"))
        print(f"❌ {name} — {type(e).__name__}: {e}")


def _env():
    manquantes = [v for v in ("SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY") if not os.getenv(v)]
    if manquantes:
        raise RuntimeError(f"variables manquantes : {manquantes}")
    return "SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY présentes"


def _supabase():
    from core.supabase_storage import SupabaseStorage

    storage = SupabaseStorage(silent=True)
    resp = storage.client.table("gazelle_pianos").select("id").limit(1).execute()
    n = len(resp.data or [])
    return f"lecture OK (table gazelle_pianos joignable, {n} ligne lue)"


def _gazelle():
    from core.gazelle_api_client import GazelleAPIClient

    client = GazelleAPIClient()
    clients = client.get_clients(limit=1)
    return f"token chargé + requête GraphQL OK ({len(clients)} client lu)"


def _gmail():
    from core.gmail_scanner import get_gmail_scanner

    scanner = get_gmail_scanner()
    if not scanner.initialize():
        raise RuntimeError("initialize() a renvoyé False (authentification Gmail échouée)")
    return "authentification Gmail OK — scan PDA horaire prêt pour le nuage"


def _sheets():
    from workspace.tools import gsheet

    creds = gsheet._credentials()
    if creds is None:
        raise RuntimeError("credentials Google Sheets introuvables (GOOGLE_SHEETS_JSON ?)")
    return "credentials service account chargés depuis Supabase (GOOGLE_SHEETS_JSON)"


def main():
    print("=== Validation « tout cloud » (lecture seule) ===\n")
    check("1. Variables d'environnement", _env)
    check("2. Supabase", _supabase)
    check("3. Gazelle (lecture seule)", _gazelle)
    check("4. Gmail (scan PDA, auth)", _gmail)
    check("5. Google Sheets (credentials)", _sheets)

    reussies = sum(1 for _, ok, _ in results if ok)
    total = len(results)
    print(f"\n===> {reussies}/{total} vérifications réussies")

    if reussies < total:
        echecs = [name for name, ok, _ in results if not ok]
        print(f"     Échecs : {', '.join(echecs)}")
        print("     (Le reste tourne en nuage ; corriger les services ci-dessus.)")

    sys.exit(0 if reussies == total else 1)


if __name__ == "__main__":
    main()
