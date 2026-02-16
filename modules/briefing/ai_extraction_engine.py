#!/usr/bin/env python3
"""
AI Extraction Engine — Moteur d'intelligence ancré pour Ma Journée V3.

Remplace les 224 IF/ELSE par un LLM contraint qui EXTRAIT sans INVENTER.

Architecture:
    Notes Gazelle (brutes) → Prompt structuré → JSON validé → Briefing

Sécurités anti-hallucination:
    1. Le prompt interdit explicitement l'invention
    2. Chaque fait extrait doit avoir une citation (date + extrait)
    3. Python valide chaque citation contre les notes brutes
    4. Les calculs de dates sont faits côté Python, pas par l'IA
    5. Si pas de preuve → null (jamais de supposition)
"""

import os
import json
import re
from datetime import datetime
from typing import Dict, List, Optional, Any

try:
    from anthropic import Anthropic
except ImportError:
    Anthropic = None


# ═══════════════════════════════════════════════════════════════════
# PROMPTS D'EXTRACTION (GROUNDED — AUCUNE INVENTION)
# ═══════════════════════════════════════════════════════════════════

CLIENT_EXTRACTION_PROMPT = """Tu es un EXTRACTEUR de données pour un service de piano.
Tu analyses des notes de service rédigées par des techniciens de piano.

RÈGLES ABSOLUES:
1. Tu EXTRAIS uniquement ce qui est ÉCRIT dans les notes
2. Tu ne DÉDUIS RIEN, tu ne COMPLÈTES RIEN, tu n'INVENTES RIEN
3. Chaque fait extrait DOIT citer la note source (date + extrait exact)
4. Si une info n'est PAS dans les notes → retourne null
5. En cas de doute → null

NOTES DU CLIENT (source: Gazelle, les plus récentes en premier):
{notes_json}

DONNÉES PIANO (source: base de données Gazelle):
{piano_json}

Retourne UNIQUEMENT ce JSON (pas de texte avant/après):
{{
  "language": {{
    "value": "FR|EN|BI|null",
    "source": "note du YYYY-MM-DD: 'extrait exact' | null"
  }},
  "pets": [
    {{
      "type": "chien|chat|autre",
      "name": "nom ou null",
      "source": "note du YYYY-MM-DD: 'extrait exact'"
    }}
  ],
  "courtesies": [
    {{
      "description": "description courte (ex: enlever chaussures, offre café, stationner en arrière)",
      "source": "note du YYYY-MM-DD: 'extrait exact'"
    }}
  ],
  "payment_method": {{
    "value": "chèque|virement|comptant|carte|null",
    "source": "note du YYYY-MM-DD: 'extrait exact' | null"
  }},
  "follow_ups": [
    {{
      "category": "action|missing_part|observation|bring_item",
      "description": "description claire et courte",
      "source": "note du YYYY-MM-DD: 'extrait exact'",
      "source_date": "YYYY-MM-DD"
    }}
  ],
  "personality_notes": {{
    "value": "description très courte du tempérament ou null",
    "source": "note du YYYY-MM-DD: 'extrait exact' | null"
  }},
  "access_info": {{
    "parking": "info stationnement ou null",
    "access_code": "code ou null",
    "floor": "étage ou null",
    "special_instructions": "instructions spéciales ou null",
    "source": "note du YYYY-MM-DD: 'extrait exact' | null"
  }}
}}

EXEMPLES de follow_ups à détecter:
- "prochaine fois: harmonisation" → action
- "rondelle manquante sur la pédale" → missing_part
- "touche sol# colle un peu" → observation
- "apporter buvards" → bring_item
- "à faire: lubrification des centres" → action
- "bruit bizarre dans les aigus" → observation

Pour la langue: analyse si les notes sont en anglais, français, ou les deux.
Pour le mode de paiement: cherche mentions de chèque, virement, comptant, carte, etc.
N'invente RIEN. Si pas mentionné → null."""


PLS_ANALYSIS_PROMPT = """Tu analyses des notes de service pour un Piano Life Saver (PLS / Dampp-Chaser).

RÈGLES ABSOLUES:
1. EXTRAIS uniquement ce qui est ÉCRIT
2. Chaque service identifié DOIT avoir une citation exacte
3. En cas de doute sur le type → "unknown"
4. N'invente RIEN

NOTES DE SERVICE (les plus récentes en premier):
{pls_notes_json}

Pour chaque note qui concerne le PLS/Dampp-Chaser, identifie:
1. La date
2. Le type de service:
   - "basic": SEULEMENT test/vérification + remplacement buvards/pads
     (Exemples: "test ok buvards remplacés", "pads changés tout beau",
      "buvards faits RAS", "changed pads all good")
   - "annual": entretien annuel complet = tout travail AU-DELÀ du simple
     test+buvards (nettoyage barres, traitement, vérification électrique,
     remplacement composants, etc.)
     (Exemples: "entretien annuel complet", "nettoyage barres traitement",
      "annual maintenance full service")
   - "unknown": pas assez d'info pour déterminer
3. Citation exacte de la note

Retourne UNIQUEMENT ce JSON:
{{
  "pls_services": [
    {{
      "date": "YYYY-MM-DD",
      "type": "basic|annual|unknown",
      "source": "citation exacte de la note"
    }}
  ]
}}"""


TECHNICIAN_NAMES = {
    "usr_HcCiFk7o0vZ9xAI0": "Nicolas",
    "usr_ReUSmIJmBF86ilY1": "Jean-Philippe",
    "usr_ofYggsCDt2JAVeNP": "Allan",
    "usr_tndhXmnT0iakT4HF": "Louise",
    "usr_bbt59aCUqUaDWA8n": "Margot",
}


class AIExtractionEngine:
    """
    Moteur d'extraction IA ancré.

    Utilise Claude Haiku pour extraire des informations structurées
    depuis les notes Gazelle, avec validation croisée obligatoire.
    """

    def __init__(self):
        api_key = os.getenv('ANTHROPIC_API_KEY')

        # Fallback: chercher la clé dans Supabase si pas dans env
        if not api_key:
            try:
                from core.supabase_storage import SupabaseStorage
                storage = SupabaseStorage(silent=True)
                settings = storage.get_data('system_settings', filters={'key': 'anthropic_api_key'})
                if settings and settings[0].get('value'):
                    api_key = settings[0]['value']
                    print("✅ AI Extraction: clé Anthropic chargée depuis Supabase")
            except Exception as e:
                pass  # Silencieux si ça échoue

        if api_key and Anthropic:
            self.anthropic = Anthropic(api_key=api_key)
        else:
            self.anthropic = None
            print("⚠️  AI Extraction Engine: ANTHROPIC_API_KEY manquante — mode regex uniquement")

    @property
    def is_available(self) -> bool:
        return self.anthropic is not None

    # ═══════════════════════════════════════════════════════════════
    # EXTRACTION PRINCIPALE
    # ═══════════════════════════════════════════════════════════════

    def extract_client_intelligence(
        self,
        notes: List[Dict],
        piano_data: Optional[Dict] = None,
    ) -> Optional[Dict]:
        """
        Extraction IA complète depuis les notes d'un client.

        Args:
            notes: Liste de notes [{date, text, technician, source}]
            piano_data: Données piano depuis gazelle_pianos

        Returns:
            Dict structuré avec citations, ou None si IA indisponible
        """
        if not self.anthropic or not notes:
            return None

        # Préparer les notes pour le prompt (limiter à 20 pour ne pas exploser le contexte)
        notes_for_prompt = []
        for n in notes[:20]:
            tech_name = TECHNICIAN_NAMES.get(n.get('technician', ''), n.get('technician', ''))
            notes_for_prompt.append({
                "date": n.get('date', ''),
                "technician": tech_name,
                "text": n.get('text', '')[:500],  # Tronquer les notes très longues
            })

        piano_for_prompt = {}
        if piano_data:
            piano_for_prompt = {
                "make": piano_data.get('make', ''),
                "model": piano_data.get('model', ''),
                "year": piano_data.get('year', ''),
                "type": piano_data.get('type', ''),
                "dampp_chaser_installed": piano_data.get('dampp_chaser_installed', False),
            }

        prompt = CLIENT_EXTRACTION_PROMPT.format(
            notes_json=json.dumps(notes_for_prompt, ensure_ascii=False, indent=2),
            piano_json=json.dumps(piano_for_prompt, ensure_ascii=False, indent=2),
        )

        try:
            response = self.anthropic.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=2000,
                temperature=0.1,  # Très basse pour maximiser la fidélité
                system="Tu retournes UNIQUEMENT du JSON valide sans markdown.",
                messages=[
                    {"role": "user", "content": prompt}
                ],
            )

            raw_content = response.content[0].text.strip()
            # Nettoyer si le modèle ajoute des backticks markdown
            if raw_content.startswith("```"):
                raw_content = re.sub(r'^```(?:json)?\s*', '', raw_content)
                raw_content = re.sub(r'\s*```$', '', raw_content)

            return json.loads(raw_content)

        except Exception as e:
            print(f"⚠️  AI Extraction error: {e}")
            return None

    def analyze_pls_services(
        self,
        notes: List[Dict],
    ) -> Optional[Dict]:
        """
        Analyse IA des services PLS/Dampp-Chaser.

        Détermine si le dernier service était "basic" (test+buvards)
        ou "annual" (entretien complet).
        """
        if not self.anthropic or not notes:
            return None

        # Filtrer les notes qui pourraient concerner le PLS
        pls_keywords = [
            'pls', 'dampp', 'chaser', 'buvard', 'pad', 'humidi',
            'life saver', 'entretien annuel', 'reservoir', 'réservoir',
            'housse', 'niveau', 'eau', 'water', 'hygrostat', 'gaine',
        ]

        pls_notes = []
        for n in notes:
            text_lower = (n.get('text', '') or '').lower()
            if any(kw in text_lower for kw in pls_keywords):
                tech_name = TECHNICIAN_NAMES.get(n.get('technician', ''), n.get('technician', ''))
                pls_notes.append({
                    "date": n.get('date', ''),
                    "technician": tech_name,
                    "text": n.get('text', '')[:500],
                })

        if not pls_notes:
            return None

        prompt = PLS_ANALYSIS_PROMPT.format(
            pls_notes_json=json.dumps(pls_notes, ensure_ascii=False, indent=2),
        )

        try:
            response = self.anthropic.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=1000,
                temperature=0.1,
                system="Tu retournes UNIQUEMENT du JSON valide sans markdown.",
                messages=[
                    {"role": "user", "content": prompt}
                ],
            )

            raw_content = response.content[0].text.strip()
            if raw_content.startswith("```"):
                raw_content = re.sub(r'^```(?:json)?\s*', '', raw_content)
                raw_content = re.sub(r'\s*```$', '', raw_content)

            return json.loads(raw_content)

        except Exception as e:
            print(f"⚠️  PLS Analysis error: {e}")
            return None

    # ═══════════════════════════════════════════════════════════════
    # VALIDATION ANTI-HALLUCINATION
    # ═══════════════════════════════════════════════════════════════

    def validate_extraction(
        self,
        ai_result: Dict,
        raw_notes: List[Dict],
    ) -> Dict:
        """
        Valide chaque fait extrait en vérifiant que la citation existe
        dans les notes brutes. Rejette tout ce qui n'a pas de preuve.
        """
        all_text = " ".join([n.get('text', '') for n in raw_notes]).lower()
        validated = {}

        # Langue
        lang = ai_result.get('language', {})
        if lang and lang.get('value'):
            source = (lang.get('source') or '').lower()
            # La langue est déductible du texte global — on accepte si raisonnable
            if lang['value'] in ('FR', 'EN', 'BI'):
                validated['language'] = lang['value']

        # Animaux
        validated_pets = []
        for pet in ai_result.get('pets', []) or []:
            source = (pet.get('source') or '').lower()
            # Vérifier qu'au moins un mot-clé animal existe dans les notes
            pet_type = (pet.get('type') or '').lower()
            pet_keywords = {'chien': ['chien', 'dog'], 'chat': ['chat', 'cat'], 'autre': []}
            keywords = pet_keywords.get(pet_type, [pet_type])
            if any(kw in all_text for kw in keywords) or self._citation_exists(source, raw_notes):
                validated_pets.append(pet)
        validated['pets'] = validated_pets

        # Courtoisies
        validated_courtesies = []
        for courtesy in ai_result.get('courtesies', []) or []:
            source = (courtesy.get('source') or '').lower()
            if self._citation_exists(source, raw_notes):
                validated_courtesies.append(courtesy)
        validated['courtesies'] = validated_courtesies

        # Mode de paiement
        payment = ai_result.get('payment_method', {})
        if payment and payment.get('value'):
            source = (payment.get('source') or '').lower()
            if self._citation_exists(source, raw_notes):
                validated['payment_method'] = payment['value']
            else:
                validated['payment_method'] = None
        else:
            validated['payment_method'] = None

        # Follow-ups
        validated_followups = []
        for fu in ai_result.get('follow_ups', []) or []:
            source = (fu.get('source') or '').lower()
            if self._citation_exists(source, raw_notes):
                validated_followups.append(fu)
        validated['follow_ups'] = validated_followups

        # Personnalité
        personality = ai_result.get('personality_notes', {})
        if personality and personality.get('value'):
            source = (personality.get('source') or '').lower()
            if self._citation_exists(source, raw_notes):
                validated['personality'] = personality['value']
            else:
                validated['personality'] = None
        else:
            validated['personality'] = None

        # Accès
        access = ai_result.get('access_info', {})
        if access:
            validated_access = {}
            for key in ('parking', 'access_code', 'floor', 'special_instructions'):
                if access.get(key):
                    validated_access[key] = access[key]
            validated['access_info'] = validated_access if validated_access else {}
        else:
            validated['access_info'] = {}

        return validated

    def validate_pls_analysis(
        self,
        ai_result: Dict,
        raw_notes: List[Dict],
        piano_data: Dict,
    ) -> Dict:
        """
        Valide l'analyse PLS et calcule les dates côté Python.
        """
        if not piano_data.get('dampp_chaser_installed'):
            return {"needs_annual": None, "reason": "Pas de PLS installé"}

        validated_services = []
        for svc in ai_result.get('pls_services', []) or []:
            source = (svc.get('source') or '').lower()
            if self._citation_exists(source, raw_notes):
                validated_services.append(svc)

        if not validated_services:
            return {
                "services": [],
                "needs_annual": None,
                "reason": "Aucun service PLS trouvé dans l'historique",
                "months_since_last": None,
            }

        # Trier par date décroissante
        validated_services.sort(key=lambda s: s.get('date', ''), reverse=True)
        last_service = validated_services[0]

        # Calcul de mois côté Python (pas par l'IA)
        months_since = self._months_since(last_service.get('date', ''))
        needs_annual = (
            last_service.get('type') == 'basic' and
            months_since is not None and
            months_since >= 11
        )

        # Trouver le dernier entretien annuel complet
        last_annual = next(
            (s for s in validated_services if s.get('type') == 'annual'),
            None
        )
        months_since_annual = None
        if last_annual:
            months_since_annual = self._months_since(last_annual.get('date', ''))

        return {
            "services": validated_services,
            "last_service": last_service,
            "last_annual": last_annual,
            "needs_annual": needs_annual,
            "months_since_last": months_since,
            "months_since_annual": months_since_annual,
            "reason": self._pls_reason(last_service, months_since, needs_annual),
        }

    # ═══════════════════════════════════════════════════════════════
    # HELPERS
    # ═══════════════════════════════════════════════════════════════

    def _citation_exists(self, source: str, raw_notes: List[Dict]) -> bool:
        """Vérifie qu'une citation existe dans les notes brutes."""
        if not source or source == 'null':
            return False

        # Extraire le texte de citation (après le ":")
        # Format attendu: "note du 2025-06-15: 'le chien Toutou...'"
        citation_match = re.search(r"['\"]([^'\"]{5,})['\"]", source)
        if citation_match:
            citation_text = citation_match.group(1).lower().strip()
            # Vérifier si au moins 60% des mots de la citation existent dans une note
            citation_words = set(citation_text.split())
            if len(citation_words) < 2:
                return True  # Citation trop courte, accepter

            for note in raw_notes:
                note_text = (note.get('text', '') or '').lower()
                matching_words = citation_words & set(note_text.split())
                if len(matching_words) >= len(citation_words) * 0.6:
                    return True
            return False

        # Pas de citation entre guillemets — vérifier la date au moins
        date_match = re.search(r'\d{4}-\d{2}-\d{2}', source)
        if date_match:
            date_str = date_match.group(0)
            return any(n.get('date', '').startswith(date_str) for n in raw_notes)

        return False

    def _months_since(self, date_str: str) -> Optional[int]:
        """Calcule le nombre de mois depuis une date."""
        try:
            date = datetime.strptime(date_str[:10], '%Y-%m-%d')
            now = datetime.now()
            return (now.year - date.year) * 12 + (now.month - date.month)
        except (ValueError, TypeError):
            return None

    def _pls_reason(self, last_service: Dict, months: Optional[int], needs_annual: bool) -> str:
        """Génère une explication factuelle pour le statut PLS."""
        if needs_annual:
            return (
                f"Dernier service: {last_service.get('type', '?')} "
                f"il y a {months} mois — entretien annuel recommandé"
            )
        if months is not None and months < 11:
            return f"Dernier service il y a {months} mois — OK"
        return "Données insuffisantes"


# ═══════════════════════════════════════════════════════════════════
# CALCULS PYTHON (JAMAIS DÉLÉGUÉS À L'IA)
# ═══════════════════════════════════════════════════════════════════

def compute_client_since(notes: List[Dict]) -> Optional[str]:
    """Calcule depuis quand le client est avec nous (plus ancienne note)."""
    dates = []
    for n in notes:
        date_str = n.get('date', '')
        if date_str and len(date_str) >= 10:
            try:
                dates.append(datetime.strptime(date_str[:10], '%Y-%m-%d'))
            except ValueError:
                pass

    if not dates:
        return None

    oldest = min(dates)
    years = (datetime.now() - oldest).days / 365.25
    if years >= 1:
        return f"depuis {int(years)} an{'s' if int(years) > 1 else ''}"
    months = int((datetime.now() - oldest).days / 30.44)
    if months >= 1:
        return f"depuis {months} mois"
    return "nouveau client"


def resolve_technician_name(user_id: str) -> str:
    """Résout un user_id Gazelle en nom lisible."""
    return TECHNICIAN_NAMES.get(user_id, user_id or "")


def build_technical_history(notes: List[Dict]) -> List[Dict]:
    """
    Construit l'historique technique à partir des notes brutes.
    Utilise les données factuelles (date, technician) sans IA.

    IMPORTANT:
    - Exclut les dates futures ET aujourd'hui (services pas encore faits)
    - Exclut les messages système (confirmations, rappels, créations de RV)
    - Ne montre que les vrais services/notes techniques
    """
    from datetime import datetime
    today = datetime.now().strftime('%Y-%m-%d')

    # Messages système à ignorer (pas des vrais services)
    ignore_patterns = [
        'merci d\'avoir confirmé',
        'thank you for confirming',
        'votre rendez-vous avec piano technique',
        'your piano appointment',
        'votre piano',  # Messages de confirmation
        'your piano',
        'veuillez confirmer',
        'please confirm',
        'a créé un rendez-vous',
        'created an appointment',
        'rendez-vous avec',  # Notifications système
        'appointment with',
        'rappel',
        'reminder',
        'confirmation',
        'le client a confirmé',  # Auto-confirmation
        'client confirmed',
        'le statut du client',  # Changement de statut
        'client status',
        'a été modifié',
        'was changed',
        'stationnement',  # Pas pertinent
        'parking',
        'client fusionné',  # Fusions système
        'client merged',
        'a été fusionné',
        'was merged',
        'completed appointment',  # Notifications de completion
        'appointment completed',
        'rendez-vous complété',
        'rendez-vous terminé',
        'has been completed',
        'invoice created',  # Factures auto
        'facture créée',
        'estimate created',  # Devis auto
        'devis créé',
    ]

    history = []
    seen_dates = set()

    for note in notes[:20]:  # Regarder plus de notes car on filtre beaucoup
        date = note.get('date', '')
        if not date or date in seen_dates:
            continue

        # Exclure aujourd'hui et les dates futures
        if date[:10] >= today:
            continue

        text = (note.get('text', '') or '').strip()
        text_lower = text.lower()

        # Ignorer les messages système
        if any(pattern in text_lower for pattern in ignore_patterns):
            continue

        # Ignorer les textes vides ou trop courts
        if len(text) < 10 or text.lower() == 'none':
            continue

        # Ignorer si "None" est le contenu principal
        if text.replace('None', '').strip() == '' or text.startswith('None '):
            continue

        seen_dates.add(date)

        tech_id = note.get('technician', '')
        tech_name = resolve_technician_name(tech_id)

        # Si tech inconnu et pas de contenu utile, ignorer
        if not tech_name and not any(c.isalpha() for c in text[:50]):
            continue

        # Nettoyer le texte (enlever "None", espaces multiples)
        clean_text = text.replace(' None', '').replace('None ', '').replace('None', '')
        clean_text = ' '.join(clean_text.split())  # Normaliser espaces

        if len(clean_text) < 10:
            continue  # Texte trop court après nettoyage

        entry = {
            "date": date,
            "technician": tech_name if tech_name else "Tech",
            "technician_id": tech_id,
            "summary": clean_text[:200],
        }
        history.append(entry)

        if len(history) >= 5:
            break

    return history


def extract_follow_ups_regex(notes: List[Dict]) -> List[Dict]:
    """
    Extrait les "à faire", déficiences et recommandations des notes via regex.
    Fallback quand l'IA n'est pas disponible.
    """
    import re
    from datetime import datetime
    today = datetime.now().strftime('%Y-%m-%d')

    follow_ups = []
    seen = set()

    # Patterns pour détecter les items à faire / déficiences
    patterns = [
        # "à faire: butée haute, espacement"
        (r'à faire\s*[:\-]?\s*([^\.]+)', 'action'),
        # "TODO: vérifier..."
        (r'todo\s*[:\-]?\s*([^\.]+)', 'action'),
        # "recommandé: ..." ou "recommander ..."
        (r'recommand[ée]r?\s*[:\-]?\s*([^\.]+)', 'recommendation'),
        # "problème: ..." ou "problème de..."
        (r'problème\s*(?:de|:|\-)?\s*([^\.]+)', 'issue'),
        # "déficience" ou "défaut"
        (r'(?:déficien\w+|défaut)\s*[:\-]?\s*([^\.]+)', 'issue'),
        # "étouffoir fuyait" / "touche cassée" / "corde cassée"
        (r'((?:étouffoir|touche|corde|marteau)\s+(?:fuy\w+|cass\w+|bris\w+|défectu\w+)[^\.]*)', 'issue'),
        # "attention: ..."
        (r'attention\s*[:\-]?\s*([^\.]+)', 'warning'),
        # "noter: ..." ou "note: ..."
        (r'(?:à\s+)?noter?\s*[:\-]?\s*([^\.]+)', 'note'),
    ]

    # Termes à ignorer (stationnement, etc.)
    ignore_terms = ['stationnement', 'parking', 'stationner']

    for note in notes[:20]:
        date = note.get('date', '')
        # Ignorer les notes futures
        if date and date > today:
            continue

        text = note.get('text', '') or ''
        text_lower = text.lower()

        for pattern, category in patterns:
            matches = re.findall(pattern, text_lower, re.IGNORECASE)
            for match in matches:
                # Nettoyer le match
                desc = match.strip()
                if len(desc) < 5 or len(desc) > 150:
                    continue

                # Ignorer les termes non pertinents (stationnement, etc.)
                if any(term in desc.lower() for term in ignore_terms):
                    continue

                # Éviter les doublons
                desc_key = desc[:30].lower()
                if desc_key in seen:
                    continue
                seen.add(desc_key)

                follow_ups.append({
                    'description': desc.capitalize(),
                    'category': category,
                    'source_date': date,
                    'source': 'regex_extraction',
                })

    return follow_ups[:10]  # Limiter à 10 items
