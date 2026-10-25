"""Lien de réservation prérempli à partir d'un courriel dans Front.

Un clic dans Front : on ajoute l'étiquette « Lien RV » à la conversation.
Toutes les 2 minutes, l'assistant :
  1. lit le dernier courriel du client dans chaque conversation étiquetée ;
  2. en extrait (Claude Haiku) prénom, nom, courriel, téléphone, ville,
     code postal, piano et besoin — jamais le numéro civique ;
  3. si le courriel correspond déjà à un client Gazelle, donne son lien
     personnel (/cli_…), sinon un lien prérempli (fragment #source=courriel,
     jamais envoyé au serveur de réservation) ;
  4. publie le lien en commentaire interne et retire l'étiquette.

Rien n'est envoyé au client : l'équipe colle le lien dans sa réponse.
"""
import json
import os
import re
from typing import Any, Dict, List, Optional
from urllib.parse import quote, urlencode

import requests

from core.front_client import get_front_client

# Adresse publique de la page (domaine PTM dès qu'il est en service : variable PAGE_RESERVATION sur Render)
PAGE_RESERVATION = os.getenv("PAGE_RESERVATION", "https://reserver.pianotechniquemontreal.com/")
NOM_ETIQUETTE = "Lien RV"
AUTEUR_COMMENTAIRE = "info@piano-tek.com"
CHAMPS = ["prenom", "nom", "courriel", "tel", "ville", "cp", "type", "marque", "annee", "lieu", "besoin"]

CONSIGNE = (
    "Tu lis le courriel d'un client de Piano Technique Montréal (accord et entretien de pianos) "
    "et tu en extrais les renseignements pour préremplir sa réservation en ligne. "
    "Réponds UNIQUEMENT par un objet JSON avec ces clés (chaîne vide si inconnu) : "
    "prenom, nom, courriel, tel, ville, cp (code postal canadien, ex. H1M 1E9), "
    "type (UPRIGHT pour un piano droit, GRAND pour un piano à queue, sinon vide), "
    "marque, annee, lieu (la pièce où se trouve le piano : salon, sous-sol, 2e étage…), "
    "besoin (une phrase courte : modèle, numéro de série, dernier accord, demande particulière). "
    "ville = la municipalité (un arrondissement ou quartier de Montréal, ex. Plateau, "
    "Mercier–Hochelaga-Maisonneuve, Rosemont, donne « Montréal »). "
    "N'interprète jamais : « S/O », « N/A » ou une case vide veulent dire inconnu, pas « jamais ». "
    "Ne mets JAMAIS le numéro civique ni la rue : le client les inscrira lui-même. "
    "Les coordonnées du signataire priment sur celles de l'expéditeur."
)


def _texte_message(m: Dict[str, Any]) -> str:
    texte = m.get("text") or ""
    if not texte:
        texte = re.sub(r"<[^>]+>", " ", m.get("body") or "")
    return texte.strip()[:6000]


def _expediteur(m: Dict[str, Any]) -> Dict[str, str]:
    for r in m.get("recipients") or []:
        if r.get("role") == "from":
            return {"courriel": r.get("handle") or "", "nom": r.get("name") or ""}
    return {"courriel": "", "nom": ""}


def extraire_renseignements(texte: str, expediteur: Dict[str, str]) -> Dict[str, str]:
    """Demande à Claude Haiku d'extraire les champs ; complète avec l'expéditeur."""
    import anthropic

    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    rep = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=600,
        system=CONSIGNE,
        messages=[{"role": "user", "content":
                   f"Expéditeur : {expediteur['nom']} <{expediteur['courriel']}>\n\nCourriel :\n{texte}"}],
    )
    brut = "".join(b.text for b in rep.content if getattr(b, "type", "") == "text")
    m = re.search(r"\{[\s\S]*\}", brut)
    donnees = json.loads(m.group(0)) if m else {}
    infos = {c: str(donnees.get(c) or "").strip() for c in CHAMPS}
    if not infos["courriel"]:
        infos["courriel"] = expediteur["courriel"]
    if not infos["prenom"] and not infos["nom"] and expediteur["nom"]:
        morceaux = expediteur["nom"].split(" ", 1)
        infos["prenom"] = morceaux[0]
        infos["nom"] = morceaux[1] if len(morceaux) > 1 else ""
    if infos["type"] not in ("UPRIGHT", "GRAND"):
        infos["type"] = ""
    return infos


def client_gazelle_par_courriel(courriel: str) -> Optional[Dict[str, Any]]:
    """Client Gazelle déjà connu (table synchronisée gazelle_clients), sinon None."""
    url, cle = os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
    if not courriel or not url or not cle:
        return None
    r = requests.get(
        f"{url}/rest/v1/gazelle_clients",
        headers={"apikey": cle, "Authorization": f"Bearer {cle}"},
        params={"select": "external_id,first_name,last_name", "email": f"ilike.{courriel}", "limit": "1"},
        timeout=10,
    )
    r.raise_for_status()
    lignes = r.json()
    return lignes[0] if lignes else None


def construire_lien(infos: Dict[str, str]) -> str:
    fragment = {"source": "courriel", **{c: infos[c] for c in CHAMPS if infos.get(c)}}
    return PAGE_RESERVATION + "#" + urlencode(fragment, quote_via=quote)


def commentaire(infos: Dict[str, str], lien: str, connu: Optional[Dict[str, Any]]) -> str:
    if connu:
        entete = ("🤖 Lien de réservation personnel (client déjà dans Gazelle : la page reprend sa fiche "
                  "après confirmation de son code postal) :")
    else:
        entete = "🤖 Lien de réservation prérempli (le client n'aura qu'à ajouter son numéro civique) :"
    resume = ", ".join(f"{c} : {infos[c]}" for c in ["prenom", "nom", "courriel", "tel", "ville", "cp", "marque"]
                       if infos.get(c))
    return f"{entete}\n{lien}\n\nPrérempli — {resume or 'coordonnées seulement'}\nÀ coller dans la réponse au client."


class LienReservation:
    def __init__(self):
        self.front = get_front_client()

    def _id_etiquette(self) -> Optional[str]:
        for t in self.front._get("/tags", params={"limit": 100}).get("_results", []):
            if (t.get("name") or "").strip().lower() == NOM_ETIQUETTE.lower():
                return t["id"]
        return None

    def creer_etiquette_si_absente(self) -> str:
        tid = self._id_etiquette()
        if tid:
            return tid
        return self.front._post("/tags", {"name": NOM_ETIQUETTE, "highlight": "blue"}).get("id", "")

    def _retirer_etiquette(self, conversation_id: str, tag_id: str) -> None:
        r = requests.delete(
            f"{self.front.BASE_URL}/conversations/{conversation_id}/tags",
            headers={**self.front._headers(), "Content-Type": "application/json"},
            json={"tag_ids": [tag_id]}, timeout=10,
        )
        if r.status_code >= 400:
            raise RuntimeError(f"Front {r.status_code}: {r.text[:200]}")

    def traiter_conversation(self, conversation_id: str) -> Dict[str, Any]:
        messages: List[Dict[str, Any]] = self.front.list_messages(conversation_id, limit=20)
        entrants = [m for m in messages if m.get("is_inbound") and not m.get("is_draft")]
        if not entrants:
            return {"conversation": conversation_id, "statut": "aucun courriel client"}
        dernier = max(entrants, key=lambda m: m.get("created_at") or 0)
        infos = extraire_renseignements(_texte_message(dernier), _expediteur(dernier))
        connu = client_gazelle_par_courriel(infos["courriel"])
        lien = PAGE_RESERVATION + connu["external_id"] if connu else construire_lien(infos)
        self.front.add_comment(conversation_id, commentaire(infos, lien, connu), AUTEUR_COMMENTAIRE)
        return {"conversation": conversation_id, "statut": "ok", "client_connu": bool(connu), "lien": lien}

    def traiter_etiquetees(self) -> Dict[str, Any]:
        tag_id = self._id_etiquette()
        if not tag_id:
            return {"traitees": 0, "note": "étiquette absente"}
        convs = self.front._get(f"/tags/{tag_id}/conversations", params={"limit": 25}).get("_results", [])
        resultats = []
        for c in convs:
            cid = c.get("id")
            try:
                resultats.append(self.traiter_conversation(cid))
            except Exception as e:  # on retire quand même l'étiquette pour ne pas boucler
                resultats.append({"conversation": cid, "statut": f"erreur : {e}"})
                try:
                    self.front.add_comment(cid, "🤖 Lien RV : je n'ai pas pu préparer le lien "
                                                f"({str(e)[:150]}). Réessayez ou faites-le à la main.",
                                           AUTEUR_COMMENTAIRE)
                except Exception:
                    pass
            try:
                self._retirer_etiquette(cid, tag_id)
            except Exception as e:
                resultats.append({"conversation": cid, "statut": f"étiquette non retirée : {e}"})
        return {"traitees": len(convs), "resultats": resultats}
