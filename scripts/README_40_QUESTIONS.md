# 🎯 40 Questions de Test - Guide Rapide

Système SUPER FACILE pour tester et raffiner les réponses de l'assistant.

## 🚀 Démarrage en 3 Étapes

### 1️⃣ Choisis tes questions
```bash
python3 scripts/select_questions.py
```

Interface avec presets rapides:
- **Essentiels** (16 questions) - Le minimum pour tester
- **Haute priorité** (11 questions) - Les plus importantes
- **Haute + Moyenne** (23 questions) - Bon équilibre
- **Toutes** (40 questions) - Test complet

### 2️⃣ Teste les questions sélectionnées
```bash
python3 scripts/test_assistant_responses.py --test-enabled
```

### 3️⃣ Note les réponses

Pour chaque question, tu vois:
- La question posée
- La réponse générée
- Possibilité de noter (1-5 ⭐)
- Ajouter un commentaire

---

## 📋 Les 40 Questions

### Rendez-vous (14 questions)

**Quotidien** (haute priorité ✅)
- `.mes rv` - RV du jour
- `mes rendez-vous` - Variante
- `mes rv demain` - RV de demain
- `qu'est-ce que j'ai mardi prochain` - Date spécifique

**Vue globale** (pour Louise ✅)
- `tous les rv` - Agenda complet
- `tous les rv demain` - Demain complet
- `agenda complet de la semaine` - Vue hebdo

**Autres**
- `mes rv cette semaine`
- `rendez-vous du mois`
- `rv non confirmés`
- `rv urgents`

### Recherche Client (12 questions)

**VIP** (✅)
- `client Yannick` - Yannick Nézet-Séguin

**Contacts** (✅)
- `client anne-marie` - Test contacts vs clients

**Organisations** (✅)
- `client université` - Institutions

**Par ID** (✅)
- `client cli_xxx` - ID Gazelle exact

**Noms communs**
- `client Marie` - Prénom commun
- `client Tremblay` - Nom commun
- `client Jean-Philippe Reny` - Nom complet

**Recherche avancée**
- `clients à Montréal` - Par ville
- `client email@example.com` - Par email
- `client 514-555-1234` - Par téléphone

**Cas limites**
- `client INEXISTANT` - Aucun résultat

### Piano (8 questions)

**Marques** (✅)
- `piano Steinway` - Prestige
- `pianos Yamaha` - Populaire
- `piano Kawai RX3` - Modèle spécifique

**Recherche avancée**
- `piano série 123456` - Numéro de série
- `pianos à queue` - Par type
- `pianos nécessitant réparation` - Par état

**Historique**
- `historique piano série 123456`

### Edge Cases (4 questions)

**Erreurs attendues** (✅)
- `mes rv` (Louise) - Pas technicien
- `client INEXISTANT` - Aucun résultat
- `piano` - Trop vague

### Aide (2 questions)

- `.aide` - Liste des commandes ✅
- `qu'est-ce que tu peux faire` - Capacités ✅

---

## 🎨 Interface de Sélection

### Menu Principal

```
📊 RÉSUMÉ DES QUESTIONS
Total: 40 questions
✅ Activées: 16
❌ Désactivées: 24

Par catégorie:
  ✅ Rendez-vous - Quotidien: 4/4 (100%)
  ✅ Rendez-vous - Vue globale: 2/3 (67%)
  ✅ Recherche - Client VIP: 1/1 (100%)
  ...

📋 MENU

1. 🚀 Sélection rapide (presets)
2. 📁 Sélection par catégorie
3. 📝 Sélection individuelle
4. 👀 Voir questions activées
5. ✅ Terminer et sauvegarder
```

### 1. Sélection Rapide

Choix de presets en 1 clic:
```
1. Essentiels uniquement (16 questions)
2. Haute priorité (11 questions)
3. Haute + Moyenne priorité (23 questions)
4. Toutes les questions (40 questions)
5. Aucune (tout désactiver)
```

### 2. Par Catégorie

Activer/désactiver par groupe:
```
 1. ✅ Rendez-vous - Quotidien (4/4)
 2. ❌ Rendez-vous - Période (0/2)
 3. ✅ Recherche - Client VIP (1/1)
 ...
```

### 3. Individuelle

Toggle une par une:
```
 1. ✅ 🔴 .mes rv                    - Rendez-vous - Quotidien
 2. ✅ 🔴 mes rendez-vous            - Rendez-vous - Quotidien
 3. ✅ 🔴 mes rv demain              - Rendez-vous - Futur
 ...

Numéro(s) pour toggle (ex: 1,5,12)
> 7,8,9
```

### 4. Voir Activées

Liste groupée par catégorie:
```
✅ QUESTIONS ACTIVÉES

📁 Rendez-vous - Quotidien
    1. .mes rv
    2. mes rendez-vous
    3. mes rv demain

📁 Recherche - Client VIP
    8. client Yannick

Total: 16 questions activées
```

---

## 💡 Workflows Recommandés

### Workflow 1: Premier Test (15 min)

```bash
# 1. Sélectionner "Essentiels"
python3 scripts/select_questions.py
# → Choix 1 → Choix 1 (Essentiels)

# 2. Tester
python3 scripts/test_assistant_responses.py --test-enabled

# 3. Noter rapidement (pas de commentaires pour l'instant)
# Note: 3/5 pour tout noter vite

# 4. Identifier les pires réponses
grep '"user_rating": 1' test_results.json
grep '"user_rating": 2' test_results.json
```

### Workflow 2: Test Approfondi (1-2h)

```bash
# 1. Sélectionner "Haute + Moyenne"
python3 scripts/select_questions.py
# → Choix 1 → Choix 3

# 2. Tester avec notes détaillées
python3 scripts/test_assistant_responses.py -i
# Mode interactif: note + commentaire pour chaque

# 3. Analyser patterns
# Quelles catégories sont mal notées?
# Quels commentaires reviennent?
```

### Workflow 3: Raffiner une Catégorie

```bash
# 1. Activer UNE catégorie
python3 scripts/select_questions.py
# → Choix 2 → Choisir catégorie

# 2. Tester
python3 scripts/test_assistant_responses.py --test-enabled

# 3. Modifier le code
# Éditer api/assistant.py selon les retours

# 4. Re-tester
python3 scripts/test_assistant_responses.py --test-enabled

# 5. Comparer notes avant/après
```

---

## 📊 Analyse des Résultats

### Fichier de Résultats

`test_results.json` contient tout:

```json
{
  "timestamp": "2025-12-15T20:30:00",
  "scenario": {
    "name": "Recherche - Client VIP - 8",
    "question": "client Yannick",
    "category": "Recherche - Client VIP",
    "priority": "high"
  },
  "response": "🔍 **1 clients trouvés:**\n\n- **Yannick Nézet-Séguin** [Contact]",
  "user_rating": 4,
  "user_comment": "Bon mais manque ville et téléphone"
}
```

### Commandes Utiles

```bash
# Combien de tests?
cat test_results.json | grep '"timestamp"' | wc -l

# Moyenne des notes
cat test_results.json | grep '"user_rating"' | awk '{sum+=$2; n++} END {print sum/n}'

# Tests mal notés (≤ 2/5)
cat test_results.json | jq '.[] | select(.user_rating <= 2)'

# Tests par catégorie
cat test_results.json | jq -r '.[].scenario.category' | sort | uniq -c
```

---

## 💬 Modes d'Évaluation

Le système offre **2 modes d'évaluation**:

### Mode 1: Évaluation Structurée (Rapide)

```
Note (1-5): 4
Commentaire: Bon mais manque ville et téléphone
```

**Avantages:**
- ⚡ Rapide
- 📊 Notes comparables
- 🎯 Direct

**Utilise quand:**
- Test rapide de plusieurs questions
- Note simple suffit

### Mode 2: Feedback en Langage Naturel (Détaillé)

```
💬 Ton feedback:
Tu aurais dû inclure l'adresse complète
La réponse devrait mentionner le temps de déplacement
Manque le numéro de téléphone du client
```

**Avantages:**
- 📝 Détails précis
- 💡 Exemples concrets
- 🎨 Instructions claires

**Utilise quand:**
- Besoin de préciser exactement quoi changer
- Montrer un exemple de réponse attendue
- Expliquer le contexte

**Note:** Le système extrait automatiquement une note implicite du feedback naturel (1-5).

Voir [README_FEEDBACK_NATUREL.md](README_FEEDBACK_NATUREL.md) pour le guide complet.

---

## 🎯 Critères d'Évaluation

### ⭐⭐⭐⭐⭐ (5/5) - Excellent
- Réponse claire et concise
- Toutes les infos importantes
- Format professionnel
- Aucune amélioration évidente

### ⭐⭐⭐⭐ (4/5) - Très bon
- Réponse correcte
- Quelques détails manquants
- Format ok mais perfectible

### ⭐⭐⭐ (3/5) - Correct
- Réponse acceptable
- Manque plusieurs infos
- Format à améliorer

### ⭐⭐ (2/5) - Insuffisant
- Réponse incomplète
- Infos importantes manquantes
- Format confus

### ⭐ (1/5) - Mauvais
- Réponse incorrecte
- Données manquantes
- Inutilisable

---

## 🚀 Quick Start Complet

```bash
# Installation (première fois)
cd /Users/allansutton/Documents/assistant-gazelle-v5

# Étape 1: Choisis 16 questions essentielles
python3 scripts/select_questions.py
# → Menu: 1 (Sélection rapide)
# → Preset: 1 (Essentiels)
# → Menu: 5 (Terminer)

# Étape 2: Teste-les
python3 scripts/test_assistant_responses.py --test-enabled
# Note chaque réponse (1-5)

# Étape 3: Vois les résultats
cat test_results.json | jq '.[-10:]'  # 10 derniers tests

# Étape 4: Identifie améliorations
cat test_results.json | jq '.[] | select(.user_rating <= 2)'
```

---

**Créé:** 2025-12-15
**Pour:** Raffinement itératif des réponses
**Réutilisable:** Toutes les instances Piano-Tek

