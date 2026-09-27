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
        apres = anon_peut_executer()
        ok_global &= not apres
        rapport.append(f"Sécurité APRÈS : clé publique peut exécuter du SQL = {'OUI (FAILLE TOUJOURS OUVERTE)' if apres else 'non'}")

    texte = "\n".join(rapport)
    print(texte)
    try:
        from core.email_notifier import get_email_notifier
        sujet = f"[PTM] Migrations SQL — {'OK' if ok_global else 'À VÉRIFIER'}"
        get_email_notifier().send_email(
            to_emails=["asutton@piano-tek.com"], subject=sujet,
            html_content="<pre>" + texte.replace("<", "&lt;") + "</pre>", plain_content=texte)
    except Exception as e:
        print(f"Courriel non envoyé : {e}")
    return 0 if ok_global else 1


if __name__ == "__main__":
    sys.exit(main())
