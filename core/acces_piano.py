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


def note_acces_pianos(gz, piano_ids: Iterable[str]) -> str:
    """Bloc « Accès » à ajouter à la note du RV ; chaîne vide si rien d'utile.
    Ne bloque jamais la création du RV."""
    blocs = []
    for pid in [p for p in (piano_ids or []) if p]:
        try:
            res = gz._execute_query(
                "query($id: String!) { piano(id: $id) { id make model notes } }", {"id": pid})
            p = ((res or {}).get("data") or {}).get("piano") or {}
        except Exception:
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
