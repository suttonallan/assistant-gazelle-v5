# 🧪 Test Assistant - Guide d'Utilisation

Script interactif pour tester et raffiner les réponses de l'assistant avec de vraies données.

## 🚀 Démarrage Rapide

```bash
# Mode interactif (recommandé pour commencer)
python3 scripts/test_assistant_responses.py

# Tester une question spécifique
python3 scripts/test_assistant_responses.py --question "client Yannick"

# Trouver des clients avec données riches
python3 scripts/test_assistant_responses.py --rich-clients

# Tester tous les scénarios prédéfinis
python3 scripts/test_assistant_responses.py --test-all
```

## 📋 Mode Interactif

Le mode interactif vous permet de:

1. **Tester des scénarios prédéfinis** (journée chargée, recherche client, etc.)
2. **Poser vos propres questions** personnalisées
3. **Noter les réponses** (1-5 étoiles)
4. **Ajouter des commentaires** sur ce qui pourrait être amélioré
5. **Voir l'historique** des tests précédents

### Menu Principal

```
Options:
1. Tester un scénario prédéfini
2. Tester une question personnalisée
3. Voir les clients avec données riches
4. Voir historique des tests
5. Quitter
```

## 🎯 Scénarios Prédéfinis

1. **Journée chargée technicien** - `.mes rv` (Nick)
2. **Tous les RV (Louise)** - `tous les rv demain` (Assistante)
3. **Recherche client riche** - `client Yannick` (Yannick Nézet-Séguin)
4. **Recherche contact** - `client anne-marie` (Test contacts vs clients)
5. **Piano spécifique** - `piano Steinway` (Pianos de prestige)

## 💾 Sauvegarde des Résultats

Tous les tests sont automatiquement sauvegardés dans `test_results.json`:

**Mode structuré:**
```json
{
  "timestamp": "2025-12-15T20:30:00",
  "scenario": {
    "name": "Recherche client riche",
    "question": "client Yannick",
    "user_id": "anonymous"
  },
  "response": "🔍 **1 clients trouvés:**\n\n- **Yannick Nézet-Séguin** [Contact]",
  "user_rating": 4,
  "user_comment": "Bon mais manque ville et téléphone"
}
```

**Mode feedback naturel:**
```json
{
  "timestamp": "2025-12-15T20:35:00",
  "scenario": {
    "name": "Rendez-vous - Quotidien - 1",
    "question": ".mes rv",
    "user_id": "nlessard@piano-tek.com"
  },
  "response": "📅 Aujourd'hui: 3 rendez-vous...",
  "feedback_mode": "natural",
  "natural_feedback": "Tu aurais dû mentionner le temps de déplacement\nLa réponse devrait inclure l'adresse complète\nTrop de détails sur l'heure",
  "implicit_rating": 3
}
```

## 🔍 Trouver des Clients Riches

Pour tester avec des données réalistes, utilisez:

```bash
python3 scripts/test_assistant_responses.py --rich-clients
```

Cela affiche les clients avec le plus de données (pianos, historique, etc.):

```
📚 Clients trouvés avec données:

1. Yannick Nézet-Séguin (Montréal)
   • ID: con_B0MSYk5mU7NGZsWn
   • Type: contact

2. Marie-Anne Rozankovic (Québec)
   • ID: con_TxkjuNzZ3XmGbRJL
   • Type: contact
```

## 📊 Workflow de Raffinement

### 1. Tester

```bash
python3 scripts/test_assistant_responses.py
```

→ Choisissez un scénario ou posez une question

### 2. Noter

Deux modes d'évaluation disponibles:

**Mode structuré** (classique):
```
Mode d'évaluation:
1. Évaluation structurée (note + commentaire)
2. Feedback en langage naturel
3. Passer (pas d'évaluation)

Choix: 1
Note (1-5): 3
Commentaire: Trop verbeux, manque infos importantes sur le piano
```

**Mode langage naturel** (nouveau):
```
Choix: 2

💬 Feedback en langage naturel
Exemples:
  • Tu aurais dû me dire ceci: ...
  • La réponse devrait inclure ...
  • Trop verbeux, simplifie en ...
  • Manque l'information sur ...

Ton feedback:
Tu aurais dû mentionner le numéro de série du piano directement
La ville du client devrait apparaître après le nom
Trop de détails inutiles sur les heures
```

### 3. Identifier les Problèmes

Regardez les résultats dans `test_results.json`:
- Quels formats de réponse sont mal notés?
- Quels commentaires reviennent souvent?
- Quelles informations manquent?

**Note sur le feedback naturel:**
Le système extrait automatiquement une note implicite du feedback naturel:
- Mots comme "excellent", "parfait" → Note implicite: 5/5
- "très bon", "bien" → 4/5
- "correct", "acceptable", "ok" → 3/5
- "insuffisant", "mauvais" → 2/5
- "terrible", "inutilisable" → 1/5

Cette note apparaît dans les résultats et l'historique.

### 4. Modifier les Templates

Les réponses sont formatées dans `api/assistant.py`:

```python
# Ligne ~425 pour recherche clients
def _format_response(query_type, results):
    if query_type == QueryType.SEARCH_CLIENT:
        # Modifier ici le format de réponse
        ...
```

### 5. Re-tester

Relancez les mêmes scénarios pour comparer:

```bash
python3 scripts/test_assistant_responses.py --test-all
```

### 6. Comparer

Ouvrez `test_results.json` et comparez les notes avant/après.

## 🎨 Personnaliser les Scénarios

Éditez `scripts/test_assistant_responses.py`, fonction `load_test_scenarios()`:

```python
def load_test_scenarios(self) -> List[Dict]:
    return [
        {
            'name': 'Mon scénario personnalisé',
            'question': 'résume la semaine de Nick',
            'user_id': 'nlessard@piano-tek.com',
            'description': 'Test résumé hebdomadaire'
        },
        # Ajoutez vos scénarios ici...
    ]
```

## 📈 Métriques de Qualité

Pour chaque test, vous verrez:

- **Parsing**
  - Type détecté correctement?
  - Confiance du parser (%)
  - Paramètres extraits

- **Résultats**
  - Nombre de résultats
  - Données retournées

- **Réponse**
  - Format final affiché à l'utilisateur

## 💡 Conseils

### Pour Tester Efficacement

1. **Commencez simple** - Testez d'abord les scénarios prédéfinis
2. **Variez les utilisateurs** - Testez en tant que Nick, Louise, anonymous
3. **Notez systématiquement** - Même si c'est juste 3/5, ça aide
4. **Commentez précisément** - "Manque la ville" plutôt que "Pas bien"
5. **Testez les edge cases** - Clients sans pianos, contacts sans email, etc.

### Cas Intéressants à Tester

- Client VIP (Yannick) → Doit ressortir comme important
- Clients avec plusieurs pianos → Doit lister tous les pianos
- Journée chargée → Doit optimiser l'affichage
- Pas de rendez-vous → Message clair
- Louise demande "mes rv" → Message explicatif (elle n'est pas technicienne)

## 🔧 Dépannage

### Erreur: "cannot import..."

Vérifiez que vous êtes dans le bon répertoire:

```bash
cd /Users/allansutton/Documents/assistant-gazelle-v5
python3 scripts/test_assistant_responses.py
```

### Erreur 400 / 401

Variables d'environnement manquantes:

```bash
# Vérifier
python3 -c "import os; print('SUPABASE_URL' in os.environ)"

# Charger
source .env  # ou export SUPABASE_URL=...
```

### Pas de résultats

La table est peut-être vide. Synchronisez d'abord:

```bash
python3 modules/sync_gazelle/sync_to_supabase.py
```

## 🔎 Analyser le Feedback Naturel

Pour extraire et analyser les feedbacks naturels des tests:

```bash
# Voir tous les feedbacks naturels
cat test_results.json | jq '.[] | select(.natural_feedback) | {question: .scenario.question, feedback: .natural_feedback, rating: .implicit_rating}'

# Feedbacks avec note implicite faible (≤ 2)
cat test_results.json | jq '.[] | select(.implicit_rating <= 2) | .natural_feedback'

# Compter les feedbacks par mode
cat test_results.json | jq -r '.[].feedback_mode' | sort | uniq -c

# Extraire patterns communs
cat test_results.json | jq -r '.[] | select(.natural_feedback) | .natural_feedback' | grep -i "devrait"
cat test_results.json | jq -r '.[] | select(.natural_feedback) | .natural_feedback' | grep -i "manque"
```

## 📝 Exemples d'Utilisation

### Exemple 1: Test Rapide d'une Question

```bash
$ python3 scripts/test_assistant_responses.py --question "mes rv demain" --user "nlessard@piano-tek.com"

======================================================================
📝 Test: Test CLI
======================================================================
Question: mes rv demain
User: nlessard@piano-tek.com

🧠 Parsing:
   Type: QueryType.APPOINTMENTS
   Confiance: 85%

💬 Réponse générée:
----------------------------------------------------------------------
📅 Demain: 3 rendez-vous
...
```

### Exemple 2: Session Interactive Complète

```bash
$ python3 scripts/test_assistant_responses.py

🎮 MODE INTERACTIF - Test de l'Assistant

Options:
1. Tester un scénario prédéfini
2. Tester une question personnalisée
...

Choix: 1

Scénarios disponibles:
1. Journée chargée technicien - Test résumé quotidien
2. Tous les RV (Louise) - Vue complète agenda
...

Numéro du scénario: 1

[Test s'exécute...]

📊 ÉVALUATION
Mode d'évaluation:
1. Évaluation structurée (note + commentaire)
2. Feedback en langage naturel
3. Passer (pas d'évaluation)

Choix: 1
Note (1-5): 4
Commentaire: Bon mais pourrait inclure temps de déplacement

✅ Résultat sauvegardé!
```

### Exemple 3: Feedback en Langage Naturel

```bash
$ python3 scripts/test_assistant_responses.py

[...test s'exécute...]

💬 Réponse générée:
----------------------------------------------------------------------
📅 Aujourd'hui: 2 rendez-vous

1. 09:00 - Accordage - Yannick Nézet-Séguin
2. 14:30 - Réparation - Conservatoire de Montréal
----------------------------------------------------------------------

📊 ÉVALUATION
Mode d'évaluation:
1. Évaluation structurée (note + commentaire)
2. Feedback en langage naturel
3. Passer (pas d'évaluation)

Choix: 2

💬 Feedback en langage naturel
Exemples:
  • Tu aurais dû me dire ceci: ...
  • La réponse devrait inclure ...
  • Trop verbeux, simplifie en ...
  • Manque l'information sur ...

Ton feedback (ligne vide pour terminer):
Tu aurais dû inclure l'adresse complète pour chaque RV
La réponse devrait mentionner le temps de déplacement estimé
Manque le numéro de téléphone du client pour le premier rendez-vous

✅ Résultat sauvegardé!
Note implicite extraite: 3/5
```

## 🎯 Objectif Final

L'objectif est d'avoir des réponses qui:

1. ✅ Sont **claires** et **concises**
2. ✅ Contiennent toutes les **informations essentielles**
3. ✅ Sont **adaptées** au contexte (technicien vs assistante)
4. ✅ Ont un **format cohérent** et professionnel
5. ✅ Sont **personnalisables** par préférences utilisateur

---

**Créé le:** 2025-12-15
**Pour:** Raffinement continu des réponses de l'assistant
**Réutilisable pour:** Toutes les instances Piano-Tek
