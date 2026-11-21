"""Infos d'accès d'un piano (salle, porte, code, entrée) recopiées dans la note du RV.

Le technicien qui arrive à une salle doit savoir, dans le RV, qu'il faut demander le code
(les codes changent souvent) et connaître le dernier code noté.
Source unique : le mémo (notes) du piano dans Gazelle — Gazelle fait foi. Rien
n'est écrit en dur ici (dépôt public) : on relit le mémo au moment de créer le RV.

On ne garde que l'en-tête du mémo (avant le premier historique daté, ex. « Juin 2025 »)
et seulement les lignes qui parlent d'accès : salle, porte, code, entrée, étage,
sécurité, clé, ascenseur, local.
"""
import re
from typing import Iterable, List

_MOIS = (r"(jan(v(ier)?)?|f[ée]vr(ier)?|mars|avr(il)?|mai|juin|juil(let)?|ao[uû]t|sept(embre)?"
         r"|oct(obre)?|nov(embre)?|d[ée]c(embre)?)\.?")
# Début de l'historique daté : « Juin 2025 », « Jan26 », « Mars 26 », « 27 mars »…
_DEBUT_HISTORIQUE = re.compile(rf"^\s*(\d{{1,2}}\s+{_MOIS}(?![a-z])|{_MOIS}\s*\d{{2,4}}\b)", re.IGNORECASE)
_ACCES = re.compile(
    r"\b(code|porte|entr[ée]e|[ée]tage|s[ée]curit[ée]|cl[ée]|ascenseur|salle|local|loge|ouvre)\b",
    re.IGNORECASE)


_CODE = re.compile(r"\bcode\b", re.IGNORECASE)
AVIS_CODE = ("⚠️ CODE DE PORTE À DEMANDER avant d'arriver : les codes changent souvent. "
             "Le code ci-dessous est seulement le dernier connu et peut avoir changé.")


def lignes_acces(notes: str) -> List[str]:
    """Lignes d'accès de l'en-tête d'un mémo de piano."""
    garde = []
    for ligne in (notes or "").splitlines():
        if _DEBUT_HISTORIQUE.match(ligne):
            break
        t = ligne.strip()
        if t and _ACCES.search(t):
            garde.append(t)
    return garde


def note_acces_pianos(gz, piano_ids: Iterable[str], strict: bool = False) -> str:
    """Bloc « Accès » à ajouter à la note du RV ; chaîne vide si rien d'utile.
    Ne bloque jamais la création du RV. strict=True : lève une erreur si un mémo
    ne peut pas être lu (la vérification du soir ne doit pas écrire un bloc incomplet)."""
    blocs = []
    for pid in [p for p in (piano_ids or []) if p]:
        try:
            res = gz._execute_query(
                "query($id: String!) { piano(id: $id) { id make model notes } }", {"id": pid})
            if strict and (not isinstance(res, dict) or res.get("errors")
                           or not (res.get("data") or {}).get("piano")):
                raise RuntimeError(f"mémo du piano {pid} illisible : {(res or {}).get('errors')}")
            p = ((res or {}).get("data") or {}).get("piano") or {}
        except Exception:
            if strict:
                raise
            continue
        lignes = lignes_acces(p.get("notes") or "")
        if lignes:
            nom = f"{p.get('make') or ''} {p.get('model') or ''}".strip()
            blocs.append((nom, lignes))
    if not blocs:
        return ""
    # Les codes changent souvent (décision d'Allan, 13 nov. 2026) : toujours demander
    # le code à jour ; le code du mémo n'est donné que comme dernier code connu.
    a_un_code = any(_CODE.search(l) for _, lignes in blocs for l in lignes)
    consigne = (AVIS_CODE + "\n") if a_un_code else ""
    if len(blocs) == 1:
        return consigne + "Accès (mémo du piano) : " + " — ".join(blocs[0][1])
    return consigne + "Accès (mémo du piano) :\n" + "\n".join(
        f"- {nom} : " + " — ".join(l) for nom, l in blocs)


def ajouter_acces(notes: str, acces: str) -> str:
    """Ajoute le bloc d'accès en tête de note, sans doublon."""
    if not acces or acces in (notes or ""):
        return notes or ""
    return acces + ("\n\n" + notes if notes else "")


_TETE_BLOC = "Accès (mémo du piano)"


def _bornes_bloc(texte: str):
    """(début, fin) du bloc d'accès dans une note de RV, ou None.
    Le bloc = avertissement facultatif + « Accès (mémo du piano) … » jusqu'à la
    première ligne vide (ajouter_acces met toujours une ligne vide après)."""
    t = texte or ""
    i = t.find(_TETE_BLOC)
    if i < 0:
        return None
    debut = i
    j = t.rfind(AVIS_CODE, 0, i)
    if j >= 0 and not t[j + len(AVIS_CODE):i].strip():
        debut = j
    # Fin = format connu du bloc, jamais « jusqu'à la ligne vide » : une ligne tapée
    # juste sous le bloc par l'équipe ne doit pas être avalée.
    #  - un piano : la ligne « Accès (mémo du piano) : … » ;
    #  - plusieurs : « Accès (mémo du piano) : » puis les lignes « - … ».
    fin = _fin_de_ligne(t, i)
    if t[i:fin].strip() == _TETE_BLOC + " :":
        while True:
            nxt = _ligne_suivante(t, fin)
            if nxt >= len(t):
                break
            e = _fin_de_ligne(t, nxt)
            if not t[nxt:e].startswith("- "):
                break
            fin = e
    return debut, fin


def _ligne_suivante(t: str, fin: int) -> int:
    if t.startswith("\r\n", fin):
        return fin + 2
    if t.startswith("\n", fin):
        return fin + 1
    return len(t)


def _fin_de_ligne(t: str, i: int) -> int:
    j = t.find("\n", i)
    if j < 0:
        return len(t)
    return j - 1 if j > 0 and t[j - 1] == "\r" else j


def retirer_bloc_acces(texte: str) -> str:
    """La note sans le bloc d'accès. Sert aux détecteurs de salle (rappel TM/JD,
    appariement des demandes PdA) : « Sécurité Maisonneuve » dans le mémo d'un piano
    de Wilfrid-Pelletier ne veut pas dire que le RV est au Théâtre Maisonneuve."""
    b = _bornes_bloc(texte)
    if not b:
        return texte or ""
    return (texte[:b[0]] + texte[b[1]:]).strip("\r\n")


def mettre_a_jour_acces(notes: str, acces: str) -> str:
    """Ajoute le bloc d'accès, ou remplace l'ancien s'il a changé (nouveau code dans le
    mémo). Sans nouveau bloc, la note reste telle quelle (on n'efface jamais rien)."""
    notes = notes or ""
    if not acces:
        return notes
    b = _bornes_bloc(notes)
    if not b:
        return ajouter_acces(notes, acces)
    if notes[b[0]:b[1]].replace("\r\n", "\n") == acces.replace("\r\n", "\n"):
        return notes
    return notes[:b[0]] + acces + notes[b[1]:]
