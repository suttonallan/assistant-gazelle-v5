#!/usr/bin/env python3
"""
Fiches clients en double dans Gazelle.

Un groupe = des fiches qui partagent un téléphone ou un courriel, dont au moins
une est un client potentiel (PROSPECT). Rapport hebdomadaire à info@ (Front) :
seuls les groupes jamais revus y figurent. Rien n'est modifié dans Gazelle par
le rapport.

Revue d'Allan du 2026-10-28 (35 groupes) : GROUPES_DISTINCTS ne reviennent plus ;
FUSIONS_APPROUVEES sont les fusions qu'il a décidées (fiche à garder, fiches
absorbées). Seuls des identifiants Gazelle figurent ici (dépôt public).
"""
import html
import re
from typing import Any, Dict, List

import requests

DESTINATAIRE = "info@piano-tek.com"
LIEN = "https://gazelleapp.io/app/v2/clients/x/"

# Groupes jugés « pas un doublon » : ignorés tant qu'aucune nouvelle fiche ne s'y ajoute.
GROUPES_DISTINCTS = [
    frozenset(["cli_QIpditSctq7Bdvtb", "cli_sutfLzfcQCXciPZS"]),
    frozenset(["cli_9UMLkteep8EsISbG", "cli_RjYJsu0Q9ss2HiMd", "cli_uaElGO1D6YEo0WHG", "cli_xkMYNQrSX7T7E1q0"]),
    frozenset(["cli_R1PuKDpFl4ii2bdw", "cli_nyCgotqWSRPNZpxh"]),
    frozenset(["cli_lkJB7yg7Xwxm68HB", "cli_riggZzRP3yqc40kB"]),
    frozenset(["cli_OqfT2xiv0CazZ73w", "cli_e7FlP2keER16tuAH"]),
    frozenset(["cli_FvBoegI0bkl5m6zF", "cli_eiyU2axIhgdojFp8"]),
    frozenset(["cli_AnsIrmfi98tw8eAy", "cli_pEiTGamQJQkRfB6y"]),
    frozenset(["cli_3HyEFPaeNgWHntw5", "cli_RMe7Ou9JqVfmJMPi"]),
]

# (fiche à garder, [fiches à fusionner dedans]) — décidé par Allan le 2026-10-28
# (groupes Dina/Zartspace et Saine retirés à sa demande : restent à vérifier).
FUSIONS_APPROUVEES = [
    ("cli_Xwffc3j1E8eKlDjl", ["cli_dPAfQXHsH6da4FkA"]),
    ("cli_YXobayGcV22z1R4q", ["cli_NWLXSCnmE1Pucisi"]),
    ("cli_ifqvvIRylLCrJR4Z", ["cli_FTimCGl3o90AOWN3"]),
    ("cli_ck3MojRkDMTWFqKL", ["cli_Bj4W2LPjcEI64ODt"]),
    ("cli_rRzkCXorZVnvsH6H", ["cli_dNzK34RBqXEa8Sbw", "cli_zUr7RiDl3wLgUiLZ"]),
    ("cli_DMiSOkE1xYhApdVa", ["cli_LJNsTy1gFu5SO3vG"]),
    ("cli_0T1O3NwqgJAk7xAy", ["cli_6ioWs2WsEKZf5BhE"]),
    ("cli_WJiENFjLwdO5bQEb", ["cli_OmYOR7tpRlXclpz3"]),
    ("cli_4qPDqd74si6NTH66", ["cli_DMfUlRO9eTDC8Pnv"]),
    ("cli_TLIgtdA7bIF9aY2b", ["cli_Xhgl5C2NhCExemEN"]),
    ("cli_vqnSc1mZdaImmKCC", ["cli_82hHnciOEuIlcGZk"]),
    ("cli_mZUh9huQ5eSNHQK5", ["cli_xg42tfJ3xGxFKoDQ"]),
    ("cli_AcJbLJF2AvqS2n0m", ["cli_QVQCQXlgcc2KShwp"]),
    ("cli_ggCLlJVtIIVHz93N", ["cli_JiDSwuHb7rqNwNVR"]),
    ("cli_ZPkSGCM1V2EA4XFz", ["cli_7B1YCz3sLXFQTs6u"]),
    ("cli_h668GORRlcFbvNvW", ["cli_ceBhXZD9m1rMVAKE"]),
    ("cli_E1vx00hP2oCW88Ss", ["cli_NjiS8KeVz3bHiJKF"]),
    ("cli_53QMZWoYqU0xCds0", ["cli_2YXDj10qWMGxQRkz"]),
    ("cli_ljISEzEJB5sKXpdK", ["cli_JPGmQTZdkJHsNwEq"]),
    ("cli_YAMhe6RrYuQdnOU0", ["cli_FqCVEAFrmm8Jlz35"]),
    ("cli_B0XU6QcA25OdhbFt", ["cli_sPbbTPfYCXIH2Vvf"]),
    ("cli_ZPzdGn6W7FSI7rOQ", ["cli_KIAVDe4IXTPCqb8d"]),
]

_DEJA_REVUS = [frozenset([t, *s]) for t, s in FUSIONS_APPROUVEES]


def _chiffres(t: Any) -> str:
    return re.sub(r"\D", "", str(t or ""))[-10:]


def _tout_lire(table: str, select: str) -> List[Dict[str, Any]]:
    from core.supabase_storage import SupabaseStorage
    db = SupabaseStorage()
    h = dict(db._get_headers())
    lignes, debut = [], 0
    while True:
        h["Range"] = f"{debut}-{debut + 999}"
        r = requests.get(f"{db.api_url}/{table}?select={select}&order=external_id", headers=h, timeout=30)
        bloc = r.json() if r.status_code in (200, 206) else []
        lignes += bloc
        if len(bloc) < 1000:
            return lignes
        debut += 1000


def _rang(c: Dict[str, Any]):
    """Fiche à garder en priorité : active, puis nouvelle, puis avec courriel, puis la plus ancienne."""
    st = str(c.get("status") or "").upper()
    return ({"ACTIVE": 0, "NEW": 1}.get(st, 2), 0 if (c.get("email") or "").strip() else 1, c.get("created_at") or "")


def trouver_doublons(tous: bool = False) -> List[List[Dict[str, Any]]]:
    """Groupes de doublons, la fiche suggérée à garder en premier.
    tous=False : sans les groupes déjà revus par Allan."""
    clients = {c["external_id"]: c for c in _tout_lire(
        "gazelle_clients", "external_id,company_name,first_name,last_name,status,email,phone,city,created_at")}
    cles: Dict[str, set] = {}

    def ajouter(cle, cid):
        if cid in clients:
            cles.setdefault(cle, set()).add(cid)

    sources = [(c["external_id"], c.get("phone"), c.get("email")) for c in clients.values()]
    sources += [(ct.get("client_external_id"), ct.get("phone"), ct.get("email"))
                for ct in _tout_lire("gazelle_contacts", "client_external_id,email,phone")]
    for cid, tel, mel in sources:
        d = _chiffres(tel)
        if len(d) == 10:
            ajouter("t:" + d, cid)
        if (mel or "").strip():
            ajouter("m:" + mel.strip().lower(), cid)

    groupes: List[set] = []
    for ids in cles.values():
        if len(ids) < 2:
            continue
        lies = [g for g in groupes if g & ids]
        nouveau = set(ids).union(*lies) if lies else set(ids)
        groupes = [g for g in groupes if g not in lies] + [nouveau]

    resultat = []
    for g in groupes:
        fiches = sorted((clients[i] for i in g), key=_rang)
        if not any(str(c.get("status") or "").upper() == "PROSPECT" for c in fiches):
            continue
        if not tous and any(g <= r for r in GROUPES_DISTINCTS + _DEJA_REVUS):
            continue
        resultat.append(fiches)
    return sorted(resultat, key=lambda f: max(c.get("created_at") or "" for c in f), reverse=True)


def _nom(c: Dict[str, Any]) -> str:
    return c.get("company_name") or f"{c.get('first_name') or ''} {c.get('last_name') or ''}".strip() or "—"


def corps_rapport(groupes: List[List[Dict[str, Any]]]) -> str:
    e = lambda s: html.escape(str(s or "—"))
    blocs = []
    for n, fiches in enumerate(groupes, 1):
        lignes = "".join(
            f"<tr><td>{'⭐ garder' if i == 0 else 'fusionner ?'}</td>"
            f"<td><a href='{LIEN}{c['external_id']}'>{e(_nom(c))}</a></td><td>{e(c.get('status'))}</td>"
            f"<td>{e(c.get('phone'))}</td><td>{e(c.get('email'))}</td><td>{e((c.get('created_at') or '')[:10])}</td></tr>"
            for i, c in enumerate(fiches))
        blocs.append(f"<p style='margin:14px 0 4px'><b>Groupe {n}</b></p>"
                     f"<table border='1' cellpadding='4' style='border-collapse:collapse'>{lignes}</table>")
    return (f"<p><b>{len(groupes)} nouveau(x) groupe(s) de fiches en double</b> cette semaine "
            "(même téléphone ou même courriel, au moins une fiche « client potentiel »).</p>"
            "<p>La fiche suggérée à garder est en premier (active d'abord, puis celle qui a un courriel). "
            "Si ce sont de vrais doublons, fusionnez-les dans Gazelle (fiche client → Fusionner). "
            "Si ce ne sont pas des doublons (même standard téléphonique, organisme et contact), dites-le à Allan "
            "pour qu'ils ne reviennent plus.</p>" + "".join(blocs) +
            "<p style='color:#777'>Rapport hebdomadaire de l'assistant — rien n'a été modifié dans Gazelle.</p>")


def rapport_hebdomadaire() -> Dict[str, Any]:
    """Tâche du lundi : courriel à info@ seulement s'il y a de nouveaux groupes."""
    from core.email_notifier import get_email_notifier
    groupes = trouver_doublons()
    if not groupes:
        return {"groupes": 0, "envoye": False}
    ok = get_email_notifier().send_email(
        to_emails=[DESTINATAIRE],
        subject=f"Fiches clients en double — {len(groupes)} nouveau(x) groupe(s) cette semaine",
        html_content=corps_rapport(groupes))
    return {"groupes": len(groupes), "envoye": bool(ok)}


def fusionner_approuves() -> Dict[str, Any]:
    """Exécute FUSIONS_APPROUVEES dans Gazelle (mergeClients). Idempotent : une fiche
    déjà absorbée (introuvable) est passée. IRRÉVERSIBLE — décidé par Allan."""
    from core.gazelle_api_client import GazelleAPIClient
    from core.supabase_storage import SupabaseStorage
    gz, db = GazelleAPIClient(), SupabaseStorage()
    faits = set(db.get_system_setting("clients_fusions_faites") or [])
    bilan = {"fusionnees": [], "deja_faites": [], "erreurs": []}
    m = """mutation($input: PrivateMergeClientsInput!) { mergeClients(input: $input) {
             client { id } mutationErrors { fieldName messages } } }"""
    for cible, sources in FUSIONS_APPROUVEES:
        for source in sources:
            cle = f"{source}>{cible}"
            if cle in faits:
                bilan["deja_faites"].append(cle)
                continue
            try:
                r = gz._execute_query(m, {"input": {"sourceClientId": source, "targetClientId": cible}})
                p = (r.get("data") or {}).get("mergeClients") or {}
                err = r.get("errors") or p.get("mutationErrors")
                if err:
                    bilan["erreurs"].append({"fusion": cle, "erreur": str(err)[:300]})
                    continue
                faits.add(cle)
                db.save_system_setting("clients_fusions_faites", sorted(faits))
                bilan["fusionnees"].append(cle)
            except Exception as ex:
                bilan["erreurs"].append({"fusion": cle, "erreur": str(ex)[:300]})
    return bilan
