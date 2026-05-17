#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Digest quotidien 17h a info@ des fiches d'accord a valider.

Scanne chaque jour ouvrable a 17h les fiches `piano_service_records` en statut
`draft` (saisies par un technicien, pas encore validees par Nicolas). Si au
moins une fiche est en attente de validation, envoie un email recapitulatif a
info@piano-tek.com pour rappeler a Nicolas de valider et pousser.

Contexte : quand un tech saisit du travail sur un piano institutionnel,
Nicolas doit etre avise pour valider (et pousser dans la foulee).
Le digest sert de rappel de fin de journee.

Parametres :
- Destinataire : info@piano-tek.com (Nicolas lit cette boite)
- Escalation : si une fiche traine depuis >3 jours sans validation, Allan en CC
- Heure : 17h00 Montreal, lundi-vendredi
- Si zero fiche en attente : aucun email (silence = tout est propre)
- Pas de deduplication : on VEUT re-rappeler tous les jours tant que pas valide
"""

import os
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
from collections import defaultdict
from urllib.parse import quote

import requests as http_requests

from core.supabase_storage import SupabaseStorage
from core.email_notifier import EmailNotifier
from config.techniciens_config import get_technicien_by_email


ESCALATION_DAYS = 3  # Au-dela, Allan en CC

# Mapping slug d'institution -> nom affichable
INSTITUTION_LABELS = {
    "vincent-dindy": "Vincent d'Indy",
    "place-des-arts": "Place des Arts",
    "orford": "Orford",
}

FRONTEND_BASE_URL = "https://suttonallan.github.io/assistant-gazelle-v5/"


def _tech_abbreviation(email: Optional[str]) -> str:
    """Retourne l'abbreviation du tech a partir de son email (ex: 'Nick', 'JP')."""
    if not email:
        return "?"
    tech = get_technicien_by_email(email)
    if tech:
        return tech.get("abbreviation") or tech.get("prenom") or "?"
    # Fallback : premiere partie de l'email
    return email.split("@")[0].capitalize()


def _fetch_draft_records(storage: SupabaseStorage) -> List[Dict]:
    """Retourne toutes les fiches status='draft' (saisies par un tech, pas validees)
    avec les champs necessaires au digest. Joint avec gazelle_pianos pour
    enrichir avec location/make/model."""
    url = (
        f"{storage.api_url}/piano_service_records"
        f"?status=eq.draft"
        f"&select=id,piano_id,institution_slug,started_at,updated_at,technician_email,travail"
        f"&order=institution_slug.asc"
    )
    try:
        r = http_requests.get(url, headers=storage._get_headers(), timeout=15)
        if r.status_code != 200:
            print(f"WARN fetch draft HTTP {r.status_code}: {r.text[:200]}")
            return []
        records = r.json() or []
    except Exception as exc:
        print(f"WARN fetch draft erreur : {exc}")
        return []

    if not records:
        return []

    # Enrichir avec gazelle_pianos.location / make / model
    piano_ids = list({rec.get("piano_id") for rec in records if rec.get("piano_id")})
    pianos_info = _fetch_pianos_info(storage, piano_ids)
    for rec in records:
        info = pianos_info.get(rec.get("piano_id"), {})
        rec["piano_local"] = info.get("location") or ""
        make = info.get("make") or ""
        model = info.get("model") or ""
        rec["piano_name"] = f"{make} {model}".strip()
        rec["tech_abbrev"] = _tech_abbreviation(rec.get("technician_email"))

    # Trier par piano_local apres enrichissement
    records.sort(key=lambda r: (r.get("institution_slug") or "", r.get("piano_local") or ""))
    return records


def _fetch_pianos_info(storage: SupabaseStorage, piano_ids: List[str]) -> Dict[str, Dict]:
    """Retourne {external_id: {location, make, model}} pour les pianos demandes."""
    if not piano_ids:
        return {}
    ids_csv = ",".join(quote(pid) for pid in piano_ids)
    url = (
        f"{storage.api_url}/gazelle_pianos"
        f"?select=external_id,location,make,model"
        f"&external_id=in.({ids_csv})"
    )
    try:
        r = http_requests.get(url, headers=storage._get_headers(), timeout=15)
        if r.status_code == 200:
            return {p["external_id"]: p for p in r.json() if p.get("external_id")}
    except Exception as exc:
        print(f"WARN fetch pianos info erreur : {exc}")
    return {}


def _days_since(iso_ts: Optional[str]) -> Optional[int]:
    """Nombre de jours (arrondi vers le bas) depuis un timestamp ISO UTC."""
    if not iso_ts:
        return None
    try:
        ts = iso_ts.replace("Z", "").split("+")[0]
        dt = datetime.fromisoformat(ts).replace(tzinfo=timezone.utc)
        delta = datetime.now(timezone.utc) - dt
        return delta.days
    except Exception:
        return None


def _format_date(iso_ts: Optional[str]) -> str:
    """Format lisible du timestamp pour l'email."""
    if not iso_ts:
        return "date inconnue"
    try:
        ts = iso_ts.replace("Z", "").split("+")[0]
        dt = datetime.fromisoformat(ts)
        return dt.strftime("%d %b %Y")
    except Exception:
        return iso_ts[:10]


def _group_by_institution(records: List[Dict]) -> Dict[str, List[Dict]]:
    """Groupe les fiches par institution_slug, avec enrichissement
    `age_days` et `escalate`."""
    grouped: Dict[str, List[Dict]] = defaultdict(list)
    for rec in records:
        slug = rec.get("institution_slug") or "unknown"
        # Age calcule depuis started_at (quand le tech a commence) ou updated_at
        ref_ts = rec.get("started_at") or rec.get("updated_at")
        age = _days_since(ref_ts)
        rec["age_days"] = age
        rec["escalate"] = age is not None and age >= ESCALATION_DAYS
        rec["date_label"] = _format_date(ref_ts)
        grouped[slug].append(rec)
    return grouped


def _build_html(grouped: Dict[str, List[Dict]], total: int, has_escalation: bool, today_str: str) -> str:
    """Compose le corps HTML du digest."""
    sections = []
    for slug, records in grouped.items():
        inst_label = INSTITUTION_LABELS.get(slug, slug)
        rows = []
        for rec in records:
            piano_local = rec.get("piano_local") or ""
            piano_name = rec.get("piano_name") or ""
            piano_label = f"Local <strong>{piano_local}</strong>" if piano_local else "Piano"
            if piano_name:
                piano_label += f" &mdash; {piano_name}"

            tech_abbrev = rec.get("tech_abbrev") or "?"
            date_label = rec.get("date_label")
            age = rec.get("age_days")
            age_str = ""
            if age is not None:
                if age == 0:
                    age_str = " (aujourd'hui)"
                elif age == 1:
                    age_str = " (hier)"
                else:
                    age_str = f" (il y a {age} jours)"

            escalate = rec.get("escalate")
            marker = "&#9888;&#65039;" if escalate else "&#128203;"
            row_bg = "background:#fff4e5;" if escalate else ""

            travail_preview = (rec.get("travail") or "").strip().replace("\n", " ")
            if len(travail_preview) > 120:
                travail_preview = travail_preview[:117] + "..."

            rows.append(
                f"<tr style='{row_bg}'>"
                f"<td style='padding:10px 8px;border-bottom:1px solid #eee;vertical-align:top;'>"
                f"{marker} {piano_label}"
                f"</td>"
                f"<td style='padding:10px 8px;border-bottom:1px solid #eee;vertical-align:top;'>"
                f"Saisi par <strong>{tech_abbrev}</strong><br/>"
                f"<small style='color:#666;'>le {date_label}{age_str}</small>"
                f"</td>"
                f"<td style='padding:10px 8px;border-bottom:1px solid #eee;vertical-align:top;color:#555;font-size:13px;'>"
                f"{travail_preview or '&mdash;'}"
                f"</td>"
                f"</tr>"
            )

        sections.append(
            f"<h3 style='color:#2d5a87;margin-top:25px;margin-bottom:8px;'>{inst_label} "
            f"<span style='color:#666;font-weight:normal;font-size:14px;'>"
            f"&mdash; {len(records)} fiche(s)</span></h3>"
            f"<table style='width:100%;border-collapse:collapse;'>"
            f"<thead><tr style='background:#f5f5f5;'>"
            f"<th style='text-align:left;padding:8px;border-bottom:2px solid #ccc;'>Piano</th>"
            f"<th style='text-align:left;padding:8px;border-bottom:2px solid #ccc;'>Tech</th>"
            f"<th style='text-align:left;padding:8px;border-bottom:2px solid #ccc;'>Travail</th>"
            f"</tr></thead>"
            f"<tbody>{''.join(rows)}</tbody>"
            f"</table>"
        )

    escalation_banner = ""
    if has_escalation:
        escalation_banner = (
            "<div style='background:#fff4e5;border-left:4px solid #e67e22;"
            "padding:12px 16px;margin-top:15px;border-radius:4px;'>"
            "<strong>&#9888;&#65039; Fiches en attente depuis plus de 3 jours</strong>"
            "<br/><span style='color:#666;font-size:13px;'>"
            f"Allan est en copie pour les fiches qui trainent. Valide-les aujourd'hui si possible."
            "</span></div>"
        )

    return f"""<!DOCTYPE html>
<html><body style="font-family:-apple-system,Helvetica,Arial,sans-serif;color:#333;max-width:760px;margin:0 auto;padding:20px;">
<h2 style="color:#2d5a87;">Fiches d'accord a valider</h2>
<p>Salut,</p>
<p>
  Il y a <strong>{total} fiche(s)</strong> saisies par les techs qui attendent
  ta validation. Valide et pousse vers Gazelle pour garder tout propre.
</p>
{escalation_banner}
<p style="color:#666;font-size:13px;">
  Genere le {today_str}.
</p>
{''.join(sections)}
<p style="margin-top:30px;padding:12px;background:#f5f5f5;border-radius:4px;">
  <strong>Comment faire ?</strong><br/>
  Ouvre le dashboard, clique <em>Tout valider</em>, puis <em>Pousser vers Gazelle</em>.<br/>
  <a href="{FRONTEND_BASE_URL}" style="color:#2d5a87;">Ouvrir l'application &rarr;</a>
</p>
<p style="color:#999;font-size:12px;margin-top:20px;">
  <em>Ce digest est envoye a 17h chaque jour ouvrable tant qu'il reste des
  fiches a valider. Aucun email = tout est valide et pousse, bravo.</em>
</p>
</body></html>"""


def _build_plain(grouped: Dict[str, List[Dict]], total: int) -> str:
    """Version texte simple du digest."""
    lines = [
        f"Il y a {total} fiche(s) d'accord a valider et pousser vers Gazelle.",
        "",
    ]
    for slug, records in grouped.items():
        inst_label = INSTITUTION_LABELS.get(slug, slug)
        lines.append(f"== {inst_label} ({len(records)} fiche(s)) ==")
        for rec in records:
            local = rec.get("piano_local") or "?"
            tech = rec.get("tech_abbrev") or "?"
            age = rec.get("age_days")
            age_str = f" (il y a {age} jours)" if age and age > 1 else ""
            marker = "[!]" if rec.get("escalate") else "-"
            lines.append(f"  {marker} Local {local}, saisi par {tech}{age_str}")
        lines.append("")
    lines.append(f"Ouvrir l'application : {FRONTEND_BASE_URL}")
    return "\n".join(lines)


async def run_push_digest() -> Dict:
    """Entry point appele par le scheduler. Retourne un rapport.

    Retourne :
        {
            "success": bool,
            "draft_count": int,
            "institutions_count": int,
            "escalations_count": int,
            "email_sent": bool,
            "error": Optional[str],
        }
    """
    storage = SupabaseStorage(silent=True)

    records = _fetch_draft_records(storage)
    total = len(records)

    if total == 0:
        print("OK Aucune fiche draft en attente -- pas d'email envoye")
        return {
            "success": True,
            "draft_count": 0,
            "institutions_count": 0,
            "escalations_count": 0,
            "email_sent": False,
        }

    grouped = _group_by_institution(records)
    escalations_count = sum(1 for r in records if r.get("escalate"))
    has_escalation = escalations_count > 0

    today_str = datetime.now().strftime("%Y-%m-%d")
    html = _build_html(grouped, total, has_escalation, today_str)
    plain = _build_plain(grouped, total)

    # Destinataires
    recipients: List[str] = []
    info_addr = os.getenv("EMAIL_INFO") or "info@piano-tek.com"
    recipients.append(info_addr)
    if has_escalation:
        allan = os.getenv("EMAIL_ALLAN") or "asutton@piano-tek.com"
        if allan and allan not in recipients:
            recipients.append(allan)

    subject_icon = "\u26a0\ufe0f" if has_escalation else "\U0001f4cb"
    subject = f"{subject_icon} {total} fiche(s) d'accord a valider"

    notifier = EmailNotifier()
    sent = notifier.send_email(
        to_emails=recipients,
        subject=subject,
        html_content=html,
        plain_content=plain,
    )

    if sent:
        print(f"OK Digest envoye a {recipients} ({total} fiches, {escalations_count} escalations)")
    else:
        print("ERR Envoi email echoue")

    return {
        "success": True,
        "draft_count": total,
        "institutions_count": len(grouped),
        "escalations_count": escalations_count,
        "email_sent": bool(sent),
    }


if __name__ == "__main__":
    import asyncio
    result = asyncio.run(run_push_digest())
    print(result)
