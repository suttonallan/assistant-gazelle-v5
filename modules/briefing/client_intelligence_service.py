#!/usr/bin/env python3
"""
Client Intelligence Service - "Ma Journée" V3

Architecture HYBRIDE:
- IA (GPT-4o-mini) pour extraction intelligente + validation anti-hallucination
- Regex comme fallback si clé API absente
- Calculs factuels (dates, durées) toujours côté Python

4 Piliers d'Intelligence:
1. PROFIL HUMAIN: Langue, animaux, courtoisies, mode de paiement
2. HISTORIQUE TECHNIQUE: Visites passées avec noms de techniciens résolus
3. FICHE PIANO: Âge, avertissements, statut PLS
4. SUIVIS: Items "à faire" persistants entre visites
"""

import re
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict, field

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.supabase_storage import SupabaseStorage
from modules.briefing.ai_extraction_engine import (
    AIExtractionEngine,
    compute_client_since,
    resolve_technician_name,
    build_technical_history,
    extract_follow_ups_regex,
    TECHNICIAN_NAMES,
)


@dataclass
class ClientProfile:
    """Profil humain du client"""
    language: str = "FR"
    pets: List[str] = None
    courtesies: List[str] = None
    personality: str = ""
    parking_info: str = ""
    access_notes: str = ""
    payment_method: str = ""
    access_code: str = ""

    def __post_init__(self):
        self.pets = self.pets or []
        self.courtesies = self.courtesies or []


@dataclass
class PianoInfo:
    """Fiche piano"""
    piano_id: str = ""
    make: str = ""
    model: str = ""
    year: int = 0
    type: str = ""
    age_years: int = 0
    warnings: List[str] = None
    dampp_chaser: bool = False
    pls_status: Dict = None
    special_notes: str = ""

    def __post_init__(self):
        self.warnings = self.warnings or []
        self.pls_status = self.pls_status or {}
        if self.year and self.year > 1800:
            self.age_years = datetime.now().year - self.year


class ClientIntelligenceService:
    """Service de génération de briefings intelligents — V3 Hybride"""

    def __init__(self):
        self.storage = SupabaseStorage(silent=True)
        self.ai_engine = AIExtractionEngine()
        self._load_training_feedback()

    def _load_training_feedback(self):
        """Charge les corrections d'Allan depuis ai_training_feedback"""
        self.feedback_rules = {}
        try:
            data = self.storage.get_data('ai_training_feedback',
                                          filters={'is_active': True},
                                          order_by='created_at.desc')
            for fb in data:
                client_id = fb.get('client_external_id')
                if client_id not in self.feedback_rules:
                    self.feedback_rules[client_id] = {}

                category = fb.get('category', 'general')
                field_name = fb.get('field_name')
                self.feedback_rules[client_id][f"{category}.{field_name}"] = fb.get('corrected_value')
        except Exception as e:
            print(f"⚠️  Feedback non chargé: {e}")

    def _apply_feedback(self, client_id: str, category: str, field_name: str, detected_value: Any) -> Any:
        """Applique les corrections si elles existent"""
        key = f"{category}.{field_name}"
        if client_id in self.feedback_rules and key in self.feedback_rules[client_id]:
            return self.feedback_rules[client_id][key]
        return detected_value

    # ═══════════════════════════════════════════════════════════════════
    # FALLBACK REGEX (utilisé si pas de clé API OpenAI)
    # ═══════════════════════════════════════════════════════════════════

    def _detect_language_regex(self, text: str) -> str:
        text_lower = text.lower()
        en_words = ['the', 'and', 'please', 'thank', 'hello', 'good', 'call']
        en_count = sum(1 for w in en_words if w in text_lower)
        fr_words = ['le', 'la', 'les', 'et', 'merci', 'bonjour', 'svp']
        fr_count = sum(1 for w in fr_words if w in text_lower)

        if en_count > fr_count + 2:
            return "EN"
        elif fr_count > en_count + 2:
            return "FR"
        elif en_count > 0 and fr_count > 0:
            return "BI"
        return "FR"

    def _detect_pets_regex(self, text: str) -> List[str]:
        pets = []
        text_lower = text.lower()
        patterns = [
            r'(?:chien|dog)\s+(?:appelé|nommé|named)?\s*(\w+)',
            r'(?:chat|cat)\s+(?:appelé|nommé|named)?\s*(\w+)',
            r'attention\s+(?:au|à)\s+(?:chien|chat)',
        ]
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for m in matches:
                if m and len(m) > 2:
                    pets.append(m)

        if 'chien' in text_lower or 'dog' in text_lower:
            if not pets:
                pets.append('chien présent')
        if 'chat' in text_lower or 'cat' in text_lower:
            if not pets:
                pets.append('chat présent')

        return list(set(pets))

    def _detect_courtesies_regex(self, text: str) -> List[str]:
        courtesies = []
        text_lower = text.lower()
        patterns = {
            'enlever chaussures': [r'\benlever?\s+(?:les\s+)?chaussures\b', r'\bshoes?\s+off\b'],
            'offre café': [r'\boffre\s+(?:un\s+)?(?:café|thé)\b', r'\boffers?\s+(?:coffee|tea)\b'],
            'stationnement arrière': [r'\bstationn\w*\s+(?:en\s+)?arrière\b', r'\bparking\s+(?:in\s+)?(?:the\s+)?back\b'],
            'sonnette ne fonctionne pas': [r'\bsonnette\s+(?:ne\s+)?(?:fonctionne|marche)\s*(?:pas|plus)?\b', r'\bcogner\b'],
            'appeler avant': [r'\bappeler\s+avant\b', r'\bcall\s+before\b'],
        }
        for courtesy, regex_list in patterns.items():
            for pattern in regex_list:
                if re.search(pattern, text_lower):
                    courtesies.append(courtesy)
                    break
        return courtesies

    # ═══════════════════════════════════════════════════════════════════
    # GÉNÉRATION DE BRIEFING
    # ═══════════════════════════════════════════════════════════════════

    def generate_briefing(self, client_external_id: str,
                          appointment_context: Dict = None) -> Dict[str, Any]:
        """
        Génère un briefing complet pour un client.
        Mode hybride: IA si disponible, regex en fallback.
        """

        # 1. Récupérer les données client
        client = self._get_client(client_external_id)
        if not client:
            return {"error": "Client non trouvé"}

        # 2. Récupérer les pianos du client
        pianos = self._get_client_pianos(client_external_id)

        # 3. Matcher le piano pour ce RV
        # PRIORITÉ: utiliser piano_external_id du RV si disponible (lien direct Gazelle)
        piano_data = {}
        piano_id_from_appointment = appointment_context.get('piano_external_id') if appointment_context else None

        if piano_id_from_appointment and pianos:
            # Lien direct: chercher le piano par son ID
            for p in pianos:
                if p.get('external_id') == piano_id_from_appointment:
                    piano_data = p
                    break

        # Fallback: matcher par contexte texte si pas de lien direct
        if not piano_data and pianos:
            piano_data = self._match_piano_from_context(pianos, appointment_context)

        # 4. Récupérer les notes (timeline + appointments) - INCLUT le piano_id pour les déficiences
        piano_id = piano_data.get('external_id') if piano_data else None
        notes = self._get_client_notes(client_external_id, piano_id=piano_id)

        # 5. EXTRACTION: IA si disponible, sinon regex
        if self.ai_engine.is_available and notes:
            ai_raw = self.ai_engine.extract_client_intelligence(notes, piano_data)
            if ai_raw:
                extraction = self.ai_engine.validate_extraction(ai_raw, notes)
            else:
                extraction = self._fallback_regex_extraction(notes)
        else:
            extraction = self._fallback_regex_extraction(notes)

        # 6. PILIER 1: Profil Humain (IA enrichi)
        # Détecter si c'est une institution (langue non pertinente)
        client_name = client.get('company_name') or f"{client.get('first_name', '')} {client.get('last_name', '')}".strip()
        institution_keywords = ['place des arts', 'vincent', 'indy', 'orford', 'uqam', 'mcgill',
                                'conservatoire', 'école', 'université', 'collège', 'smcq', 'osm']
        is_institution = any(kw in client_name.lower() for kw in institution_keywords)

        profile = ClientProfile(
            language='' if is_institution else self._apply_feedback(
                client_external_id, 'profile', 'language',
                extraction.get('language', 'FR')
            ),
            pets=self._format_pets(extraction.get('pets', [])) if not is_institution else [],
            courtesies=self._format_courtesies(extraction.get('courtesies', [])),
            personality=extraction.get('personality', ''),
            payment_method=extraction.get('payment_method', ''),
            parking_info=(extraction.get('access_info') or {}).get('parking', ''),
            access_code=(extraction.get('access_info') or {}).get('access_code', ''),
            access_notes=(extraction.get('access_info') or {}).get('special_instructions', ''),
        )

        # 7. PILIER 2: Historique Technique (données factuelles Python)
        technical_history = build_technical_history(notes)

        # 8. PILIER 3: Fiche Piano
        piano_info = self._build_piano_info(piano_data, notes)

        # 9. PILIER 4: Suivis ouverts
        follow_ups = self._get_open_follow_ups(client_external_id)

        # Ajouter les nouveaux follow-ups détectés par l'IA
        ai_follow_ups = extraction.get('follow_ups', [])
        if ai_follow_ups:
            self._save_new_follow_ups(client_external_id, piano_data.get('external_id'), ai_follow_ups)

        # FALLBACK: Extraire "à faire" et déficiences via regex si pas d'IA ou si vide
        if not ai_follow_ups and notes:
            regex_follow_ups = extract_follow_ups_regex(notes)
            for rfu in regex_follow_ups:
                # Ajouter seulement si pas déjà dans la liste
                if not any(f.get('description', '').lower() == rfu['description'].lower() for f in follow_ups):
                    follow_ups.append(rfu)

        # 10. Client depuis combien de temps
        client_since = compute_client_since(notes)

        # 11. Construire le briefing final
        briefing = {
            "client_id": client_external_id,
            "client_name": client.get('company_name') or f"{client.get('first_name', '')} {client.get('last_name', '')}".strip(),
            "client_since": client_since,
            "profile": asdict(profile),
            "technical_history": technical_history,
            "piano": piano_info,
            "follow_ups": follow_ups,
            "confidence_score": 0.85 if (self.ai_engine.is_available and notes) else (0.5 if notes else 0.3),
            "extraction_mode": "ai" if self.ai_engine.is_available else "regex",
            "notes_analyzed": len(notes),
            "generated_at": datetime.now().isoformat(),
        }

        # 12. Sauvegarder dans client_intelligence (cache)
        self._save_intelligence(client_external_id, briefing)

        return briefing

    def _fallback_regex_extraction(self, notes: List[Dict]) -> Dict:
        """Extraction regex quand l'IA n'est pas disponible."""
        all_text = " ".join([n.get('text', '') for n in notes])
        return {
            'language': self._detect_language_regex(all_text),
            'pets': [{'type': p, 'name': None, 'source': ''} for p in self._detect_pets_regex(all_text)],
            'courtesies': [{'description': c, 'source': ''} for c in self._detect_courtesies_regex(all_text)],
            'payment_method': None,
            'follow_ups': [],
            'personality': None,
            'access_info': {},
        }

    def _format_pets(self, pets_data: List[Dict]) -> List[str]:
        """Formate les données animaux en strings lisibles."""
        result = []
        for pet in pets_data:
            if isinstance(pet, str):
                result.append(pet)
                continue
            pet_type = pet.get('type', '')
            name = pet.get('name')
            if name:
                result.append(f"{pet_type}: {name}")
            else:
                result.append(f"{pet_type} présent")
        return result

    def _format_courtesies(self, courtesies_data: List[Dict]) -> List[str]:
        """Formate les courtoisies en strings lisibles."""
        result = []
        for c in courtesies_data:
            if isinstance(c, str):
                result.append(c)
                continue
            desc = c.get('description', '')
            if desc:
                result.append(desc)
        return result

    def _build_piano_info(self, piano_data: Dict, notes: List[Dict]) -> Dict:
        """Construit la fiche piano avec statut PLS intelligent."""
        if not piano_data:
            return {}

        year = piano_data.get('year') or 0
        age = datetime.now().year - year if year > 1800 else 0

        warnings = []
        if age > 80:
            warnings.append("Piano > 80 ans - Fragilité mécanique")
        elif age > 40:
            warnings.append("Piano mature (> 40 ans) - Attention particulière")

        # Analyse PLS
        pls_status = {}
        if piano_data.get('dampp_chaser_installed'):
            if self.ai_engine.is_available and notes:
                pls_raw = self.ai_engine.analyze_pls_services(notes)
                if pls_raw:
                    pls_status = self.ai_engine.validate_pls_analysis(
                        pls_raw, notes, piano_data
                    )
                else:
                    pls_status = {"needs_annual": None, "reason": "Analyse PLS non disponible"}
            else:
                pls_status = {"needs_annual": None, "reason": "IA non disponible"}

            # Warning PLS basé sur l'analyse
            if pls_status.get('needs_annual') is True:
                months = pls_status.get('months_since_last', '?')
                warnings.append(f"PLS: entretien annuel dû ({months} mois depuis dernier service)")
            elif pls_status.get('needs_annual') is False:
                months = pls_status.get('months_since_last', '?')
                # Pas de warning, mais info dans pls_status pour Niveau 2
            else:
                warnings.append("Dampp-Chaser installé - Vérifier niveau d'eau")

        piano_info = asdict(PianoInfo(
            piano_id=piano_data.get('external_id', ''),
            make=piano_data.get('make', ''),
            model=piano_data.get('model', ''),
            year=year,
            type=piano_data.get('type', ''),
            age_years=age,
            warnings=warnings,
            dampp_chaser=piano_data.get('dampp_chaser_installed', False),
            pls_status=pls_status,
        ))

        return piano_info

    # ═══════════════════════════════════════════════════════════════════
    # FOLLOW-UPS (SUIVI PERSISTANT)
    # ═══════════════════════════════════════════════════════════════════

    def _get_open_follow_ups(self, client_id: str) -> List[Dict]:
        """Récupère les follow-ups ouverts pour un client."""
        try:
            items = self.storage.get_data(
                'follow_up_items',
                filters={'client_external_id': client_id, 'status': 'open'},
                order_by='detected_at.desc'
            )
            return [
                {
                    "id": item.get('id'),
                    "category": item.get('category'),
                    "description": item.get('description'),
                    "source_citation": item.get('source_citation'),
                    "detected_at": item.get('detected_at'),
                }
                for item in items
            ]
        except Exception:
            return []

    def _save_new_follow_ups(self, client_id: str, piano_id: Optional[str],
                              ai_follow_ups: List[Dict]):
        """Sauvegarde les nouveaux follow-ups détectés par l'IA."""
        for fu in ai_follow_ups:
            try:
                record = {
                    'client_external_id': client_id,
                    'piano_external_id': piano_id,
                    'category': fu.get('category', 'action'),
                    'description': fu.get('description', ''),
                    'source_citation': fu.get('source', ''),
                    'status': 'open',
                    'detected_by': 'ai_extraction',
                }
                # Upsert pour éviter les doublons (unique index sur client+description WHERE open)
                self.storage.upsert_data(
                    'follow_up_items', record,
                    conflict_column='client_external_id,description'
                )
            except Exception as e:
                # Duplicate ou erreur — on continue
                pass

    def resolve_follow_up(self, item_id: str, resolved_by: str = None,
                           resolution_note: str = None) -> bool:
        """Marque un follow-up comme résolu."""
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

    # ═══════════════════════════════════════════════════════════════════
    # PIANO MATCHING (inchangé)
    # ═══════════════════════════════════════════════════════════════════

    def _match_piano_from_context(self, pianos: List[Dict],
                                    appointment_context: Dict = None) -> Dict:
        """Trouve le piano correspondant au RV basé sur la description/titre."""
        if not pianos:
            return {}
        if len(pianos) == 1:
            return pianos[0]
        if not appointment_context:
            return pianos[0]

        search_text = " ".join([
            appointment_context.get('title', ''),
            appointment_context.get('description', ''),
            appointment_context.get('notes', ''),
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

    # ═══════════════════════════════════════════════════════════════════
    # DATA ACCESS (inchangé)
    # ═══════════════════════════════════════════════════════════════════

    def _get_client(self, client_id: str) -> Optional[Dict]:
        try:
            clients = self.storage.get_data('gazelle_clients',
                                            filters={'external_id': client_id})
            return clients[0] if clients else None
        except:
            return None

    def _get_client_notes(self, client_id: str, piano_id: str = None) -> List[Dict]:
        notes = []
        seen_texts = set()  # Éviter les doublons

        # 1. Timeline par client
        try:
            timeline = self.storage.get_data('gazelle_timeline_entries',
                                              filters={'client_id': client_id},
                                              order_by='occurred_at.desc')
            for t in timeline[:20]:
                text = f"{t.get('title', '')} {t.get('description', '')}".strip()
                if text and text not in seen_texts:
                    seen_texts.add(text)
                    notes.append({
                        'date': t.get('occurred_at', '')[:10],
                        'text': text,
                        'technician': t.get('user_id', ''),
                        'source': 'timeline'
                    })
        except:
            pass

        # 2. Timeline par piano (important pour les déficiences liées au piano!)
        if piano_id:
            try:
                piano_timeline = self.storage.get_data('gazelle_timeline_entries',
                                                        filters={'piano_id': piano_id},
                                                        order_by='occurred_at.desc')
                for t in piano_timeline[:20]:
                    text = f"{t.get('title', '')} {t.get('description', '')}".strip()
                    if text and text not in seen_texts:
                        seen_texts.add(text)
                        notes.append({
                            'date': t.get('occurred_at', '')[:10],
                            'text': text,
                            'technician': t.get('user_id', ''),
                            'source': 'piano_timeline'
                        })
            except:
                pass

        # 3. Appointments
        try:
            appts = self.storage.get_data('gazelle_appointments',
                                           filters={'client_external_id': client_id},
                                           order_by='start_datetime.desc')
            for a in appts[:10]:
                text = f"{a.get('title', '')} {a.get('description', '')} {a.get('notes', '')}".strip()
                if text and text not in seen_texts:
                    seen_texts.add(text)
                    notes.append({
                        'date': a.get('appointment_date', ''),
                        'text': text,
                        'technician': a.get('technicien', ''),
                        'source': 'appointment'
                    })
        except:
            pass

        return notes

    def _get_client_pianos(self, client_id: str) -> List[Dict]:
        try:
            return self.storage.get_data('gazelle_pianos',
                                          filters={'client_external_id': client_id})
        except:
            return []

    def _save_intelligence(self, client_id: str, briefing: Dict):
        try:
            record = {
                'client_external_id': client_id,
                'profile_data': briefing.get('profile', {}),
                'technical_history': briefing.get('technical_history', []),
                'piano_info': briefing.get('piano', {}),
                'confidence_score': briefing.get('confidence_score', 0.5),
                'notes_analyzed_count': briefing.get('notes_analyzed', 0),
                'last_generated_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat(),
            }
            self.storage.upsert_data('client_intelligence', record,
                                      conflict_column='client_external_id')
        except Exception as e:
            print(f"⚠️  Erreur sauvegarde intelligence: {e}")

    # ═══════════════════════════════════════════════════════════════════
    # BRIEFINGS DU JOUR (inchangé sauf format)
    # ═══════════════════════════════════════════════════════════════════

    def get_daily_briefings(self, technician_id: str = None,
                            exclude_technician_id: str = None,
                            target_date: str = None) -> List[Dict]:
        if not target_date:
            target_date = datetime.now().strftime('%Y-%m-%d')

        filters = {'appointment_date': target_date}
        if technician_id:
            filters['technicien'] = technician_id

        try:
            appointments = self.storage.get_data('gazelle_appointments',
                                                  filters=filters,
                                                  order_by='appointment_time.asc')
        except:
            appointments = []

        if exclude_technician_id:
            appointments = [a for a in appointments
                           if a.get('technicien') != exclude_technician_id]

        briefings = []
        for appt in appointments:
            client_id = appt.get('client_external_id')
            if not client_id:
                continue

            appointment_context = {
                'title': appt.get('title', ''),
                'description': appt.get('description', ''),
                'notes': appt.get('notes', ''),
                'piano_external_id': appt.get('piano_external_id'),  # 🔗 Lien direct vers le piano
            }

            briefing = self.generate_briefing(client_id, appointment_context)

            briefing['appointment'] = {
                'id': appt.get('external_id'),
                'time': appt.get('appointment_time', '')[:5],
                'title': appt.get('title', ''),
                'description': appt.get('description', ''),
                'technician_id': appt.get('technicien'),
            }

            briefings.append(briefing)

        return briefings

    def format_briefing_card(self, briefing: Dict) -> str:
        """Formate un briefing en texte concis pour affichage mobile."""
        lines = []

        appt = briefing.get('appointment', {})
        client_since = briefing.get('client_since', '')
        since_str = f" ({client_since})" if client_since else ""
        lines.append(f"⏰ {appt.get('time', '?')} - {briefing.get('client_name', 'Client')}{since_str}")
        lines.append("─" * 30)

        profile = briefing.get('profile', {})
        icons = []
        if profile.get('language') == 'EN':
            icons.append("🇬🇧")
        if profile.get('pets'):
            icons.append("🐕 " + ", ".join(profile['pets']))
        courtesies = profile.get('courtesies') or []
        if 'enlever chaussures' in courtesies:
            icons.append("👟❌")
        if 'offre café' in courtesies:
            icons.append("☕")
        if profile.get('payment_method'):
            icons.append(f"💳 {profile['payment_method']}")
        if icons:
            lines.append(" ".join(icons))

        piano = briefing.get('piano', {})
        if piano and piano.get('make'):
            piano_line = f"🎹 {piano.get('make', '')} {piano.get('model', '')}"
            if piano.get('year'):
                piano_line += f" ({piano.get('year')})"
            lines.append(piano_line)
            for warning in (piano.get('warnings') or []):
                lines.append(f"   ⚠️ {warning}")

        # Dernière visite
        history = briefing.get('technical_history', [])
        if history:
            h = history[0]
            tech = h.get('technician', '')
            date = h.get('date', '')
            lines.append(f"📋 Dernier: {tech}, {date}")

        # Follow-ups ouverts
        follow_ups = briefing.get('follow_ups', [])
        if follow_ups:
            lines.append(f"🔔 {len(follow_ups)} suivi(s) en attente")
            for fu in follow_ups[:2]:
                lines.append(f"   → {fu.get('description', '')}")

        return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════
# API FEEDBACK (Allan Only)
# ═══════════════════════════════════════════════════════════════════════

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


# ═══════════════════════════════════════════════════════════════════════
# TEST
# ═══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print("TEST CLIENT INTELLIGENCE SERVICE V3")
    print("=" * 60)

    service = ClientIntelligenceService()
    print(f"Mode: {'IA' if service.ai_engine.is_available else 'Regex fallback'}")

    print("\n📅 Briefings du jour:")
    briefings = service.get_daily_briefings()

    if not briefings:
        print("   Aucun RV aujourd'hui")
    else:
        for b in briefings[:3]:
            print("\n" + service.format_briefing_card(b))
            print()
