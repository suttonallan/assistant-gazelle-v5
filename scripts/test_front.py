#!/usr/bin/env python3
"""Test de connectivité Front — à lancer localement.

Lit FRONT_API_KEY depuis l'environnement (via .env si python-dotenv est
installé), fait un /me, liste les inboxes et teammates, puis fait une
recherche exemple.

Aucune écriture. Aucun effet de bord. Sécuritaire à lancer.

Usage :
    export FRONT_API_KEY=xxx        # ou dans le .env
    python3 scripts/test_front.py
    python3 scripts/test_front.py "Place des Arts"
"""
import os
import sys
from pathlib import Path

# Chargement du .env à la racine (silencieux si python-dotenv absent)
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env")
except ImportError:
    pass

# Import après load_dotenv pour que FRONT_API_KEY soit disponible
sys.path.insert(0, str(Path(__file__).parent.parent))
from core.front_client import FrontClient


def main():
    query = sys.argv[1] if len(sys.argv) > 1 else "Place des Arts"

    if not os.getenv("FRONT_API_KEY"):
        print("❌ FRONT_API_KEY manquant.")
        print("   Ajoute-le à ton .env ou fais : export FRONT_API_KEY=xxx")
        sys.exit(1)

    client = FrontClient()

    print("→ /me")
    me = client.me()
    print(f"   Connecté comme : {me.get('name') or me.get('first_name')} <{me.get('email')}>")

    print("\n→ Inboxes accessibles")
    for inbox in client.list_inboxes():
        print(f"   · {inbox.get('name')} ({inbox.get('type')}, id={inbox.get('id')})")

    print("\n→ Teammates du workspace")
    for tm in client.list_teammates():
        fn = tm.get('first_name') or ''
        ln = tm.get('last_name') or ''
        avail = "actif" if tm.get('is_available') else "inactif"
        print(f"   · {fn} {ln} — {tm.get('email')} ({avail})")

    print(f"\n→ Recherche : « {query} »")
    results = client.search_conversations(query, limit=10)
    print(f"   {len(results)} conversation(s) trouvée(s).")
    for c in results[:5]:
        subj = c.get('subject') or '(sans sujet)'
        status = c.get('status') or '?'
        cid = c.get('id')
        print(f"   · [{status}] {subj[:70]}  ({cid})")

    print("\n✅ Test terminé — l'API Front répond correctement.")


if __name__ == "__main__":
    main()
