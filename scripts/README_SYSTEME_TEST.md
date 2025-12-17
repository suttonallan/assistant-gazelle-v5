# 🧪 Système de Test de l'Assistant - Vue d'Ensemble

Système complet pour tester, évaluer et raffiner les réponses de l'assistant Piano-Tek avec des données réelles.

## 📚 Documentation

Le système est composé de plusieurs guides:

1. **[README_40_QUESTIONS.md](README_40_QUESTIONS.md)** - Guide rapide des 40 questions de test
   - Choix facile des questions à tester
   - Presets prédéfinis (Essentiels, Haute priorité, etc.)
   - Interface de sélection interactive

2. **[README_TEST_ASSISTANT.md](README_TEST_ASSISTANT.md)** - Guide complet du testeur
   - Mode interactif
   - Test de scénarios prédéfinis
   - Sauvegarde et historique des résultats

3. **[README_FEEDBACK_NATUREL.md](README_FEEDBACK_NATUREL.md)** - Guide du feedback naturel
   - Comment donner des feedbacks en langage naturel
   - Extraction automatique de notes implicites
   - Analyse des patterns de feedback

## 🚀 Quick Start (3 étapes)

### 1. Choisis tes questions

```bash
python3 scripts/select_questions.py
```

Interface avec presets:
- **Essentiels** (16 questions) - Le minimum
- **Haute priorité** (11 questions) - Les plus importantes
- **Haute + Moyenne** (23 questions) - Bon équilibre
- **Toutes** (40 questions) - Test complet

### 2. Teste

```bash
python3 scripts/test_assistant_responses.py --test-enabled
```

ou

```bash
python3 scripts/test_assistant_responses.py  # Mode interactif
```

### 3. Évalue

Deux modes au choix:

**Mode Rapide (Structuré):**
```
Note (1-5): 4
Commentaire: Bon mais manque ville
```

**Mode Détaillé (Langage Naturel):**
```
Tu aurais dû inclure:
- L'adresse complète
- Le numéro de téléphone
- Le nombre de pianos associés
```

## 📁 Fichiers du Système

### Scripts

- `scripts/select_questions.py` - Sélectionneur interactif de questions
- `scripts/test_assistant_responses.py` - Testeur interactif principal
- `scripts/questions_test.json` - 40 questions organisées par catégorie

### Documentation

- `scripts/README_40_QUESTIONS.md` - Guide des 40 questions
- `scripts/README_TEST_ASSISTANT.md` - Guide du testeur
- `scripts/README_FEEDBACK_NATUREL.md` - Guide du feedback naturel
- `scripts/README_SYSTEME_TEST.md` - Ce fichier (vue d'ensemble)

### Résultats

- `test_results.json` - Tous les résultats de tests (créé automatiquement)
- `test_results_example.json` - Exemple de structure de résultats

## 🎯 Workflows

### Workflow 1: Test Rapide (15 min)

```bash
# 1. Sélectionner essentiels
python3 scripts/select_questions.py
# → Menu: 1 → Choix: 1

# 2. Tester
python3 scripts/test_assistant_responses.py --test-enabled

# 3. Noter vite (mode structuré)
# Note: 3, Commentaire: court
```

### Workflow 2: Raffinement Approfondi (1-2h)

```bash
# 1. Sélectionner haute + moyenne priorité
python3 scripts/select_questions.py
# → Menu: 1 → Choix: 3

# 2. Tester en mode interactif
python3 scripts/test_assistant_responses.py

# 3. Donner feedback naturel détaillé pour chaque
# Mode: 2 (Feedback naturel)

# 4. Analyser patterns
cat test_results.json | jq -r '.[] | select(.natural_feedback) | .natural_feedback' | grep -i "devrait"

# 5. Modifier api/assistant.py

# 6. Re-tester
python3 scripts/test_assistant_responses.py --test-enabled
```

### Workflow 3: Focus sur une Catégorie

```bash
# 1. Activer UNE catégorie
python3 scripts/select_questions.py
# → Menu: 2 → Choisir catégorie

# 2. Tester
python3 scripts/test_assistant_responses.py --test-enabled

# 3. Raffiner code

# 4. Re-tester et comparer
```

## 📊 Analyser les Résultats

### Statistiques Générales

```bash
# Nombre total de tests
cat test_results.json | jq '. | length'

# Moyenne des notes
cat test_results.json | jq '[.[] | select(.user_rating) | .user_rating] | add / length'

# Tests par mode d'évaluation
cat test_results.json | jq -r '.[].feedback_mode' | sort | uniq -c
```

### Tests Mal Notés

```bash
# Notes ≤ 2
cat test_results.json | jq '.[] | select(.user_rating <= 2 or .implicit_rating <= 2)'

# Avec commentaires
cat test_results.json | jq '.[] | select((.user_rating <= 2 or .implicit_rating <= 2) and (.user_comment or .natural_feedback))'
```

### Feedbacks Naturels

```bash
# Tous les feedbacks naturels
cat test_results.json | jq '.[] | select(.natural_feedback) | {question: .scenario.question, feedback: .natural_feedback, rating: .implicit_rating}'

# Extraire patterns
cat test_results.json | jq -r '.[] | select(.natural_feedback) | .natural_feedback' | grep -i "devrait"
cat test_results.json | jq -r '.[] | select(.natural_feedback) | .natural_feedback' | grep -i "manque"
cat test_results.json | jq -r '.[] | select(.natural_feedback) | .natural_feedback' | grep -i "aurais dû"
```

### Par Catégorie

```bash
# Tests par catégorie
cat test_results.json | jq -r '.[].scenario.category' | sort | uniq -c

# Moyenne par catégorie
cat test_results.json | jq -r '.[] | "\(.scenario.category)|\(.user_rating // .implicit_rating // 0)"' | \
  awk -F'|' '{sum[$1]+=$2; count[$1]++} END {for (cat in sum) print cat": "sum[cat]/count[cat]}'
```

## 💡 Bonnes Pratiques

### Quand utiliser le mode structuré?

- ✅ Test rapide de plusieurs questions
- ✅ Note simple suffit
- ✅ Commentaire court et clair

### Quand utiliser le feedback naturel?

- ✅ Besoin de détails précis
- ✅ Montrer exemple de réponse attendue
- ✅ Expliquer contexte et raisonnement
- ✅ Instructions multiples

### Conseils d'Évaluation

1. **Sois cohérent** - Utilise les mêmes critères pour tous les tests
2. **Sois spécifique** - "Manque la ville" plutôt que "Pas bien"
3. **Donne des exemples** - Montre ce que tu attendais
4. **Priorise** - Concentre-toi sur les problèmes les plus importants
5. **Re-teste** - Compare avant/après modifications

## 🎨 Exemples de Feedbacks Utiles

### ✅ Feedback Excellent

```
Tu aurais dû dire:
"Yannick Nézet-Séguin
📍 Montréal, QC
📞 514-555-1234
🎹 2 pianos (Steinway, Yamaha)"

Au lieu de juste:
"Yannick Nézet-Séguin [Contact]"

Manquent: ville, téléphone, nombre de pianos
```

### ✅ Feedback Bon

```
La réponse devrait inclure:
- L'adresse complète du rendez-vous
- Le temps de déplacement estimé
- Le numéro de téléphone du client
```

### ❌ Feedback Moins Utile

```
Pas bien
Mauvais
À améliorer
Pas ce que je voulais
```

## 🔧 Personnalisation

### Ajouter tes propres questions

Édite `scripts/questions_test.json`:

```json
{
  "id": 41,
  "category": "Ma Catégorie",
  "question": "ma question",
  "user": "user@example.com",
  "description": "Description",
  "priority": "high",
  "enabled": true
}
```

### Créer tes propres presets

Édite `scripts/select_questions.py`, fonction `quick_select()`:

```python
elif choice == '6':
    # Ton preset personnalisé
    for q in self.questions:
        q['enabled'] = (ton_critère_ici)
```

## 📈 Objectifs

Ce système vise à obtenir des réponses qui:

1. ✅ Sont **claires** et **concises**
2. ✅ Contiennent toutes les **informations essentielles**
3. ✅ Sont **adaptées** au contexte (technicien vs assistante)
4. ✅ Ont un **format cohérent** et professionnel
5. ✅ Sont **personnalisables** selon les préférences

## 🎓 Ressources

- [README_40_QUESTIONS.md](README_40_QUESTIONS.md) - Guide rapide
- [README_TEST_ASSISTANT.md](README_TEST_ASSISTANT.md) - Guide complet
- [README_FEEDBACK_NATUREL.md](README_FEEDBACK_NATUREL.md) - Guide feedback naturel
- `test_results_example.json` - Exemples de résultats

---

**Créé:** 2025-12-15
**Version:** 1.0
**Pour:** Raffinement itératif de l'assistant Piano-Tek
**Réutilisable:** Toutes les instances
