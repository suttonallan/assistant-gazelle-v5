"""Provenance d'un client (« comment nous avez-vous trouvés ? »).

Gazelle a des champs natifs pour ça dans la fiche client : « Référé par »
(referredBy), ses notes (referredByNotes) et le client référent (referralClient).
On considère aussi la réponse connue si les notes de la fiche la mentionnent.
"""
import re
from typing import Optional

RAPPEL_PROVENANCE = ("Nouveau client : lui demander comment il nous a trouvés "
                     "(puis l'inscrire dans « Référé par » de sa fiche Gazelle).")

_MOTS = re.compile(r"(nous a trouv|nous ont trouv|référé|refere|référence|recommand|bouche[- ]à[- ]oreille|"
                   r"referred|found us|via google|trouvé sur)", re.IGNORECASE)


def provenance_connue(client_id: str) -> Optional[bool]:
    """True si la fiche Gazelle dit déjà comment le client nous a trouvés ; None si on ne sait pas."""
    try:
        from core.gazelle_api_client import GazelleAPIClient
        res = GazelleAPIClient()._execute_query(
            "query($id: String!) { client(id: $id) { referredBy referredByNotes referralClient { id } "
            "personalNotes preferenceNotes } }", {"id": client_id})
        c = ((res or {}).get("data") or {}).get("client")
        if c is None:
            return None
        if (c.get("referredBy") or "").strip() or (c.get("referredByNotes") or "").strip() or c.get("referralClient"):
            return True
        notes = f"{c.get('personalNotes') or ''} {c.get('preferenceNotes') or ''}"
        return bool(_MOTS.search(notes))
    except Exception:
        return None


def faut_demander(client_id: str) -> bool:
    """À rappeler seulement si on est SÛR que la provenance n'est pas connue."""
    return provenance_connue(client_id) is False
