# Assistant v6 - Architecture Propre

## Les 4 Piliers Fondamentaux

### 1. Mapping Instrument-Centric
La logique Client → Pianos → Timeline est au cœur du système.
- Les notes de service sont liées aux pianos, pas aux clients
- Toute requête d'historique doit d'abord chercher les pianos du client

### 2. Parser de Priorité
Distinction claire entre passé et futur:
- **TIMELINE**: historique, notes de service, passé
- **APPOINTMENTS**: rendez-vous, calendrier, futur
- **CLIENT_INFO**: informations client, paiement
- **DEDUCTIONS**: recommandations basées sur les attributs des pianos

### 3. Déduplication Propre
Fusion intelligente des entités:
- Clé: nom normalisé (sans espaces multiples, en minuscules)
- Priorité: client > contact
- Évite les doublons à l'affichage

### 4. Connexion Supabase Directe
Accès direct aux tables via PostgREST API:
- `gazelle_timeline_entries`: historique de service
- `gazelle_pianos`: inventaire des instruments
- `gazelle_clients`: informations clients
- `gazelle_appointments`: rendez-vous futurs
- Tri sur `created_at` (puisque `occurred_at` est souvent vide)

## Tests A/B

Pour tester facilement v5 vs v6:

```python
# Dans api/main.py, ajoutez:
from assistant-v6.api.assistant_v6 import router as assistant_v6_router
app.include_router(assistant_v6_router, prefix="/v6")
```

Ensuite testez:
- **v5**: `POST http://localhost:8000/assistant/chat`
- **v6**: `POST http://localhost:8000/v6/assistant/chat`

## Structure

```
assistant-v6/
├── api/
│   └── assistant_v6.py         # Endpoint FastAPI v6
├── modules/
│   ├── assistant/
│   │   └── services/
│   │       ├── parser_v6.py    # Parser avec priorités claires
│   │       └── queries_v6.py   # Logique instrument-centric
│   └── storage/
│       └── supabase.py         # Connexion Supabase (copie de core/)
└── tests/
    └── test_queries.py         # Tests unitaires
```

## Installation

```bash
# Le v6 utilise les mêmes dépendances que v5
# Assurez-vous que SUPABASE_URL et SUPABASE_KEY sont dans .env
```

## Usage

```python
# Test direct
from assistant-v6.modules.assistant.services.queries_v6 import QueriesServiceV6

queries = QueriesServiceV6()
result = queries.execute_query("montre-moi l'historique complet de Monique Hallé avec toutes les notes de service")
print(result)
```
