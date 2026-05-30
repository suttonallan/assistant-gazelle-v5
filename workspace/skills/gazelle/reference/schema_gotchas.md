# Pièges du schéma GraphQL Gazelle — validés en prod

Tout ce qui suit a été validé sur l'API privée `https://gazelleapp.io/graphql/private/`
entre le 2026-04-08 et le 2026-04-11. Ces pièges ont coûté des heures de debug en prod.
**Ne pas les réapprendre.**

## Endpoint et auth

- **URL** : `https://gazelleapp.io/graphql/private/` (slash final obligatoire)
- **Auth** : token < 50 chars → header `x-gazelle-api-key`, sinon `Authorization: Bearer`
- Le token est dans Supabase `system_settings`, clé `gazelle_oauth_token`
- Le champ `value` est une **string JSON sérialisée** (double-parse nécessaire)

## Soumissions (Estimates)

### Pattern de création obligatoire en 2 étapes

```
1. createEstimate(input minimal: clientId, pianoId, estimatedOn, expiresOn)
   → NE JAMAIS envoyer estimateTiers ici (erreur Ruby "undefined method 'each' for nil")
2. updateEstimate(id, input avec estimateTiers complets)
```

### Champs obligatoires

- `PrivateCreateEstimateInput` : `clientId`, `pianoId`, `estimatedOn`, `expiresOn` — tous NON_NULL
- **`type`** sur chaque item : enum `MasterServiceItemType`. Sans valeur valide →
  "Kind n'est pas inclus(e) dans la liste". Défaut : `LABOR_FIXED_RATE`.
  Valeurs : `LABOR_FIXED_RATE | LABOR_HOURLY | EXPENSE | MILEAGE | OTHER`
- **`photos: []`** — obligatoire sur chaque item, même vide
- **`duration: 0`** — explicite si non fourni (pas null)

### Champs à ne JAMAIS envoyer si nuls

- **`externalUrl`** : ne pas envoyer `null` ni `""` — omettre complètement la clé
- **`notes`** : ne pas envoyer `None` sur un tier — omettre la clé

### Taxes Québec

Pour les items taxables (`isTaxable: true`, montant > 0) : **NE PAS envoyer
le champ `taxes`** du tout. Gazelle applique automatiquement TPS+TVQ depuis
la config du compte, et les checkboxes apparaissent cochées dans l'UI.

Envoyer un bloc `taxes: [{taxId, rate, total}]` explicite crée un **override
manuel** qui désactive les checkboxes auto dans l'UI — Nicolas doit alors les
recocher à la main. Découvert sur #11915 et #11916 le 2026-04-12.

Pour les items NON taxables (`isTaxable: false`) ou à 0 $ → envoyer `taxes: []`
explicitement pour empêcher Gazelle de taxer.

IDs de référence (si besoin de calcul côté Python) :
```python
TPS : taxId="tax_JeCfY4wfbXtN6J28", rate=5000   → 5,000 %
TVQ : taxId="tax_xe9FEApq94zI7kXD", rate=9975   → 9,975 %
```

`build_item_input()` gère tout automatiquement (omit quand taxable, `[]` quand non).

### Montants et quantités

- `amount` en **cents** (45000 = 450,00 $)
- `quantity` en **centièmes** (100 = 1 unité)

### Nommage INPUT vs OUTPUT

- **Outputs** (query) : préfixe `all*` — `allEstimateTiers`, `allEstimateTierGroups`,
  `allEstimateTierItems`, `allUngroupedEstimateTierItems`
- **Inputs** (mutation) : sans préfixe — `estimateTiers`, `estimateTierGroups`,
  `estimateTierItems`, `ungroupedEstimateTierItems`

### Noms de champs piégeux

- `PrivateEstimateTierGroupInput.estimateTierItems` — **PAS `estimateItems`**
  (erreur réelle commise sur #11912)
- `PrivateEstimateTierInput` n'a **PAS de champ `name`** — utiliser `notes` pour libeller le tier
- `PrivateEstimateTierGroupInput` n'a **PAS de champ `notes`**

### mutationErrors

La réponse contient toujours `{ estimate, mutationErrors }`. Vérifier `mutationErrors`
même si HTTP 200. Utiliser `_raise_if_mutation_errors()` côté v6.

### Recherche par numéro

`PrivateAllEstimatesFilter` n'a PAS de champ `number`. Utiliser `search: "11914"`
puis filtrer côté Python sur `node.number == 11914`.

## Rendez-vous (Events)

### Modèle de données

- Le concept s'appelle `Event` (pas `Appointment`) : type APPOINTMENT, PERSONAL, MEMO, SYNCED
- **1 event = 1 technicien** : `PrivateEvent.user` = singulier `PrivateUser`
- `PrivateEventInput.userId` = singulier `String`
- Query : `allEventsBatched(first, after, filters: PrivateAllEventsFilter)`
- Mutation : `createEvent(input: PrivateEventInput!)`
- Pas de `PrivateUpdateEventInput` — pour modifier, probablement même mutation avec l'id
- Pas de `duplicateEvent` natif — cloner manuellement

### RV conjoint apprenti

Puisqu'un event ne supporte qu'un seul `userId`, un RV conjoint = 2 events séparés.
**Le clone doit être `type: PERSONAL`** (pas `APPOINTMENT`) pour éviter que le client
reçoive 2 avis de rendez-vous. Voir `workflows/clone_appointment_joint.md`.

## Clients et pianos

- `PrivateClient` a 45+ champs (introspection 2026-03-29)
- `PrivatePiano` a 46+ champs
- Langue client : `defaultClientLocalization { locale }` (fr_CA / en_US)
- Pianos d'institutions : attention à ne pas mélanger les lieux d'un même client
  (ex: Maison Symphonique vs Espace OSM sous le même client OSM)
