"""Photos de piano — ajouter au dossier Gazelle d'un piano les photos reçues par courriel (Front).

Étape 1 (diagnostic, lecture seule) : explorer le schéma Gazelle pour trouver
comment Gazelle accepte une photo de piano, et lister les pianos d'un client.
"""
from typing import Any, Dict

from fastapi import APIRouter, HTTPException

from core.gazelle_api_client import GazelleAPIClient

router = APIRouter(prefix="/photos-piano", tags=["photos-piano"])

_INTROSPECTION = """
query {
  __schema {
    mutationType { fields { name args { name type { name kind ofType { name kind ofType { name kind } } } } } }
    types { name kind inputFields { name type { name kind ofType { name kind ofType { name kind } } } }
            fields { name type { name kind ofType { name kind } } } }
  }
}
"""


@router.get("/schema")
def schema(q: str = "photo") -> Dict[str, Any]:
    """Mutations et types du schéma Gazelle dont le nom contient `q` (lecture seule)."""
    res = GazelleAPIClient()._execute_query(_INTROSPECTION)
    sch = (res.get("data") or {}).get("__schema") or {}
    ql = q.lower()
    mutations = [m for m in (sch.get("mutationType") or {}).get("fields", []) if ql in m["name"].lower()]
    types = [t for t in sch.get("types", []) if ql in (t.get("name") or "").lower()]
    return {"mutations": mutations, "types": types}


@router.get("/client/{client_id}/pianos")
def pianos_du_client(client_id: str) -> Dict[str, Any]:
    q = """query($id: String!) { client(id: $id) { id
      allPianos { nodes { id make model serialNumber type location } } } }"""
    res = GazelleAPIClient()._execute_query(q, {"id": client_id})
    if res.get("errors"):
        raise HTTPException(status_code=502, detail=res["errors"])
    return res.get("data") or {}
