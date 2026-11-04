"""Survol de la provenance des clients (« Référé par » vide dans Gazelle).

Pour chaque client sans « Référé par », cherche des indices ailleurs :
- notes de la fiche (personnelles, préférences, notes de référence) ;
- factures (« accord de courtoisie <marchand> », marchand à facturer) ;
- historique Gazelle (timeline) ;
- courriels Front (« je vous ai trouvé sur Google », « recommandé par… »).
Une IA lit les indices et PROPOSE une provenance. Rien n'est écrit dans Gazelle :
Allan approuve, met à discuter ou refuse chaque proposition (panneau de décisions).

Résultat gardé dans system_settings « provenance_survol ».
"""
import json
import os
import re
import time
from datetime import datetime, timezone
from typing import Any, Dict, List

import requests

CLE = "provenance_survol"
_MOTS = re.compile(r"(trouv|référ|refer|recommand|bouche|google|facebook|kijiji|marketplace|site web|"
                   r"votre site|nantel|archambault|steinway|yamaha canada|courtoisie|ami[e]? de|voisin|"
                   r"publicit|annonce|pages jaunes|found you|recommended|word of mouth)", re.IGNORECASE)
_RECHERCHES_FRONT = ["trouvé", "Google", "recommandé", "référé", "votre site", "courtoisie", "Nantel",
                     "recommended", "found you", "Facebook"]


def _st():
    from core.supabase_storage import SupabaseStorage
    return SupabaseStorage(silent=True)


def _etat(maj: Dict[str, Any]) -> None:
    st = _st()
    actuel = st.get_system_setting(CLE) or {}
    if isinstance(actuel, str):
        actuel = json.loads(actuel)
    actuel.update(maj)
    st.save_system_setting(CLE, actuel)


def lire() -> Dict[str, Any]:
    val = _st().get_system_setting(CLE) or {}
    return json.loads(val) if isinstance(val, str) else val


# ─── Collecte ─────────────────────────────────────────────────────

def _clients_gazelle() -> List[Dict[str, Any]]:
    from core.gazelle_api_client import GazelleAPIClient
    gz = GazelleAPIClient()
    q = """query($after: String) { allClients(first: 100, after: $after) {
      pageInfo { hasNextPage endCursor }
      nodes { id companyName status tags createdAt referredBy referredByNotes referralClient { id }
              personalNotes preferenceNotes
              defaultContact { firstName lastName defaultEmail { email } } } } }"""
    sortie, apres = [], None
    for _ in range(60):
        res = gz._execute_query(q, {"after": apres})
        bloc = ((res or {}).get("data") or {}).get("allClients") or {}
        sortie += bloc.get("nodes") or []
        pi = bloc.get("pageInfo") or {}
        if not pi.get("hasNextPage"):
            break
        apres = pi.get("endCursor")
    return sortie


def _nom(c: Dict[str, Any]) -> str:
    dc = c.get("defaultContact") or {}
    return c.get("companyName") or f"{dc.get('firstName') or ''} {dc.get('lastName') or ''}".strip()


def _institution(c: Dict[str, Any]) -> bool:
    tags = c.get("tags") or []
    texte = (" ".join(tags) if isinstance(tags, list) else str(tags)).lower()
    return "institution" in texte


def _indices_factures(ids: set) -> Dict[str, List[str]]:
    """Lignes de facture parlantes (courtoisie, marchand) depuis Supabase."""
    st = _st()
    h = st._get_headers()
    sortie: Dict[str, List[str]] = {}
    for mot in ("courtoisie", "nantel", "archambault", "facturer"):
        r = requests.get(f"{st.api_url}/gazelle_invoice_items?select=description,invoice_external_id"
                         f"&description=ilike.*{mot}*&limit=1000", headers=h, timeout=30)
        if r.status_code != 200:
            continue
        lignes = r.json()
        inv_ids = sorted({l["invoice_external_id"] for l in lignes if l.get("invoice_external_id")})
        clients: Dict[str, str] = {}
        for i in range(0, len(inv_ids), 80):
            lot = ",".join(inv_ids[i:i + 80])
            r2 = requests.get(f"{st.api_url}/gazelle_invoices?select=external_id,client_id,invoice_date"
                              f"&external_id=in.({lot})", headers=h, timeout=30)
            if r2.status_code == 200:
                for f in r2.json():
                    clients[f["external_id"]] = (f.get("client_id"), f.get("invoice_date"))
        for l in lignes:
            cid, date = clients.get(l.get("invoice_external_id"), (None, None))
            if cid in ids:
                sortie.setdefault(cid, []).append(f"Facture {date} : {(l.get('description') or '')[:200]}")
    return sortie


def _indices_timeline(ids: set) -> Dict[str, List[str]]:
    st = _st()
    h = st._get_headers()
    sortie: Dict[str, List[str]] = {}
    for mot in ("référ", "refere", "recommand", "trouvé", "google", "courtoisie", "nantel", "bouche"):
        for champ in ("description", "title"):
            r = requests.get(f"{st.api_url}/gazelle_timeline_entries?select=client_id,occurred_at,{champ}"
                             f"&{champ}=ilike.*{mot}*&limit=500", headers=h, timeout=30)
            if r.status_code != 200:
                continue
            for e in r.json():
                cid = e.get("client_id")
                if cid in ids:
                    texte = (e.get(champ) or "")
                    m = _MOTS.search(texte)
                    debut = max(0, (m.start() if m else 0) - 120)
                    extrait = f"Historique {(e.get('occurred_at') or '')[:10]} : …{texte[debut:debut + 300]}…"
                    if extrait not in sortie.get(cid, []):
                        sortie.setdefault(cid, []).append(extrait)
    return sortie


def _indices_front(par_courriel: Dict[str, str]) -> Dict[str, List[str]]:
    """Courriels reçus contenant des mots de provenance, rattachés au client par son adresse."""
    from core.front_client import get_front_client
    from api.ivo_routes import _texte
    front = get_front_client()
    sortie: Dict[str, List[str]] = {}
    vus = set()
    for mot in _RECHERCHES_FRONT:
        try:
            convs = front.search_conversations(mot, limit=100)
        except Exception:
            continue
        for conv in convs:
            courriel = ((conv.get("recipient") or {}).get("handle") or "").lower()
            cid = par_courriel.get(courriel)
            if not cid or conv["id"] in vus:
                continue
            vus.add(conv["id"])
            try:
                msgs = front.list_messages(conv["id"], limit=20)
            except Exception:
                continue
            time.sleep(0.4)
            for m in sorted([m for m in msgs if m.get("is_inbound")], key=lambda m: m.get("created_at") or 0):
                texte = _texte(m.get("text") or m.get("body") or "")
                hit = _MOTS.search(texte)
                if hit:
                    debut = max(0, hit.start() - 150)
                    date = datetime.fromtimestamp(m.get("created_at") or 0, timezone.utc).strftime("%Y-%m-%d")
                    sortie.setdefault(cid, []).append(f"Courriel {date} : …{texte[debut:debut + 350]}…")
                    break
    return sortie


# ─── Analyse IA ───────────────────────────────────────────────────

_CONSIGNE = """Tu aides Piano Technique Montréal (PTM) à savoir comment chaque client l'a connu.
Pour chaque client, lis UNIQUEMENT les indices fournis. Propose une provenance seulement si un indice la dit vraiment.
Valeurs courtes et uniformes pour « refere_par » : « Google », « Site web PTM », « Facebook », « Kijiji / Marketplace »,
« Nantel Musique », « Archambault », « <autre marchand> », « Recommandation — <nom> », « Bouche-à-oreille », « Ancien client ».
Un « accord de courtoisie <marchand> » ou « facturer <marchand> » = le marchand nous a envoyé le client.
Si aucun indice ne dit la provenance, mets refere_par à null.
Réponds UNIQUEMENT en JSON : [{"client_id": "...", "refere_par": "..." ou null, "confiance": "haute"|"moyenne"|"basse",
"preuve": "citation courte de l'indice (≤ 200 caractères)"}]"""


def _analyser(lots: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    from anthropic import Anthropic
    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    modele = os.getenv("IVO_MODELE", "claude-sonnet-5-5")
    sortie = []
    for i in range(0, len(lots), 20):
        groupe = lots[i:i + 20]
        texte = "\n\n".join(f"CLIENT {c['client_id']} — {c['nom']}\n" + "\n".join(f"- {x}" for x in c["indices"][:8])
                            for c in groupe)
        try:
            rep = client.messages.create(model=modele, max_tokens=4000, system=_CONSIGNE,
                                         messages=[{"role": "user", "content": texte}])
            brut = "".join(getattr(b, "text", "") for b in rep.content)
            m = re.search(r"\[.*\]", brut, re.DOTALL)
            sortie += json.loads(m.group(0)) if m else []
        except Exception as e:
            print(f"⚠️ Survol provenance — analyse IA : {e}")
    return sortie


# ─── Survol complet ───────────────────────────────────────────────

def lancer() -> Dict[str, Any]:
    _etat({"statut": "en cours", "debut": datetime.now(timezone.utc).isoformat()})
    try:
        clients = _clients_gazelle()
        sans = [c for c in clients
                if not (c.get("referredBy") or "").strip() and not c.get("referralClient") and not _institution(c)]
        ids = {c["id"] for c in sans}
        indices: Dict[str, List[str]] = {}

        def ajouter(src: Dict[str, List[str]]):
            for k, v in src.items():
                indices.setdefault(k, []).extend(v)

        for c in sans:
            if (c.get("referredByNotes") or "").strip():
                indices.setdefault(c["id"], []).append(f"Note de référence (fiche) : {c['referredByNotes'][:300]}")
            notes = f"{c.get('personalNotes') or ''}\n{c.get('preferenceNotes') or ''}"
            m = _MOTS.search(notes)
            if m:
                d = max(0, m.start() - 120)
                indices.setdefault(c["id"], []).append(f"Notes de la fiche : …{notes[d:d + 300]}…")
        ajouter(_indices_factures(ids))
        ajouter(_indices_timeline(ids))
        par_courriel = {(((c.get("defaultContact") or {}).get("defaultEmail") or {}).get("email") or "").lower(): c["id"]
                        for c in sans}
        par_courriel.pop("", None)
        try:
            ajouter(_indices_front(par_courriel))
        except Exception as e:
            print(f"⚠️ Survol provenance — Front : {e}")

        noms = {c["id"]: _nom(c) for c in sans}
        lots = [{"client_id": k, "nom": noms.get(k, k), "indices": v} for k, v in indices.items() if v]
        analyses = {a.get("client_id"): a for a in _analyser(lots)}

        anciennes = {p["client_id"]: p for p in (lire().get("propositions") or [])}
        propositions = []
        for lot in lots:
            a = analyses.get(lot["client_id"]) or {}
            if not a.get("refere_par"):
                continue
            prec = anciennes.get(lot["client_id"]) or {}
            propositions.append({
                "client_id": lot["client_id"], "nom": lot["nom"], "refere_par": a["refere_par"],
                "confiance": a.get("confiance") or "basse", "preuve": a.get("preuve") or "",
                "indices": lot["indices"][:6],
                "statut": prec.get("statut") or "a_decider", "note": prec.get("note") or "",
            })
        ordre = {"haute": 0, "moyenne": 1, "basse": 2}
        propositions.sort(key=lambda p: (p["statut"] != "a_decider", ordre.get(p["confiance"], 3), p["nom"]))
        resume = {"statut": "termine", "fin": datetime.now(timezone.utc).isoformat(),
                  "total_clients": len(clients), "sans_provenance": len(sans),
                  "avec_indices": len(lots), "propositions": propositions}
        _etat(resume)
        return {k: v for k, v in resume.items() if k != "propositions"} | {"nb_propositions": len(propositions)}
    except Exception as e:
        _etat({"statut": "erreur", "erreur": str(e)[:500]})
        raise


def decider(client_id: str, decision: str, note: str = "", valeur: str = "") -> Dict[str, Any]:
    """approuver → inscrit « Référé par » (sans jamais écraser) ; discuter / refuser → mémorisé."""
    etat = lire()
    props = etat.get("propositions") or []
    p = next((x for x in props if x["client_id"] == client_id), None)
    if not p:
        raise ValueError("Proposition introuvable")
    if decision == "approuver":
        from api.taches_routes import inscrire_reference, ReferenceClientIn
        texte = (valeur or p["refere_par"]).strip()
        inscrire_reference(client_id, ReferenceClientIn(
            refere_par=texte, notes=f"Déduit par l'assistant : {p.get('preuve') or ''}"[:500]))
        p["refere_par"] = texte
    p["statut"] = {"approuver": "approuve", "discuter": "a_discuter", "refuser": "refuse"}[decision]
    p["note"] = note or p.get("note") or ""
    _etat({"propositions": props})
    return p
