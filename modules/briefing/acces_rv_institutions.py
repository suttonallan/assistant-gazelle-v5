#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Code de porte dans TOUS les RV d'institution, peu importe qui les a créés.

Contexte (21 nov. 2026, Allan à la salle de répétition 1 de Wilfrid-Pelletier, sans
code dans son RV) : le bloc « Accès » n'était ajouté qu'aux RV créés par l'assistant
ou par Ivo (depuis le 13 nov.). Un RV créé directement dans Gazelle, ou avant le
13 nov., n'avait rien.

Cette vérification passe à 6 h et à 21 h sur les RV d'institution d'aujourd'hui aux
7 prochains jours :
  - aucun bloc et le mémo d'un piano du RV donne un code → on ajoute le bloc en tête
    de la note (avertissement « code à demander » + dernier code connu) ;
  - bloc déjà là mais le mémo a changé (nouveau code) → on le remplace ;
  - sinon on ne touche à rien.

Garde-fous :
  - seulement les RV ACTIFS de type APPOINTMENT, avec au moins un piano ;
  - seulement si le bloc contient un code (pas de bloc « salle » seul) ;
  - un mémo illisible → RV sauté (jamais de bloc incomplet) ;
  - relecture du RV juste avant d'écrire, on n'envoie que la note (et la durée telle
    quelle) ; après coup, on vérifie que rien d'autre n'a bougé et on le remet sinon ;
  - le reste de la note n'est jamais modifié ni effacé.
"""
import json
import logging
from datetime import timedelta
from typing import Dict, List

import requests

from core.acces_piano import _CODE, mettre_a_jour_acces, note_acces_pianos
from core.timezone_utils import aujourdhui_montreal

logger = logging.getLogger(__name__)

# Repli si la table des clients ne répond pas (CLAUDE.md)
INSTITUTIONS_CONNUES = {
    'cli_9UMLkteep8EsISbG',  # Vincent-d'Indy
    'cli_HbEwl9rN11pSuDEU',  # Place des Arts
    'cli_PmqPUBTbPFeCMGmz',  # Orford
}

_CHAMPS_RV = """id title start duration status type isAllDay buffer tags travelMode notes
  client { id } user { id firstName } allEventPianos(first: 20) { nodes { isTuning piano { id } } }"""

Q_RVS = ("query($f: PrivateAllEventsFilter){ allEventsBatched(first: 100, filters: $f){ "
         "pageInfo { hasNextPage } nodes { " + _CHAMPS_RV + " } } }")
Q_RV = "query($id: String!) { event(eventId: $id) { " + _CHAMPS_RV + " } }"
M_MAJ = """mutation($id: String!, $input: PrivateEventInput!) { updateEvent(id: $id, input: $input) {
  event { id } mutationErrors { fieldName messages } } }"""

# Tout ce qui ne doit PAS bouger quand on change la note
_PRESERVES = ('title', 'start', 'duration', 'type', 'isAllDay', 'buffer', 'tags',
              'travelMode', 'client', 'user', 'pianos')


def _instantane(ev: Dict) -> Dict:
    return {
        'title': ev.get('title') or '', 'start': ev.get('start'), 'duration': ev.get('duration'),
        'type': ev.get('type'), 'isAllDay': bool(ev.get('isAllDay')), 'buffer': ev.get('buffer'),
        'tags': sorted(ev.get('tags') or []), 'travelMode': ev.get('travelMode'),
        'client': (ev.get('client') or {}).get('id'), 'user': (ev.get('user') or {}).get('id'),
        'pianos': sorted((n['piano']['id'], bool(n.get('isTuning')))
                         for n in ((ev.get('allEventPianos') or {}).get('nodes') or [])
                         if n.get('piano')),
    }


def _input_remise(inst: Dict, champs: List[str]) -> Dict:
    inp = {}
    for c in champs:
        if c == 'client':
            if inst['client']:
                inp['clientId'] = inst['client']
        elif c == 'user':
            if inst['user']:
                inp['userId'] = inst['user']
        elif c == 'pianos':
            inp['pianos'] = [{"pianoId": pid, "isTuning": t} for pid, t in inst['pianos']]
        elif inst.get(c) is not None:
            inp[c] = inst[c]
    return inp


def institutions() -> set:
    ids = set(INSTITUTIONS_CONNUES)
    try:
        from core.supabase_storage import SupabaseStorage
        st = SupabaseStorage(silent=True)
        r = requests.get(f"{st.api_url}/gazelle_clients?select=external_id,tags&tags=not.is.null",
                         headers=st._get_headers(), timeout=20)
        for c in (r.json() if r.status_code == 200 else []):
            tags = c.get('tags') or []
            texte = (" ".join(tags) if isinstance(tags, list) else str(tags)).lower()
            if 'institution' in texte and c.get('external_id'):
                ids.add(c['external_id'])
    except Exception as e:
        logger.warning(f"Accès RV : liste des institutions depuis Supabase impossible ({e}) — repli")
    return ids


def _lire_rv(gz, eid: str) -> Dict:
    res = gz._execute_query(Q_RV, {"id": eid})
    ev = ((res or {}).get('data') or {}).get('event')
    if not ev:
        raise RuntimeError(f"RV {eid} illisible : {(res or {}).get('errors')}")
    return ev


def traiter_rv(gz, ev: Dict, dry_run: bool) -> Dict:
    rapport = {'event_id': ev.get('id'), 'titre': ev.get('title'), 'debut': ev.get('start'),
               'technicien': (ev.get('user') or {}).get('firstName'), 'action': 'SAUTÉ', 'raison': ''}
    if (ev.get('status') or '').upper() != 'ACTIVE':
        rapport['raison'] = f"statut {ev.get('status')}"
        return rapport
    if (ev.get('type') or '').upper() != 'APPOINTMENT':
        rapport['raison'] = f"type {ev.get('type')}"
        return rapport
    pianos = [n['piano']['id'] for n in ((ev.get('allEventPianos') or {}).get('nodes') or []) if n.get('piano')]
    if not pianos:
        rapport['raison'] = 'aucun piano au RV'
        return rapport
    try:
        acces = note_acces_pianos(gz, pianos, strict=True)
    except Exception as e:
        rapport.update(action='ERREUR', raison=f"mémo illisible, RV non touché : {e}")
        return rapport
    if not acces or not _CODE.search(acces):
        rapport['raison'] = 'aucun code dans le mémo des pianos'
        return rapport
    nouvelles = mettre_a_jour_acces(ev.get('notes') or '', acces)
    if nouvelles == (ev.get('notes') or ''):
        rapport['raison'] = 'bloc d’accès déjà à jour'
        return rapport
    rapport['bloc'] = acces
    rapport['remplace'] = 'Accès (mémo du piano)' in (ev.get('notes') or '')
    if dry_run:
        rapport['action'] = 'À METTRE À JOUR' if rapport['remplace'] else 'À AJOUTER'
        return rapport

    # Écriture : relire juste avant (une note modifiée entre-temps par l'équipe est gardée)
    try:
        avant = _lire_rv(gz, ev['id'])
        if (avant.get('status') or '').upper() != 'ACTIVE':
            rapport['raison'] = f"statut {avant.get('status')} à la relecture"
            return rapport
        nouvelles = mettre_a_jour_acces(avant.get('notes') or '', acces)
        if nouvelles == (avant.get('notes') or ''):
            rapport['raison'] = 'déjà à jour à la relecture'
            return rapport
        inp = {"notes": nouvelles}
        if avant.get('duration') is not None:
            inp["duration"] = avant['duration']   # durée gardée telle quelle
        res = gz._execute_query(M_MAJ, {"id": ev['id'], "input": inp})
        payload = ((res or {}).get('data') or {}).get('updateEvent') or {}
        if not payload.get('event'):
            rapport.update(action='ERREUR', raison=f"Gazelle a refusé : {payload.get('mutationErrors') or (res or {}).get('errors')}")
            return rapport
        apres = _lire_rv(gz, ev['id'])
        ia, ip = _instantane(avant), _instantane(apres)
        changes = [c for c in _PRESERVES if ia[c] != ip[c]]
        if changes:
            logger.error(f"Accès RV {ev['id']} : Gazelle a changé {changes} — remise")
            gz._execute_query(M_MAJ, {"id": ev['id'], "input": _input_remise(ia, changes)})
            ip = _instantane(_lire_rv(gz, ev['id']))
            encore = [c for c in _PRESERVES if ia[c] != ip[c]]
            if encore:
                rapport.update(action='ERREUR', raison=(
                    f"note ajoutée, mais Gazelle a modifié {encore} et la remise a échoué — "
                    f"à corriger dans Gazelle. Avant : {json.dumps({c: ia[c] for c in encore}, ensure_ascii=False)[:400]}"))
                return rapport
        if (apres.get('notes') or '').replace('\r\n', '\n').strip() != nouvelles.replace('\r\n', '\n').strip():
            rapport.update(action='ERREUR', raison="Gazelle n'affiche pas la note attendue — à vérifier")
            return rapport
        rapport['action'] = 'MIS À JOUR' if rapport['remplace'] else 'AJOUTÉ'
        return rapport
    except Exception as e:
        rapport.update(action='ERREUR', raison=str(e))
        return rapport


def run(dry_run: bool = True, jours: int = 7) -> Dict:
    from core.gazelle_api_client import GazelleAPIClient
    gz = GazelleAPIClient()
    debut = aujourdhui_montreal()
    fin = debut + timedelta(days=jours)
    rapports, avertissements = [], []
    for cid in sorted(institutions()):
        try:
            res = gz._execute_query(Q_RVS, {"f": {"clientId": cid, "dateGet": debut.isoformat(),
                                                   "dateLet": fin.isoformat()}})
        except Exception as e:
            avertissements.append(f"{cid} : lecture des RV impossible ({e})")
            continue
        lot = ((res or {}).get('data') or {}).get('allEventsBatched') or {}
        if (lot.get('pageInfo') or {}).get('hasNextPage'):
            avertissements.append(f"{cid} : plus de 100 RV, seuls les 100 premiers traités")
        for ev in lot.get('nodes') or []:
            r = traiter_rv(gz, ev, dry_run)
            r['client_id'] = cid
            rapports.append(r)
    faits = [r for r in rapports if r['action'] not in ('SAUTÉ', 'ERREUR')]
    return {
        'du': debut.isoformat(), 'au': fin.isoformat(), 'dry_run': dry_run,
        'total_rvs': len(rapports), 'modifies': len(faits),
        'erreurs': sum(1 for r in rapports if r['action'] == 'ERREUR'),
        'avertissements': avertissements,
        'rapports': [r for r in rapports if r['action'] != 'SAUTÉ'] + [
            {k: r[k] for k in ('event_id', 'titre', 'debut', 'action', 'raison')}
            for r in rapports if r['action'] == 'SAUTÉ'],
    }


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('--appliquer', action='store_true')
    ap.add_argument('--jours', type=int, default=7)
    a = ap.parse_args()
    print(json.dumps(run(dry_run=not a.appliquer, jours=a.jours), indent=2, ensure_ascii=False))
