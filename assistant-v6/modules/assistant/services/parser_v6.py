#!/usr/bin/env python3
"""
Parser v6 - Architecture propre avec priorités claires

Pilier #2: Parser de Priorité
- Distinction claire entre passé (TIMELINE) et futur (APPOINTMENTS)
- Règles de priorité pour éviter les ambiguïtés
"""

from enum import Enum
from typing import Tuple


class QueryType(Enum):
    """Types de requêtes supportés par l'assistant v6"""
    TIMELINE = "timeline"  # Historique, notes de service (PASSÉ)
    APPOINTMENTS = "appointments"  # Rendez-vous, calendrier (FUTUR)
    SEARCH_CLIENT = "search_client"  # Recherche de clients
    CLIENT_INFO = "client_info"  # Infos client (paiement, etc.)
    DEDUCTIONS = "deductions"  # Recommandations basées sur piano attributes
    VALIDATE_PDA = "validate_pda"  # Validation cohérence Place des Arts <-> Gazelle
    UNKNOWN = "unknown"


# Mots-clés pour chaque type de requête
QUERY_KEYWORDS = {
    QueryType.TIMELINE: [
        # Mots-clés principaux
        'historique', 'histoire', 'timeline', 'passé',
        'notes de service', 'toutes les notes', 'service history',
        'montre-moi l\'historique', 'affiche l\'historique',

        # Verbes au passé
        'a fait', 'a été', 'avait', 'était',

        # Événements passés
        'dernière visite', 'dernier service', 'anciennes notes',
        'ce qui s\'est passé', 'qu\'est-ce qui s\'est passé',
    ],

    QueryType.APPOINTMENTS: [
        # Mots-clés temporels (futur)
        'rendez-vous', 'rv', 'rdv', 'appointment',
        'demain', 'après-midi', 'matin', 'soir',
        'aujourd\'hui', 'cette semaine', 'semaine prochaine',
        'ce mois', 'mois prochain',
        'quand', 'quel jour', 'quelle heure',

        # Verbes au futur
        'mes rv', 'prochain', 'à venir', 'planifié', 'prévu',
        'calendrier', 'agenda', 'horaire',
    ],

    QueryType.SEARCH_CLIENT: [
        # Recherche de clients
        'trouve', 'cherche', 'recherche', 'qui est',
        'client', 'contact', 'personne',
        'téléphone', 'adresse', 'email', 'courriel',
    ],

    QueryType.CLIENT_INFO: [
        # Informations financières/administratives
        'a payé', 'paiement', 'facture', 'en retard',
        'doit', 'balance', 'compte', 'facturation',
        'adresse', 'coordonnées', 'informations',
    ],

    QueryType.DEDUCTIONS: [
        # Recommandations/préparation
        'apporter', 'préparer', 'kit', 'équipement',
        'humidité', 'système', 'player',
        'qu\'est-ce que je dois', 'que dois-je',
    ],

    QueryType.VALIDATE_PDA: [
        # Validation Place des Arts
        'vérifie place des arts', 'valide place des arts',
        'cohérence place des arts', 'pda', 'place des arts',
        'incohérences', 'alertes pda', 'problèmes place des arts',
    ],
}


def parse_query(question: str) -> Tuple[QueryType, float]:
    """
    Parse une question et détermine son type avec un score de confiance.

    Args:
        question: La question de l'utilisateur

    Returns:
        Tuple (QueryType, confidence_score)

    Exemple:
        >>> parse_query("montre-moi l'historique de Michelle Alie")
        (QueryType.TIMELINE, 0.95)

        >>> parse_query("mes rv demain")
        (QueryType.APPOINTMENTS, 0.90)
    """
    question_lower = question.lower().strip()

    # Calculer les scores pour chaque type
    scores = {}
    for query_type, keywords in QUERY_KEYWORDS.items():
        score = 0.0
        matches = []

        for keyword in keywords:
            if keyword in question_lower:
                score += 1.0
                matches.append(keyword)

        # Normaliser le score (0-1)
        if score > 0:
            scores[query_type] = min(score / len(keywords), 1.0)
            print(f"🔍 Parser v6: {query_type.value} score={scores[query_type]:.2f} (matches: {matches})")

    # RÈGLES DE PRIORITÉ (évite les ambiguïtés)

    # Priorité 1: Si "historique" ou "notes de service" présent → FORCER TIMELINE
    timeline_priority_keywords = ['historique', 'timeline', 'notes de service', 'toutes les notes', 'service history']
    if any(kw in question_lower for kw in timeline_priority_keywords):
        print(f"🎯 Parser v6: TIMELINE priorité détectée (mots-clés critiques)")
        return QueryType.TIMELINE, 0.95

    # Priorité 2: Si mots temporels futurs → FORCER APPOINTMENTS
    future_keywords = ['demain', 'prochain', 'à venir', 'mes rv', 'calendrier', 'agenda']
    if any(kw in question_lower for kw in future_keywords):
        print(f"🎯 Parser v6: APPOINTMENTS priorité détectée (futur)")
        return QueryType.APPOINTMENTS, 0.90

    # Priorité 3: Si mots de recherche + nom → SEARCH_CLIENT
    search_keywords = ['trouve', 'cherche', 'recherche', 'qui est']
    if any(kw in question_lower for kw in search_keywords):
        print(f"🎯 Parser v6: SEARCH_CLIENT priorité détectée")
        return QueryType.SEARCH_CLIENT, 0.85

    # Priorité 4: Si commence par "client " ou juste un nom (2-3 mots) → SEARCH_CLIENT
    # Exemples: "client michelle", "michelle sutton", "jean-philippe"
    if question_lower.startswith('client '):
        print(f"🎯 Parser v6: SEARCH_CLIENT détecté (préfixe 'client')")
        return QueryType.SEARCH_CLIENT, 0.80

    # Si pas de mot-clé mais 1-3 mots qui ressemblent à un nom → SEARCH_CLIENT
    words = question_lower.split()
    if 1 <= len(words) <= 3 and not scores:
        # Vérifier que ce n'est pas un mot-clé système
        system_words = ['aide', 'help', 'bonjour', 'salut', 'merci']
        if not any(w in words for w in system_words):
            print(f"🎯 Parser v6: SEARCH_CLIENT inféré (nom simple: {question})")
            return QueryType.SEARCH_CLIENT, 0.75

    # Pas de règle de priorité → prendre le meilleur score
    if scores:
        best_type = max(scores.items(), key=lambda x: x[1])
        print(f"✅ Parser v6: Type détecté = {best_type[0].value} (confiance: {best_type[1]:.2f})")
        return best_type[0], best_type[1]

    # Aucun match
    print(f"❓ Parser v6: Type UNKNOWN (aucun mot-clé trouvé)")
    return QueryType.UNKNOWN, 0.0


def extract_entity_name(question: str, query_type: QueryType) -> str:
    """
    Extrait le nom de l'entité (client, technicien) de la question.

    Args:
        question: La question de l'utilisateur
        query_type: Type de requête détecté

    Returns:
        Nom de l'entité ou chaîne vide

    Exemple:
        >>> extract_entity_name("historique de Michelle Alie", QueryType.TIMELINE)
        "Michelle Alie"

        >>> extract_entity_name("mes rv demain", QueryType.APPOINTMENTS)
        ""  # "mes rv" = technicien actuel
    """
    question_lower = question.lower().strip()

    # Patterns de préfixes à enlever
    prefixes_to_remove = [
        'montre-moi l\'historique complet de ',
        'montre-moi l\'historique de ',
        'affiche l\'historique de ',
        'historique de ',
        'historique complet de ',
        'timeline de ',
        'notes de service de ',
        'toutes les notes de ',
        'trouve ',
        'cherche ',
        'recherche ',
        'qui est ',
        'client ',  # Nouveau: supporter "client michelle"
        'rendez-vous de ',
        'rv de ',
        'rdv de ',
        'calendrier de ',
    ]

    # Suffixes à enlever
    suffixes_to_remove = [
        ' avec toutes les notes de service',
        ' avec toutes les notes',
        ' notes de service',
        ' demain',
        ' aujourd\'hui',
        ' cette semaine',
        ' ce mois',
    ]

    # Nettoyer la question
    cleaned = question

    for prefix in prefixes_to_remove:
        if cleaned.lower().startswith(prefix):
            cleaned = cleaned[len(prefix):]
            break

    for suffix in suffixes_to_remove:
        if cleaned.lower().endswith(suffix):
            cleaned = cleaned[:-len(suffix)]

    # Nettoyer les espaces
    cleaned = cleaned.strip()

    print(f"📝 Parser v6: Entité extraite = '{cleaned}'")
    return cleaned


# Tests rapides
if __name__ == "__main__":
    # Tests
    test_questions = [
        "montre-moi l'historique complet de Monique Hallé avec toutes les notes de service",
        "mes rv demain",
        "trouve Michelle Alie",
        "ce client a payé ses factures en retard",
        "apporter le kit d'entretien",
        "calendrier de Nick cette semaine",
    ]

    print("="*80)
    print("Tests Parser v6")
    print("="*80)

    for q in test_questions:
        print(f"\nQuestion: {q}")
        query_type, confidence = parse_query(q)
        entity = extract_entity_name(q, query_type)
        print(f"→ Type: {query_type.value} (confiance: {confidence:.0%})")
        print(f"→ Entité: '{entity}'")
        print("-"*80)
