# Assistant Gazelle V6

**Architecture industrielle de nouvelle génération**

## 📁 Structure du Projet

```
v6/
├── docs/
│   └── STRATEGIE_V6.md          # Document maître d'architecture
│
├── gazelle-fetcher/             # Pilier 1: Extraction
│   ├── fetchers/                # Un fetcher par type de données
│   │   ├── __init__.py
│   │   ├── base_fetcher.py      # Classe abstraite
│   │   ├── client_fetcher.py
│   │   ├── piano_fetcher.py
│   │   ├── timeline_fetcher.py
│   │   └── user_fetcher.py
│   ├── core/
│   │   ├── graphql_client.py    # Client GraphQL réutilisable
│   │   ├── rate_limiter.py      # Respect limites API Gazelle
│   │   └── token_manager.py     # Gestion OAuth
│   └── output/
│       └── raw_data/            # JSON brut (gitignored)
│
├── reconciler/                  # Pilier 3: Transformation
│   ├── matchers/
│   │   ├── user_matcher.py      # Matching users
│   │   ├── client_matcher.py
│   │   └── piano_matcher.py
│   ├── transformers/
│   │   ├── timeline_transformer.py
│   │   └── measurement_transformer.py
│   ├── rules/
│   │   ├── validation_rules.py  # Règles métier
│   │   └── business_rules.py
│   └── fallbacks/
│       └── orphan_handler.py    # Gestion données orphelines
│
├── staging/                     # Pilier 2: Zone de transit
│   └── migrations/              # Migrations SQL staging tables
│       ├── 001_create_staging_tables.sql
│       └── 002_create_sync_status.sql
│
├── monitoring/                  # Pilier 4: Observabilité
│   ├── dashboard.py             # Dashboard simple
│   ├── metrics.py               # Collecte métriques
│   └── alerts.py                # Système d'alertes
│
├── tests/
│   ├── unit/                    # Tests unitaires
│   ├── integration/             # Tests d'intégration
│   └── e2e/                     # Tests end-to-end
│
└── scripts/
    ├── setup_v6.sh              # Setup initial
    ├── migrate_v5_to_v6.py      # Migration données V5
    └── run_sync.py              # Point d'entrée principal
```

## 🚀 Quick Start

### 1. Setup Environnement
```bash
cd v6
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Créer Tables Staging
```bash
psql $DATABASE_URL < staging/migrations/001_create_staging_tables.sql
```

### 3. Tester Fetcher
```bash
python -m gazelle-fetcher.fetchers.timeline_fetcher
# Résultat: output/raw_data/timeline_YYYYMMDD.json
```

### 4. Lancer Sync Complète
```bash
python scripts/run_sync.py --module timeline
```

## 📊 Monitoring

### Dashboard Simple
```bash
python monitoring/dashboard.py
# Ouvre http://localhost:8080
```

### Métriques API
```bash
curl http://localhost:8080/api/v6/health
```

## 🧪 Tests

```bash
# Tests unitaires
pytest tests/unit/

# Tests d'intégration
pytest tests/integration/

# Tests E2E (nécessite Supabase actif)
pytest tests/e2e/
```

## 📖 Documentation

- [Stratégie V6](docs/STRATEGIE_V6.md) - Architecture complète
- [Guide Migration](docs/MIGRATION_V5_V6.md) - Passer de V5 à V6
- [API Reference](docs/API_REFERENCE.md) - Documentation API

## 🔧 Développement

### Ajouter un Nouveau Module

1. Créer le fetcher:
```python
# gazelle-fetcher/fetchers/my_module_fetcher.py
from .base_fetcher import BaseFetcher

class MyModuleFetcher(BaseFetcher):
    def fetch(self):
        # Votre logique ici
        pass
```

2. Créer table staging:
```sql
-- staging/migrations/00X_add_my_module.sql
CREATE TABLE stg_my_module (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    raw_data JSONB NOT NULL,
    processed BOOLEAN DEFAULT FALSE
);
```

3. Créer transformer:
```python
# reconciler/transformers/my_module_transformer.py
def transform(raw_data):
    # Transformation staging → production
    return cleaned_data
```

4. Ajouter au pipeline:
```python
# scripts/run_sync.py
MODULES = [..., 'my_module']
```

## 🎯 Principes V6

1. **Jamais échouer silencieusement** - Toutes les erreurs sont loggées et tracées
2. **Idempotence** - Exécuter 10x = même résultat qu'1x
3. **Observabilité** - Dashboard en temps réel obligatoire
4. **Tests automatiques** - Pas de merge sans tests verts
5. **Documentation vivante** - Code = documentation

## 📞 Support

Questions? Voir [STRATEGIE_V6.md](docs/STRATEGIE_V6.md) section "Leçons Apprises"
