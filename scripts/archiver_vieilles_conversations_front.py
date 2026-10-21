"""Ménage ponctuel de Front : archive les conversations ouvertes sans activité
depuis une date limite, dans les boîtes info@ et asutton@.

Pourquoi : presque rien n'avait jamais été archivé (≈ 47 000 conversations
ouvertes). Avec « Send & archive » par défaut, une conversation qui revient
dans la liste = du nouveau. Le ménage initial rend ce signal utilisable.

Sécurité :
- Archiver n'efface rien : une conversation archivée se retrouve par la
  recherche et revient d'elle-même dès qu'il y a un nouveau message ou
  commentaire.
- La recherche Front `before:` vise « n'importe quel message », donc on
  revérifie la dernière activité de chaque conversation avant d'archiver :
  si elle est postérieure à la date limite, on ne touche pas.
- Idempotent : relancer le script ne fait que continuer le travail.

Clé : FRONT_API_KEY (variable d'env) ou, à défaut, le jeton Front gardé dans
Supabase `system_settings`.
"""
import os
import sys
import time
import urllib.parse
from datetime import datetime, timezone

import requests

BASE = "https://api2.frontapp.com"
BOITES = {"info": "inb_342mn", "asutton": "inb_342j3"}
# Date limite fixe : ménage unique, pas une règle permanente.
LIMITE = datetime(2026, 10, 7, 4, 0, tzinfo=timezone.utc)  # 7 oct. 00 h, Montréal
DUREE_MAX_S = int(os.getenv("DUREE_MAX_S", str(5 * 3600 + 30 * 60)))
SIMULATION = os.getenv("SIMULATION", "0") == "1"


def _cle_front() -> str:
    cle = os.getenv("FRONT_API_KEY") or os.getenv("FRONT_API_TOKEN")
    if cle:
        return cle.strip()
    url = os.getenv("SUPABASE_URL", "").rstrip("/")
    sk = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
    if not (url and sk):
        sys.exit("Aucune clé Front (FRONT_API_KEY) ni accès Supabase.")
    h = {"apikey": sk, "Authorization": f"Bearer {sk}"}
    r = requests.get(f"{url}/rest/v1/system_settings?select=key,value&key=ilike.*front*",
                     headers=h, timeout=20)
    r.raise_for_status()
    for ligne in r.json():
        v = ligne.get("value")
        if isinstance(v, dict):
            v = v.get("token") or v.get("api_key") or v.get("value")
        if isinstance(v, str) and len(v) > 20:
            _avis(f"Clé Front lue dans system_settings ({ligne['key']}).")
            return v.strip()
    _avis("Clé Front introuvable dans system_settings.")
    sys.exit(1)


class Front:
    def __init__(self, cle: str):
        self.s = requests.Session()
        self.s.headers.update({"Authorization": f"Bearer {cle}",
                               "Accept": "application/json"})

    def _req(self, methode: str, url: str, **kw):
        for essai in range(8):
            r = self.s.request(methode, url, timeout=30, **kw)
            if r.status_code == 429:
                attente = float(r.headers.get("Retry-After", "10"))
                time.sleep(min(max(attente, 1), 120))
                continue
            if r.status_code >= 500:
                time.sleep(5 * (essai + 1))
                continue
            return r
        return r

    def chercher(self, requete: str, page_token: str = None):
        url = f"{BASE}/conversations/search/{urllib.parse.quote(requete)}"
        params = {"limit": 100}
        if page_token:
            params["page_token"] = page_token
        r = self._req("GET", url, params=params)
        r.raise_for_status()
        return r.json()

    def archiver(self, cid: str) -> bool:
        r = self._req("PATCH", f"{BASE}/conversations/{cid}",
                      json={"status": "archived"})
        return r.status_code in (200, 204)


def _derniere_activite(conv: dict):
    """Plus récente date connue (secondes Unix) ; None si inconnue."""
    dates = []
    for champ in ("updated_at", "last_activity_at"):
        if conv.get(champ):
            dates.append(float(conv[champ]))
    lm = conv.get("last_message") or {}
    if lm.get("created_at"):
        dates.append(float(lm["created_at"]))
    return max(dates) if dates else None


def menage_boite(front: Front, nom: str, inbox_id: str, debut: float) -> dict:
    limite_s = int(LIMITE.timestamp())
    requete = f"inbox:{inbox_id} is:open before:{limite_s}"
    stats = {"archivees": 0, "gardees_recentes": 0, "erreurs": 0}
    vus = set()
    page_token = None
    while time.time() - debut < DUREE_MAX_S:
        data = front.chercher(requete, page_token)
        resultats = data.get("_results", [])
        if page_token is None:
            _avis(f"[{nom}] {data.get('_total', '?')} trouvées, {len(resultats)} sur la 1re page")
        nouveaux = [c for c in resultats if c["id"] not in vus]
        for conv in nouveaux:
            vus.add(conv["id"])
            act = _derniere_activite(conv)
            if act is None or act >= limite_s:
                stats["gardees_recentes"] += 1
                continue
            if SIMULATION or front.archiver(conv["id"]):
                stats["archivees"] += 1
            else:
                stats["erreurs"] += 1
            if stats["archivees"] % 500 == 0 and stats["archivees"]:
                print(f"[{nom}] {stats['archivees']} archivées…", flush=True)
        if not resultats:
            break
        # Les conversations archivées sortent des résultats : on relit la
        # première page tant qu'elle apporte du neuf ; sinon page suivante.
        if nouveaux and not SIMULATION:
            page_token = None
            continue
        suivant = (data.get("_pagination") or {}).get("next")
        if not suivant:
            break
        page_token = urllib.parse.parse_qs(urllib.parse.urlparse(suivant).query).get(
            "page_token", [None])[0]
        if not page_token:
            break
    return stats


def _avis(msg: str):
    """Visible dans l'onglet Actions (annotation), même sans accès aux logs."""
    print(msg, flush=True)
    if os.getenv("GITHUB_ACTIONS"):
        print(f"::notice title=Menage Front::{msg}", flush=True)


def main():
    front = Front(_cle_front())
    moi = front._req("GET", f"{BASE}/me")
    _avis(f"Jeton Front : HTTP {moi.status_code} {moi.text[:120]}")
    debut = time.time()
    print(f"Limite : {LIMITE.isoformat()} — simulation={SIMULATION}")
    for nom, inbox_id in BOITES.items():
        try:
            stats = menage_boite(front, nom, inbox_id, debut)
            _avis(f"[{nom}] terminé : {stats}")
        except requests.HTTPError as e:
            corps = e.response.text[:200] if e.response is not None else ""
            _avis(f"[{nom}] erreur Front : {e} {corps}")
    print(f"Durée : {int(time.time() - debut)} s")


if __name__ == "__main__":
    main()
