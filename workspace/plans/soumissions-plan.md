# Refonte des soumissions Gazelle — plan d'architecture

**Statut :** 🟢 actif
**Créé le :** 2026-04-11
**Dernière mise à jour :** 2026-04-15
**Prochain pas :** Terminer la phase 3 (digest info@ à 8h00 pour les soumissions sans relance, tag `relance-faite` côté Gazelle). Le module `modules/briefing/follow_up_digest.py` reste à écrire ; le scheduler a déjà la place pour la tâche, l'infrastructure SQL est prête (table `critical_estimate_notifications` avec colonne `kind`, à exécuter dans Supabase). Ensuite : draft du message équipe sur le suivi à envoyer via Gmail.
**Bloqué par :** rien — Allan a validé tag = `relance-faite`, fenêtre 7-90 jours, destinataire info@, heure 8h.

**Phases complétées :**
- ✅ Phase 1 — Module v6 `service_bundles.py` + helpers `build_service_bundle_item` / `build_estimate_notes` / `validate_tier_inclusion` (132 tests verts)
- ✅ Phase 2 — Reconstruction de soumissions réelles (#11915 Murray, #11916 Deraps, #11919 Sutton, #11920 Ariza, #11921 Murray fresh, #11922 Grands Ballets touches, #11880 Grands Ballets PLS+housse)
- ✅ Phase 2bis — Digest 7h Louise des soumissions critiques avant RV (déployé commit 002844f)
- 🟡 Phase 3 — Digest 8h info@ des soumissions sans relance (en cours)
- ⏳ Phase 4 — CLI `sandbox/scripts/build_estimate.py`
- ⏳ Phase 5 — Migrer Nicolas vers le nouveau workflow

**Sous-projets dérivés :**
- `bundles-checklists-plan.md` — qualité des listes d'actions par bundle
- `soumissions-analytics-plan.md` — mesure du ROI des améliorations (statut : en attente phase 3)

---

## Pour toi, Claude de la nouvelle session

**Lis CE FICHIER EN ENTIER avant de toucher à quoi que ce soit.** Il contient :
1. Le contexte métier (pourquoi cette refonte)
2. Les 3 frictions à résoudre
3. L'architecture solution en 4 couches
4. Les décisions déjà prises
5. La checklist des tâches à attaquer
6. Les références vers le code existant

Allan est en mode autonomie maximale — décisions techniques sans confirmation, sauf changements d'architecture majeurs. Parle-lui en français. Commits en anglais.

---

## 1. Contexte métier

Piano Tek Musique émet des soumissions via **Gazelle** (GraphQL privé `https://gazelleapp.io/graphql/private/`). Les soumissions actuelles souffrent de trois frictions que le client ressent :

### Friction 1 — Options pas claires
Les techniciens créent souvent deux "tiers" (option 1 / option 2) pour donner le choix au client. Mais structurellement, les deux tiers sont souvent des **alternatives** et non des **niveaux croissants**. Exemple réel : sur la soumission **#11914 Isabelle Murray**, le tier 2 **retire** le traitement du sommier et **ajoute** des cordes. Résultat : le client ne comprend pas la différence et n'arrive pas à décider.

### Friction 2 — Détails via items à 0 $
Les techniciens veulent documenter ce qui est inclus dans un service (exemple : *un "Grand entretien" à 1 045 $ inclut nettoyage, lubrification, serrage des vis, harmonisation, etc.*). Actuellement, la seule façon d'afficher ces détails côté client est de créer des **items supplémentaires à 0 $**, ce qui pollue visuellement la facture et déroute le client.

### Friction 3 — Avertissements qui polluent
Les avertissements (*« les nouvelles cordes vont s'étirer, plusieurs accords seront nécessaires »*) sont actuellement mis comme des items à 0 $ avec un nom très long. Ce n'est pas leur place.

---

## 2. La découverte clé

**Gazelle a déjà deux champs texte par item** qu'on n'utilise pas à leur plein potentiel :

| Champ | Type | Usage | État actuel |
|---|---|---|---|
| `description` | I18nString | "Le quoi" — liste des actions concrètes | Utilisé sur 20 items multi-ligne |
| `educationDescription` | I18nString | "Le pourquoi" — explication pédagogique | Rempli sur **124 items** du MSL |

Vérifié par introspection et lecture des MSL items le 2026-04-11. Le *Grand entretien piano droit* (mit_xxx, 1 045 $) a déjà :

- `description` : *« Nettoyage en profondeur. Serrer toutes les vis de mécanique, du meuble et des pentures. Lubrifier les tiges du clavier et les garnitures de noix de marteaux. Sabler les marteaux. Niveler le clavier. Accord, réglages, harmonisation. »* (232 chars)
- `educationDescription` : *« Avec le temps, les feutres et les cuirs se tassent et s'usent, les touches bougent moins librement et avec moins de précision... »* (406 chars)

**Donc on a déjà l'espace visuel côté client pour détailler sans multiplier les items.** Il faut juste l'utiliser intelligemment.

---

## 3. Solution : réutiliser les champs existants + contraintes structurelles

### Solution à Friction 1 (options claires) — inclusion stricte
Règle : **Tier 2 ⊇ Tier 1 strictement.** Tier 2 contient **tous** les items de Tier 1, **plus** des extras. Le client pense naturellement : *« Si je prends l'option 2, je paie un peu plus, je reçois tout ça en plus. »*

Le schéma `PrivateEstimateTierInput` n'accepte pas de champ `name` (confirmé par introspection). Mais il accepte `notes` — on y met le libellé de l'option :
- Tier 1 : `notes = "Option essentielle — les réparations indispensables"`
- Tier 2 : `notes = "Option recommandée — tout de l'option 1 + harmonisation et cordes aiguës"` + `isPrimary = True`

### Solution à Friction 2 (détails sans inflation) — override de la description
Au moment de créer l'item "Grand entretien" dans la soumission, on **surcharge dynamiquement** sa `description` avec une liste formatée des actions réellement pertinentes pour CE piano, sans toucher au `masterServiceItemId` ni au montant.

Rendu attendu côté client :
```
Grand entretien piano droit                                1 045,00 $

Inclut pour votre piano :
  • Nettoyage en profondeur du clavier, cavités, sommier et meuble
  • Lubrification des tiges de clavier et noix de marteaux
  • Serrage de toutes les vis de mécanique et meuble
  • Harmonisation légère des marteaux
  • Accord final à 440 Hz

Pourquoi c'est important : avec le temps, les feutres se tassent...
[educationDescription du MSL — héritée, pas touchée]
```

Aucun item à 0 $. Un seul item facturé. Détails personnalisés.

### Solution à Friction 3 (avertissements) — notes de la soumission
Les avertissements vont dans le champ `notes` de `PrivateUpdateEstimateInput` (niveau soumission), ou dans les `notes` du tier concerné. Ces zones sont rendues séparément de la liste d'items côté client.

---

## 4. Architecture cible — 4 couches

### Couche 1 — Catalogue des bundles de service (data layer)

**Nouveau fichier :** `C:\PTM\assistant-v6\sandbox\app\modules\gazelle\service_bundles.py`

Format :
```python
BUNDLES = {
    "grand_entretien_droit": {
        "msl_id": "mit_xxx",              # id MSL Gazelle, porte le prix
        "name": "Grand entretien piano droit",
        "amount_cents": 104500,
        "item_type": "LABOR_FIXED_RATE",
        "description_header": "Inclut pour votre piano :",
        "actions": [
            {"code": "nettoyage",      "label": "Nettoyage en profondeur du clavier, cavites, sommier et meuble",   "default": True},
            {"code": "serrage_vis",    "label": "Serrage de toutes les vis de mecanique et meuble",                 "default": True},
            {"code": "lubrification",  "label": "Lubrification des tiges de clavier et noix de marteaux",            "default": True},
            {"code": "nivel_clavier",  "label": "Nivellement du clavier",                                            "default": False},
            {"code": "harmo_marteaux", "label": "Harmonisation legere des marteaux",                                 "default": True},
            {"code": "accord_final",   "label": "Accord final a 440 Hz",                                             "default": True},
        ],
    },
    # puis: grand_entretien_queue, entretien_recuperation, pls_droit_install, ...
}
```

**Choix délibéré :** fichier Python versionné en git, pas table Supabase. Plus rapide à itérer, testable, zéro dépendance d'infra au démarrage. Migration Supabase possible plus tard si Allan veut une UI d'édition.

**Bundles à créer en priorité (Allan doit valider la liste) :**
1. `grand_entretien_droit` (1 045 $)
2. `grand_entretien_queue_1j` (1 045 $)
3. `grand_entretien_queue_2j` (1 995 $)
4. `entretien_recuperation` — prix à récupérer depuis MSL
5. `entretien_apres_rodage` — prix à récupérer
6. `pls_install_droit` (975 $)
7. `pls_install_queue_complet` (1 135 $)
8. `pls_install_queue_sec` (449 $) — déjà corrigé de 444 $ le 2026-04-09 par Allan
9. `pls_install_2cuves` (1 688 $) — corrigé de 1 400 $ le 2026-04-09
10. `pls_install_2cuves_arriere` (1 788 $) — corrigé de 1 112 $ le 2026-04-09
11. `cordes_basses_complet` (cordes + install = 2 000 $)
12. `remplacement_marteaux_droit` (1 250 $)
13. `remplacement_marteaux_queue` (1 850 $)

Pour chaque bundle, tirer le `msl_id` et le `amount_cents` directement depuis Gazelle via `allMasterServiceItems` — c'est la source de vérité du prix.

### Couche 2 — Builder (logic layer)

**Ajouter à :** `C:\PTM\assistant-v6\sandbox\app\modules\gazelle\estimates.py`

```python
def build_service_bundle_item(
    bundle_code: str,
    selected_action_codes: list[str],
    *,
    sequence_number: int = 0,
    custom_header: Optional[str] = None,
    custom_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Construit un PrivateEstimateTierItemInput a partir d'un bundle
    avec selection d'actions a la carte. La description de l'item est
    surchargee avec la liste formatee des actions selectionnees."""
    bundle = BUNDLES[bundle_code]
    actions = [a for a in bundle["actions"] if a["code"] in selected_action_codes]
    header = custom_header or bundle["description_header"]
    description_lines = [header, ""] + [f"  • {a['label']}" for a in actions]
    description = "\n".join(description_lines)
    return build_item_input(
        name=custom_name or bundle["name"],
        amount_cents=bundle["amount_cents"],
        description=description,
        master_service_item_id=bundle["msl_id"],
        sequence_number=sequence_number,
        item_type=bundle.get("item_type", ItemType.LABOR_FIXED_RATE),
    )
```

Tests unitaires obligatoires (le module en a déjà 90+ qui passent). Ajouter :
- Test: filtre correctement les actions par `selected_action_codes`
- Test: respecte l'ordre des actions dans le bundle
- Test: header custom override le header du bundle
- Test: description contient toutes les actions sélectionnées, formatées avec puces
- Test: lève une erreur claire si `bundle_code` inconnu

### Couche 3 — Helpers pour tiers inclusifs + avertissements (architecture)

**Ajouter à :** `estimates.py`

```python
def build_estimate_notes(
    body: str,
    warnings: Optional[list[str]] = None,
    signature: Optional[str] = None,
) -> str:
    """Compose les notes de la soumission avec une section warnings."""
    parts = [body.strip()]
    if warnings:
        parts.append("")
        parts.append("AVERTISSEMENTS")
        for w in warnings:
            parts.append(f"  • {w}")
    if signature:
        parts.append("")
        parts.append(signature)
    return "\n".join(parts)


def validate_tier_inclusion(tier_base: dict, tier_extended: dict) -> list[str]:
    """Retourne la liste des codes d'items du tier de base qui ne sont
    PAS presents dans le tier etendu. Liste vide = inclusion stricte OK.
    Utilise name + master_service_item_id comme cle de comparaison."""
    # ... implementation
```

### Couche 4 — CLI interactive (tooling)

**Nouveau script :** `C:\PTM\assistant-v6\sandbox\scripts\build_estimate.py`

Flow :
1. `--client` ou recherche interactive par nom
2. `--piano` ou auto-sélection si un seul
3. Choix du / des bundles à inclure
4. Pour chaque bundle : affichage de la checklist, cocher/décocher (par défaut = les `default: True`)
5. Choix des avertissements (liste prédéfinie, cochables)
6. Dry-run : affichage visuel de la soumission reconstituée
7. Confirmation → `create_estimate` + `update_estimate`

Plus tard, cette logique pourra alimenter une UI React côté v5 ou v6.

---

## 5. Décisions déjà prises (ne pas réouvrir)

| Décision | Raison |
|---|---|
| Utiliser les champs `description` et `notes` existants, pas créer de nouveaux items à 0 $ | Les 2 champs sont déjà rendus par Gazelle côté client (124 items MSL utilisent `educationDescription`) |
| Bundles en fichier Python versionné, pas table Supabase | Plus rapide à itérer, testable, pas de dépendance infra, migrable plus tard |
| Tier 2 strictement inclusif de Tier 1 | Règle UX claire pour le client, évite la confusion de #11914 |
| Libellé des tiers dans leur champ `notes` | Le champ `name` n'existe pas sur `PrivateEstimateTierInput` (validé par introspection 2026-04-09) |
| Surcharge dynamique de `description` par soumission | Permet la personnalisation par piano sans toucher au MSL |
| Module v6, pas v5 | v6 a déjà le module `app/modules/gazelle/` avec 90 tests verts, v5 est le legacy |

---

## 6. Ce qui existe déjà (NE PAS DUPLIQUER)

- **Module Gazelle v6** : `C:\PTM\assistant-v6\sandbox\app\modules\gazelle\`
  - `client.py` — `GazelleClient`, auth via token Supabase
  - `estimates.py` — `create_estimate`, `update_estimate`, `get_estimate_by_number`, `build_item_input`, `build_group_input`, `build_tier_input`, `build_taxes_block`, `ItemType`
  - Tests : `C:\PTM\assistant-v6\sandbox\tests\modules\gazelle\` — 90 tests verts
- **Script v5 d'analyse** : `C:\PTM\assistant-gazelle-v5\scripts\review_estimate.py` — analyse les soumissions existantes avec Claude, propose des corrections
- **Client Gazelle v5** : `C:\PTM\assistant-gazelle-v5\core\gazelle_api_client.py` — version historique avec `get_estimate_by_number` et `update_estimate` aussi disponibles
- **`.env`** : `C:\PTM\assistant-gazelle-v5\.env` — contient `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `ANTHROPIC_API_KEY`. Charger avec `load_dotenv('C:/PTM/assistant-gazelle-v5/.env')` depuis n'importe quel script Python.

---

## 7. Checklist des tâches (dans l'ordre)

### Phase 1 — Couches 1-2 (foundation)
- [ ] Créer `service_bundles.py` avec 4 bundles pilote : grand entretien droit, grand entretien queue 1j, cordes basses complet, remplacement marteaux droit
- [ ] Récupérer les vrais `msl_id` et `amount_cents` depuis Gazelle pour ces 4 bundles (query `allMasterServiceItems` filtré par nom)
- [ ] Ajouter `build_service_bundle_item()` dans `estimates.py`
- [ ] Ajouter `build_estimate_notes()` et `validate_tier_inclusion()` dans `estimates.py`
- [ ] Exporter les nouveaux symboles dans `__init__.py`
- [ ] Tests unitaires (viser ~15 tests neufs)
- [ ] `pytest` doit rester 100 % vert

### Phase 2 — Validation visuelle sur une vraie soumission
- [ ] **Reconstruire #11914 (Isabelle Murray)** avec la nouvelle architecture :
  - Tier 1 "Essentiel" = mécanique essentielle + clavier + sommier + cordes basses
  - Tier 2 "Recommandée" = Tier 1 + cordes médium + resurfaçage V + harmonisation
  - Notes de soumission = texte personnalisé + avertissements
  - Descriptions d'items = listes d'actions via `build_service_bundle_item()`
- [ ] Créer une soumission #test dans Gazelle (ne PAS toucher #11914 original)
- [ ] Allan vérifie visuellement côté app Gazelle client
- [ ] Itérer sur la mise en page jusqu'à ce qu'Allan valide

### Phase 3 — Complétion des bundles
- [ ] Valider avec Allan la liste finale des ~15 bundles
- [ ] Créer les bundles manquants
- [ ] Peupler les actions de chaque bundle avec Allan (ou ingest depuis les checklists Gazelle existantes qu'il a analysées hier)

### Phase 4 — CLI
- [ ] Écrire `scripts/build_estimate.py`
- [ ] Allan teste sur un nouveau client réel
- [ ] Documenter l'usage

### Phase 5 — Migration progressive
- [ ] Remplacer le workflow de Nicolas (le principal créateur de soumissions) vers la nouvelle CLI
- [ ] Éventuellement intégrer dans UI v5 (bouton "Nouvelle soumission intelligente")

---

## 8. Contraintes techniques importantes (pièges déjà rencontrés)

Tout ce qui est ci-dessous est **validé en prod** le 2026-04-09/10 sur la soumission de test #11912 (Mario Demartini). Ne pas réapprendre à tes dépens.

- **Ne jamais envoyer `estimateTiers` dans `createEstimate`** → erreur Ruby `"undefined method 'each' for nil"`. Toujours faire `createEstimate` minimal puis `updateEstimate` avec les tiers.
- **`pianoId`, `estimatedOn`, `expiresOn` sont NON_NULL** dans `PrivateCreateEstimateInput`.
- **Les OUTPUTS utilisent les préfixes `all*`** : `allEstimateTiers`, `allEstimateTierGroups`, `allEstimateTierItems`, `allUngroupedEstimateTierItems`. **Les INPUTS utilisent les noms sans préfixe** : `estimateTierGroups`, `estimateTierItems`, `ungroupedEstimateTierItems`.
- **`PrivateEstimateTierGroupInput.estimateTierItems`** (pas `estimateItems` — erreur que j'ai faite sur #11912 au premier essai).
- **`PrivateEstimateTier` n'a PAS de champ `name`** en input ni en output. Utiliser `notes` pour libeller le tier.
- **`type` obligatoire sur les items** (enum `MasterServiceItemType`). Sans valeur valide → `"Kind n'est pas inclus(e) dans la liste"`. Défaut dans v6 : `LABOR_FIXED_RATE`. Valeurs : `LABOR_FIXED_RATE | LABOR_HOURLY | EXPENSE | MILEAGE | OTHER`.
- **Taxes** : chaque item taxable doit envoyer `{taxId, rate, total}`. Le champ `rate` est obligatoire (sinon `"nil can't be coerced into Integer"`). Utiliser `build_taxes_block()` qui gère tout :
  - TPS : `taxId="tax_JeCfY4wfbXtN6J28"`, `rate=5000` → 5,000 %
  - TVQ : `taxId="tax_xe9FEApq94zI7kXD"`, `rate=9975` → 9,975 %
- **`photos: []`** obligatoire sur chaque item (liste vide OK).
- **`duration: 0`** explicite si non fourni (pas null).
- **Ne jamais envoyer `externalUrl: null` ou `externalUrl: ""`** → omettre complètement.
- **`mutationErrors` à vérifier** à chaque réponse (HTTP 200 peut cacher des erreurs métier). `_raise_if_mutation_errors()` le fait dans v6.
- **Filtre `number` n'existe pas** dans `PrivateAllEstimatesFilter`. Utiliser `search: "11914"` puis filtrer le numéro exact côté Python. `get_estimate_by_number()` le fait dans v6.
- **Montants en cents** (`45000` = 450 $), **quantités en centièmes** (`100` = 1 unité).
- **Endpoint GraphQL** : `https://gazelleapp.io/graphql/private/` (slash final important).
- **Auth** : token API < 50 chars → header `x-gazelle-api-key`, sinon `Authorization: Bearer`. Déjà géré dans `GazelleClient`.

---

## 9. Première action à faire quand tu prends la relève

1. **Demande à Allan** s'il valide la liste des 4 bundles pilote de la Phase 1, et s'il veut commencer par reconstruire **#11914** ou partir sur un nouveau client réel.
2. **Lis `C:\PTM\assistant-v6\sandbox\app\modules\gazelle\estimates.py`** en entier pour te mettre à jour sur l'API actuelle et ne pas dupliquer les helpers.
3. **Attaque la Couche 1** (`service_bundles.py`) et itère avec Allan sur le format.

Bonne continuation.

— session source du 2026-04-11
