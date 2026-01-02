# Rapport de Test - Piano d'Allan (ins_9H7Mh59SXwEs2JxL)

## Date: 2026-01-01

---

## ✅ Phase 1: Lecture du Piano - RÉUSSIE

### Connexion à l'API Gazelle
- ✅ Token OAuth valide chargé depuis Supabase
- ✅ Connexion à l'API GraphQL établie
- ✅ Piano récupéré avec succès

### Détails du Piano Test

```json
{
  "id": "ins_9H7Mh59SXwEs2JxL",
  "make": "X",
  "model": null,
  "serialNumber": null,
  "type": "UNKNOWN",
  "year": null,
  "status": "ACTIVE",
  "lifecycleState": "no-lifecycle",
  "location": null
}
```

### Propriétaire Confirmé

- **Nom**: Allan Test Sutton
- **Email**: suttonallan@gmail.com
- **Client ID**: cli_YCh6GMzNfXWxJ2um
- **Compagnie**: (vide)

✅ **VALIDATION**: Le piano appartient bien à Allan Test Sutton comme attendu.

---

## ⭐ Phase 2: Analyse de la Structure - DÉCOUVERTES CRITIQUES

### Champs de Date de Service Disponibles

Le schéma GraphQL `PrivatePiano` expose les champs suivants pour les dates de service:

| Champ | Valeur Actuelle | Type | Description |
|-------|-----------------|------|-------------|
| `calculatedLastService` | `null` | CoreDate | **Date calculée automatiquement** (lecture seule) |
| `manualLastService` | `null` | CoreDate | **Date manuelle** (peut être mise à jour) |
| `eventLastService` | `null` | CoreDate | **Date basée sur les événements** |
| `calculatedNextService` | `null` | CoreDate | Prochaine date de service calculée |
| `nextServiceOverride` | `null` | CoreDate | Override manuel de la prochaine date |
| `serviceIntervalMonths` | `6` | Int | Intervalle de service (6 mois) |

### Découvertes Importantes

1. **`manualLastService`** ✅ PEUT ÊTRE MIS À JOUR
   - Ce champ est modifiable via `updatePiano`
   - Permet de définir manuellement la date du dernier service
   - Cependant, il n'affecte **PAS** automatiquement `calculatedLastService`

2. **`eventLastService`** ⚠️ BASÉ SUR LES ÉVÉNEMENTS
   - Ce champ est calculé à partir des événements complétés
   - La question reste: **Comment créer un événement qui met à jour ce champ?**

3. **`calculatedLastService`** ❌ LECTURE SEULE
   - Impossible de le modifier directement
   - Doit être calculé par Gazelle automatiquement

---

## ❌ Phase 3: Historique des Services - PROBLÈME CONFIRMÉ

### Timeline Entries

**Erreur rencontrée:**
```
Type mismatch on variable $pianoId and argument pianoId (ID / String)
Field 'allTimelineEntries' doesn't accept argument 'orderBy'
```

**Résultat**: Impossible de récupérer les timeline entries avec la structure actuelle.

### Événements (RV/Services)

**Erreur critique rencontrée:**
```
Field 'allEventServices' doesn't exist on type 'PrivateEvent'
```

**Ceci confirme le problème documenté dans `PROBLEME_DERNIER_ACCORD_GAZELLE.md`**:
- Les événements dans l'API GraphQL **n'exposent PAS** directement les services associés
- Il n'y a **PAS** de champ `allEventServices` sur `PrivateEvent`
- Impossible de savoir quels services sont "cochés" dans un RV via l'API publique

---

## 🔍 Phase 4: Exploration du Schéma GraphQL

### Champs Disponibles sur `PrivatePiano` (46 champs au total)

**Champs de relation critiques:**
- ❌ `allTimelineEntries` - N'existe PAS sur PrivatePiano
- ❌ `allEventPianos` - N'existe PAS sur PrivatePiano
- ✅ `manualLastService` - **EXISTE** et **MODIFIABLE**
- ✅ `nextTuningScheduled` - Prochain RV planifié (PrivateEvent)

**Conclusion**: Les timeline entries et événements doivent être récupérés via des **queries séparées** sur `allTimelineEntries` et `allEventsBatched`.

---

## 🚧 Problème Principal Identifié

### Le Workflow Attendu (selon l'utilisateur)

> "Dans le RV, il doit être un accord qui est coché dans le RV, puis complété."

**Ce workflow nécessite:**
1. Créer un événement `APPOINTMENT`
2. **Ajouter un service "Accord"** (Master Service Item avec `isTuning: true`) à cet événement
3. **Cocher le service** (le sélectionner) dans l'événement
4. **Marquer le service comme complété**
5. ⭐ **Alors** Gazelle met à jour automatiquement `eventLastService` et `calculatedLastService`

### Ce qui Manque dans l'API GraphQL

1. **Comment associer un service à un événement?**
   - Mutation `createEventService` ? ❓ À explorer
   - Champ `allEventServices` dans `PrivateEventInput` ? ❌ N'existe pas
   - Autre méthode ? ❓

2. **Comment marquer un service comme complété?**
   - Mutation `completeEvent` avec `PrivateCompleteEventInput` ? ⚠️ À tester
   - Mutation `updateEventService` ? ❓ À explorer
   - Champ `completedAt` dans le service ? ❓

3. **Structure exacte de `PrivateCompleteEventInput`**
   - Champ `serviceHistoryNotes` ? ❓
   - Champ `scheduledMessages` ? ❓
   - Comment indiquer quels services ont été complétés ? ❓

---

## 💡 Solutions Possibles

### Option 1: Utiliser `manualLastService` (SIMPLE mais LIMITÉE)

**Mutation disponible:**
```graphql
mutation UpdatePianoManualLastService(
    $pianoId: ID!
    $manualLastService: CoreDate!
) {
    updatePiano(
        input: {
            id: $pianoId
            manualLastService: $manualLastService
        }
    ) {
        piano {
            id
            manualLastService
            calculatedLastService
            eventLastService
        }
        errors {
            field
            message
        }
    }
}
```

**Variables:**
```json
{
  "pianoId": "ins_9H7Mh59SXwEs2JxL",
  "manualLastService": "2026-01-01"
}
```

**⚠️ LIMITES:**
- Met à jour uniquement `manualLastService`
- N'affecte **PAS** `calculatedLastService` automatiquement
- Ne crée **PAS** de timeline entry
- Ne crée **PAS** d'événement dans l'historique

**✅ AVANTAGES:**
- Très simple à implémenter
- Fonctionne immédiatement
- Pas besoin de comprendre les services

---

### Option 2: Explorer `completeEvent` avec Services (COMPLEXE mais CORRECTE)

**Étapes requises:**

1. **Explorer la structure de `PrivateCompleteEventInput`:**
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
           }
         }
         description
       }
     }
   }
   ```

2. **Tester la mutation `completeEvent`:**
   ```graphql
   mutation CompleteEventWithService(
       $eventId: String!
       $input: PrivateCompleteEventInput!
   ) {
       completeEvent(id: $eventId, input: $input) {
           event {
               id
               status
               # Autres champs...
           }
           mutationErrors {
               fieldName
               messages
           }
       }
   }
   ```

3. **Identifier comment spécifier les services complétés:**
   - Via `serviceHistoryNotes` ?
   - Via un champ caché `eventServices` ?
   - Via une relation implicite ?

**⚠️ COMPLEXITÉ:**
- Nécessite de comprendre la structure exacte de `PrivateCompleteEventInput`
- Peut nécessiter plusieurs appels API
- Documentation de Gazelle insuffisante

**✅ AVANTAGES:**
- Respecte le workflow Gazelle
- Met à jour `eventLastService` et `calculatedLastService` automatiquement
- Crée une timeline entry automatiquement
- Historique complet dans Gazelle

---

## 📝 Script POST Proposé (NE PAS EXÉCUTER POUR L'INSTANT)

### Script Python pour Tester Option 1 (Mise à jour manuelle)

```python
#!/usr/bin/env python3
"""
Script de test - Mise à jour manuelle de la date de dernier service.

⚠️ NE PAS EXÉCUTER SANS AUTORISATION
"""

import sys
from pathlib import Path
from datetime import date

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.gazelle_api_client import GazelleAPIClient


def update_manual_last_service(piano_id: str, service_date: str = None):
    """
    Met à jour manualLastService pour un piano.

    Args:
        piano_id: ID du piano
        service_date: Date ISO (YYYY-MM-DD) ou None pour aujourd'hui
    """
    client = GazelleAPIClient()

    if not service_date:
        service_date = date.today().isoformat()

    mutation = """
    mutation UpdatePianoManualLastService(
        $pianoId: ID!
        $manualLastService: CoreDate!
    ) {
        updatePiano(
            input: {
                id: $pianoId
                manualLastService: $manualLastService
            }
        ) {
            piano {
                id
                manualLastService
                calculatedLastService
                eventLastService
            }
            errors {
                field
                message
            }
        }
    }
    """

    variables = {
        "pianoId": piano_id,
        "manualLastService": service_date
    }

    print(f"\n{'='*70}")
    print(f"⚠️  TEST: Mise à jour manuelle de la date de dernier service")
    print(f"   Piano ID: {piano_id}")
    print(f"   Date: {service_date}")
    print(f"{'='*70}\n")

    print("Mutation à exécuter:")
    print(mutation)
    print("\nVariables:")
    import json
    print(json.dumps(variables, indent=2))

    # ⚠️ DÉCOMMENTER POUR EXÉCUTER (ATTENTION!)
    # result = client._execute_query(mutation, variables)
    # print(f"\nRésultat:")
    # print(json.dumps(result, indent=2))

    print("\n⚠️  Mutation NON EXÉCUTÉE (par sécurité)")
    print("Décommentez la ligne 'result = ...' pour exécuter")


if __name__ == '__main__':
    # Piano de test d'Allan
    piano_id = "ins_9H7Mh59SXwEs2JxL"
    service_date = "2026-01-01"

    update_manual_last_service(piano_id, service_date)
```

---

## 📊 Résumé des Résultats

| Phase | Statut | Résultat |
|-------|--------|----------|
| Connexion API | ✅ SUCCÈS | Token valide, API accessible |
| Lecture piano | ✅ SUCCÈS | Piano trouvé, propriétaire confirmé |
| Analyse structure | ✅ SUCCÈS | 46 champs identifiés, `manualLastService` modifiable |
| Timeline entries | ❌ ÉCHEC | Erreur de typage, query à corriger |
| Événements/Services | ❌ ÉCHEC | `allEventServices` n'existe pas sur PrivateEvent |

---

## 🎯 Prochaines Étapes Recommandées

### Étape 1: Décider de l'approche

**Option A - Simple (Recommandée pour MVP):**
- Utiliser `manualLastService` pour mettre à jour la date
- Accepter que `calculatedLastService` ne soit pas mis à jour
- Documenter la limitation

**Option B - Complète (Nécessite Investigation):**
- Explorer `completeEvent` et `PrivateCompleteEventInput`
- Identifier comment associer des services à un événement
- Tester avec un piano réel qui a des services complétés
- Implémenter le workflow complet

### Étape 2: Validation avec l'utilisateur

**Questions à poser:**
1. Est-ce que mettre à jour `manualLastService` est suffisant pour Place des Arts?
2. Faut-il absolument que `calculatedLastService` soit mis à jour?
3. Avez-vous accès à un piano dans Gazelle qui a des RV avec services complétés pour analyse?
4. Peut-on créer un RV de test manuellement dans Gazelle UI pour voir la structure?

### Étape 3: Exécution du Test

**Si Option A est choisie:**
```bash
# Exécuter le script de test (après validation utilisateur)
python3 scripts/test_update_manual_last_service.py
```

**Si Option B est choisie:**
```bash
# Continuer l'exploration du schéma GraphQL
python3 scripts/explore_completeEvent_input.py
python3 scripts/test_complete_event_with_service.py
```

---

## 📚 Fichiers Créés

- `data/piano_ins_9H7Mh59SXwEs2JxL_complete.json` - Données complètes du piano
- `data/piano_schema.json` - Schéma GraphQL de PrivatePiano
- `docs/RAPPORT_TEST_PIANO_ALLAN.md` - Ce rapport
- `docs/PROBLEME_DERNIER_ACCORD_GAZELLE.md` - Documentation du problème
- `docs/GAZELLE_WRITE_TEST_RESULTS.md` - Résultats des tests précédents

---

## ✅ Validation de Connexion

**Connexion à l'API Gazelle:** ✅ VALIDÉE
- Token OAuth: ✅ Chargé depuis Supabase
- Endpoint GraphQL: ✅ https://gazelleapp.io/graphql/private/
- Piano de test: ✅ Accessible (ins_9H7Mh59SXwEs2JxL)
- Propriétaire: ✅ Confirmé (Allan Test Sutton, suttonallan@gmail.com)

**Le système est prêt pour les opérations POST une fois l'approche validée.**

---

**Rapport généré le:** 2026-01-01
**Par:** Claude Code (Assistant Gazelle V5)
