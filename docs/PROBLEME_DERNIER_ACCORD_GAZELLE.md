# Problème : Mise à jour de la date de dernier accord dans Gazelle

## Contexte

L'objectif est de mettre à jour automatiquement le champ "dernier accord" (`calculatedLastService`) d'un piano dans Gazelle lorsqu'un technicien complète un service d'accord via l'application Place des Arts.

## Problème Identifié

### Ce qui ne fonctionne PAS

1. **Mutation `updatePiano` avec `lastTunedDate`**
   - ❌ Le champ `lastTunedDate` n'existe pas dans `PrivatePianoInput`
   - ❌ Erreur : `InputObject 'PrivatePianoInput' doesn't accept argument 'lastTunedDate'`
   - ❌ Le champ `calculatedLastService` est en lecture seule (calculé automatiquement)

2. **Mutation `createTimelineEntry`**
   - ❌ Cette mutation n'existe pas dans l'API Gazelle
   - ❌ Erreur : `Field 'createTimelineEntry' doesn't exist on type 'PrivateMutation'`

3. **Mise à jour directe du champ**
   - ❌ `calculatedLastService` est un champ calculé, pas modifiable directement
   - ❌ Aucune mutation ne permet de le mettre à jour manuellement

### Ce qui fonctionne PARTIELLEMENT

1. **Création d'un événement `APPOINTMENT`**
   - ✅ On peut créer un événement avec `createEvent`
   - ✅ On peut associer un piano via `pianos: [{"pianoId": piano_id}]`
   - ✅ On peut marquer l'événement comme `COMPLETE` via `updateEvent`
   - ⚠️ **MAIS** : `calculatedLastService` n'est PAS mis à jour automatiquement

## Découverte Importante

D'après les tests et les informations de l'utilisateur :

> "Dans le RV, il doit être un accord qui est coché dans le RV, puis complété."

**Cela signifie que :**
- Il faut créer un événement (RV) avec un **service "Accord" associé**
- Ce service doit être **"coché"** (sélectionné) dans l'événement
- Le service doit être **marqué comme complété**
- **ALORS** Gazelle met à jour automatiquement `calculatedLastService`

## Structure GraphQL Explorée

### Événements avec Services

Les événements dans Gazelle ont une structure `allEventServices` qui contient :
- `masterServiceItem` : Le service (ex: "Accord" avec `isTuning: true`)
- `status` : Statut du service
- `completedAt` : Date de complétion

### Mutations Disponibles

1. **`createEvent`** : Crée un événement
   - Input : `PrivateEventInput`
   - ❌ Ne contient PAS de champ pour associer des services directement

2. **`completeEvent`** : Marque un événement comme complété
   - Input : `PrivateCompleteEventInput`
   - Contient : `serviceHistoryNotes`, `scheduledMessages`, etc.
   - ⚠️ Structure exacte à explorer

3. **`updateEvent`** : Met à jour un événement
   - Input : `PrivateEventInput`
   - ❌ Ne semble pas permettre d'ajouter des services

## Ce qui manque

### 1. Comment associer un service "Accord" à un événement ?

**Questions à résoudre :**
- Existe-t-il une mutation `createEventService` ?
- Peut-on ajouter des services via `PrivateEventInput.allEventServices` ?
- Faut-il utiliser `scheduledMessages` dans `PrivateCompleteEventInput` ?

### 2. Comment marquer un service comme complété ?

**Questions à résoudre :**
- Comment indiquer qu'un service spécifique est complété ?
- Faut-il utiliser `completeEvent` avec des paramètres spécifiques ?
- Y a-t-il une mutation `updateEventService` ou `completeEventService` ?

### 3. Structure exacte des données

**À explorer :**
- Structure de `PrivateCompleteEventInput.serviceHistoryNotes`
- Structure de `PrivateCompleteEventInput.scheduledMessages`
- Comment les services sont stockés dans un événement

## Tests Effectués

### Test 1 : Créer un événement et le marquer COMPLETE
```python
# ✅ Événement créé avec succès
# ✅ Piano associé avec succès
# ✅ Événement marqué COMPLETE
# ❌ calculatedLastService n'a PAS été mis à jour
```

### Test 2 : Explorer la structure des événements
```python
# ✅ Trouvé : allEventServices existe dans les événements
# ❌ Mais : Ne peut pas être ajouté via createEvent
# ❓ À explorer : Comment ajouter des services après création ?
```

### Test 3 : Explorer les mutations disponibles
```python
# ✅ Trouvé : completeEvent existe
# ✅ Trouvé : PrivateCompleteEventInput contient serviceHistoryNotes
# ❓ À explorer : Comment utiliser ces champs pour les services ?
```

## Services "Accord" Disponibles

Les services d'accord sont dans `allMasterServiceItems` avec `isTuning: true` :
- ID exemple : `mit_GL9kL9FS1mHifXY3`
- Nom : "Accord 440Hz. Nettoyage sommaire..."
- `isTuning: true`

## Prochaines Étapes pour Claude (Code)

### 1. Explorer la structure complète de `PrivateCompleteEventInput`

```graphql
query {
  __type(name: "PrivateCompleteEventInput") {
    inputFields {
      name
      type {
        name
        kind
        ofType {
          name
          kind
          inputFields {
            name
            type {
              name
            }
          }
        }
      }
      description
    }
  }
}
```

### 2. Explorer comment ajouter des services à un événement

- Chercher une mutation `createEventService` ou similaire
- Explorer si `updateEvent` peut ajouter des services via `allEventServices`
- Tester `completeEvent` avec différents paramètres

### 3. Tester le workflow complet

1. Créer un événement `APPOINTMENT` avec un piano
2. Ajouter un service "Accord" à cet événement
3. Marquer le service comme complété
4. Vérifier si `calculatedLastService` est mis à jour

### 4. Explorer les événements existants avec services

- Récupérer un événement réel qui a un service "Accord" complété
- Analyser sa structure complète
- Comprendre comment les services sont stockés

## Code de Test Existant

Les scripts de test sont dans :
- `scripts/test_push_technician_service.py` : Test de création d'événement
- `scripts/test_last_tuned_update.py` : Test de mise à jour calculatedLastService
- `scripts/explore_event_services.py` : Exploration de la structure des services
- `scripts/explore_completeEvent.py` : Exploration de completeEvent

## Conclusion

Le problème principal est que **nous ne savons pas comment associer un service "Accord" à un événement et le marquer comme complété** via l'API GraphQL de Gazelle.

Une fois cette étape résolue, Gazelle devrait mettre à jour automatiquement `calculatedLastService` quand un service d'accord est complété dans un événement.




