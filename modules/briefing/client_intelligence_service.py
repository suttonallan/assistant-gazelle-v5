#!/usr/bin/env python3
"""
Client Intelligence Service - "Ma Journee" V4 — Narrative Architecture

ONE AI call per client → natural language briefing paragraph.
Parallel processing via asyncio.gather() → ~4s instead of 35s.

Flow:
  1. Fetch appointments for the day
  2. Batch-fetch all data (clients, pianos, timeline, follow-ups, estimates) in parallel
  3. For each appointment, generate ONE narrative briefing (AI) + computed flags (Python)
  4. Return flat list of briefings
"""

import os
import re
import json
import asyncio
from datetime import datetime, date as date_type
from typing import Dict, List, Optional, Any
from urllib.parse import quote

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.supabase_storage import SupabaseStorage
from modules.briefing.ai_extraction_engine import (
    compute_client_since,
    resolve_technician_name,
    TECHNICIAN_NAMES,
    ADMIN_STAFF_IDS,
)

try:
    from anthropic import Anthropic
except ImportError:
    Anthropic = None

import requests as http_requests


# ═══════════════════════════════════════════════════════════════════
# NARRATIVE PROMPT
# ═══════════════════════════════════════════════════════════════════

NARRATIVE_PROMPT = """Tu prépares un briefing pour un technicien de piano avant sa visite.
Écris 2-4 phrases en français, comme un collègue qui résume l'essentiel avant que le tech parte.

CONCENTRE-TOI SUR:
- Ce que le tech devrait SAVOIR avant d'arriver (accès, animaux, langue si anglophone, personnalité)
- Ce qui est ACTIONABLE (items à faire, pièces à apporter, choses à vérifier)
- Ce qui est INHABITUEL ou mérite attention
- L'historique pertinent (dernier tech, quand, quoi de notable)

NE MENTIONNE PAS:
- Les confirmations de RV, factures, rappels, statuts (bruit système)
- Les infos triviales ou évidentes
- Le nom de marque "Dampp-Chaser" — utilise "PLS" si pertinent

Si c'est un premier RV (aucun historique), dis-le simplement.
Si les notes sont vides ou inutiles, dis "Aucune info particulière à signaler."

CLIENT: {client_name} ({client_since})
PIANO: {piano_summary}

NOTES DE SERVICE (les plus récentes en premier):
{timeline_summary}

CONTEXTE DU RV: {appointment_context}

{feedback_context}

Retourne UNIQUEMENT ce JSON:
{{
  "narrative": "Le paragraphe de briefing en français...",
  "action_items": ["item actionable 1", "item actionable 2"]
}}"""


# Entry types to include in timeline queries
USEFUL_ENTRY_TYPES = (
    'SERVICE_ENTRY_MANUAL',
    'NOTE',
    'APPOINTMENT',
    'PIANO_MEASUREMENT',
    'USER_COMMENT',
    'ESTIMATE',
    'SERVICE_ENTRY_AUTOMATED',
)


class NarrativeBriefingService:
    """Service de briefings narratifs — V4 One-Shot Architecture"""

    def __init__(self):
        self.storage = SupabaseStorage(silent=True)
        self.anthropic = self._init_anthropic()
        self.feedback_rules = self._load_training_feedback()

    def _init_anthropic(self):
        """Initialize Anthropic client."""
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            try:
                settings = self.storage.get_data('system_settings', filters={'key': 'anthropic_api_key'})
                if settings and settings[0].get('value'):
                    api_key = settings[0]['value']
            except Exception:
                pass
        if api_key and Anthropic:
            return Anthropic(api_key=api_key)
        print("⚠️  ANTHROPIC_API_KEY manquante — briefings sans narratif IA")
        return None

    def _load_training_feedback(self) -> Dict:
        """Load Allan's corrections from ai_training_feedback."""
        rules = {}
        try:
            data = self.storage.get_data('ai_training_feedback',
                                          filters={'is_active': True},
                                          order_by='created_at.desc')
            for fb in data:
                client_id = fb.get('client_external_id')
                if client_id not in rules:
                    rules[client_id] = []
                rules[client_id].append(fb.get('corrected_value', ''))
        except Exception:
            pass
        return rules

    # ═══════════════════════════════════════════════════════════════
    # MAIN ENTRY POINT
    # ═══════════════════════════════════════════════════════════════

    async def get_daily_briefings(self, technician_id: str = None,
                                   exclude_technician_id: str = None,
                                   target_date: str = None) -> List[Dict]:
        """
        Generate narrative briefings for all appointments on a given date.
        Uses batch data fetching + parallel AI generation.
        """
        target_date = target_date or datetime.now().strftime('%Y-%m-%d')

        # 1. Fetch appointments
        appointments = await asyncio.to_thread(
            self._fetch_appointments, target_date, technician_id, exclude_technician_id
        )
        if not appointments:
            return []

        # 2. Collect all needed IDs
        client_ids = list(set(
            a['client_external_id'] for a in appointments
            if a.get('client_external_id')
        ))
        piano_ids = list(set(
            a['piano_external_id'] for a in appointments
            if a.get('piano_external_id')
        ))

        # 3. Batch fetch ALL data in parallel
        fetch_tasks = [
            asyncio.to_thread(self._batch_fetch_clients, client_ids),
            asyncio.to_thread(self._batch_fetch_pianos, client_ids),
            asyncio.to_thread(self._batch_fetch_timeline, client_ids, piano_ids),
            asyncio.to_thread(self._batch_fetch_followups, client_ids),
            asyncio.to_thread(self._batch_fetch_estimates, client_ids, piano_ids),
        ]
        # Only fetch all-day appointments if we need collaboration detection
        if technician_id:
            fetch_tasks.append(
                asyncio.to_thread(self._fetch_all_day_appointments, target_date)
            )

        results = await asyncio.gather(*fetch_tasks)

        clients_data = results[0]
        pianos_data = results[1]
        timeline_data = results[2]
        followups_data = results[3]
        estimates_data = results[4]
        all_day_appts = results[5] if technician_id else []

        # 4. Generate narrative briefings in PARALLEL
        gen_tasks = []
        for appt in appointments:
            cid = appt.get('client_external_id')
            if not cid:
                continue
            gen_tasks.append(self._generate_one_briefing(
                appt=appt,
                client=clients_data.get(cid, {}),
                pianos=pianos_data.get(cid, []),
                timeline=timeline_data.get(cid, []),
                followups=followups_data.get(cid, []),
                estimates=estimates_data.get(cid, []),
                technician_id=technician_id,
                all_day_appts=all_day_appts,
            ))

        briefings = await asyncio.gather(*gen_tasks)
        return [b for b in briefings if b]

    # ═══════════════════════════════════════════════════════════════
    # PER-CLIENT BRIEFING GENERATION
    # ═══════════════════════════════════════════════════════════════

    async def _generate_one_briefing(self, appt: Dict, client: Dict,
                                      pianos: List[Dict], timeline: List[Dict],
                                      followups: List[Dict], estimates: List[Dict],
                                      technician_id: str, all_day_appts: List[Dict]) -> Optional[Dict]:
        """Generate a narrative briefing for ONE appointment."""
        try:
            cid = appt.get('client_external_id', '')

            # ── Match piano for this appointment ──
            piano_id_from_appt = appt.get('piano_external_id')
            piano = {}
            if piano_id_from_appt and pianos:
                piano = next((p for p in pianos if p.get('external_id') == piano_id_from_appt), {})
            if not piano and pianos:
                piano = self._match_piano_from_context(pianos, appt)

            # ── Python-computed flags ──
            client_name = (
                client.get('company_name')
                or f"{client.get('first_name', '')} {client.get('last_name', '')}".strip()
                or 'Client'
            )

            # Client since
            client_since = compute_client_since(
                [{'date': t.get('occurred_at', '')[:10]} for t in timeline]
            )

            # Piano label
            piano_label = self._compute_piano_label(piano)

            # PLS badge
            has_pls = piano.get('dampp_chaser_installed', False)

            # Language detection (simple heuristic, not AI)
            language = self._detect_language_from_notes(timeline)

            # Institution detection
            institution_keywords = ['place des arts', 'vincent', 'indy', 'orford', 'uqam', 'mcgill',
                                    'conservatoire', 'école', 'université', 'collège', 'smcq', 'osm']
            is_institution = any(kw in client_name.lower() for kw in institution_keywords)
            if is_institution:
                language = None  # Not relevant for institutions

            # Collaboration detection
            collaboration = []
            if technician_id and all_day_appts:
                for other in all_day_appts:
                    if (other.get('client_external_id') == cid
                            and other.get('technicien', '') != technician_id
                            and other.get('technicien')):
                        collaboration.append({
                            'technician_name': resolve_technician_name(other['technicien']),
                            'time': (other.get('appointment_time', '') or '')[:5],
                        })

            # Estimate summary
            estimate_items = self._format_estimates(estimates)

            # ── Generate narrative via AI ──
            narrative = "Aucune info particulière à signaler."
            action_items = []

            if self.anthropic:
                narrative, action_items = await asyncio.to_thread(
                    self._call_narrative_ai,
                    client_name=client_name,
                    client_since=client_since or "nouveau client",
                    piano_summary=piano_label or "Piano non spécifié",
                    timeline=timeline,
                    appt=appt,
                    feedback_notes=self.feedback_rules.get(cid, []),
                )

            # ── Build final briefing ──
            return {
                "client_id": cid,
                "client_name": client_name,
                "client_since": client_since,
                "narrative": narrative,
                "action_items": action_items,
                "flags": {
                    "language": language,
                    "pls": has_pls,
                    "piano_label": piano_label,
                },
                "piano": {
                    "make": piano.get('make', ''),
                    "model": piano.get('model', ''),
                    "type": piano.get('type', ''),
                    "year": piano.get('year', 0),
                    "age_years": (datetime.now().year - piano['year']) if piano.get('year') and piano['year'] > 1800 else 0,
                    "dampp_chaser": has_pls,
                },
                "appointment": {
                    "id": appt.get('external_id'),
                    "time": (appt.get('appointment_time', '') or '')[:5],
                    "title": appt.get('title', ''),
                    "description": appt.get('description', ''),
                    "technician_id": appt.get('technicien'),
                    "collaboration": collaboration,
                },
                "follow_ups": followups,
                "estimate_items": estimate_items,
                "generated_at": datetime.now().isoformat(),
            }

        except Exception as e:
            print(f"❌ Erreur briefing {appt.get('client_external_id', '?')}: {e}")
            import traceback
            traceback.print_exc()
            return None

    # ═══════════════════════════════════════════════════════════════
    # AI NARRATIVE GENERATION
    # ═══════════════════════════════════════════════════════════════

    def _call_narrative_ai(self, client_name: str, client_since: str,
                            piano_summary: str, timeline: List[Dict],
                            appt: Dict, feedback_notes: List[str]) -> tuple:
        """Call Claude Haiku to generate a narrative briefing. Returns (narrative, action_items)."""
        today_str = date_type.today().isoformat()

        # Format timeline for prompt (skip noise, keep last 15 useful entries)
        timeline_lines = []
        for entry in timeline[:30]:  # Look at more, keep 15
            entry_date = (entry.get('occurred_at', '') or '')[:10]
            if entry_date >= today_str:
                continue

            # Skip admin staff entries
            user_id = entry.get('user_id', '')
            if user_id in ADMIN_STAFF_IDS:
                continue

            text = f"{entry.get('title', '')} {entry.get('description', '')}".strip()
            if not text or len(text) < 10:
                continue

            tech_name = resolve_technician_name(user_id)
            entry_type = entry.get('entry_type', '')
            timeline_lines.append(f"[{entry_date}] ({tech_name or 'Tech'}, {entry_type}) {text[:300]}")

            if len(timeline_lines) >= 15:
                break

        timeline_summary = "\n".join(timeline_lines) if timeline_lines else "(Aucun historique)"

        # Appointment context
        appt_context = f"{appt.get('title', '')} {appt.get('description', '')} {appt.get('notes', '')}".strip()
        if not appt_context:
            appt_context = "Accord standard"

        # Feedback context (Allan's corrections)
        feedback_context = ""
        if feedback_notes:
            feedback_context = "CORRECTIONS D'ALLAN (prioritaires, intègre-les au briefing):\n"
            for note in feedback_notes[:5]:
                if note:
                    feedback_context += f"- {note}\n"

        prompt = NARRATIVE_PROMPT.format(
            client_name=client_name,
            client_since=client_since,
            piano_summary=piano_summary,
            timeline_summary=timeline_summary,
            appointment_context=appt_context,
            feedback_context=feedback_context,
        )

        try:
            response = self.anthropic.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=500,
                temperature=0.2,
                system="Tu retournes UNIQUEMENT du JSON valide sans markdown. Sois concis et utile.",
                messages=[{"role": "user", "content": prompt}],
            )

            raw = response.content[0].text.strip()
            # Clean markdown fences if present
            if raw.startswith("```"):
                raw = re.sub(r'^```(?:json)?\s*', '', raw)
                raw = re.sub(r'\s*```$', '', raw)

            result = json.loads(raw)
            narrative = result.get('narrative', 'Aucune info particulière à signaler.')
            action_items = result.get('action_items', [])
            # Filter empty items
            action_items = [item for item in action_items if item and len(item) > 3]
            return narrative, action_items

        except Exception as e:
            print(f"⚠️  Narrative AI error: {e}")
            return "Aucune info particulière à signaler.", []

    # ═══════════════════════════════════════════════════════════════
    # PYTHON-COMPUTED FLAGS
    # ═══════════════════════════════════════════════════════════════

    def _compute_piano_label(self, piano: Dict) -> str:
        """Build a human-readable piano label. E.g. 'Yamaha U1 droit (2015, 11 ans)'"""
        if not piano:
            return ""

        make = piano.get('make', '')
        model = piano.get('model', '')
        ptype = piano.get('type', '')
        year = piano.get('year', 0)

        has_make = make and make.lower() != 'unknown'
        has_model = model and model.lower() not in ('none', 'unknown', '')

        type_label = {
            'UPRIGHT': 'droit', 'GRAND': 'à queue',
            'BABY_GRAND': 'petit queue',
        }.get(ptype, '')

        if has_make:
            label = make
            if has_model:
                label += f" {model}"
            if type_label:
                label += f" {type_label}"
        elif type_label:
            label = f"Piano {type_label}"
        else:
            return ""

        if year and year > 1800:
            age = datetime.now().year - year
            label += f" ({year}, {age} ans)"

        return label

    def _detect_language_from_notes(self, timeline: List[Dict]) -> Optional[str]:
        """Simple heuristic: detect EN/BI from timeline text. Returns None if FR (default)."""
        all_text = " ".join(
            f"{t.get('title', '')} {t.get('description', '')}"
            for t in timeline[:15]
        ).lower()

        if not all_text.strip():
            return None

        en_words = ['the ', ' and ', 'please', 'thank', 'hello', 'good morning',
                     'call me', 'don\'t', 'won\'t', 'can\'t', 'should']
        fr_words = ['le ', ' la ', ' les ', ' et ', 'merci', 'bonjour', 'svp',
                     'rendez-vous', 'veuillez', 'prochaine']

        en_count = sum(1 for w in en_words if w in all_text)
        fr_count = sum(1 for w in fr_words if w in all_text)

        if en_count > fr_count + 2:
            return "EN"
        if en_count > 0 and fr_count > 0 and en_count >= 2:
            return "BI"
        return None  # FR is default, don't flag it

    def _format_estimates(self, estimates: List[Dict]) -> List[Dict]:
        """Format estimate entries for display."""
        items = []
        seen_ids = set()
        estimate_noise = [
            'estimate created', 'devis créé', 'soumission créée',
            'estimate sent', 'devis envoyé', 'soumission envoyée',
            'estimate #', 'devis #', 'soumission #', 'estimation #',
            'created for', 'sent to', 'envoyé à',
        ]
        for entry in estimates:
            est_id = entry.get('estimate_id')
            if est_id in seen_ids:
                continue
            seen_ids.add(est_id)

            text = (entry.get('description') or entry.get('title') or '').strip()
            text_lower = text.lower()
            if not text or len(text) < 15 or any(noise in text_lower for noise in estimate_noise):
                text = 'Soumission'

            items.append({
                'date': (entry.get('occurred_at') or '')[:10],
                'text': text[:300],
                'estimate_id': est_id,
            })
        return items

    # ═══════════════════════════════════════════════════════════════
    # BATCH DATA FETCHING
    # ═══════════════════════════════════════════════════════════════

    def _supabase_get(self, url: str) -> list:
        """Helper: GET from Supabase REST API."""
        try:
            resp = http_requests.get(url, headers=self.storage._get_headers(), timeout=10)
            if resp.status_code == 200:
                return resp.json()
        except Exception as e:
            print(f"⚠️  Supabase GET error: {e}")
        return []

    def _fetch_appointments(self, target_date: str, technician_id: str = None,
                             exclude_technician_id: str = None) -> List[Dict]:
        """Fetch appointments for a given date."""
        filters = {'appointment_date': target_date}
        if technician_id:
            filters['technicien'] = technician_id
        try:
            appointments = self.storage.get_data('gazelle_appointments',
                                                  filters=filters,
                                                  order_by='appointment_time.asc')
        except Exception:
            appointments = []

        if exclude_technician_id:
            appointments = [a for a in appointments if a.get('technicien') != exclude_technician_id]

        return appointments

    def _fetch_all_day_appointments(self, target_date: str) -> List[Dict]:
        """Fetch ALL appointments for a day (for collaboration detection)."""
        try:
            return self.storage.get_data('gazelle_appointments',
                                          filters={'appointment_date': target_date},
                                          order_by='appointment_time.asc')
        except Exception:
            return []

    def _batch_fetch_clients(self, client_ids: List[str]) -> Dict[str, Dict]:
        """Fetch all clients in one query. Returns {client_id: client_data}."""
        if not client_ids:
            return {}
        ids_csv = ",".join(quote(cid) for cid in client_ids)
        url = f"{self.storage.api_url}/gazelle_clients?external_id=in.({ids_csv})"
        data = self._supabase_get(url)
        return {c['external_id']: c for c in data if c.get('external_id')}

    def _batch_fetch_pianos(self, client_ids: List[str]) -> Dict[str, List[Dict]]:
        """Fetch all pianos for all clients. Returns {client_id: [pianos]}."""
        if not client_ids:
            return {}
        ids_csv = ",".join(quote(cid) for cid in client_ids)
        url = f"{self.storage.api_url}/gazelle_pianos?client_external_id=in.({ids_csv})"
        data = self._supabase_get(url)
        result = {}
        for p in data:
            cid = p.get('client_external_id')
            if cid:
                result.setdefault(cid, []).append(p)
        return result

    def _batch_fetch_timeline(self, client_ids: List[str], piano_ids: List[str]) -> Dict[str, List[Dict]]:
        """Fetch timeline entries for all clients + pianos. Returns {client_id: [entries]}."""
        if not client_ids:
            return {}

        types_csv = ",".join(USEFUL_ENTRY_TYPES)
        result = {}

        # Fetch by client_id
        ids_csv = ",".join(quote(cid) for cid in client_ids)
        url = (
            f"{self.storage.api_url}/gazelle_timeline_entries?select=*"
            f"&client_id=in.({ids_csv})"
            f"&entry_type=in.({types_csv})"
            f"&order=occurred_at.desc"
            f"&limit=200"
        )
        client_entries = self._supabase_get(url)
        for entry in client_entries:
            cid = entry.get('client_id')
            if cid:
                result.setdefault(cid, []).append(entry)

        # Fetch by piano_id (may catch entries linked to piano but not client)
        if piano_ids:
            piano_csv = ",".join(quote(pid) for pid in piano_ids)
            url = (
                f"{self.storage.api_url}/gazelle_timeline_entries?select=*"
                f"&piano_id=in.({piano_csv})"
                f"&entry_type=in.({types_csv})"
                f"&order=occurred_at.desc"
                f"&limit=100"
            )
            piano_entries = self._supabase_get(url)
            # Add piano entries to the correct client (deduplicate by external_id)
            seen_ids = {e.get('external_id') for entries in result.values() for e in entries if e.get('external_id')}
            for entry in piano_entries:
                if entry.get('external_id') in seen_ids:
                    continue
                cid = entry.get('client_id')
                if cid:
                    result.setdefault(cid, []).append(entry)

        # Sort each client's entries by date desc
        for cid in result:
            result[cid].sort(key=lambda e: e.get('occurred_at', ''), reverse=True)

        return result

    def _batch_fetch_followups(self, client_ids: List[str]) -> Dict[str, List[Dict]]:
        """Fetch open follow-ups for all clients. Returns {client_id: [items]}."""
        if not client_ids:
            return {}
        ids_csv = ",".join(quote(cid) for cid in client_ids)
        url = (
            f"{self.storage.api_url}/follow_up_items?"
            f"client_external_id=in.({ids_csv})"
            f"&status=eq.open"
            f"&order=detected_at.desc"
        )
        data = self._supabase_get(url)
        result = {}
        for item in data:
            cid = item.get('client_external_id')
            if cid:
                result.setdefault(cid, []).append({
                    "id": item.get('id'),
                    "category": item.get('category'),
                    "description": item.get('description'),
                    "source_citation": item.get('source_citation'),
                    "detected_at": item.get('detected_at'),
                })
        return result

    def _batch_fetch_estimates(self, client_ids: List[str], piano_ids: List[str]) -> Dict[str, List[Dict]]:
        """Fetch estimate-linked timeline entries. Returns {client_id: [entries]}."""
        if not client_ids:
            return {}
        ids_csv = ",".join(quote(cid) for cid in client_ids)
        url = (
            f"{self.storage.api_url}/gazelle_timeline_entries?select=*"
            f"&client_id=in.({ids_csv})"
            f"&estimate_id=not.is.null"
            f"&order=occurred_at.desc"
            f"&limit=30"
        )
        data = self._supabase_get(url)
        result = {}
        for entry in data:
            cid = entry.get('client_id')
            if cid:
                result.setdefault(cid, []).append(entry)
        return result

    # ═══════════════════════════════════════════════════════════════
    # PIANO MATCHING (unchanged from V3)
    # ═══════════════════════════════════════════════════════════════

    def _match_piano_from_context(self, pianos: List[Dict], appt: Dict) -> Dict:
        """Find the piano matching the appointment based on description/title."""
        if not pianos:
            return {}
        if len(pianos) == 1:
            return pianos[0]

        search_text = " ".join([
            appt.get('title', ''), appt.get('description', ''), appt.get('notes', ''),
        ]).lower()

        if not search_text.strip():
            return pianos[0]

        for piano in pianos:
            make = (piano.get('make') or '').lower()
            if make and len(make) > 2 and make in search_text:
                return piano

        for piano in pianos:
            model = (piano.get('model') or '').lower()
            if model and len(model) > 2 and model in search_text:
                return piano

        if 'queue' in search_text or 'grand' in search_text:
            for piano in pianos:
                ptype = (piano.get('type') or '').lower()
                if ptype in ['grand', 'queue', 'baby grand']:
                    return piano

        return pianos[0]

    # ═══════════════════════════════════════════════════════════════
    # FOLLOW-UP RESOLUTION (kept for API endpoint)
    # ═══════════════════════════════════════════════════════════════

    def resolve_follow_up(self, item_id: str, resolved_by: str = None,
                           resolution_note: str = None) -> bool:
        """Mark a follow-up as resolved."""
        try:
            self.storage.client.table('follow_up_items').update({
                'status': 'resolved',
                'resolved_at': datetime.now().isoformat(),
                'resolved_by': resolved_by,
                'resolution_note': resolution_note,
                'updated_at': datetime.now().isoformat(),
            }).eq('id', item_id).execute()
            return True
        except Exception as e:
            print(f"❌ Erreur résolution follow-up: {e}")
            return False

    # ═══════════════════════════════════════════════════════════════
    # SINGLE CLIENT BRIEFING (for /client/{id} endpoint)
    # ═══════════════════════════════════════════════════════════════

    async def generate_single_briefing(self, client_external_id: str) -> Dict:
        """Generate a briefing for a single client (no appointment context)."""
        client = await asyncio.to_thread(
            lambda: (self.storage.get_data('gazelle_clients', filters={'external_id': client_external_id}) or [None])[0]
        )
        if not client:
            return {"error": "Client non trouvé"}

        pianos = await asyncio.to_thread(
            lambda: self.storage.get_data('gazelle_pianos', filters={'client_external_id': client_external_id})
        )

        timeline = await asyncio.to_thread(
            self._batch_fetch_timeline, [client_external_id], []
        )

        followups = await asyncio.to_thread(
            self._batch_fetch_followups, [client_external_id]
        )

        estimates = await asyncio.to_thread(
            self._batch_fetch_estimates, [client_external_id], []
        )

        fake_appt = {
            'client_external_id': client_external_id,
            'piano_external_id': pianos[0].get('external_id') if pianos else None,
            'external_id': None,
            'appointment_time': '',
            'title': '',
            'description': '',
            'notes': '',
            'technicien': '',
        }

        result = await self._generate_one_briefing(
            appt=fake_appt,
            client=client,
            pianos=pianos or [],
            timeline=timeline.get(client_external_id, []),
            followups=followups.get(client_external_id, []),
            estimates=estimates.get(client_external_id, []),
            technician_id=None,
            all_day_appts=[],
        )
        return result or {"error": "Erreur de génération"}


# ═══════════════════════════════════════════════════════════════════
# BACKWARD COMPATIBILITY — save_feedback (used by briefing_routes.py)
# ═══════════════════════════════════════════════════════════════════

def save_feedback(client_id: str, category: str, field_name: str,
                  original_value: str, corrected_value: str,
                  created_by: str = "asutton@piano-tek.com") -> bool:
    storage = SupabaseStorage(silent=True)
    record = {
        'client_external_id': client_id,
        'category': category,
        'field_name': field_name,
        'original_value': original_value,
        'corrected_value': corrected_value,
        'created_by': created_by,
        'is_active': True,
    }
    try:
        storage.insert_data('ai_training_feedback', record)
        return True
    except Exception as e:
        print(f"❌ Erreur sauvegarde feedback: {e}")
        return False


# Keep old class name as alias for backward compatibility during transition
ClientIntelligenceService = NarrativeBriefingService
