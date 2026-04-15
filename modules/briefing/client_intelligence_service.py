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
    fetch_earliest_client_date,
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
- Le piano spécifique: numéro de série, salle/emplacement, diapason habituel (440 ou 442)
- Ce que le tech devrait SAVOIR avant d'arriver (accès, langue si anglophone, personnalité)
- L'historique pertinent (dernier tech, quand)
- Ce qui est INHABITUEL ou mérite attention

POUR LES INSTITUTIONS (Place des Arts, UQAM, Vincent-d'Indy, Orford, OSM, etc.):
- NE PAS suggérer de faire des travaux de réglage/réparation. Le RV est un accord standard.
- Si des choses ont été notées lors de visites précédentes, les mentionner simplement : "Des choses ont été notées : [liste]" — sans dire de les corriger.
- NE PAS mentionner le nombre total de pianos du client.
- "avant Xh" signifie que l'accord doit être TERMINÉ à cette heure, pas qu'il faut arriver avant.

NE MENTIONNE PAS:
- Les confirmations de RV, factures, rappels, statuts (bruit système)
- Les infos triviales ou évidentes
- Le nom de marque "Dampp-Chaser" — utilise "PLS" si pertinent
- Le nombre de pianos d'un client institutionnel

NE JAMAIS INVENTER:
- Des codes d'accès, mots de passe, numéros de téléphone, adresses
- Des diapasons (440/442) sans source dans les préférences client
- Des noms de contact sans source dans les notes
- Si une info n'est pas explicitement dans les données fournies, NE PAS l'inclure

RÈGLES CRITIQUES:
- Utilise la DESCRIPTION DU RV pour identifier le bon piano (numéro de série, salle). Ne pas deviner.
- DIAPASON — deux cas très différents:
  * INSTITUTION (PDA, OSM, UQAM, etc.) : le diapason est une RÈGLE FIXE par salle. Lis les préférences client. Dire "Accord à 440Hz" ou "Accord à 442Hz" selon la salle.
  * CLIENT PRIVÉ : si un diapason apparaît dans l'historique (timeline), c'est une OBSERVATION, pas une exigence. Dire "Dernier accord à 441.25Hz" — jamais "Accord à 441.25Hz" comme si c'était une instruction.
- Un client institutionnel peut avoir plusieurs LIEUX distincts (ex: Maison Symphonique, Espace OSM, Salle E). Chaque lieu a ses propres accès, contacts, et pianos. NE PAS mélanger les infos d'un lieu avec un autre. Utilise SEULEMENT les infos pertinentes au lieu du RV.
- Si les notes mentionnent un contact (ex: "Béatrice pour accès Espace OSM"), n'inclure ce contact QUE si le RV est à cet endroit spécifique.

Si c'est un premier RV pour un CLIENT PRIVÉ (aucun historique), dis-le simplement.
Pour les INSTITUTIONS, ne jamais dire "premier RV" — ces pianos sont accordés régulièrement.
Si les notes sont vides ou inutiles, dis "Aucune info particulière à signaler."

CLIENT: {client_name} ({client_since})
PIANO PRINCIPAL: {piano_summary}
{all_pianos_context}
NOTES PERSONNELLES DU CLIENT:
{personal_notes}

PRÉFÉRENCES DU CLIENT:
{preference_notes}

NOTES DU PIANO:
{piano_notes}

NOTES DE SERVICE (les plus récentes en premier):
{timeline_summary}

{soumissions_context}
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
        """Load Allan's corrections from ai_training_feedback.

        Notes with client_external_id='__GLOBAL__' apply to ALL clients.
        Other notes apply only to the specific client.
        """
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
            asyncio.to_thread(self._batch_fetch_past_appointments, client_ids),
            # Nouveau : fetch live Gazelle des vraies soumissions par client
            asyncio.to_thread(self._batch_fetch_gazelle_estimates, client_ids),
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
        past_appts_data = results[5]
        gazelle_estimates_data = results[6]
        all_day_appts = results[7] if technician_id else []

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
                past_appointments=past_appts_data.get(cid, []),
                followups=followups_data.get(cid, []),
                estimates=estimates_data.get(cid, []),
                gazelle_estimates=gazelle_estimates_data.get(cid, []),
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
                                      past_appointments: List[Dict],
                                      followups: List[Dict], estimates: List[Dict],
                                      gazelle_estimates: List[Dict],
                                      technician_id: str, all_day_appts: List[Dict]) -> Optional[Dict]:
        """Generate a narrative briefing for ONE appointment."""
        try:
            cid = appt.get('client_external_id', '')

            # ── Enrichir le RV avec les infos de la demande PDA si disponible ──
            pda_request = self._fetch_pda_request_for_appointment(appt.get('external_id'))
            if pda_request:
                # Injecter salle, piano, diapason dans la description du RV
                pda_room = pda_request.get('room', '')
                pda_piano = pda_request.get('piano', '')
                pda_diapason = pda_request.get('diapason', '')
                pda_time = pda_request.get('time', '')
                pda_for_who = pda_request.get('for_who', '')

                pda_context = []
                if pda_room:
                    pda_context.append(f"Salle {pda_room}")
                if pda_piano:
                    pda_context.append(pda_piano)
                if pda_diapason:
                    pda_context.append(f"{pda_diapason}Hz")
                if pda_time:
                    pda_context.append(pda_time)
                if pda_for_who:
                    pda_context.append(f"pour {pda_for_who}")

                # Enrichir la description du RV pour le matching et le prompt
                existing_desc = appt.get('description', '') or ''
                appt['description'] = f"{existing_desc} | PDA: {', '.join(pda_context)}".strip(' |')

            # ── Match piano(s) for this appointment ──
            piano_id_from_appt = appt.get('piano_external_id')
            piano = {}
            if piano_id_from_appt and pianos:
                piano = next((p for p in pianos if p.get('external_id') == piano_id_from_appt), {})
            if not piano and pianos:
                piano = self._match_piano_from_context(pianos, appt)

            # All pianos for this client (for narrative context)
            all_pianos_list = pianos if len(pianos) > 1 else []

            # ── Python-computed flags ──
            client_name = (
                client.get('company_name')
                or f"{client.get('first_name', '')} {client.get('last_name', '')}".strip()
                or 'Client'
            )

            # Client since — cherche dans timeline, appointments ET created_at
            client_created_at = client.get('created_at', '')
            client_since = fetch_earliest_client_date(
                self.storage, cid, client_created_at
            )
            if client_since is None:
                # Fallback sur le batch existant
                client_since = compute_client_since(
                    [{'date': t.get('occurred_at', '')[:10]} for t in timeline]
                )

            # Piano label (mention count if multiple)
            piano_label = self._compute_piano_label(piano)
            if len(pianos) > 1:
                piano_label = f"{piano_label} (+{len(pianos) - 1} autre{'s' if len(pianos) > 2 else ''})"

            # PLS badge (default False if data missing)
            has_pls = bool(piano.get('dampp_chaser_installed'))

            # Language detection: Gazelle locale field > client notes > timeline heuristic
            language = self._detect_language_from_locale(client) or self._detect_language_from_client(client)

            # Dog name detection
            dog_name = self._detect_dog_from_notes(timeline)

            # Children names detection
            children_names = self._detect_children_from_notes(timeline)

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

            # Estimate summary (timeline-based, legacy)
            estimate_items = self._format_estimates(estimates)

            # ── Soumissions Gazelle live : enrichir avec "likely_done" ──
            # Allan, 2026-04-14: "Si le travail recommandé a été fait ensuite
            # ça serait suffisant." Inférence : un RV COMPLETE après estimatedOn
            # sur le même client (idéalement même piano) → probablement fait.
            gazelle_estimates_enriched = []
            for est_summary in gazelle_estimates or []:
                likely_done = False
                est_date = est_summary.get("estimated_on") or ""
                est_piano = est_summary.get("piano_id")
                if est_date:
                    for past_appt in past_appointments or []:
                        if (past_appt.get("status") or "").upper() not in ("COMPLETE", "COMPLETED"):
                            continue
                        appt_date = (past_appt.get("appointment_date") or "")[:10]
                        if appt_date <= est_date:
                            continue
                        # Bonus : match piano si dispo
                        if est_piano and past_appt.get("piano_external_id"):
                            if past_appt["piano_external_id"] == est_piano:
                                likely_done = True
                                break
                        else:
                            likely_done = True
                            break
                est_summary["likely_done"] = likely_done
                gazelle_estimates_enriched.append(est_summary)

            # ── Generate narrative via AI ──
            narrative = "Aucune info particulière à signaler."
            action_items = []

            if self.anthropic:
                # Enrichir piano_summary avec SN et salle pour l'IA
                piano_detail = piano_label or "Piano non spécifié"
                if piano.get('serial_number'):
                    piano_detail += f" (SN {piano['serial_number']})"
                if piano.get('location'):
                    piano_detail += f" — {piano['location']}"

                narrative, action_items = await asyncio.to_thread(
                    self._call_narrative_ai,
                    client_name=client_name,
                    client_since=client_since or "nouveau client",
                    piano_summary=piano_detail,
                    timeline=timeline,
                    past_appointments=past_appointments,
                    appt=appt,
                    feedback_notes=self.feedback_rules.get('__GLOBAL__', []) + self.feedback_rules.get(cid, []),
                    personal_notes=client.get('personal_notes', '') or '',
                    preference_notes=client.get('preference_notes', '') or '',
                    piano_notes=piano.get('notes', '') or '',
                    all_pianos=all_pianos_list,
                    gazelle_estimates=gazelle_estimates_enriched,
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
                    "dog_name": dog_name,
                    "children_names": children_names,
                },
                "piano": {
                    "make": piano.get('make', ''),
                    "model": piano.get('model', ''),
                    "type": piano.get('type', ''),
                    "year": piano.get('year', 0),
                    "age_years": (datetime.now().year - piano['year']) if piano.get('year') and piano['year'] > 1800 else 0,
                    "dampp_chaser": has_pls or False,
                },
                "all_pianos": [
                    {
                        "make": p.get('make', ''),
                        "model": p.get('model', ''),
                        "type": p.get('type', ''),
                        "serial_number": p.get('serial_number', ''),
                        "location": p.get('location', ''),
                        "dampp_chaser": bool(p.get('dampp_chaser_installed')),
                    }
                    for p in pianos
                ] if len(pianos) > 1 else [],
                "appointment": {
                    "id": appt.get('external_id'),
                    "time": (appt.get('appointment_time', '') or '')[:5],
                    "title": appt.get('title', ''),
                    "description": appt.get('description', ''),
                    "technician_id": appt.get('technicien'),
                    "technician_name": resolve_technician_name(appt.get('technicien', '')),
                    "collaboration": collaboration,
                },
                "follow_ups": followups,
                "estimate_items": estimate_items,
                "gazelle_estimates": gazelle_estimates_enriched,
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
                            past_appointments: List[Dict],
                            appt: Dict, feedback_notes: List[str],
                            personal_notes: str = "", preference_notes: str = "",
                            piano_notes: str = "",
                            all_pianos: List[Dict] = None,
                            gazelle_estimates: List[Dict] = None) -> tuple:
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

        # Add past appointments (contain rich descriptions/notes not in timeline)
        for pa in past_appointments[:10]:
            pa_date = (pa.get('appointment_date', '') or '')[:10]
            if pa_date >= today_str:
                continue
            desc = (pa.get('description', '') or '').strip()
            notes = (pa.get('notes', '') or '').strip()
            # Only add if there's actual content beyond the client name
            text = f"{desc} {notes}".strip()
            if not text or len(text) < 15 or text == client_name:
                continue
            tech_name = resolve_technician_name(pa.get('technicien', ''))
            timeline_lines.append(f"[{pa_date}] ({tech_name or 'Tech'}, RV) {text[:300]}")

        # Sort by date descending and keep top 15
        timeline_lines.sort(key=lambda l: l[:12], reverse=True)
        timeline_lines = timeline_lines[:15]

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

        # Build all pianos context
        all_pianos_context = ""
        if all_pianos and len(all_pianos) > 1:
            lines = []
            for p in all_pianos:
                label = p.get('make', 'Piano')
                if p.get('model'):
                    label += f" {p['model']}"
                if p.get('serial_number'):
                    label += f" (SN {p['serial_number']})"
                loc = p.get('location') or p.get('notes') or ''
                if loc:
                    label += f" — {loc[:80]}"
                pls = " [PLS]" if p.get('dampp_chaser_installed') else ""
                lines.append(f"  - {label}{pls}")
            all_pianos_context = f"TOUS LES PIANOS DU CLIENT ({len(all_pianos)}):\n" + "\n".join(lines) + "\nIMPORTANT: Mentionne TOUS les pianos dans le briefing, pas seulement le premier.\n"

        # Build soumissions context (Gazelle live)
        soumissions_context = ""
        if gazelle_estimates:
            # Garder les 5 plus récentes (déjà triées par date desc)
            recent = gazelle_estimates[:5]
            lines = []
            for est in recent:
                number = est.get("number", "?")
                est_date = est.get("estimated_on") or "?"
                total = est.get("total_dollars") or "?"
                items = est.get("main_items") or []
                items_str = " + ".join(items[:3]) if items else "contenu non détaillé"
                archived = est.get("is_archived")
                done = est.get("likely_done")
                if done:
                    status = "travaux probablement faits (RV complété après)"
                elif archived:
                    status = "archivée"
                else:
                    status = "active"
                lines.append(
                    f"  - Soumission #{number} ({est_date}) — {total}$ — "
                    f"{items_str} — {status}"
                )
            soumissions_context = (
                "SOUMISSIONS GAZELLE POUR CE CLIENT:\n"
                + "\n".join(lines)
                + "\nIMPORTANT: Si une soumission existe, mentionne-la en UNE phrase courte "
                "(pas plus). Format: 'Soumission de [mois année] — [items principaux] — [statut].' "
                "Si le travail a probablement été fait (likely_done), dis-le clairement. "
                "Ne liste pas toutes les soumissions — mentionne la plus pertinente pour le RV d'aujourd'hui.\n"
            )

        prompt = NARRATIVE_PROMPT.format(
            client_name=client_name,
            client_since=client_since,
            piano_summary=piano_summary,
            all_pianos_context=all_pianos_context,
            personal_notes=personal_notes or "(Aucune)",
            preference_notes=preference_notes or "(Aucune)",
            piano_notes=piano_notes or "(Aucune)",
            timeline_summary=timeline_summary,
            appointment_context=appt_context,
            feedback_context=feedback_context,
            soumissions_context=soumissions_context,
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

    def _detect_language_from_locale(self, client: Dict) -> Optional[str]:
        """Check the locale field from Gazelle (most reliable source)."""
        locale = (client.get('locale') or '').lower()
        if not locale:
            return None
        if locale.startswith('en'):
            return "EN"
        if locale.startswith('fr'):
            return None  # FR is default, no flag needed
        return None

    def _detect_language_from_client(self, client: Dict) -> Optional[str]:
        """Check personal_notes and preference_notes for explicit language indication."""
        text = f"{client.get('personal_notes', '') or ''} {client.get('preference_notes', '') or ''}".lower()
        if not text.strip():
            return None

        en_markers = ['anglophone', 'english', 'english speaking', 'speaks english', 'parle anglais', 'anglo']
        bi_markers = ['bilingue', 'bilingual', 'fr/en', 'en/fr']
        fr_markers = ['francophone', 'french', 'speaks french', 'parle français', 'parle francais', 'unilingue français', 'unilingue francais']

        for marker in bi_markers:
            if marker in text:
                return "BI"
        for marker in en_markers:
            if marker in text:
                return "EN"
        for marker in fr_markers:
            if marker in text:
                return None  # FR is default, no flag needed
        return None


    def _detect_dog_from_notes(self, timeline: List[Dict]) -> Optional[str]:
        """Extract dog name from timeline notes. Returns name or None."""
        all_text = " ".join(
            f"{t.get('title', '')} {t.get('description', '')}"
            for t in timeline
        )
        if not all_text.strip():
            return None

        patterns = [
            r'chien\s*[:=]\s*([A-ZÀ-Üa-zà-ÿ][a-zà-ÿ]+)',
            r'chien\s+(?:nommé|appelé|s\'appelle)\s+([A-ZÀ-Üa-zà-ÿ][a-zà-ÿ]+)',
            r'chien\s+([A-ZÀ-Ü][a-zà-ÿ]+)',           # "Chien Tom" — format naturel
            r'dog\s*[:=]\s*([A-Za-z][a-z]+)',
            r'🐕\s*[:=]?\s*([A-ZÀ-Üa-zà-ÿ][a-zà-ÿ]+)',
            r'🐶\s*[:=]?\s*([A-ZÀ-Üa-zà-ÿ][a-zà-ÿ]+)',
        ]
        for pattern in patterns:
            match = re.search(pattern, all_text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return None

    def _detect_children_from_notes(self, timeline: List[Dict]) -> Optional[str]:
        """Extract children names from timeline notes. Returns comma-separated names or None."""
        all_text = " ".join(
            f"{t.get('title', '')} {t.get('description', '')}"
            for t in timeline
        )
        if not all_text.strip():
            return None

        names = []
        patterns = [
            # "enfants: Sophie, Lucas" or "enfants = Sophie et Lucas"
            r'enfants?\s*[:=]\s*([A-ZÀ-Üa-zà-ÿ][\w\sà-ÿ,&et]+)',
            # "children: Sophie, Lucas"
            r'children\s*[:=]\s*([A-Za-z][\w\s,&and]+)',
            # "fils: Lucas" / "fille: Sophie"
            r'(?:fils|fille|son|daughter)\s*[:=]\s*([A-ZÀ-Üa-zà-ÿ][a-zà-ÿ]+)',
            # "fils nommé Lucas" / "fille nommée Sophie"
            r'(?:fils|fille)\s+(?:nommée?|appelée?|s\'appelle)\s+([A-ZÀ-Üa-zà-ÿ][a-zà-ÿ]+)',
            # "👧: Sophie" / "👦: Lucas"
            r'[👧👦👶🧒]\s*[:=]?\s*([A-ZÀ-Üa-zà-ÿ][a-zà-ÿ]+)',
        ]
        for pattern in patterns:
            match = re.search(pattern, all_text, re.IGNORECASE)
            if match:
                raw = match.group(1).strip()
                # Split on common separators: comma, &, "et", "and"
                parts = re.split(r'\s*[,&]\s*|\s+et\s+|\s+and\s+', raw)
                for part in parts:
                    name = part.strip().rstrip('.')
                    if name and len(name) >= 2 and name[0].isupper():
                        names.append(name)
                if names:
                    break
        return ", ".join(names) if names else None

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
        """Fetch appointments for a given date. Excludes CANCELLED."""
        filters = {'appointment_date': target_date}
        if technician_id:
            filters['technicien'] = technician_id
        try:
            appointments = self.storage.get_data('gazelle_appointments',
                                                  filters=filters,
                                                  order_by='appointment_time.asc')
        except Exception:
            appointments = []

        # Exclure les RV supprimés dans Gazelle
        appointments = [a for a in appointments if a.get('status') != 'CANCELLED']

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

    def _batch_fetch_past_appointments(self, client_ids: List[str]) -> Dict[str, List[Dict]]:
        """Fetch past appointments for all clients (contain rich descriptions/notes).
        Returns {client_id: [appointments]}."""
        if not client_ids:
            return {}
        ids_csv = ",".join(quote(cid) for cid in client_ids)
        url = (
            f"{self.storage.api_url}/gazelle_appointments?"
            f"client_external_id=in.({ids_csv})"
            f"&order=appointment_date.desc"
            f"&limit=50"
        )
        data = self._supabase_get(url)
        result = {}
        for a in data:
            cid = a.get('client_external_id')
            if cid:
                result.setdefault(cid, []).append(a)
        return result

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

    def _batch_fetch_gazelle_estimates(self, client_ids: List[str]) -> Dict[str, List[Dict]]:
        """Fetch REAL estimates from Gazelle live (not Supabase cache) per client.

        Returns {client_external_id: [estimate_summaries]} where each summary
        has the actual content of the soumission (items, total, status) —
        so the briefing narrative can describe what was in the soumission,
        not just that one was created. Complément de _batch_fetch_estimates
        qui ne lit que les entries log.
        """
        if not client_ids:
            return {}
        try:
            from core.gazelle_api_client import GazelleAPIClient
            gz = GazelleAPIClient()
        except Exception as exc:
            print(f"⚠️  Init GazelleAPIClient échoué pour estimates live: {exc}")
            return {}

        query = """
        query Estimates($filters: PrivateAllEstimatesFilter) {
            allEstimates(first: 20, filters: $filters) {
                nodes {
                    id number estimatedOn expiresOn isArchived
                    recommendedTierTotal
                    piano { id }
                    allEstimateTiers {
                        sequenceNumber isPrimary subtotal
                        allEstimateTierGroups {
                            allEstimateTierItems {
                                name amount
                                masterServiceItem { id }
                            }
                        }
                    }
                }
            }
        }
        """

        result = {}
        for cid in client_ids:
            try:
                r = gz._execute_query(query, {"filters": {"clientId": cid}})
                nodes = (r.get("data", {}).get("allEstimates", {}) or {}).get("nodes", []) or []
                summaries = []
                for est in nodes:
                    s = self._summarize_estimate(est)
                    if s:
                        summaries.append(s)
                # Trier par date desc (plus récent en premier)
                summaries.sort(key=lambda s: s.get("estimated_on") or "", reverse=True)
                result[cid] = summaries
            except Exception as exc:
                print(f"⚠️  Fetch estimates Gazelle pour {cid}: {exc}")
                result[cid] = []
        return result

    @staticmethod
    def _summarize_estimate(est: Dict) -> Optional[Dict]:
        """Compact summary of a Gazelle estimate for briefing display.

        Picks the primary tier (or first if none primary), collects all
        non-zero items sorted by amount desc, keeps the top 3 as a one-line
        description of what the soumission was about.
        """
        tiers = est.get("allEstimateTiers") or []
        if not tiers:
            return None
        primary = next((t for t in tiers if t.get("isPrimary")), tiers[0])
        all_items = []
        for group in primary.get("allEstimateTierGroups") or []:
            for item in group.get("allEstimateTierItems") or []:
                amt = item.get("amount") or 0
                name = (item.get("name") or "").strip()
                if amt > 0 and name:
                    all_items.append({"name": name, "amount": amt})
        all_items.sort(key=lambda i: i["amount"], reverse=True)
        top_items = [i["name"] for i in all_items[:3]]
        total_cents = est.get("recommendedTierTotal") or 0
        return {
            "number": est.get("number"),
            "estimated_on": (est.get("estimatedOn") or "")[:10],
            "is_archived": bool(est.get("isArchived")),
            "total_cents": total_cents,
            "total_dollars": f"{total_cents/100:,.0f}".replace(",", " "),
            "main_items": top_items,
            "piano_id": (est.get("piano") or {}).get("id"),
        }

    # ═══════════════════════════════════════════════════════════════
    # PDA REQUEST LOOKUP
    # ═══════════════════════════════════════════════════════════════

    def _fetch_pda_request_for_appointment(self, appointment_id: str) -> Optional[Dict]:
        """Fetch the PDA request linked to this Gazelle appointment."""
        if not appointment_id:
            return None
        try:
            cid_encoded = quote(appointment_id, safe='')
            url = (
                f"{self.storage.api_url}/place_des_arts_requests?"
                f"appointment_id=eq.{cid_encoded}"
                f"&select=room,piano,diapason,time,for_who"
                f"&limit=1"
            )
            data = self._supabase_get(url)
            return data[0] if data else None
        except Exception:
            return None

    # ═══════════════════════════════════════════════════════════════
    # PIANO MATCHING
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

        # 1. Match par numéro de série (le plus fiable)
        for piano in pianos:
            sn = (piano.get('serial_number') or '').strip()
            if sn and len(sn) >= 4 and sn in search_text:
                return piano

        # 2. Match par salle/location
        for piano in pianos:
            loc = (piano.get('location') or '').lower().strip()
            if loc and len(loc) >= 3 and loc in search_text:
                return piano
            # Aussi vérifier si la salle du RV est dans la location du piano
            if loc:
                for word in search_text.split():
                    if len(word) >= 3 and word in loc:
                        return piano

        # 3. Match par marque
        for piano in pianos:
            make = (piano.get('make') or '').lower()
            if make and len(make) > 2 and make in search_text:
                return piano

        # 4. Match par modèle
        for piano in pianos:
            model = (piano.get('model') or '').lower()
            if model and len(model) > 2 and model in search_text:
                return piano

        # 5. Match par type
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

        past_appts = await asyncio.to_thread(
            self._batch_fetch_past_appointments, [client_external_id]
        )

        gazelle_estimates = await asyncio.to_thread(
            self._batch_fetch_gazelle_estimates, [client_external_id]
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
            past_appointments=past_appts.get(client_external_id, []),
            followups=followups.get(client_external_id, []),
            estimates=estimates.get(client_external_id, []),
            gazelle_estimates=gazelle_estimates.get(client_external_id, []),
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
        url = f"{storage.api_url}/ai_training_feedback"
        response = http_requests.post(url, json=record, headers=storage._get_headers())
        if response.status_code in (200, 201):
            print(f"✅ Feedback sauvegardé pour client {client_id}")
            return True
        else:
            print(f"❌ Erreur sauvegarde feedback: {response.status_code} {response.text}")
            return False
    except Exception as e:
        print(f"❌ Erreur sauvegarde feedback: {e}")
        return False


# Keep old class name as alias for backward compatibility during transition
ClientIntelligenceService = NarrativeBriefingService
