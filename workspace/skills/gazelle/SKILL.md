---
name: gazelle
description: |
  Interact with the Gazelle CRM API (GraphQL private endpoint) for Piano Tek Musique.
  TRIGGER when: user asks to create/modify/read estimates (soumissions), create/clone
  appointments (rendez-vous), look up clients or pianos, query master service items,
  or any operation involving gazelleapp.io. Also triggers on keywords: soumission,
  estimate, devis, rendez-vous, RV conjoint, bundle, tier, MSL, Gazelle.
---

# Skill Gazelle — API Gazelle pour PTM

Tu es l'agent qui pilote les opérations Gazelle pour Piano Tek Musique. Ce skill
couvre TOUTES les interactions avec l'API GraphQL privée `https://gazelleapp.io/graphql/private/`.

## Architecture et code existant

### Module v6 (source de vérité pour les builders)
```
C:\PTM\assistant-v6\sandbox\app\modules\gazelle\
├── client.py          — GazelleClient (auth token Supabase, retry 401)
├── estimates.py       — builders + helpers soumissions
├── service_bundles.py — catalogue des bundles de service (dict BUNDLES)
└── __init__.py        — exports publics
```

**Helpers disponibles (tous dans `estimates.py`) :**
- `build_item_input(name, amount_cents, ...)` — construit un PrivateEstimateTierItemInput
- `build_group_input(name, items)` — construit un PrivateEstimateTierGroupInput
- `build_tier_input(groups, notes, is_primary, ...)` — construit un PrivateEstimateTierInput
- `build_taxes_block(amount_cents, taxable)` — bloc TPS+TVQ québécois
- `build_service_bundle_item(bundle_code, selected_actions, ...)` — construit un item depuis un bundle
- `build_estimate_notes(body, warnings, signature)` — compose les notes de soumission
- `validate_tier_inclusion(tier_base, tier_extended)` — vérifie Tier 2 ⊇ Tier 1
- `create_estimate(client_id, piano_id, ...)` — étape 1 (création minimale)
- `update_estimate(estimate_id, update_input, ...)` — étape 2 (peuplement tiers)
- `get_estimate_by_number(number)` — lecture d'une soumission existante

**Bundles disponibles (dans `service_bundles.py`) :**
- `get_bundle(code)` — récupère un bundle par code
- `list_bundle_codes()` — liste triée des codes
- `BUNDLES` — dict complet

### Client v5 (pour l'auth quand v6 n'a pas le service_role_key)
```
C:\PTM\assistant-gazelle-v5\core\gazelle_api_client.py
```
Le v6 sandbox n'a que la clé anon (lecture seule). Pour les mutations en prod,
utiliser le client v5 qui lit le token depuis Supabase system_settings.

**Pattern d'import combiné :**
```python
import sys
sys.path.insert(0, r"C:\PTM\assistant-gazelle-v5")
sys.path.insert(0, r"C:\PTM\assistant-v6\sandbox")
from core.gazelle_api_client import GazelleAPIClient  # auth v5
from app.modules.gazelle.estimates import (             # builders v6
    build_item_input, build_group_input, build_tier_input,
    build_service_bundle_item, build_estimate_notes,
    validate_tier_inclusion,
)
```

### Env
- `.env` avec credentials : `C:\PTM\assistant-gazelle-v5\.env`
- Toujours `PYTHONIOENCODING=utf-8` quand tu lances Python (Windows cp1252 vs emojis v5)

## Règles métier ABSOLUES

Lis `reference/schema_gotchas.md` avant toute opération GraphQL. Les pièges ont été
validés en prod et coûtent du temps si réappris. Résumé critique :

1. **JAMAIS `estimateTiers` dans `createEstimate`** → crash Ruby. Toujours create minimal puis update.
2. **`type` OBLIGATOIRE** sur chaque item (défaut `LABOR_FIXED_RATE`).
3. **`photos: []`** obligatoire, **`duration: 0`** explicite, **jamais `externalUrl: null`**.
4. **Taxes** : items taxables → **OMETTRE le champ `taxes`** (Gazelle auto-applique). Items non taxables ou 0 $ → `taxes: []`. Ne PAS envoyer de bloc taxes explicite sur les items taxables — ça désactive les checkboxes auto dans l'UI (#11915/#11916).
5. **Montants en cents**, quantités en centièmes.
6. **`mutationErrors` à vérifier** même si HTTP 200.
7. **Filtre `number`** n'existe pas → utiliser `search` puis filtrer côté Python.
8. **Tier 2 ⊇ Tier 1 strictement** — vérifier avec `validate_tier_inclusion()` avant d'envoyer.
9. **Pas d'items à 0 $** pour documenter — utiliser `description` surchargée ou `notes` de soumission.
10. **Avertissements dans `notes`** de soumission (via `build_estimate_notes(warnings=[...])`), pas en items.

## Règles bundles

Lis `reference/bundles.md` pour comprendre la philosophie. Points clés :
- Un bundle = une seule ligne facturée, description surchargée avec actions en puces
- Les actions cochées par défaut doivent refléter la pratique réelle de Nicolas
- **JAMAIS d'accord de suivi 3 semaines post-PLS** dans les bundles `pls_install_*`

## Workflows disponibles

### Soumissions
Lis `workflows/create_estimate.md` pour le flow complet.

### RV conjoints (apprenti)
Lis `workflows/clone_appointment_joint.md` pour le flow.

### Lecture / analyse
Lis `workflows/read_estimate.md` pour les patterns de requête.

## Langue et style

- **Code et commits** : anglais
- **Communication avec Allan** : français
- **Notes de soumission** : français (fr_CA), ton professionnel mais accessible
- **Noms de bundles et codes** : snake_case anglophone (`grand_entretien_droit`)
