# Bundles de service — philosophie et catalogue

## Concept

Un **bundle** est un service facturé en UNE seule ligne sur la soumission,
dont la `description` est surchargée dynamiquement avec la liste des actions
réellement sélectionnées pour CE piano. But : éviter la prolifération d'items
à 0 $ et donner au client une vue claire de ce qu'il paie.

## Fichier source

`C:\PTM\assistant-v6\sandbox\app\modules\gazelle\service_bundles.py`

Chaque bundle contient :
- `msl_id` : lien vers le MasterServiceItem Gazelle (source de vérité du prix)
- `name` : libellé par défaut
- `amount_cents` : montant en cents
- `item_type` : généralement `LABOR_FIXED_RATE`
- `description_header` : phrase d'intro (ex: "Inclut pour votre piano :")
- `actions` : liste d'actions cochables, chacune avec `code`, `label`, `default`

## Bundles actuels (Phase 1 — 4 pilotes)

| Code | MSL ID | Montant | Actions |
|---|---|---|---|
| `grand_entretien_droit` | mit_l6o2sjpCLZn9ZUHi | 1 045 $ | 8 (nettoyage → accord final) |
| `grand_entretien_queue_1j` | mit_FQKKxagZOiQQQHYh | 1 045 $ | 8 (mêmes actions adaptées queue) |
| `cordes_basses_complet` | mit_2HBYLndAxf1C993j | 2 000 $ | 5 (fabrication → accord) |
| `remplacement_marteaux_droit` | mit_pDYrT2B8oxWAJ7ou | 1 250 $ | 6 (dépose → accord post) |

## Bundles à créer (Phase 3 — cibles)

1. `grand_entretien_queue_2j` — 1 995 $
2. `entretien_recuperation` — prix à récupérer
3. `entretien_apres_rodage` — prix à récupérer
4. `pls_install_droit` — 975 $
5. `pls_install_queue_complet` — 1 135 $
6. `pls_install_queue_sec` — 449 $
7. `pls_install_2cuves` — 1 688 $
8. `pls_install_2cuves_arriere` — 1 788 $
9. `remplacement_marteaux_queue` — 1 850 $

## Contraintes dures

- ❌ **JAMAIS d'accord de suivi 3 semaines post-PLS install** dans les bundles
  `pls_install_*`. C'est un service facturé séparément, pas une étape de l'installation.
- Les actions par défaut (`default: True`) doivent refléter ce que Nicolas fait
  dans 90 % des cas — sous-projet `bundles-checklists-plan.md` en cours.
- Les libellés doivent être compréhensibles par un client non technicien.

## Pattern de fusion matériel + labour

Quand un service combine du matériel et de la main-d'œuvre qui sont 2 MSL séparés
dans Gazelle (ex: cordes des basses = matériel 1 200 $ + installation 800 $), on
les fusionne en UN seul bundle à prix combiné. Le `msl_id` pointe sur l'un des
deux (généralement le matériel), et `amount_cents` est surchargé avec le total.
