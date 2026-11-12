"""Assistant conversationnel — fil de discussion avec mémoire + tous les outils.

Contrairement aux endpoints à message unique (/review-estimate, /duplicate-estimate…),
celui-ci garde l'HISTORIQUE et laisse Claude choisir l'outil, ce qui permet les
suivis (« oui, réactive-la avec le prix à jour »).

POST /assistant/converse
  body : { messages: [{role, content}...], current_user_first_name? }
  ret  : { reply: str, actions: [ {type, result} ... ] }

Réutilise les outils et fonctions d'exécution déjà validés dans assistant_routes.
Les créations de soumission restent des BROUILLONS (rien n'est envoyé au client).
"""
import json
import os
from datetime import date
from core.timezone_utils import aujourdhui_montreal
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from api.assistant_routes import (
    REVIEW_ESTIMATE_TOOL, SEARCH_KEYWORD_TOOL, JOINT_APPOINTMENT_TOOL, LIST_CALLS_TOOL,
    execute_review_estimate, execute_search_keyword, execute_joint_appointment, execute_list_calls,
)
from api.assistant_duplication import duplicate_estimate
from api.photos_piano_routes import ATTACH_PHOTOS_TOOL, execute_attach_photos

router = APIRouter()

# Outil de réactivation/création à partir d'un numéro (le manquant côté chat).
REACTIVATE_ESTIMATE_TOOL = {
    "name": "reactivate_estimate",
    "description": (
        "Crée une NOUVELLE soumission (brouillon) à partir d'une soumission "
        "EXISTANTE identifiée par son numéro. Mets reprice=true quand "
        "l'utilisateur veut « réactiver », « une nouvelle soumission à jour », "
        "« avec les nouveaux prix / le prix à jour » : les montants sont alors "
        "remis aux tarifs courants du catalogue. reprice=false = copie fidèle. "
        "Ne fait qu'un brouillon (rien n'est envoyé au client)."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "estimate_number": {"type": "integer",
                                "description": "Numéro de la soumission source (ex: 11766)."},
            "reprice": {"type": "boolean",
                        "description": "true = remettre aux prix courants ; false = copie fidèle."},
        },
        "required": ["estimate_number"],
    },
}

# Outil de repli : quand l'assistant ne sait pas faire, la demande est transmise
# à l'administrateur (Allan) par courriel, pour devenir une future fonctionnalité.
FEATURE_REQUEST_TOOL = {
    "name": "request_new_feature",
    "description": (
        "Transmet à l'administrateur (Allan) une demande que tu NE SAIS PAS faire "
        "avec tes autres outils (ex. déplacer un RV, modifier un client, envoyer un "
        "courriel). À utiliser seulement pour une vraie demande d'action ou de "
        "fonctionnalité, pas pour une simple question ou une demande ambiguë "
        "(dans ce cas, pose d'abord une question)."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "summary": {"type": "string",
                        "description": "Résumé en une phrase de ce que l'utilisateur voulait faire."},
            "original_request": {"type": "string",
                                 "description": "La demande de l'utilisateur, telle qu'écrite."},
        },
        "required": ["summary", "original_request"],
    },
}

ADMIN_EMAIL = "asutton@piano-tek.com"


def execute_feature_request(summary: str, original_request: str,
                            user_first_name: Optional[str] = None) -> Dict[str, Any]:
    """Envoie la demande non prise en charge par courriel à l'administrateur."""
    from html import escape
    from core.email_notifier import get_email_notifier
    qui = user_first_name or "Un utilisateur"
    sujet = f"[Assistant Gazelle] Demande non prise en charge — {qui} : {summary[:80]}"
    html = (
        f"<p><b>{escape(qui)}</b> a demandé à l'assistant quelque chose qu'il ne sait pas encore faire.</p>"
        f"<p><b>Résumé :</b> {escape(summary)}</p>"
        f"<p><b>Demande originale :</b><br>{escape(original_request)}</p>"
        f"<p style='color:#888'>Date : {aujourdhui_montreal().isoformat()}</p>"
    )
    texte = f"{qui} : {summary}\n\nDemande originale :\n{original_request}"
    notifier = get_email_notifier()
    ok = notifier.send_email([ADMIN_EMAIL], sujet, html, texte)
    if ok:
        return {"success": True, "message": "Demande transmise à l'administrateur."}
    return {"success": False, "error": f"Envoi impossible : {notifier.last_error}"}


LIEN_RESERVATION_TOOL = {
    "name": "preparer_lien_reservation",
    "description": (
        "Prépare le lien de la page de réservation en ligne de PTM, prérempli avec les "
        "coordonnées et le piano d'un client (par ex. d'après un courriel de client transféré). "
        "N'y mets jamais le numéro civique ni la rue : le client les inscrira. Si le courriel "
        "correspond à un client déjà dans Gazelle, retourne son lien personnel. Rien n'est envoyé."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "prenom": {"type": "string"}, "nom": {"type": "string"},
            "courriel": {"type": "string"}, "tel": {"type": "string"},
            "ville": {"type": "string", "description": "Municipalité (un arrondissement de Montréal → Montréal)."},
            "cp": {"type": "string", "description": "Code postal, ex. H1M 1E9."},
            "type": {"type": "string", "enum": ["UPRIGHT", "GRAND", ""]},
            "marque": {"type": "string"}, "annee": {"type": "string"},
            "lieu": {"type": "string", "description": "Pièce où se trouve le piano : salon, sous-sol…"},
            "besoin": {"type": "string", "description": "Une phrase : modèle, série, emplacement, demande."},
        },
        "required": ["courriel"],
    },
}


def execute_lien_reservation(**champs) -> Dict[str, Any]:
    from core.lien_reservation import CHAMPS, client_gazelle_par_courriel, construire_lien, lien_personnel
    infos = {c: str(champs.get(c) or "").strip() for c in CHAMPS}
    connu = client_gazelle_par_courriel(infos["courriel"])
    if connu:
        return {"success": True, "lien": lien_personnel(connu["external_id"]), "client_gazelle": True}
    return {"success": True, "lien": construire_lien(infos), "client_gazelle": False}


# ── Créer un rendez-vous Gazelle (en 2 temps : aperçu, puis création sur confirmation) ──
TECHNICIENS = {
    "allan": "usr_ofYggsCDt2JAVeNP",
    "nicolas": "usr_HcCiFk7o0vZ9xAI0", "nick": "usr_HcCiFk7o0vZ9xAI0",
    "jp": "usr_ReUSmIJmBF86ilY1", "jean-philippe": "usr_ReUSmIJmBF86ilY1",
    "margot": "usr_bbt59aCUqUaDWA8n",
}

CREER_RV_TOOL = {
    "name": "creer_rendez_vous",
    "description": (
        "Crée un rendez-vous dans Gazelle pour un client et un technicien. "
        "TOUJOURS en deux temps : appelle d'abord avec confirme=false (aucune création, "
        "renvoie un aperçu : client trouvé, pianos, technicien, date et heure), montre "
        "l'aperçu à l'utilisateur et demande « Je le crée ? ». Rappelle l'outil avec "
        "confirme=true SEULEMENT après un oui explicite. Si la date n'est pas donnée, "
        "demande-la (ne devine jamais le jour)."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "client": {"type": "string", "description": "Nom du client tel que dit par l'utilisateur."},
            "client_id": {"type": "string", "description": "ID Gazelle (cli_…) si connu (ex. après un aperçu à plusieurs choix)."},
            "technicien": {"type": "string", "description": "Prénom : Allan, Nicolas, JP, Margot."},
            "date": {"type": "string", "description": "AAAA-MM-JJ (heure de Montréal)."},
            "heure": {"type": "string", "description": "HH:MM, 24 h (ex. 14:30)."},
            "duree_min": {"type": "integer", "description": "Durée en minutes (défaut 120)."},
            "notes": {"type": "string", "description": "Ce qu'il faut faire, tel que demandé."},
            "accord": {"type": "boolean", "description": "true si c'est un accord (défaut true ; false pour mesures, estimation, réparation)."},
            "confirme": {"type": "boolean", "description": "false = aperçu seulement ; true = créer (après oui de l'utilisateur)."},
        },
        "required": ["technicien", "date", "heure", "confirme"],
    },
}


import contextvars
# Canal de la demande : « assistant » (case de Ma Journée) ou « ivo » (commentaire @Ivo dans Front).
_CANAL = contextvars.ContextVar("canal_assistant", default="assistant")
_PRENOM = contextvars.ContextVar("prenom_assistant", default=None)


def execute_creer_rv(**t) -> Dict[str, Any]:
    from api.taches_routes import chercher_clients, creer_rendez_vous, RendezVousIn
    tech = (t.get("technicien") or "").strip().lower()
    user_id = TECHNICIENS.get(tech)
    if not user_id:
        return {"success": False, "error": f"Technicien inconnu : {t.get('technicien')!r} (Allan, Nicolas, JP, Margot)."}
    client_id = t.get("client_id")
    trouves = []
    if not client_id:
        nom = (t.get("client") or "").strip()
        if len(nom) < 2:
            return {"success": False, "error": "Nom du client manquant."}
        trouves = chercher_clients(q=nom)["clients"]
        if not trouves:
            return {"success": False, "error": f"Aucun client « {nom} » dans Gazelle."}
        if len(trouves) > 1:
            return {"success": False, "plusieurs_clients": [
                {"client_id": c["external_id"], "nom": c["company_name"],
                 "pianos": [f"{p.get('make') or ''} {p.get('model') or ''}".strip() for p in c["pianos"]]}
                for c in trouves],
                "message": "Plusieurs clients correspondent : demande lequel, puis repasse son client_id."}
        client_id = trouves[0]["external_id"]
    if trouves:
        client = trouves[0]
    else:
        client = next((c for c in chercher_clients(q=(t.get("client") or "").strip() or client_id)["clients"]
                       if c["external_id"] == client_id), {"external_id": client_id, "pianos": []})
    pianos = client.get("pianos", [])
    debut = f"{t['date']}T{t['heure']}"
    apercu = {
        "client": client.get("company_name") or client_id, "client_id": client_id,
        "technicien": t.get("technicien"), "debut_montreal": debut,
        "duree_min": int(t.get("duree_min") or 120), "notes": t.get("notes") or "",
        "accord": bool(t.get("accord", True)),
        "pianos": [f"{p.get('make') or ''} {p.get('model') or ''}".strip() for p in pianos],
    }
    if not t.get("confirme"):
        return {"success": True, "apercu": apercu, "cree": False,
                "message": "Aperçu seulement : rien n'est créé. Demande confirmation."}
    qui = _PRENOM.get() or "l'équipe"
    par_ivo = _CANAL.get() == "ivo"
    res = creer_rendez_vous(RendezVousIn(
        client_id=client_id, user_id=user_id, debut_montreal=debut,
        duree_min=apercu["duree_min"], notes=apercu["notes"] or None,
        piano_ids=[p["external_id"] for p in pianos], accord=apercu["accord"],
        # Case de l'assistant : confirmation Gazelle au client comme avant. Ivo : jamais
        # automatique (décision d'Allan, 4 nov. 2026) — l'équipe relit puis envoie.
        confirmation_client=not par_ivo,
        par=f"Ivo (assistant IA) à la demande de {qui}"))
    return {"success": True, "cree": True, "apercu": apercu,
            "evenement_id": (res.get("evenement") or {}).get("id")}


from core.ivo_regles import OUTILS as _OUTILS_REGLES

AJOUTER_COURRIEL_TOOL = {
    "name": "ajouter_courriel_client",
    "description": (
        "Ajoute un courriel à la fiche Gazelle d'un client (contact principal). Ne remplace jamais "
        "le courriel principal existant ; refuse si un autre client a déjà ce courriel. "
        "Donne le client_id (cli_…) si connu, sinon le nom du client."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "courriel": {"type": "string"},
            "client_id": {"type": "string"},
            "client": {"type": "string", "description": "Nom du client si le client_id n'est pas connu."},
        },
        "required": ["courriel"],
    },
}


def execute_ajouter_courriel(**t) -> Dict[str, Any]:
    from api.taches_routes import chercher_clients, ajouter_courriel
    client_id = (t.get("client_id") or "").strip()
    if not client_id:
        nom = (t.get("client") or "").strip()
        if len(nom) < 2:
            return {"success": False, "error": "Client manquant (client_id ou nom)."}
        trouves = chercher_clients(q=nom)["clients"]
        if not trouves:
            return {"success": False, "error": f"Aucun client « {nom} » dans Gazelle."}
        if len(trouves) > 1:
            return {"success": False, "plusieurs_clients": [
                {"client_id": c["external_id"], "nom": c["company_name"]} for c in trouves],
                "message": "Plusieurs clients correspondent : demande lequel, puis repasse son client_id."}
        client_id = trouves[0]["external_id"]
    r = ajouter_courriel(client_id, t.get("courriel") or "")
    return {"success": True, **r}


CATALOGUE_TOOL = {
    "name": "chercher_catalogue",
    "description": (
        "Cherche dans le catalogue Gazelle (Master Service List) les services et leurs PRIX COURANTS. "
        "À utiliser AVANT creer_soumission pour trouver le service_id de chaque ligne. "
        "Donne plusieurs mots-clés courts à la fois (ex. [\"corde\", \"nettoyage\", \"basse\"])."
    ),
    "input_schema": {
        "type": "object",
        "properties": {"mots": {"type": "array", "items": {"type": "string"},
                                "description": "Mots-clés (sous-chaîne du nom du service)."}},
        "required": ["mots"],
    },
}


def execute_catalogue(mots: List[str]) -> Dict[str, Any]:
    from api.taches_routes import chercher_services
    out = {}
    for m in (mots or [])[:8]:
        out[m] = chercher_services(q=(m or "").strip())["services"][:25]
    return {"success": True, "resultats": out}


CREER_SOUMISSION_TOOL = {
    "name": "creer_soumission",
    "description": (
        "Crée une NOUVELLE soumission (brouillon, rien n'est envoyé au client) pour un client et un piano, "
        "sans soumission existante de départ. Chaque ligne vient du catalogue (service_id trouvé avec "
        "chercher_catalogue : le prix courant du catalogue est appliqué automatiquement). Une ligne hors "
        "catalogue n'est permise que si l'utilisateur a donné lui-même son montant. Les avertissements "
        "vont dans « notes » (pas en lignes)."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "client": {"type": "string", "description": "Nom du client tel que dit par l'utilisateur."},
            "client_id": {"type": "string", "description": "ID Gazelle (cli_…) si connu."},
            "piano_id": {"type": "string", "description": "ID du piano (ins_…) si le client en a plusieurs."},
            "lignes": {"type": "array", "items": {"type": "object", "properties": {
                "service_id": {"type": "string", "description": "mit_… du catalogue."},
                "nom": {"type": "string", "description": "Seulement pour une ligne hors catalogue."},
                "montant": {"type": "number", "description": "Seulement hors catalogue, donné par l'utilisateur."},
                "description": {"type": "string", "description": "Précision propre à ce piano (facultatif)."}}}},
            "notes": {"type": "string", "description": "Notes de la soumission : courte intro + section « À savoir avant de décider : » avec les avertissements d'usage."},
            "locale": {"type": "string", "enum": ["fr", "en"]},
        },
        "required": ["lignes"],
    },
}


def execute_creer_soumission(**t) -> Dict[str, Any]:
    from api.taches_routes import chercher_clients, chercher_services, creer_soumission, SoumissionIn, LigneSoumission
    client_id = (t.get("client_id") or "").strip()
    nom = (t.get("client") or "").strip()
    trouves = chercher_clients(q=nom)["clients"] if nom else []
    if not client_id:
        if not trouves:
            return {"success": False, "error": f"Aucun client « {nom} » dans Gazelle." if nom else "Client manquant."}
        if len(trouves) > 1:
            return {"success": False, "plusieurs_clients": [
                {"client_id": c["external_id"], "nom": c["company_name"],
                 "pianos": [{"piano_id": p.get("external_id"), "piano": f"{p.get('make') or ''} {p.get('model') or ''}".strip()} for p in c["pianos"]]}
                for c in trouves], "message": "Plusieurs clients correspondent : demande lequel, puis repasse son client_id."}
        client_id = trouves[0]["external_id"]
    client = next((c for c in trouves if c["external_id"] == client_id), None) or \
        next((c for c in chercher_clients(q=client_id)["clients"] if c["external_id"] == client_id), {"pianos": []})
    pianos = client.get("pianos") or []
    piano_id = (t.get("piano_id") or "").strip()
    if not piano_id:
        if len(pianos) == 1:
            piano_id = pianos[0].get("external_id")
        elif not pianos:
            return {"success": False, "error": "Ce client n'a aucun piano dans Gazelle : il faut d'abord ajouter le piano."}
        else:
            return {"success": False, "plusieurs_pianos": [
                {"piano_id": p.get("external_id"), "piano": f"{p.get('make') or ''} {p.get('model') or ''}".strip(),
                 "lieu": p.get("location")} for p in pianos],
                "message": "Le client a plusieurs pianos : demande lequel, puis repasse son piano_id."}
    prix = {x["id"]: x for x in chercher_services(q="")["services"]}
    lignes, manquantes = [], []
    for l in t.get("lignes") or []:
        sid = (l.get("service_id") or "").strip()
        if sid:
            if sid not in prix:
                manquantes.append(f"service {sid} introuvable au catalogue")
                continue
            lignes.append(LigneSoumission(nom=prix[sid]["nom"], montant=prix[sid]["prix"],
                                          description=l.get("description"), service_id=sid))
        elif l.get("nom") and l.get("montant"):
            lignes.append(LigneSoumission(nom=l["nom"], montant=float(l["montant"]), description=l.get("description")))
        else:
            manquantes.append(f"« {l.get('nom') or '?'} » : ni service du catalogue ni montant donné")
    if manquantes or not lignes:
        return {"success": False, "error": "Soumission non créée. " + " ; ".join(manquantes or ["aucune ligne"]) +
                ". Demande le prix à l'utilisateur au lieu de le deviner."}
    r = creer_soumission(SoumissionIn(client_id=client_id, piano_id=piano_id, lignes=lignes,
                                      notes=t.get("notes"), locale=t.get("locale") or "fr"))
    return {"success": True, "cree": True, "numero": r.get("numero"), "client": client.get("company_name"),
            "piano": next((f"{p.get('make') or ''} {p.get('model') or ''}".strip() for p in pianos if p.get("external_id") == piano_id), piano_id),
            "lignes": [{"nom": l.nom, "montant": l.montant} for l in lignes],
            "total_avant_taxes": r.get("total_avant_taxes"),
            "message": "Brouillon créé dans Gazelle, rien n'a été envoyé au client."}


AJOUTER_DEMANDE_PDA_TOOL = {
    "name": "ajouter_demande_pda",
    "description": ("Ajoute une demande dans l'onglet Place des Arts de l'assistant (comme l'import d'un "
                    "courriel de PdA). Ne crée PAS de RV dans Gazelle : le RV se crée ensuite depuis la demande. "
                    "D'abord confirme=false (aperçu + recherche de doublon), puis confirme=true après un oui, "
                    "ou directement confirme=true si l'équipe a donné l'ordre explicite d'ajouter la demande."),
    "input_schema": {"type": "object", "properties": {
        "appointment_date": {"type": "string", "description": "Date du service AAAA-MM-JJ (le jour où le technicien y va)"},
        "room": {"type": "string", "description": "Salle, au format de l'onglet : WP, TM, MS, 5E, TJD, SCL, « Salle D », « Salle F »…"},
        "for_who": {"type": "string", "description": "Pour qui (ex. OSM, Opéra de Montréal) + événement si connu"},
        "piano": {"type": "string", "description": "Piano demandé, tel qu'écrit dans la demande (ex. Steinway M 5'7'')"},
        "diapason": {"type": "string", "description": "440, 442…"},
        "time": {"type": "string", "description": "Heure ou contrainte (ex. « Avant 9h », « 10h »)"},
        "requester": {"type": "string", "description": "Initiales du demandeur à PdA (ex. IC = Isabelle Clairoux, AJ = Annie Jenkins, EP = Erik Palardy)"},
        "technicien": {"type": "string", "description": "Prénom du technicien à assigner (Nicolas, JP, Margot, Allan) ; vide = à attribuer"},
        "notes": {"type": "string"},
        "confirme": {"type": "boolean"},
    }, "required": ["appointment_date", "room", "for_who"]},
}

_TECH_IDS = {"nicolas": "usr_HcCiFk7o0vZ9xAI0", "allan": "usr_ofYggsCDt2JAVeNP",
             "jp": "usr_ReUSmIJmBF86ilY1", "jean-philippe": "usr_ReUSmIJmBF86ilY1",
             "margot": "usr_bbt59aCUqUaDWA8n"}


def execute_ajouter_demande_pda(**t) -> Dict[str, Any]:
    from api.place_des_arts import get_storage, importer_demandes, ImportPreviewRequest
    date_s = (t.get("appointment_date") or "")[:10]
    tech_txt = (t.get("technicien") or "").strip().lower()
    tech_id = _TECH_IDS.get(tech_txt) if tech_txt else None
    if tech_txt and not tech_id:
        return {"success": False, "error": f"Technicien inconnu : {t.get('technicien')}"}
    item = {k: (t.get(k) or "") for k in ("room", "for_who", "piano", "diapason", "time", "requester", "notes")}
    item["appointment_date"] = date_s
    item["technician_id"] = tech_id
    # Doublon : déjà une demande ce jour-là dans la même salle ?
    storage = get_storage()
    existantes = storage.client.table("place_des_arts_requests")\
        .select("id,appointment_date,room,for_who,piano,time,status,appointment_id")\
        .gte("appointment_date", date_s).lt("appointment_date", date_s + "T23:59:59")\
        .execute().data or []
    import re as _r
    def _salle(x):  # « Salle F », « F », « salle f » → « f » ; « WP - Salle 1 » → « wp1 »
        return _r.sub(r"[^a-z0-9]", "", _r.sub(r"\bsalle\b", "", (x or "").lower()))
    def _qui(x):
        return _r.sub(r"[^a-z0-9]", "", (x or "").lower())
    meme_salle = [e for e in existantes
                  if (e.get("status") or "").upper() not in ("CANCELLED", "CANCELED")
                  and ((_salle(e.get("room")) and _salle(e.get("room")) == _salle(item["room"]))
                       or (_qui(e.get("for_who")) and _qui(item["for_who"])
                           and (_qui(e.get("for_who")) in _qui(item["for_who"]) or _qui(item["for_who"]) in _qui(e.get("for_who")))
                           and _salle(e.get("room")) in ("", _salle(item["room"]), "confirmer")))]
    if not t.get("confirme"):
        return {"success": True, "apercu": item, "technicien": t.get("technicien") or "à attribuer",
                "demandes_deja_ce_jour_la": existantes, "meme_salle": meme_salle,
                "message": "Aperçu seulement : rien n'est ajouté. Redemande avec confirme=true."}
    if meme_salle:
        return {"success": False, "error": "Une demande semblable existe déjà ce jour-là (même salle ou même client) : rien n'a été ajouté, pour éviter un doublon. Montre-la à l'utilisateur.",
                "meme_salle": meme_salle}
    r = importer_demandes(ImportPreviewRequest(items=[item]))
    if not r.get("imported"):
        return {"success": False, "error": r.get("message") or "Aucune demande ajoutée."}
    return {"success": True, "ajoutee": True, "id": (r.get("ids") or [None])[0], "demande": item,
            "message": "Demande ajoutée dans l'onglet Place des Arts. Aucun RV Gazelle n'a été créé."}


VERIFIER_PDA_TOOL = {
    "name": "verifier_services_pda",
    "description": ("Vérifie que TOUS les services Place des Arts faits ou prévus dans Gazelle (60 derniers "
                    "jours et à venir) ont bien leur demande dans l'assistant (onglet Place des Arts), et "
                    "liste ceux qui manquent. Signale aussi les demandes de l'assistant dont la date est "
                    "passée sans RV Gazelle lié. Lecture seule. À utiliser pour « est-ce que tous les "
                    "services de PdA sont dans l'assistant ? »."),
    "input_schema": {"type": "object", "properties": {}},
}


def execute_verifier_pda() -> Dict[str, Any]:
    from api.place_des_arts import get_storage, detecter_services_orphelins
    from modules.place_des_arts.services.gazelle_sync import GazelleSyncService
    storage = get_storage()
    svc = GazelleSyncService(storage)
    rvs = svc._get_gazelle_appointments()
    orphelins = detecter_services_orphelins(storage, svc, rvs)
    manquants = [{k: o.get(k) for k in ("date", "time", "title", "technicien_nom", "termine", "pianos", "appointment_id")}
                 for o in orphelins]
    nb_pda = sum(1 for a in rvs if "PLACE DES ARTS" in (a.get("title") or "").upper())
    hier = aujourdhui_montreal().isoformat()
    sans_rv = storage.client.table("place_des_arts_requests")\
        .select("appointment_date,room,for_who,piano,status")\
        .is_("appointment_id", "null").lt("appointment_date", hier)\
        .gte("appointment_date", (aujourdhui_montreal().replace(day=1)).isoformat())\
        .order("appointment_date").execute().data or []
    sans_rv = [d for d in sans_rv if (d.get("status") or "").upper() not in ("CANCELLED", "CANCELED")]
    return {"success": True,
            "rv_gazelle_pda_examines": nb_pda,
            "services_gazelle_absents_de_l_assistant": manquants,
            "demandes_du_mois_passees_sans_rv_gazelle": sans_rv,
            "note": ("Période : 60 derniers jours et à venir. Les services absents se règlent dans l'onglet "
                     "Place des Arts (bouton de vérification : « Ajouter » ou « Ignorer »).")}



DOSSIER_CLIENT_TOOL = {
    "name": "dossier_client",
    "description": ("Historique COMPLET d'un client Gazelle, en direct : fiche, chronologie (services, notes, "
                    "appels), factures, soumissions avec le suivi du courriel (envoyée ? ouverte par le client ?) "
                    "et tous les messages Gazelle envoyés avec leur statut (ouvert, cliqué, livré, rejeté, "
                    "désabonné). À utiliser pour « résume-moi ce client », « a-t-il ouvert la soumission ? », "
                    "« a-t-il reçu son rappel ? » — vérifier ici avant d'affirmer qu'un client n'a rien vu ou rien reçu."),
    "input_schema": {"type": "object", "required": ["client_id"],
                     "properties": {"client_id": {"type": "string", "description": "ID Gazelle cli_…"}}},
}

TOOLS = [VERIFIER_PDA_TOOL, AJOUTER_DEMANDE_PDA_TOOL, CATALOGUE_TOOL, CREER_SOUMISSION_TOOL, AJOUTER_COURRIEL_TOOL, LIEN_RESERVATION_TOOL, REACTIVATE_ESTIMATE_TOOL, REVIEW_ESTIMATE_TOOL, SEARCH_KEYWORD_TOOL,
         JOINT_APPOINTMENT_TOOL, CREER_RV_TOOL, LIST_CALLS_TOOL, ATTACH_PHOTOS_TOOL, FEATURE_REQUEST_TOOL,
         DOSSIER_CLIENT_TOOL, *_OUTILS_REGLES]


# ── Garde-fou heures ─────────────────────────────────────────────────
# Gazelle et Supabase renvoient des heures UTC (« …T13:00:00Z »). Le modèle les
# lirait telles quelles (13h au lieu de 9h). Avant de donner un résultat d'outil
# au modèle, TOUTE date-heure UTC est convertie en heure de Montréal.
import re as _re
_ISO_UTC = _re.compile(r"\b(\d{4}-\d{2}-\d{2})[T ](\d{2}:\d{2})(?::\d{2}(?:\.\d+)?)?(?:Z|\+00:00|\+0000)")


def _vers_montreal(valeur: Any) -> Any:
    from core.timezone_utils import utc_to_montreal
    if isinstance(valeur, str):
        def conv(m):
            try:
                dt = utc_to_montreal(f"{m.group(1)}T{m.group(2)}:00+00:00")
                return dt.strftime("%Y-%m-%d %Hh%M (heure de Montréal)")
            except Exception:
                return m.group(0)
        return _ISO_UTC.sub(conv, valeur)
    if isinstance(valeur, dict):
        return {k: _vers_montreal(v) for k, v in valeur.items()}
    if isinstance(valeur, list):
        return [_vers_montreal(v) for v in valeur]
    return valeur


def _run_tool(name: str, tool_input: Dict[str, Any],
              user_first_name: Optional[str] = None) -> Dict[str, Any]:
    """Exécute un outil et retourne un dict résultat (jamais d'exception qui remonte)."""
    from core import ivo_regles
    if _CANAL.get() == "ivo" and name in ivo_regles.ACTIONS_RESERVEES and not ivo_regles.peut_agir(user_first_name):
        return {"success": False, "error": ivo_regles.MESSAGE_LECTURE_SEULE}
    try:
        if name == "request_new_feature":
            if _CANAL.get() == "ivo":
                # Dans Front, Ivo relaie lui-même à Claude (transmettre_a_claude) : pas de courriel
                # en double à asutton@ pour la même demande.
                return {"success": False, "error": ("Pas de courriel à l'administrateur depuis Front : "
                        "dis simplement que tu ne sais pas le faire ; Ivo transmettra la demande à Claude.")}
            return execute_feature_request(
                summary=tool_input.get("summary", ""),
                original_request=tool_input.get("original_request", ""),
                user_first_name=user_first_name,
            )
        if name == "dossier_client":
            from core.historique_client import dossier_client
            return {"success": True, "dossier": dossier_client(tool_input.get("client_id") or "")}
        if name == "preparer_lien_reservation":
            return execute_lien_reservation(**tool_input)
        if name == "ajouter_demande_pda":
            return execute_ajouter_demande_pda(**tool_input)
        if name == "verifier_services_pda":
            return execute_verifier_pda()
        if name == "chercher_catalogue":
            return execute_catalogue(tool_input.get("mots") or [])
        if name == "creer_soumission":
            return execute_creer_soumission(**tool_input)
        if name == "reactivate_estimate":
            return duplicate_estimate(
                int(tool_input["estimate_number"]),
                reprice=bool(tool_input.get("reprice", False)),
            )
        if name == "review_estimate":
            return execute_review_estimate(
                estimate_number=tool_input.get("estimate_number"),
                client_name_hint=tool_input.get("client_name_hint"),
            )
        if name == "search_events_by_keyword":
            return execute_search_keyword(
                keyword=tool_input.get("keyword"),
                tech_filter_first_name=tool_input.get("tech_filter_first_name"),
                months_back=tool_input.get("months_back"),
            )
        if name == "create_joint_appointment":
            return execute_joint_appointment(**tool_input)
        if name == "creer_rendez_vous":
            return execute_creer_rv(**tool_input)
        if name == "ajouter_courriel_client":
            return execute_ajouter_courriel(**tool_input)
        if name in ("retenir_regle", "oublier_regle"):
            from core import ivo_regles
            return ivo_regles.executer(name, tool_input, user_first_name)
        if name == "attach_email_photos_to_piano":
            return execute_attach_photos(
                client_name=tool_input.get("client_name", ""),
                client_email=tool_input.get("client_email"),
                piano_id=tool_input.get("piano_id"),
                toutes=bool(tool_input.get("toutes", False)),
            )
        if name == "list_recent_calls":
            return execute_list_calls(
                technician_first_name=tool_input.get("technician_first_name"),
                hours_back=tool_input.get("hours_back"),
            )
        return {"success": False, "error": f"Outil inconnu : {name}"}
    except HTTPException as exc:
        return {"success": False, "error": f"{name} : {exc.detail}"}
    except Exception as exc:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        return {"success": False, "error": f"Erreur d'exécution ({name}) : {exc}"}


class ConverseMessage(BaseModel):
    role: str = Field(..., description="'user' ou 'assistant'")
    content: str


class ConverseRequest(BaseModel):
    messages: List[ConverseMessage]
    current_user_first_name: Optional[str] = None
    canal: str = "assistant"  # « ivo » quand la demande vient d'un commentaire @Ivo dans Front
    contexte: Optional[str] = None  # ex. le fil client Front, pour Ivo


@router.post("/converse", response_model=Dict[str, Any])
async def converse(req: ConverseRequest):
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY non configurée")
    if not req.messages:
        return {"reply": "Pose-moi une question ou une demande.", "actions": []}

    from anthropic import Anthropic
    client = Anthropic(api_key=api_key)

    today_iso = aujourdhui_montreal().isoformat()
    user_ctx = ""
    if req.current_user_first_name:
        user_ctx = f"\nL'utilisateur courant est {req.current_user_first_name}."

    system_prompt = (
        f"Tu es Ivo, l'assistant de Piano Technique Montréal (PTM). Dans l'appli comme dans Front (« @Ivo »), tu es le même assistant. Aujourd'hui : {today_iso}. "
        "Tu réponds en français, de façon concise et concrète. Techniciens connus : "
        "Allan, Nicolas, JP (Jean-Philippe), Margot.\n\n"
        "Tu as des OUTILS. Utilise-les quand c'est pertinent :\n"
        "- reactivate_estimate : créer une nouvelle soumission (brouillon) à partir "
        "d'un numéro. reprice=true pour « réactiver / à jour / nouveaux prix ».\n"
        "- creer_soumission : créer une soumission NEUVE (sans numéro de départ) pour un client. "
        "Ne demande PAS de numéro existant. Étapes : chercher_catalogue avec les mots-clés des travaux "
        "demandés, puis creer_soumission avec les service_id trouvés (le prix du catalogue s'applique). "
        "Ne devine jamais un prix : si un travail n'est pas au catalogue et que l'utilisateur n'a pas donné "
        "son montant, crée la soumission avec le reste et dis clairement quelle ligne manque, ou demande. "
        "« Avec les avertissements d'usage » : mets dans les notes une courte intro puis « À savoir avant "
        "de décider : » et des puces factuelles propres aux travaux (ex. cordes neuves qui s'étirent et "
        "demandent des accords de stabilisation la première année ; vieilles cordes qui peuvent casser à "
        "l'accord ; constats confirmables seulement une fois le travail commencé, soumis avant d'être "
        "exécutés ; équilibre sonore entre cordes neuves et d'origine). Aucun prix inventé dans les notes.\n"
        "- review_estimate : analyser/réviser une soumission existante.\n"
        "- search_events_by_keyword : retrouver des rendez-vous par mot-clé.\n"
        "- create_joint_appointment : créer un RV conjoint.\n"
        "- creer_rendez_vous : créer un rendez-vous pour un client (aperçu d'abord avec "
        "confirme=false, puis confirme=true seulement après un oui). « Demain », « jeudi » : "
        "calcule la date à partir d'aujourd'hui et montre-la dans l'aperçu.\n"
        "- list_recent_calls : liste des appels du Call Center Gazelle faits par un "
        "technicien (relances client, avec résultat noté). Si l'utilisateur dit "
        "« mes appels » sans préciser qui, utilise son prénom (indiqué ci-dessous).\n"
        "- preparer_lien_reservation : lien de réservation en ligne prérempli pour un client "
        "(coordonnées et piano, jamais le numéro civique) ; donne le lien tel quel.\n"
        "- ajouter_demande_pda : ajouter une demande Place des Arts (courriel de PdA, OSM, Opéra…) dans l'onglet "
        "Place des Arts. Sur ordre explicite (« ajoute la demande… »), fais-le directement avec confirme=true. "
        "Prends date, salle, pour qui, piano, diapason, heure et demandeur dans le courriel du fil. Ne crée pas le RV "
        "Gazelle en même temps (il se crée depuis la demande) et ne pose pas de question de facturation : "
        "la facturation PdA/OSM se règle dans l'onglet au moment de facturer.\n"
        "- verifier_services_pda : « est-ce que tous les services de PdA sont dans l'assistant ? » — "
        "compare Gazelle et l'onglet Place des Arts. Réponds par oui/non d'abord, puis liste ce qui manque "
        "(date, heure, technicien, piano, fait ou à venir). Si rien ne manque, dis combien de RV ont été vérifiés.\n"
        "- attach_email_photos_to_piano : ajouter au dossier du piano d'un client les "
        "photos qu'il a envoyées par courriel.\n\n"
        "HEURES : toutes les heures que tu reçois sont déjà en heure de Montréal ; "
        "ne fais jamais de conversion de fuseau horaire. Pour « le premier RV », passe "
        "source_time_hint='premier'.\n"
        "Sers-toi de l'HISTORIQUE : si l'utilisateur confirme (« oui », « vas-y ») une "
        "action que tu viens de proposer, exécute-la avec l'outil. Si une demande est "
        "ambiguë (numéro ou client manquant), pose UNE question courte au lieu de deviner.\n"
        "IMPORTANT : si AUCUN outil ne correspond à une vraie demande d'action (ex. déplacer / "
        "replanifier un rendez-vous existant, changer son lieu, modifier un client), n'utilise JAMAIS "
        "un outil qui ne convient pas : appelle request_new_feature pour transmettre la "
        "demande à l'administrateur, puis dis à l'utilisateur que tu ne sais pas encore le "
        "faire et que sa demande a été envoyée à l'administrateur (Allan). Ne promets "
        "jamais de revenir vers l'utilisateur plus tard : tu ne peux pas le faire. "
        "Les créations de soumission sont toujours des brouillons : rien n'est envoyé au client."
        + user_ctx
    )

    from core import ivo_regles
    system_prompt += ("\n\nPRINCIPE FONDAMENTAL — tu vérifies, tu ne te souviens pas : tout fait que tu affirmes "
                      "(client, piano, n° de série, prix, date, technicien, statut) doit venir d'un outil consulté dans "
                      "cette réponse. Le cahier de connaissances donne les règles de métier, ce n'est pas une base de "
                      "données : Gazelle fait foi pour les faits. Ne dis jamais qu'une chose manque, est inconnue ou est "
                      "réglée sans l'avoir vérifiée ; sinon écris [à vérifier] sans en tirer de conclusion.")
    if ivo_regles.cahier_pour_ia():
        system_prompt += "\n\n" + ivo_regles.cahier_pour_ia()
    if ivo_regles.texte_pour_ia():
        system_prompt += "\n\n" + ivo_regles.texte_pour_ia()
    system_prompt += ("\n\nAPPRENDRE : quand on te dit « la prochaine fois… », « dorénavant… », « à l'avenir… », "
                      "« ne fais plus… », appelle retenir_regle (règle claire : le cas + quoi faire) et confirme-la. "
                      "« Quelles sont tes règles ? » : liste-les avec leur numéro ; « oublie la règle N » : oublier_regle. "
                      "Seuls Allan, Nicolas et Louise peuvent donner ou retirer une règle.")
    if req.contexte:
        system_prompt += ("\n\nCONTEXTE (fil Front du client, à utiliser pour trouver le client, "
                          "ses coordonnées et sa demande) :\n" + req.contexte[:12000])
    _CANAL.set(req.canal or "assistant")
    _PRENOM.set(req.current_user_first_name)
    messages: List[Dict[str, Any]] = [{"role": m.role, "content": m.content} for m in req.messages]
    actions: List[Dict[str, Any]] = []

    # Boucle outil : Claude peut enchaîner quelques appels avant de répondre en texte.
    for _ in range(7):
        resp = client.messages.create(
            model="claude-sonnet-5",
            max_tokens=3000,
            system=system_prompt,
            tools=TOOLS,
            messages=messages,
        )
        tool_uses = [b for b in resp.content if getattr(b, "type", None) == "tool_use"]
        texts = [b.text for b in resp.content if getattr(b, "type", None) == "text"]

        if not tool_uses:
            return {"reply": " ".join(t for t in texts if t).strip()
                    or "D'accord.", "actions": actions}

        messages.append({"role": "assistant", "content": resp.content})
        tool_results = []
        for tu in tool_uses:
            result = _run_tool(tu.name, tu.input or {}, req.current_user_first_name)
            actions.append({"type": tu.name, "input": tu.input, "result": result})
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tu.id,
                "content": json.dumps(_vers_montreal(result), ensure_ascii=False, default=str),
            })
        messages.append({"role": "user", "content": tool_results})

    return {"reply": "J'ai fait plusieurs étapes mais je n'ai pas pu conclure — reformule ?",
            "actions": actions}
