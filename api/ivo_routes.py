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

VERSION = "ivo-17"
MODELE = os.getenv("IVO_MODELE", "claude-sonnet-5-5")
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


def _guide_ton() -> str:
    chemin = os.path.join(os.path.dirname(__file__), "..", "workspace", "guide-ton-ptm.md")
    try:
        with open(chemin, encoding="utf-8") as f:
            return f.read()[:6000]
    except OSError:
        return ""


# ─── Rédaction (Claude) ──────────────────────────────────────────

_SYSTEME = """Tu es Ivo, l'assistant de Piano Technique Montréal (PTM), entreprise d'accord et d'entretien de pianos.
Un membre de l'équipe te donne une consigne pour le brouillon de réponse à un client, ou te demande quelque chose.
RÈGLE N° 1 : tu ne réponds JAMAIS « je ne peux pas » ou « je n'ai pas accès » sans avoir d'abord essayé l'outil « demander_assistant ». C'est ton accès à tout l'assistant Gazelle de PTM (notes et historique des RV, soumissions, appels, création de RV, liens de réservation, photos, frais partagés…). Toute demande qui n'est pas une réécriture du brouillon passe par lui, sauf si tes autres outils y répondent directement.
Règles absolues :
- N'invente JAMAIS un prix, des frais, une date, une disponibilité ou une règle qui n'est pas dans le fil ou dans les règles fournies. Si une information manque, garde-la entre crochets, ex. [prix à confirmer].
- Réponds dans la langue du client. Vouvoiement par défaut.
- Pas de signature dans le corps (Front l'ajoute) : termine par la formule de politesse seulement.
- Tu ne fais que préparer un brouillon : un humain le relira et l'enverra.
Deux sortes de consignes :
A) Une correction du brouillon (« plus court », « propose la réservation en ligne »…) → action "brouillon".
B) Une question pour l'équipe (« qui est dans le coin à ces dates ? », « ça fonctionne avec l'horaire ? »…) → action "reponse" : réponds dans "note", sans toucher au brouillon.
Pour l'horaire, sers-toi UNIQUEMENT de l'HORAIRE DE L'ÉQUIPE fourni (RV clients avec leur ville et code postal ; « occupé » = bloc personnel). Raisonne sur la géographie (villes voisines, temps de route approximatif), propose concrètement qui, quel jour et à quelle heure, et dis clairement quand c'est serré ou incertain. Allan ne fait plus de visites : propose Nicolas, JP (Jean-Philippe) ou Margot. Ne mentionne jamais la nature d'un bloc personnel.
Historique du client : ta réponse dépend de son dossier. Client existant avec visites → reprends ce qui a été fait (ex. accord + entretien Piano Life Saver), le technicien habituel, et les frais de déplacement DÉJÀ FACTURÉS la dernière fois. Si le calculateur donne un montant différent de ce qui a été facturé, signale l'écart à l'équipe dans ta note et ne mets dans le brouillon que le montant que l'équipe confirme ([frais à confirmer] sinon). Nouveau client → calculateur officiel.
Provenance : lis tout le dossier avant de dire qu'on ignore comment le client nous a connus — un « accord de courtoisie <marchand> » dans une facture (ex. Nantel Musique) veut dire que ce marchand nous l'a envoyé.
Fiche client : pour toute demande d'un client, vérifie avec « chercher_client » (courriel, téléphone, puis nom) s'il a déjà une fiche et des visites. S'il n'a AUCUNE fiche, crée-la tout de suite avec « creer_client » (client potentiel), avec les coordonnées du fil, sans attendre qu'on te le demande, et dis-le dans ta note. Ne crée jamais de fiche si une fiche correspond déjà (même courriel, même téléphone, ou même nom et même ville) : signale plutôt un doublon possible.
Pour tout ce que la case de l'assistant de Ma Journée sait faire (créer un RV, RV conjoint, soumissions, recherche dans les notes, appels récents, lien de réservation, photos d'un courriel, frais partagés…), utilise « demander_assistant » et rapporte sa réponse telle quelle dans ta note (action "reponse"). Un RV passe toujours par un aperçu ; il n'est créé qu'après un « oui » de l'équipe, et sans confirmation automatique au client.
Apprendre : quand l'équipe dit « la prochaine fois… », « dorénavant… », « à l'avenir… », « ne fais plus… », appelle « retenir_regle » avec une règle claire et générale (le cas + quoi faire), puis confirme-la dans ta note. « @Ivo quelles sont tes règles ? » : liste les règles apprises avec leur numéro. « @Ivo oublie la règle 3 » : appelle « oublier_regle ». Seuls Allan, Nicolas et Louise peuvent te donner ou retirer une règle.
Bloquer un technicien : quand l'équipe le demande (« bloque JP mardi matin »), utilise « bloquer_technicien » : c'est un bloc personnel « RÉSERVÉ (à confirmer) » dans Gazelle, sans aucun avis au client. Tu ne crées jamais de vrai RV client ni de confirmation.
Nouveau client (aucune visite passée) : quand tu proposes ou prépares un RV, rappelle que la note du RV doit dire au technicien de demander au client comment il nous a trouvés.
Frais de déplacement : ne les devine JAMAIS. Appelle l'outil « frais_deplacement » avec l'adresse ou le code postal du client (dans le fil, ou trouvé avec « chercher_client » à partir de son courriel ou de son nom). C'est le calculateur officiel de PTM : donne le montant qu'il retourne, tel quel. Regrouper une visite avec un RV voisin ne change pas les frais du client, sauf décision de l'équipe : tu peux le signaler comme piste, sans promettre de rabais. Si l'outil échoue ou si l'adresse est introuvable, dis-le et mets [frais à confirmer].
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


def _horaire(jours: int = 45) -> str:
    """Horaire de l'équipe (lecture seule) : RV clients avec ville, blocs perso réduits à « occupé »."""
    from datetime import datetime, timedelta
    from core.gazelle_api_client import GazelleAPIClient
    from core.timezone_utils import MONTREAL_TZ
    noms = {"usr_HcCiFk7o0vZ9xAI0": "Nicolas", "usr_ofYggsCDt2JAVeNP": "Allan", "usr_ReUSmIJmBF86ilY1": "JP",
            "usr_QmEpdeM2xMgZVkDS": "JP", "usr_bbt59aCUqUaDWA8n": "Margot", "usr_HihJsEgkmpTEziJo": "À attribuer"}
    debut = datetime.now(MONTREAL_TZ).date()
    evs = GazelleAPIClient().get_appointments(start_date_override=debut.isoformat(),
                                              end_date_override=(debut + timedelta(days=jours)).isoformat()) or []
    villes = _villes_clients({(e.get("client") or {}).get("id") for e in evs} - {None})
    lignes = []
    for e in evs:
        if (e.get("status") or "").upper() in ("CANCELLED", "CANCELED") or (e.get("type") or "") == "MEMO":
            continue
        try:
            d = datetime.fromisoformat(e["start"].replace("Z", "+00:00")).astimezone(MONTREAL_TZ)
        except Exception:
            continue
        tech = noms.get((e.get("user") or {}).get("id"), "?")
        fin = d + timedelta(minutes=int(e.get("duration") or 60))
        if e.get("isAllDay"):
            quand = f"{d:%Y-%m-%d %a} toute la journée"
        else:
            quand = f"{d:%Y-%m-%d %a} {d:%H:%M}-{fin:%H:%M}"
        if e.get("type") == "APPOINTMENT":
            loc = e.get("location") or {}
            lieu = (" ".join(x for x in (loc.get("municipality"), loc.get("postalCode")) if x)
                    or villes.get((e.get("client") or {}).get("id")) or "lieu inconnu")
            quoi = f"RV client « {(e.get('title') or '')[:40]} » à {lieu}"
        else:
            quoi = "occupé"
        lignes.append((d, f"{quand} — {tech} : {quoi}"))
    return "\n".join(l for _, l in sorted(lignes))


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


def _executer_outil(nom: str, arg: Dict[str, Any]) -> str:
    try:
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
            return ivo_regles.executer(nom, arg, (_CTX.get() or {}).get("prenom"))["message"]
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
                lignes.append(f"{nom_c} ({cid or 'id ?'}) — {adr} — {visites}"
                              + (_factures_resume(cid) if cid.startswith("cli_") else ""))
            return "\n".join(lignes)
        return "Outil inconnu."
    except Exception as e:
        _log.exception("Ivo : outil %s", nom)
        return f"Échec de l'outil : {e}"


def _rediger(consigne: str, fil: str, brouillon: str, regles: List[str], echanges: str = "") -> Dict[str, Any]:
    from anthropic import Anthropic
    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    systeme = _SYSTEME
    from core import ivo_regles
    if ivo_regles.texte_pour_ia():
        systeme += "\n\n" + ivo_regles.texte_pour_ia()
    ton = _guide_ton()
    if ton:
        systeme += "\n\nGuide de ton de PTM (extrait) :\n" + ton
    try:
        horaire = _horaire()
    except Exception:
        _log.exception("Ivo : horaire indisponible")
        horaire = "(horaire indisponible pour l'instant)"
    from core.timezone_utils import MONTREAL_TZ
    from datetime import datetime
    contenu = (f"AUJOURD'HUI : {datetime.now(MONTREAL_TZ):%Y-%m-%d %A}\n\n"
               f"HORAIRE DE L'ÉQUIPE (45 prochains jours) :\n{horaire}\n\n"
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
        {"name": "frais_deplacement",
         "description": "Calculateur officiel des frais de déplacement PTM pour une adresse ou un code postal client.",
         "input_schema": {"type": "object", "required": ["adresse"],
                          "properties": {"adresse": {"type": "string"}}}},
        *__import__("core.ivo_regles", fromlist=["OUTILS"]).OUTILS,
        {"name": "demander_assistant",
         "description": ("Ton accès principal à tout l'assistant Gazelle de PTM. Transmet une demande à l'assistant (la même case que dans Ma Journée) : "
                         "créer un RV (aperçu d'abord, puis création après un oui), RV conjoint, réactiver ou réviser "
                         "une soumission, chercher dans les notes, appels récents, lien de réservation prérempli, "
                         "photos d'un courriel → dossier du piano, frais partagés, etc. Écris la demande complète "
                         "avec le nom du client. Pour une confirmation (« oui »), redis l'action confirmée."),
         "input_schema": {"type": "object", "required": ["demande"],
                          "properties": {"demande": {"type": "string"}}}},
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
        {"name": "chercher_client",
         "description": "Cherche un client dans Gazelle par courriel, nom ou téléphone ; retourne nom, ville, code postal et nombre de visites passées.",
         "input_schema": {"type": "object", "required": ["texte"],
                          "properties": {"texte": {"type": "string"}}}},
    ]
    messages = [{"role": "user", "content": contenu}]
    for _ in range(6):
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
        lignes.append(f"--- {qui} {auteur} ---\n{_texte(m.get('text') or m.get('body') or '')[:4000]}")
    return "\n\n".join(lignes[-12:])


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
        while historique and historique[0][0] != "user":
            historique.pop(0)
        _CTX.set({"historique": historique, "fil": fil, "prenom": _PRENOMS.get(auteur_email)})
        echanges = "\n".join(f"{'Équipe' if r == 'user' else 'Ivo'} : {t[:600]}" for r, t in historique)
        res = _rediger(consigne, fil, texte_brouillon, _regles(), echanges)
        if res.get("action") == "reponse":
            front.add_comment(conversation_id, PREFIXE_REPONSE + (res.get("note") or "je n'ai pas de réponse."),
                              auteur_email)
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

    reponse = f"{PREFIXE_REPONSE}{action}."
    if res.get("note"):
        reponse += f" {res['note']}"
    regle = (res.get("regle_generale") or "").strip()
    if regle:
        from core import ivo_regles
        reponse += " " + ivo_regles.ajouter(regle, _PRENOMS.get(auteur_email))["message"]
    front.add_comment(conversation_id, reponse, auteur_email)
    return {"statut": "ok", "action": action, "regle": regle or None}


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
    return {"evenements": len(evenements), "ivo": vus}


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
            "cle_voix": bool(os.getenv("OPENAI_API_KEY"))}


# ─── Voix d'Ivo (narration de la vidéo de présentation) — TEMPORAIRE ───
# Bornée : 40 appels par démarrage, 1500 caractères, expire le 2026-11-07. À retirer après usage.
_voix_compteur = {"n": 0}


class VoixIn(__import__("pydantic").BaseModel):
    texte: str
    voix: str = "coral"
    consigne: str = ("Voix chaleureuse, souriante et posée, accent québécois léger, rythme calme, "
                     "comme un assistant sympathique qui présente un nouvel outil à ses collègues.")


@router.post("/voix")
def voix(v: VoixIn):
    from datetime import date
    from fastapi import HTTPException, Response
    if date.today() > date(2026, 11, 7):
        raise HTTPException(410, "expiré")
    if _voix_compteur["n"] >= 40 or len(v.texte) > 1500:
        raise HTTPException(429, "limite")
    cle = os.getenv("OPENAI_API_KEY")
    if not cle:
        raise HTTPException(503, "pas de clé")
    _voix_compteur["n"] += 1
    r = requests.post("https://api.openai.com/v1/audio/speech", timeout=120,
                      headers={"Authorization": f"Bearer {cle}"},
                      json={"model": "gpt-4o-mini-tts", "voice": v.voix[:20], "input": v.texte,
                            "instructions": v.consigne[:600], "response_format": "mp3"})
    if r.status_code >= 400:
        raise HTTPException(502, r.text[:300])
    return Response(content=r.content, media_type="audio/mpeg")


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
    return {"derniers": _derniers}


@router.get("/horaire")
def horaire(jours: int = 30):
    """Ce qu'Ivo voit de l'horaire (diagnostic, lecture seule)."""
    return {"horaire": _horaire(min(max(jours, 1), 60)).split("\n")}


@router.get("/regles")
def regles():
    """Règles de réponse retenues par Ivo au fil des consignes."""
    return {"regles": _regles()}
