"""
Clients Gazelle → contacts externes partagés de Zoom Phone.

But : quand un client appelle, Louise et les techniciens voient son nom dans Zoom
au lieu d'un simple numéro.

Fonctionnement (chaque nuit, et sur demande) :
1. On lit TOUS les clients Gazelle et leurs contacts dans la copie Supabase
   (gazelle_clients + gazelle_contacts) — aucun appel à Gazelle.
2. Un contact Zoom par client Gazelle, avec tous ses numéros (fiche client + contacts).
   Un numéro partagé par deux clients ne va qu'au premier (Zoom refuse les doublons).
3. On compare avec les contacts externes déjà dans Zoom et on ne touche qu'aux
   contacts créés par l'assistant (repérés par leur description « Gazelle:<id> ») :
   création des nouveaux, mise à jour des changés, retrait de ceux dont le client a
   disparu de Gazelle. Les contacts saisis à la main dans Zoom ne sont jamais modifiés.
4. Garde-fou : si la copie Supabase paraît incomplète (beaucoup moins de clients que
   de contacts déjà dans Zoom), aucune suppression n'est faite.

Le rapport du dernier passage est gardé dans system_settings (zoom_contacts_dernier).
"""

import re
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import requests

from core.zoom_sms import get_zoom_access_token, ZOOM_API_BASE_URL
from core.timezone_utils import MONTREAL_TZ

MARQUEUR = "Gazelle:"
NUMEROS_PTM = {"5143448008", "4382285774"}
CLE_RAPPORT = "zoom_contacts_dernier"
PAUSE = 0.12  # Zoom : limite « Light » → on reste sous ~8 requêtes/s


# ---------------------------------------------------------------- Numéros

def normaliser(numero: Any) -> Optional[str]:
    """« (514) 555-1234 poste 22 » → « 5145551234 » ; None si pas un numéro nord-américain."""
    if not numero:
        return None
    texte = str(numero).split("x")[0].split("X")[0].split("#")[0]
    texte = re.split(r"(?i)poste|ext", texte)[0]
    d = re.sub(r"\D", "", texte)
    if len(d) == 11 and d.startswith("1"):
        d = d[1:]
    if len(d) != 10 or d[0] in "01" or d in NUMEROS_PTM:
        return None
    return d


def e164(d: str) -> str:
    return f"+1{d}"


# ---------------------------------------------------------------- Supabase (lecture)

def _lire_table(table: str, colonnes: str) -> List[Dict[str, Any]]:
    from core.supabase_storage import SupabaseStorage
    db = SupabaseStorage()
    h = dict(db._get_headers())
    lignes: List[Dict[str, Any]] = []
    debut = 0
    while True:
        r = requests.get(f"{db.api_url}/{table}", headers={**h, "Range": f"{debut}-{debut + 999}"},
                         params={"select": colonnes, "order": "external_id"}, timeout=30)
        if r.status_code not in (200, 206):
            raise RuntimeError(f"Supabase {table} : HTTP {r.status_code} {r.text[:200]}")
        lot = r.json()
        lignes.extend(lot)
        if len(lot) < 1000:
            return lignes
        debut += 1000


def _nom_personne(p: Dict[str, Any]) -> str:
    return " ".join(x.strip() for x in (p.get("first_name") or "", p.get("last_name") or "") if x and x.strip())


def contacts_voulus() -> List[Dict[str, Any]]:
    """Un contact Zoom par client Gazelle ayant au moins un numéro valide."""
    clients = _lire_table("gazelle_clients", "external_id,company_name,first_name,last_name,email,phone")
    contacts = _lire_table("gazelle_contacts", "external_id,client_external_id,first_name,last_name,email,phone")

    par_client: Dict[str, List[Dict[str, Any]]] = {}
    for c in contacts:
        if c.get("client_external_id"):
            par_client.setdefault(c["client_external_id"], []).append(c)

    deja_pris: Dict[str, str] = {}
    voulus: List[Dict[str, Any]] = []
    for cl in clients:
        cid = cl.get("external_id")
        if not cid:
            continue
        lies = par_client.get(cid, [])
        numeros: List[str] = []
        for source in [cl] + lies:
            d = normaliser(source.get("phone"))
            if d and d not in numeros and deja_pris.get(d, cid) == cid:
                numeros.append(d)
                deja_pris[d] = cid
        if not numeros:
            continue

        personne = _nom_personne(cl) or next((_nom_personne(c) for c in lies if _nom_personne(c)), "")
        societe = (cl.get("company_name") or "").strip()
        if societe and personne and personne.lower() not in societe.lower():
            nom = f"{societe} ({personne})"
        else:
            nom = societe or personne
        if not nom:
            continue
        courriel = (cl.get("email") or next((c.get("email") for c in lies if c.get("email")), "") or "").strip()
        voulus.append({
            "client_id": cid,
            "name": nom[:120],
            "email": courriel if "@" in courriel else "",
            "phone_numbers": [e164(d) for d in numeros[:5]],
            "description": f"{MARQUEUR}{cid}",
        })
    return voulus


# ---------------------------------------------------------------- Zoom

class Zoom:
    def __init__(self) -> None:
        self.token = get_zoom_access_token()
        self.appels = 0

    def requete(self, methode: str, chemin: str, **kw) -> requests.Response:
        for essai in range(5):
            time.sleep(PAUSE)
            self.appels += 1
            r = requests.request(methode, f"{ZOOM_API_BASE_URL}{chemin}", timeout=30,
                                 headers={"Authorization": f"Bearer {self.token}"}, **kw)
            if r.status_code == 401 and essai == 0:
                self.token = get_zoom_access_token()
                continue
            if r.status_code == 429:
                time.sleep(int(r.headers.get("Retry-After", "2") or 2) + 1)
                continue
            return r
        return r

    def lister(self) -> List[Dict[str, Any]]:
        tous: List[Dict[str, Any]] = []
        jeton = ""
        while True:
            params = {"page_size": 300}
            if jeton:
                params["next_page_token"] = jeton
            r = self.requete("GET", "/phone/external_contacts", params=params)
            if r.status_code != 200:
                raise PermissionError(f"Lecture des contacts Zoom : HTTP {r.status_code} {r.text[:300]}")
            d = r.json()
            tous.extend(d.get("external_contacts") or [])
            jeton = d.get("next_page_token") or ""
            if not jeton:
                return tous


def _id_zoom(c: Dict[str, Any]) -> str:
    return c.get("external_contact_id") or c.get("id") or ""


def _pareil(z: Dict[str, Any], v: Dict[str, Any]) -> bool:
    nz = sorted(normaliser(n) or n for n in (z.get("phone_numbers") or []))
    nv = sorted(normaliser(n) or n for n in v["phone_numbers"])
    return (z.get("name") or "") == v["name"] and nz == nv and (z.get("email") or "") == v["email"]


def _corps(v: Dict[str, Any]) -> Dict[str, Any]:
    corps = {k: v[k] for k in ("name", "phone_numbers", "description")}
    if v["email"]:
        corps["email"] = v["email"]
    return corps


def _envoyer(zoom: "Zoom", methode: str, chemin: str, v: Dict[str, Any]) -> requests.Response:
    """Envoie le contact ; si Zoom refuse (400), réessaie sans courriel, puis avec un nom simplifié."""
    corps = _corps(v)
    r = zoom.requete(methode, chemin, json=corps)
    if r.status_code != 400:
        return r
    corps.pop("email", None)
    r = zoom.requete(methode, chemin, json=corps)
    if r.status_code != 400:
        return r
    corps["name"] = (re.sub(r"[^\w\s'&().,-]", " ", corps["name"]).strip() or "Client Gazelle")[:60]
    return zoom.requete(methode, chemin, json=corps)


# ---------------------------------------------------------------- Synchronisation

def synchroniser(essai_a_blanc: bool = False, maximum: Optional[int] = None) -> Dict[str, Any]:
    debut = time.time()
    rapport: Dict[str, Any] = {"debut": datetime.now(MONTREAL_TZ).isoformat(timespec="seconds"),
                               "essai_a_blanc": essai_a_blanc}
    voulus = contacts_voulus()
    zoom = Zoom()
    existants = zoom.lister()

    a_nous: Dict[str, Dict[str, Any]] = {}
    manuels: List[Dict[str, Any]] = []
    for z in existants:
        desc = z.get("description") or ""
        if desc.startswith(MARQUEUR):
            a_nous[desc[len(MARQUEUR):].strip()] = z
        else:
            manuels.append(z)

    # Reprise de l'ancien import : un contact manuel dont un numéro est celui d'un client
    # Gazelle (pas encore suivi) est pris en charge par l'assistant — un seul par client.
    proprio_num = {normaliser(n): v["client_id"] for v in voulus for n in v["phone_numbers"]}
    repris: Dict[str, Dict[str, Any]] = {}
    numeros_manuels = set()
    for z in manuels:
        nums = [d for d in (normaliser(n) for n in z.get("phone_numbers") or []) if d]
        cid = next((proprio_num[d] for d in nums if d in proprio_num), None)
        if cid and cid not in a_nous and cid not in repris:
            repris[cid] = z
        else:
            numeros_manuels.update(nums)  # contact laissé tel quel : ses numéros restent à lui

    a_creer: List[Dict[str, Any]] = []
    a_modifier: List[Tuple[str, Dict[str, Any]]] = []
    for v in voulus:
        z = a_nous.get(v["client_id"]) or repris.get(v["client_id"])
        # Pas de numéro déjà tenu par un contact manuel qu'on ne gère pas (doublon),
        # sauf si notre contact l'a déjà lui-même.
        siens = {normaliser(n) for n in (z or {}).get("phone_numbers") or []}
        v["phone_numbers"] = [n for n in v["phone_numbers"]
                              if normaliser(n) not in numeros_manuels or normaliser(n) in siens]
        if not v["phone_numbers"]:
            continue
        if z is None:
            a_creer.append(v)
        elif v["client_id"] in repris or not _pareil(z, v):
            a_modifier.append((_id_zoom(z), v))
    rapport["repris_de_l_ancien_import"] = len(repris)
    ids_voulus = {v["client_id"] for v in voulus}
    a_retirer = [_id_zoom(z) for cid, z in a_nous.items() if cid not in ids_voulus]

    garde_fou = len(a_nous) > 50 and len(voulus) < 0.7 * len(a_nous)
    if garde_fou:
        a_retirer = []

    rapport.update({
        "clients_avec_numero": len(voulus),
        "contacts_zoom_total": len(existants),
        "contacts_zoom_assistant": len(a_nous),
        "contacts_zoom_manuels": len(existants) - len(a_nous),
        "a_creer": len(a_creer), "a_modifier": len(a_modifier), "a_retirer": len(a_retirer),
        "garde_fou_suppressions": garde_fou,
    })

    crees = modifies = retires = 0
    erreurs: List[str] = []
    if not essai_a_blanc:
        limite = maximum if maximum is not None else 10 ** 9
        for v in a_creer[:limite]:
            r = _envoyer(zoom, "POST", "/phone/external_contacts", v)
            if r.status_code in (200, 201):
                crees += 1
            else:
                erreurs.append(f"création {v['client_id']} : HTTP {r.status_code} {r.text[:150]}")
                if r.status_code in (400, 401, 403) and crees == 0 and len(erreurs) >= 3:
                    break  # permission manquante ou format refusé : inutile d'insister
        for zid, v in a_modifier[:limite]:
            r = _envoyer(zoom, "PATCH", f"/phone/external_contacts/{zid}", v)
            if r.status_code in (200, 204):
                modifies += 1
            else:
                erreurs.append(f"mise à jour {v['client_id']} : HTTP {r.status_code} {r.text[:150]}")
        for zid in a_retirer[:limite]:
            r = zoom.requete("DELETE", f"/phone/external_contacts/{zid}")
            if r.status_code in (200, 204):
                retires += 1
            else:
                erreurs.append(f"retrait {zid} : HTTP {r.status_code} {r.text[:150]}")

    rapport.update({"crees": crees, "modifies": modifies, "retires": retires,
                    "erreurs": len(erreurs), "exemples_erreurs": erreurs[:5],
                    "appels_zoom": zoom.appels, "duree_s": round(time.time() - debut),
                    "fin": datetime.now(MONTREAL_TZ).isoformat(timespec="seconds")})
    if not essai_a_blanc:
        try:
            from core.supabase_storage import SupabaseStorage
            SupabaseStorage().save_system_setting(CLE_RAPPORT, rapport)
        except Exception as e:
            print(f"⚠️ Rapport contacts Zoom non enregistré : {e}")
    return rapport


def dernier_rapport() -> Optional[Dict[str, Any]]:
    from core.supabase_storage import SupabaseStorage
    return SupabaseStorage().get_system_setting(CLE_RAPPORT)
