"""Analyse de photos de piano par l'IA (vision), pour Ivo et l'assistant.

Le prompt d'expert vient du chat client du site (dépôt ptm-chat-api, services/piano_analysis.py),
pour que l'équipe et le chat jugent un piano de la même façon. Ici l'analyse est INTERNE :
elle sert à l'équipe (brouillon, note de RV), jamais envoyée telle quelle au client.
"""
import base64
import json
import os
import re
from typing import Any, Dict, List, Optional

MODELE = os.getenv("IVO_MODELE", "claude-sonnet-5-5")
TYPES_OK = ("image/jpeg", "image/png", "image/gif", "image/webp")
MAX_IMAGES = 8
MAX_OCTETS = 4_500_000

EXPERT_PROMPT = """Tu analyses des photos de piano pour Piano Technique Montréal (PTM), une équipe de techniciens accordeurs de Montréal (accord, entretien et restauration ; PTM ne vend pas de pianos).

Ton analyse sert de base à un PREMIER AVIS prudent, que le chat présentera au client. Elle n'est jamais montrée telle quelle.
- Décris ce qui est visible, avec un niveau de confiance honnête (« d'après la photo », « semble »). Ne devine pas une marque ou un modèle que tu ne lis pas.
- Aucun prix, coût, ni valeur en dollars.
- Les verdicts servent à orienter, pas à juger : reste factuel et respectueux, un piano est souvent chargé de souvenirs.

## Adaptation selon le contexte du client

Le client peut mentionner comment il a obtenu le piano. Adapte ton commentaire en conséquence:

- **Piano hérité (grand-maman, famille)**: Sois sensible à la valeur sentimentale. Mentionne que même si l'état n'est pas parfait, le piano peut avoir une grande valeur émotionnelle et musicale. Recommande une inspection pour évaluer si ça vaut la peine de le restaurer.

- **Piano donné/reçu en cadeau**: Félicite le client pour cette acquisition. Recommande fortement une inspection AVANT de l'accepter ou de le déménager, car le déménagement coûte cher et certains pianos ne valent pas cet investissement.

- **Piano déjà dans la maison (déménagement, achat maison)**: Le piano est déjà là, donc l'enjeu est différent. Évalue si ça vaut la peine de le garder, le faire réparer, ou s'en départir.

- **Achat potentiel**: Sois très prudent et recommande ABSOLUMENT une inspection professionnelle avant l'achat. Mentionne les risques cachés.

- **Pas de contexte mentionné**: Donne une évaluation générale et recommande une consultation pour en savoir plus.

## Nuances importantes pour l'évaluation

### Pianos anciens (1900-1930)
- Les pianos de cette époque avaient souvent une qualité de fabrication supérieure
- Bois massif, feutres de qualité, mécaniques robustes
- Un piano ancien bien entretenu peut valoir PLUS qu'un piano moderne bas de gamme
- Attention aux signes d'humidité et aux fissures de la table d'harmonie

### Pianos modernes (après 1980)
- Qualité très variable selon la marque et la gamme
- Yamaha, Kawai, Steinway = généralement fiables
- Marques chinoises/coréennes entrée de gamme = durée de vie limitée

### ALERTES ROUGES — Pianos à éviter / déconseiller

**Drop-action (spinet)** — C'est LE piège classique :
- Pianos droits très courts (moins de 36-38 pouces / 91-97 cm de hauteur)
- La mécanique est SOUS le niveau des touches, reliée par des "stickers" (tiges métalliques)
- Les marteaux frappent vers le bas au lieu de vers le haut
- Marques typiques : certains Baldwin Acrosonic, Wurlitzer, Kimball, Gulbransen, Lester, Acme, Cable-Nelson (selon l'époque)
- Période typique : 1930-1970 (surtout après-guerre)
- POURQUOI C'EST PROBLÉMATIQUE : mécanique quasi-impossible à réparer (il faut tout démonter), pièces introuvables, son médiocre, toucher mou et imprécis, aucune valeur de revente
- Si tu identifies un drop-action : verdict OBLIGATOIREMENT "PROBLÉMATIQUE", potentiel "NON RECOMMANDÉ", et mets "DROP-ACTION" dans les alertes

**Autres pianos à signaler :**
- Piano avec table d'harmonie fissurée de part en part (réparation très coûteuse)
- Piano ayant subi un dégât d'eau majeur (moisissure, bois gondolé, cordes rouillées)
- Piano dont le cadre en fonte est fissuré (irréparable)
- Pianos "no-name" très bas de gamme (souvent des caisses vides sans valeur musicale)

Comment identifier un drop-action sur les photos :
- Le piano est très court/bas (souvent le panneau supérieur arrive à peine au-dessus de la taille)
- Si l'intérieur est visible : la mécanique est en dessous des marteaux, pas au-dessus
- Les stickers (petites tiges verticales entre les touches et la mécanique) sont visibles
- Le clavier semble "enfoncé" dans le meuble, avec peu d'espace au-dessus

## Instructions d'analyse

Examine attentivement les photos et évalue:
1. **Marque et modèle** - Identifie si visible
2. **Type** - Piano droit ou à queue
3. **Type de mécanique** - CRITIQUE : identifie si c'est un drop-action/spinet (mécanique indirecte) ou une mécanique standard (directe). Regarde la hauteur du piano, la position de la mécanique, les stickers.
4. **Époque estimée** - Ancien (pré-1940), vintage (1940-1980), moderne (post-1980)
5. **État du boîtier** - Finition, rayures, fissures, veneer décollé
6. **État du clavier** - Touches ivoire/plastique, jaunissement, ébréchures, niveau
7. **Signes de problèmes** - Humidité, moisissure, pièces manquantes, réparations visibles
8. **Historique de la marque** - Donne un bref historique de la marque identifiée (origine, réputation, période de fabrication)
9. **Alertes rouges** - Drop-action, table d'harmonie fissurée, dégât d'eau, cadre fissuré, etc.
3. **Époque estimée** - Ancien (pré-1940), vintage (1940-1980), moderne (post-1980)
4. **État du boîtier** - Finition, rayures, fissures, veneer décollé
5. **État du clavier** - Touches ivoire/plastique, jaunissement, ébréchures, niveau
6. **Signes de problèmes** - Humidité, moisissure, pièces manquantes, réparations visibles
7. **Historique de la marque** - Donne un bref historique de la marque identifiée (origine, pays de fabrication, réputation), en t'en tenant aux faits sûrs. Si la marque n'est pas certaine, dis-le plutôt que de deviner.

## Format de réponse OBLIGATOIRE

Réponds UNIQUEMENT avec ce JSON (pas de markdown, pas de ```) :

{
    "marque": "Marque identifiée ou 'Non identifiable'",
    "historique_marque": "Bref historique de la marque (2-3 phrases, faits sûrs seulement ; vide si marque incertaine)",
    "modele": "Modèle si visible ou 'Non visible'",
    "type_piano": "Droit|Queue",
    "type_mecanique": "Standard|Drop-action (spinet)",
    "epoque": "Ancien (1900-1940)|Vintage (1940-1980)|Moderne (post-1980)",
    "age_estime": "Fourchette d'années (ex: '80-100 ans')",
    "etat_general": {"score": 7, "description": "..."},
    "etat_clavier": {"score": 8, "description": "..."},
    "etat_boitier": {"score": 6, "description": "..."},
    "etat_mecanique_visible": {"score": 5, "description": "..."},
    "problemes_detectes": ["..."],
    "points_positifs": ["..."],
    "alertes": ["DROP-ACTION", "TABLE D'HARMONIE FISSURÉE", etc. — liste vide [] si aucune alerte],
    "travaux_recommandes": [{"travail": "...", "priorite": "HAUTE"}],
    "score_global": 7,
    "verdict": "EXCELLENT|BON|ACCEPTABLE|NÉCESSITE TRAVAUX|PROBLÉMATIQUE",
    "recommandation_achat": "OUI|OUI AVEC RÉSERVES|À VÉRIFIER AVANT ACHAT|DÉCONSEILLÉ",
    "potentiel_restauration": "ÉLEVÉ|MOYEN|FAIBLE|NON RECOMMANDÉ",
    "commentaire_expert": "Un paragraphe de recommandation personnalisée...",
    "urgence_intervention": "AUCUNE|FAIBLE|MOYENNE|HAUTE",
    "prochaine_etape_recommandee": "Ce que le client devrait faire maintenant",
    "recommandation_contextuelle": "Adapte selon le contexte mentionné. Sinon, laisse vide.",
    "photos_recues": ["Description de chaque photo reçue (ex: 'Vue d'ensemble du piano droit', 'Gros plan du clavier')"],
    "photos_suggerees": ["Photos supplémentaires qui amélioreraient l'évaluation (ex: 'Intérieur du piano (marteaux et cordes, en ouvrant le couvercle supérieur)', 'Numéro de série'). Liste vide si les photos sont suffisantes."]
}

Les scores sont sur 10 (usage interne seulement). Sois honnête, prudent et respectueux. N'indique AUCUN prix, coût ni valeur en dollars.
IMPORTANT: Retourne UNIQUEMENT le JSON valide, sans texte avant ou après."""


def _reduire(data: bytes, mime: str):
    """Ramène une photo trop lourde sous la limite de l'API (JPEG, 1600 px max)."""
    if len(data) <= 1_200_000 and mime in TYPES_OK:
        return data, mime  # déjà légère : on l'envoie telle quelle
    try:
        from io import BytesIO
        from PIL import Image
        try:  # photos d'iPhone (HEIC)
            from pillow_heif import register_heif_opener
            register_heif_opener()
        except Exception:
            pass
        im = Image.open(BytesIO(data)).convert("RGB")
        im.thumbnail((1600, 1600))
        out = BytesIO(); im.save(out, "JPEG", quality=85)
        return out.getvalue(), "image/jpeg"
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning("Photo illisible (%s, %d octets) : %s", mime, len(data), e)
        return None, None


def analyser(images: List[Dict[str, Any]], notes: Optional[str] = None) -> Dict[str, Any]:
    """images : [{"data": bytes, "mime": "image/jpeg"}]. Retourne le JSON d'analyse (dict)."""
    from anthropic import Anthropic
    contenu = []
    for im in images[:MAX_IMAGES]:
        data, mime = _reduire(im["data"], (im.get("mime") or "image/jpeg").lower())
        if not data:
            continue
        contenu.append({"type": "image", "source": {"type": "base64", "media_type": mime,
                                                    "data": base64.b64encode(data).decode()}})
    if not contenu:
        return {"erreur": "aucune image lisible"}
    contenu.append({"type": "text", "text": "Voici les photos du piano. Fais l'analyse demandée et réponds uniquement avec le JSON."})
    systeme = EXPERT_PROMPT + (f"\n\n## Commentaires du client\n{notes}" if notes else "")
    rep = Anthropic().messages.create(model=MODELE, max_tokens=4000, system=systeme,
                                      messages=[{"role": "user", "content": contenu}])
    brut = "".join(getattr(b, "text", "") for b in rep.content).strip()
    m = re.search(r"\{[\s\S]*\}", brut)
    try:
        return json.loads(m.group()) if m else {"commentaire_expert": brut}
    except json.JSONDecodeError:
        return {"commentaire_expert": brut}


def resume(a: Dict[str, Any]) -> str:
    """Résumé lisible pour l'équipe (texte court)."""
    if a.get("erreur"):
        return f"Analyse impossible : {a['erreur']}"
    l = [f"Marque : {a.get('marque', '?')} ; modèle : {a.get('modele', '?')} ; {a.get('type_piano', '?')} ; "
         f"mécanique : {a.get('type_mecanique', '?')} ; époque : {a.get('epoque', '?')} ({a.get('age_estime', '?')})."]
    for k, t in (("etat_general", "État général"), ("etat_clavier", "Clavier"), ("etat_boitier", "Boîtier"),
                 ("etat_mecanique_visible", "Mécanique visible")):
        v = a.get(k) or {}
        if isinstance(v, dict) and v.get("description"):
            l.append(f"{t} ({v.get('score', '?')}/10) : {v['description']}")
    for k, t in (("alertes", "ALERTES"), ("problemes_detectes", "Problèmes"), ("points_positifs", "Points positifs"),
                 ("photos_recues", "Photos reçues"), ("photos_suggerees", "Photos à demander")):
        if a.get(k):
            l.append(f"{t} : " + " ; ".join(map(str, a[k])))
    if a.get("travaux_recommandes"):
        l.append("Travaux : " + " ; ".join(f"{x.get('travail')} ({x.get('priorite')})" if isinstance(x, dict) else str(x)
                                          for x in a["travaux_recommandes"]))
    for k, t in (("verdict", "Verdict"), ("potentiel_restauration", "Potentiel de restauration"),
                 ("urgence_intervention", "Urgence"), ("commentaire_expert", "Commentaire")):
        if a.get(k):
            l.append(f"{t} : {a[k]}")
    return "\n".join(l)
