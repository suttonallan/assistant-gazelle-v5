# ✅ Résultat du Test avec l'API Gazelle

**Date:** 2026-01-01
**Piano testé:** `ins_9H7Mh59SXwEs2JxL` (Allan Test Sutton)
**Objectif:** Lire le piano, analyser sa structure, et préparer un script POST

---

## 📖 Phase de Lecture - RÉUSSIE ✅

### Connexion à l'API

- ✅ **Token OAuth** chargé depuis Supabase `system_settings`
- ✅ **API GraphQL** accessible à `https://gazelleapp.io/graphql/private/`
- ✅ **Piano récupéré** avec tous les champs disponibles

### Détails du Piano

| Champ | Valeur |
|-------|--------|
| **ID** | `ins_9H7Mh59SXwEs2JxL` |
| **Marque** | X |
| **Modèle** | null |
| **Type** | UNKNOWN |
| **Statut** | ACTIVE ✅ |
| **Propriétaire** | Allan Test Sutton ✅ |
| **Email** | suttonallan@gmail.com ✅ |
| **Client ID** | `cli_YCh6GMzNfXWxJ2um` |

**✅ VALIDATION:** Le piano appartient bien à Allan Test Sutton comme indiqué.

---

## 🔍 Analyse de Structure - DÉCOUVERTES IMPORTANTES

### Champs de Date de Service Disponibles

Le piano expose **5 champs** liés aux dates de service:

| Champ | Valeur Actuelle | Modifiable? | Description |
|-------|-----------------|-------------|-------------|
| `manualLastService` | `null` | ✅ **OUI** | Date manuelle (peut être définie via `updatePiano`) |
| `calculatedLastService` | `null` | ❌ **NON** | Date calculée automatiquement (lecture seule) |
| `eventLastService` | `null` | ❌ **NON** | Date basée sur les événements complétés |
| `calculatedNextService` | `null` | ❌ **NON** | Prochaine date de service calculée |
| `nextServiceOverride` | `null` | ⚠️ **?** | Override manuel de la prochaine date |

### Découverte Critique

Le schéma GraphQL de `PrivatePiano` contient **46 champs** au total, mais:

- ❌ **PAS de champ `allTimelineEntries`** directement sur le piano
- ❌ **PAS de champ `allEventPianos`** directement sur le piano
- ❌ **PAS de champ `allEventServices`** sur les événements

**Conclusion:** L'historique des services et les événements doivent être récupérés via des **queries séparées**, et la structure exacte des services dans les événements n'est **PAS exposée** publiquement via l'API GraphQL.

---

## ⚠️ Problème Identifié: Services dans les Événements

### Erreur rencontrée

Lors de la tentative de récupération des événements avec leurs services:

```
Field 'allEventServices' doesn't exist on type 'PrivateEvent'
```

**Ceci confirme le problème documenté:**

> Les événements dans l'API GraphQL **n'exposent PAS** le champ `allEventServices` permettant de voir quels services sont "cochés" et complétés.

### Implications

D'après l'utilisateur:
> "Dans le RV, il doit être un accord qui est coché dans le RV, puis complété."

**Ce workflow nécessite:**
1. Créer un événement `APPOINTMENT`
2. Ajouter un service "Accord" (Master Service Item avec `isTuning: true`)
3. Cocher le service (le sélectionner)
4. Marquer le service comme complété
5. ⭐ **Alors** Gazelle met à jour `eventLastService` et `calculatedLastService`

**Mais actuellement:**
- ❌ Impossible de voir les services via l'API
- ❌ Impossible de savoir comment ajouter/cocher un service
- ❌ Impossible de vérifier si un service est complété

**Voir la documentation complète du problème:** [`docs/PROBLEME_DERNIER_ACCORD_GAZELLE.md`](./PROBLEME_DERNIER_ACCORD_GAZELLE.md)

---

## 💡 Solution Proposée: Option Simple (Option A)

Étant donné que le workflow complet avec services n'est pas accessible, voici la **solution de contournement**:

### Utiliser `manualLastService`

Au lieu de créer un événement avec un service coché et complété, **mettre à jour directement** le champ `manualLastService` via la mutation `updatePiano`.

**Avantages:**
- ✅ **Simple** à implémenter
- ✅ **Fonctionne immédiatement** (mutation disponible)
- ✅ **Pas besoin** de comprendre la structure des services
- ✅ **Visible dans Gazelle** (champ affiché dans l'interface)

**Limites:**
- ⚠️ Ne met **PAS** à jour `calculatedLastService` automatiquement
- ⚠️ Ne crée **PAS** de timeline entry
- ⚠️ Ne crée **PAS** d'événement dans l'historique
- ⚠️ Ne respecte **PAS** le workflow Gazelle complet

---

## 📝 Script POST Proposé (NON EXÉCUTÉ)

### Mutation GraphQL

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
            calculatedNextService
        }
        errors {
            field
            message
        }
    }
}
```

### Variables

```json
{
  "pianoId": "ins_9H7Mh59SXwEs2JxL",
  "manualLastService": "2026-01-01"
}
```

### Script Python

Un script de test est disponible: **`scripts/test_update_manual_last_service.py`**

**Utilisation (mode dry-run, sans exécution):**
```bash
python3 scripts/test_update_manual_last_service.py
```

**Utilisation (exécution réelle):**
```bash
python3 scripts/test_update_manual_last_service.py --execute
```

**⚠️ IMPORTANT:** Le script demande une confirmation avant d'exécuter la mutation pour éviter les modifications accidentelles.

---

## 📊 Résumé des Résultats

| Phase | Statut | Détails |
|-------|--------|---------|
| **Connexion API** | ✅ **SUCCÈS** | Token valide, piano accessible |
| **Lecture piano** | ✅ **SUCCÈS** | Tous les champs récupérés |
| **Propriétaire** | ✅ **VALIDÉ** | Allan Test Sutton confirmé |
| **Champs modifiables** | ✅ **IDENTIFIÉS** | `manualLastService` peut être mis à jour |
| **Historique services** | ❌ **LIMITÉ** | `allEventServices` n'existe pas |
| **Script POST** | ✅ **PRÉPARÉ** | Mutation prête, NON exécutée |

---

## 🎯 Prochaines Étapes - ATTENTE SIGNAL UTILISATEUR

### Option A: Approche Simple (Recommandée pour MVP)

**Si cette approche est acceptable:**

1. ✅ **Le script est prêt** (`scripts/test_update_manual_last_service.py`)
2. ⏸️ **En attente du signal utilisateur** pour l'exécution
3. 📋 **Mode dry-run testé** avec succès

**Commande à exécuter (après validation):**
```bash
python3 scripts/test_update_manual_last_service.py --execute
```

---

### Option B: Approche Complète (Nécessite Investigation)

**Si l'approche simple n'est pas suffisante:**

**Étapes suivantes:**

1. **Explorer `PrivateCompleteEventInput`:**
   - Créer un script d'introspection pour voir tous les champs
   - Identifier si un champ permet de spécifier les services complétés

2. **Tester avec un piano réel:**
   - Trouver un piano dans Gazelle qui a des RV avec services complétés
   - Récupérer sa structure pour voir comment les services sont stockés

3. **Créer un RV de test manuellement dans Gazelle UI:**
   - Créer un événement avec un service d'accord
   - Le marquer comme complété
   - Analyser via l'API comment cela apparaît

4. **Contacter le support Gazelle:**
   - Demander la documentation officielle sur `completeEvent`
   - Demander comment associer des services à un événement via l'API

**Temps estimé:** Plusieurs heures à plusieurs jours selon la complexité

---

## 📚 Fichiers Créés

| Fichier | Description |
|---------|-------------|
| `docs/RAPPORT_TEST_PIANO_ALLAN.md` | Rapport technique détaillé |
| `docs/RESULTAT_TEST_API_GAZELLE.md` | Ce document (résumé) |
| `docs/PROBLEME_DERNIER_ACCORD_GAZELLE.md` | Documentation du problème avec services |
| `scripts/test_update_manual_last_service.py` | Script POST proposé (non exécuté) |
| `scripts/read_piano_with_history.py` | Script de lecture complète |
| `scripts/explore_piano_schema.py` | Script d'exploration du schéma |
| `data/piano_ins_9H7Mh59SXwEs2JxL_complete.json` | Données du piano (JSON) |
| `data/piano_schema.json` | Schéma GraphQL complet de PrivatePiano |

---

## ✅ Validation Finale

### Connexion API Gazelle
- ✅ **Token OAuth:** Chargé depuis Supabase
- ✅ **Endpoint GraphQL:** `https://gazelleapp.io/graphql/private/`
- ✅ **Piano de test:** Accessible (`ins_9H7Mh59SXwEs2JxL`)
- ✅ **Propriétaire:** Confirmé (Allan Test Sutton)

### Script POST
- ✅ **Mutation:** Testée en dry-run
- ✅ **Variables:** Validées
- ✅ **Sécurité:** Confirmation requise avant exécution
- ⏸️ **Exécution:** En attente du signal utilisateur

---

## ⏸️ EN ATTENTE DU SIGNAL UTILISATEUR

**Comme demandé dans la consigne initiale:**

> "Rapport technique : Une fois la lecture réussie, propose-moi le script POST exact pour ajouter une note de service **sans l'exécuter tout de suite. Attend mon signal.**"

✅ **Tâche accomplie:**
- ✅ Piano lu avec succès
- ✅ Structure analysée
- ✅ Script POST préparé (Option A: `manualLastService`)
- ✅ Script NON exécuté
- ⏸️ **En attente du signal pour l'exécution**

---

**📞 Questions pour l'utilisateur:**

1. **L'approche simple (Option A: `manualLastService`) est-elle acceptable?**
   - ✅ Si oui → Donner le signal pour exécuter le script
   - ❌ Si non → Explorer l'Option B (workflow complet avec services)

2. **Acceptez-vous que `calculatedLastService` ne soit pas mis à jour automatiquement?**
   - C'est une limitation de l'Option A

3. **Avez-vous un piano dans Gazelle avec des RV complétés pour analyse?**
   - Cela aiderait à comprendre la structure des services

---

**Rapport généré le:** 2026-01-01
**Par:** Claude Code (Assistant Gazelle V5)
**Statut:** ⏸️ En attente du signal utilisateur
