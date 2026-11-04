"""Survol de la provenance des clients (« Référé par ») — propositions à décider par Allan."""
import threading
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/provenance", tags=["provenance"])
_verrou = threading.Lock()


@router.post("/survol")
def lancer_survol():
    """Lance le survol en arrière-plan (quelques minutes). Lecture seule dans Gazelle."""
    from core.provenance_survol import lancer, lire
    if lire().get("statut") == "en cours" and _verrou.locked():
        return {"statut": "déjà en cours"}

    def tache():
        with _verrou:
            try:
                lancer()
            except Exception as e:
                print(f"⚠️ Survol provenance : {e}")

    threading.Thread(target=tache, daemon=True).start()
    return {"statut": "lancé"}


@router.get("/survol")
def resultats():
    from core.provenance_survol import lire
    return lire()


class DecisionIn(BaseModel):
    client_id: str
    decision: str  # approuver | discuter | refuser
    note: str = ""
    valeur: Optional[str] = None  # provenance corrigée avant d'approuver


@router.post("/decision")
def decision(d: DecisionIn):
    from core.provenance_survol import decider
    if d.decision not in ("approuver", "discuter", "refuser"):
        raise HTTPException(400, "decision : approuver, discuter ou refuser")
    try:
        return decider(d.client_id, d.decision, d.note, d.valeur or "")
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(404, str(e))
