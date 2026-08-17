# Workflow — Créer une fiche client + un rendez-vous depuis un appel téléphonique

**Déclencheurs** : « fais une fiche dans Gazelle », « place-moi un rendez-vous avec cette
personne », « nouveau client au téléphone », collage d'une transcription ou d'un résumé
d'appel entrant. Allan colle souvent le résumé d'appel généré par Zoom Phone.

Validé en prod le **2026-08-17** (client `cli_2BOIOLm6imhVO7Gs`, RV `evt_fU25flJJIWTJSYFO`,
memo `evt_NxMHlPZmSU0kYhnP`).

---

## Étape 0 — Extraire, et surtout lister ce qui manque

Une transcription d'appel est une source **bruitée**. Avant toute mutation, dresser deux
listes explicitement :

| À extraire | Trou fréquent |
|---|---|
| Prénom / nom | Noms épelés au téléphone → transcription fausse |
| Téléphone + type (HOME/MOBILE) | **Souvent absent du résumé** alors que c'est le seul canal |
| Courriel | Souvent « pas de courriel » |
| Adresse + municipalité + code postal | Code postal donné en fin d'appel |
| Marque / modèle du piano | Le client va « vérifier au sous-sol » et ne rappelle jamais |
| Prix annoncé de vive voix | À consigner : c'est un engagement verbal |
| Date + heure convenues | Vérifier que le jour de semaine correspond à la date |
| Provenance (« comment nous avez-vous trouvés ? ») | → champ `referredBy` |

**Règle absolue : ne jamais inventer une donnée manquante.** Créer la fiche avec ce qu'on
a, consigner le trou dans `preferenceNotes`, et **demander la donnée à Allan** dans la
réponse. Un numéro de téléphone inventé sur une fiche est pire qu'une fiche incomplète.

Piège de transcription vécu : « Lennox D. Dee ». Le « Dee » était vraisemblablement le
client qui **épelait son initiale** (« D comme dans Dee »), pas un nom de famille. Inscrire
`lastName: "D."` et poser la question, plutôt que de créer un « Dee » fantôme.

## Étape 1 — Chercher un doublon AVANT de créer

```graphql
query($s: String!) {
  allClients(filters: {search: $s}) {
    nodes {
      id companyName status
      defaultContact {
        firstName lastName
        defaultPhone { phoneNumber type }
        defaultLocation { street1 municipality region postalCode }
      }
    }
  }
}
```

Lancer sur le nom, **et sur la rue** (un client existant peut être fiché sous le nom du
conjoint). ⚠️ **`search` matche aussi les IDs** : une chaîne courte comme `"Dee"` remonte
`cli_K57R47uDEe38yN0W` et cinq autres faux positifs. Toujours vérifier le contenu des
nœuds, jamais se contenter du compte de résultats.

## Étape 2 — `createClient`

Le nom, le téléphone et l'adresse **ne sont pas des champs du client** : ils vivent dans
`contacts[] → phones[] / emails[] / locations[]`. Détail complet du schéma dans la mémoire
`reference_gazelle_create_client`.

```python
client_input = {
    "status": "ACTIVE",
    "referredBy": "Recherche web (trouvé PTM en ligne)",
    "preferenceNotes": (
        "AUCUN courriel, AUCUN cellulaire. Téléphone résidentiel seulement.\n"
        "=> Confirmer par téléphone la veille de chaque rendez-vous.\n"
        "Nom de famille à confirmer : entendu « Lennox D. Dee » au téléphone.\n"
        "Marque du piano non fournie."
    ),
    "contacts": [{
        "firstName": "Lennox",
        "lastName": "D.",
        "isDefault": True,
        "isBillingDefault": True,
        "wantsEmail": False,   # ← faux si pas de courriel : coupe les avis automatiques
        "wantsText": False,
        "wantsPhone": True,
        # "phones": [{"type": "HOME", "isDefault": True, "phoneNumber": "514 555 1234"}],
        "locations": [{
            "locationType": "ADDRESS",     # OBLIGATOIRE
            "usageType": "STREET",
            "street1": "25 Rockwood",
            "municipality": "Dollard-des-Ormeaux",
            "region": "QC",
            "postalCode": "H9A 2S3",
            "countryCode": "CA",
        }],
    }],
}
```

Sélection de retour : `PrivateClient` n'a **ni `name` ni `contacts`** — passer par
`defaultContact`. Une mauvaise sélection fait échouer la validation **avant** exécution,
donc aucune demi-fiche n'est créée. Vérifier `mutationErrors` même sur HTTP 200.

## Étape 3 — `createEvent` (le rendez-vous)

**Calquer le format des RV natifs** — relever un échantillon du mois courant avant
d'inventer quoi que ce soit :

```graphql
query($f: PrivateAllEventsFilter) {
  allEventsBatched(first: 25, filters: $f) {
    nodes { id title start duration type status travelMode
            user { id firstName lastName } client { id }
            location { locationType street1 municipality region postalCode } }
  }
}
```

Format PTM constaté (août 2026, ~25 RV) :

| Champ | Valeur | Note |
|---|---|---|
| `title` | le nom du client, rien de plus | pas de « Accord — » en préfixe |
| `duration` | **minutes** | 120 pour un accord résidentiel ; 80 Place des Arts ; 180 gros entretien |
| `type` | `APPOINTMENT` | |
| `travelMode` | `DRIVING` | présent sur tous |
| `userId` | un seul technicien | 1 event = 1 technicien |
| `location` | **absent** | PTM ne le met pas sur l'event ; l'adresse vient de la fiche client |
| `notes` | prix annoncé, marque inconnue, consignes d'appel | |

**Fuseau horaire** : `start` est en **UTC avec `Z`**. Convertir depuis `America/Montreal` —
EDT = UTC−4 (mars→nov), EST = UTC−5. Un RV à **10h00 le 28 août 2026** s'envoie
`"2026-08-28T14:00:00Z"`. Voir la convention timezone du `CLAUDE.md` racine.

**Vérifier le jour de semaine.** Allan dicte souvent « vendredi prochain le 28 » : confirmer
que le 28 est bien un vendredi, et le dire dans la réponse. Une date et un jour qui ne
concordent pas veut dire qu'on a mal entendu l'un des deux.

**Vérifier les conflits d'agenda** du technicien sur la journée (`startOn`/`endOn` au même
jour) et signaler tout chevauchement — y compris les blocs `PERSONAL` longs, faciles à
manquer : dans l'exemple, un bloc « Admin » de `duration: 2880` (48 h) couvrait le créneau.

## Étape 4 — Le rappel, si l'exécution dépend d'un humain qui s'en souvienne

Quand le plan comprend « appeler la veille pour confirmer », **en faire un event daté**, pas
une note. C'est la même règle que pour les sous-tâches fournisseurs : une étape qui vit
seulement dans la tête de quelqu'un ne survit pas.

```python
{"title": "Appeler Lennox D. pour confirmer le RV de demain 10h",
 "start": "2026-08-27T13:00:00Z", "duration": 15, "type": "MEMO",
 "userId": ALLAN, "notes": "... profiter de l'appel pour demander la MARQUE du piano."}
```

⚠️ Un event `type: MEMO` **ne conserve pas `clientId`** (retour `client: null` malgré un
`clientId` valide en entrée). Mettre tout le contexte utile dans `notes`.

## Étape 5 — Lecture-retour et rapport

Relire ce qui a été créé et le présenter à Allan en tableau (ID + détail lisible), puis
énumérer **séparément** :

1. ce qui a été créé,
2. les données manquantes qu'il doit fournir,
3. les points d'incertitude consignés dans la fiche plutôt que devinés,
4. les conflits d'agenda repérés.

Ne pas créer de fiche piano avec une marque inventée ou « inconnu » : poser la question.

## Effets de bord à connaître

- `wantsEmail: False` + aucun courriel ⇒ créer l'`APPOINTMENT` **n'envoie aucun avis** au
  client. C'est voulu ici, mais ça signifie que l'appel de confirmation est le seul canal.
- Le miroir Supabase (`gazelle_clients` / `gazelle_contacts` / `gazelle_pianos`) ne se met à
  jour qu'au **sync nocturne** (GitHub Actions). La fiche n'apparaît pas immédiatement dans
  l'assistant : patcher le miroir ou déclencher un sync si Allan la cherche tout de suite.
- `PrivateUser` n'a **pas de champ `name`** — demander `firstName` / `lastName`.

## Checklist

- [ ] Trous de données listés, aucun inventé
- [ ] Recherche de doublon lancée sur le nom **et** la rue, faux positifs d'ID écartés
- [ ] `wantsEmail` / `wantsText` cohérents avec ce que le client a dit
- [ ] `referredBy` rempli si la provenance a été dite
- [ ] Date ↔ jour de semaine vérifiés
- [ ] Heure convertie America/Montreal → UTC
- [ ] `duration` en minutes, calquée sur les RV natifs
- [ ] Conflits d'agenda du technicien vérifiés et signalés
- [ ] Memo de rappel créé si un appel de confirmation est prévu
- [ ] `mutationErrors` vérifiés sur chaque mutation
- [ ] Lecture-retour faite, données manquantes demandées à Allan
