"""
Recherche de programmes de concerts à Place des Arts.

Tente d'abord de trouver la page de l'événement directement sur
placedesarts.com/evenement/{slug}, puis fait un lien vers la
programmation si pas trouvé.
"""

import logging
import re
from typing import Optional
from urllib.parse import quote_plus

import httpx

logger = logging.getLogger(__name__)

PDA_BASE_URL = "https://www.placedesarts.com"
PDA_PROGRAMMING_URL = f"{PDA_BASE_URL}/fr/programmation"

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

# User-Agent réaliste pour éviter les blocages 403
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "fr-CA,fr;q=0.9,en;q=0.5",
}


def _slugify(text: str) -> str:
    """Convertit un nom d'artiste en slug URL potentiel."""
    import unicodedata
    text = unicodedata.normalize('NFKD', text.lower())
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_]+', '-', text.strip())
    return text


async def rechercher_concert(
    for_who: str,
    appointment_date: Optional[str] = None,
    room: Optional[str] = None,
) -> dict:
    """
    Recherche un concert sur placedesarts.com.

    Stratégie:
    1. Tenter l'accès direct via /evenement/{slug}
    2. Si pas trouvé, retourner un lien vers la page de programmation
    """
    if not for_who or not for_who.strip():
        return {"found": False, "message": "Aucun artiste spécifié", "results": []}

    query = for_who.strip()
    salle_nom = ROOM_NAMES.get((room or "").upper(), None)

    # Générer des slugs candidats à partir du nom
    slugs = _generate_slug_candidates(query)

    logger.info(f"Recherche concert PDA: '{query}' (date={appointment_date}, salle={room}, slugs={slugs[:3]})")

    # Lien de recherche Google comme fallback
    google_search_url = f"https://www.google.com/search?q={quote_plus(f'site:placedesarts.com {query}')}"
    programming_url = PDA_PROGRAMMING_URL

    try:
        async with httpx.AsyncClient(
            timeout=10.0,
            follow_redirects=True,
            headers=_HEADERS,
        ) as client:
            # Stratégie 1: Essayer les URLs directes /evenement/{slug}
            for slug in slugs:
                event_url = f"{PDA_BASE_URL}/evenement/{slug}"
                try:
                    resp = await client.get(event_url)
                    if resp.status_code == 200:
                        # Extraire le titre de la page
                        titre = _extract_title(resp.text) or query
                        result = {
                            "titre": titre,
                            "url": str(resp.url),  # URL finale après redirects
                        }
                        # Chercher la date du spectacle
                        date_spectacle = _extract_date(resp.text)
                        if date_spectacle:
                            result["date_spectacle"] = date_spectacle
                        # Chercher la salle
                        salle_trouvee = _extract_salle(resp.text)
                        if salle_trouvee:
                            result["salle"] = salle_trouvee

                        return {
                            "found": True,
                            "query": query,
                            "search_url": str(resp.url),
                            "salle": salle_nom or salle_trouvee,
                            "date": appointment_date,
                            "results": [result],
                            "message": "Spectacle trouvé",
                        }
                except httpx.HTTPStatusError:
                    continue
                except Exception:
                    continue

            # Stratégie 2: Essayer la page de programmation et chercher dedans
            try:
                resp = await client.get(PDA_PROGRAMMING_URL)
                if resp.status_code == 200:
                    resultats = _extraire_resultats_programmation(resp.text, query)
                    if resultats:
                        return {
                            "found": True,
                            "query": query,
                            "search_url": programming_url,
                            "salle": salle_nom,
                            "date": appointment_date,
                            "results": resultats,
                            "message": f"{len(resultats)} spectacle(s) trouvé(s)",
                        }
            except Exception as e:
                logger.warning(f"Erreur accès programmation PDA: {e}")

    except httpx.TimeoutException:
        logger.warning(f"Timeout recherche PDA pour '{query}'")
    except Exception as e:
        logger.warning(f"Erreur recherche PDA: {e}")

    # Fallback: pas trouvé, retourner le lien Google
    return {
        "found": False,
        "query": query,
        "search_url": google_search_url,
        "salle": salle_nom,
        "date": appointment_date,
        "results": [],
        "message": f"Aucun résultat direct — recherchez sur Google",
    }


def _generate_slug_candidates(query: str) -> list:
    """Génère plusieurs slugs candidats à partir du nom de l'artiste."""
    candidates = []
    # Slug direct du nom complet
    candidates.append(_slugify(query))
    # Premiers mots seulement (souvent le nom de famille ou nom court)
    words = query.strip().split()
    if len(words) > 1:
        # Nom de famille seul (dernier mot)
        candidates.append(_slugify(words[-1]))
        # Prénom + nom
        candidates.append(_slugify(f"{words[0]} {words[-1]}"))
        # Premier mot seul (si c'est un nom de groupe)
        candidates.append(_slugify(words[0]))
    # Retirer les doublons tout en gardant l'ordre
    seen = set()
    unique = []
    for c in candidates:
        if c and c not in seen:
            seen.add(c)
            unique.append(c)
    return unique[:5]


def _extract_title(html: str) -> Optional[str]:
    """Extrait le titre de la page."""
    m = re.search(r'<title[^>]*>(.*?)</title>', html, re.DOTALL | re.IGNORECASE)
    if m:
        titre = re.sub(r'<[^>]+>', '', m.group(1)).strip()
        # Retirer le suffixe "| Place des Arts"
        titre = re.sub(r'\s*\|\s*Place des Arts.*$', '', titre, flags=re.IGNORECASE).strip()
        return titre if titre else None
    return None


def _extract_date(html: str) -> Optional[str]:
    """Extrait une date de spectacle depuis le HTML."""
    m = re.search(
        r'(\d{1,2}\s+(?:janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre)\s+\d{4})',
        html, re.IGNORECASE,
    )
    return m.group(1) if m else None


def _extract_salle(html: str) -> Optional[str]:
    """Extrait le nom de la salle depuis le HTML."""
    for salle in ROOM_NAMES.values():
        if salle.lower() in html.lower():
            return salle
    return None


def _extraire_resultats_programmation(html: str, query: str) -> list:
    """Extrait les événements pertinents depuis la page de programmation PDA."""
    resultats = []
    query_lower = query.lower()
    query_words = [w for w in query_lower.split() if len(w) > 2]

    # Chercher les liens d'événements
    event_pattern = re.compile(
        r'<a[^>]+href="(/(?:fr/)?evenement/[^"]*)"[^>]*>(.*?)</a>',
        re.DOTALL | re.IGNORECASE,
    )

    seen_urls = set()
    for match in event_pattern.finditer(html):
        url_path = match.group(1)
        text_brut = re.sub(r'<[^>]+>', ' ', match.group(2)).strip()
        text_brut = re.sub(r'\s+', ' ', text_brut)

        if not text_brut or len(text_brut) < 3 or url_path in seen_urls:
            continue
        seen_urls.add(url_path)

        text_lower = text_brut.lower()
        if not any(w in text_lower for w in query_words):
            continue

        result = {
            "titre": text_brut[:200],
            "url": f"{PDA_BASE_URL}{url_path}",
        }

        date_match = re.search(
            r'(\d{1,2}\s+(?:janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre)\s+\d{4})',
            html[max(0, match.start() - 500): match.end() + 500],
            re.IGNORECASE,
        )
        if date_match:
            result["date_spectacle"] = date_match.group(1)

        resultats.append(result)

    return resultats[:5]
