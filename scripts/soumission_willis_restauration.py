#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Soumission « Restauration complète — piano droit Willis & Co. (Montréal) ».

Deux tiers avec inclusion stricte :
  Tier 1 « Restauration essentielle »  — remise en état mécanique et sonore
  Tier 2 « Restauration complète »     — Tier 1 + touches, meuble, PLS, rodage

Usage
-----
    # Aperçu chiffré, rien n'est envoyé
    python3 scripts/soumission_willis_restauration.py --dry-run

    # Résolution du client et du piano par nom, puis création
    python3 scripts/soumission_willis_restauration.py --client-search "Éric Le Reste"
    python3 scripts/soumission_willis_restauration.py --client-search "Éric Le Reste" --yes

    # Création réelle dans Gazelle (2 étapes : create minimal puis update)
    python3 scripts/soumission_willis_restauration.py \
        --client-id cli_XXXX --piano-id ins_XXXX \
        --client-name "Éric Le Reste" --piano-make Willis

Règles Gazelle respectées (voir workspace/skills/gazelle/) :
  1. JAMAIS `estimateTiers` dans `createEstimate` → create minimal puis update.
  2. `type` obligatoire sur chaque item (défaut LABOR_FIXED_RATE).
  3. `photos: []`, `duration: 0` explicites, jamais `externalUrl: null`.
  4. Taxes : blocs TPS+TVQ explicites AVEC le champ `name` ("tps"/"tvq"),
     sinon les cases restent décochées dans l'UI (#11983).
  5. Montants en cents, quantités en centièmes.
  6. `mutationErrors` vérifiés même si HTTP 200.
  7. Aucun item à 0 $ — les inclusions vont dans la `description`.
  8. Tier 2 ⊇ Tier 1, vérifié avant l'envoi.
  9. Avertissements dans les notes de soumission, pas en items.
 10. Garde d'identité : le client et le piano sont revalidés avant l'update.
"""

from __future__ import annotations

import argparse
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Taxes Québec — mêmes constantes que api/assistant_duplication.py.
TPS_TAX_ID, TPS_NAME, TPS_RATE = "tax_JeCfY4wfbXtN6J28", "tps", 5000    # 5,000 %
TVQ_TAX_ID, TVQ_NAME, TVQ_RATE = "tax_xe9FEApq94zI7kXD", "tvq", 9975    # 9,975 %

VALIDITE_JOURS = 45

# MasterServiceItem connus (source de vérité du prix côté Gazelle).
MSL_MARTEAUX_DROIT = "mit_pDYrT2B8oxWAJ7ou"   # remplacement marteaux droit
MSL_CORDES_BASSES = "mit_2HBYLndAxf1C993j"    # cordes des basses (matériel + pose)


def item(name: str, amount: float, description: str,
         master_service_item_id: str | None = None,
         taxable: bool = True) -> Dict[str, Any]:
    """Item de soumission. `amount` en dollars, converti en cents."""
    return {
        "name": name,
        "amount_cents": int(round(amount * 100)),
        "description": description.strip(),
        "master_service_item_id": master_service_item_id,
        "is_taxable": taxable,
    }


# --------------------------------------------------------------------------
# Contenu de la soumission
# --------------------------------------------------------------------------

GROUPES_BASE: List[Dict[str, Any]] = [
    {
        "name": "Prise en charge et diagnostic",
        "items": [
            item(
                "Transport aller-retour à l'atelier",
                795.00,
                "Enlèvement et retour à domicile (grand Montréal) :\n"
                "• emballage et protection du meuble\n"
                "• manutention par deux techniciens\n"
                "• assurance transport pendant tout le séjour en atelier\n"
                "Escaliers, monte-charge ou distance hors zone : supplément confirmé d'avance.",
            ),
            item(
                "Démontage complet et diagnostic documenté",
                650.00,
                "Une fois le piano à l'atelier :\n"
                "• démontage de la mécanique, du clavier et des panneaux\n"
                "• dépoussiérage complet de la caisse et du cadre\n"
                "• mesure du couple des chevilles et relevé de la tenue d'accord\n"
                "• inspection de la table d'harmonie, des chevalets et du sommier\n"
                "• rapport photo avant travaux, remis avant la suite des opérations",
            ),
        ],
    },
    {
        "name": "Cordes, cadre et structure",
        "items": [
            item(
                "Cordage complet neuf et chevilles surdimensionnées",
                3850.00,
                "Remise à neuf de tout le plan de cordes :\n"
                "• dépose des cordes d'origine et des chevilles usées\n"
                "• cordes filées des basses fabriquées sur mesure pour ce piano\n"
                "• fil d'acier neuf (médium et aigus), calibres relevés corde par corde\n"
                "• chevilles neuves surdimensionnées, couple ajusté au sommier\n"
                "• nettoyage du cadre en fonte, retouches et protection du décalque\n"
                "• pressions et alignements repris aux chevalets et au sillet",
                master_service_item_id=MSL_CORDES_BASSES,
            ),
            item(
                "Réparation de la table d'harmonie et des chevalets",
                1450.00,
                "Travaux structuraux avec le cadre décordé :\n"
                "• collage et flipots des fentes de la table\n"
                "• recollage des barres de table décollées\n"
                "• révision des chevalets : pointes redressées ou remplacées, fissures recollées\n"
                "• vernis de la table nettoyé et raccordé",
            ),
        ],
    },
    {
        "name": "Mécanique",
        "items": [
            item(
                "Remplacement des marteaux",
                1250.00,
                "Jeu de marteaux neufs choisi pour l'échelle de ce Willis :\n"
                "• dépose des marteaux d'origine\n"
                "• têtes neuves montées et alignées sur les manches\n"
                "• perçage et angle de frappe repris corde par corde\n"
                "• pré-harmonisation en atelier\n"
                "• accord de contrôle après pose",
                master_service_item_id=MSL_MARTEAUX_DROIT,
            ),
            item(
                "Remplacement des étouffoirs",
                695.00,
                "Étouffement remis à neuf :\n"
                "• feutres d'étouffoirs neufs (cuillères, coins et basses)\n"
                "• portée et synchronisme réglés note par note\n"
                "• cuillères recintrées pour une levée uniforme",
            ),
            item(
                "Recentrage complet et refeutrage de la mécanique",
                1380.00,
                "Remise en jeu de toutes les pièces mobiles :\n"
                "• recentrage des axes de marteaux, de bascules et de chevalets d'échappement\n"
                "• bagues et feutres d'axes remplacés là où le jeu est hors tolérance\n"
                "• casimirs, feutres de butée et de repos remplacés\n"
                "• nettoyage et lubrification des points de friction",
            ),
            item(
                "Régulation complète mécanique et clavier",
                980.00,
                "Réglage fin de l'ensemble, en atelier puis revalidé à domicile :\n"
                "• enfoncement, échappement, attrape et levée d'étouffoir\n"
                "• course des touches et profondeur de toucher uniformisées\n"
                "• pilotes et bascules ajustés note par note\n"
                "• contrôle de la répétition sur les 88 notes",
            ),
        ],
    },
    {
        "name": "Clavier et pédalier",
        "items": [
            item(
                "Clavier : mortaises, rondelles et nivelage",
                780.00,
                "Assise du clavier reprise au complet :\n"
                "• mortaises de balancier et d'avant refeutrées\n"
                "• rondelles de nivelage et de course renouvelées\n"
                "• pointes de balancier polies et redressées\n"
                "• nivelage fin des 88 touches, blanches et noires",
            ),
            item(
                "Révision de la lyre et des pédales",
                425.00,
                "Pédalier remis en état :\n"
                "• tringlerie démontée, nettoyée et refeutrée\n"
                "• articulations reprises, bruits parasites éliminés\n"
                "• pédale douce et sourdine réglées à leur course d'origine\n"
                "• fixation de la lyre consolidée",
            ),
        ],
    },
    {
        "name": "Finition sonore et mise en service",
        "items": [
            item(
                "Harmonisation des marteaux neufs",
                590.00,
                "Le timbre est travaillé en trois passes :\n"
                "• piquage initial en atelier après la mise en tension\n"
                "• égalisation du registre grave, médium et aigu\n"
                "• passe finale à domicile, une fois le piano stabilisé dans sa pièce",
            ),
            item(
                "Mise au diapason progressive — trois accords",
                540.00,
                "Un jeu de cordes neuf s'étire : la montée au diapason se fait par étapes.\n"
                "• deux accords de montée en atelier, à quelques jours d'intervalle\n"
                "• accord de mise en service à domicile après la livraison\n"
                "• contrôle de la tenue et de la stabilité du sommier à chaque passe",
            ),
            item(
                "Nettoyage, retouches et polissage du meuble",
                690.00,
                "Finition d'origine conservée :\n"
                "• nettoyage en profondeur de l'ébénisterie et des placages\n"
                "• retouches localisées des éraflures et des manques de vernis\n"
                "• polissage et cirage final\n"
                "• quincaillerie (charnières, serrures, chandeliers) nettoyée et refixée",
            ),
        ],
    },
]

# Ajouts du Tier 2 — greffés dans les groupes existants pour garder l'inclusion.
AJOUTS_COMPLET: Dict[str, List[Dict[str, Any]]] = {
    "Clavier et pédalier": [
        item(
            "Replacage des touches et fronts neufs",
            1150.00,
            "Surface de jeu refaite à neuf :\n"
            "• dépose des placages d'origine fendus ou jaunis\n"
            "• placages d'ivoirine neufs, ajustés et polis touche par touche\n"
            "• fronts de touches neufs\n"
            "• touches noires nettoyées, poncées et repolies",
        ),
    ],
    "Finition sonore et mise en service": [
        item(
            "Refinition complète du meuble",
            3900.00,
            "Ébénisterie reprise à nu (remplace le simple polissage, qui reste inclus) :\n"
            "• décapage complet des panneaux et du meuble\n"
            "• réparation des placages soulevés ou manquants\n"
            "• teinture raccordée à la couleur d'origine\n"
            "• laque satinée en plusieurs couches, égrenée entre chaque\n"
            "• quincaillerie déposée, nettoyée et remontée",
        ),
        item(
            "Système de contrôle d'humidité Dampp-Chaser — piano droit",
            975.00,
            "Protection de tout le travail de restauration :\n"
            "• installation complète du système sous le clavier (piano droit)\n"
            "• barre chauffante, humidificateur et hygrostat\n"
            "• branchement électrique et mise en service\n"
            "• formation sur le remplissage et le traitement de l'eau\n"
            "L'accord de suivi trois semaines après l'installation est facturé séparément.",
        ),
        item(
            "Accord de rodage à domicile (3 à 4 mois)",
            199.00,
            "Un accord supplémentaire une fois le piano acclimaté à votre pièce :\n"
            "• reprise de la tenue après stabilisation des cordes neuves\n"
            "• contrôle de la régulation et retouches de réglage\n"
            "• vérification du système d'humidité s'il est installé",
        ),
    ],
}

NOTES_INTRO = """Bonjour,

Merci pour l'accueil lors de notre rendez-vous. Voici la soumission détaillée pour la \
restauration de votre piano droit Willis & Co. — un instrument de fabrication montréalaise \
qui mérite qu'on le remette en état plutôt que de le remplacer.

La soumission est présentée en deux options. L'option « Restauration essentielle » redonne \
à l'instrument tout son potentiel sonore et mécanique : cordage neuf, table d'harmonie \
consolidée, mécanique entièrement reprise et régulée, harmonisation et mise au diapason \
progressive. L'option « Restauration complète » reprend intégralement la première et y \
ajoute la réfection du clavier, la refinition du meuble, le système de contrôle d'humidité \
et l'accord de rodage — c'est l'option qui livre un piano fini, protégé et prêt pour les \
trente prochaines années.

Le travail se fait à notre atelier. Comptez de 8 à 12 semaines à partir de la prise en \
charge. Un dépôt de 40 % confirme la réservation de la plage d'atelier; le solde est payable \
à la livraison. Les prix affichés excluent les taxes, qui sont détaillées au bas de la \
soumission."""

AVERTISSEMENTS = [
    "Les prix sont établis à partir de l'inspection faite chez vous. Certains constats ne "
    "sont confirmables qu'une fois le piano décordé et la mécanique déposée : tout écart "
    "vous est soumis pour approbation écrite avant d'être exécuté.",

    "Sommier : sur un instrument de cet âge, les chevilles surdimensionnées suffisent dans "
    "la grande majorité des cas. Si le couple mesuré reste insuffisant après le recordage, "
    "le remplacement du sommier devient nécessaire — supplément estimé entre 3 200 $ et "
    "4 200 $, jamais engagé sans votre accord.",

    "Table d'harmonie : le collage des fentes stabilise la table, mais la couronne d'origine "
    "ne se reconstitue pas. Le rendu sonore final dépend de la couronne résiduelle, qui sera "
    "mesurée dès le décordage et documentée dans le rapport photo.",

    "Cordes neuves : elles s'étirent pendant environ un an. Les trois accords de mise au "
    "diapason sont inclus; prévoyez deux accords d'entretien la première année pour "
    "stabiliser complètement l'instrument.",

    "Pièces d'origine : certaines pièces de mécanique Willis ne se fabriquent plus. "
    "L'adaptation sur mesure est incluse dans les prix, mais elle peut allonger le délai "
    "d'atelier de deux à trois semaines.",

    "Valeur : la restauration d'un Willis ancien dépasse sa valeur de revente. C'est un "
    "investissement d'usage et d'attachement à l'instrument, pas un placement — nous "
    "préférons le dire clairement avant que vous décidiez.",

    f"Cette soumission est valide {VALIDITE_JOURS} jours. Au-delà, les prix des cordes, "
    "feutres et marteaux sont revalidés auprès des fournisseurs.",
]

TIER_NOTES_BASE = (
    "Option 1 — Restauration essentielle. Le piano retrouve son plein potentiel sonore et "
    "mécanique. Le meuble est nettoyé, retouché et poli, sans décapage; les placages de "
    "touches d'origine sont conservés."
)
TIER_NOTES_COMPLET = (
    "Option 2 — Restauration complète (recommandée). Tout ce que comprend l'option 1, plus "
    "la réfection du clavier, la refinition complète du meuble, le système de contrôle "
    "d'humidité Dampp-Chaser et l'accord de rodage à domicile. Le piano est livré fini et "
    "protégé contre les écarts d'humidité qui, autrement, défont une partie du travail dès "
    "le premier hiver."
)


# --------------------------------------------------------------------------
# Portée « ciblée » — Éric : cordes de basse, contre-attrapes, marteaux,
# mortaises de clavier, réparation des ivoires existants. Un seul tier.
# --------------------------------------------------------------------------

GROUPES_CIBLEE: List[Dict[str, Any]] = [
    {
        "name": "Cordes",
        "items": [
            item(
                "Cordes des basses — jeu complet neuf",
                2000.00,
                "Remplacement de toutes les cordes filées du registre grave :\n"
                "• relevé des mesures corde par corde (âme, filage, longueur parlante)\n"
                "• cordes filées fabriquées sur mesure pour ce piano\n"
                "• dépose des cordes d'origine et nettoyage du cadre et du chevalet des basses\n"
                "• pose, mise en tension progressive et égalisation des pressions\n"
                "• accord de mise en tension inclus à la fin de la pose",
                master_service_item_id=MSL_CORDES_BASSES,
            ),
        ],
    },
    {
        "name": "Mécanique",
        "items": [
            item(
                "Remplacement des marteaux",
                1250.00,
                "Jeu de marteaux neufs choisi pour l'échelle de ce Willis :\n"
                "• dépose des marteaux d'origine\n"
                "• têtes neuves montées et alignées sur les manches\n"
                "• perçage et angle de frappe repris corde par corde\n"
                "• échappement et attrape réajustés après la pose\n"
                "• harmonisation des marteaux neufs et accord de contrôle",
                master_service_item_id=MSL_MARTEAUX_DROIT,
            ),
            item(
                "Garnitures de contre-attrape",
                585.00,
                "Reprise de la retenue du marteau après la frappe :\n"
                "• garnitures de contre-attrape usées remplacées sur les 88 notes\n"
                "• surfaces des attrapes nettoyées et redressées\n"
                "• hauteur et angle de prise réglés note par note\n"
                "• contrôle de la répétition sur toute l'étendue",
            ),
        ],
    },
    {
        "name": "Clavier",
        "items": [
            item(
                "Garnitures de mortaises de clavier",
                850.00,
                "Guidage des touches remis à neuf :\n"
                "• garnitures de mortaises de balancier et d'avant remplacées, 88 touches\n"
                "• pointes de guidage polies et redressées\n"
                "• jeu latéral calibré touche par touche\n"
                "• nivelage et course des touches revalidés après la pose",
            ),
            item(
                "Réparation des placages d'ivoire existants",
                495.00,
                "Les ivoires d'origine sont conservés et remis en état :\n"
                "• recollage des placages soulevés ou décollés\n"
                "• remplacement ponctuel des éclats à partir d'ivoires de récupération\n"
                "• joints rebouchés, arêtes reprises\n"
                "• ponçage fin et polissage de l'ensemble des touches\n"
                "• fronts de touches nettoyés et refixés au besoin",
            ),
        ],
    },
]

TIER_NOTES_CIBLEE = (
    "Les cinq postes convenus lors du rendez-vous : cordes des basses, marteaux, garnitures "
    "de contre-attrape, garnitures de mortaises de clavier et réparation des ivoires "
    "existants. Chaque poste comprend les réglages et l'accord nécessaires à sa propre mise "
    "au point."
)

NOTES_INTRO_CIBLEE = """Bonjour Éric,

Merci pour l'accueil. Voici la soumission pour les travaux ciblés sur votre piano droit \
Willis & Co., tels qu'on les a arrêtés ensemble : les cordes des basses, les marteaux, les \
garnitures de contre-attrape, les garnitures de mortaises du clavier et la réparation des \
placages d'ivoire d'origine.

C'est une remise en état des points qui limitent réellement l'instrument aujourd'hui — pas \
une restauration complète. Vos ivoires sont conservés et réparés plutôt que remplacés, et \
le meuble n'est pas touché.

Les travaux se font en deux visites à domicile, à une ou deux semaines d'intervalle, le \
temps que les cordes neuves s'étirent avant la mise au point finale. Les prix affichés \
excluent les taxes, détaillées au bas de la soumission."""

AVERTISSEMENTS_CIBLEE = [
    "Ivoires : les placages d'origine sont recollés, rebouchés et repolis. Les éclats "
    "importants se remplacent avec des ivoires de récupération dont la teinte ne sera jamais "
    "parfaitement identique — un ivoire jauni ne redevient pas neuf, aucun traitement ne le "
    "fait sans détruire la surface.",

    "Cordes des basses neuves : elles s'étirent pendant plusieurs mois. L'accord de pose est "
    "compris; prévoyez deux accords d'entretien la première année pour stabiliser le "
    "registre grave.",

    "Équilibre sonore : des basses neuves sonnent nettement plus riches que des médiums "
    "d'origine. L'harmonisation des marteaux neufs atténue l'écart, mais un léger "
    "déséquilibre subsiste tant que le reste du plan de cordes n'est pas refait.",

    "Chevilles : les chevilles du registre grave sont réutilisées. Si le couple mesuré au "
    "recordage est insuffisant, il faut passer à des chevilles surdimensionnées — supplément "
    "d'environ 240 $ pour la section des basses, jamais engagé sans votre accord.",

    "Régulation : les réglages compris ici sont ceux qu'exigent les pièces remplacées. Une "
    "régulation complète de la mécanique et du clavier n'est pas incluse; si le piano en a "
    "besoin, elle se chiffre à 980 $ et se décide après la pose des marteaux.",

    "Travaux à domicile. Si vous préférez que la mécanique et le clavier partent à l'atelier "
    "pour ces travaux, le transport aller-retour est chiffré séparément.",

    f"Cette soumission est valide {VALIDITE_JOURS} jours. Au-delà, les prix des cordes, "
    "feutres et marteaux sont revalidés auprès des fournisseurs.",
]


# --------------------------------------------------------------------------
# Construction du payload Gazelle
# --------------------------------------------------------------------------

def build_taxes(amount_cents: int, is_taxable: bool) -> List[Dict[str, Any]]:
    """Bloc TPS+TVQ avec le champ `name` (requis pour cocher les cases)."""
    if not is_taxable or not amount_cents:
        return []
    return [
        {"taxId": TPS_TAX_ID, "name": TPS_NAME, "rate": TPS_RATE,
         "total": round(amount_cents * TPS_RATE / 100000)},
        {"taxId": TVQ_TAX_ID, "name": TVQ_NAME, "rate": TVQ_RATE,
         "total": round(amount_cents * TVQ_RATE / 100000)},
    ]


def build_item_input(it: Dict[str, Any], sequence: int) -> Dict[str, Any]:
    amount = it["amount_cents"]
    taxable = it["is_taxable"]
    payload: Dict[str, Any] = {
        "name": it["name"],
        "description": it["description"],
        "amount": amount,
        "quantity": 100,          # quantités en centièmes → 1,00
        "duration": 0,
        "type": "LABOR_FIXED_RATE",
        "isTaxable": taxable,
        "isTuning": False,
        "sequenceNumber": sequence,
        "photos": [],
        "taxes": build_taxes(amount, taxable),
    }
    if it.get("master_service_item_id"):
        payload["masterServiceItemId"] = it["master_service_item_id"]
    return payload


def build_groups(groupes: List[Dict[str, Any]],
                 extras: Dict[str, List[Dict[str, Any]]] | None = None) -> List[Dict[str, Any]]:
    groups = []
    for gi, groupe in enumerate(groupes):
        items = list(groupe["items"])
        if extras:
            items += extras.get(groupe["name"], [])
        groups.append({
            "name": groupe["name"],
            "sequenceNumber": gi,
            "estimateTierItems": [build_item_input(it, i) for i, it in enumerate(items)],
        })
    return groups


def build_tier(sequence: int, is_primary: bool, notes: str,
               groupes: List[Dict[str, Any]],
               extras: Dict[str, List[Dict[str, Any]]] | None = None) -> Dict[str, Any]:
    return {
        "sequenceNumber": sequence,
        "isPrimary": is_primary,
        "notes": notes,
        "estimateTierGroups": build_groups(groupes, extras),
        "ungroupedEstimateTierItems": [],
    }


def build_notes(intro: str, avertissements: List[str]) -> str:
    lines = [intro, "", "À savoir avant de décider :", ""]
    lines += [f"• {w}" for w in avertissements]
    return "\n".join(lines)


def build_scope(scope: str) -> Dict[str, Any]:
    """Retourne les tiers et les notes de la portée demandée."""
    if scope == "ciblee":
        tier = build_tier(0, is_primary=True, notes=TIER_NOTES_CIBLEE,
                          groupes=GROUPES_CIBLEE)
        return {"tiers": [tier],
                "notes": build_notes(NOTES_INTRO_CIBLEE, AVERTISSEMENTS_CIBLEE)}
    base = build_tier(0, is_primary=False, notes=TIER_NOTES_BASE,
                      groupes=GROUPES_BASE)
    complet = build_tier(1, is_primary=True, notes=TIER_NOTES_COMPLET,
                         groupes=GROUPES_BASE, extras=AJOUTS_COMPLET)
    return {"tiers": [base, complet],
            "notes": build_notes(NOTES_INTRO, AVERTISSEMENTS)}


# --------------------------------------------------------------------------
# Lint et garde d'inclusion
# --------------------------------------------------------------------------

def lint(tiers: List[Dict[str, Any]]) -> List[str]:
    """Reproduit les règles bloquantes de lint_estimate() côté v6."""
    errors: List[str] = []
    for tier in tiers:
        for group in tier["estimateTierGroups"]:
            for it in group["estimateTierItems"]:
                label = f"[tier {tier['sequenceNumber']}] {group['name']} / {it['name']}"
                if not it["amount"]:
                    errors.append(f"ZERO_DOLLAR_ITEM — {label}")
                if not it.get("type"):
                    errors.append(f"MISSING_TYPE — {label}")
                if it.get("photos") is None:
                    errors.append(f"MISSING_PHOTOS — {label}")
                if it["isTaxable"] and not it["taxes"]:
                    errors.append(f"MISSING_TAXES — {label}")
                for tax in it["taxes"]:
                    if not tax.get("name"):
                        errors.append(f"TAX_WITHOUT_NAME — {label}")
                if not it.get("description"):
                    errors.append(f"MISSING_DESCRIPTION — {label}")
    return errors


def validate_inclusion(base: Dict[str, Any], extended: Dict[str, Any]) -> List[str]:
    """Tier étendu ⊇ tier de base, à la ligne et au montant près."""
    def keys(tier):
        return {(g["name"], i["name"], i["amount"])
                for g in tier["estimateTierGroups"] for i in g["estimateTierItems"]}
    return sorted(f"{g} / {n} ({a/100:.2f} $)" for g, n, a in keys(base) - keys(extended))


# --------------------------------------------------------------------------
# Totaux et aperçu
# --------------------------------------------------------------------------

def tier_totals(tier: Dict[str, Any]) -> Dict[str, float]:
    subtotal = tps = tvq = 0
    for group in tier["estimateTierGroups"]:
        for it in group["estimateTierItems"]:
            subtotal += it["amount"]
            for tax in it["taxes"]:
                if tax["name"] == TPS_NAME:
                    tps += tax["total"]
                else:
                    tvq += tax["total"]
    return {"sous_total": subtotal / 100, "tps": tps / 100, "tvq": tvq / 100,
            "total": (subtotal + tps + tvq) / 100}


def money(value: float) -> str:
    return f"{value:,.2f} $".replace(",", " ").replace(".", ",")


def tier_titre(tier: Dict[str, Any], nb_tiers: int) -> str:
    if nb_tiers == 1:
        return "TRAVAUX CONVENUS"
    return "OPTION 2 — RESTAURATION COMPLÈTE" if tier["sequenceNumber"] \
        else "OPTION 1 — RESTAURATION ESSENTIELLE"


def print_preview(tiers: List[Dict[str, Any]], notes: str,
                  estimated_on: str, expires_on: str, titre: str) -> None:
    print("=" * 78)
    print(f"SOUMISSION — {titre}")
    print(f"Émise le {estimated_on} · valide jusqu'au {expires_on}")
    print("=" * 78)
    for tier in tiers:
        flag = "  ★ recommandée" if tier["isPrimary"] and len(tiers) > 1 else ""
        print(f"\n{tier_titre(tier, len(tiers))}{flag}")
        print("-" * 78)
        for group in tier["estimateTierGroups"]:
            print(f"\n  {group['name']}")
            for it in group["estimateTierItems"]:
                print(f"    {it['name']:<58}{money(it['amount']/100):>16}")
        t = tier_totals(tier)
        print("\n" + " " * 4 + "-" * 70)
        print(f"    {'Sous-total':<58}{money(t['sous_total']):>16}")
        print(f"    {'TPS (5 %)':<58}{money(t['tps']):>16}")
        print(f"    {'TVQ (9,975 %)':<58}{money(t['tvq']):>16}")
        print(f"    {'TOTAL':<58}{money(t['total']):>16}")
    print("\n" + "=" * 78)
    print("NOTES DE SOUMISSION")
    print("=" * 78)
    print(notes)


# --------------------------------------------------------------------------
# Création dans Gazelle
# --------------------------------------------------------------------------

CREATE_ESTIMATE = """
mutation($input: PrivateCreateEstimateInput!) {
  createEstimate(input: $input) {
    estimate { id number }
    mutationErrors { fieldName messages }
  }
}
"""

FETCH_ESTIMATE = """
query($s: String!) {
  allEstimates(first: 5, filters: {search: $s}) {
    nodes {
      id number
      client { id companyName defaultContact { firstName lastName } }
      piano { id make model year }
    }
  }
}
"""


class EstimateIdentityMismatch(RuntimeError):
    """La soumission créée ne pointe pas le client/piano attendu — on n'update pas."""


def create_in_gazelle(client_id: str, piano_id: str, tiers: List[Dict[str, Any]],
                      notes: str, estimated_on: str, expires_on: str,
                      expected_client_name: str | None,
                      expected_piano_make: str | None) -> Dict[str, Any]:
    from core.gazelle_api_client import GazelleAPIClient

    gz = GazelleAPIClient()

    # Étape 1 — création minimale. JAMAIS de tiers ici.
    create_input = {
        "clientId": client_id,
        "pianoId": piano_id,
        "locale": "fr_CA",
        "estimatedOn": estimated_on,
        "expiresOn": expires_on,
        "notes": notes,
    }
    res = gz._execute_query(CREATE_ESTIMATE, {"input": create_input})
    payload = ((res or {}).get("data") or {}).get("createEstimate") or {}
    errors = payload.get("mutationErrors") or []
    if errors or not payload.get("estimate"):
        raise RuntimeError(f"createEstimate refusé : {errors}")
    est = payload["estimate"]

    # Garde d'identité — on relit la soumission créée avant de la peupler.
    check = gz._execute_query(FETCH_ESTIMATE, {"s": str(est["number"])})
    nodes = (((check or {}).get("data") or {}).get("allEstimates") or {}).get("nodes") or []
    node = next((n for n in nodes if str(n.get("number")) == str(est["number"])), None)
    if not node:
        raise EstimateIdentityMismatch(f"Soumission #{est['number']} illisible après création.")
    cli = node.get("client") or {}
    contact = cli.get("defaultContact") or {}
    real_name = (cli.get("companyName") or "").strip() or \
        " ".join(x for x in [contact.get("firstName"), contact.get("lastName")] if x).strip()
    real_make = ((node.get("piano") or {}).get("make") or "")
    if cli.get("id") != client_id or (node.get("piano") or {}).get("id") != piano_id:
        raise EstimateIdentityMismatch(
            f"#{est['number']} pointe {cli.get('id')} / "
            f"{(node.get('piano') or {}).get('id')} au lieu de {client_id} / {piano_id}.")
    if expected_client_name and expected_client_name.lower() not in real_name.lower():
        raise EstimateIdentityMismatch(
            f"#{est['number']} : client « {real_name} » ≠ « {expected_client_name} ».")
    if expected_piano_make and expected_piano_make.lower() not in real_make.lower():
        raise EstimateIdentityMismatch(
            f"#{est['number']} : piano « {real_make} » ≠ « {expected_piano_make} ».")

    # Étape 2 — peuplement des tiers (déclenche le calcul des taxes).
    gz.update_estimate(est["id"], {"estimateTiers": tiers, "notes": notes})
    return est


# --------------------------------------------------------------------------
# Résolution client / piano par nom — évite d'avoir à retrouver les IDs
# --------------------------------------------------------------------------

CLIENT_SEARCH_QUERY = """
query($s: String!) {
  allClients(first: 25, filters: {search: $s}) {
    nodes { id companyName defaultContact { firstName lastName } }
  }
}
"""

CLIENT_SCAN_QUERY = """
query {
  allClients {
    nodes { id companyName defaultContact { firstName lastName } }
  }
}
"""

CLIENT_PIANOS_QUERY = """
query($cid: String!) {
  allPianos(first: 50, filters: {clientId: $cid}) {
    nodes { id make model year type serialNumber }
  }
}
"""

PIANOS_SCAN_QUERY = """
query {
  allPianos {
    nodes { id client { id } make model year type serialNumber }
  }
}
"""


class ResolutionAmbigue(RuntimeError):
    """Zéro ou plusieurs correspondances — on ne devine jamais."""


def _client_label(node: Dict[str, Any]) -> str:
    contact = node.get("defaultContact") or {}
    return (node.get("companyName") or "").strip() or \
        " ".join(x for x in [contact.get("firstName"), contact.get("lastName")] if x).strip()


def _nodes(result: Dict[str, Any], key: str) -> List[Dict[str, Any]]:
    return (((result or {}).get("data") or {}).get(key) or {}).get("nodes") or []


def resolve_client(gz, search: str) -> Dict[str, Any]:
    """Cherche le client par nom. Bascule sur un scan complet si le filtre
    `search` n'est pas accepté par le schéma."""
    try:
        nodes = _nodes(gz._execute_query(CLIENT_SEARCH_QUERY, {"s": search}), "allClients")
    except Exception:
        nodes = []
    if not nodes:
        needle = search.lower()
        nodes = [n for n in _nodes(gz._execute_query(CLIENT_SCAN_QUERY), "allClients")
                 if needle in _client_label(n).lower()]
    if not nodes:
        raise ResolutionAmbigue(f"Aucun client ne correspond à « {search} ».")
    if len(nodes) > 1:
        listing = "\n".join(f"  - {_client_label(n)} ({n['id']})" for n in nodes[:15])
        raise ResolutionAmbigue(
            f"{len(nodes)} clients correspondent à « {search} » :\n{listing}\n"
            "Relance avec --client-id.")
    return nodes[0]


def resolve_piano(gz, client_id: str, make: str) -> Dict[str, Any]:
    """Cherche, parmi les pianos du client, celui de la marque demandée."""
    try:
        pianos = _nodes(gz._execute_query(CLIENT_PIANOS_QUERY, {"cid": client_id}), "allPianos")
    except Exception:
        pianos = []
    if not pianos:
        pianos = [p for p in _nodes(gz._execute_query(PIANOS_SCAN_QUERY), "allPianos")
                  if (p.get("client") or {}).get("id") == client_id]
    if not pianos:
        raise ResolutionAmbigue(f"Ce client n'a aucun piano dans Gazelle ({client_id}).")
    matches = [p for p in pianos if make.lower() in (p.get("make") or "").lower()]
    if not matches:
        listing = "\n".join(f"  - {p.get('make')} {p.get('model') or ''} ({p['id']})"
                             for p in pianos)
        raise ResolutionAmbigue(
            f"Aucun piano « {make} » chez ce client. Pianos au dossier :\n{listing}")
    if len(matches) > 1:
        listing = "\n".join(f"  - {p.get('make')} {p.get('model') or ''} "
                            f"{p.get('year') or ''} ({p['id']})" for p in matches)
        raise ResolutionAmbigue(
            f"{len(matches)} pianos « {make} » chez ce client :\n{listing}\n"
            "Relance avec --piano-id.")
    return matches[0]


TITRES = {
    "ciblee": "Travaux ciblés, piano droit Willis & Co. — Éric Le Reste",
    "complete": "Restauration piano droit Willis & Co. (Montréal)",
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scope", choices=("ciblee", "complete"), default="ciblee",
                        help="ciblee = 5 postes convenus avec Éric (défaut) ; "
                             "complete = restauration complète en 2 options")
    parser.add_argument("--client-search",
                        help="Nom du client à résoudre dans Gazelle (ex. \"Éric Le Reste\") — "
                             "évite d'avoir à retrouver les IDs")
    parser.add_argument("--yes", action="store_true",
                        help="Confirme la création après une résolution par nom")
    parser.add_argument("--client-id", help="ID Gazelle du client (cli_xxx)")
    parser.add_argument("--piano-id", help="ID Gazelle du piano (ins_xxx)")
    parser.add_argument("--client-name", help="Nom attendu — garde d'identité")
    parser.add_argument("--piano-make", default="Willis", help="Marque attendue — garde d'identité")
    parser.add_argument("--dry-run", action="store_true", help="Aperçu seulement, rien n'est créé")
    args = parser.parse_args()

    today = date.today()
    estimated_on = today.isoformat()
    expires_on = (today + timedelta(days=VALIDITE_JOURS)).isoformat()

    scope = build_scope(args.scope)
    tiers, notes = scope["tiers"], scope["notes"]

    violations = lint(tiers)
    if violations:
        print("Lint bloquant — rien créé :", file=sys.stderr)
        for v in violations:
            print(f"  - {v}", file=sys.stderr)
        return 1

    if len(tiers) > 1:
        missing = validate_inclusion(tiers[0], tiers[1])
        if missing:
            print("Tier 2 n'inclut pas Tier 1 — rien créé :", file=sys.stderr)
            for m in missing:
                print(f"  - {m}", file=sys.stderr)
            return 1

    client_id, piano_id = args.client_id, args.piano_id
    client_name = args.client_name

    if args.client_search and not (client_id and piano_id):
        from core.gazelle_api_client import GazelleAPIClient
        gz = GazelleAPIClient()
        client = resolve_client(gz, args.client_search)
        piano = resolve_piano(gz, client["id"], args.piano_make)
        client_id, piano_id = client["id"], piano["id"]
        client_name = client_name or _client_label(client)
        print(f"Client : {_client_label(client)} ({client_id})")
        print(f"Piano  : {piano.get('make')} {piano.get('model') or ''} "
              f"{piano.get('year') or ''} ({piano_id})".replace("  ", " "))
        if not args.yes:
            print("\nRelance avec --yes pour créer la soumission.")
            print_preview(tiers, notes, estimated_on, expires_on, TITRES[args.scope])
            return 0

    if args.dry_run or not (client_id and piano_id):
        print_preview(tiers, notes, estimated_on, expires_on, TITRES[args.scope])
        if not args.dry_run:
            print("\n[!] Identité du client manquante : aperçu seulement, rien n'a été créé. "
                  "Utilise --client-search \"Nom\" ou --client-id/--piano-id.", file=sys.stderr)
        return 0

    est = create_in_gazelle(client_id, piano_id, tiers, notes,
                            estimated_on, expires_on,
                            client_name, args.piano_make)
    print(f"✅ Soumission #{est['number']} créée ({est['id']})")
    for tier in tiers:
        t = tier_totals(tier)
        print(f"   {tier_titre(tier, len(tiers))} : {money(t['total'])} (taxes incluses)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
