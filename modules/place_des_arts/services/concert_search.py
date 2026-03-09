"""
Recherche de programmes de concerts à Place des Arts.

Utilise l'API de recherche du site placedesarts.com pour trouver
les spectacles correspondant à une demande (artiste, date, salle).
"""

import logging
import re
from datetime import datetime
from typing import Optional
from urllib.parse import quote_plus

import httpx

logger = logging.getLogger(__name__)

# URL de recherche Place des Arts
PDA_SEARCH_URL = "https://placedesarts.com/fr/recherche"
PDA_CALENDAR_URL = "https://placedesarts.com/fr/calendrier"
PDA_BASE_URL = "https://placedesarts.com"

# Mapping des codes de salle internes vers les noms officiels PDA
ROOM_NAMES = {
    "WP": "Salle Wilfrid-Pelletier",
    "TM": "Théâtre Maisonneuve",
    "MS": "Maison symphonique",
    "SD": "Salle de récital",
    "C5": "Cinquième Salle",
    "5E": "Cinquième Salle",
    "SCL": "Salle Claude-Léveillée",
    "CL": "Salle Claude-Léveillée",
    "ODM": "Espace culturel Georges-Émile-Lapalme",
}


async def rechercher_concert(
    for_who: str,
    appointment_date: Optional[str] = None,
    room: Optional[str] = None,
) -> dict:
    """
    Recherche un concert sur placedesarts.com.

    Args:
        for_who: Nom de l'artiste ou de l'ensemble
        appointment_date: Date du rendez-vous (YYYY-MM-DD)
        room: Code de la salle (WP, TM, MS, etc.)

    Returns:
        dict avec les résultats trouvés
    """
    if not for_who or not for_who.strip():
        return {"found": False, "message": "Aucun artiste spécifié", "results": []}

    query = for_who.strip()
    salle_nom = ROOM_NAMES.get((room or "").upper(), None)

    # Construire l'URL de recherche
    search_url = f"{PDA_SEARCH_URL}?q={quote_plus(query)}"

    logger.info(f"Recherche concert PDA: '{query}' (date={appointment_date}, salle={room})")

    try:
        async with httpx.AsyncClient(
            timeout=15.0,
            follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; PianoTekBot/1.0)",
                "Accept": "text/html,application/xhtml+xml",
                "Accept-Language": "fr-CA,fr;q=0.9",
            },
        ) as client:
            response = await client.get(search_url)
            response.raise_for_status()
            html = response.text

        # Extraire les résultats de la page de recherche
        resultats = _extraire_resultats_recherche(html, query, appointment_date, salle_nom)

        if resultats:
            return {
                "found": True,
                "query": query,
                "search_url": search_url,
                "salle": salle_nom,
                "date": appointment_date,
                "results": resultats,
                "message": f"{len(resultats)} spectacle(s) trouvé(s)",
            }
        else:
            # Aucun résultat — retourner le lien de recherche quand même
            return {
                "found": False,
                "query": query,
                "search_url": search_url,
                "salle": salle_nom,
                "date": appointment_date,
                "results": [],
                "message": f"Aucun spectacle trouvé pour « {query} »",
            }

    except httpx.TimeoutException:
        logger.warning(f"Timeout recherche PDA pour '{query}'")
        return {
            "found": False,
            "query": query,
            "search_url": search_url,
            "results": [],
            "message": "Délai d'attente dépassé — essayez le lien direct",
        }
    except Exception as e:
        logger.error(f"Erreur recherche PDA: {e}")
        return {
            "found": False,
            "query": query,
            "search_url": search_url,
            "results": [],
            "message": f"Erreur de recherche: {str(e)}",
        }


def _extraire_resultats_recherche(
    html: str,
    query: str,
    appointment_date: Optional[str],
    salle_nom: Optional[str],
) -> list:
    """
    Parse le HTML de la page de recherche PDA pour extraire les spectacles.
    Utilise des regex simples pour éviter une dépendance lourde (BeautifulSoup).
    """
    resultats = []

    # Chercher les liens de spectacles dans le HTML
    # Pattern typique : <a href="/fr/evenement/..." class="...">
    event_pattern = re.compile(
        r'<a[^>]+href="(/fr/(?:evenement|spectacle|programmation)[^"]*)"[^>]*>'
        r'(.*?)</a>',
        re.DOTALL | re.IGNORECASE,
    )

    # Pattern pour les titres de cartes / résultats
    card_pattern = re.compile(
        r'<(?:h[2-4]|div|span)[^>]*class="[^"]*(?:title|titre|card|result)[^"]*"[^>]*>'
        r'\s*(.*?)\s*</(?:h[2-4]|div|span)>',
        re.DOTALL | re.IGNORECASE,
    )

    # Extraire les événements depuis les liens
    seen_urls = set()
    for match in event_pattern.finditer(html):
        url_path = match.group(1)
        text_brut = re.sub(r'<[^>]+>', ' ', match.group(2)).strip()
        text_brut = re.sub(r'\s+', ' ', text_brut)

        if not text_brut or len(text_brut) < 3:
            continue
        if url_path in seen_urls:
            continue
        seen_urls.add(url_path)

        # Vérifier la pertinence par rapport à la recherche
        query_lower = query.lower()
        text_lower = text_brut.lower()
        query_words = query_lower.split()
        if not any(w in text_lower for w in query_words if len(w) > 2):
            continue

        result = {
            "titre": text_brut[:200],
            "url": f"{PDA_BASE_URL}{url_path}",
        }

        # Chercher une date dans le texte environnant
        date_match = re.search(
            r'(\d{1,2}\s+(?:janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre)\s+\d{4})',
            html[max(0, match.start() - 500) : match.end() + 500],
            re.IGNORECASE,
        )
        if date_match:
            result["date_spectacle"] = date_match.group(1)

        # Chercher le nom de la salle
        if salle_nom:
            salle_match = re.search(
                re.escape(salle_nom),
                html[max(0, match.start() - 500) : match.end() + 500],
                re.IGNORECASE,
            )
            if salle_match:
                result["salle"] = salle_nom

        resultats.append(result)

    # Dédupliquer et limiter
    return resultats[:5]
