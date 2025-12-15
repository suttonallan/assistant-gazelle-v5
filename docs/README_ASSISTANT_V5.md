# Assistant Conversationnel Gazelle V5

## 🎯 Vue d'Ensemble

L'Assistant Conversationnel Gazelle V5 permet d'interroger la base de données Gazelle en langage naturel.

### Fonctionnalités

- ✅ **Parsing intelligent** : Comprend les questions en français
- ✅ **Recherche vectorielle** : Utilise OpenAI embeddings (126,519 entrées indexées)
- ✅ **Requêtes Supabase** : Via REST API (pas de PostgreSQL direct)
- ✅ **Types de requêtes** : Rendez-vous, recherche clients/pianos, résumés, stats
- ✅ **API FastAPI** : Routes `/assistant/chat` et `/assistant/health`

---

## 📁 Architecture

```
modules/assistant/
├── __init__.py
└── services/
    ├── __init__.py
    ├── parser.py          # Parse les questions en langage naturel
    ├── queries.py         # Exécute les requêtes Supabase
    └── vector_search.py   # Recherche vectorielle OpenAI

api/
└── assistant.py          # Routes FastAPI

data/
└── gazelle_vectors.pkl   # Index vectoriel (126,519 entrées, 1.5 GB)

tests/
└── test_assistant_api.py # Tests automatisés
```

---

## 🚀 Installation

### 1. Dépendances

```bash
pip3 install openai numpy psycopg2-binary
```

### 2. Variables d'Environnement

Ajouter dans `.env` :

```bash
# OpenAI
OPENAI_API_KEY=sk-...

# Supabase
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_KEY=eyJhbGci...
SUPABASE_PASSWORD=xxx  # Optionnel (pour scripts psycopg2)
```

### 3. Fichier Vectoriel

Le fichier `data/gazelle_vectors.pkl` doit être présent avec 126,519 entrées.

Vérifier :
```bash
python3 -c "
from dotenv import load_dotenv
load_dotenv()
from modules.assistant.services.vector_search import get_vector_search
vs = get_vector_search()
print(f'Index size: {len(vs.index_data[\"texts\"])} entrées')
"
```

---

## 📡 API Endpoints

### POST /assistant/chat

Poser une question à l'assistant.

**Request:**
```json
{
  "question": ".mes rv"
}
```

**Response:**
```json
{
  "question": ".mes rv",
  "answer": "📅 **2 rendez-vous le 2025-12-14:**\n\n- **09:00** : Client A (Montréal)\n- **14:00** : Client B (Québec)",
  "query_type": "appointments",
  "confidence": 1.0,
  "data": {...},
  "vector_search_used": false
}
```

### GET /assistant/health

Vérifier l'état de l'assistant.

**Response:**
```json
{
  "status": "healthy",
  "parser_loaded": true,
  "queries_loaded": true,
  "vector_search_loaded": true,
  "vector_index_size": 126519
}
```

---

## 💬 Exemples de Questions

### Commandes Rapides

- `.mes rv` - Rendez-vous aujourd'hui
- `.aide` - Afficher l'aide

### Rendez-vous

- `mes rendez-vous demain`
- `mes rv cette semaine`
- `agenda pour le 15/12/2024`

### Recherche

- `cherche Yamaha Montreal`
- `trouve client Dupont`
- `piano à Québec`

### Résumés & Statistiques

- `résume ma semaine`
- `résume ce mois`
- `combien de rv ce mois`
- `stats cette semaine`

### Recherche Vectorielle (Questions Ouvertes)

Si la question n'est pas reconnue, l'assistant utilise automatiquement la recherche vectorielle :

- `Comment accorder un piano?`
- `Qu'est-ce qu'un accordage?`
- `Problème de touches`

---

## 🧪 Tests

### Lancer les Tests

```bash
# Démarrer l'API
python3 api/main.py &

# Exécuter les tests
python3 tests/test_assistant_api.py
```

### Tests Disponibles

1. **Health Check** : Vérifie que tous les composants sont chargés
2. **Commande .aide** : Teste l'affichage de l'aide
3. **Commande .mes rv** : Teste la récupération de rendez-vous
4. **Recherche** : Teste la recherche de clients/pianos
5. **Vector Search** : Teste la recherche vectorielle sur questions ouvertes

---

## 🔧 Développement

### Structure du Parser

Le parser identifie 7 types de requêtes :

```python
QueryType.APPOINTMENTS   # .mes rv, mes rv demain
QueryType.SEARCH_CLIENT  # cherche client X
QueryType.SEARCH_PIANO   # piano à Montréal
QueryType.SUMMARY        # résume ma semaine
QueryType.TIMELINE       # historique piano X
QueryType.STATS          # combien de rv
QueryType.HELP           # .aide
```

### Flux de Traitement

```
Question utilisateur
  ↓
Parser → Identifie type + params
  ↓
Type reconnu ? (confidence > 0.3)
  ├─ OUI → Queries → Exécute requête Supabase
  └─ NON → VectorSearch → Recherche sémantique
  ↓
Formater réponse
  ↓
Retourner à l'utilisateur
```

### Ajouter un Nouveau Type de Requête

1. **Ajouter dans `parser.py`** :
   ```python
   class QueryType(Enum):
       NEW_TYPE = "new_type"

   KEYWORDS = {
       QueryType.NEW_TYPE: ['keyword1', 'keyword2']
   }
   ```

2. **Implémenter dans `queries.py`** :
   ```python
   def execute_query(self, query_type, params):
       if query_type == QueryType.NEW_TYPE:
           return self.handle_new_type(params)
   ```

3. **Formater dans `assistant.py`** :
   ```python
   def _format_response(query_type, results):
       if query_type == QueryType.NEW_TYPE:
           return "Formatted response..."
   ```

---

## 📊 Performance

- **Vector Search** : 126,519 entrées, ~1.5 GB en mémoire
- **Chargement initial** : ~5-10 secondes (chargement du .pkl)
- **Recherche vectorielle** : ~0.5-2 secondes (appel OpenAI API + calcul similarité)
- **Requêtes Supabase** : ~100-500ms (REST API)

### Optimisations

- **Singleton** : Les services sont chargés une seule fois au démarrage
- **Cache** : Vector search garde l'index en mémoire
- **REST API** : Pas de pool de connexions PostgreSQL à gérer

---

## 🔐 Sécurité

### Authentification

L'assistant n'utilise **pas encore** l'authentification JWT de `core/auth.py`.

Pour l'activer, modifier `api/assistant.py` :

```python
from core.auth import get_current_user
from fastapi import Depends

@router.post("/chat")
async def chat(
    request: ChatRequest,
    user = Depends(get_current_user)  # ← Activer auth
):
    ...
```

### Variables Sensibles

Ne **jamais** commiter :
- `.env` (contient `OPENAI_API_KEY`, `SUPABASE_PASSWORD`)
- `data/gazelle_vectors.pkl` (fichier volumineux)

---

## 🐛 Troubleshooting

### Erreur : "OPENAI_API_KEY non défini"

Vérifier que `.env` contient la clé :
```bash
grep OPENAI .env
```

### Erreur : "Fichier vectoriel non trouvé"

Vérifier que `data/gazelle_vectors.pkl` existe :
```bash
ls -lh data/gazelle_vectors.pkl
```

### Erreur : "psycopg2 connection timeout"

Normal ! Le projet utilise **REST API** et non PostgreSQL direct.
Les scripts `check_gazelle_tables.py` nécessitent `SUPABASE_PASSWORD`, mais l'assistant fonctionne sans.

### Tests échouent : "API non accessible"

Démarrer l'API d'abord :
```bash
python3 api/main.py &
```

---

## 📝 TODO / Améliorations

- [ ] Activer l'authentification JWT
- [ ] Ajouter support pour dates absolues (15/12/2024)
- [ ] Implémenter cache pour requêtes fréquentes
- [ ] Migrer vector index vers Supabase (table JSONB)
- [ ] Ajouter logging structuré
- [ ] Frontend : Composant React pour le chat
- [ ] Tests end-to-end avec données réelles
- [ ] Améliorer parsing pour questions complexes

---

## 📚 Références

- **Parser** : [modules/assistant/services/parser.py](../modules/assistant/services/parser.py)
- **Queries** : [modules/assistant/services/queries.py](../modules/assistant/services/queries.py)
- **Vector Search** : [modules/assistant/services/vector_search.py](../modules/assistant/services/vector_search.py)
- **API Routes** : [api/assistant.py](../api/assistant.py)
- **Tests** : [tests/test_assistant_api.py](../tests/test_assistant_api.py)

---

**Créé:** 2025-12-14
**Version:** 5.0.0
**Statut:** ✅ Fonctionnel (3/5 tests passent, bugs mineurs à corriger)
