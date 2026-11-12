"""Ivo — l'assistant qu'on interpelle dans un commentaire Front.

Fonctionnement :
- Un membre de l'équipe écrit un commentaire interne qui COMMENCE par « @Ivo »
  dans une conversation Front (ex. « @Ivo plus court et plus chaleureux »).
- Une règle Front (« commentaire ajouté » → « envoyer au webhook ») appelle
  POST /api/front/ivo/webhook.
- Ivo relit le fil, réécrit le brouillon de réponse (ou en crée un s'il n'y en
  a pas), répond par un commentaire, et retient la consigne si c'est une règle
  générale (system_settings.ivo_regles_reponse).

Sécurité : le contenu du webhook n'est jamais cru sur parole. Ivo relit le
commentaire directement dans Front avec son propre jeton : seul un vrai
commentaire « @Ivo » d'un coéquipier déclenche quelque chose. Rien n'est
jamais envoyé : Ivo ne touche qu'aux brouillons et aux commentaires.
"""
import html
import json
import logging
import os
import re
import threading

import requests
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, Request

from core.front_client import get_front_client

router = APIRouter(prefix="/front/ivo", tags=["front-ivo"])
_log = logging.getLogger(__name__)

VERSION = "2026-11-11-sans-voix-elevenlabs"
MODELE = os.getenv("IVO_MODELE_REDACTION", "claude-opus-5-5")
CLE_REGLES = "ivo_regles_reponse"
PREFIXE_REPONSE = "🤖 Ivo : "
_DECLENCHEUR = re.compile(r"^\s*@?ivo\b[\s,:;.\-–—]*", re.IGNORECASE)

import contextvars
_CTX = contextvars.ContextVar("ivo_ctx", default={})
_PRENOMS = {"asutton@piano-tek.com": "Allan", "nlessard@piano-tek.com": "Nicolas", "info@piano-tek.com": "Louise",
            "margotcharignon@gmail.com": "Margot", "jpreny@gmail.com": "JP"}

_deja_traites: set = set()          # commentaires déjà pris en charge (évite les doublons)
_verrou = threading.Lock()


# ─── Utilitaires ─────────────────────────────────────────────────


def _est_photo(x: Dict[str, Any]) -> bool:
    """Photo envoyée par le client : pièce jointe image, OU image insérée dans le corps
    du courriel (cas courant depuis un iPhone) si elle fait au moins 30 Ko — les petites
    images insérées sont des logos de signature."""
    if not (x.get("content_type") or "").startswith("image/"):
        return False
    if not (x.get("metadata") or {}).get("is_inline"):
        return True
    return (x.get("size") or 0) >= 30000

def _texte(html_ou_texte: str) -> str:
    """HTML Front → texte simple."""
    t = re.sub(r"<br\s*/?>|</p>|</div>", "\n", html_ou_texte or "", flags=re.IGNORECASE)
    t = html.unescape(re.sub(r"<[^>]+>", "", t))
    return re.sub(r"\n{3,}", "\n\n", t).strip()


def _en_html(texte: str) -> str:
    """Texte simple → paragraphes HTML (ligne vide = nouveau paragraphe)."""
    blocs = [b for b in re.split(r"\n\s*\n", texte.strip()) if b.strip()]
    return "".join("<p>" + "<br>".join(html.escape(l) for l in b.split("\n")) + "</p>" for b in blocs)


def consigne_ivo(corps: str) -> Optional[str]:
    """Retourne la consigne si le commentaire commence par @Ivo, sinon None."""
    t = _texte(corps)
    if t.startswith("🤖"):
        return None  # nos propres réponses
    m = _DECLENCHEUR.match(t)
    if not m:
        return None
    return t[m.end():].strip() or "Améliore ce brouillon."


def _regles() -> List[str]:
    from core import ivo_regles
    return [r["regle"] for r in ivo_regles.lire()]


_TARIFS_CACHE: Dict[str, Any] = {"t": 0.0, "texte": ""}


def _tarifs() -> str:
    """Grille de prix de PTM, lue dans la liste des services de Gazelle (celle qui sert à facturer).
    Gardée une heure en mémoire."""
    import time
    if _TARIFS_CACHE["texte"] and time.time() - _TARIFS_CACHE["t"] < 3600:
        return _TARIFS_CACHE["texte"]
    from core.gazelle_api_client import GazelleAPIClient
    res = GazelleAPIClient()._execute_query("query { allMasterServiceItems { name amount isArchived type } }")
    items = ((res or {}).get("data") or {}).get("allMasterServiceItems") or []
    from api.taches_routes import _nom_i18n
    lignes = sorted({f"{(i.get('amount') or 0) / 100:.2f} $ — {_nom_i18n(i.get('name')).strip()[:220]}"
                     for i in items if not i.get("isArchived") and (i.get("amount") or 0) > 0})
    texte = "\n".join(lignes)
    _TARIFS_CACHE.update(t=time.time(), texte=texte)
    return texte


def _guide_ton() -> str:
    chemin = os.path.join(os.path.dirname(__file__), "..", "workspace", "guide-ton-ptm.md")
    try:
        with open(chemin, encoding="utf-8") as f:
            return f.read()[:6000]
    except OSError:
        return ""


# ─── Rédaction (Claude) ──────────────────────────────────────────

_SYSTEME = """Tu es Ivo, l'assistant de Piano Technique Montréal (PTM), entreprise d'accord et d'entretien de pianos.
Un membre de l'équipe te donne une consigne pour le brouillon de réponse à un client, ou te pose une question.

PRINCIPE FONDAMENTAL — tu vérifies, tu ne te souviens pas.
Tout fait que tu affirmes (client, piano, numéro de série, emplacement, prix, frais, date, disponibilité, technicien, statut d'un RV, d'une facture ou d'une soumission) doit venir de ce que tu as consulté DANS CETTE RÉPONSE : le fil, un de tes outils, la grille des tarifs ou l'horaire fournis.
- Le cahier de connaissances donne les règles de métier de PTM (tarifs, politiques, façons de faire). Ce n'est PAS une base de données : il ne contient pas tous les clients, pianos ou RV. Gazelle et Front font foi pour les faits.
- Avant de dire qu'une chose manque, est inconnue, ne correspond à rien, est faite ou est réglée, vérifie-la avec l'outil qui la connaît (« chercher_client » donne les pianos du client avec leur n° de série ; « lire_rv », « dossier_front »…).
- Si tu ne peux pas vérifier, écris [à vérifier] et n'en tire aucune conclusion. Ne signale jamais une anomalie qui ne repose que sur ce que tu crois savoir.

Tes outils d'abord : ne réponds jamais « je ne peux pas » ou « je n'ai pas accès » sans avoir essayé tes outils. Tu as directement ceux de l'assistant Gazelle (soumissions, recherche dans les notes, appels récents, RV d'accompagnement, liens de réservation, photos d'un courriel, courriel d'un client…) ; « demander_assistant » n'est qu'un secours. Si, après ça, tu ne peux pas faire la demande ou y répondre avec certitude, appelle « transmettre_a_claude » (pas pour une simple rédaction de brouillon ni pour une question que tes outils règlent).

Dossier du client : lis TOUT le fil, à commencer par le premier message du client, et ne redemande jamais une information déjà donnée. Vérifie avec « chercher_client » (courriel, téléphone, puis nom) s'il a une fiche, des visites et des pianos ; avec « dossier_front » (téléphone, courriel, nom), ses autres fils : messages vocaux, textos et résumés d'appel y sont souvent. Pour l'historique Gazelle complet (services, factures, soumissions ouvertes ou non, courriels reçus/ouverts, désabonnement), utilise « dossier_client » avec son client_id. Ne mélange jamais deux clients : un fil ou une fiche ne compte que s'il correspond au même téléphone, courriel ou nom.
- Coordonnées : chaque message du fil indique son expéditeur et ses destinataires (« → à : Nom <courriel> »). Quand c'est PTM qui écrit, le client est dans les destinataires : prends son nom complet et son courriel de là pour la fiche, au lieu d'écrire qu'ils manquent.
- Aucune fiche : crée-la avec « creer_client » (client potentiel), sans attendre qu'on te le demande, et dis-le dans ta note. Une fiche qui correspond déjà (même courriel, téléphone, ou nom et ville) : n'en crée pas, signale un doublon possible.
- Le piano décrit par le client doit être dans sa fiche : sinon, « ajouter_piano » (marque, modèle, type) avant de créer le RV, et passe son id dans piano_ids. Une coquille évidente de modèle (ex. « BG-1 » pour un Yamaha GB1) : corrige-la et signale-le.
- Client existant : reprends ce qui a été fait, le technicien habituel et les frais de déplacement DÉJÀ FACTURÉS ; un écart avec le calculateur se signale à l'équipe, et le brouillon garde [frais à confirmer] tant qu'elle n'a pas tranché. Provenance : un « accord de courtoisie <marchand> » dans une facture veut dire que ce marchand nous a envoyé le client.
- Nouveau client (aucune visite passée) : la note du RV doit dire au technicien de demander comment le client nous a trouvés.

Consigne ambiguë : une consigne dictée peut être mal transcrite (« corrige » / « corrigé »). Si elle peut se lire comme un ORDRE ou comme un CONSTAT, ne choisis pas : demande laquelle dans ta note (action "reponse"), sans rien faire.

Prix et frais : jamais devinés. Le prix doit correspondre au service ET à la durée réellement demandés ou réservés (un RV de 3 h n'est pas une visite de base : cherche dans la grille le service de cette durée) ; un prix déjà annoncé par l'équipe dans le fil se reprend tel quel. Les services nommés d'après une institution ou un marchand (PdA, UQAM, Grands Ballets, Nantel, Archambault, Piano Vertu) ne s'appliquent qu'à eux. Frais de déplacement : appelle « frais_deplacement » avec l'adresse ou le code postal du client et donne le montant tel quel ; si l'outil échoue, [frais à confirmer]. Regrouper une visite avec un RV voisin ne change pas les frais, sauf décision de l'équipe.

Brouillon au client : langue du client, vouvoiement, pas de signature dans le corps (Front l'ajoute) : termine par la formule de politesse. Tu ne fais que préparer : un humain relit et envoie.

Principe premier : VÉRIFIE AVANT D'AFFIRMER. Tes outils lisent Gazelle et Front en direct ; ta mémoire et le cahier ne remplacent jamais une vérification. N'écris jamais qu'une information manque, qu'elle est inconnue ou qu'une chose est impossible sans avoir d'abord appelé l'outil qui la donne ; si un outil renvoie un résultat étrange, dis exactement ce qu'il a renvoyé au lieu de généraliser.

Horaire : appelle « consulter_horaire » pour les dates en jeu (avec « secteur » = ville, quartier ou début de code postal du client et des villes voisines quand la géographie compte). Il donne chaque RV avec sa ville et son code postal, les RV déjà prévus dans le secteur (à jumeler) et les plages libres de chaque technicien. « Occupé » = bloc personnel, dont tu ne mentionnes jamais la nature. Raisonne sur la géographie et la route, propose concrètement qui, quel jour et à quelle heure, et dis quand c'est serré ou incertain. Allan ne fait plus de visites : propose Nicolas, JP (Jean-Philippe) ou Margot.
Identifiants des techniciens : usr_HcCiFk7o0vZ9xAI0 = Nicolas ; usr_ReUSmIJmBF86ilY1 ou usr_QmEpdeM2xMgZVkDS = JP (Jean-Philippe) ; usr_bbt59aCUqUaDWA8n = Margot ; usr_ofYggsCDt2JAVeNP ou usr_tndhXmnT0iakT4HF = Allan ; usr_HihJsEgkmpTEziJo = « À attribuer ».

Actions :
- Créer un RV : sur ordre explicite de l'équipe (« crée le RV », « oui », « vas-y ») et quand tu connais le client, le technicien, le jour, l'heure et la durée, crée-le DIRECTEMENT avec « creer_rendez_vous », avec des notes complètes pour le technicien, sans aperçu. S'il manque un élément, demande seulement celui-là. Jamais de confirmation automatique au client.
- Un bloc personnel du technicien occupe déjà la plage pour CE client (ex. « accorder fazioli à la maison trestler ») : c'est la place réservée. Transforme-le en vrai RV avec « convertir_bloc_en_rv » au lieu de répondre qu'il y a un conflit.
- Facture (« fais la facture », « facture alternative à X ») : « creer_facture » crée le brouillon dans Gazelle, avec la facturation alternative (facturer_a_client_id) et le technicien ; passe rv_id pour écrire « Facture créée » dans le RV. Le prix vient du fil ou de la grille. Ne dis jamais qu'aucun outil ne fait de facture.
- Bloquer un technicien (« bloque JP mardi matin ») : « bloquer_technicien » crée un bloc personnel « RÉSERVÉ (à confirmer) », sans avis au client ; ce n'est jamais un vrai RV.
- Tout ce que sait faire la case de l'assistant de Ma Journée : utilise l'outil correspondant et rapporte son résultat (action "reponse"). Repères : soumission NEUVE (pas de numéro de départ) → chercher_catalogue puis creer_soumission, sans demander de numéro existant ; reprice=true pour réactiver une soumission « à jour » (toujours un brouillon) ; « mes appels » sans nom = la personne qui t'écrit ; « le premier RV » : source_time_hint='premier' ; les heures rendues sont déjà en heure de Montréal ; un lien de réservation se donne tel quel ; frais partagés entre plusieurs clients : calculateur « Frais partagés » de l'assistant.

Apprendre : ce qui est déjà dans le cahier ne se réenseigne pas. Si ton dernier commentaire dans le fil propose une règle tirée d'une modification de ton brouillon (« Je retiens pour les prochains clients : … ? ») et qu'on te répond oui (ou avec une correction), appelle « retenir_regle » avec cette règle, corrigée s'il y a lieu, puis confirme-la. Quand l'équipe dit « la prochaine fois… », « dorénavant… », « ne fais plus… », appelle « retenir_regle » avec une règle générale (le cas + quoi faire) et confirme-la. « Quelles sont tes règles ? » : liste-les avec leur numéro ; « oublie la règle 3 » : « oublier_regle ». Seuls Allan, Nicolas et Louise peuvent donner ou retirer une règle.

Deux sortes de consignes :
A) Une correction du brouillon (« plus court », « propose la réservation en ligne »…) → action "brouillon".
B) Une question pour l'équipe (« qui est dans le coin à ces dates ? »…) → action "reponse" : réponds dans "note", sans toucher au brouillon.
Transmets OBLIGATOIREMENT ton résultat en appelant l'outil « repondre », sans autre texte : {"action": "brouillon" ou "reponse", "brouillon": "..." ou null, "regle_generale": "..." ou null, "note": "..."}
- brouillon : (action "brouillon" seulement) le texte complet du nouveau brouillon (texte simple, paragraphes séparés par une ligne vide).
- regle_generale : null (pour retenir une règle, utilise l'outil « retenir_regle »).
- note : pour "brouillon", une phrase (ce que tu as changé, ce qui reste à vérifier) ; pour "reponse", la réponse complète à la question, courte et concrète."""


def _villes_clients(ids: set) -> Dict[str, str]:
    """Ville + code postal des clients (table gazelle_clients), pour situer les RV."""
    from urllib.parse import quote
    if not ids:
        return {}
    from core.supabase_storage import SupabaseStorage
    st = SupabaseStorage(silent=True)
    sortie: Dict[str, str] = {}
    ids = sorted(ids)
    for i in range(0, len(ids), 80):
        lot = ",".join(quote(x) for x in ids[i:i + 80])
        r = requests.get(f"{st.api_url}/gazelle_clients?select=external_id,city,postal_code&external_id=in.({lot})",
                         headers=st._get_headers(), timeout=15)
        if r.status_code == 200:
            for c in r.json():
                v = " ".join(x for x in (c.get("city"), c.get("postal_code")) if x)
                if v:
                    sortie[c["external_id"]] = v
    return sortie


_NOMS_TECH = {"usr_HcCiFk7o0vZ9xAI0": "Nicolas", "usr_ofYggsCDt2JAVeNP": "Allan", "usr_tndhXmnT0iakT4HF": "Allan",
              "usr_ReUSmIJmBF86ilY1": "JP", "usr_QmEpdeM2xMgZVkDS": "JP", "usr_bbt59aCUqUaDWA8n": "Margot",
              "usr_HihJsEgkmpTEziJo": "À attribuer"}
_EVTS_TEST = contextvars.ContextVar("ivo_evts_test", default=None)   # horaire figé des cas de test


def _evenements(debut, fin) -> List[Dict[str, Any]]:
    """RV et blocs de l'équipe entre deux dates (Gazelle en direct, ou horaire figé en test).
    Chaque élément : jour, debut/fin (datetime Montréal), tech, client (bool), titre, lieu."""
    from datetime import datetime, timedelta
    from core.timezone_utils import MONTREAL_TZ
    evs = _EVTS_TEST.get()
    if evs is None:
        from core.gazelle_api_client import GazelleAPIClient
        evs = GazelleAPIClient().get_appointments(start_date_override=debut.isoformat(),
                                                  end_date_override=(fin + timedelta(days=1)).isoformat()) or []
        villes = _villes_clients({(e.get("client") or {}).get("id") for e in evs} - {None})
    else:
        villes = {}
    sortie = []
    for e in evs:
        if (e.get("status") or "").upper() in ("CANCELLED", "CANCELED") or (e.get("type") or "") == "MEMO":
            continue
        try:
            d = datetime.fromisoformat(e["start"].replace("Z", "+00:00")).astimezone(MONTREAL_TZ)
        except Exception:
            continue
        if not (debut <= d.date() <= fin):
            continue
        client = e.get("type") == "APPOINTMENT"
        lieu = ""
        if client:
            loc = e.get("location") or {}
            lieu = (" ".join(x for x in (loc.get("municipality"), loc.get("postalCode")) if x)
                    or (loc.get("singleLineAddress") or "").strip()
                    or villes.get((e.get("client") or {}).get("id")) or "")
        fin_ev = d + timedelta(minutes=int(e.get("duration") or 60))
        if e.get("isAllDay"):
            d, fin_ev = d.replace(hour=0, minute=0), d.replace(hour=23, minute=59)
        sortie.append({"jour": d.date(), "debut": d, "fin": fin_ev, "journee": bool(e.get("isAllDay")),
                       "tech": _NOMS_TECH.get((e.get("user") or {}).get("id"), "?"), "client": client,
                       "titre": (e.get("title") or "")[:40], "lieu": lieu})
    return sorted(sortie, key=lambda x: (x["debut"], x["tech"]))


def _ligne_ev(x: Dict[str, Any]) -> str:
    quand = (f"{x['jour']:%Y-%m-%d %a} toute la journée" if x["journee"]
             else f"{x['jour']:%Y-%m-%d %a} {x['debut']:%H:%M}-{x['fin']:%H:%M}")
    quoi = (f"RV client « {x['titre']} » à {x['lieu'] or 'adresse absente de Gazelle'}" if x["client"] else "occupé")
    return f"{quand} — {x['tech']} : {quoi}"


def _horaire(jours: int = 45) -> str:
    """Horaire de l'équipe (lecture seule) : RV clients avec ville, blocs perso réduits à « occupé »."""
    from datetime import datetime, timedelta
    from core.timezone_utils import MONTREAL_TZ
    debut = datetime.now(MONTREAL_TZ).date()
    return "\n".join(_ligne_ev(x) for x in _evenements(debut, debut + timedelta(days=jours)))


def _consulter_horaire(arg: Dict[str, Any]) -> str:
    """Outil d'Ivo : horaire d'une période, RV dans un secteur, et plages libres de chaque technicien."""
    from datetime import date, datetime, timedelta
    from core.timezone_utils import MONTREAL_TZ
    try:
        debut = date.fromisoformat(arg["debut"])
        fin = date.fromisoformat(arg.get("fin") or arg["debut"])
        h0, h1 = arg.get("heure_debut") or "08:00", arg.get("heure_fin") or "18:00"
        datetime.strptime(h0, "%H:%M"), datetime.strptime(h1, "%H:%M")
    except Exception:
        return "Dates ou heures illisibles : dates AAAA-MM-JJ, heures HH:MM (ex. 08:00)."
    if fin < debut:
        debut, fin = fin, debut
    if (fin - debut).days > 31:
        fin = debut + timedelta(days=31)
    techs = [t for t in (arg.get("techniciens") or ["Nicolas", "JP", "Margot"])]
    evs = _evenements(debut, fin)
    parties = [f"HORAIRE du {debut} au {fin} (heure de Montréal ; « occupé » = bloc personnel, nature jamais mentionnée) :"]
    parties += [_ligne_ev(x) for x in evs if x["tech"] in techs or x["tech"] in ("À attribuer", "?")] or ["(rien à l'horaire)"]
    brut = arg.get("secteur")
    brut = [brut] if isinstance(brut, str) else (brut or [])
    secteur = [s.strip().lower() for s in brut if s and s.strip()]
    if secteur:
        proches = [x for x in evs if x["client"] and any(s in x["lieu"].lower() for s in secteur)]
        parties.append(f"\nRV DANS LE SECTEUR ({', '.join(brut)}) — tous techniciens, à jumeler si possible :")
        parties += [_ligne_ev(x) for x in proches] or ["(aucun RV dans ce secteur pendant cette période)"]
    sans_lieu = sum(1 for x in evs if x["client"] and not x["lieu"])
    if sans_lieu:
        parties.append(f"\n({sans_lieu} RV sans adresse dans Gazelle : ce sont des exceptions, pas tout l'horaire.)")
    parties.append(f"\nPLAGES LIBRES ({h0}-{h1}, durée en minutes ; la route n'est pas déduite) :")
    j = debut
    while j <= fin:
        if j.weekday() < 5:
            bornes = (datetime.combine(j, datetime.strptime(h0, "%H:%M").time(), MONTREAL_TZ),
                      datetime.combine(j, datetime.strptime(h1, "%H:%M").time(), MONTREAL_TZ))
            morceaux = []
            for t in techs:
                pris = sorted((max(x["debut"], bornes[0]), min(x["fin"], bornes[1]))
                              for x in evs if x["tech"] == t and x["jour"] == j
                              and x["fin"] > bornes[0] and x["debut"] < bornes[1])
                libres, curseur = [], bornes[0]
                for a, b in pris:
                    if a > curseur:
                        libres.append((curseur, a))
                    curseur = max(curseur, b)
                if curseur < bornes[1]:
                    libres.append((curseur, bornes[1]))
                txt = ", ".join(f"{a:%H:%M}-{b:%H:%M} ({int((b - a).total_seconds() // 60)})"
                                for a, b in libres if (b - a).total_seconds() >= 1800)
                morceaux.append(f"{t} : {txt or 'aucune'}")
            parties.append(f"{j:%Y-%m-%d %a} — " + " ; ".join(morceaux))
        j += timedelta(days=1)
    return "\n".join(parties)[:15000]


def _factures_resume(client_id: str) -> str:
    """3 dernières factures Gazelle : date, technicien, total, et frais de déplacement facturés."""
    try:
        from core.gazelle_api_client import GazelleAPIClient
        from api.taches_routes import _Q_FACTURES_CLIENT
        noms = {"usr_HcCiFk7o0vZ9xAI0": "Nicolas", "usr_ofYggsCDt2JAVeNP": "Allan", "usr_tndhXmnT0iakT4HF": "Allan",
                "usr_ReUSmIJmBF86ilY1": "JP", "usr_QmEpdeM2xMgZVkDS": "JP", "usr_bbt59aCUqUaDWA8n": "Margot"}
        res = GazelleAPIClient()._execute_query(_Q_FACTURES_CLIENT, {"c": client_id})
        nodes = (((res or {}).get("data") or {}).get("allInvoices") or {}).get("nodes") or []
        if not nodes:
            return "\n   Factures : aucune."
        sortie = []
        for f in sorted(nodes, key=lambda f: f.get("createdAt") or "", reverse=True)[:3]:
            items = ((f.get("allInvoiceItems") or {}).get("nodes")) or []
            depl = [i for i in items if "déplacement" in (i.get("description") or "").lower()
                    or "deplacement" in (i.get("description") or "").lower()]
            travaux = "; ".join((i.get("description") or "")[:70] for i in items if i not in depl)[:200]
            frais = (f"frais de déplacement facturés : {sum(i.get('amount') or 0 for i in depl) / 100:.2f} $"
                     if depl else "aucuns frais de déplacement facturés")
            tech = noms.get(((f.get("assignedTo") or {}).get("id")) or "", "?")
            sortie.append(f"   Facture du {(f.get('createdAt') or '')[:10]} ({tech}, {f.get('status')}) : "
                          f"{(f.get('subTotal') or 0) / 100:.2f} $ avant taxes — {travaux} — {frais}")
        return "\n" + "\n".join(sortie)
    except Exception as e:
        return f"\n   Factures : non disponibles ({e})."



# ─── Dossier complet dans Front (autres fils du même client) ─────────────

def _variantes_tel(tel: str) -> List[str]:
    chiffres = re.sub(r"\D", "", tel or "")
    if len(chiffres) == 11 and chiffres.startswith("1"):
        chiffres = chiffres[1:]
    if len(chiffres) != 10:
        return [tel] if tel else []
    a, b, c = chiffres[:3], chiffres[3:6], chiffres[6:]
    return [chiffres, f"{a}-{b}-{c}", f"({a}) {b}-{c}", f"{a} {b}-{c}"]


def _dossier_front(arg: Dict[str, Any]) -> str:
    """Cherche dans tout Front les AUTRES fils du même client (messages vocaux, textos,
    résumés d'appel, courriels) par téléphone, courriel ou nom, et en donne le contenu."""
    front = get_front_client()
    courant = (_CTX.get() or {}).get("conversation_id")
    requetes: List[str] = []
    for t in (arg.get("telephones") or []):
        requetes += _variantes_tel(t)
    if arg.get("courriel"):
        requetes.append(arg["courriel"])
    if arg.get("nom"):
        requetes.append(f'"{arg["nom"]}"')
    vus: Dict[str, Dict] = {}
    for q in requetes:
        try:
            for c in front.search_conversations(q, limit=15):
                if c.get("id") and c["id"] != courant:
                    vus.setdefault(c["id"], c)
        except Exception as e:
            _log.warning("Ivo dossier_front : recherche %r : %s", q, e)
    if not vus:
        return "Aucun autre fil trouvé dans Front pour ce client."
    convs = sorted(vus.values(), key=lambda c: c.get("last_message_at") or c.get("created_at") or 0, reverse=True)[:8]
    ctx = _CTX.get() or {}
    sortie = []
    for c in convs:
        bloc = [f"=== Fil « {c.get('subject') or '(sans objet)'} » ({c['id']}) ==="]
        try:
            for m in sorted(front.list_messages(c["id"], limit=10), key=lambda m: m.get("created_at") or 0)[-6:]:
                qui = "CLIENT" if m.get("is_inbound") else "PTM"
                photos = [x for x in (m.get("attachments") or []) if _est_photo(x)]
                if photos and m.get("is_inbound"):
                    ctx.setdefault("photos", []).extend(photos[:8])
                pj = f" [{len(photos)} photo(s) — outil analyser_photos]" if photos else ""
                bloc.append(f"--- {qui} ---\n{_texte(m.get('text') or m.get('body') or '')[:1500]}{pj}")
            for co in front.list_comments(c["id"], limit=10)[-5:]:
                bloc.append(f"[commentaire interne] {_texte(co.get('body') or '')[:400]}")
        except Exception as e:
            bloc.append(f"(lecture impossible : {e})")
        sortie.append("\n".join(bloc))
    return "\n\n".join(sortie)[:14000]


# ─── RV créé directement sur ordre explicite ────────────────────────────

_TECHS = {"Nicolas": "usr_HcCiFk7o0vZ9xAI0", "JP": "usr_ReUSmIJmBF86ilY1", "Margot": "usr_bbt59aCUqUaDWA8n"}


def _creer_rv_direct(arg: Dict[str, Any]) -> str:
    from datetime import datetime, timedelta
    from core.timezone_utils import MONTREAL_TZ
    from api.taches_routes import creer_rendez_vous, RendezVousIn, charge_techniciens
    tech = arg.get("technicien") or ""
    uid = _TECHS.get(tech)
    if not uid:
        return "Technicien inconnu (Nicolas, JP ou Margot) : rien créé."
    try:
        debut = datetime.fromisoformat(arg["debut"]).replace(tzinfo=MONTREAL_TZ)
    except Exception:
        return "Date ou heure illisible (AAAA-MM-JJTHH:MM) : rien créé."
    if debut < datetime.now(MONTREAL_TZ):
        return "Date passée : rien créé."
    duree = int(arg.get("duree_min") or 0)
    if duree <= 0:
        return "Durée manquante : rien créé (demande-la à l'équipe)."
    fin = debut + timedelta(minutes=duree)
    # Garde-fou : aucun chevauchement avec l'horaire du technicien
    try:
        jour = debut.strftime("%Y-%m-%d")
        for e in charge_techniciens(debut=jour, fin=jour).get("evenements") or []:
            if e.get("tech") != tech or e.get("journee"):
                continue
            d = datetime.fromisoformat(f"{e['jour']}T{e['heure']}").replace(tzinfo=MONTREAL_TZ)
            f = d + timedelta(minutes=int(e.get("duree_min") or 0))
            if d < fin and debut < f:
                if e.get("type") == "PERSONAL":
                    return (f"Conflit : {tech} a déjà le bloc personnel « {e.get('titre')} » ({e.get('id')}) de "
                            f"{d:%H:%M} à {f:%H:%M}. Si ce bloc est réservé pour CE client, utilise "
                            "« convertir_bloc_en_rv » avec ce bloc : il devient le vrai RV. Sinon, propose une autre heure.")
                return (f"Conflit : {tech} a déjà « {e.get('titre')} » de {d:%H:%M} à {f:%H:%M} ce jour-là. "
                        "Rien créé : propose une autre heure à l'équipe.")
    except Exception as e:
        _log.warning("Ivo : vérification d'horaire impossible : %s", e)
        return "Je n'ai pas pu vérifier l'horaire du technicien : rien créé, par prudence."
    prenom = (_CTX.get() or {}).get("prenom") or "l'équipe"
    try:
        res = creer_rendez_vous(RendezVousIn(
            client_id=arg["client_id"], user_id=uid, debut_montreal=debut.strftime("%Y-%m-%dT%H:%M"),
            duree_min=duree, notes=arg.get("notes"), piano_ids=arg.get("piano_ids") or [],
            lieu=arg.get("lieu"), par=f"Ivo (assistant IA) à la demande de {prenom}"))
    except Exception as e:
        return f"Gazelle a refusé le RV : {getattr(e, 'detail', e)}"
    ev = res.get("evenement") or {}
    return (f"RV créé dans Gazelle ({ev.get('id')}) : {ev.get('title')}, {tech}, {debut:%A %d %B %Y} "
            f"de {debut:%H:%M} à {fin:%H:%M}. Aucune confirmation envoyée au client.")

def _creer_facture(arg: Dict[str, Any]) -> str:
    """Facture Gazelle en brouillon + facturation alternative + mention « Facture créée » dans le RV."""
    from api.taches_routes import (creer_facture, FactureIn, LigneFacture, maj_facture, FactureMajIn,
                                   modifier_rendez_vous, ModifRvIn)
    lignes = [LigneFacture(description=l["description"], montant=float(l["montant"]),
                           service_id=l.get("service_id"), piano_id=l.get("piano_id"))
              for l in (arg.get("lignes") or []) if l.get("description") and l.get("montant") is not None]
    if not lignes:
        return "Aucune ligne avec description et montant : rien créé."
    uid = _TECHS.get(arg.get("technicien") or "")
    try:
        f = creer_facture(FactureIn(client_id=arg["client_id"], lignes=lignes, assigne_a=uid))
    except Exception as e:
        return f"Gazelle a refusé la facture : {getattr(e, 'detail', e)}"
    msg = [f"Facture n° {f.get('numero')} créée en BROUILLON ({f.get('id')}) : sous-total {f.get('sous_total')} $, "
           f"total {f.get('total')} $ taxes incluses. Rien envoyé."]
    alt = ""
    if arg.get("facturer_a_client_id"):
        try:
            m = maj_facture(f["id"], FactureMajIn(facturer_a_client_id=arg["facturer_a_client_id"]))
            alt = m.get("facture_a") or "la fiche demandée"
            msg.append(f"Facturation alternative : {alt}.")
        except Exception as e:
            msg.append(f"⚠️ Facturation alternative NON appliquée : {getattr(e, 'detail', e)}")
    if arg.get("rv_id"):
        note = f"Facture créée (n° {f.get('numero')}, brouillon" + (f", facturée à {alt}" if alt else "") + ")."
        try:
            modifier_rendez_vous(arg["rv_id"], ModifRvIn(notes_ajout=note))
            msg.append(f"Écrit dans le RV {arg['rv_id']} : « {note} »")
        except Exception as e:
            msg.append(f"⚠️ Note du RV non écrite : {getattr(e, 'detail', e)}")
    return " ".join(msg)


_NOMS_TECHS = {"usr_HcCiFk7o0vZ9xAI0": "Nicolas", "usr_ofYggsCDt2JAVeNP": "Allan", "usr_tndhXmnT0iakT4HF": "Allan",
               "usr_ReUSmIJmBF86ilY1": "JP", "usr_QmEpdeM2xMgZVkDS": "JP", "usr_bbt59aCUqUaDWA8n": "Margot",
               "usr_HihJsEgkmpTEziJo": "À attribuer"}

_Q_RV_IVO = """query($id: String!) { event(eventId: $id) { id title start duration status notes
  client { id } user { id firstName }
  allEventPianos(first: 20) { nodes { piano { id make model serialNumber } } } } }"""


def _lire_rv(arg: Dict[str, Any]) -> str:
    """LECTURE SEULE : un RV Gazelle (evt_…) tel qu'il est maintenant, avec ses pianos,
    son technicien en clair et les demandes Place des Arts qui y sont liées."""
    from datetime import datetime
    from urllib.parse import quote
    from core.gazelle_api_client import GazelleAPIClient
    from core.supabase_storage import SupabaseStorage
    from core.timezone_utils import MONTREAL_TZ
    eid = (arg.get("rv_id") or "").strip()
    if not eid.startswith("evt_"):
        return "Identifiant de RV invalide (il commence par evt_)."
    res = GazelleAPIClient()._execute_query(_Q_RV_IVO, {"id": eid}) or {}
    ev = (res.get("data") or {}).get("event")
    if not ev:
        return f"RV {eid} introuvable dans Gazelle (supprimé ?)."
    debut = datetime.fromisoformat(ev["start"].replace("Z", "+00:00")).astimezone(MONTREAL_TZ)
    uid = (ev.get("user") or {}).get("id")
    pianos = [n.get("piano") or {} for n in ((ev.get("allEventPianos") or {}).get("nodes") or [])]
    lignes = [f"RV {eid} : « {ev.get('title') or ''} », {debut:%Y-%m-%d %H:%M}, {ev.get('duration') or '?'} min, "
              f"statut {ev.get('status')}, technicien {_NOMS_TECHS.get(uid, (ev.get('user') or {}).get('firstName') or uid)}.",
              f"Pianos du RV ({len(pianos)}) : " + ("; ".join(
                  f"{p.get('make') or ''} {p.get('model') or ''} n° {p.get('serialNumber') or '?'} ({p.get('id')})"
                  for p in pianos) or "aucun")]
    if ev.get("notes"):
        lignes.append(f"Notes du RV : {ev['notes'][:600]}")
    st = SupabaseStorage(silent=True)
    r = requests.get(f"{st.api_url}/place_des_arts_requests?select=id,appointment_date,room,for_who,piano,time,"
                     f"technician_id,status,notes&appointment_id=eq.{quote(eid)}", headers=st._get_headers(), timeout=15)
    dem = r.json() if r.status_code == 200 else []
    if dem:
        lignes.append(f"Demandes Place des Arts liées à ce RV ({len(dem)}) :")
        for d in dem:
            lignes.append(f"- {d['id']} : {str(d.get('appointment_date') or '')[:10]} {d.get('room')} "
                          f"« {d.get('for_who')} », piano « {d.get('piano')} », {d.get('time') or 'sans heure'}, "
                          f"technicien noté dans l'assistant : {_NOMS_TECHS.get(d.get('technician_id'), d.get('technician_id') or 'aucun')}, "
                          f"statut {d.get('status')}" + (f" — note : {d['notes'][:300]}" if d.get("notes") else ""))
    return "\n".join(lignes)


# Outils de la case de l'assistant, donnés DIRECTEMENT à Ivo (sans repasser par une seconde IA).
# Exclus : ceux qu'Ivo a déjà en mieux (creer_rendez_vous direct, retenir/oublier_regle) et
# request_new_feature (remplacé par transmettre_a_claude).
_OUTILS_ASSISTANT_EXCLUS = {"creer_rendez_vous", "request_new_feature", "retenir_regle", "oublier_regle"}


def _outils_assistant() -> List[Dict[str, Any]]:
    try:
        from api.assistant_converse import TOOLS
        return [t for t in TOOLS if t.get("name") not in _OUTILS_ASSISTANT_EXCLUS]
    except Exception:
        _log.exception("Ivo : outils de l'assistant indisponibles")
        return []


def _noms_outils_assistant() -> set:
    return {t["name"] for t in _outils_assistant()}


def _executer_outil_assistant(nom: str, arg: Dict[str, Any]) -> str:
    from api import assistant_converse as ac
    prenom = (_CTX.get() or {}).get("prenom")
    ac._CANAL.set("ivo")
    ac._PRENOM.set(prenom)
    res = ac._run_tool(nom, arg, prenom)
    from core import ivo_regles as _ir
    if isinstance(res, dict) and res.get("error") == _ir.MESSAGE_LECTURE_SEULE:
        (_CTX.get() or {}).setdefault("bloques", []).append(nom)
    return json.dumps(ac._vers_montreal(res), ensure_ascii=False, default=str)[:12000]


def _transmettre_a_claude(arg: Dict[str, Any]) -> str:
    """Relais Ivo → Claude : la demande est gardée ; une tâche planifiée Claude la reprend
    (en semaine, toutes les heures de 8 h à 18 h) et répond dans le même fil Front."""
    from core.supabase_storage import SupabaseStorage
    ctx = _CTX.get() or {}
    if not ctx.get("conversation_id"):
        return "Relais impossible : aucun fil Front associé à cette demande."
    st = SupabaseStorage(silent=True)
    ligne = {"conversation_id": ctx["conversation_id"], "qui": ctx.get("prenom") or "équipe",
             "demande": (arg.get("demande") or "")[:4000], "contexte": (arg.get("contexte") or "")[:4000]}
    r = requests.post(f"{st.api_url}/ivo_relais", headers={**st._get_headers(), "Prefer": "return=minimal"},
                      json=ligne, timeout=15)
    if r.status_code >= 400:
        _log.warning("Ivo : relais impossible : %s", r.text[:200])
        return "Le relais vers Claude a échoué : dis à l'équipe de demander directement à Allan."
    return ("Transmis à Claude. Il répondra dans ce fil, en général dans l'heure en semaine (8 h à 18 h). "
            "Dis-le à l'équipe dans ta note.")


def _apres_regle(conversation_id: Optional[str], regle: str) -> None:
    """Règle retenue après une leçon proposée par Ivo : le cas devient un cas de test de nuit."""
    try:
        from core import ivo_apprentissage
        ivo_apprentissage.regle_retenue(conversation_id, regle)
    except Exception:
        _log.exception("Ivo : cas de test appris non enregistré")


def _executer_outil(nom: str, arg: Dict[str, Any]) -> str:
    from core import ivo_regles as _ir
    if nom in _ir.ACTIONS_RESERVEES and not _ir.peut_agir((_CTX.get() or {}).get("prenom")):
        (_CTX.get() or {}).setdefault("bloques", []).append(nom)
        return _ir.MESSAGE_LECTURE_SEULE
    if _EVTS_TEST.get() is not None and nom != "consulter_horaire":
        return "Outil non disponible pendant un cas de test : réponds avec l'horaire (« consulter_horaire »)."
    try:
        if nom == "consulter_horaire":
            return _consulter_horaire(arg)
        if nom == "analyser_photos":
            photos = (_CTX.get() or {}).get("photos") or []
            if not photos:
                return "Aucune photo jointe par le client dans ce fil."
            def _front_telecharger(url):
                fc = get_front_client()
                r = fc._requete("GET", url, headers={"Authorization": fc._headers()["Authorization"]})
                r.raise_for_status()
                return r.content
            from core.analyse_photos_piano import analyser, resume
            images = []
            for x in photos:
                try:
                    images.append({"data": _front_telecharger(x["url"]), "mime": x.get("content_type")})
                except Exception as e:
                    _log.warning("Ivo : photo illisible %s : %s", x.get("filename"), e)
            if not images:
                return "Les photos n'ont pas pu être téléchargées de Front."
            return f"Analyse de {len(images)} photo(s) (interne, ne pas copier telle quelle au client) :\n" + \
                resume(analyser(images, arg.get("contexte")))
        if nom == "frais_deplacement":
            from modules.travel_fees.calculator import TravelFeeCalculator
            r = TravelFeeCalculator().calculer_frais_client(arg.get("adresse") or "")
            km_aller = r.distance_km / 2
            if r.is_free:
                return f"GRATUIT (environ {km_aller:.0f} km aller depuis le point de référence PTM)."
            texte = f"{r.total_fee:.2f} $ (environ {km_aller:.0f} km aller depuis le point de référence PTM)."
            if km_aller > TravelFeeCalculator.LIMITE_TARIF_GRADUEL_KM:
                texte += (" Au-delà de 45 km : montant ESTIMATIF, la coordonnatrice fixe le RV et les frais "
                          "(visites regroupées).")
            return texte
        if nom in ("retenir_regle", "oublier_regle"):
            from core import ivo_regles
            oubliee = None
            if nom == "oublier_regle":
                try:
                    oubliee = ivo_regles.lire()[int(arg.get("numero") or 0) - 1]["regle"]
                except Exception:
                    oubliee = None
            res_r = ivo_regles.executer(nom, arg, (_CTX.get() or {}).get("prenom"))
            if nom == "retenir_regle" and res_r.get("ok"):
                _apres_regle((_CTX.get() or {}).get("conversation_id"), arg.get("regle") or "")
            if nom == "oublier_regle" and res_r.get("ok") and oubliee:
                try:
                    from core import ivo_apprentissage
                    ivo_apprentissage.retirer_cas(oubliee)
                except Exception:
                    _log.exception("Ivo : cas appris non retiré")
            return res_r["message"]
        if nom == "demander_assistant":
            import asyncio
            from api.assistant_converse import converse, ConverseRequest, ConverseMessage
            ctx = _CTX.get() or {}
            hist = [ConverseMessage(role=r, content=c) for r, c in (ctx.get("historique") or [])][-8:]
            hist.append(ConverseMessage(role="user", content=arg.get("demande") or ""))
            rep = asyncio.run(converse(ConverseRequest(messages=hist, current_user_first_name=ctx.get("prenom"),
                                                       canal="ivo", contexte=ctx.get("fil"))))
            faits = [f"{a.get('type')}: {json.dumps(a.get('result'), ensure_ascii=False, default=str)[:600]}"
                     for a in (rep.get("actions") or [])]
            from core import ivo_regles as _ir2
            if any(((a.get("result") or {}).get("error") or "") == _ir2.MESSAGE_LECTURE_SEULE
                   for a in (rep.get("actions") or []) if isinstance(a.get("result"), dict)):
                ctx.setdefault("bloques", []).append("demander_assistant")
            return (rep.get("reply") or "") + ("\n\nActions : " + " | ".join(faits) if faits else "")
        if nom == "creer_client":
            from core.gazelle_api_client import GazelleAPIClient
            gz = GazelleAPIClient()
            existant = gz.trouver_client_existant(
                telephones=[arg["telephone"]] if arg.get("telephone") else None, courriel=arg.get("courriel"))
            if existant:
                return f"Fiche déjà existante ({existant}) : rien créé."
            cid = gz.create_client(arg.get("prenom"), arg.get("nom"), telephone=arg.get("telephone"),
                                   courriel=arg.get("courriel"),
                                   adresse={"rue": arg.get("rue"), "ville": arg.get("ville"),
                                            "code_postal": arg.get("code_postal")},
                                   statut="PROSPECT", reference="Fiche créée par Ivo à partir d'un courriel à info@")
            return f"Fiche client potentiel créée dans Gazelle : {cid}."
        if nom == "bloquer_technicien":
            from datetime import datetime, timezone
            from core.gazelle_api_client import GazelleAPIClient
            from core.timezone_utils import MONTREAL_TZ
            ids = {"Nicolas": "usr_HcCiFk7o0vZ9xAI0", "JP": "usr_ReUSmIJmBF86ilY1", "Margot": "usr_bbt59aCUqUaDWA8n"}
            uid = ids.get(arg.get("technicien") or "")
            if not uid:
                return "Technicien inconnu."
            local = datetime.fromisoformat(arg["debut"]).replace(tzinfo=MONTREAL_TZ)
            if local < datetime.now(MONTREAL_TZ):
                return "Date passée : rien bloqué."
            inp = {"title": f"RÉSERVÉ (à confirmer) — {arg.get('motif') or ''}".strip(" —"),
                   "start": local.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                   "duration": int(arg.get("duree_min") or 120), "type": "PERSONAL", "userId": uid,
                   "notes": "Bloc temporaire posé par Ivo à la demande de l'équipe. À convertir en RV ou à supprimer."}
            res = GazelleAPIClient()._execute_query(
                "mutation($input: PrivateEventInput!) { createEvent(input: $input) { event { id } "
                "mutationErrors { fieldName messages } } }", {"input": inp})
            p = ((res or {}).get("data") or {}).get("createEvent") or {}
            if not p.get("event"):
                return f"Gazelle a refusé le bloc : {p.get('mutationErrors') or res.get('errors')}"
            return f"Bloc posé à l'horaire de {arg['technicien']} le {local:%Y-%m-%d} à {local:%H:%M} ({inp['duration']} min)."
        if nom == "ajouter_piano":
            from api.taches_routes import ajouter_piano_client, PianoClientIn
            r = ajouter_piano_client(arg["client_id"], PianoClientIn(
                marque=arg["marque"], modele=arg.get("modele"), type_piano=arg.get("type_piano") or "UNKNOWN",
                numero_serie=arg.get("numero_serie"), notes=arg.get("notes")))
            pi = r.get("piano") or {}
            etat = "déjà dans la fiche" if r.get("deja") else "ajouté à la fiche"
            return f"Piano {etat} : {pi.get('make')} {pi.get('model') or ''} ({pi.get('type')}), id {pi.get('id')}."
        if nom == "dossier_front":
            return _dossier_front(arg)
        if nom == "lire_rv":
            return _lire_rv(arg)
        if nom == "changer_pianos_rv":
            from api.taches_routes import changer_pianos_rv, PianosRvIn
            r = changer_pianos_rv(arg["rv_id"], PianosRvIn(retirer=arg.get("retirer") or [], ajouter=arg.get("ajouter") or []))
            if not r.get("change"):
                return r["message"]
            return (f"Pianos du RV {arg['rv_id']} : avant {r['avant']}, maintenant {r['pianos']}."
                    + (" ⚠️ " + " ; ".join(r["avertissements"]) if r.get("avertissements") else ""))
        if nom == "transmettre_a_claude":
            return _transmettre_a_claude(arg)
        if nom == "creer_rendez_vous":
            return _creer_rv_direct(arg)
        if nom == "convertir_bloc_en_rv":
            from api.taches_routes import convertir_bloc_en_rv, ConversionBlocIn
            prenom = (_CTX.get() or {}).get("prenom") or "l'équipe"
            r = convertir_bloc_en_rv(arg["bloc_id"], ConversionBlocIn(
                client_id=arg["client_id"], piano_ids=arg.get("piano_ids") or [], notes=arg.get("notes"),
                par=f"Ivo (assistant IA) à la demande de {prenom}"))
            ev = r.get("rv") or {}
            return (f"RV créé ({ev.get('id')}) : {ev.get('title')}, à l'heure du bloc (fin {r.get('fin')}). "
                    + ("Bloc retiré." if r.get("bloc_supprime") else f"⚠️ {r.get('avertissement')}")
                    + " Aucune confirmation envoyée au client.")
        if nom == "creer_facture":
            return _creer_facture(arg)
        if nom == "chercher_client":
            from modules.assistant.services.queries import GazelleQueries
            from core.supabase_storage import SupabaseStorage
            res = GazelleQueries(SupabaseStorage(silent=True)).search_clients([arg.get("texte") or ""]) or []
            if not res:
                return "Aucun client trouvé."
            st = SupabaseStorage(silent=True)
            lignes = []
            for c in res[:5]:
                cid = c.get("external_id") or c.get("client_id") or c.get("client_external_id") or ""
                visites = "?"
                if cid.startswith("cli_"):
                    from core.timezone_utils import MONTREAL_TZ
                    from datetime import datetime
                    r = requests.get(f"{st.api_url}/gazelle_appointments?select=appointment_date"
                                     f"&client_external_id=eq.{cid}"
                                     f"&appointment_date=lt.{datetime.now(MONTREAL_TZ):%Y-%m-%d}"
                                     f"&order=appointment_date.desc&limit=20", headers=st._get_headers(), timeout=10)
                    if r.status_code == 200:
                        d = r.json()
                        visites = f"{len(d)} visite(s) passée(s)" + (f", la dernière le {d[0]['appointment_date']}" if d else "")
                nom_c = c.get('company_name') or f"{c.get('first_name') or ''} {c.get('last_name') or ''}".strip()
                adr = ', '.join(x for x in (c.get('address'), c.get('city'), c.get('postal_code')) if x) or 'adresse inconnue'
                pianos = "pianos : ?"
                if cid.startswith("cli_"):
                    try:
                        from core.gazelle_api_client import GazelleAPIClient
                        q = GazelleAPIClient()._execute_query(
                            "query($id: String!) { client(id: $id) { allPianos { nodes { id make model type status serialNumber location } } } }",
                            {"id": cid})
                        ns = [n for n in ((((q or {}).get("data") or {}).get("client") or {}).get("allPianos") or {}).get("nodes") or []
                              if n.get("status") != "INACTIVE"]
                        pianos = ("pianos : " + "; ".join(f"{n.get('make')} {n.get('model') or ''} {n.get('type')}"
                                                         + (f" n° {n['serialNumber']}" if n.get('serialNumber') else "")
                                                         + (f" [{n['location']}]" if n.get('location') else "")
                                                         + f" ({n['id']})"
                                                         for n in ns)) if ns else "AUCUN piano dans la fiche"
                    except Exception:
                        pass
                lignes.append(f"{nom_c} ({cid or 'id ?'}) — {adr} — {pianos} — {visites}"
                              + (_factures_resume(cid) if cid.startswith("cli_") else ""))
            return "\n".join(lignes)
        if nom in _noms_outils_assistant():
            return _executer_outil_assistant(nom, arg)
        return "Outil inconnu."
    except Exception as e:
        _log.exception("Ivo : outil %s", nom)
        return f"Échec de l'outil : {e}"


def _rediger(consigne: str, fil: str, brouillon: str, regles: List[str], echanges: str = "") -> Dict[str, Any]:
    from anthropic import Anthropic
    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    systeme = _SYSTEME
    from core import ivo_regles
    if ivo_regles.cahier_pour_ia():
        systeme += "\n\n" + ivo_regles.cahier_pour_ia()
    if ivo_regles.texte_pour_ia():
        systeme += "\n\n" + ivo_regles.texte_pour_ia()
    ton = _guide_ton()
    if ton:
        systeme += "\n\nGuide de ton de PTM (extrait) :\n" + ton
    from core.timezone_utils import MONTREAL_TZ
    from datetime import datetime
    try:
        tarifs = _tarifs()
    except Exception:
        _log.exception("Ivo : tarifs indisponibles")
        tarifs = ""
    contenu = (f"AUJOURD'HUI : {datetime.now(MONTREAL_TZ):%Y-%m-%d %A}\n\n"
               + (f"GRILLE DES TARIFS DE PTM (liste des services de Gazelle, avant taxes) :\n{tarifs}\n\n" if tarifs
                  else "GRILLE DES TARIFS : indisponible — mets [prix à confirmer] plutôt que de deviner.\n\n")
               + "HORAIRE DE L'ÉQUIPE : consulte-le avec l'outil « consulter_horaire » (Gazelle en direct).\n\n"
               f"FIL DE LA CONVERSATION (du plus ancien au plus récent) :\n{fil}\n\n"
               f"BROUILLON ACTUEL :\n{brouillon or '(aucun — rédige une première réponse)'}\n\n"
               + (f"ÉCHANGES PRÉCÉDENTS AVEC IVO DANS CE FIL (pour comprendre « oui », « vas-y », etc.) :\n{echanges}\n\n"
                  if echanges else "")
               + f"CONSIGNE DE L'ÉQUIPE :\n{consigne}")
    outils = [
        {"name": "repondre", "description": "Transmet le résultat final d'Ivo (à appeler en dernier).",
         "input_schema": {"type": "object", "required": ["action", "note"], "properties": {
             "action": {"type": "string", "enum": ["brouillon", "reponse"]},
             "brouillon": {"type": ["string", "null"]},
             "regle_generale": {"type": ["string", "null"]},
             "note": {"type": "string"}}}},
        {"name": "analyser_photos",
         "description": ("Regarde les photos de piano jointes par le client dans ce fil (vision) et en tire marque, modèle, "
                         "type, époque, état, problèmes, alertes (ex. drop-action), photos à demander. À utiliser dès que "
                         "le fil indique des photos jointes, avant de répondre ou de rédiger."),
         "input_schema": {"type": "object", "properties": {
             "contexte": {"type": ["string", "null"], "description": "Ce que le client dit de son piano (héritage, achat, etc.)"}}}},
        {"name": "consulter_horaire",
         "description": ("Horaire de l'équipe EN DIRECT dans Gazelle pour une période : chaque RV avec ville et code "
                         "postal, les RV déjà prévus dans un secteur (pour jumeler) et les plages libres de chaque "
                         "technicien. À appeler avant toute réponse sur des disponibilités, un secteur ou un jumelage."),
         "input_schema": {"type": "object", "required": ["debut"], "properties": {
             "debut": {"type": "string", "description": "AAAA-MM-JJ"},
             "fin": {"type": ["string", "null"], "description": "AAAA-MM-JJ (31 jours au plus)"},
             "techniciens": {"type": ["array", "null"], "items": {"type": "string", "enum": ["Nicolas", "JP", "Margot", "Allan"]},
                             "description": "Par défaut Nicolas, JP et Margot."},
             "secteur": {"type": ["array", "null"], "items": {"type": "string"},
                         "description": "Villes, quartiers ou débuts de code postal du secteur, ex. [\"Lorraine\", \"J6Z\", \"Rosemère\", \"Blainville\"]"},
             "heure_debut": {"type": ["string", "null"], "description": "HH:MM, début de la plage du client (défaut 08:00)"},
             "heure_fin": {"type": ["string", "null"], "description": "HH:MM, fin de la plage du client (défaut 18:00)"}}}},
        {"name": "frais_deplacement",
         "description": "Calculateur officiel des frais de déplacement PTM pour une adresse ou un code postal client.",
         "input_schema": {"type": "object", "required": ["adresse"],
                          "properties": {"adresse": {"type": "string"}}}},
        *__import__("core.ivo_regles", fromlist=["OUTILS"]).OUTILS,
        {"name": "demander_assistant",
         "description": ("SECOURS SEULEMENT, si aucun de tes autres outils ne convient. Transmet une demande à l'assistant (la même case que dans Ma Journée) : "
                         "créer un RV (aperçu d'abord, puis création après un oui), RV conjoint, réactiver ou réviser "
                         "une soumission, chercher dans les notes, appels récents, lien de réservation prérempli, "
                         "photos d'un courriel → dossier du piano, frais partagés, etc. Écris la demande complète "
                         "avec le nom du client. Pour une confirmation (« oui »), redis l'action confirmée."),
         "input_schema": {"type": "object", "required": ["demande"],
                          "properties": {"demande": {"type": "string"}}}},
        *_outils_assistant(),
        {"name": "transmettre_a_claude",
         "description": ("Transmet la demande à Claude (accès complet : code de l'assistant, API, Gazelle, Front, "
                         "QuickBooks) quand TES outils ne permettent pas de la faire ou d'y répondre avec certitude. "
                         "Claude répond dans ce même fil. Écris la demande complète et ce que tu as déjà essayé."),
         "input_schema": {"type": "object", "required": ["demande"], "properties": {
             "demande": {"type": "string", "description": "Ce que l'équipe veut, en clair, avec le client, le RV, la date."},
             "contexte": {"type": ["string", "null"], "description": "Ce que tu as déjà vérifié ou essayé, et pourquoi tu bloques."}}}},
        {"name": "lire_rv",
         "description": ("LECTURE SEULE : ouvre un RV Gazelle (evt_…) tel qu'il est maintenant : date, heure, durée, "
                         "statut, technicien en clair, pianos (marque, modèle, n° de série), notes, et les demandes "
                         "Place des Arts qui y sont liées (avec le technicien noté dans l'assistant). À utiliser pour "
                         "toute question sur un RV précis ou une alerte du vérificateur quotidien."),
         "input_schema": {"type": "object", "required": ["rv_id"],
                          "properties": {"rv_id": {"type": "string"}}}},
        {"name": "changer_pianos_rv",
         "description": ("Change le ou les pianos d'un RV Gazelle EXISTANT (evt_…), ex. remplacer le Steinway B par le "
                         "Steinway D. Ne touche à rien d'autre (heure, technicien, notes) et n'écrit pas au client. "
                         "Trouve d'abord les ins_… avec « lire_rv » (pianos du RV) et « chercher_client » (pianos du client). "
                         "Seulement sur ordre explicite de l'équipe ; pour plusieurs RV, un appel par RV, puis rapporte RV par RV."),
         "input_schema": {"type": "object", "required": ["rv_id"], "properties": {
             "rv_id": {"type": "string"},
             "retirer": {"type": "array", "items": {"type": "string"}, "description": "ins_… à enlever du RV"},
             "ajouter": {"type": "array", "items": {"type": "string"}, "description": "ins_… à mettre sur le RV"}}}},
        {"name": "creer_client",
         "description": "Crée une fiche client potentiel dans Gazelle (refuse si une fiche existe déjà avec ce courriel ou ce téléphone).",
         "input_schema": {"type": "object", "required": ["prenom", "nom"], "properties": {
             "prenom": {"type": "string"}, "nom": {"type": "string"},
             "courriel": {"type": ["string", "null"]}, "telephone": {"type": ["string", "null"]},
             "rue": {"type": ["string", "null"]}, "ville": {"type": ["string", "null"]},
             "code_postal": {"type": ["string", "null"]},
             "langue": {"type": "string", "enum": ["fr", "en"]}}}},
        {"name": "bloquer_technicien",
         "description": "Pose un bloc personnel temporaire « RÉSERVÉ (à confirmer) » à l'horaire Gazelle d'un technicien.",
         "input_schema": {"type": "object", "required": ["technicien", "debut", "duree_min", "motif"], "properties": {
             "technicien": {"type": "string", "enum": ["Nicolas", "JP", "Margot"]},
             "debut": {"type": "string", "description": "AAAA-MM-JJTHH:MM, heure de Montréal"},
             "duree_min": {"type": "integer"},
             "motif": {"type": "string", "description": "ex. « Yves-Jerry Loiseau, Mascouche »"}}}},
        {"name": "dossier_front",
         "description": ("Cherche dans TOUT Front les autres fils du même client (messages vocaux, textos, résumés "
                         "d'appel Zoom, autres courriels, commentaires internes) par téléphone, courriel ou nom, et "
                         "retourne leur contenu. À utiliser AVANT de dire qu'une information manque."),
         "input_schema": {"type": "object", "properties": {
             "telephones": {"type": "array", "items": {"type": "string"}},
             "courriel": {"type": ["string", "null"]}, "nom": {"type": ["string", "null"]}}}},
        {"name": "creer_rendez_vous",
         "description": ("Crée DIRECTEMENT un RV client dans Gazelle (sans confirmation au client). Seulement sur un "
                         "ordre explicite de l'équipe (« crée le RV », « oui ») quand client, technicien, jour, heure "
                         "et durée sont connus. Refuse s'il y a un conflit à l'horaire."),
         "input_schema": {"type": "object", "required": ["client_id", "technicien", "debut", "duree_min", "notes"],
                          "properties": {
             "client_id": {"type": "string"},
             "technicien": {"type": "string", "enum": ["Nicolas", "JP", "Margot"]},
             "debut": {"type": "string", "description": "AAAA-MM-JJTHH:MM, heure de Montréal"},
             "duree_min": {"type": "integer"},
             "notes": {"type": "string", "description": "Notes pour le technicien : service, prix connu, qui facturer, adresse, contacts, points à vérifier."},
             "piano_ids": {"type": "array", "items": {"type": "string"}},
             "lieu": {"type": ["string", "null"], "description": "Adresse si différente de la fiche ou absente de la fiche."}}}},
        {"name": "convertir_bloc_en_rv",
         "description": ("Transforme un bloc PERSONNEL déjà à l'horaire d'un technicien (ex. « accorder fazioli à la maison "
                         "trestler ») en vrai RV client, à la même heure et pour la même durée, avec le piano. Le bloc est "
                         "retiré une fois le RV créé. Aucun courriel au client. Seulement sur ordre explicite de l'équipe, "
                         "et seulement si le bloc vise ce client (trouve son evt_… avec « consulter_horaire »)."),
         "input_schema": {"type": "object", "required": ["bloc_id", "client_id", "notes"], "properties": {
             "bloc_id": {"type": "string"}, "client_id": {"type": "string"},
             "piano_ids": {"type": "array", "items": {"type": "string"}},
             "notes": {"type": "string", "description": "Notes pour le technicien : service, prix convenu, qui facturer, contacts."}}}},
        {"name": "creer_facture",
         "description": ("Crée une facture Gazelle en BROUILLON (TPS/TVQ cochées, rien envoyé au client), avec au besoin une "
                         "FACTURATION ALTERNATIVE (facturer une autre fiche que le client du piano, ex. le propriétaire, un "
                         "marchand) et le technicien assigné. Si un RV est donné, écrit « Facture créée (n° …) » en tête "
                         "de ses notes. Le montant doit venir du fil (prix convenu avec le client) ou de la grille des tarifs, "
                         "jamais deviné. Sur ordre explicite de l'équipe seulement."),
         "input_schema": {"type": "object", "required": ["client_id", "lignes"], "properties": {
             "client_id": {"type": "string", "description": "Client du service (fiche du piano)."},
             "lignes": {"type": "array", "items": {"type": "object", "required": ["description", "montant"], "properties": {
                 "description": {"type": "string"}, "montant": {"type": "number", "description": "dollars avant taxes"},
                 "service_id": {"type": ["string", "null"], "description": "mit_… de la grille, si applicable"},
                 "piano_id": {"type": ["string", "null"]}}}},
             "facturer_a_client_id": {"type": ["string", "null"], "description": "cli_… de la fiche à facturer (facturation alternative)."},
             "technicien": {"type": ["string", "null"], "enum": ["Nicolas", "JP", "Margot", None]},
             "rv_id": {"type": ["string", "null"], "description": "evt_… où écrire « Facture créée »."}}}},
        {"name": "ajouter_piano",
         "description": ("Ajoute à la fiche Gazelle d'un client le piano qu'il a décrit (refuse s'il a déjà un piano actif "
                         "de la même marque, et retourne alors celui-là). Retourne l'id du piano pour piano_ids."),
         "input_schema": {"type": "object", "required": ["client_id", "marque", "type_piano"], "properties": {
             "client_id": {"type": "string"}, "marque": {"type": "string"},
             "modele": {"type": ["string", "null"]},
             "type_piano": {"type": "string", "enum": ["UPRIGHT", "GRAND", "DIGITAL", "UNKNOWN"]},
             "numero_serie": {"type": ["string", "null"]},
             "notes": {"type": ["string", "null"], "description": "Ex. année d'achat, problème décrit par le client."}}}},
        {"name": "chercher_client",
         "description": "Cherche un client dans Gazelle par courriel, nom ou téléphone ; retourne nom, ville, code postal, pianos de la fiche et nombre de visites passées.",
         "input_schema": {"type": "object", "required": ["texte"],
                          "properties": {"texte": {"type": "string"}}}},
    ]
    messages = [{"role": "user", "content": contenu}]
    for _ in range(8):
        if not ivo_regles.peut_agir((_CTX.get() or {}).get("prenom")):
            outils = [o for o in outils if o["name"] not in ivo_regles.ACTIONS_RESERVEES]
            if "LECTURE SEULE" not in systeme:
                systeme += ("\n\nLECTURE SEULE : la personne qui t'écrit peut te poser des questions et te faire "
                            "préparer un brouillon, mais tu ne crées, ne modifies ni ne confirmes rien dans Gazelle "
                            "(pas de RV, de fiche, de bloc ni de règle). Si on te demande une telle action, prépare-la "
                            "quand même en détail (client, technicien, date, heure, durée, piano) et décris-la dans ta note, "
                            "car Louise pourra l'autoriser dans ce fil ; dis : " + ivo_regles.MESSAGE_LECTURE_SEULE)
        rep = client.messages.create(model=MODELE, max_tokens=4000, system=systeme, tools=outils,
                                     tool_choice={"type": "auto"}, messages=messages)
        appels = [b for b in rep.content if getattr(b, "type", "") == "tool_use"]
        final = next((b for b in appels if b.name == "repondre"), None)
        if final:
            return dict(final.input)
        if not appels:
            brut = "".join(getattr(b, "text", "") for b in rep.content).strip()
            m = re.search(r"\{.*\}", brut, re.DOTALL)
            if m:
                return json.loads(m.group(0))
            break
        messages.append({"role": "assistant", "content": rep.content})
        messages.append({"role": "user", "content": [
            {"type": "tool_result", "tool_use_id": b.id, "content": _executer_outil(b.name, dict(b.input))}
            for b in appels]})
    raise ValueError("réponse de l'IA illisible")


# ─── Traitement ──────────────────────────────────────────────────

def _fil(messages: List[Dict]) -> str:
    lignes = []
    for m in sorted([m for m in messages if not m.get("is_draft")], key=lambda m: m.get("created_at") or 0):
        qui = "CLIENT" if m.get("is_inbound") else "PTM"
        auteur = ((m.get("author") or {}).get("email")) or next(
            (r.get("handle") for r in (m.get("recipients") or []) if r.get("role") == "from"), "")
        imgs = [x.get("filename") or "photo" for x in (m.get("attachments") or [])
                if _est_photo(x)]
        pj = f"\n[{len(imgs)} photo(s) jointe(s) : {', '.join(imgs[:8])} — outil analyser_photos]" if imgs else ""
        dest = ", ".join(f"{r.get('name') or ''} <{r.get('handle')}>".strip()
                         for r in (m.get("recipients") or []) if r.get("role") in ("to", "cc") and r.get("handle"))
        dest = f" → à : {dest}" if dest else ""
        lignes.append(f"--- {qui} {auteur}{dest} ---\n{_texte(m.get('text') or m.get('body') or '')[:4000]}{pj}")
    # Le premier message du client (marque, modèle, adresse, demande) est toujours gardé
    if len(lignes) > 12:
        lignes = [lignes[0], "[… messages intermédiaires omis …]"] + lignes[-11:]
    return "\n\n".join(lignes)


def traiter(conversation_id: str, comment_id: Optional[str]) -> Dict[str, Any]:
    front = get_front_client()
    commentaires = front.list_comments(conversation_id)
    # Le commentaire visé, relu dans Front (jamais celui du webhook)
    if comment_id:
        cibles = [c for c in commentaires if c.get("id") == comment_id]
    else:
        cibles = sorted([c for c in commentaires if consigne_ivo(c.get("body") or "") is not None],
                        key=lambda c: c.get("posted_at") or 0)[-1:]
    if not cibles:
        return {"statut": "ignoré", "raison": "commentaire introuvable"}
    com = cibles[0]
    consigne = consigne_ivo(com.get("body") or "")
    if consigne is None:
        return {"statut": "ignoré", "raison": "pas un commentaire @Ivo"}
    auteur_email = ((com.get("author") or {}).get("email") or "").lower()
    if not auteur_email:
        return {"statut": "ignoré", "raison": "auteur inconnu"}

    with _verrou:
        if com["id"] in _deja_traites:
            return {"statut": "ignoré", "raison": "déjà traité"}
        _deja_traites.add(com["id"])
    # Déjà répondu (après un redémarrage) : un commentaire Ivo plus récent existe
    if any(_texte(c.get("body") or "").startswith("🤖 Ivo")
           and "pas réussi" not in _texte(c.get("body") or "")
           and (c.get("posted_at") or 0) > (com.get("posted_at") or 0) for c in commentaires):
        return {"statut": "ignoré", "raison": "déjà traité"}

    messages = front.list_messages(conversation_id)
    brouillons = sorted([m for m in messages if m.get("is_draft")], key=lambda m: m.get("created_at") or 0)
    brouillon = brouillons[-1] if brouillons else None
    texte_brouillon = _texte((brouillon or {}).get("text") or (brouillon or {}).get("body") or "")

    try:
        fil = _fil(messages)
        anterieurs = sorted([c for c in commentaires if (c.get("posted_at") or 0) < (com.get("posted_at") or 0)],
                            key=lambda c: c.get("posted_at") or 0)
        historique = []
        for c in anterieurs[-10:]:
            t = _texte(c.get("body") or "")
            if t.startswith("🤖 Ivo"):
                historique.append(("assistant", t))
            elif consigne_ivo(c.get("body") or "") is not None:
                historique.append(("user", consigne_ivo(c.get("body") or "")))
        # Notes internes de l'équipe (commentaires Front qui ne s'adressent pas à Ivo) : Ivo doit les voir
        notes = []
        for c in anterieurs[-15:]:
            t = _texte(c.get("body") or "")
            if t.startswith("🤖 Ivo") or consigne_ivo(c.get("body") or "") is not None or not t.strip():
                continue
            qui_c = ((c.get("author") or {}).get("first_name")) or ((c.get("author") or {}).get("email")) or "équipe"
            notes.append(f"- {qui_c} : {t[:800]}")
        if notes:
            fil = (fil + "\n\n--- NOTES INTERNES DE L'ÉQUIPE (commentaires Front, non vus du client) ---\n"
                   + "\n".join(notes))
        while historique and historique[0][0] != "user":
            historique.pop(0)
        photos = []
        for m in sorted([m for m in messages if m.get("is_inbound")], key=lambda m: m.get("created_at") or 0, reverse=True):
            for x in (m.get("attachments") or []):
                if _est_photo(x):
                    photos.append(x)
        _CTX.set({"photos": photos[:8], "historique": historique, "fil": fil, "prenom": _PRENOMS.get(auteur_email), "bloques": [], "conversation_id": conversation_id})
        echanges = "\n".join(f"{'Équipe' if r == 'user' else 'Ivo'} : {t[:600]}" for r, t in historique)
        res = _rediger(consigne, fil, texte_brouillon, _regles(), echanges)
        if res.get("action") == "reponse":
            note = re.sub(r"^\s*(🤖\s*)?(Ivo\s*:\s*)?(🤖\s*)?", "", res.get("note") or "") or "je n'ai pas de réponse."
            front.add_comment(conversation_id, PREFIXE_REPONSE + note,
                              auteur_email)
            _transmettre_a_louise(front, conversation_id, auteur_email, consigne)
            return {"statut": "ok", "action": "réponse"}
        nouveau = (res.get("brouillon") or "").strip()
        if not nouveau:
            raise ValueError("brouillon vide")
    except Exception as e:
        _log.exception("Ivo : rédaction impossible")
        front.add_comment(conversation_id, f"{PREFIXE_REPONSE}je n'ai pas réussi à refaire le brouillon ({e}). "
                                           "Réessayez avec un nouveau commentaire @Ivo.", auteur_email)
        return {"statut": "erreur", "raison": str(e)}

    corps = _en_html(nouveau)
    canal = front._channel_de_conversation(conversation_id)
    if brouillon:
        front.edit_draft(brouillon["id"], brouillon.get("version"), corps, canal)
        action = "brouillon mis à jour"
    else:
        front.create_draft_reply(conversation_id, corps, auteur_email, mode="shared")
        action = "brouillon créé"
    try:
        from core import ivo_apprentissage
        ivo_apprentissage.memoriser_brouillon(conversation_id, nouveau, auteur_email, fil)
    except Exception:
        _log.exception("Ivo : brouillon non mémorisé pour l'apprentissage")

    reponse = f"{PREFIXE_REPONSE}{action}."
    if res.get("note"):
        reponse += f" {res['note']}"
    regle = (res.get("regle_generale") or "").strip()
    if regle:
        from core import ivo_regles
        res_regle = ivo_regles.ajouter(regle, _PRENOMS.get(auteur_email))
        reponse += " " + res_regle["message"]
        if res_regle.get("ok"):
            _apres_regle(conversation_id, regle)
    front.add_comment(conversation_id, reponse, auteur_email)
    _transmettre_a_louise(front, conversation_id, auteur_email, consigne)
    return {"statut": "ok", "action": action, "regle": regle or None}


def _transmettre_a_louise(front, conversation_id: str, auteur_email: str, consigne: str) -> None:
    """Une action refusée faute d'autorisation (ex. demandée par Margot) est transmise à Louise :
    elle est abonnée au fil (donc notifiée) et peut l'autoriser par « @Ivo oui » ; Ivo reprend
    alors la demande grâce à l'historique du fil, au nom de Louise."""
    from core import ivo_regles
    if not (_CTX.get() or {}).get("bloques"):
        return
    qui = _PRENOMS.get(auteur_email) or auteur_email
    try:
        front.ajouter_abonnes(conversation_id, [ivo_regles.APPROBATRICE])
    except Exception:
        _log.exception("Ivo : abonnement de Louise impossible")
    front.add_comment(conversation_id,
                      f"{PREFIXE_REPONSE}@louise, {qui} demande une action qui exige ton accord : « {consigne[:500]} ». "
                      "Pour l'autoriser, réponds dans ce fil « @Ivo oui, vas-y » (tu peux préciser ou corriger). "
                      "Sinon, ignore ce message : rien n'a été fait.", auteur_email)


def _ids_du_webhook(evt: Dict[str, Any]) -> Dict[str, Optional[str]]:
    """Accepte les formes d'événement Front (règle « envoyer au webhook », application)."""
    p = evt.get("payload") if isinstance(evt.get("payload"), dict) else evt
    conv = p.get("conversation") or {}
    cible = (p.get("target") or {}).get("data") or {}
    cid = conv.get("id") or p.get("conversation_id")
    if not cid:
        lien = ((cible.get("_links") or {}).get("related") or {}).get("conversation") or ""
        cid = lien.rstrip("/").rsplit("/", 1)[-1] or None
    com = cible.get("id") if str(cible.get("id", "")).startswith("com_") else p.get("comment_id")
    return {"conversation_id": cid, "comment_id": com}


_derniers: List[Dict[str, Any]] = []  # journal court des derniers traitements (diagnostic)


def _traiter_sans_erreur(conversation_id: str, comment_id: Optional[str]) -> None:
    import traceback
    try:
        res = traiter(conversation_id, comment_id)
    except Exception as e:
        _log.exception("Ivo : échec du traitement")
        res = {"statut": "exception", "raison": f"{e}", "trace": traceback.format_exc()[-800:]}
    _derniers.append({"conversation": conversation_id, **res})
    del _derniers[:-10]


# ─── Surveillance (la règle « webhook » de Front exige un forfait supérieur) ───
_curseur: Dict[str, float] = {}


def surveiller(fenetre_s: int = 600) -> Dict[str, Any]:
    """Lit les nouveaux commentaires Front (événements) et traite ceux qui commencent par @Ivo.

    Appelé toutes les 30 s par le scheduler. Les doublons sont écartés par traiter().
    """
    import time
    front = get_front_client()
    depuis = _curseur.get("t") or (time.time() - fenetre_s)
    rep = requests.get(f"{front.BASE_URL}/events", headers=front._headers(), timeout=15,
                       params={"q[types]": "comment", "q[after]": int(depuis), "limit": 15})
    if rep.status_code >= 400:
        raise RuntimeError(f"Front {rep.status_code}: {rep.text[:300]}")
    r = rep.json()
    evenements = r.get("_results", [])
    vus = 0
    plus_recent = depuis
    for e in evenements:
        plus_recent = max(plus_recent, float(e.get("emitted_at") or 0))
        cible = ((e.get("target") or {}).get("data")) or {}
        if consigne_ivo(cible.get("body") or "") is None:
            continue
        conv = (e.get("conversation") or {}).get("id")
        if conv:
            vus += 1
            _traiter_sans_erreur(conv, cible.get("id"))
    _curseur["t"] = plus_recent
    envois, erreur_envois = 0, None
    try:
        envois = _surveiller_envois(front, fenetre_s)
    except Exception as e:
        _log.exception("Ivo : surveillance des envois impossible")
        erreur_envois = str(e)[:300]
    return {"evenements": len(evenements), "ivo": vus, "envois_compares": envois, "erreur_envois": erreur_envois}


def _sans_citation(corps_html: str) -> str:
    """Corps d'un courriel envoyé, sans le texte cité des messages précédents."""
    t = re.split(r"<blockquote|<div class=\"gmail_quote|<div class=\"front-blockquote", corps_html or "",
                 maxsplit=1, flags=re.IGNORECASE)[0]
    t = _texte(t)
    return re.split(r"\n\s*(Le .{5,120} a écrit\s*:|On .{5,120} wrote\s*:|-{2,}\s*Original Message)", t,
                    maxsplit=1)[0].strip()


def _surveiller_envois(front, fenetre_s: int) -> int:
    """Réponses envoyées par l'équipe : comparées au dernier brouillon d'Ivo du même fil (apprentissage).
    Les comparaisons se font dans un fil à part pour ne pas retarder les @Ivo."""
    import time
    depuis = _curseur.get("envois") or (time.time() - fenetre_s)
    plus_recent, a_comparer = depuis, []
    for type_evt in ("out_reply", "outbound"):
        rep = requests.get(f"{front.BASE_URL}/events", headers=front._headers(), timeout=15,
                           params={"q[types]": type_evt, "q[after]": int(depuis), "limit": 15})
        if rep.status_code >= 400:
            raise RuntimeError(f"Front {rep.status_code}: {rep.text[:300]}")
        for e in rep.json().get("_results", []):
            plus_recent = max(plus_recent, float(e.get("emitted_at") or 0))
            msg = ((e.get("target") or {}).get("data")) or {}
            conv = (e.get("conversation") or {}).get("id")
            if not conv or msg.get("is_draft"):
                continue
            with _verrou:
                cle = "envoi:" + str(msg.get("id") or e.get("id"))
                if cle in _deja_traites:
                    continue
                _deja_traites.add(cle)
            a_comparer.append((conv, _sans_citation(msg.get("body") or msg.get("text") or "")))
    _curseur["envois"] = plus_recent
    if a_comparer:
        def _comparer_tout(lot):
            from core import ivo_apprentissage
            for conv, texte in lot:
                try:
                    _derniers_envois.append({"conversation": conv, **ivo_apprentissage.traiter_envoi(conv, texte)})
                    del _derniers_envois[:-20]
                except Exception:
                    _log.exception("Ivo : comparaison brouillon/envoi impossible")
        threading.Thread(target=_comparer_tout, args=(a_comparer,), daemon=True).start()
    return len(a_comparer)


_derniers_envois: List[Dict[str, Any]] = []


# ─── Endpoints ───────────────────────────────────────────────────

@router.post("/webhook")
async def webhook(request: Request, background_tasks: BackgroundTasks):
    """Reçoit l'événement Front et répond tout de suite ; le travail se fait en arrière-plan."""
    try:
        evt = await request.json()
    except Exception:
        return {"ok": True, "ignoré": "corps illisible"}
    ids = _ids_du_webhook(evt if isinstance(evt, dict) else {})
    if not ids["conversation_id"] or not str(ids["conversation_id"]).startswith("cnv_"):
        return {"ok": True, "ignoré": "conversation absente"}
    background_tasks.add_task(_traiter_sans_erreur, ids["conversation_id"], ids["comment_id"])
    return {"ok": True}


@router.get("/sante")
def sante():
    return {"ok": True, "version": VERSION, "modele": MODELE,
            "cle_ia": bool(os.getenv("ANTHROPIC_API_KEY")), "cle_front": bool(os.getenv("FRONT_API_KEY")),
            "cahier": bool(__import__("core.ivo_regles", fromlist=["x"]).cahier_pour_ia())}


@router.post("/surveiller")
def surveiller_maintenant():
    """Lance une surveillance tout de suite (diagnostic)."""
    try:
        return surveiller()
    except Exception as e:
        return {"erreur": str(e)[:500]}


@router.get("/journal")
def journal():
    """Les derniers traitements d'Ivo (diagnostic, sans contenu de courriel)."""
    return {"derniers": _derniers, "envois": [{k: v for k, v in x.items() if k != "regle"} for x in _derniers_envois]}


_tests_en_cours = {"depuis": 0.0}


@router.post("/tests")
def lancer_tests(background_tasks: BackgroundTasks):
    """Rejoue les cas de test d'Ivo (horaire figé) ; résultats via GET /tests dans quelques minutes."""
    import time
    if time.time() - _tests_en_cours["depuis"] < 600:
        return {"lance": False, "message": "Des cas de test ont été lancés il y a moins de 10 minutes."}
    _tests_en_cours["depuis"] = time.time()
    from core import ivo_cas_tests
    background_tasks.add_task(ivo_cas_tests.executer, False)
    return {"lance": True, "message": "Cas de test lancés ; lire GET /api/front/ivo/tests dans 3 à 5 minutes."}


@router.get("/tests")
def resultats_tests():
    """Résultats des derniers cas de test d'Ivo."""
    from core import ivo_cas_tests
    return ivo_cas_tests.derniers_resultats()


@router.get("/horaire")
def horaire(jours: int = 30):
    """Ce qu'Ivo voit de l'horaire (diagnostic, lecture seule)."""
    return {"horaire": _horaire(min(max(jours, 1), 60)).split("\n")}


@router.get("/relais")
def relais(statut: str = "ouvert"):
    """Demandes transmises par Ivo à Claude (lues par la tâche planifiée)."""
    from core.supabase_storage import SupabaseStorage
    st = SupabaseStorage(silent=True)
    r = requests.get(f"{st.api_url}/ivo_relais?select=*&statut=eq.{statut}&order=cree_le.asc",
                     headers=st._get_headers(), timeout=15)
    return {"relais": r.json() if r.status_code == 200 else [], "erreur": None if r.status_code == 200 else r.text[:200]}


class RelaisFait(__import__("pydantic").BaseModel):
    reponse: str


@router.post("/relais/{rid}/traite")
def relais_traite(rid: str, f: RelaisFait):
    from datetime import datetime, timezone
    from core.supabase_storage import SupabaseStorage
    st = SupabaseStorage(silent=True)
    r = requests.patch(f"{st.api_url}/ivo_relais?id=eq.{rid}", headers={**st._get_headers(), "Prefer": "return=minimal"},
                       json={"statut": "traite", "reponse": f.reponse[:8000], "traite_le": datetime.now(timezone.utc).isoformat()},
                       timeout=15)
    return {"ok": r.status_code < 400}


@router.get("/regles")
def regles():
    """Règles de réponse retenues par Ivo au fil des consignes."""
    return {"regles": _regles()}
