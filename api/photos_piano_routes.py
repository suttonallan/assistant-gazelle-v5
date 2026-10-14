"""Photos de piano — ajouter au dossier Gazelle d'un piano les photos reçues par courriel (Front).

- GET  /photos-piano/schema?q=…            : diagnostic du schéma Gazelle (lecture seule)
- GET  /photos-piano/client/{id}/pianos    : pianos d'un client
- POST /photos-piano/depuis-front          : télécharge les images d'un message Front
  et les dépose comme pièces jointes sur le piano Gazelle.

Téléversement Gazelle (API privée) : createUpload → PUT sur l'URL présignée S3
→ completeUpload. Aucune clé dans le code : Front (FRONT_API_KEY) et Gazelle
(jeton Supabase) viennent de l'environnement du serveur.
"""
import os
from typing import Any, Dict, List, Optional

import requests
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core.gazelle_api_client import GazelleAPIClient

router = APIRouter(prefix="/photos-piano", tags=["photos-piano"])

_INTROSPECTION = """
query {
  __schema {
    mutationType { fields { name args { name type { name kind ofType { name kind ofType { name kind } } } } } }
    types { name kind enumValues { name } inputFields { name type { name kind ofType { name kind ofType { name kind } } } }
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


_CREATE_UPLOAD = """mutation($input: PrivateCreateUploadInput!) {
  createUpload(input: $input) {
    mutationErrors { fieldName messages }
    attachment { id }
    upload { presignedUrl bucket key region }
  } }"""
_COMPLETE_UPLOAD = """mutation($id: String!) {
  completeUpload(id: $id) { mutationErrors { fieldName messages } attachment { id } } }"""


class DepuisFrontRequest(BaseModel):
    piano_id: str
    message_id: str                      # msg_xxx (message Front contenant les photos)
    attachable_type: str = "PIANO"
    seulement_images: bool = True


def _front_message(message_id: str) -> Dict[str, Any]:
    cle = os.getenv("FRONT_API_KEY")
    if not cle:
        raise HTTPException(status_code=500, detail="FRONT_API_KEY absente sur le serveur")
    r = requests.get(f"https://api2.frontapp.com/messages/{message_id}",
                     headers={"Authorization": f"Bearer {cle}"}, timeout=20)
    r.raise_for_status()
    return r.json()


def _front_telecharger(url: str) -> bytes:
    r = requests.get(url, headers={"Authorization": f"Bearer {os.getenv('FRONT_API_KEY')}"}, timeout=60)
    r.raise_for_status()
    return r.content


@router.post("/depuis-front")
def depuis_front(req: DepuisFrontRequest) -> Dict[str, Any]:
    msg = _front_message(req.message_id)
    pieces = [a for a in msg.get("attachments", [])
              if not req.seulement_images or (a.get("content_type") or "").startswith("image/")]
    if not pieces:
        raise HTTPException(status_code=404, detail="Aucune image dans ce message Front")
    gz = GazelleAPIClient()
    resultats: List[Dict[str, Any]] = []
    for a in pieces:
        nom = a.get("filename") or "photo.jpg"
        try:
            data = _front_telecharger(a["url"])
            res = gz._execute_query(_CREATE_UPLOAD, {"input": {
                "attachableType": req.attachable_type, "attachableId": req.piano_id,
                "filename": nom, "fileSizeBytes": len(data),
                "mimeHint": a.get("content_type") or "image/jpeg"}})
            if res.get("errors"):
                resultats.append({"fichier": nom, "erreur": res["errors"]}); continue
            cu = res["data"]["createUpload"]
            if cu.get("mutationErrors"):
                resultats.append({"fichier": nom, "erreur": cu["mutationErrors"]}); continue
            att_id = (cu.get("attachment") or {}).get("id")
            url = (cu.get("upload") or {}).get("presignedUrl")
            if not url:
                resultats.append({"fichier": nom, "erreur": "pas d'URL présignée", "upload": cu.get("upload")}); continue
            put = requests.put(url, data=data, headers={"Content-Type": a.get("content_type") or "image/jpeg"}, timeout=120)
            if put.status_code >= 300:
                put = requests.put(url, data=data, timeout=120)  # URL signée sans Content-Type
            if put.status_code >= 300:
                gz._execute_query("mutation($id:String!){cancelUpload(id:$id){isCancelled}}", {"id": att_id})
                resultats.append({"fichier": nom, "erreur": f"S3 {put.status_code}: {put.text[:300]}"}); continue
            fin = gz._execute_query(_COMPLETE_UPLOAD, {"id": att_id})
            cp = (fin.get("data") or {}).get("completeUpload") or {}
            resultats.append({"fichier": nom, "attachment_id": att_id,
                              "erreur": fin.get("errors") or cp.get("mutationErrors") or None})
        except Exception as e:  # une photo en échec n'empêche pas les autres
            resultats.append({"fichier": nom, "erreur": str(e)[:300]})
    ok = [r for r in resultats if not r.get("erreur")]
    return {"piano_id": req.piano_id, "ajoutees": len(ok), "total": len(resultats), "resultats": resultats}
