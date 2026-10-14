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


def deposer_images(piano_id: str, pieces: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Dépose sur un piano Gazelle des pièces jointes Front ({filename, url, content_type}).
    Les fichiers déjà présents sur le piano (même nom et même taille) sont ignorés."""
    gz = GazelleAPIClient()
    deja = set()
    try:
        ex = pieces_du_piano(piano_id)
        for n in ((ex.get("piano") or {}).get("attachments") or {}).get("nodes", []):
            deja.add(n.get("filename"))
    except Exception:
        pass
    resultats: List[Dict[str, Any]] = []
    for a in pieces:
        nom = a.get("filename") or "photo.jpg"
        if nom in deja:
            resultats.append({"fichier": nom, "ignore": "déjà sur le piano"}); continue
        try:
            data = _front_telecharger(a["url"])
            res = gz._execute_query(_CREATE_UPLOAD, {"input": {
                "attachableType": "PIANO", "attachableId": piano_id,
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
                resultats.append({"fichier": nom, "erreur": "pas d'URL présignée"}); continue
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
    ok = [r for r in resultats if r.get("attachment_id") and not r.get("erreur")]
    ignores = [r for r in resultats if r.get("ignore")]
    return {"piano_id": piano_id, "ajoutees": len(ok), "deja_presentes": len(ignores),
            "total": len(resultats), "resultats": resultats}


def _est_image(a: Dict[str, Any]) -> bool:
    return ((a.get("content_type") or "").startswith("image/")
            and not (a.get("metadata") or {}).get("is_inline"))


@router.post("/depuis-front")
def depuis_front(req: DepuisFrontRequest) -> Dict[str, Any]:
    msg = _front_message(req.message_id)
    pieces = [a for a in msg.get("attachments", []) if not req.seulement_images or _est_image(a)]
    if not pieces:
        raise HTTPException(status_code=404, detail="Aucune image dans ce message Front")
    return deposer_images(req.piano_id, pieces)


# ── Outil de l'Assistant : « ajoute au piano de X les photos de son courriel » ──

def _chercher_clients(nom: str) -> List[Dict[str, Any]]:
    from core.supabase_storage import SupabaseStorage
    st = SupabaseStorage(silent=True)
    mots = [m for m in nom.replace(",", " ").split() if len(m) >= 2]
    if not mots:
        return []
    filtre = ",".join(f"{c}.ilike.*{mots[-1]}*" for c in ("first_name", "last_name", "company_name"))
    r = requests.get(f"{st.api_url}/gazelle_clients?select=external_id,first_name,last_name,company_name,email"
                     f"&or=({filtre})&limit=30", headers=st._get_headers(), timeout=20)
    lignes = r.json() if r.status_code == 200 else []
    def nom_de(c):
        return (c.get("company_name") or f"{c.get('first_name') or ''} {c.get('last_name') or ''}").strip()
    # garder ceux qui contiennent TOUS les mots donnés
    bons = [c for c in lignes if all(m.lower() in (nom_de(c) + " " + (c.get("email") or "")).lower() for m in mots)]
    return [{"client_id": c["external_id"], "nom": nom_de(c), "email": c.get("email")} for c in (bons or lignes)][:8]


def _images_recues(email: str, toutes: bool, jours: int = 60) -> List[Dict[str, Any]]:
    """Images reçues du client par courriel (messages entrants Front), la plus récente d'abord.
    toutes=False → seulement le dernier message qui contient des images."""
    import time
    from core.front_client import get_front_client
    fc = get_front_client()
    limite = time.time() - jours * 86400
    convs = fc.conversations_contact(email, limit=15).get("conversations", [])
    messages = []
    for cv in convs[:15]:
        for m in fc.list_messages(cv["id"], limit=50):
            if not m.get("is_inbound") or (m.get("created_at") or 0) < limite:
                continue
            imgs = [a for a in m.get("attachments", []) if _est_image(a)]
            if imgs:
                messages.append((m.get("created_at") or 0, m["id"], imgs))
    messages.sort(key=lambda x: x[0], reverse=True)
    if not messages:
        return []
    choisis = messages if toutes else messages[:1]
    pieces, vus = [], set()
    for _, _, imgs in choisis:
        for a in imgs:
            if a.get("filename") not in vus:
                vus.add(a.get("filename")); pieces.append(a)
    return pieces


ATTACH_PHOTOS_TOOL = {
    "name": "attach_email_photos_to_piano",
    "description": (
        "Ajoute au dossier Gazelle du piano d'un client (pièces jointes du piano) les photos "
        "que ce client a envoyées par courriel (boîte Front). Par défaut : les photos du "
        "dernier courriel du client qui en contient. toutes=true : toutes les photos reçues "
        "de lui dans les 60 derniers jours. Les photos déjà présentes sur le piano sont ignorées. "
        "Si le client a plusieurs pianos, l'outil renvoie la liste : demande lequel, puis "
        "rappelle l'outil avec piano_id."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "client_name": {"type": "string", "description": "Nom du client (ex. « Rebecca Boyce »)."},
            "client_email": {"type": "string", "description": "Courriel du client, si connu."},
            "piano_id": {"type": "string", "description": "ins_… si le client a plusieurs pianos."},
            "toutes": {"type": "boolean", "description": "true = toutes les photos reçues récemment."},
        },
        "required": ["client_name"],
    },
}


def execute_attach_photos(client_name: str, client_email: Optional[str] = None,
                          piano_id: Optional[str] = None, toutes: bool = False) -> Dict[str, Any]:
    clients = _chercher_clients(client_name)
    if not clients and not client_email:
        return {"success": False, "error": f"Aucun client trouvé pour « {client_name} »."}
    if len(clients) > 1 and not client_email:
        exacts = [c for c in clients if c["nom"].lower() == client_name.strip().lower()]
        if len(exacts) == 1:
            clients = exacts
        else:
            return {"success": False, "a_preciser": "Plusieurs clients correspondent.",
                    "clients": clients}
    client = clients[0] if clients else {}
    email = client_email or client.get("email")
    if not email:
        return {"success": False, "error": f"Pas de courriel connu pour {client.get('nom')}."}
    if not piano_id:
        if not client.get("client_id"):
            return {"success": False, "error": "Client introuvable dans Gazelle."}
        pianos = ((pianos_du_client(client["client_id"]).get("client") or {})
                  .get("allPianos") or {}).get("nodes", [])
        if not pianos:
            return {"success": False, "error": f"{client.get('nom')} n'a aucun piano dans Gazelle."}
        if len(pianos) > 1:
            return {"success": False, "a_preciser": "Ce client a plusieurs pianos : lequel ?",
                    "pianos": pianos}
        piano_id = pianos[0]["id"]
    pieces = _images_recues(email, toutes)
    if not pieces:
        return {"success": False, "error": f"Aucune photo reçue de {email} dans Front (60 derniers jours)."}
    res = deposer_images(piano_id, pieces)
    res["success"] = res["ajoutees"] > 0 or res["deja_presentes"] > 0
    res["client"] = client.get("nom") or email
    return res


@router.get("/piano/{piano_id}")
def pieces_du_piano(piano_id: str) -> Dict[str, Any]:
    """Pièces jointes (photos) d'un piano Gazelle, avec leur état de traitement."""
    q = """query($id: String!) { piano(id: $id) { id make totalAttachmentsCount
      attachments { nodes { id filename status type createdAt } } } }"""
    res = GazelleAPIClient()._execute_query(q, {"id": piano_id})
    if res.get("errors"):
        raise HTTPException(status_code=502, detail=res["errors"])
    return res.get("data") or {}
