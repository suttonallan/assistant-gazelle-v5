#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Digest quotidien 17h a info@ des fiches d'accord validees pas encore poussees.

Scanne chaque jour ouvrable a 17h les fiches `piano_service_records` en statut
`validated` (donc pas encore poussees vers Gazelle). Si au moins une fiche
est en attente, envoie un email recapitulatif a info@piano-tek.com pour
rappeler a Nicolas (ou la personne au bureau) de finir sa journee en
poussant le lot vers Gazelle.

Contexte : demande par Allan le 2026-04-18 apres que Nicolas ait exprime
de la confusion sur le workflow validate/push. Quand une fiche validee
traine, elle cree de l'ambiguite visuelle le lendemain quand on ouvre le
piano pour une nouvelle saisie. La solution est comportementale : pousser
chaque jour, et le digest sert de rappel quotidien.

Parametres valides par Allan le 2026-04-18 :
- Destinataire : info@piano-tek.com (seulement, Nicolas lit cette boite)
- Escalation : si une fiche validee traine depuis >3 jours, Allan en CC
- Heure : 17h00 Montreal, lundi-vendredi
- Si zero fiche en attente : aucun email (silence = tout est propre)
- Pas de deduplication : on VEUT re-rappeler tous les jours tant que pas pousse
- Le push reste manuel : le digest rappelle, ne declenche rien
"""

import os
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
from collections import defaultdict
from urllib.parse import quote

import requests as http_requests

from core.supabase_storage import SupabaseStorage
from core.email_notifier import EmailNotifier


ESCALATION_DAYS = 3  # Au-dela, Allan en CC

# Mapping slug d'institution -> nom affichable
INSTITUTION_LABELS = {
    "vincent-dindy": "Vincent d'Indy",
    "place-des-arts": "Place des Arts",
    "orford": "Orford",
}

FRONTEND_BASE_URL = "https://suttonallan.github.io/assistant-gazelle-v5/"


def _fetch_validated_records(storage: SupabaseStorage) -> List[Dict]:
    """Retourne toutes les fiches status='validated' (donc pas encore poussees)
    avec les champs necessaires au digest. Joint avec gazelle_pianos pour
    enrichir avec location/make/model (qui ne sont pas dans piano_service_records)."""
    url = (
        f"{storage.api_url}/piano_service_records"
        f"?status=eq.validated"
        f"&select=id,piano_id,institution_slug,validated_at,validated_by,travail"
        f"&order=institution_slug.asc"
    )
    try:
        r = http_requests.get(url, headers=storage._get_headers(), timeout=15)
        if r.status_code != 200:
            print(f"WARN fetch validated HTTP {r.status_code}: {r.text[:200]}")
            return []
        records = r.json() or []
    except Exception as exc:
        print(f"WARN fetch validated erreur : {exc}")
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
        # validated_at est stocke en UTC (datetime.utcnow().isoformat())
        ts = iso_ts.replace("Z", "").split("+")[0]
        dt = datetime.fromisoformat(ts).replace(tzinfo=timezone.utc)
        delta = datetime.now(timezone.utc) - dt
        return delta.days
    except Exception:
        return None


def _format_validated_on(iso_ts: Optional[str]) -> str:
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
        age = _days_since(rec.get("validated_at"))
        rec["age_days"] = age
        rec["escalate"] = age is not None and age >= ESCALATION_DAYS
        rec["validated_on_label"] = _format_validated_on(rec.get("validated_at"))
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
            validated_by = rec.get("validated_by") or "?"
            validated_on = rec.get("validated_on_label")
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
            marker = "&#9888;&#65039;" if escalate else "&#128203;"  # warning or clipboard
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
                f"Valide par {validated_by}<br/>"
                f"<small style='color:#666;'>le {validated_on}{age_str}</small>"
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
            f"<th style='text-align:left;padding:8px;border-bottom:2px solid #ccc;'>Validation</th>"
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
            f"Allan est en copie pour les fiches qui trainent. Pousse-les aujourd'hui si possible."
            "</span></div>"
        )

    return f"""<!DOCTYPE html>
<html><body style="font-family:-apple-system,Helvetica,Arial,sans-serif;color:#333;max-width:760px;margin:0 auto;padding:20px;">
<h2 style="color:#2d5a87;">Fiches d'accord a pousser vers Gazelle</h2>
<p>Salut,</p>
<p>
  Il reste <strong>{total} fiche(s)</strong> validee(s) qui n'ont pas encore
  ete poussees vers Gazelle. Pour garder les entrees claires pour tout le
  monde, pense a les pousser avant de terminer la journee.
</p>
{escalation_banner}
<p style="color:#666;font-size:13px;">
  Genere le {today_str}.
</p>
{''.join(sections)}
<p style="margin-top:30px;padding:12px;background:#f5f5f5;border-radius:4px;">
  <strong>Comment pousser ?</strong><br/>
  Ouvre le dashboard de l'institution concernee, va dans la vue admin
  des fiches validees, et clique <em>Pousser vers Gazelle</em>.<br/>
  <a href="{FRONTEND_BASE_URL}" style="color:#2d5a87;">Ouvrir l'application &rarr;</a>
</p>
<p style="color:#999;font-size:12px;margin-top:20px;">
  <em>Ce digest est envoye a 17h chaque jour ouvrable tant qu'il reste des
  fiches validees en attente. Aucun email = tout est pousse, bravo.</em>
</p>
</body></html>"""


def _build_plain(grouped: Dict[str, List[Dict]], total: int) -> str:
    """Version texte simple du digest."""
    lines = [
        f"Il reste {total} fiche(s) d'accord validee(s) a pousser vers Gazelle.",
        "",
    ]
    for slug, records in grouped.items():
        inst_label = INSTITUTION_LABELS.get(slug, slug)
        lines.append(f"== {inst_label} ({len(records)} fiche(s)) ==")
        for rec in records:
            local = rec.get("piano_local") or "?"
            age = rec.get("age_days")
            age_str = f" (il y a {age} jours)" if age and age > 1 else ""
            marker = "[!]" if rec.get("escalate") else "-"
            lines.append(f"  {marker} Local {local}, valide par {rec.get('validated_by') or '?'}{age_str}")
        lines.append("")
    lines.append(f"Ouvrir l'application : {FRONTEND_BASE_URL}")
    return "\n".join(lines)


async def run_push_digest() -> Dict:
    """Entry point appele par le scheduler. Retourne un rapport.

    Retourne :
        {
            "success": bool,
            "validated_count": int,
            "institutions_count": int,
            "escalations_count": int,
            "email_sent": bool,
            "error": Optional[str],
        }
    """
    storage = SupabaseStorage(silent=True)

    records = _fetch_validated_records(storage)
    total = len(records)

    if total == 0:
        print("OK Aucune fiche validee en attente -- pas d'email envoye")
        return {
            "success": True,
            "validated_count": 0,
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
    subject = f"{subject_icon} {total} fiche(s) d'accord a pousser vers Gazelle"

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
        "validated_count": total,
        "institutions_count": len(grouped),
        "escalations_count": escalations_count,
        "email_sent": bool(sent),
    }


if __name__ == "__main__":
    import asyncio
    result = asyncio.run(run_push_digest())
    print(result)
