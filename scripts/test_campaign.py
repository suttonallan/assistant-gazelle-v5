#!/usr/bin/env python3
"""Test d'agrégation d'une campagne — pas d'écriture, pas d'effet de bord.

Aggrège les conversations Front + commentaires internes de l'équipe pour
un client donné, et affiche le résultat lisible en terminal.

Usage :
    python3 scripts/test_campaign.py                        # défaut: Place des Arts
    python3 scripts/test_campaign.py "Vincent-d'Indy"
    python3 scripts/test_campaign.py "Orford"
    python3 scripts/test_campaign.py "Guy Levesque"         # par nom de personne
"""
import os
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env")
except ImportError:
    pass

sys.path.insert(0, str(Path(__file__).parent.parent))
from modules.campaigns.campaign_service import get_campaign_context


def main():
    client = sys.argv[1] if len(sys.argv) > 1 else "Place des Arts"

    if not os.getenv("FRONT_API_KEY"):
        print("❌ FRONT_API_KEY manquant dans .env")
        sys.exit(1)

    print(f"→ Agrégation campagne « {client} »\n")
    ctx = get_campaign_context(client, max_conversations=10, max_recent_comments_feed=10)

    print(f"  {ctx['conversation_count']} conversation(s) trouvée(s).\n")

    print("─── Conversations ────────────────────────────────")
    for c in ctx["conversations"]:
        subject = (c["subject"] or "")[:75]
        parts = ", ".join(c.get("participants", [])[:3])
        n_com = c.get("comment_count", 0)
        com_flag = f"💬 {n_com}" if n_com else "     "
        status = f"[{c.get('status', '?')}]".ljust(13)
        print(f"  {status} {com_flag}  {subject}")
        if parts:
            print(f"                       ↳ {parts[:80]}")

    print("\n─── Feed activité équipe (derniers commentaires) ────")
    feed = ctx.get("recent_team_comments", [])
    if not feed:
        print("  (aucun commentaire interne sur ces conversations)")
    else:
        for cm in feed:
            author = cm.get("author_name", "?")
            when = (cm.get("posted_at") or "")[:16]
            text = (cm.get("text") or "").replace("\n", " ")[:100]
            subj = (cm.get("conversation_subject") or "")[:40]
            print(f"  · {author:<20} {when}  « {text} »")
            if subj:
                print(f"                                  sur : {subj}")

    print("\n✅ Terminé.")


if __name__ == "__main__":
    main()
