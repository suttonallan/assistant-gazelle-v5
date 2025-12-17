# 🚀 Démarrage Rapide - Entraînement des Sommaires

Guide rapide en 5 minutes pour commencer à raffiner les formats de sommaires.

## ⚡ Lancer le Système

```bash
cd /Users/allansutton/Documents/assistant-gazelle-v5
python3 scripts/train_summaries.py
```

## 📋 Menu Principal

```
1. Tester sommaire de journée
2. Tester sommaire client
3. Voir historique d'entraînement
4. Comparer formats côte à côte
5. Quitter
```

## 🎯 Workflow Recommandé (Première Fois)

### Étape 1: Comparer les Formats (2 min)

```
Choix: 4
Que veux-tu comparer?: 1 (Sommaire de journée)
```

**Résultat:** Voir les 3 formats côte à côte avec tes RV réels d'aujourd'hui.

### Étape 2: Tester ton Format Préféré (2 min)

```
Choix: 1 (Tester sommaire de journée)

Date: 1 (Aujourd'hui)
Technicien: 2 (Nick) ou 1 (Tous)
Format: 2 (Détaillé) ou autre selon préférence
```

**Résultat:** Sommaire généré avec tes vraies données.

### Étape 3: Donner Feedback (1 min)

```
Options:
1. Donner feedback détaillé (recommandé)
2. Note rapide (1-5)
3. Passer

Choix: 1
```

**Exemple de feedback:**
```
Tu aurais dû inclure le numéro de téléphone
La réponse devrait mentionner le temps de déplacement
Manque les détails du piano à accorder
```

**Note:** Le système extrait automatiquement une note de ton feedback!

### Étape 4: Voir l'Historique (30 sec)

```
Choix: 3
```

**Résultat:** Tous tes tests avec feedbacks sauvegardés.

## 🎨 Les 3 Formats en Bref

### Format 1: Compact

**Pour:** Aperçu rapide, notification SMS

```
1. 09:00 - Accordage - Yannick Nézet-Séguin
2. 14:30 - Réparation - Conservatoire
```

### Format 2: Détaillé

**Pour:** Planification de journée, infos complètes

```
1. 🕐 09:00 - Accordage
   👤 Yannick Nézet-Séguin
   📍 123 Rue Example, Montréal
   📞 514-555-1234
```

### Format 3: V4 Style

**Pour:** Compatible ancien système, extraction reminders

```
1. 09:00 - Yannick Nézet-Séguin
  Adresse: 123 Rue Example, Montréal
  Service: Accordage
  ⚠️ RAPPEL: !! Apporter cordes
```

## 💬 Exemples de Bon Feedback

### ✅ Excellent (Détaillé et Actionnable)

```
Tu aurais dû dire:
"9:00 - Yannick Nézet-Séguin (514-555-1234)
📍 123 Rue Example, Montréal (15 min de ton dernier RV)
🎹 Steinway Grand Piano
⚠️ Apporter cordes de remplacement"

Au lieu de juste:
"9:00 - Accordage - Yannick Nézet-Séguin"

Manquent: téléphone, adresse, temps de déplacement, type de piano, reminders
```

### ✅ Bon (Liste Claire)

```
La réponse devrait inclure:
- Le numéro de téléphone du client
- L'adresse complète (pas juste la ville)
- Le temps de déplacement estimé
- Les reminders importants (lignes avec !!)
```

### ❌ Pas Assez Spécifique

```
Pas bien
Manque des choses
À améliorer
```

## 📁 Fichiers Générés

### `scripts/summary_training_results.json`

Tous tes tests avec feedbacks. Analyse avec:

```bash
# Voir tous les feedbacks
cat scripts/summary_training_results.json | jq -r '.[] | .feedback.feedback'

# Notes moyennes par format
cat scripts/summary_training_results.json | jq -r '.[] | "\(.format_style)|\(.feedback.rating // .feedback.implicit_rating // 0)"' | awk -F'|' '{sum[$1]+=$2; count[$1]++} END {for (f in sum) print f": "sum[f]/count[f]}'
```

## 🔍 Prochaines Étapes

### Après 5-10 Tests

1. **Analyser les patterns** - Qu'est-ce qui manque souvent?
2. **Identifier format préféré** - Quel format a les meilleures notes?
3. **Raffiner le code** - Ajuster selon feedbacks
4. **Re-tester** - Vérifier améliorations

### Fonctionnalités Futures

- Google Maps Distance Matrix API (temps de déplacement)
- Extraction intelligente de reminders
- Templates personnalisables par utilisateur

## 📚 Documentation Complète

- **[README_TRAIN_SUMMARIES.md](README_TRAIN_SUMMARIES.md)** - Guide complet (500+ lignes)
- **[docs/CHANGELOG_TRAIN_SUMMARIES.md](../docs/CHANGELOG_TRAIN_SUMMARIES.md)** - Changelog détaillé
- **[summary_training_results_example.json](summary_training_results_example.json)** - Exemples de résultats

## ❓ Questions Fréquentes

### Le système utilise-t-il de vraies données?

Oui! Il se connecte à Supabase et utilise tes RV réels, tes vrais clients, et tes pianos réels.

### Est-ce que ça modifie mes données?

Non! C'est lecture seule. Ça génère juste des sommaires et sauvegarde tes feedbacks localement.

### C'est web ou local?

100% local. Interface CLI uniquement, pas de serveur web.

### Ça fait partie de l'assistant?

Non. C'est un outil séparé pour **entraîner/raffiner** les formats avant de les intégrer à l'assistant.

### Combien de temps ça prend?

- **Premier test:** 2-3 minutes
- **Comparer formats:** 30 secondes
- **Donner feedback:** 1-2 minutes
- **Session complète:** 10-15 minutes

---

**Prêt?** Lance `python3 scripts/train_summaries.py` et commence! 🚀
