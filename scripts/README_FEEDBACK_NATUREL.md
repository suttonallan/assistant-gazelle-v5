# 💬 Feedback en Langage Naturel - Guide

Le système de test de l'assistant supporte maintenant le **feedback en langage naturel**, te permettant de donner tes commentaires de manière conversationnelle.

## 🎯 Pourquoi cette fonctionnalité?

Au lieu de donner une note numérique rigide (1-5) et un commentaire court, tu peux maintenant exprimer tes retours de manière plus naturelle et détaillée, comme si tu parlais à l'assistant directement.

## 📝 Comment ça marche?

### 1. Lors de l'évaluation

Quand tu testes une question, tu auras 3 choix:

```
📊 ÉVALUATION
Mode d'évaluation:
1. Évaluation structurée (note + commentaire)
2. Feedback en langage naturel
3. Passer (pas d'évaluation)

Choix: 2
```

### 2. Donner ton feedback

```
💬 Feedback en langage naturel
Exemples:
  • Tu aurais dû me dire ceci: ...
  • La réponse devrait inclure ...
  • Trop verbeux, simplifie en ...
  • Manque l'information sur ...

Ton feedback (ligne vide pour terminer):
```

**Écris autant de lignes que tu veux.** Laisse une ligne vide pour terminer.

## ✍️ Exemples de Feedback

### Exemple 1: Instructions directes

```
Tu aurais dû inclure l'adresse complète
La ville devrait apparaître après le nom du client
Ajoute le numéro de téléphone
```

### Exemple 2: Feedback constructif

```
La réponse est correcte mais trop verbeuse
Simplifie en enlevant les détails sur les heures exactes
Concentre-toi sur l'essentiel: nom, type de service, piano
```

### Exemple 3: Feedback détaillé

```
Tu aurais dû dire ceci:
"📅 2 rendez-vous aujourd'hui:
1. Yannick (accordage) - 514-555-1234
2. Conservatoire (réparation) - 514-555-9999"

Au lieu de tout ce texte verbeux avec les heures et descriptions
```

### Exemple 4: Problèmes spécifiques

```
Manque l'information sur le modèle de piano
Le client a 3 pianos mais tu n'en montres qu'un
La date du prochain rendez-vous devrait être mentionnée
```

## 🤖 Extraction Automatique de Note

Le système analyse ton feedback et **extrait automatiquement une note implicite** basée sur les mots-clés:

| Mots-clés | Note Implicite |
|-----------|----------------|
| excellent, parfait, impeccable | ⭐⭐⭐⭐⭐ (5/5) |
| très bon, bien | ⭐⭐⭐⭐ (4/5) |
| correct, acceptable, ok | ⭐⭐⭐ (3/5) |
| insuffisant, mauvais, pas bon | ⭐⭐ (2/5) |
| terrible, inutilisable, incorrect | ⭐ (1/5) |

**Exemple:**
```
Feedback: "La réponse est correcte mais manque plusieurs détails importants"
→ Note implicite: 3/5 (mot "correcte" détecté)
```

## 💾 Format de Sauvegarde

Le feedback est sauvegardé dans `test_results.json`:

```json
{
  "timestamp": "2025-12-15T20:35:00",
  "scenario": {
    "name": "Rendez-vous - Quotidien - 1",
    "question": ".mes rv"
  },
  "response": "📅 Aujourd'hui: 3 rendez-vous...",
  "feedback_mode": "natural",
  "natural_feedback": "Tu aurais dû mentionner le temps de déplacement\nLa réponse devrait inclure l'adresse complète\nTrop de détails sur l'heure",
  "implicit_rating": 3
}
```

## 🔍 Analyser les Feedbacks

### Voir tous les feedbacks naturels

```bash
cat test_results.json | jq '.[] | select(.natural_feedback) | {question: .scenario.question, feedback: .natural_feedback, rating: .implicit_rating}'
```

### Feedbacks avec problèmes (note ≤ 2)

```bash
cat test_results.json | jq '.[] | select(.implicit_rating <= 2) | .natural_feedback'
```

### Extraire patterns communs

```bash
# Toutes les mentions de "devrait"
cat test_results.json | jq -r '.[] | select(.natural_feedback) | .natural_feedback' | grep -i "devrait"

# Toutes les mentions de "manque"
cat test_results.json | jq -r '.[] | select(.natural_feedback) | .natural_feedback' | grep -i "manque"

# Toutes les mentions de "trop"
cat test_results.json | jq -r '.[] | select(.natural_feedback) | .natural_feedback' | grep -i "trop"
```

### Compter par mode d'évaluation

```bash
cat test_results.json | jq -r '.[].feedback_mode' | sort | uniq -c
```

Résultat exemple:
```
  15 natural
  23 structured
   5 skipped
```

## 💡 Conseils d'Utilisation

### Quand utiliser le feedback naturel?

✅ **Utilise le feedback naturel quand:**
- Tu as plusieurs points précis à améliorer
- Tu veux montrer un exemple concret de ce que tu attendais
- La réponse nécessite des modifications structurelles
- Tu veux expliquer le contexte de tes attentes

✅ **Utilise l'évaluation structurée quand:**
- Tu veux juste une note rapide
- Le commentaire tient en une phrase
- Tu testes rapidement plusieurs scénarios

### Formulations efficaces

**✅ Bon:**
```
Tu aurais dû inclure l'adresse complète du client
La réponse devrait montrer le numéro de série du piano
Manque l'information sur le prochain rendez-vous prévu
```

**❌ Moins bon:**
```
Pas bien
Mauvais
À améliorer
```

**✅ Excellent (avec exemple):**
```
Tu aurais dû dire:
"Yannick Nézet-Séguin - 514-555-1234
📍 1234 rue Sherbrooke, Montréal
🎹 Steinway Grand Piano (S/N: 123456)"

Au lieu de juste "Yannick Nézet-Séguin [Contact]"
```

## 🎯 Workflow Recommandé

### Session de Raffinement avec Feedback Naturel

```bash
# 1. Sélectionner 5-10 questions importantes
python3 scripts/select_questions.py
# → Menu: 1 (Sélection rapide) → Choix: 2 (Haute priorité)

# 2. Tester en mode interactif
python3 scripts/test_assistant_responses.py

# 3. Pour chaque test:
#    - Lis la réponse générée
#    - Choisis mode 2 (Feedback naturel)
#    - Décris PRÉCISÉMENT ce qui manque ou ce qui devrait changer

# 4. Analyser les patterns
cat test_results.json | jq -r '.[] | select(.natural_feedback) | .natural_feedback' | grep -i "devrait"

# 5. Identifier les améliorations les plus demandées
cat test_results.json | jq -r '.[] | select(.natural_feedback) | .natural_feedback' | sort | uniq -c | sort -rn

# 6. Modifier api/assistant.py selon les feedbacks

# 7. Re-tester et comparer
python3 scripts/test_assistant_responses.py --test-enabled
```

## 🚀 Exemples Réels

### Avant Feedback

**Question:** `client Yannick`

**Réponse générée:**
```
🔍 **1 clients trouvés:**

- **Yannick Nézet-Séguin** [Contact]
```

**Feedback naturel:**
```
Tu aurais dû inclure:
- Le numéro de téléphone
- La ville
- L'email si disponible
- Le nombre de pianos associés

Format souhaité:
"🔍 1 contact trouvé:

Yannick Nézet-Séguin
📍 Montréal
📞 514-555-1234
📧 yannick@example.com
🎹 2 pianos"
```

### Après Modification

**Réponse améliorée:**
```
🔍 **1 contact trouvé:**

**Yannick Nézet-Séguin**
📍 Montréal
📞 514-555-1234
📧 yns@osm.ca
🎹 2 pianos enregistrés
```

---

**Créé:** 2025-12-15
**Objectif:** Raffiner les réponses de l'assistant avec des feedbacks précis et actionnables
**Réutilisable:** Toutes les instances Piano-Tek
