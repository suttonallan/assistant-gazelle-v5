#!/usr/bin/env python3
"""
Client Intelligence Service - "Ma Journée" V2

Analyse les notes Gazelle pour générer des briefings concis pour les techniciens.

3 Piliers d'Intelligence:
1. PROFIL HUMAIN: Langue, famille, animaux, courtoisies
2. HISTORIQUE TECHNIQUE: Recommandations, travaux effectués
3. FICHE PIANO: Âge, avertissements, particularités
"""

import re
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.supabase_storage import SupabaseStorage


@dataclass
class ClientProfile:
    """Profil humain du client (permanent)"""
    language: str = "FR"  # FR, EN, BI
    family_members: List[str] = None
    pets: List[str] = None
    courtesies: List[str] = None
    personality: str = ""  # bavard, discret, pressé
    parking_info: str = ""
    access_notes: str = ""

    def __post_init__(self):
        self.family_members = self.family_members or []
        self.pets = self.pets or []
        self.courtesies = self.courtesies or []


@dataclass
class TechnicalVisit:
    """Une visite technique"""
    date: str
    technician: str = ""
    recommendations: List[str] = None
    work_done: List[str] = None
    next_action: str = ""

    def __post_init__(self):
        self.recommendations = self.recommendations or []
        self.work_done = self.work_done or []


@dataclass
class PianoInfo:
    """Fiche piano"""
    piano_id: str = ""
    make: str = ""
    model: str = ""
    year: int = 0
    type: str = ""  # grand, upright
    age_years: int = 0
    warnings: List[str] = None
    dampp_chaser: bool = False
    special_notes: str = ""

    def __post_init__(self):
        self.warnings = self.warnings or []
        if self.year and self.year > 1800:
            self.age_years = datetime.now().year - self.year


class ClientIntelligenceService:
    """Service de génération de briefings intelligents"""

    def __init__(self):
        self.storage = SupabaseStorage(silent=True)
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
                field = fb.get('field_name')
                self.feedback_rules[client_id][f"{category}.{field}"] = fb.get('corrected_value')
        except Exception as e:
            print(f"⚠️  Feedback non chargé: {e}")

    def _apply_feedback(self, client_id: str, category: str, field: str, detected_value: Any) -> Any:
        """Applique les corrections si elles existent"""
        key = f"{category}.{field}"
        if client_id in self.feedback_rules and key in self.feedback_rules[client_id]:
            return self.feedback_rules[client_id][key]
        return detected_value

    # ═══════════════════════════════════════════════════════════════════
    # DÉTECTEURS DE PATTERNS
    # ═══════════════════════════════════════════════════════════════════

    def _detect_language(self, text: str) -> str:
        """Détecte la langue préférée"""
        text_lower = text.lower()

        # Mots anglais fréquents
        en_words = ['the', 'and', 'please', 'thank', 'hello', 'good', 'call', 'email']
        en_count = sum(1 for w in en_words if w in text_lower)

        # Mots français
        fr_words = ['le', 'la', 'les', 'et', 'merci', 'bonjour', 'svp', 'appeler']
        fr_count = sum(1 for w in fr_words if w in text_lower)

        if en_count > fr_count + 2:
            return "EN"
        elif fr_count > en_count + 2:
            return "FR"
        elif en_count > 0 and fr_count > 0:
            return "BI"
        return "FR"

    def _detect_pets(self, text: str) -> List[str]:
        """Détecte les mentions d'animaux"""
        pets = []
        patterns = [
            r'(?:chien|dog)\s+(?:appelé|nommé|named)?\s*(\w+)',
            r'(?:chat|cat)\s+(?:appelé|nommé|named)?\s*(\w+)',
            r'(\w+)\s+(?:le|the)\s+(?:chien|chat|dog|cat)',
            r'attention\s+(?:au|à)\s+(?:chien|chat)',
        ]
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for m in matches:
                if m and len(m) > 2:
                    pets.append(m)

        # Mentions simples
        if 'chien' in text.lower() or 'dog' in text.lower():
            if not pets:
                pets.append('chien présent')
        if 'chat' in text.lower() or 'cat' in text.lower():
            if not pets:
                pets.append('chat présent')

        return list(set(pets))

    def _detect_courtesies(self, text: str) -> List[str]:
        """
        Détecte les préférences de courtoisie.

        IMPORTANT: Ne détecte QUE les patterns explicites pour éviter
        les faux positifs (ex: "théâtre" ne doit pas matcher "thé").
        """
        courtesies = []
        text_lower = text.lower()

        # Patterns avec regex pour éviter les faux positifs
        # Chaque pattern doit être explicite et sans ambiguïté
        patterns = {
            'enlever chaussures': [
                r'\benlever?\s+(?:les\s+)?chaussures\b',
                r'\bshoes?\s+off\b',
                r'\bremove\s+shoes\b',
                r'\bsans\s+chaussures\b',
            ],
            'offre café': [
                r'\boffre\s+(?:un\s+)?(?:café|thé)\b',
                r'\boffers?\s+(?:coffee|tea)\b',
                r'\bcafé\s+offert\b',
            ],
            'stationnement arrière': [
                r'\bstationn\w*\s+(?:en\s+)?arrière\b',
                r'\bparking\s+(?:in\s+)?(?:the\s+)?back\b',
                r'\bse\s+garer\s+(?:en\s+)?arrière\b',
            ],
            'sonnette ne fonctionne pas': [
                r'\bsonnette\s+(?:ne\s+)?(?:fonctionne|marche)\s*(?:pas|plus)?\b',
                r'\bdoorbell\s+(?:does\s*n.t|broken)\b',
                r'\bcogner\b',
                r'\bknock\b',
            ],
            'appeler avant': [
                r'\bappeler\s+avant\b',
                r'\btéléphoner\s+avant\b',
                r'\bcall\s+before\b',
                r'\bconfirmer\s+(?:le\s+)?(?:rv|rendez)\b',
            ],
        }

        for courtesy, regex_list in patterns.items():
            for pattern in regex_list:
                if re.search(pattern, text_lower):
                    courtesies.append(courtesy)
                    break  # Une seule détection par courtoisie

        return courtesies

    def _detect_recommendations(self, text: str) -> List[str]:
        """Détecte les recommandations techniques (verbes d'action)"""
        recommendations = []
        text_lower = text.lower()

        # Patterns de recommandations
        action_patterns = [
            r'(?:recommand[eé]|suggér[eé]|à faire|should|need)\s*:?\s*([^.]+)',
            r'(?:prochain|next)\s+(?:fois|time|visite)\s*:?\s*([^.]+)',
            r'(?:lubrifi|harmonis|régl|adjust|tune|clean|nettoy)\w*',
        ]

        keywords = {
            'lubrification': ['lubrifi', 'lubricat'],
            'harmonisation': ['harmonis', 'voic'],
            'réglage mécanique': ['réglage', 'adjust', 'mécanique'],
            'vérifier humidité': ['humid', 'dampp', 'hygrométr'],
            'accord': ['accord', 'tun'],
            'nettoyage': ['nettoy', 'clean'],
        }

        for action, patterns in keywords.items():
            if any(p in text_lower for p in patterns):
                recommendations.append(action)

        return list(set(recommendations))

    def _detect_work_done(self, text: str) -> List[str]:
        """Détecte les travaux effectués"""
        work = []
        text_lower = text.lower()

        past_patterns = {
            'accord effectué': ['accordé', 'tuned', 'accord fait'],
            'nettoyage effectué': ['nettoyé', 'cleaned'],
            'réglage effectué': ['réglé', 'adjusted'],
            'harmonisation effectuée': ['harmonisé', 'voiced'],
        }

        for work_item, patterns in past_patterns.items():
            if any(p in text_lower for p in patterns):
                work.append(work_item)

        return work

    # ═══════════════════════════════════════════════════════════════════
    # GÉNÉRATION DE BRIEFING
    # ═══════════════════════════════════════════════════════════════════

    def generate_briefing(self, client_external_id: str,
                          appointment_context: Dict = None) -> Dict[str, Any]:
        """
        Génère un briefing complet pour un client.

        Args:
            client_external_id: ID externe du client
            appointment_context: Contexte du RV (title, description, notes) pour matcher le bon piano
        """

        # 1. Récupérer les données client
        client = self._get_client(client_external_id)
        if not client:
            return {"error": "Client non trouvé"}

        # 2. Récupérer les notes (timeline + appointments)
        notes = self._get_client_notes(client_external_id)

        # 3. Récupérer les pianos du client
        pianos = self._get_client_pianos(client_external_id)

        # 4. Analyser et générer les 3 piliers
        all_text = " ".join([n.get('text', '') for n in notes])

        # PILIER 1: Profil Humain
        profile = ClientProfile(
            language=self._apply_feedback(client_external_id, 'profile', 'language',
                                          self._detect_language(all_text)),
            pets=self._detect_pets(all_text),
            courtesies=self._detect_courtesies(all_text),
        )

        # PILIER 2: Historique Technique (dernières visites)
        technical_history = []
        for note in notes[:5]:  # 5 dernières
            visit = TechnicalVisit(
                date=note.get('date', ''),
                technician=note.get('technician', ''),
                recommendations=self._detect_recommendations(note.get('text', '')),
                work_done=self._detect_work_done(note.get('text', '')),
            )
            if visit.recommendations or visit.work_done:
                technical_history.append(asdict(visit))

        # PILIER 3: Fiche Piano
        piano_info = {}
        if pianos:
            # Matcher le piano mentionné dans le RV (si contexte fourni)
            p = self._match_piano_from_context(pianos, appointment_context)
            year = p.get('year') or 0
            age = datetime.now().year - year if year > 1800 else 0

            warnings = []
            if age > 80:
                warnings.append("⚠️ DISCLAIMER: Piano > 80 ans - Fragilité mécanique")
            elif age > 40:
                warnings.append("Piano mature (> 40 ans) - Attention particulière")

            if p.get('dampp_chaser_installed'):
                warnings.append("Dampp-Chaser installé - Vérifier niveau d'eau")

            piano_info = asdict(PianoInfo(
                piano_id=p.get('external_id', ''),
                make=p.get('make', ''),
                model=p.get('model', ''),
                year=year,
                type=p.get('type', ''),
                age_years=age,
                warnings=warnings,
                dampp_chaser=p.get('dampp_chaser_installed', False),
            ))

        # 5. Construire le briefing final
        briefing = {
            "client_id": client_external_id,
            "client_name": client.get('company_name') or f"{client.get('first_name', '')} {client.get('last_name', '')}".strip(),
            "profile": asdict(profile),
            "technical_history": technical_history,
            "piano": piano_info,
            "confidence_score": 0.7 if notes else 0.3,
            "notes_analyzed": len(notes),
            "generated_at": datetime.now().isoformat(),
        }

        # 6. Sauvegarder dans client_intelligence (cache)
        self._save_intelligence(client_external_id, briefing)

        return briefing

    def _match_piano_from_context(self, pianos: List[Dict],
                                    appointment_context: Dict = None) -> Dict:
        """
        Trouve le piano correspondant au RV basé sur la description/titre.

        Recherche le nom de marque (make) dans le texte du RV.
        Si un client a 2 pianos (Yamaha N-2, Fuchs & Mohr) et le RV dit
        "Piano à queue Fuchs & Mohr", retourne le Fuchs & Mohr.

        Args:
            pianos: Liste des pianos du client
            appointment_context: {'title': ..., 'description': ..., 'notes': ...}

        Returns:
            Le piano matché ou le premier par défaut
        """
        if not pianos:
            return {}

        if len(pianos) == 1:
            return pianos[0]

        # Pas de contexte = premier piano
        if not appointment_context:
            return pianos[0]

        # Construire le texte de recherche depuis le contexte du RV
        search_text = " ".join([
            appointment_context.get('title', ''),
            appointment_context.get('description', ''),
            appointment_context.get('notes', ''),
        ]).lower()

        if not search_text.strip():
            return pianos[0]

        # Chercher chaque piano par marque (make)
        for piano in pianos:
            make = (piano.get('make') or '').lower()
            if make and len(make) > 2 and make in search_text:
                return piano

        # Chercher par modèle aussi
        for piano in pianos:
            model = (piano.get('model') or '').lower()
            if model and len(model) > 2 and model in search_text:
                return piano

        # Chercher "grand" ou "queue" pour piano à queue
        if 'queue' in search_text or 'grand' in search_text:
            for piano in pianos:
                ptype = (piano.get('type') or '').lower()
                if ptype in ['grand', 'queue', 'baby grand']:
                    return piano

        # Fallback: premier piano
        return pianos[0]

    def _get_client(self, client_id: str) -> Optional[Dict]:
        """Récupère les infos client"""
        try:
            clients = self.storage.get_data('gazelle_clients',
                                            filters={'external_id': client_id})
            return clients[0] if clients else None
        except:
            return None

    def _get_client_notes(self, client_id: str) -> List[Dict]:
        """Récupère toutes les notes d'un client"""
        notes = []

        # Timeline entries
        try:
            timeline = self.storage.get_data('gazelle_timeline_entries',
                                              filters={'client_id': client_id},
                                              order_by='occurred_at.desc')
            for t in timeline[:20]:
                notes.append({
                    'date': t.get('occurred_at', '')[:10],
                    'text': f"{t.get('title', '')} {t.get('description', '')}",
                    'technician': t.get('user_id', ''),
                    'source': 'timeline'
                })
        except:
            pass

        # Appointments notes
        try:
            appts = self.storage.get_data('gazelle_appointments',
                                           filters={'client_external_id': client_id},
                                           order_by='start_datetime.desc')
            for a in appts[:10]:
                text = f"{a.get('title', '')} {a.get('description', '')} {a.get('notes', '')}"
                if text.strip():
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
        """Récupère les pianos du client"""
        try:
            return self.storage.get_data('gazelle_pianos',
                                          filters={'client_external_id': client_id})
        except:
            return []

    def _save_intelligence(self, client_id: str, briefing: Dict):
        """Sauvegarde le briefing dans client_intelligence"""
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
    # BRIEFINGS DU JOUR
    # ═══════════════════════════════════════════════════════════════════

    def get_daily_briefings(self, technician_id: str = None,
                            exclude_technician_id: str = None,
                            target_date: str = None) -> List[Dict]:
        """
        Récupère les briefings pour les RV du jour.

        Args:
            technician_id: Filtrer par technicien (optionnel)
            exclude_technician_id: Exclure ce technicien (optionnel)
            target_date: Date cible YYYY-MM-DD (défaut: aujourd'hui)

        Returns:
            Liste de briefings pour chaque RV
        """
        if not target_date:
            target_date = datetime.now().strftime('%Y-%m-%d')

        # Récupérer les RV du jour
        filters = {'appointment_date': target_date}
        if technician_id:
            filters['technicien'] = technician_id

        try:
            appointments = self.storage.get_data('gazelle_appointments',
                                                  filters=filters,
                                                  order_by='appointment_time.asc')
        except:
            appointments = []

        # Exclure un technicien si demandé
        if exclude_technician_id:
            appointments = [a for a in appointments
                           if a.get('technicien') != exclude_technician_id]

        briefings = []
        for appt in appointments:
            client_id = appt.get('client_external_id')
            if not client_id:
                continue

            # Contexte du RV pour matcher le bon piano
            appointment_context = {
                'title': appt.get('title', ''),
                'description': appt.get('description', ''),
                'notes': appt.get('notes', ''),
            }

            # Générer le briefing avec le contexte du RV
            briefing = self.generate_briefing(client_id, appointment_context)

            # Ajouter les infos du RV
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
        """
        Formate un briefing en texte concis pour affichage mobile.
        Lisible en 10 secondes.
        """
        lines = []

        # Header
        appt = briefing.get('appointment', {})
        lines.append(f"⏰ {appt.get('time', '?')} - {briefing.get('client_name', 'Client')}")
        lines.append("─" * 30)

        # Profil rapide
        profile = briefing.get('profile', {})
        icons = []
        if profile.get('language') == 'EN':
            icons.append("🇬🇧")
        if profile.get('pets'):
            icons.append("🐕")
        if 'enlever chaussures' in (profile.get('courtesies') or []):
            icons.append("👟❌")
        if 'offre café' in (profile.get('courtesies') or []):
            icons.append("☕")
        if icons:
            lines.append(" ".join(icons))

        # Piano
        piano = briefing.get('piano', {})
        if piano:
            piano_line = f"🎹 {piano.get('make', '')} {piano.get('model', '')}"
            if piano.get('year'):
                piano_line += f" ({piano.get('year')})"
            lines.append(piano_line)

            for warning in (piano.get('warnings') or []):
                lines.append(f"   {warning}")

        # Dernière recommandation
        history = briefing.get('technical_history', [])
        if history and history[0].get('recommendations'):
            rec = history[0]['recommendations'][0]
            lines.append(f"📋 Dernière reco: {rec}")

        return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════
# API FEEDBACK (Allan Only)
# ═══════════════════════════════════════════════════════════════════════

def save_feedback(client_id: str, category: str, field_name: str,
                  original_value: str, corrected_value: str,
                  created_by: str = "asutton@piano-tek.com") -> bool:
    """
    Sauvegarde une correction d'Allan.

    Args:
        client_id: ID externe du client
        category: 'profile', 'technical', 'piano', 'general'
        field_name: Nom du champ corrigé
        original_value: Ce que l'IA avait détecté
        corrected_value: La correction
        created_by: Email de l'utilisateur

    Returns:
        True si succès
    """
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
    print("TEST CLIENT INTELLIGENCE SERVICE")
    print("=" * 60)

    service = ClientIntelligenceService()

    # Test: récupérer les briefings du jour
    print("\n📅 Briefings du jour:")
    briefings = service.get_daily_briefings()

    if not briefings:
        print("   Aucun RV aujourd'hui")
    else:
        for b in briefings[:3]:
            print("\n" + service.format_briefing_card(b))
            print()
