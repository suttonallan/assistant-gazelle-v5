"""
Résumés d'appels Zoom Phone → chronologie Gazelle du client.

Flux :
1. Zoom envoie l'événement « Call Summary Changed » au webhook /api/zoom/webhook.
2. On récupère le résumé IA par l'API Zoom (app Server-to-Server « texto zomm vers
   assistant », clés ZOOM_ACCOUNT_ID / ZOOM_CLIENT_ID / ZOOM_CLIENT_SECRET sur Render).
3. On retrouve le client Gazelle par son numéro de téléphone.
4. Claude réécrit le résumé : concis, en français, erreurs de transcription corrigées
   (noms des techniciens, adresse, prix) à partir de la fiche Gazelle.
5. La note est ajoutée à la chronologie du client (createClientLog).
   Numéro inconnu → on vérifie d'abord si c'est un client existant qui appelle d'un
   autre numéro (même courriel, ou même nom + même code postal) : note rattachée à sa
   fiche. Nom semblable mais doute → rien n'est créé, courriel à info@ avec les fiches
   possibles. Personne de semblable + vraie demande de service + nom → fiche créée comme client
   potentiel (PROSPECT) avec téléphone, courriel et adresse tirés de l'appel.
   Sinon (fournisseur, démarchage, nom inconnu) → la note part à info@.

La structure exacte des réponses Zoom n'est pas documentée publiquement : l'extraction
est volontairement tolérante (parcours récursif du JSON) et le JSON brut est journalisé.
"""

import json
import os
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

import requests

from core.zoom_sms import get_zoom_access_token, ZOOM_API_BASE_URL

# Numéros de PTM : jamais pris pour le numéro du client.
NUMEROS_PTM = {"5143448008", "4382285774"}

CLE_TRAITES = "zoom_resumes_appels_traites"
COURRIEL_SECOURS = "info@piano-tek.com"

EQUIPE = (
    "Équipe PTM (orthographe exacte des noms) : Allan Sutton (copropriétaire, technicien), "
    "Nicolas Lessard (copropriétaire, technicien), Jean-Philippe Reny (technicien, « JP »), "
    "Margot Charignon (technicienne), Louise Paradis (coordonnatrice)."
)


def cles_zoom_configurees() -> bool:
    return all(os.getenv(k) for k in ("ZOOM_CLIENT_ID", "ZOOM_CLIENT_SECRET", "ZOOM_ACCOUNT_ID"))


def _chiffres(numero: Any) -> str:
    d = re.sub(r"\D", "", str(numero or ""))
    if len(d) == 11 and d.startswith("1"):
        d = d[1:]
    return d


def _parcourir(obj: Any, chemin: str = ""):
    """Rend (clé_complète, valeur) pour toutes les feuilles d'un JSON."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from _parcourir(v, f"{chemin}.{k}" if chemin else k)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from _parcourir(v, f"{chemin}[{i}]")
    else:
        yield chemin, obj


def _premiere_valeur(obj: Any, *noms: str) -> Optional[str]:
    for cle, val in _parcourir(obj):
        derniere = cle.split(".")[-1].split("[")[0].lower()
        if derniere in noms and val:
            return str(val)
    return None


def _numeros(obj: Any) -> List[str]:
    """Numéros de 10 chiffres trouvés dans le JSON (hors PTM), dans l'ordre."""
    vus: List[str] = []
    for cle, val in _parcourir(obj):
        derniere = cle.split(".")[-1].lower()
        if ("number" in derniere or "phone" in derniere) and val:
            d = _chiffres(val)
            if len(d) == 10 and d not in NUMEROS_PTM and d not in vus:
                vus.append(d)
    return vus


# ---------------------------------------------------------------- API Zoom

def _zoom_get(chemin: str, token: str) -> Dict[str, Any]:
    r = requests.get(f"{ZOOM_API_BASE_URL}{chemin}",
                     headers={"Authorization": f"Bearer {token}"}, timeout=20)
    if r.status_code != 200:
        raise RuntimeError(f"Zoom GET {chemin} → {r.status_code} : {r.text[:300]}")
    return r.json()


def recuperer_resume(payload_objet: Dict[str, Any]) -> Dict[str, Any]:
    """Récupère le résumé IA complet à partir de l'objet reçu par le webhook."""
    token = get_zoom_access_token()
    resume_id = _premiere_valeur(payload_objet, "ai_call_summary_id", "summary_id", "id")
    user_id = _premiere_valeur(payload_objet, "user_id", "owner_id")
    call_id = _premiere_valeur(payload_objet, "call_log_id", "call_id", "call_history_id")

    # Repli : l'historique d'appel donne l'identifiant du résumé.
    if (not resume_id or not user_id) and call_id:
        detail = _zoom_get(f"/phone/call_history_detail/{call_id}", token)
        resume_id = resume_id or _premiere_valeur(detail, "ai_call_summary_id")
        user_id = user_id or _premiere_valeur(detail, "user_id", "owner_id")

    if not (resume_id and user_id):
        raise RuntimeError(f"Identifiants de résumé introuvables dans le webhook : {json.dumps(payload_objet)[:500]}")

    resume = _zoom_get(f"/phone/user/{user_id}/ai_call_summary/{resume_id}", token)
    resume["_ids"] = {"ai_call_summary_id": resume_id, "user_id": user_id, "call_id": call_id}
    return resume


# ---------------------------------------------------------------- Gazelle / Supabase

def trouver_client(numeros: List[str]) -> Optional[Dict[str, Any]]:
    """Cherche le client Gazelle (copie Supabase) qui a l'un de ces numéros."""
    from core.supabase_storage import SupabaseStorage
    db = SupabaseStorage()
    h = db._get_headers()
    for d in numeros:
        motif = f"*{d[0:3]}*{d[3:6]}*{d[6:]}*"
        for table, champ_client in (("gazelle_clients", "external_id"), ("gazelle_contacts", "client_external_id")):
            try:
                r = requests.get(f"{db.api_url}/{table}", headers=h, timeout=15,
                                 params={"select": "*", "phone": f"like.{motif}", "limit": "5"})
                lignes = [l for l in (r.json() if r.status_code == 200 else []) if _chiffres(l.get("phone")) == d]
            except Exception:
                lignes = []
            if lignes:
                cid = lignes[0].get(champ_client)
                if table == "gazelle_contacts":
                    r = requests.get(f"{db.api_url}/gazelle_clients", headers=h, timeout=15,
                                     params={"select": "*", "external_id": f"eq.{cid}"})
                    lignes = r.json() if r.status_code == 200 else []
                    if not lignes:
                        return {"external_id": cid, "phone": d}
                return lignes[0]
    return None


def _cp(v: Any) -> str:
    return re.sub(r"\s", "", str(v or "")).upper()


def trouver_par_identite(r: Dict[str, Any]) -> Dict[str, Any]:
    """Numéro inconnu : un client existant appelle peut-être d'un autre numéro.
    Cherche par courriel, puis par nom (confirmé par le code postal).
    Retourne {"sur": client} si certain, {"candidats": [...]} si doute, {} si rien."""
    from core.supabase_storage import SupabaseStorage
    db = SupabaseStorage()
    h = db._get_headers()

    def _get(table, params):
        try:
            rep = requests.get(f"{db.api_url}/{table}", headers=h, timeout=15, params={"select": "*", "limit": "10", **params})
            return rep.json() if rep.status_code == 200 else []
        except Exception:
            return []

    def _client(cid):
        l = _get("gazelle_clients", {"external_id": f"eq.{cid}"})
        return l[0] if l else {"external_id": cid}

    courriel = (r.get("courriel") or "").strip()
    if courriel and "@" in courriel:
        l = _get("gazelle_clients", {"email": f"ilike.{courriel}"})
        if l:
            return {"sur": l[0], "par": "courriel"}
        l = _get("gazelle_contacts", {"email": f"ilike.{courriel}"})
        if l and l[0].get("client_external_id"):
            return {"sur": _client(l[0]["client_external_id"]), "par": "courriel"}

    prenom, nom = (r.get("prenom") or "").strip(), (r.get("nom") or "").strip()
    if not nom:
        return {}
    params = {"last_name": f"ilike.{nom}"}
    if prenom:
        params["first_name"] = f"ilike.{prenom}*"
    candidats = _get("gazelle_clients", params)
    for c in _get("gazelle_contacts", params):
        cid = c.get("client_external_id")
        if cid and all(x.get("external_id") != cid for x in candidats):
            candidats.append(_client(cid))
    if not candidats:
        return {}

    cp = _cp((r.get("adresse") or {}).get("code_postal"))
    if cp:
        memes = [c for c in candidats if _cp(c.get("postal_code")) == cp]
        if len(memes) == 1:
            return {"sur": memes[0], "par": "nom et code postal"}
    return {"candidats": candidats}


def _courriel_a_confirmer(note: str, numeros: List[str], candidats: List[Dict[str, Any]]) -> None:
    """Doute entre un client existant et un nouveau : on demande à l'équipe."""
    from core.email_notifier import EmailNotifier
    n = EmailNotifier()
    if not n.method:
        return
    tel = ", ".join(numeros) or "inconnu"
    lignes = [f"{_nom_client(c)} — {c.get('city') or ''} {c.get('postal_code') or ''} — {c.get('phone') or 's.t.'} "
              f"(https://gazelleapp.io/app/v2/clients/x/{c.get('external_id')})" for c in candidats[:5]]
    liste_html = "".join(f"<li>{l}</li>" for l in lignes)
    n.send_email(
        to_emails=[COURRIEL_SECOURS],
        subject=f"📞 Appel d'un nouveau numéro ({tel}) : client existant ?",
        html_content=(f"<p>Le numéro <strong>{tel}</strong> n'est dans aucune fiche, mais l'appelant "
                      f"ressemble à un client existant :</p><ul>{liste_html}</ul>"
                      "<p>Rien n'a été créé ni ajouté. Ajoutez la note à la bonne fiche "
                      "(et le nouveau numéro au contact), ou créez le client s'il s'agit d'un homonyme.</p>"
                      f"<pre style='white-space:pre-wrap;font-family:inherit'>{note}</pre>"
                      "<p style='color:#666;font-size:12px'>Assistant Gazelle V5</p>"),
        plain_content=f"Numéro {tel} inconnu ; clients possibles :\n" + "\n".join(lignes) + f"\n\n{note}",
    )


def _nom_client(c: Dict[str, Any]) -> str:
    nom = " ".join(x for x in (c.get("first_name"), c.get("last_name")) if x)
    return nom or c.get("company_name") or "Client"


# ---------------------------------------------------------------- Claude

def reecrire_resume(resume_brut: Dict[str, Any], client: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Claude transforme le résumé Zoom en note courte et fiable pour Gazelle, et en extrait
    les coordonnées de l'appelant (servent à créer un client potentiel s'il est inconnu).
    Retourne {"note", "prenom", "nom", "courriel", "adresse": {rue, ville, code_postal}, "reference", "demande_client"}."""
    import anthropic

    brut = {k: v for k, v in resume_brut.items() if k != "_ids"}
    texte_brut = json.dumps(brut, ensure_ascii=False)[:15000]
    fiche = "Client non identifié dans Gazelle."
    if client:
        fiche = json.dumps({k: client.get(k) for k in (
            "first_name", "last_name", "company_name", "phone", "email", "city", "postal_code",
            "personal_notes", "preference_notes") if client.get(k)}, ensure_ascii=False)

    consignes = (
        "Tu rédiges une note de chronologie Gazelle pour Piano Technique Montréal (PTM), "
        "à partir du résumé automatique d'un appel téléphonique produit par Zoom.\n"
        "Le résumé Zoom est souvent maladroit et contient des erreurs de transcription "
        "(noms déformés, adresses tronquées, termes mal traduits comme « offre de prime » pour soumission, "
        "« réglage » pour accord). Corrige-les avec la fiche du client et la liste de l'équipe ; "
        "en cas de doute, omets le détail plutôt que d'inventer.\n"
        f"{EQUIPE}\n\n"
        "Format exigé, en français, texte brut, sans markdown :\n"
        "Ligne 1 : « 📞 Appel Zoom avec <employé PTM> – <date> (<durée>) » (omets ce qui est inconnu).\n"
        "Puis, seulement si l'info existe, une ligne chacune : « Problème : … », « Solution prévue : … », "
        "« Service proposé : … » (avec prix et durée), « Contexte : … » (référence, historique du piano), "
        "« Suivi : … » (prochaines étapes concrètes, qui fait quoi).\n"
        "Maximum 8 lignes. Pas de liens, pas de formules de politesse, pas de numéros de téléphone.\n\n"
        "Réponds UNIQUEMENT par un objet JSON valide, sans texte autour :\n"
        '{"note": "<la note>", "prenom": "<prénom de l\'appelant ou null>", "nom": "<nom ou null>", '
        '"courriel": "<ou null>", "adresse": {"rue": "<ou null>", "ville": "<ou null>", "code_postal": "<ou null>"}, '
        '"reference": "<qui l\'a recommandé, ou null>", '
        '"demande_client": <true si l\'appelant est un client ou client potentiel qui demande un service de piano ; '
        'false pour un fournisseur, un démarcheur, un faux numéro ou un appel sans contenu>}\n'
        "N'invente aucune coordonnée : null si l'info n'est pas dans le résumé."
    )
    message = f"FICHE GAZELLE DU CLIENT :\n{fiche}\n\nRÉSUMÉ ZOOM (JSON brut) :\n{texte_brut}"

    client_ia = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    derniere_erreur = None
    for modele in ("claude-sonnet-4-5", "claude-haiku-4-5-20251001"):
        try:
            rep = client_ia.messages.create(model=modele, max_tokens=800, system=consignes,
                                            messages=[{"role": "user", "content": message}])
            texte = "".join(b.text for b in rep.content if getattr(b, "type", "") == "text").strip()
            if texte:
                return _lire_json(texte)
        except Exception as e:  # modèle indisponible → repli
            derniere_erreur = e
    raise RuntimeError(f"Réécriture Claude impossible : {derniere_erreur}")


def _lire_json(texte: str) -> Dict[str, Any]:
    m = re.search(r"\{.*\}", texte, re.S)
    try:
        d = json.loads(m.group(0)) if m else {}
    except Exception:
        d = {}
    if not d.get("note"):
        d = {"note": texte, "demande_client": False}
    return d


# ---------------------------------------------------------------- Orchestration

def _deja_traite(resume_id: str) -> bool:
    from core.supabase_storage import SupabaseStorage
    traites = SupabaseStorage().get_system_setting(CLE_TRAITES) or []
    return resume_id in traites


def _marquer_traite(resume_id: str) -> None:
    from core.supabase_storage import SupabaseStorage
    db = SupabaseStorage()
    traites = db.get_system_setting(CLE_TRAITES) or []
    if resume_id not in traites:
        traites = (traites + [resume_id])[-500:]
        db.save_system_setting(CLE_TRAITES, traites)


def _courriel_secours(note: str, numeros: List[str], raison: str) -> None:
    from core.email_notifier import EmailNotifier
    n = EmailNotifier()
    if not n.method:
        return
    tel = ", ".join(numeros) or "inconnu"
    n.send_email(
        to_emails=[COURRIEL_SECOURS],
        subject=f"📞 Résumé d'appel Zoom à classer ({tel})",
        html_content=(f"<p><strong>{raison}</strong> — numéro : {tel}</p>"
                      f"<pre style='white-space:pre-wrap;font-family:inherit'>{note}</pre>"
                      "<p style='color:#666;font-size:12px'>Assistant Gazelle V5 — à ajouter à la bonne fiche.</p>"),
        plain_content=f"{raison} — numéro : {tel}\n\n{note}",
    )


def traiter_evenement_resume(payload_objet: Dict[str, Any]) -> Dict[str, Any]:
    """Point d'entrée (tâche de fond du webhook). Ne lève jamais d'exception."""
    try:
        if not cles_zoom_configurees():
            print("⚠️ Résumé d'appel Zoom reçu mais clés API Zoom absentes sur Render — ignoré")
            return {"ok": False, "raison": "cles_absentes"}

        resume = recuperer_resume(payload_objet)
        rid = resume["_ids"]["ai_call_summary_id"]
        print(f"📞 Résumé Zoom {rid} reçu : {json.dumps(resume, ensure_ascii=False)[:1500]}")
        if _deja_traite(rid):
            return {"ok": True, "raison": "deja_traite"}

        numeros = _numeros(resume) or _numeros(payload_objet)
        client = trouver_client(numeros)
        r = reecrire_resume(resume, client)
        note = r["note"]

        from core.gazelle_api_client import GazelleAPIClient
        gz = GazelleAPIClient()

        if not client:
            # Numéro inconnu. D'abord : est-ce un client existant qui appelle d'un
            # autre numéro ? (courriel, ou nom confirmé par le code postal)
            ident = trouver_par_identite(r)
            if ident.get("sur"):
                c = ident["sur"]
                tel = ", ".join(f"({d[0:3]}) {d[3:6]}-{d[6:]}" for d in numeros)
                gz.create_client_log(c["external_id"], note + (f"\n(Appel reçu d'un numéro absent de la fiche : {tel})" if tel else ""))
                _marquer_traite(rid)
                print(f"✅ Appel d'un autre numéro rattaché à {_nom_client(c)} ({ident['par']})")
                return {"ok": True, "client": c["external_id"], "rattache_par": ident["par"]}
            if ident.get("candidats"):
                _courriel_a_confirmer(note, numeros, ident["candidats"])
                _marquer_traite(rid)
                return {"ok": True, "raison": "a_confirmer", "candidats": [c.get("external_id") for c in ident["candidats"]]}

            # Personne de connu : fiche créée comme client potentiel, seulement si
            # l'appel est une vraie demande de service et qu'on a au moins un nom.
            if r.get("demande_client") and numeros and (r.get("prenom") or r.get("nom")):
                d = numeros[0]
                cid = gz.create_client(r.get("prenom"), r.get("nom"),
                                       telephone=f"({d[0:3]}) {d[3:6]}-{d[6:]}",
                                       courriel=r.get("courriel"), adresse=r.get("adresse") or {},
                                       reference=r.get("reference"))
                gz.create_client_log(cid, note)
                _marquer_traite(rid)
                print(f"✅ Client potentiel créé ({cid}) avec le résumé d'appel")
                return {"ok": True, "client": cid, "cree": True}
            _courriel_secours(note, numeros, "Client introuvable dans Gazelle (fiche non créée)")
            _marquer_traite(rid)
            return {"ok": True, "raison": "client_introuvable", "numeros": numeros}

        gz.create_client_log(client["external_id"], note)
        _marquer_traite(rid)
        print(f"✅ Résumé d'appel ajouté à la chronologie de {_nom_client(client)} ({client['external_id']})")
        return {"ok": True, "client": client["external_id"]}
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"❌ Résumé d'appel Zoom non traité : {e}")
        return {"ok": False, "erreur": str(e)}
