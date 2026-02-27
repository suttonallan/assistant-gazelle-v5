#!/usr/bin/env python3
"""
Service de parsing pour l'assistant conversationnel.

Parse et analyse les questions en langage naturel pour extraire:
- Type de requête (rendez-vous, recherche, résumé, etc.)
- Entités (dates, noms, lieux, etc.)
- Paramètres de requête
"""

import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum


class QueryType(Enum):
    """Types de requêtes supportées par l'assistant."""
    APPOINTMENTS = "appointments"  # Rendez-vous (.mes rv, mes rv demain)
    SEARCH_CLIENT = "search_client"  # Recherche client (cherche Yamaha)
    SEARCH_PIANO = "search_piano"  # Recherche piano (piano à Montréal)
    SUMMARY = "summary"  # Résumé (résume ma semaine)
    TIMELINE = "timeline"  # Historique (historique du piano X)
    STATS = "stats"  # Statistiques (combien de rv ce mois)
    HELP = "help"  # Aide (.aide)
    UNKNOWN = "unknown"  # Type non reconnu


class ConversationalParser:
    """Parser de questions en langage naturel pour l'assistant Gazelle."""

    # Patterns de commandes rapides
    QUICK_COMMANDS = {
        r'^\.mes\s+rv$': QueryType.APPOINTMENTS,
        r'^\.aide$': QueryType.HELP,
        r'^\.help$': QueryType.HELP,
    }

    # Keywords pour identifier le type de requête
    KEYWORDS = {
        QueryType.APPOINTMENTS: [
            'rendez-vous', 'rv', 'appointment', 'rdv',
            'mes rv', 'agenda', 'calendrier', 'prochains rv'
        ],
        QueryType.SEARCH_CLIENT: [
            'cherche', 'trouve', 'client', 'recherche',
            'où est', 'trouver', 'localiser'
        ],
        QueryType.SEARCH_PIANO: [
            'piano', 'pianos', 'instrument', 'instruments'
        ],
        QueryType.SUMMARY: [
            'résume', 'resume', 'résumé', 'summary',
            'semaine', 'mois', 'période'
        ],
        QueryType.TIMELINE: [
            'historique', 'histoire', 'timeline', 'passé',
            'dernières interventions', 'derniers événements',
            'notes de service', 'historique complet', 'toutes les notes',
            'montre-moi l\'historique', 'affiche l\'historique'
        ],
        QueryType.STATS: [
            'combien', 'statistiques', 'stats', 'nombre',
            'total', 'compte'
        ]
    }

    # Patterns de dates relatives
    # NOTE: Les patterns composés (après-demain, avant-hier) utilisent un lookbehind négatif
    # pour éviter les doubles matches
    DATE_PATTERNS = {
        r'\baprès[\s-]?demain\b': lambda: datetime.now() + timedelta(days=2),
        r'\bapres[\s-]?demain\b': lambda: datetime.now() + timedelta(days=2),  # Sans accent
        r'(?<!après[\s-])(?<!apres[\s-])(?<!après)(?<!apres)\bdemain\b': lambda: datetime.now() + timedelta(days=1),
        r'\baujourd\'?hui\b': lambda: datetime.now(),
        r'\bavant[\s-]?hier\b': lambda: datetime.now() - timedelta(days=2),
        r'(?<!avant[\s-])(?<!avant)\bhier\b': lambda: datetime.now() - timedelta(days=1),
        r'\bcette\s+semaine\b': lambda: datetime.now(),
        r'\bla\s+semaine\s+prochaine\b': lambda: datetime.now() + timedelta(weeks=1),
        r'\bce\s+mois\b': lambda: datetime.now(),
        r'\ble\s+mois\s+prochain\b': lambda: datetime.now() + timedelta(days=30),
    }
    
    # Mapping des jours de la semaine (français et anglais)
    WEEKDAY_NAMES = {
        'lundi': 0, 'monday': 0,
        'mardi': 1, 'tuesday': 1,
        'mercredi': 2, 'wednesday': 2,
        'jeudi': 3, 'thursday': 3,
        'vendredi': 4, 'friday': 4,
        'samedi': 5, 'saturday': 5,
        'dimanche': 6, 'sunday': 6,
    }
    
    # Mapping des jours de la semaine (français et anglais)
    WEEKDAY_NAMES = {
        'lundi': 0, 'monday': 0,
        'mardi': 1, 'tuesday': 1,
        'mercredi': 2, 'wednesday': 2,
        'jeudi': 3, 'thursday': 3,
        'vendredi': 4, 'friday': 4,
        'samedi': 5, 'saturday': 5,
        'dimanche': 6, 'sunday': 6,
    }

    def __init__(self):
        """Initialise le parser conversationnel."""
        pass

    def parse(self, question: str) -> Dict[str, Any]:
        """
        Parse une question en langage naturel.

        Args:
            question: Question de l'utilisateur

        Returns:
            Dictionnaire contenant:
                - query_type: Type de requête (QueryType)
                - original_query: Question originale
                - params: Paramètres extraits (dates, noms, etc.)
                - confidence: Niveau de confiance (0-1)
        """
        question = question.strip()

        # Vérifier les commandes rapides
        for pattern, query_type in self.QUICK_COMMANDS.items():
            if re.match(pattern, question, re.IGNORECASE):
                return {
                    'query_type': query_type,
                    'original_query': question,
                    'params': {},
                    'confidence': 1.0
                }

        # Identifier le type de requête via keywords
        query_type, confidence = self._identify_query_type(question)

        # Extraire les paramètres selon le type
        params = self._extract_params(question, query_type)

        # Détecter "tous les rv" ou "les rv de tous" pour bypass filtre technicien
        if query_type == QueryType.APPOINTMENTS:
            if re.search(r'\b(tous les rv|les rv de tous|tous les rendez-vous|agenda complet)\b', question, re.IGNORECASE):
                params['show_all'] = True

        return {
            'query_type': query_type,
            'original_query': question,
            'params': params,
            'confidence': confidence
        }

    def _identify_query_type(self, question: str) -> Tuple[QueryType, float]:
        """
        Identifie le type de requête via analyse des keywords.

        Args:
            question: Question de l'utilisateur

        Returns:
            (QueryType, confidence_score)
        """
        question_lower = question.lower()

        # Compter les matches pour chaque type
        scores = {}
        for query_type, keywords in self.KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in question_lower)
            if score > 0:
                scores[query_type] = score

        if not scores:
            # Si aucun keyword trouvé, vérifier si c'est un nom propre

            # Pattern 1: Nom complet (2+ mots avec ou sans majuscules)
            # Ex: "olivier asselin", "Jean-Philippe Dumoulin"
            name_pattern = r'^[A-ZÀÂÄÇÉÈÊËÏÎÔÙÛÜ][a-zàâäçéèêëïîôùûüœ\-]+(?:\s+[A-ZÀÂÄÇÉÈÊËÏÎÔÙÛÜ][a-zàâäçéèêëïîôùûüœ\-]+)+$'
            simple_name_pattern = r'^[a-zàâäçéèêëïîôùûüœ\-]+(?:\s+[a-zàâäçéèêëïîôùûüœ\-]+)+$'

            # Pattern 2: Un seul mot avec majuscule (probablement un prénom ou nom)
            # Ex: "Olivier", "Lucie", "Jean-Philippe"
            single_word_capitalized = r'^[A-ZÀÂÄÇÉÈÊËÏÎÔÙÛÜ][a-zàâäçéèêëïîôùûüœ\-]{2,}$'

            # Pattern 3: Un seul mot minuscule mais assez long (probablement un nom)
            # Ex: "olivier", "lucie" (3+ lettres pour éviter "ok", "le", etc.)
            single_word_lowercase = r'^[a-zàâäçéèêëïîôùûüœ\-]{3,}$'

            if (re.match(name_pattern, question.strip()) or
                re.match(simple_name_pattern, question_lower) or
                re.match(single_word_capitalized, question.strip()) or
                re.match(single_word_lowercase, question_lower)):
                # C'est probablement un nom → recherche client
                return QueryType.SEARCH_CLIENT, 0.5

            return QueryType.UNKNOWN, 0.0

        # Règles de priorité spéciales
        # Si "historique" ou "timeline" est présent, forcer TIMELINE (même si d'autres mots-clés matchent)
        if QueryType.TIMELINE in scores and any(kw in question_lower for kw in ['historique', 'timeline', 'notes de service']):
            print(f"🔍 Parser: Priorité TIMELINE détectée (mots-clés: historique/timeline/notes)")
            return QueryType.TIMELINE, 0.9

        # Retourner le type avec le plus de matches
        best_type = max(scores, key=scores.get)
        max_score = scores[best_type]

        # Calculer la confiance (0-1)
        total_keywords = len(self.KEYWORDS[best_type])
        confidence = min(max_score / total_keywords, 1.0)

        return best_type, confidence

    def _extract_params(self, question: str, query_type: QueryType) -> Dict[str, Any]:
        """
        Extrait les paramètres selon le type de requête.

        Args:
            question: Question de l'utilisateur
            query_type: Type de requête identifié

        Returns:
            Dictionnaire de paramètres
        """
        params = {}

        # Extraire les dates
        dates = self._extract_dates(question)
        if dates:
            params['dates'] = dates

        # Extraire les noms/termes de recherche
        if query_type in [QueryType.SEARCH_CLIENT, QueryType.SEARCH_PIANO]:
            search_terms = self._extract_search_terms(question)
            if search_terms:
                params['search_terms'] = search_terms

        # Extraire les périodes pour résumés/stats ET pour les rendez-vous sur une plage
        if query_type in [QueryType.SUMMARY, QueryType.STATS, QueryType.APPOINTMENTS]:
            period = self._extract_period(question)
            if period:
                params['period'] = period

        return params

    def _extract_dates(self, question: str) -> List[datetime]:
        """
        Extrait les dates depuis la question.

        Args:
            question: Question de l'utilisateur

        Returns:
            Liste de dates identifiées
        """
        dates = []

        # Chercher les patterns de dates relatives
        for pattern, date_func in self.DATE_PATTERNS.items():
            if re.search(pattern, question, re.IGNORECASE):
                dates.append(date_func())

        # Chercher les jours de la semaine (lundi, mardi, vendredi, etc.)
        question_lower = question.lower()
        for day_name, target_weekday in self.WEEKDAY_NAMES.items():
            if re.search(r'\b' + day_name + r'\b', question_lower):
                now = datetime.now()
                current_weekday = now.weekday()
                # Calculer le nombre de jours jusqu'au jour cible
                days_ahead = target_weekday - current_weekday
                # Si le jour est déjà passé cette semaine, prendre celui de la semaine prochaine
                if days_ahead < 0:
                    days_ahead += 7
                # Si c'est aujourd'hui et qu'on demande explicitement le jour, prendre celui de la semaine prochaine
                elif days_ahead == 0:
                    # Vérifier si c'est une demande explicite (pas juste "aujourd'hui")
                    if day_name in question_lower and not re.search(r'\baujourd\'?hui\b', question_lower):
                        days_ahead = 7
                target_date = now + timedelta(days=days_ahead)
                dates.append(target_date)
                break  # Un seul jour de la semaine par requête

        # Chercher les dates absolues (JJ/MM/AAAA, AAAA-MM-JJ, etc.)
        date_formats = [
            r'\b(\d{1,2})/(\d{1,2})/(\d{4})\b',  # 15/12/2024
            r'\b(\d{4})-(\d{2})-(\d{2})\b',  # 2024-12-15
        ]

        for fmt in date_formats:
            matches = re.finditer(fmt, question)
            for match in matches:
                try:
                    if '/' in fmt:
                        day, month, year = match.groups()
                        dates.append(datetime(int(year), int(month), int(day)))
                    else:
                        year, month, day = match.groups()
                        dates.append(datetime(int(year), int(month), int(day)))
                except ValueError:
                    continue  # Date invalide, ignorer

        return dates

    def _extract_search_terms(self, question: str) -> List[str]:
        """
        Extrait les termes de recherche depuis la question.

        Args:
            question: Question de l'utilisateur

        Returns:
            Liste de termes de recherche
        """
        # Retirer les mots-clés de commande
        stop_words = [
            'cherche', 'trouve', 'client', 'recherche',
            'où', 'est', 'trouver', 'localiser', 'le', 'la', 'les',
            'un', 'une', 'des', 'piano', 'pianos',
            'frais', 'déplacement', 'deplacement', 'pour'
        ]

        # Préserver la casse pour les IDs Gazelle (cli_xxx, pia_xxx, etc.)
        # mais comparer les stop words en minuscules
        words = question.split()
        search_terms = [
            word for word in words
            if word.lower() not in stop_words and len(word) > 2
        ]

        return search_terms

    def _extract_period(self, question: str) -> Optional[Dict[str, datetime]]:
        """
        Extrait la période de temps (pour résumés/stats).

        Args:
            question: Question de l'utilisateur

        Returns:
            Dictionnaire avec start_date et end_date, ou None
        """
        now = datetime.now()

        # Semaine en cours
        if re.search(r'\bcette\s+semaine\b', question, re.IGNORECASE):
            start = now - timedelta(days=now.weekday())
            end = start + timedelta(days=6)
            return {'start_date': start, 'end_date': end}

        # Mois en cours
        if re.search(r'\bce\s+mois\b', question, re.IGNORECASE):
            start = now.replace(day=1)
            # Dernier jour du mois
            if now.month == 12:
                end = now.replace(year=now.year + 1, month=1, day=1) - timedelta(days=1)
            else:
                end = now.replace(month=now.month + 1, day=1) - timedelta(days=1)
            return {'start_date': start, 'end_date': end}

        # 7 derniers jours
        if re.search(r'\b7\s+derniers?\s+jours?\b', question, re.IGNORECASE):
            return {
                'start_date': now - timedelta(days=7),
                'end_date': now
            }

        # 30 derniers jours
        if re.search(r'\b30\s+derniers?\s+jours?\b', question, re.IGNORECASE):
            return {
                'start_date': now - timedelta(days=30),
                'end_date': now
            }

        return None

    def format_help_response(self) -> str:
        """
        Génère le message d'aide.

        Returns:
            Message d'aide formaté
        """
        return """
🤖 **Assistant Gazelle - Commandes Disponibles**

**Rendez-vous:**
- `.mes rv` - Vos rendez-vous aujourd'hui
- `mes rendez-vous demain` - RV de demain
- `mes rv cette semaine` - RV de la semaine

**Recherche:**
- `cherche Yamaha Montreal` - Recherche client/piano
- `piano à Montreal` - Pianos dans une ville

**Résumés:**
- `résume ma semaine` - Résumé de la semaine
- `résume ce mois` - Résumé du mois

**Statistiques:**
- `combien de rv ce mois` - Nombre de RV
- `stats cette semaine` - Statistiques

**Questions libres (admin/assistantes):**
- `quelles sont les dernières églises accordées ?`
- `combien avons-nous chargé pour remplacer des marteaux ?`
- `clients à Laval pas vus depuis 1 an ?`
- L'assistant apprend de chaque nouvelle question !

**Aide:**
- `.aide` ou `.help` - Affiche ce message
"""


# Instance singleton
_parser_instance: Optional[ConversationalParser] = None


def get_parser() -> ConversationalParser:
    """
    Retourne l'instance singleton du parser.

    Returns:
        Instance de ConversationalParser
    """
    global _parser_instance

    if _parser_instance is None:
        _parser_instance = ConversationalParser()

    return _parser_instance
