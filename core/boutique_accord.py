"""Boutique « avec l'accord » : ce que le client peut ajouter à son rendez-vous.

Le technicien apporte l'article à la visite ; il est payé sur la facture Gazelle du rendez-vous.
Choix d'Allan (panneau de décisions, 4 nov. 2026). Les prix ne sont PAS écrits ici :
ils sont lus en direct dans la Master Service List de Gazelle (Gazelle fait foi).

- quantite : nombre d'unités Gazelle par article vendu (coupelles : prix Gazelle à l'unité,
  vendues par ensemble de 4 pour un piano droit ou de 3 pour un piano à queue).
- mode « soumission » : affiché sans prix, le client demande une soumission lors de son accord.
"""

ARTICLES = [
    {"cle": "ensemble-cory", "msl": "mit_eRqZsLAzRs3ypEGC", "nom_fr": "Ensemble d'entretien Cory",
     "nom_en": "Cory care kit", "detail_fr": "Poli 4 oz, Key-Brite 4 oz et 2 chiffons, pour fini lustré",
     "detail_en": "4 oz polish, 4 oz Key-Brite and 2 cloths, for high-gloss finishes", "quantite": 1, "mode": "achat"},
    {"cle": "key-brite-4", "msl": "mit_MnWfmDHQLItiuK8v", "nom_fr": "Key-Brite 4 oz", "nom_en": "Key-Brite 4 oz",
     "detail_fr": "Nettoyant pour clavier", "detail_en": "Keyboard cleaner", "quantite": 1, "mode": "achat"},
    {"cle": "poli-cory-4", "msl": "mit_LzjQTqXjCtbmERoy", "nom_fr": "Poli à piano Cory 4 oz", "nom_en": "Cory piano polish 4 oz",
     "detail_fr": "Pour fini lustré", "detail_en": "For high-gloss finishes", "quantite": 1, "mode": "achat"},
    {"cle": "traitement-eau-227", "msl": "mit_CX6CvWXbjs08vg70", "nom_fr": "Traitement de l'eau Piano Life Saver 227 ml",
     "nom_en": "Piano Life Saver water treatment 227 ml", "detail_fr": "Pour les pianos déjà équipés",
     "detail_en": "For pianos already equipped", "quantite": 1, "mode": "achat"},
    {"cle": "coupelles-noir-droit", "msl": "mit_UDPCleMKmUM7Hjf7", "nom_fr": "Coupelles de bois noir lustré, ensemble de 4 (piano droit)",
     "nom_en": "Black high-gloss wood caster cups, set of 4 (upright)", "detail_fr": "Vrai bois, feutre vert dessous · installation comprise",
     "detail_en": "Real wood, green felt underneath · installation included", "quantite": 4, "mode": "achat"},
    {"cle": "coupelles-noir-queue", "msl": "mit_UDPCleMKmUM7Hjf7", "nom_fr": "Coupelles de bois noir lustré, ensemble de 3 (piano à queue)",
     "nom_en": "Black high-gloss wood caster cups, set of 3 (grand)", "detail_fr": "Vrai bois, feutre vert dessous · installation comprise",
     "detail_en": "Real wood, green felt underneath · installation included", "quantite": 3, "mode": "achat"},
    {"cle": "coupelles-bois-droit", "msl": "mit_42NwKWMNgvFkJqND", "nom_fr": "Coupelles de bois, ensemble de 4 (piano droit)",
     "nom_en": "Wood caster cups, set of 4 (upright)", "detail_fr": "Vrai bois, feutre vert dessous · installation comprise",
     "detail_en": "Real wood, green felt underneath · installation included", "quantite": 4, "mode": "achat"},
    {"cle": "coupelles-bois-queue", "msl": "mit_42NwKWMNgvFkJqND", "nom_fr": "Coupelles de bois, ensemble de 3 (piano à queue)",
     "nom_en": "Wood caster cups, set of 3 (grand)", "detail_fr": "Vrai bois, feutre vert dessous · installation comprise",
     "detail_en": "Real wood, green felt underneath · installation included", "quantite": 3, "mode": "achat"},
    {"cle": "piano-life-saver", "msl": None, "nom_fr": "Système Piano Life Saver", "nom_en": "Piano Life Saver system",
     "detail_fr": "Stabilise l'humidité dans le piano, pour un accord qui tient mieux",
     "detail_en": "Keeps humidity stable inside the piano, so the tuning holds better", "quantite": 1, "mode": "soumission"},
    {"cle": "systeme-silent", "msl": None, "nom_fr": "Système Silent", "nom_en": "Silent system",
     "detail_fr": "Jouer au casque sans déranger, sur votre propre piano",
     "detail_en": "Play with headphones on your own piano without disturbing anyone", "quantite": 1, "mode": "soumission"},
]


def catalogue(prix_msl: dict) -> list:
    """Articles de la boutique avec le prix total calculé depuis la Master Service List.
    Un article d'achat dont le prix Gazelle est introuvable est retiré (jamais de prix deviné)."""
    out = []
    for a in ARTICLES:
        item = {k: a[k] for k in ("cle", "nom_fr", "nom_en", "detail_fr", "detail_en", "mode", "quantite")}
        if a["mode"] == "achat":
            unite = prix_msl.get(a["msl"])
            if not unite:
                continue
            item["prix"] = round(unite * a["quantite"], 2)
        out.append(item)
    return out
