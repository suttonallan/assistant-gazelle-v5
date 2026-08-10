"""
Canari de sante quotidien — Assistant Gazelle V5.

Frappe l'API en production comme un vrai utilisateur, mesure le temps de
reponse de chaque endpoint cle, verifie la fraicheur de la derniere sync, et
envoie un courriel a Allan UNIQUEMENT si quelque chose est tombe, lent ou
perime. En temps normal : aucun courriel.

Complementaire au verificateur de DONNEES (daily_sanity_check.py) : celui-ci
surveille la SANTE et la VITESSE de l'app (ce qui manquait quand PDA / Ma
Journee devenaient lents ou muets).

Usage : python modules/data_quality/daily_health_canary.py
        DRY_RUN=1 python ... (affiche le rapport sans envoyer)
"""

import os
import sys
import time
from datetime import datetime, timezone

import requests

RECIPIENT = "asutton@piano-tek.com"
API_BASE = os.getenv("CANARY_API_BASE", "https://assistant-gazelle-v5-api.onrender.com")

# Un technicien reel pour l'appel briefing (Allan).
_ALLAN = "usr_ofYggsCDt2JAVeNP"
_TODAY = datetime.now(timezone.utc).strftime("%Y-%m-%d")

# endpoint, libelle, seuil "lent" (s), timeout dur (s)
ENDPOINTS = [
    ("/health", "Sante de base", 5, 30),
    ("/api/institutions/list", "Menu institutions", 5, 30),
    ("/api/place-des-arts/requests?limit=200", "Place des Arts (ouverture)", 8, 45),
    (f"/api/briefing/daily?date={_TODAY}&technician_id={_ALLAN}", "Ma Journee (briefing)", 25, 60),
    ("/api/system/status", "Statut systeme", 5, 30),
]

# Mode leger (CANARY_LIGHT=1) : ne garder que les endpoints rapides qui TOUCHENT
# Supabase, pour un check frequent (toutes les 15 min) sans marteler le briefing
# ni la liste PDA. Suffit a detecter une panne comme la cle Supabase revoquee.
if os.getenv("CANARY_LIGHT", "").lower() in ("1", "true", "yes"):
    _LIGHT_PATHS = ("/health", "/api/institutions/list", "/api/system/status")
    ENDPOINTS = [e for e in ENDPOINTS if e[0] in _LIGHT_PATHS]

# Age max tolere pour la derniere sync avant de crier "perime" (heures).
# La sync complete tourne chaque nuit + incrementale a l'heure : 30h laisse une
# marge pour une nuit ratee sans fausse alerte.
STALE_SYNC_HOURS = 30


def check_endpoints() -> list:
    problems = []
    for path, label, slow_s, timeout_s in ENDPOINTS:
        url = f"{API_BASE}{path}"
        t0 = time.monotonic()
        try:
            r = requests.get(url, timeout=timeout_s)
            dt = time.monotonic() - t0
            if r.status_code != 200:
                problems.append({
                    "severity": "critique",
                    "title": f"{label} : HTTP {r.status_code}",
                    "detail": f"{path} a repondu {r.status_code} (attendu 200).",
                })
            elif dt > slow_s:
                problems.append({
                    "severity": "avertissement",
                    "title": f"{label} : lent ({dt:.1f}s)",
                    "detail": f"{path} a pris {dt:.1f}s (seuil {slow_s}s).",
                })
            else:
                print(f"OK  {label}: {dt:.2f}s")
        except requests.Timeout:
            problems.append({
                "severity": "critique",
                "title": f"{label} : aucun retour (timeout {timeout_s}s)",
                "detail": f"{path} n'a pas repondu en {timeout_s}s. Serveur muet ou sature.",
            })
        except Exception as e:
            problems.append({
                "severity": "critique",
                "title": f"{label} : erreur de connexion",
                "detail": f"{path} : {str(e)[:200]}",
            })
    return problems


def check_freshness() -> list:
    """Verifie la derniere sync via /api/system/status."""
    problems = []
    try:
        r = requests.get(f"{API_BASE}/api/system/status", timeout=30)
        if r.status_code != 200:
            return problems  # deja signale par check_endpoints
        data = r.json()
        status = data.get("last_sync_status")
        last_date = data.get("last_sync_date")
        if status and status != "success":
            problems.append({
                "severity": "critique",
                "title": f"Derniere sync en echec ({status})",
                "detail": f"Job: {data.get('last_sync_job')} — {data.get('last_sync_error') or 'sans detail'}",
            })
        if last_date:
            try:
                dt = datetime.fromisoformat(last_date.replace("Z", "+00:00"))
                age_h = (datetime.now(timezone.utc) - dt).total_seconds() / 3600
                if age_h > STALE_SYNC_HOURS:
                    problems.append({
                        "severity": "avertissement",
                        "title": f"Donnees possiblement perimees ({age_h:.0f}h)",
                        "detail": f"Derniere sync reussie il y a {age_h:.0f}h (seuil {STALE_SYNC_HOURS}h).",
                    })
                else:
                    print(f"OK  Derniere sync: il y a {age_h:.1f}h ({status})")
            except Exception as e:
                print(f"(freshness non calculee: {e})")
    except Exception as e:
        problems.append({
            "severity": "critique",
            "title": "Statut systeme injoignable",
            "detail": str(e)[:200],
        })
    return problems


def build_email(problems: list):
    n = len(problems)
    crit = sum(1 for p in problems if p["severity"] == "critique")
    subject = f"[PTM] Canari sante — {crit} critique(s), {n - crit} avertissement(s)"
    plain = [f"Canari de sante PTM — {n} probleme(s) detecte(s)", f"API: {API_BASE}", ""]
    html = [f"<h2>Canari de sante — {n} probleme(s)</h2>",
            f"<p style='color:#666'>API: {API_BASE}</p>"]
    for p in problems:
        tag = "CRITIQUE" if p["severity"] == "critique" else "avertissement"
        plain.append(f"[{tag}] {p['title']} :: {p['detail']}")
        color = "#c0392b" if p["severity"] == "critique" else "#e67e22"
        html.append(
            f"<p><strong style='color:{color}'>[{tag}]</strong> "
            f"<strong>{p['title']}</strong><br>{p['detail']}</p>"
        )
    return subject, "".join(html), "\n".join(plain)


def send_slack(subject: str, plain: str) -> bool:
    """Alerte Slack — canal PRIMAIRE, volontairement INDEPENDANT de Supabase :
    un simple POST HTTP vers le webhook. Il fonctionne meme quand Supabase ou
    Render sont morts (contrairement au courriel, qui peut dependre de la meme
    infra en panne). C'est ce qui garantit qu'Allan est averti d'une coupure."""
    webhook = os.getenv("BRIEFING_SLACK_WEBHOOK_ALLAN", "").strip()
    if not webhook:
        print("(pas de webhook Slack configure — alerte Slack sautee)")
        return False
    text = f"*[ALERTE PTM] {subject}*\n{plain}"
    try:
        r = requests.post(webhook, json={"text": text}, timeout=15)
        ok = 200 <= r.status_code < 300
        print("Alerte Slack envoyee." if ok else f"Echec Slack HTTP {r.status_code}")
        return ok
    except Exception as e:
        print(f"Echec Slack: {str(e)[:200]}")
        return False


def main() -> int:
    dry_run = os.getenv("DRY_RUN", "").lower() in ("1", "true", "yes")
    print(f"Canari de sante — {API_BASE}")

    problems = check_endpoints() + check_freshness()

    print(f"\nResultat : {len(problems)} probleme(s)")
    for p in problems:
        print(f"  [{p['severity']}] {p['title']} :: {p['detail']}")

    if not problems:
        print("Tout va bien — aucune alerte envoyee.")
        return 0

    subject, html, plain = build_email(problems)
    if dry_run:
        print("\n--- DRY RUN (aucune alerte) ---")
        print(f"[Slack] [ALERTE PTM] {subject}")
        print(plain)
        return 0

    # Canal PRIMAIRE : Slack (independant de Supabase — marche meme si tout est mort).
    slack_ok = send_slack(subject, plain)

    # Canal SECONDAIRE : courriel (best-effort ; ne doit pas bloquer si son infra est en panne).
    email_ok = False
    try:
        from core.email_notifier import get_email_notifier
        email_ok = get_email_notifier().send_email(
            to_emails=[RECIPIENT], subject=subject, html_content=html, plain_content=plain)
        print("Courriel envoye." if email_ok else "Echec envoi courriel.")
    except Exception as e:
        print(f"Echec courriel (non bloquant): {str(e)[:200]}")

    # Succes si AU MOINS un canal a livre l'alerte.
    return 0 if (slack_ok or email_ok) else 1


if __name__ == "__main__":
    sys.exit(main())
