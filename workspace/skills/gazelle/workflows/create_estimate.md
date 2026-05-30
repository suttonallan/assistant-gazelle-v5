# Workflow — Créer une soumission intelligente

## Pré-requis

- Client ID Gazelle (`cli_xxx`)
- Piano ID Gazelle (`ins_xxx`)
- Connaître les services à inclure (bundles ou items manuels)

## Flow

### 1. Construire les items

Pour chaque service :
- **Si un bundle existe** → `build_service_bundle_item(bundle_code, action_codes)`
- **Si pas de bundle** → `build_item_input(name, amount_cents, description=..., master_service_item_id=...)`

Pour chaque item, écrire une `description` qui liste les actions en puces. Ne JAMAIS
créer d'items à 0 $ pour documenter.

### 2. Organiser en groupes et tiers

```python
group = build_group_input(name="Mécanique", items=[item1, item2])
tier1 = build_tier_input(
    sequence_number=0,
    is_primary=True,  # ou False si c'est l'option de base
    notes="Option essentielle — les réparations indispensables.",
    groups=[group_meca, group_clavier, group_cordes],
)
```

Si 2 tiers :
- Tier 1 = option de base
- Tier 2 = Tier 1 + extras (**inclusion stricte obligatoire**)

```python
missing = validate_tier_inclusion(tier1, tier2)
assert missing == [], f"Tier 2 manque: {missing}"
```

### 3. Composer les notes de soumission

```python
notes = build_estimate_notes(
    body="Texte personnalisé pour le client...",
    warnings=[
        "Les nouvelles cordes vont s'étirer...",
        "Le sommier étant fatigué...",
    ],
    # PAS de signature — Allan l'a explicitement demandé (2026-04-12).
    # Gazelle identifie déjà l'entreprise dans le header de la soumission.
)
```

### 4. Créer dans Gazelle (2 étapes)

```python
# Étape 1 — création minimale (JAMAIS de tiers ici)
estimate = create_estimate(
    client_id="cli_xxx",
    piano_id="ins_xxx",
    estimated_on="2026-04-12",
    expires_on="2026-05-12",
    locale="fr_CA",
)

# Étape 2 — peuplement tiers + notes (garde d'identité OBLIGATOIRE)
update_estimate_safe(
    estimate["number"],
    {"notes": notes, "estimateTiers": [tier1, tier2]},
    expected_client_name="Isabelle Murray",
    expected_piano_make="Schomaker",
)
```

**RÈGLE ABSOLUE — update_estimate_safe() au lieu de update_estimate() :**
Pour toute modification d'une soumission existante, **TOUJOURS** passer par
`update_estimate_safe(numero, payload, expected_client_name=..., expected_piano_make=...)`.
Le helper résout l'ID par le numéro public et vérifie que le client et le
piano correspondent AVANT d'envoyer l'update. Si mismatch, `EstimateIdentityMismatch`
est levé — aucune contamination possible.

Contexte : le 2026-04-12, #11915 (Isabelle Murray) a été écrasée avec les
données d'une autre soumission (Sutton/Fuchs & Mohr) parce qu'un ID avait été
copié-collé à tort dans un script one-off. Les champs `client`/`piano` ne
sont pas dans `PrivateUpdateEstimateInput`, donc Gazelle n'a rien bloqué.
Jamais plus d'update direct avec un ID hardcodé.

### 5. Vérifier

- Vérifier `mutationErrors` (géré automatiquement par v6)
- Comparer le `recommendedTierTotal` retourné avec le calcul attendu
- Marquer les notes `[TEST — ne pas envoyer au client]` si c'est un test

## Exemples réels

- **#11915** : reconstruction d'Isabelle Murray (#11914) — 2 tiers, 5 groupes, bundle cordes_basses
- **#11916** : reconstruction de Francine Deraps (#11913) — 2 tiers, 3 bundles simultanés

## Notes techniques

- Si v6 n'a pas le `SERVICE_ROLE_KEY`, utiliser le client v5 pour les mutations
  mais les builders v6 pour le payload. Voir pattern d'import dans SKILL.md.
- Toujours `PYTHONIOENCODING=utf-8` sur Windows.
