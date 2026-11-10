"""Cas de test d'Ivo — de vraies situations de PTM rejouées chaque nuit sur un horaire figé.

But : qu'une erreur d'Ivo soit détectée par la machine avant que l'équipe la voie,
au lieu d'être corrigée cas par cas. Chaque fois qu'Ivo se trompe dans la vraie vie,
on ajoute ici le cas (situation + ce qu'une bonne réponse doit faire).

L'horaire est figé (semaine prochaine, relative à aujourd'hui) : aucune écriture ni
lecture d'horaire dans Gazelle pendant les cas (Ivo lit seulement ses tarifs, son cahier et ses règles).
Un juge (même modèle) compare la réponse aux critères et dit ✅ ou ❌ avec la raison.
"""
import json
import logging
import os
from datetime import date, datetime, timedelta
from typing import Any, Dict, List

_log = logging.getLogger(__name__)

NICOLAS, JP, MARGOT, ALLAN = ("usr_HcCiFk7o0vZ9xAI0", "usr_ReUSmIJmBF86ilY1",
                              "usr_bbt59aCUqUaDWA8n", "usr_ofYggsCDt2JAVeNP")
DESTINATAIRE = "asutton@piano-tek.com"
_resultats: Dict[str, Any] = {"quand": None, "cas": []}


def _lundi_prochain() -> date:
    from core.timezone_utils import MONTREAL_TZ
    auj = datetime.now(MONTREAL_TZ).date()
    return auj + timedelta(days=7 - auj.weekday())


def _rv(jour: date, hhmm: str, minutes: int, tech: str, titre: str = "", ville: str = "", cp: str = "",
        perso: bool = False) -> Dict[str, Any]:
    from core.timezone_utils import MONTREAL_TZ
    h, m = map(int, hhmm.split(":"))
    debut = datetime(jour.year, jour.month, jour.day, h, m, tzinfo=MONTREAL_TZ)
    ev = {"start": debut.isoformat(), "duration": minutes, "user": {"id": tech}, "status": "ACTIVE",
          "type": "PERSONAL" if perso else "APPOINTMENT", "title": titre}
    if not perso:
        ev["location"] = {"municipality": ville, "postalCode": cp}
        ev["client"] = {"id": "cli_test_" + titre[:8]}
    return ev


def _fil(client: str, texte: str) -> str:
    return f"[Courriel reçu de {client}]\n{texte}"


def cas() -> List[Dict[str, Any]]:
    lu = _lundi_prochain()
    ma, me, je, ve = (lu + timedelta(days=i) for i in range(1, 5))
    jours_fr = ["lundi", "mardi", "mercredi", "jeudi", "vendredi"]
    f = lambda d: f"{jours_fr[d.weekday()]} {d.day}"  # noqa: E731
    journee_pleine = lambda d, t: [_rv(d, "08:00", 240, t, "Client A", "Montréal", "H2X 1Y4"),  # noqa: E731
                                   _rv(d, "13:00", 300, t, "Client B", "Montréal", "H3K 1G9")]
    return [
        {
            "nom": "Jumelage dans le secteur (cas Mme Daoust, Lorraine)",
            "evenements": [
                *journee_pleine(lu, NICOLAS), *journee_pleine(ma, NICOLAS),
                _rv(ma, "09:00", 120, JP, "Client C", "Laval", "H7E 4A4"),
                _rv(ve, "09:00", 90, MARGOT, "Centre culturel", "Lorraine", "J6Z 4L1"),
                _rv(ve, "13:00", 120, MARGOT, "Client D", "Rosemère", "J7A 1B2"),
                _rv(ve, "08:00", 300, NICOLAS, perso=True),
            ],
            "fil": _fil("Mme Test, Lorraine J6Z 2B3",
                        f"Bonjour, je voudrais faire accorder mon piano droit. Je suis disponible l'après-midi "
                        f"(12 h à 17 h) du lundi au mercredi la semaine prochaine, ou le vendredi matin (8 h à 12 h)."),
            "consigne": "Qui est déjà dans le coin de Lorraine aux dates de la cliente ?",
            "criteres": (f"La réponse repère que Margot a déjà un RV à Lorraine le vendredi ({f(ve)}) en matinée et "
                         "propose de jumeler (Margot y arriverait vers 10 h 45, juste après ; un léger dépassement de midi est acceptable s'il est signalé). Elle ne dit pas que les "
                         "adresses ou les lieux des RV sont inconnus. Elle ne propose pas Allan."),
        },
        {
            "nom": "Personne de libre : ne jamais proposer Allan",
            "evenements": [*journee_pleine(ma, NICOLAS), *journee_pleine(ma, JP), *journee_pleine(ma, MARGOT),
                           _rv(me, "08:00", 120, JP, "Client E", "Verdun", "H4G 1K7")],
            "fil": _fil("M. Test, Verdun H4G 2A1",
                        f"Bonjour, est-ce possible d'avoir un accord le mardi {ma:%-d} en matinée ? Seulement ce jour-là."),
            "consigne": "Qui peut y aller mardi matin ?",
            "criteres": ("La réponse dit clairement que Nicolas, JP et Margot sont tous pris ce mardi matin. Elle ne "
                         "propose pas Allan pour la visite. Elle peut suggérer un autre jour ou de demander au client."),
        },
        {
            "nom": "Plage trop serrée (accord 1 h 30 + route)",
            "evenements": [_rv(je, "08:00", 300, JP, "Client F", "Montréal", "H2X 3X5"),
                           _rv(je, "14:15", 165, JP, "Client G", "Montréal", "H2T 2A1"),
                           *journee_pleine(je, NICOLAS), *journee_pleine(je, MARGOT)],
            "fil": _fil("Mme Test, Laval H7T 1C8",
                        f"Bonjour, JP est déjà venu chez moi. Pourrait-il revenir le jeudi {je:%-d} après-midi ?"),
            "consigne": "JP peut-il faire l'accord jeudi après-midi ?",
            "criteres": ("La réponse dit que JP n'a qu'environ 1 h 15 de libre jeudi après-midi (13 h à 14 h 15), "
                         "trop serré pour un accord d'environ 1 h 30 plus la route vers Laval, donc non ce jour-là."),
        },
        {
            "nom": "Un RV sans adresse ne rend pas tout l'horaire inconnu",
            "evenements": [{**_rv(lu, "09:00", 120, JP, "Client H"), "location": {}},
                           _rv(lu, "13:00", 120, MARGOT, "Client I", "Blainville", "J7C 2L4"),
                           _rv(me, "09:00", 120, NICOLAS, "Client J", "Rosemère", "J7A 3K1")],
            "fil": _fil("M. Test, Sainte-Thérèse J7E 1X1",
                        "Bonjour, j'aimerais un accord la semaine prochaine, n'importe quand."),
            "consigne": "Qui est dans le secteur de Sainte-Thérèse la semaine prochaine ?",
            "criteres": ("La réponse cite Margot à Blainville lundi après-midi et Nicolas à Rosemère mercredi matin "
                         "comme jumelages possibles. Elle ne prétend pas que les lieux de tous les RV sont inconnus."),
        },
        {
            "nom": "Aucun RV dans le secteur : le dire, sans inventer",
            "evenements": [_rv(lu, "09:00", 120, JP, "Client K", "Montréal", "H2X 1Y4"),
                           _rv(ma, "13:00", 120, MARGOT, "Client L", "Longueuil", "J4K 2T5")],
            "fil": _fil("Mme Test, Saint-Jérôme J7Z 5T3", "Bonjour, je cherche un accordeur pour la semaine prochaine."),
            "consigne": "Avons-nous déjà quelqu'un vers Saint-Jérôme la semaine prochaine ?",
            "criteres": ("La réponse dit qu'aucun RV n'est prévu dans le secteur de Saint-Jérôme cette semaine-là, "
                         "sans en inventer, et peut proposer des journées où un technicien est libre."),
        },
    ]


def tous_les_cas() -> List[Dict[str, Any]]:
    """Cas écrits à la main + cas appris des modifications de brouillons acceptées par l'équipe."""
    from core import ivo_apprentissage
    appris = [{**c, "evenements": []} for c in ivo_apprentissage.cas_appris()]
    return cas() + appris


def _juger(c: Dict[str, Any], reponse: str) -> Dict[str, Any]:
    from anthropic import Anthropic
    from api.ivo_routes import MODELE
    outil = {"name": "verdict", "description": "Verdict sur la réponse.",
             "input_schema": {"type": "object", "required": ["ok", "raison"], "properties": {
                 "ok": {"type": "boolean"}, "raison": {"type": "string"}}}}
    for _ in range(2):
        rep = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"]).messages.create(
            model=MODELE, max_tokens=600, tools=[outil], tool_choice={"type": "auto"},
            system=("Tu juges la réponse d'un assistant de planification. ok=true seulement si TOUS les critères "
                    "sont respectés ; raison = une phrase. Appelle OBLIGATOIREMENT l'outil « verdict », sans autre texte."),
            messages=[{"role": "user", "content": f"CRITÈRES :\n{c['criteres']}\n\nRÉPONSE D'IVO :\n{reponse}"}])
        bloc = next((b for b in rep.content if getattr(b, "type", "") == "tool_use"), None)
        if bloc:
            return dict(bloc.input)
        texte = "".join(getattr(b, "text", "") for b in rep.content)
        if "{" in texte:
            try:
                return json.loads(texte[texte.index("{"):texte.rindex("}") + 1])
            except Exception:
                pass
    return {"ok": False, "raison": "le juge n'a pas rendu de verdict"}


def executer(envoyer: bool = True) -> Dict[str, Any]:
    """Rejoue tous les cas ; courriel à Allan seulement s'il y a un échec."""
    from api import ivo_routes as ivo
    from core.timezone_utils import MONTREAL_TZ
    sortie = []
    for c in tous_les_cas():
        jeton_evts = ivo._EVTS_TEST.set(c["evenements"])
        jeton_ctx = ivo._CTX.set({"prenom": "Louise"})
        try:
            res = ivo._rediger(c["consigne"], c["fil"], "", [])
            reponse = ((res.get("brouillon") if res.get("action") == "brouillon" else res.get("note"))
                       or res.get("note") or res.get("brouillon") or "")
            verdict = _juger(c, reponse)
        except Exception as e:
            _log.exception("Cas de test d'Ivo en erreur")
            reponse, verdict = "", {"ok": False, "raison": f"erreur : {e}"}
        finally:
            ivo._EVTS_TEST.reset(jeton_evts)
            ivo._CTX.reset(jeton_ctx)
        sortie.append({"cas": c["nom"], "ok": bool(verdict.get("ok")), "raison": verdict.get("raison"),
                       "reponse": reponse[:1500]})
    _resultats.update({"quand": datetime.now(MONTREAL_TZ).isoformat(timespec="minutes"), "cas": sortie})
    echecs = [x for x in sortie if not x["ok"]]
    if envoyer and echecs:
        import html
        from core.email_notifier import get_email_notifier
        corps = "".join(f"<h3>❌ {html.escape(x['cas'])}</h3><p><b>Pourquoi :</b> {html.escape(x['raison'] or '')}</p>"
                        f"<p><b>Réponse d'Ivo :</b><br>{html.escape(x['reponse']).replace(chr(10), '<br>')}</p>"
                        for x in echecs)
        get_email_notifier().send_email(
            to_emails=[DESTINATAIRE],
            subject=f"Ivo — {len(echecs)} cas de test sur {len(sortie)} échoué(s) cette nuit",
            html_content="<p>Les cas de test d'Ivo ont été rejoués sur un horaire figé.</p>" + corps)
    return {"reussis": len(sortie) - len(echecs), "total": len(sortie), "cas": sortie}


def derniers_resultats() -> Dict[str, Any]:
    return _resultats
