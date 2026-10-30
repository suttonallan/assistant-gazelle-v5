"""
Contre-vérification d'une demande Place des Arts contre le courriel d'origine.

But (Allan, oct. 2026) : la personne qui crée le RV doit pouvoir confirmer d'un coup d'œil
que l'assistant a bien compris CHAQUE détail de la demande d'Isabelle. On retrouve la ligne
du tableau du courriel qui correspond à la demande, et on dit, champ par champ, si la valeur
retenue par l'assistant se retrouve bien dans cette ligne.

Fonctions pures (aucun accès réseau) : testables sans Supabase ni Front.
"""
from __future__ import annotations

import re
import unicodedata
from datetime import date
from typing import Any, Dict, List, Optional

MOIS = {
    'jan': 1, 'janv': 1, 'janvier': 1, 'january': 1,
    'fev': 2, 'fevr': 2, 'fevrier': 2, 'feb': 2, 'february': 2,
    'mar': 3, 'mars': 3, 'march': 3,
    'avr': 4, 'avril': 4, 'apr': 4, 'april': 4,
    'mai': 5, 'may': 5,
    'juin': 6, 'jun': 6, 'june': 6,
    'juil': 7, 'juillet': 7, 'jul': 7, 'july': 7,
    'aou': 8, 'aout': 8, 'aug': 8, 'august': 8,
    'sep': 9, 'sept': 9, 'septembre': 9, 'september': 9,
    'oct': 10, 'octobre': 10, 'october': 10,
    'nov': 11, 'novembre': 11, 'november': 11,
    'dec': 12, 'decembre': 12, 'december': 12,
}
_MOIS_RE = '|'.join(sorted(MOIS, key=len, reverse=True))
# « 6-Nov », « 30 oct. », « 2 novembre », « 06/11 » (texte déjà sans accents)
DATE_RE = re.compile(
    rf"\b(\d{{1,2}})\s*(?:er)?\s*[-/ .]?\s*({_MOIS_RE})\b\.?|\b(\d{{1,2}})/(\d{{1,2}})(?:/(\d{{2,4}}))?\b",
    re.IGNORECASE)
# Début de la partie citée (courriel précédent) : on ne la lit pas.
# (Outlook rend souvent TOUT le courriel en « > » : on enlève ces marqueurs au lieu de couper.)
CITATION_RE = re.compile(
    r"^\s*(?:\*{0,2}de\s*:|\*{0,2}from\s*:|-{2,}\s*original|le .{5,80} a ecrit|on .{5,120} wrote)",
    re.IGNORECASE)
# Fin d'une ligne de demande : formule de politesse ou signature.
FIN_LIGNE_RE = re.compile(
    r"^\s*(merci|thanks|bonne journ|cordialement|si vous avez|isabelle|erik|annie|\*\*|gestionnaire|"
    r"coordonnat|t 514|260, boul|!\[|\[!\[)", re.IGNORECASE)

SALLES = {
    'WP': ['wp', 'wilfrid', 'pelletier'],
    'MS': ['ms', 'maison symphonique', 'symphonique'],
    'TM': ['tm', 'maisonneuve'],
    '5E': ['5e', '5 e', 'cinquieme'],
    'SCL': ['scl', 'leveillee'],
    'SALLE F': ['salle f'],
    'SALLE D': ['salle d'],
}
MOTS_VIDES = {'les', 'des', 'the', 'and', 'pour', 'avec', 'une', 'piano', 'pda', 'salle', 'de', 'du', 'la', 'le'}


def sans_accents(t: str) -> str:
    t = unicodedata.normalize('NFD', (t or '').lower())
    t = ''.join(c for c in t if unicodedata.category(c) != 'Mn')
    for c in '’‘′´':
        t = t.replace(c, "'")
    return t


def nettoyer_corps(texte: str) -> str:
    """Garde le message lui-même : enlève les marqueurs de citation « > », le CSS d'Outlook,
    et coupe à l'en-tête du courriel précédent (« De : », « On … wrote »)."""
    garde = []
    for ligne in (texte or '').splitlines():
        ligne = re.sub(r"^(\s*>)+\s?", '', ligne).replace('**', '').replace('\\-', '-')
        if CITATION_RE.match(sans_accents(ligne)) and any(DATE_RE.search(sans_accents(l)) for l in garde):
            break
        if ligne.lstrip().startswith(('#fae', '@page')):
            continue
        garde.append(ligne)
    return '\n'.join(garde)


def _annee_proche(jour: int, mois: int, reference: Optional[date]) -> Optional[str]:
    ref = reference or date.today()
    meilleure = None
    for an in (ref.year - 1, ref.year, ref.year + 1):
        try:
            d = date(an, mois, jour)
        except ValueError:
            continue
        if meilleure is None or abs((d - ref).days) < abs((meilleure - ref).days):
            meilleure = d
    return meilleure.isoformat() if meilleure else None


def _date_du_match(m: re.Match, reference: Optional[date]) -> Optional[str]:
    if m.group(1):
        mois = MOIS.get(m.group(2).lower().rstrip('.'))
        return _annee_proche(int(m.group(1)), mois, reference) if mois else None
    jour, mois = int(m.group(3)), int(m.group(4))
    if not (1 <= mois <= 12 and 1 <= jour <= 31):
        return None
    return _annee_proche(jour, mois, reference)


_PREFIXE_LIGNE = re.compile(r"^[\s\-–•*·]*(?:(?:un|deux|1|2)\s+accords?\s+(?:le|du)\s+)?"
                            r"(?:(?:lun|mar|mer|jeu|ven|sam|dim)\w*\.?\s+)?", re.IGNORECASE)


def analyser(texte: str, reference: Optional[date] = None):
    """Découpe le courriel en « lignes de demande » (chacune commence à une date) et en
    contexte (le reste : intro, note commune comme « Tous à 442 sur le Steinway 9' D - NY »).
    Gère les tableaux sur une ligne (« 6-Nov WP Adisq 440 Steinway 7' Avant 8h »), les tableaux
    Outlook collés une cellule par ligne, et les phrases (« - un accord le lundi 2 novembre … »).
    Une date au milieu d'une phrase d'intro (« … le 10 novembre prochain : ») n'ouvre pas de
    ligne quand le courriel contient de vraies lignes qui commencent par une date."""
    corps = nettoyer_corps(texte)
    lignes = [l.strip() for l in corps.splitlines() if l.strip()]
    rangees: List[Dict[str, Any]] = []
    courante: Optional[Dict[str, Any]] = None
    hors: List[int] = []
    fini = False

    for idx, ligne in enumerate(lignes):
        norm = sans_accents(ligne)
        matches = [m for m in DATE_RE.finditer(norm) if _date_du_match(m, reference)]
        if matches and not fini:
            for i, m in enumerate(matches):
                fin = matches[i + 1].start() if i + 1 < len(matches) else len(ligne)
                debut = 0 if i == 0 else m.start()
                tete = m.start() <= _PREFIXE_LIGNE.match(norm).end() if i == 0 else True
                courante = {'date': _date_du_match(m, reference), 'en_tete': tete,
                            'morceaux': [ligne[debut:fin].strip(' -–·,')], 'idx': [idx]}
                rangees.append(courante)
            continue
        if FIN_LIGNE_RE.match(norm):
            courante = None
            if rangees and not norm.startswith('merci'):
                fini = True   # signature : la suite n'est plus la demande
            if norm.startswith('merci'):
                hors.append(idx)
            continue
        if fini:
            continue
        if courante is not None and len(courante['morceaux']) < 8:
            courante['morceaux'].append(ligne)
            courante['idx'].append(idx)
        else:
            hors.append(idx)

    if any(r['en_tete'] for r in rangees):
        # Les dates d'intro deviennent du contexte
        for r in rangees:
            if not r['en_tete']:
                hors.extend(r['idx'])
        rangees = [r for r in rangees if r['en_tete']]
    # Une ligne de demande qui ne contient qu'une date + du texte d'intro reste une ligne ;
    # les cellules qui suivent la dernière ligne et ne ressemblent pas à des cellules
    # (phrase longue) restent dans la ligne : « Tous à 442 sur le Steinway … » sert de contexte aussi.
    resultat = [{'date': r['date'], 'texte': ' · '.join(m for m in r['morceaux'] if m)} for r in rangees]
    contexte = ' · '.join(lignes[i] for i in sorted(set(hors)))
    # La note commune après la dernière ligne vaut pour toutes les lignes
    if rangees and len(rangees[-1]['morceaux']) > 1:
        derniere = rangees[-1]
        suite = [m for m in derniere['morceaux'][1:] if len(m) > 40]
        if suite:
            contexte = ' · '.join([contexte] + suite) if contexte else ' · '.join(suite)
    return resultat, contexte


def lignes_tableau(texte: str, reference: Optional[date] = None) -> List[Dict[str, str]]:
    return analyser(texte, reference)[0]


def contexte_courriel(texte: str, reference: Optional[date] = None) -> str:
    return analyser(texte, reference)[1]


def _contient(texte_norm: str, aiguille: str) -> bool:
    a = sans_accents(aiguille).strip()
    if not a:
        return False
    return re.search(rf"(?<![a-z0-9]){re.escape(a)}(?![a-z0-9])", texte_norm) is not None


def _jetons_piano(piano: str) -> List[str]:
    """Éléments distinctifs d'un piano : taille (7', 9'), marque, modèle (U1, Ham, NY)."""
    p = sans_accents(piano)
    tailles = [re.sub(r"\s+", '', t) for t in re.findall(r"\d+\s*'", p)]
    mots = re.findall(r"steinway|baldwin|yamaha|fazioli|bosendorfer|kawai|mason|\bu\d\b|\bc\d\b|\bham|\bny\b|new york", p)
    return tailles + ['ny' if m == 'new york' else m for m in mots]


def _norm_heures(t: str) -> str:
    """« 9h00 » / « 9:00 » → « 9h », sans espaces."""
    t = re.sub(r"\s+", '', t)
    t = re.sub(r"(\d{1,2})(?:h|:)00(?!\d)", r"\1h", t)
    return re.sub(r"(\d{1,2}):(\d{2})", r"\1h\2", t)


def _jetons_heure(heure: str) -> List[str]:
    return re.findall(r"\d{1,2}h(?:\d{2})?", _norm_heures(sans_accents(heure)))


def _salle_canonique(salle: str) -> Optional[str]:
    s = sans_accents(salle).strip()
    for cle, alias in SALLES.items():
        if s == cle.lower() or s in alias:
            return cle
    return None


def _statut_champ(cle: str, val: str, ligne: Dict[str, str]) -> bool:
    t = sans_accents(ligne.get('texte') or '')
    t_compact = re.sub(r"\s+", '', t)
    if cle == 'date':
        return ligne.get('date') == val
    if cle == 'salle':
        canon = _salle_canonique(val)
        alias = (SALLES.get(canon, []) + [val]) if canon else [val]
        return any(_contient(t, a) for a in alias)
    if cle == 'pour_qui':
        mots = [m for m in re.findall(r"[a-z0-9]+", sans_accents(val)) if len(m) >= 3 and m not in MOTS_VIDES]
        return bool(mots) and sum(1 for m in mots if m in t) >= max(1, (len(mots) + 1) // 2)
    if cle == 'piano':
        jetons = _jetons_piano(val)
        if not jetons:
            return sans_accents(val) in t
        t_ny = t_compact.replace('newyork', 'ny')
        for j in jetons:
            if "'" in j:
                if j not in t_compact:
                    return False
            elif j == 'ny':
                if 'ny' not in t_ny:
                    return False
            elif j == 'ham':
                if 'ham' not in t:
                    return False
            elif not _contient(t, j):
                return False
        return True
    if cle == 'diapason':
        return re.sub(r"\D", '', val) in re.findall(r"\d{3}", t)
    if cle == 'heure':
        jetons = _jetons_heure(val)
        return all(j in _norm_heures(t) for j in jetons) if jetons else sans_accents(val) in t
    return False


CHAMPS = ('date', 'salle', 'pour_qui', 'piano', 'diapason', 'heure')


def valeurs_demande(demande: Dict[str, Any]) -> Dict[str, str]:
    return {
        'date': str(demande.get('appointment_date') or '')[:10],
        'salle': demande.get('room') or '',
        'pour_qui': demande.get('for_who') or '',
        'piano': demande.get('piano') or '',
        'diapason': str(demande.get('diapason') or ''),
        'heure': demande.get('time') or '',
    }


def comparer(demande: Dict[str, Any], ligne: Optional[Dict[str, str]],
             contexte: str = '') -> Dict[str, Dict[str, Any]]:
    """Statut par champ : 'ok' (retrouvé dans la ligne du courriel, ou à défaut ailleurs dans le
    courriel : ou='courriel'), 'ecart' (pas retrouvé), 'vide' (l'assistant n'a rien),
    'inconnu' (pas de ligne source)."""
    out: Dict[str, Dict[str, Any]] = {}
    for cle, val in valeurs_demande(demande).items():
        ou = None
        if not val:
            statut = 'vide'
        elif not ligne:
            statut = 'inconnu'
        elif _statut_champ(cle, val, ligne):
            statut, ou = 'ok', 'ligne'
        elif cle != 'date' and contexte and _statut_champ(cle, val, {'texte': contexte}):
            statut, ou = 'ok', 'courriel'
        else:
            statut = 'ecart'
        out[cle] = {'valeur': val, 'statut': statut, 'ou': ou}
    return out


def score(demande: Dict[str, Any], ligne: Dict[str, str], contexte: str = '') -> int:
    c = comparer(demande, ligne, contexte)
    poids = {'date': 5, 'pour_qui': 3, 'piano': 3, 'salle': 2, 'heure': 1, 'diapason': 1}
    return sum(p for k, p in poids.items() if c[k]['statut'] == 'ok')


def choisir_ligne(demande: Dict[str, Any], lignes: List[Dict[str, str]],
                  contexte: str = '') -> Optional[Dict[str, str]]:
    """Meilleure ligne du courriel À LA DATE de la demande (None s'il n'y en a aucune :
    soit la date a été mal lue, soit la demande vient d'un autre courriel)."""
    jour = str(demande.get('appointment_date') or '')[:10]
    candidates = [l for l in lignes if l.get('date') == jour]
    if not candidates:
        return None
    return max(candidates, key=lambda l: score(demande, l, contexte))


def associer(lignes: List[Dict[str, str]], demandes: List[Dict[str, Any]],
             contexte: str = '') -> List[List[str]]:
    """Pour chaque ligne du courriel, les ids des demandes de l'assistant qui y correspondent
    (une demande ne compte qu'une fois : la ligne où elle score le mieux)."""
    resultat: List[List[str]] = [[] for _ in lignes]
    for d in demandes:
        jour = str(d.get('appointment_date') or '')[:10]
        scores = []
        for l in lignes:
            c = comparer(d, l, contexte) if l.get('date') == jour else None
            # Même date ET même événement (ou, à défaut, même piano dans la même salle)
            if c and (c['pour_qui']['statut'] == 'ok'
                      or (c['piano']['statut'] == 'ok' and c['salle']['statut'] == 'ok')):
                scores.append(score(d, l, contexte))
            else:
                scores.append(-1)
        if scores and max(scores) >= 0:
            resultat[scores.index(max(scores))].append(d.get('id'))
    return resultat


def date_du_sujet(sujet: str) -> Optional[str]:
    m = re.search(r"(20\d{2})-(\d{2})-(\d{2})", sujet or '')
    return f"{m.group(1)}-{m.group(2)}-{m.group(3)}" if m else None
