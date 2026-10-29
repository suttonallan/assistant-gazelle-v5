#!/usr/bin/env python3
"""
Front : une conversation ARCHIVÉE ne doit plus remonter dans la boîte
personnelle des coéquipiers.

Cas réel (2026-10-29) : Allan écrit « fait » en commentaire puis archive une
conversation de info@. Le commentaire est une « nouvelle activité » : Front la
fait remonter chez tous les abonnés (ex. Nicolas), alors qu'elle est réglée.

Règle générale : aux 15 minutes, chaque conversation de info@ archivée
récemment est désabonnée de tous les coéquipiers. Rien n'est effacé. Si le
client réécrit, Front rouvre la conversation dans info@ (visible de tous) ; si
quelqu'un mentionne un collègue (@nom), ce collègue est réabonné normalement.
"""
import time
from typing import Dict

INBOX_INFO = "inb_342mn"
JOURS_A_SURVEILLER = 3
CLE_TRAITEES = "front_archives_desabonnees"


def _derniere_activite(conv: Dict) -> float:
    return float(conv.get("updated_at") or (conv.get("last_message") or {}).get("created_at")
                 or conv.get("created_at") or 0)


def desabonner_archives() -> Dict[str, int]:
    """Point d'entrée de la tâche planifiée."""
    from core.front_client import get_front_client
    from core.supabase_storage import SupabaseStorage

    stats = {"archivees": 0, "desabonnees": 0, "abonnes_retires": 0}
    front = get_front_client()
    db = SupabaseStorage()
    deja = db.get_system_setting(CLE_TRAITEES) or []

    depuis = time.time() - JOURS_A_SURVEILLER * 86400
    convs = front.search_conversations(f"inbox:{INBOX_INFO} is:archived", limit=100)

    nouvelles = []
    for conv in convs:
        activite = _derniere_activite(conv)
        if activite < depuis:
            continue
        stats["archivees"] += 1
        # Clé = conversation + dernière activité : une nouvelle activité après
        # coup (commentaire sur une conversation archivée) est retraitée.
        cle = f"{conv['id']}:{int(activite)}"
        if cle in deja:
            continue
        try:
            # Un @nom dans le dernier commentaire = on veut avertir quelqu'un :
            # on ne touche à rien (il doit voir la mention).
            commentaires = front.list_comments(conv["id"], limit=5)
            if commentaires:
                dernier = max(commentaires, key=lambda c: c.get("posted_at") or 0)
                if "@" in (dernier.get("body") or ""):
                    nouvelles.append(cle)
                    continue
            ids = [t["id"] for t in front.lister_abonnes(conv["id"]) if t.get("id")]
            front.retirer_abonnes(conv["id"], ids)
            stats["desabonnees"] += 1 if ids else 0
            stats["abonnes_retires"] += len(ids)
            nouvelles.append(cle)
        except Exception as e:
            print(f"⚠️ Désabonnement impossible ({conv['id']}) : {e}")

    if nouvelles:
        db.save_system_setting(CLE_TRAITEES, (deja + nouvelles)[-1000:])
    return stats


if __name__ == "__main__":
    print(desabonner_archives())
