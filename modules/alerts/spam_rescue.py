#!/usr/bin/env python3
"""
Rachat de spam — repère les vrais messages clients tombés dans le dossier
Spam de info@piano-tek.com (ex. le cas Jade Bruneau du 2026-09-07, où
Gmail a classé en spam une simple demande de report de rendez-vous).

On ne déplace rien automatiquement (l'accès Gmail est en lecture seule) :
on scanne le Spam régulièrement et on envoie un résumé par courriel à
Louise si un message ressemble à une vraie demande client, pour qu'elle
le sorte du spam elle-même en un clic.
"""
import json
import os
import re
from typing import Any, Dict, List

from core.gmail_scanner import get_gmail_scanner
from core.supabase_storage import SupabaseStorage

SEEN_IDS_SETTING_KEY = 'spam_rescue_seen_ids'
MAX_SEEN_IDS = 500
CONFIDENCE_THRESHOLD = 0.55

CLASSIFY_PROMPT = """Tu tries les messages du dossier Spam d'une entreprise de service de piano
(Piano Tek Musique) pour repérer les VRAIS messages de clients que le filtre anti-spam de
Gmail a classés à tort.

Exemple réel d'un message légitime classé à tort en spam (à ne PAS reproduire, juste pour
calibrer) : une cliente, Jade Bruneau, écrivait pour reporter un rendez-vous d'entretien de
piano prévu avec une technicienne, en proposant plusieurs nouvelles dates. Ton personnel,
signature professionnelle avec coordonnées réelles, référence à un rendez-vous concret.

Signes d'un VRAI message client :
- Ton personnel, direct, référence à un rendez-vous, un piano, un service, un paiement
- Signature avec un vrai nom et des coordonnées cohérentes
- Question ou demande concrète adressée à l'entreprise

Signes de VRAI spam/pourriel :
- Promotion, marketing de masse, offre non sollicitée (SEO, prêts, crypto, etc.)
- Expéditeur générique ou non lié au piano/musique
- Liens suspects, urgence artificielle, demande d'argent/gift cards inhabituelle
- Newsletter, sondage, relance commerciale d'un fournisseur inconnu

Message à évaluer :
De: {sender_name} <{sender_email}>
Sujet: {subject}
Corps (tronqué) :
{body}

Réponds UNIQUEMENT en JSON, sans markdown :
{{"is_likely_client": true/false, "confidence": 0.0-1.0, "reason": "une phrase en français expliquant pourquoi"}}"""


def _load_seen_ids(storage: SupabaseStorage) -> set:
    raw = storage.get_system_setting(SEEN_IDS_SETTING_KEY)
    if not raw:
        return set()
    # Tolère un ancien format encode en chaine JSON (json.dumps) au cas ou.
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except Exception:
            return set()
    return set(raw) if isinstance(raw, list) else set()


def _save_seen_ids(storage: SupabaseStorage, seen: set):
    capped = list(seen)[-MAX_SEEN_IDS:]
    storage.save_system_setting(SEEN_IDS_SETTING_KEY, capped)


def _get_anthropic_client():
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return None
    from anthropic import Anthropic
    return Anthropic(api_key=api_key)


def _classify(anthropic_client, email: Dict[str, Any]) -> Dict[str, Any]:
    prompt = CLASSIFY_PROMPT.format(
        sender_name=email.get('sender_name') or '(inconnu)',
        sender_email=email.get('sender_email') or '(inconnu)',
        subject=email.get('subject') or '(sans objet)',
        body=(email.get('body_text') or '')[:1500],
    )
    try:
        response = anthropic_client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text.strip()
        raw = re.sub(r'^```(?:json)?\s*', '', raw)
        raw = re.sub(r'\s*```$', '', raw)
        return json.loads(raw)
    except Exception as e:
        print(f"⚠️  Classification spam échouée pour {email.get('gmail_message_id')}: {e}")
        return {"is_likely_client": False, "confidence": 0.0, "reason": f"erreur IA: {e}"}


def scan_spam_for_real_clients(max_results: int = 30) -> Dict[str, Any]:
    """Scanne le Spam de info@piano-tek.com, alerte Louise si des messages ressemblent
    à de vraies demandes clients. Appelé par le cron (voir core/scheduler.py)."""
    storage = SupabaseStorage(silent=True)
    scanner = get_gmail_scanner()

    seen_ids = _load_seen_ids(storage)
    emails = scanner.scan_spam_messages(max_results=max_results, processed_ids=seen_ids)

    stats = {"scanned": len(emails), "candidates": 0, "notified": False}
    if not emails:
        return stats

    anthropic_client = _get_anthropic_client()
    if anthropic_client is None:
        print("⚠️  ANTHROPIC_API_KEY manquante — scan spam ignoré")
        return stats

    candidates: List[Dict[str, Any]] = []
    for email in emails:
        verdict = _classify(anthropic_client, email)
        seen_ids.add(email['gmail_message_id'])
        if verdict.get('is_likely_client') and verdict.get('confidence', 0) >= CONFIDENCE_THRESHOLD:
            candidates.append({**email, "verdict": verdict})

    _save_seen_ids(storage, seen_ids)
    stats["candidates"] = len(candidates)

    if candidates:
        _send_rescue_alert(candidates)
        stats["notified"] = True

    return stats


def _send_rescue_alert(candidates: List[Dict[str, Any]]):
    from core.email_notifier import get_email_notifier

    rows = []
    for c in candidates:
        thread_id = c.get('gmail_thread_id') or c['gmail_message_id']
        link = f"https://mail.google.com/mail/u/0/#spam/{thread_id}"
        verdict = c['verdict']
        rows.append(
            f"<div style='margin-bottom:14px;padding:10px 14px;background:#f5f5f5;"
            f"border-left:3px solid #e67e22'>"
            f"<b>{c.get('sender_name') or c.get('sender_email')}</b> — {c.get('subject')}<br>"
            f"<span style='color:#666;font-size:12px'>confiance {verdict.get('confidence', 0):.0%} — "
            f"{verdict.get('reason', '')}</span><br>"
            f"<a href='{link}'>→ Ouvrir dans le Spam</a>"
            f"</div>"
        )
    html = (
        "<p>Ces messages sont actuellement dans le Spam de info@piano-tek.com et "
        "ressemblent à de vraies demandes clients (pas déplacés automatiquement — "
        "à vérifier et sortir du spam toi-même) :</p>" + "".join(rows)
    )
    text = "Messages à vérifier dans le Spam :\n\n" + "\n".join(
        f"- {c.get('sender_name') or c.get('sender_email')} — {c.get('subject')}"
        for c in candidates
    )
    get_email_notifier().send_email(
        to_emails=['info@piano-tek.com'],
        subject=f"[PTM] {len(candidates)} message(s) à vérifier dans le Spam",
        html_content=html,
        plain_content=text,
    )
