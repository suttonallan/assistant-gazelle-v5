#!/usr/bin/env python3
"""Applique les migrations SQL de sql/auto/ (idempotentes) via la fonction
exec_sql, avec la clé service-role (secret GitHub, jamais dans le code).

Vérifie aussi que la clé PUBLIQUE (anon, visible dans le frontend) ne peut PAS
appeler exec_sql. Envoie un courriel récapitulatif à Allan.
"""
import os
import re
import sys
from pathlib import Path

import requests

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE))

URL = os.environ["SUPABASE_URL"].rstrip("/")
SERVICE = os.environ["SUPABASE_SERVICE_ROLE_KEY"]


def _cle_anon() -> str:
    env = (RACINE / "frontend" / ".env.production").read_text()
    m = re.search(r"VITE_SUPABASE_ANON_KEY=(\S+)", env)
    return m.group(1) if m else ""


def exec_sql(cle: str, sql: str) -> requests.Response:
    return requests.post(
        f"{URL}/rest/v1/rpc/exec_sql",
        headers={"apikey": cle, "Authorization": f"Bearer {cle}", "Content-Type": "application/json"},
        json={"sql_query": sql}, timeout=30)


def anon_peut_executer() -> bool:
    r = exec_sql(_cle_anon(), "SELECT 1")
    return r.status_code in (200, 204)


def tables_lisibles_par_anon() -> list:
    """Tables dont la clé publique (anon) peut lire au moins une ligne. Doit être vide."""
    cle = _cle_anon()
    h = {"apikey": cle, "Authorization": f"Bearer {cle}"}
    try:
        spec = requests.get(f"{URL}/rest/v1/", headers=h, timeout=30).json()
        noms = [p.strip("/") for p in spec.get("paths", {}) if p.count("/") == 1 and not p.startswith("/rpc")]
    except Exception as e:  # noqa: BLE001
        return [f"(vérification impossible : {e})"]
    lisibles = []
    for nom in sorted(n for n in noms if n):
        r = requests.get(f"{URL}/rest/v1/{nom}?select=*&limit=1", headers=h, timeout=30)
        if r.status_code == 200 and r.text.strip() not in ("", "[]"):
            lisibles.append(nom)
    return lisibles


def main() -> int:
    rapport = []
    ok_global = True

    existe = exec_sql(SERVICE, "SELECT 1")
    if existe.status_code not in (200, 204):
        rapport.append(f"exec_sql indisponible ({existe.status_code}) : {existe.text[:200]}")
        rapport.append("Aucune migration appliquée. Coller UNE fois dans Supabase > SQL Editor > Run :")
        for f in sorted((RACINE / "sql" / "auto").glob("*.sql")):
            corps = f.read_text().rstrip().rstrip(";")
            rapport.append(f"\n-- {f.name}\n{corps};")
        ok_global = False
    else:
        avant = anon_peut_executer()
        rapport.append(f"Sécurité AVANT : clé publique peut exécuter du SQL = {'OUI (faille)' if avant else 'non'}")
        for f in sorted((RACINE / "sql" / "auto").glob("*.sql")):
            if f.name.startswith("000_"):
                continue  # création d'exec_sql : faite une fois à la main, déjà en place
            texte = "\n".join(l for l in f.read_text().splitlines() if not l.strip().startswith("--"))
            for stmt in [s.strip() for s in texte.split(";") if s.strip()]:
                r = exec_sql(SERVICE, stmt)
                ok = r.status_code in (200, 204)
                ok_global &= ok
                rapport.append(f"{'OK ' if ok else 'ÉCHEC'} [{f.name}] {stmt[:90]}" + ("" if ok else f" -> {r.text[:200]}"))
        lisibles = tables_lisibles_par_anon()
        ok_global &= not lisibles
        rapport.append("Tables lisibles avec la clé publique : "
                       + (", ".join(lisibles) if lisibles else "aucune (OK)"))
        apres = anon_peut_executer()
        ok_global &= not apres
        rapport.append(f"Sécurité APRÈS : clé publique peut exécuter du SQL = {'OUI (FAILLE TOUJOURS OUVERTE)' if apres else 'non'}")

    texte = "\n".join(rapport)
    print(texte)
    if ok_global:
        # Tout est OK : rien à signaler à Allan, le rapport reste dans le journal GitHub.
        return 0
    try:
        from core.email_notifier import get_email_notifier
        sujet = "[PTM] Migrations SQL — À VÉRIFIER"
        get_email_notifier().send_email(
            to_emails=["asutton@piano-tek.com"], subject=sujet,
            html_content="<pre>" + texte.replace("<", "&lt;") + "</pre>", plain_content=texte)
    except Exception as e:
        print(f"Courriel non envoyé : {e}")
    return 0 if ok_global else 1


if __name__ == "__main__":
    sys.exit(main())
