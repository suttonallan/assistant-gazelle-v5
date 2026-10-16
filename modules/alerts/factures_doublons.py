#!/usr/bin/env python3
"""
Factures Gazelle en double : avertir Louise.

Cas réel (2026-10-16) : Louise avait déjà créé la facture et l'avait écrit dans
le rendez-vous ; Margot ne l'a pas vu et en a créé une deuxième.

Règle générale (peu importe la cause) : deux factures non annulées pour le même
client, créées à moins de FENETRE_JOURS l'une de l'autre, avec des totaux
semblables (écart ≤ ECART_MAX), dont au moins une est récente → courriel à
info@ (Front) pour que Louise annule celle de trop. Rien n'est modifié dans
Gazelle. Chaque paire n'est signalée qu'une fois.
"""
from datetime import datetime, timedelta, timezone
from itertools import combinations
from typing import Any, Dict, List, Optional

FENETRE_JOURS = 21          # écart max entre les deux créations
RECENTE_JOURS = 3           # au moins une des deux créée récemment
ECART_MAX = 0.25            # totaux semblables : ±25 %
CLE_SIGNALES = "factures_doublons_signales"
DESTINATAIRE = "info@piano-tek.com"

# Clients institutionnels : plusieurs factures rapprochées sont normales.
CLIENTS_EXCLUS = {
    "cli_9UMLkteep8EsISbG",  # Vincent-d'Indy
    "cli_HbEwl9rN11pSuDEU",  # Place des Arts
    "cli_PmqPUBTbPFeCMGmz",  # Orford
}

TECHS = {
    "usr_ofYggsCDt2JAVeNP": "Allan",
    "usr_HcCiFk7o0vZ9xAI0": "Nicolas",
    "usr_ReUSmIJmBF86ilY1": "Jean-Philippe",
    "usr_bbt59aCUqUaDWA8n": "Margot",
    "usr_tndhXmnT0iakT4HF": "Louise",
}

_CHAMPS = """id number status total createdAt
      client { id companyName defaultContact { firstName lastName } }
      assignedTo { id }
      allInvoiceItems { nodes { description } }"""

_Q_FILTRE = """query($f: PrivateAllInvoicesFilter, $cursor: String) {
  allInvoices(first: 100, after: $cursor, filters: $f) {
    nodes { %s }
    pageInfo { hasNextPage endCursor } } }""" % _CHAMPS

_Q_TOUT = """query($cursor: String) {
  allInvoices(first: 100, after: $cursor) {
    nodes { %s }
    pageInfo { hasNextPage endCursor } } }""" % _CHAMPS


def _date(v: Any) -> Optional[datetime]:
    try:
        return datetime.fromisoformat(str(v).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None


def _paginer(api, requete: str, variables: Dict[str, Any], max_pages: int = 150) -> Optional[List[Dict]]:
    out, cursor = [], None
    for _ in range(max_pages):
        v = dict(variables)
        if cursor:
            v["cursor"] = cursor
        res = api._execute_query(requete, v)
        if res.get("errors"):
            return None
        conn = (res.get("data") or {}).get("allInvoices") or {}
        out.extend(conn.get("nodes") or [])
        info = conn.get("pageInfo") or {}
        if not info.get("hasNextPage"):
            break
        cursor = info.get("endCursor")
    return out


def factures_recentes(depuis: datetime) -> Dict[str, Any]:
    """Factures créées depuis `depuis`. Essaie un filtre de date côté Gazelle,
    sinon parcourt tout et filtre ici (plus lent, mais toujours juste)."""
    from core.gazelle_api_client import GazelleAPIClient
    api = GazelleAPIClient()
    jour = depuis.strftime("%Y-%m-%d")
    factures, mode = None, ""
    for cle in ("createdAtGet", "invoiceDateGet"):
        try:
            factures = _paginer(api, _Q_FILTRE, {"f": {cle: jour}})
        except Exception:
            factures = None
        if factures is not None:
            mode = cle
            break
    if factures is None:
        factures = _paginer(api, _Q_TOUT, {}, max_pages=400) or []
        mode = "complet"
    garde = [f for f in factures if (_date(f.get("createdAt")) or depuis) >= depuis]
    return {"factures": garde, "mode": mode}


def _nom(f: Dict[str, Any]) -> str:
    c = f.get("client") or {}
    if c.get("companyName"):
        return c["companyName"]
    d = c.get("defaultContact") or {}
    return " ".join(x for x in (d.get("firstName"), d.get("lastName")) if x) or c.get("id", "?")


def _annulee(f: Dict[str, Any]) -> bool:
    s = str(f.get("status") or "").upper()
    return "CANCEL" in s or "VOID" in s or "DELETED" in s


def trouver_doublons(factures: List[Dict[str, Any]], maintenant: datetime) -> List[Dict[str, Any]]:
    par_client: Dict[str, List[Dict]] = {}
    for f in factures:
        cid = (f.get("client") or {}).get("id")
        if not cid or cid in CLIENTS_EXCLUS or _annulee(f):
            continue
        par_client.setdefault(cid, []).append(f)

    paires = []
    for cid, liste in par_client.items():
        for a, b in combinations(liste, 2):
            da, db_ = _date(a.get("createdAt")), _date(b.get("createdAt"))
            if not (da and db_):
                continue
            if abs(da - db_) > timedelta(days=FENETRE_JOURS):
                continue
            if max(da, db_) < maintenant - timedelta(days=RECENTE_JOURS):
                continue
            ta, tb = a.get("total") or 0, b.get("total") or 0
            if max(ta, tb) <= 0 or abs(ta - tb) > ECART_MAX * max(ta, tb):
                continue
            a, b = sorted((a, b), key=lambda f: f.get("createdAt") or "")
            paires.append({"client": _nom(a), "cle": f"{a['id']}:{b['id']}", "factures": [a, b]})
    return paires


def _ligne(f: Dict[str, Any]) -> str:
    quand = _date(f.get("createdAt"))
    if quand:
        from core.timezone_utils import MONTREAL_TZ
        quand = quand.astimezone(MONTREAL_TZ).strftime("%Y-%m-%d %H:%M")
    tech = TECHS.get((f.get("assignedTo") or {}).get("id") or "", "—")
    total = f"{(f.get('total') or 0) / 100:,.2f} $".replace(",", " ")
    return f"n° {f.get('number')} — {total} — {f.get('status')} — créée {quand} — assignée à {tech}"


def verifier_doublons(envoyer: bool = True) -> Dict[str, Any]:
    from core.supabase_storage import SupabaseStorage

    maintenant = datetime.now(timezone.utc)
    depuis = maintenant - timedelta(days=FENETRE_JOURS + RECENTE_JOURS)
    lot = factures_recentes(depuis)
    paires = trouver_doublons(lot["factures"], maintenant)

    db = SupabaseStorage()
    deja = db.get_system_setting(CLE_SIGNALES) or []
    nouvelles = [p for p in paires if p["cle"] not in deja]

    stats = {"mode": lot["mode"], "factures": len(lot["factures"]),
             "doublons": len(paires), "nouveaux": len(nouvelles),
             "detail": [{"client": p["client"], "factures": [_ligne(f) for f in p["factures"]]}
                        for p in nouvelles]}
    if not (envoyer and nouvelles):
        return stats

    from core.email_notifier import EmailNotifier
    n = EmailNotifier()
    if not n.method:
        stats["envoi"] = "aucune méthode d'envoi"
        return stats

    blocs_html, blocs_txt = [], []
    for p in nouvelles:
        lignes = [_ligne(f) for f in p["factures"]]
        blocs_html.append(f"<p><strong>{p['client']}</strong><br>" + "<br>".join(lignes) + "</p>")
        blocs_txt.append(p["client"] + "\n  " + "\n  ".join(lignes))
    sujet = ("🧾 Facture possiblement en double : " + nouvelles[0]["client"]
             if len(nouvelles) == 1 else f"🧾 {len(nouvelles)} factures possiblement en double")
    intro = ("Même client, deux factures rapprochées avec des montants semblables. "
             "Vérifier dans Gazelle et annuler celle de trop s'il y a lieu "
             "(rien n'a été modifié automatiquement).")
    ok = n.send_email(
        to_emails=[DESTINATAIRE], subject=sujet,
        html_content=f"<p>{intro}</p>" + "".join(blocs_html)
        + "<p style='color:#666;font-size:12px'>Assistant Gazelle V5</p>",
        plain_content=intro + "\n\n" + "\n\n".join(blocs_txt),
    )
    if ok:
        db.save_system_setting(CLE_SIGNALES, (deja + [p["cle"] for p in nouvelles])[-500:])
    stats["envoi"] = "ok" if ok else "échec"
    return stats


if __name__ == "__main__":
    print(verifier_doublons(envoyer=False))
