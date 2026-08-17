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

⚠️ **CORRECTION 2026-08-10 (vérifiée empiriquement sur #11983).** L'ancien
conseil ci-dessous (« omettre `taxes` → Gazelle applique auto ») donne en fait
**0 $ de taxe** quand on crée via `createEstimate` + `updateEstimate`. Testé
dans les deux sens sur #11983 :
- `taxes` **omis** sur items taxables → `taxTotal = 0` (aucune taxe).
- `taxes` **explicites** (TPS+TVQ) via `updateEstimate` → taxes correctes.

**Règle qui MARCHE (create/update par API) :** envoyer les taxes explicitement
sur chaque item taxable, **avec le champ `name`**, ET créer en 2 étapes
(createEstimate minimal → updateEstimate avec les tiers) :
```python
TPS: taxId="tax_JeCfY4wfbXtN6J28", name="tps", rate=5000 -> total=round(amount*5000/100000)
TVQ: taxId="tax_xe9FEApq94zI7kXD", name="tvq", rate=9975 -> total=round(amount*9975/100000)
```
⚠️ **Le `name` ("tps"/"tvq") est OBLIGATOIRE.** Sans lui, Gazelle jette les
lignes de taxe par item : le total se calcule mais les **cases TPS/TVQ restent
DÉCOCHÉES** dans l'UI (constaté sur #11983, 2026-08-10). Vérifier via le champ
`taxes { name rate total }` de chaque item — il doit être rempli comme sur une
soumission native (#11766). Items NON taxables ou à 0 $ → `taxes: []`.
Implémenté dans `api/assistant_duplication.py` (`_build_taxes`).

---
_Ancienne note (2026-04-12, gardée pour trace — peut valoir pour le chemin v6
`build_item_input`, mais PAS pour createEstimate+updateEstimate) :_ pour les
items taxables, ne pas envoyer `taxes` (Gazelle auto-applique, checkboxes
cochées) ; un bloc explicite créait un override désactivant les checkboxes auto
(#11915/#11916).

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
- Mutation création : `createEvent(input: PrivateEventInput!)`
- Mutation modification : **`updateEvent(id: String!, input: PrivateEventInput!)`** — CONFIRMÉ en prod
  le 2026-08-03 (déplacement d'un RV 9h→8h30). Il n'y a PAS de `PrivateUpdateEventInput` :
  on réutilise `PrivateEventInput`. ⚠️ L'input REMPLACE l'event : re-passer explicitement
  `title/start/duration/type/userId/notes` (et tout champ à garder), sinon ils sont écrasés/nullés.
- Pas de `duplicateEvent` natif — cloner manuellement

### Champ `location` (lieu d'un event)

Input : `PrivateEventLocationInput` (via `PrivateEventInput.location`). Champs utiles :
`locationType` (enum), `street1`, `street2`, `municipality`, `region`, `postalCode`,
`countryCode`, `singleLineAddress`, `latitude`, `longitude`, `what3words`.

- **`locationType` est OBLIGATOIRE** dès qu'on envoie un `location`, sinon
  mutationError `{ fieldName: "eventLocation", messages: ["Location type is not a valid type"] }`.
  Enum `EventLocationType` = `ADDRESS | COORDINATES | WHAT3WORDS | SINGLE_LINE_ADDRESS`.
  Pour une adresse civique postale → `ADDRESS`.
- **Output** (`PrivateEventLocation`) : les champs sont `street1/street2/municipality/region/postalCode`
  — PAS `name/street/city` (erreurs `undefinedField` si on les demande).
- Gazelle géocode et applique une casse d'affichage (title-case) à l'adresse retournée ;
  les données envoyées restent correctes.
- L'UTF-8 passe : envoyer les accents (`Montréal`, `entrées`), ne pas les retirer.

### Durées et format natif PTM (relevé 2026-08-17, ~25 RV d'août)

`duration` est en **minutes** (pas en secondes). Valeurs réellement utilisées :
`120` accord résidentiel · `80` Place des Arts · `180` gros entretien · `420` journée.
`travelMode: DRIVING` est présent sur tous les RV. Le `title` est **le nom du client**,
sans préfixe de service.

**PTM ne met PAS de `location` sur les events** : le champ ressort `null` sur tous les RV
natifs — l'adresse vient de la fiche client. N'en envoyer un que si le lieu diffère de
l'adresse du client.

`start` est en **UTC avec `Z`**. Convertir depuis `America/Montreal` : EDT = UTC−4
(mars→nov), EST = UTC−5. Ex. 10h00 le 2026-08-28 → `"2026-08-28T14:00:00Z"`.

### Events de type MEMO

Un `createEvent` avec `type: MEMO` **ne conserve pas `clientId`** : le retour donne
`client: null` même avec un `clientId` valide en entrée (vérifié 2026-08-17 sur
`evt_NxMHlPZmSU0kYhnP`). Mettre tout le contexte dans `notes`.

### Blocs PERSONAL longs = faux « créneau libre »

Chercher les conflits d'agenda sans regarder les `PERSONAL` fait manquer des blocs de
plusieurs jours : un « Admin » à `duration: 2880` (48 h) couvrait le créneau visé le
2026-08-28. Interroger `allEventsBatched` **sans filtre `type`** pour la journée visée.

### PrivateUser

Pas de champ `name` → demander `firstName` / `lastName` (erreur `undefinedField` sinon).

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

### Recherche de client : `search` matche aussi les IDs

`allClients(filters: {search: "Dee"})` remonte `cli_K57R47uDEe38yN0W` et cinq autres
clients sans rapport, parce que le terme apparaît dans l'**ID**. Sur une chaîne courte,
toujours inspecter le contenu des nœuds — jamais conclure sur le nombre de résultats.
Pour une recherche de doublon, lancer sur le nom **et** sur la rue.

### createClient : la validation protège des demi-fiches

Une sélection de retour invalide (`name`, `contacts`, `firstName` sur `PrivateClient`)
fait échouer la requête **avant** exécution — rien n'est créé. Passer par
`defaultContact { firstName lastName defaultPhone { phoneNumber type } defaultLocation {...} }`.
Recette complète : `workflows/create_client_and_appointment.md`.
