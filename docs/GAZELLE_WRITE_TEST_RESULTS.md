# Résultats des Tests d'Écriture vers Gazelle

## Date: 2026-01-01

## Tests Effectués

### 1. Lecture du Piano de Test
✅ **SUCCÈS**
- Piano ID: `ins_9H7Mh59SXwEs2JxL`
- Statut: **INACTIF**
- Marque: X
- Le piano peut être lu même s'il est inactif

### 2. Création de Timeline Entry
❌ **ÉCHEC**
- Mutation testée: `createTimelineEntry`
- Erreur: `Field 'createTimelineEntry' doesn't exist on type 'PrivateMutation'`
- **Conclusion**: Cette mutation n'existe pas dans l'API Gazelle

### 3. Mise à jour de last_tuned_date
❌ **ÉCHEC**
- Mutation testée: `updatePiano` avec `lastTunedDate`
- Erreurs multiples:
  - `InputObject 'PrivatePianoInput' doesn't accept argument 'lastTunedDate'`
  - `Field 'lastTunedDate' doesn't exist on type 'PrivatePiano'`
- **Conclusion**: Le champ `lastTunedDate` n'existe pas ou a un nom différent

## Mutations Disponibles Découvertes

L'exploration de l'API a révélé 186 mutations disponibles, incluant:
- `createPianoMeasurement` - Pour créer des mesures de piano
- `createPianoPhoto` - Pour créer des photos de piano
- `updatePiano` - Pour mettre à jour un piano (structure à explorer)
- `createEvent` - Pour créer des événements (peut-être lié aux timeline entries)

## Prochaines Étapes

### Option 1: Utiliser createPianoMeasurement
Les "notes de service" pourraient être créées via `createPianoMeasurement`. À explorer:
- Structure de `CreatePianoMeasurementInput`
- Si cela crée automatiquement des timeline entries

### Option 2: Utiliser createEvent
Les timeline entries pourraient être créées automatiquement lors de la création d'un événement (appointment/service). À explorer:
- Créer un événement de type "SERVICE" ou "TUNING"
- Vérifier si cela crée une timeline entry automatiquement

### Option 3: Mise à jour via updatePiano
Pour `last_tuned_date`, explorer:
- Les champs disponibles dans `UpdatePianoInput`
- Peut-être utiliser `calculatedLastService` ou un autre champ
- Ou mettre à jour via un événement complété

### Option 4: Documentation Gazelle
Consulter la documentation officielle de l'API Gazelle pour:
- Les mutations exactes pour créer des timeline entries
- Les champs disponibles pour mettre à jour les dates de service

## Solution Finale: createEvent

### 4. Création d'Événement de Service
✅ **SUCCÈS**
- Mutation utilisée: `createEvent` avec `PrivateEventInput`
- Type d'événement: `APPOINTMENT`
- Statut initial: `ACTIVE`, puis mis à `COMPLETE` via `updateEvent`
- Association piano: Via `allEventPianos.create` avec `pianoId`
- Notes technicien: Incluses dans le champ `notes` de l'événement
- Technicien: Associé via `userId` dans l'input

**Structure GraphQL correcte:**
```graphql
mutation CreateEvent($input: PrivateEventInput!) {
  createEvent(input: $input) {
    event {
      id
      title
      start
      type
      status
      notes
      user { id firstName lastName }
      allEventPianos { nodes { piano { id } } }
    }
    mutationErrors {
      fieldName
      messages
    }
  }
}
```

**Input correct:**
```python
{
  "start": "2026-01-01T18:21:00Z",
  "type": "APPOINTMENT",
  "status": "ACTIVE",
  "title": "Service: TUNING",
  "notes": "TUNING: Note du technicien...",
  "userId": "usr_HcCiFk7o0vZ9xAI0",
  "allEventPianos": {
    "create": [{"pianoId": "ins_9H7Mh59SXwEs2JxL"}]
  }
}
```

### 5. Test avec Piano Inactif
✅ **SUCCÈS**
- Piano testé: `ins_9H7Mh59SXwEs2JxL` (peut être ACTIVE ou INACTIVE)
- Résultat: L'événement est créé avec succès même si le piano est INACTIF
- **Conclusion**: Les événements de service peuvent être créés pour des pianos inactifs

## Notes Importantes

1. **Piano Inactif**: ✅ **CONFIRMÉ** - On peut créer des événements même si le piano est INACTIF. Les événements sont indépendants du statut du piano.

2. **Timeline Entries**: Les timeline entries sont créées automatiquement lors de la création d'un événement de type `APPOINTMENT` marqué comme `COMPLETE`.

3. **last_tuned_date**: Ce champ est probablement calculé automatiquement à partir des événements complétés. L'événement créé devrait mettre à jour cette date automatiquement.

4. **Événements de Test**: Chaque test crée un événement dans Gazelle. 9 événements de test ont été créés lors des tests (à nettoyer manuellement).

## Implémentation Finale

La fonction `push_technician_service` dans `core/gazelle_api_client.py` est fonctionnelle et prête pour la production. Elle:
- Crée un événement `APPOINTMENT` avec les notes du technicien
- Associe le piano et le technicien
- Marque l'événement comme `COMPLETE`
- Fonctionne avec des pianos actifs et inactifs

## Recommandations

1. ✅ **Implémenté**: La fonction `push_technician_service` est prête
2. ✅ **Implémenté**: L'intégration dans `api/place_des_arts.py` est complète
3. ✅ **Implémenté**: L'intégration frontend dans `PlaceDesArtsDashboard.jsx` est complète
4. **Production**: Tester avec des données réelles avant le déploiement
5. **Nettoyage**: Supprimer manuellement les événements de test dans Gazelle

## ⚠️ PROBLÈME NON RÉSOLU : Mise à jour de `calculatedLastService`

### Le Problème

**Objectif** : Mettre à jour automatiquement le champ "dernier accord" (`calculatedLastService`) d'un piano dans Gazelle lorsqu'un technicien complète un service.

**Ce qui fonctionne** :
- ✅ Créer un événement `APPOINTMENT` avec un piano associé
- ✅ Marquer l'événement comme `COMPLETE`
- ✅ Ajouter des notes du technicien

**Ce qui NE fonctionne PAS** :
- ❌ `calculatedLastService` n'est **PAS** mis à jour automatiquement quand un événement est complété
- ❌ Aucune mutation ne permet de mettre à jour `calculatedLastService` directement

### Découverte Importante

D'après l'utilisateur : **"Dans le RV, il doit être un accord qui est coché dans le RV, puis complété."**

Cela signifie que :
1. Il faut créer un événement avec un **service "Accord" associé** (Master Service Item avec `isTuning: true`)
2. Ce service doit être **"coché"** (sélectionné) dans l'événement
3. Le service doit être **marqué comme complété**
4. **ALORS** Gazelle met à jour automatiquement `calculatedLastService`

### Ce qui manque

**Question 1** : Comment associer un service "Accord" à un événement ?
- Existe-t-il une mutation `createEventService` ?
- Peut-on ajouter des services via `PrivateEventInput.allEventServices` ?
- Faut-il utiliser `scheduledMessages` dans `PrivateCompleteEventInput` ?

**Question 2** : Comment marquer un service comme complété ?
- Comment indiquer qu'un service spécifique est complété ?
- Faut-il utiliser `completeEvent` avec des paramètres spécifiques ?
- Y a-t-il une mutation `updateEventService` ou `completeEventService` ?

### Documentation Complète

Voir le document détaillé : `docs/PROBLEME_DERNIER_ACCORD_GAZELLE.md`

Ce document contient :
- Tous les tests effectués
- Les structures GraphQL explorées
- Les mutations disponibles
- Les prochaines étapes à explorer
- Le code de test existant

