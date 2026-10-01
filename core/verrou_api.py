"""Verrou de l'API — le PIN est vérifié par le serveur, qui remet un jeton signé.

Pourquoi : jusqu'ici le PIN n'était vérifié que dans la page (les PIN étaient
lisibles dans le code du site) et le serveur répondait à n'importe qui.

Fonctionnement :
  - POST /api/auth/connexion {pin}  → jeton signé (30 jours) + profil
  - Chaque appel à l'API envoie « Authorization: Bearer <jeton> ».
  - Les tâches automatiques (GitHub Actions) envoient « X-Cle-Service » = la clé
    service Supabase, qu'elles ont déjà dans leurs secrets.
  - Le webhook Zoom, la page d'accueil /health et le retour OAuth restent ouverts.

Déploiement en deux temps (flag system_settings « flag_api_verrou ») :
  - absent / false → mode OBSERVATION : rien n'est bloqué, les appels sans jeton
    sont comptés (GET /api/auth/journal) pour repérer un appelant oublié.
  - true → mode VERROU : les appels sans jeton reçoivent 401.

Secrets : la clé de signature et la table des PIN vivent dans system_settings
(jamais dans le code : le dépôt est public). Créées au premier démarrage.
"""
import base64
import hashlib
import hmac
import json
import os
import secrets
import threading
import time
from typing import Any, Dict, Optional

from core.supabase_storage import SupabaseStorage

DUREE_JETON = 30 * 86400
CHEMINS_OUVERTS = (
    "/api/auth/connexion",
    "/auth/connexion",
    "/api/auth/google",
    "/auth/google",
    "/api/auth/config",
    "/auth/config",
    "/api/zoom/webhook",
    "/gazelle_oauth_callback",
    "/health",
)
CHEMINS_OUVERTS_EXACTS = {"/", "/api/health", "/favicon.ico"}

# Profils de l'équipe (sans PIN : les PIN sont dans system_settings.pins_equipe)
# La page retrouve l'utilisateur complet par son courriel.
PROFILS = {
    "allan": {"email": "asutton@piano-tek.com"},
    "louise": {"email": "info@piano-tek.com"},
    "nick": {"email": "nlessard@piano-tek.com"},
    "jp": {"email": "jpreny@gmail.com"},
    "margot": {"email": "margotcharignon@gmail.com"},
    "alexandre": {"email": "alexandre.bourke@gmail.com"},
    "guillaume": {"email": "guillaume@laccordeur.ca"},
}

_etat: Dict[str, Any] = {"secret": None, "pins": None, "charge": 0}
_verrou = threading.Lock()
_echecs: Dict[str, list] = {}
_journal: Dict[str, Dict[str, Any]] = {}


def _storage() -> SupabaseStorage:
    return SupabaseStorage(silent=True)


def _hacher_pin(pin: str, sel: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", pin.encode(), sel.encode(), 100_000).hex()


def _charger() -> None:
    """Charge (ou crée au premier démarrage) la clé de signature et les PIN hachés."""
    with _verrou:
        if _etat["secret"] and time.time() - _etat["charge"] < 300:
            return
        st = _storage()
        secret_ = st.get_system_setting("api_cle_signature")
        if not secret_:
            secret_ = secrets.token_hex(32)
            st.save_system_setting("api_cle_signature", secret_)
        pins = st.get_system_setting("pins_equipe")
        if isinstance(pins, str):
            try:
                pins = json.loads(pins)
            except ValueError:
                pins = None
        if not pins:
            # Premier démarrage : reprise des PIN actuels (déjà publics, à changer ensuite).
            anciens = {"allan": "6342", "louise": "6343", "nick": "6344", "jp": "6345",
                       "margot": "6341", "alexandre": "6346", "guillaume": "6348"}
            pins = {}
            for role, pin in anciens.items():
                sel = secrets.token_hex(8)
                pins[role] = {"sel": sel, "hash": _hacher_pin(pin, sel)}
            st.save_system_setting("pins_equipe", pins)
        _etat.update(secret=secret_, pins=pins, charge=time.time())


def _signer(charge_utile: Dict[str, Any]) -> str:
    _charger()
    corps = base64.urlsafe_b64encode(json.dumps(charge_utile, separators=(",", ":")).encode()).decode().rstrip("=")
    sig = hmac.new(_etat["secret"].encode(), corps.encode(), hashlib.sha256).hexdigest()
    return f"{corps}.{sig}"


def verifier_jeton(jeton: str) -> Optional[Dict[str, Any]]:
    try:
        corps, sig = jeton.split(".", 1)
        _charger()
        attendu = hmac.new(_etat["secret"].encode(), corps.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, attendu):
            return None
        donnees = json.loads(base64.urlsafe_b64decode(corps + "=" * (-len(corps) % 4)))
        if donnees.get("exp", 0) < time.time():
            return None
        return donnees
    except Exception:
        return None


def connexion(pin: str, ip: str) -> Optional[Dict[str, Any]]:
    """Vérifie le PIN (5 essais ratés par 15 min par adresse). Retourne jeton + profil."""
    maintenant = time.time()
    essais = [t for t in _echecs.get(ip, []) if maintenant - t < 900]
    if len(essais) >= 5:
        raise PermissionError("Trop d'essais. Réessayez dans 15 minutes.")
    _charger()
    for role, h in (_etat["pins"] or {}).items():
        if hmac.compare_digest(_hacher_pin(pin, h["sel"]), h["hash"]):
            _echecs.pop(ip, None)
            jeton = _signer({"qui": role, "exp": int(maintenant + DUREE_JETON)})
            return {"jeton": jeton, "qui": role, **PROFILS.get(role, {})}
    essais.append(maintenant)
    _echecs[ip] = essais
    return None


def changer_pin(role: str, nouveau: str) -> None:
    if not (nouveau.isdigit() and 4 <= len(nouveau) <= 8):
        raise ValueError("Le PIN doit contenir de 4 à 8 chiffres.")
    _charger()
    pins = dict(_etat["pins"])
    for autre, h in pins.items():
        if autre != role and hmac.compare_digest(_hacher_pin(nouveau, h["sel"]), h["hash"]):
            raise ValueError("Ce PIN est déjà utilisé.")
    sel = secrets.token_hex(8)
    pins[role] = {"sel": sel, "hash": _hacher_pin(nouveau, sel)}
    _storage().save_system_setting("pins_equipe", pins)
    _etat.update(pins=pins, charge=time.time())


def est_ouvert(chemin: str) -> bool:
    return chemin in CHEMINS_OUVERTS_EXACTS or any(chemin.startswith(c) for c in CHEMINS_OUVERTS)


def _role_jwt(cle: str) -> Optional[str]:
    """Rôle inscrit dans une clé Supabase de type JWT (« anon », « service_role »), sinon None."""
    if not cle or not cle.startswith("eyJ") or cle.count(".") != 2:
        return None
    try:
        corps = cle.split(".")[1]
        return json.loads(base64.urlsafe_b64decode(corps + "=" * (-len(corps) % 4))).get("role")
    except Exception:
        return None


def _cles_service() -> list:
    """Clés service connues de Render. Une clé JWT « anon » (publique, visible dans le site)
    n'est JAMAIS acceptée, même si elle traîne dans une variable SUPABASE_KEY."""
    cles = {os.getenv("SUPABASE_SERVICE_ROLE_KEY", ""), os.getenv("SUPABASE_KEY", "")}
    return [v for v in cles if v and _role_jwt(v) in (None, "service_role")]


_cles_verifiees: Dict[str, float] = {}


def _verifiee_par_supabase(cle: str) -> bool:
    """Clé JWT « service_role » inconnue de Render (ex. ancienne clé dans les secrets GitHub) :
    on demande à Supabase si elle est authentique (signature). Résultat gardé 1 h."""
    empreinte = hashlib.sha256(cle.encode()).hexdigest()
    if time.time() - _cles_verifiees.get(empreinte, 0) < 3600:
        return True
    url = os.getenv("SUPABASE_URL", "").rstrip("/")
    if not url:
        return False
    try:
        import requests
        r = requests.get(f"{url}/rest/v1/system_settings?select=key&limit=1",
                         headers={"apikey": cle, "Authorization": f"Bearer {cle}"}, timeout=8)
        if r.status_code == 200:
            _cles_verifiees[empreinte] = time.time()
            return True
    except Exception:
        pass
    return False


def cle_service_valide(cle: Optional[str]) -> bool:
    if not cle:
        return False
    if any(hmac.compare_digest(cle, a) for a in _cles_service()):
        return True
    return _role_jwt(cle) == "service_role" and _verifiee_par_supabase(cle)


def _empreinte(cle: str) -> str:
    """Forme d'une clé sans la révéler : 4 premiers caractères + longueur (+ rôle si JWT)."""
    if not cle:
        return "aucune"
    role = _role_jwt(cle)
    return f"{cle[:4]}…({len(cle)})" + (f" rôle={role}" if role else "")


def _cles_toutes() -> list:
    return [v for v in {os.getenv("SUPABASE_SERVICE_ROLE_KEY", ""), os.getenv("SUPABASE_KEY", "")} if v]


def noter_sans_jeton(chemin: str, methode: str, agent: str, origine: str, cle_fournie: str = "") -> None:
    """Compte les appels sans jeton (mode observation), par route."""
    import re
    motif = re.sub(r"/(ins|cli|cnv|usr|evt|tea|com|msg)_[A-Za-z0-9]+", r"/\1_…", chemin)
    motif = re.sub(r"/[0-9a-f-]{20,}", "/…", motif)
    cle = f"{methode} {motif}"
    e = _journal.setdefault(cle, {"n": 0, "agents": set(), "origines": set()})
    e["n"] += 1
    e["dernier"] = time.strftime("%Y-%m-%d %H:%M:%S")
    if len(e["agents"]) < 5:
        e["agents"].add((agent or "")[:80])
    if len(e["origines"]) < 5:
        e["origines"].add(origine or "")
    if cle_fournie:  # clé service envoyée mais refusée : on note sa forme (jamais la clé)
        e["cle_refusee"] = f"reçue {_empreinte(cle_fournie)} ; connues {[_empreinte(a) for a in _cles_toutes()]}"


def journal() -> Dict[str, Any]:
    return {k: {**v, "agents": sorted(v["agents"]), "origines": sorted(v["origines"])}
            for k, v in sorted(_journal.items(), key=lambda kv: -kv[1]["n"])}



# ─── Connexion Google ─────────────────────────────────────────────────────
# Adresses Google autorisées → profil. Complétable sans code via
# system_settings « comptes_google » = {"adresse@…": "qui"}.
COMPTES_GOOGLE = {
    "asutton@piano-tek.com": "allan",
    "suttonallan@gmail.com": "allan",
    "info@piano-tek.com": "louise",
    "nlessard@piano-tek.com": "nick",
    "jpreny@gmail.com": "jp",
    "margotcharignon@gmail.com": "margot",
}


def google_client_id() -> Optional[str]:
    """Identifiant public de l'app Google (system_settings « google_oauth_client_id »)."""
    try:
        v = _storage().get_system_setting("google_oauth_client_id")
    except Exception:
        return None
    return str(v).strip().strip('"') if v else None


def _comptes() -> Dict[str, str]:
    comptes = dict(COMPTES_GOOGLE)
    try:
        extra = _storage().get_system_setting("comptes_google")
        if isinstance(extra, str):
            extra = json.loads(extra)
        if isinstance(extra, dict):
            comptes.update({k.lower(): v for k, v in extra.items()})
    except Exception:
        pass
    return comptes


def connexion_google(credential: str) -> Optional[Dict[str, Any]]:
    """Vérifie le jeton Google (signature, audience, courriel vérifié) puis la liste d'adresses."""
    from google.oauth2 import id_token
    from google.auth.transport import requests as g_requests
    cid = google_client_id()
    if not cid:
        raise PermissionError("Connexion Google pas encore configurée")
    try:
        infos = id_token.verify_oauth2_token(credential, g_requests.Request(), cid)
    except ValueError:
        return None
    email = (infos.get("email") or "").lower()
    if not infos.get("email_verified") or not email:
        return None
    qui = _comptes().get(email)
    if not qui:
        raise PermissionError(f"{email} n'est pas autorisé")
    jeton = _signer({"qui": qui, "exp": int(time.time() + DUREE_JETON), "via": "google"})
    return {"jeton": jeton, "qui": qui, **PROFILS.get(qui, {})}
