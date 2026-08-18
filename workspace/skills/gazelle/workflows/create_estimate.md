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

## Authentification — le pont v5 → v6 qui marche (2026-08-18)

`SKILL.md` dit d'utiliser le client v5 pour les mutations parce que le sandbox v6 n'a
que la clé anon. Mieux : **`GazelleClient` accepte un jeton explicite**, donc on peut
utiliser TOUTE la chaîne v6 — builders, lint, `create_estimate`, `update_estimate_safe`
et sa garde d'identité — en lui injectant le jeton lu par le client v5 :

```python
import sys
sys.path.insert(0, r"C:\PTMssistant-gazelle-v5")
sys.path.insert(0, r"C:\PTMssistant-v6\sandbox")

from core.supabase_storage import SupabaseStorage
from app.modules.gazelle.client import GazelleClient

tok = SupabaseStorage().get_system_setting("gazelle_oauth_token")
if isinstance(tok, dict):
    tok = tok.get("access_token") or tok.get("api_key") or tok.get("token")
gz = GazelleClient(token=str(tok))     # <- puis passer client=gz partout
```

⚠️ Piège corrigé le 2026-08-18 : le `.env` de v5 est **partagé** avec v6, et
`pydantic-settings` y refusait toute clé non déclarée (`extra_forbidden`). Ajouter une
clé sans rapport (`toggl_api_token`) suffisait à rendre tout le module gazelle v6
inutilisable. Corrigé par `extra: "ignore"` dans `assistant-v6/sandbox/app/config.py`.
Si `get_settings()` explose sur une clé inconnue, c'est ça.

## LINT AVANT CRÉATION — obligatoire

`lint_estimate(payload)` existe et **doit tourner avant `create_estimate`**, sinon une
violation ne se découvre qu'une fois la soumission créée dans Gazelle.

```python
from app.modules.gazelle.estimates import lint_estimate

violations = lint_estimate({"estimateTiers": [tier], "notes": notes})
blocking = [v for v in violations if v.severity == "error"]
if blocking:
    raise SystemExit("Lint bloquant — rien créé.")
```

Règle qui mord en pratique : **`ZERO_DOLLAR_ITEM`**. Un item à 0 $ pour documenter une
inclusion est refusé — replier la mention dans la `description` d'un item facturé et
dans les notes. ⚠️ Des soumissions existantes violent cette règle (#11967 porte une
ligne « Libération du clavier et nivelage fin » à 0 $) : **ne pas prendre une soumission
existante comme preuve de conformité**, passer le lint.

## Copier une soumission vers un autre client

`clone_estimate(source_number, new_client_id, new_piano_id, ...)` fait le trajet complet :
lecture du modèle → reconstruction des tiers (taxes régénérées avec leur `name`) → lint →
create → `update_estimate_safe`. Il accepte `dry_run=True` pour prévisualiser sans rien créer.

Il ne convient PAS quand il faut **modifier les montants ou les lignes** (ex. même cliente,
autre produit) : dans ce cas, lire la source pour en calquer la structure, puis reconstruire
les items à la main avec les builders. Exemple réel : **#11987** (Vario, 9 500 $) calquée sur
**#11967** (Adsilent) pour la même cliente et le même piano.

## Exemples réels

- **#11915** : reconstruction d'Isabelle Murray (#11914) — 2 tiers, 5 groupes, bundle cordes_basses
- **#11916** : reconstruction de Francine Deraps (#11913) — 2 tiers, 3 bundles simultanés
- **#11987** : Vario 9 500 $ pour Pascale Gasse — calquée sur #11967 (Adsilent), 1 seul tier,
  ligne à 0 $ de la source repliée dans la description après refus du lint

## Notes techniques

- Si v6 n'a pas le `SERVICE_ROLE_KEY` : injecter le jeton dans `GazelleClient(token=...)`
  et garder toute la chaîne v6 (voir § Authentification ci-dessus). Le vieux conseil
  « builders v6 + mutations v5 » fonctionne aussi mais prive du lint et de la garde d'identité.
- Toujours `PYTHONIOENCODING=utf-8` sur Windows.
