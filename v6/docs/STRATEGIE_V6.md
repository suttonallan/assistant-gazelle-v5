# Stratégie Architecture V6 - Assistant Gazelle
**Date:** 28 décembre 2025
**Status:** Draft Initial
**Objectif:** Architecture industrielle 100% fiable, maintenable, extensible

---

## 🎯 Philosophie: De "Bricolage" à "Système Industriel"

### Problèmes Actuels (V5)
1. **Logique mélangée** - Fetch + Transform + Load dans un seul fichier
2. **Erreurs silencieuses** - FK violations bloquent tout, difficile à debugger
3. **Sync "tout ou rien"** - Fenêtre temporelle arbitraire (15/30 jours)
4. **Pas d'observabilité** - print() statements, aucun dashboard
5. **Couplage fort** - Impossible de changer une partie sans tout casser

### Vision V6
> **"Chaque composant fait UNE chose, et la fait parfaitement"**

---

## 🏗️ Architecture: Les 4 Piliers

### Pilier 1: EXTRACTEUR ISOLÉ (The Fetcher)
**Responsabilité:** Parler à Gazelle, rien d'autre

```
gazelle-fetcher/
├── fetchers/
│   ├── client_fetcher.py
│   ├── piano_fetcher.py
│   ├── timeline_fetcher.py
│   └── user_fetcher.py
├── core/
│   ├── graphql_client.py      # GraphQL pur
│   ├── rate_limiter.py        # Gestion API limits
│   └── token_manager.py       # OAuth refresh
└── output/
    └── raw_data/              # JSON brut, aucune transformation
```

**Caractéristiques:**
- ✅ **Aucune dépendance Supabase** - Ne sait même pas que Supabase existe
- ✅ **Validation minimaliste** - "Gazelle a répondu? OK, on sauvegarde"
- ✅ **Reprise sur échec** - Checkpoints automatiques (page 47/100 échouée? On reprend à 47)
- ✅ **Format standardisé** - Toujours du JSON avec metadata (timestamp, version API, etc.)

**Tests:**
```bash
# Le fetcher doit pouvoir tourner SEUL
python -m fetchers.timeline_fetcher --output raw_data/timeline.json
# Résultat: 1 fichier JSON, rien dans Supabase
```

---

### Pilier 2: ZONE DE TRANSIT (Staging Area)

**Responsabilité:** Accepter TOUT, jamais rejeter

```sql
-- Tables Staging (préfixe stg_)
CREATE TABLE stg_timeline_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    raw_data JSONB NOT NULL,              -- Données brutes Gazelle
    fetched_at TIMESTAMPTZ DEFAULT NOW(),
    processed BOOLEAN DEFAULT FALSE,
    processing_attempts INT DEFAULT 0,
    last_error TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes pour performance
CREATE INDEX idx_stg_timeline_processed ON stg_timeline_entries(processed);
CREATE INDEX idx_stg_timeline_fetched ON stg_timeline_entries(fetched_at DESC);
```

**Règles:**
- ✅ **Accepte même les données invalides** - On log, on n'arrête jamais
- ✅ **Idempotent** - Même entrée 10 fois = 1 seul record
- ✅ **Traçabilité totale** - On sait quand, d'où, combien de tentatives
- ✅ **Purge automatique** - Les données > 30 jours processed=true sont archivées

---

### Pilier 3: MOTEUR DE RÉCONCILIATION (The Matcher)

**Responsabilité:** Transformer Staging → Production sans jamais échouer

```
reconciler/
├── matchers/
│   ├── user_matcher.py        # usr_XXX → users.id
│   ├── client_matcher.py      # cln_XXX → clients.id
│   └── piano_matcher.py       # pno_XXX → pianos.id
├── transformers/
│   ├── timeline_transformer.py
│   └── measurement_transformer.py
├── rules/
│   ├── validation_rules.py
│   └── business_rules.py
└── fallbacks/
    └── orphan_handler.py      # Que faire si user inconnu?
```

**Logique de Réconciliation (Exemple: Users):**
```python
def reconcile_user(gazelle_user_id: str) -> str:
    """
    Retourne TOUJOURS un user_id valide, jamais None.
    """
    # 1. Chercher dans users table
    user = db.query("SELECT id FROM users WHERE id = ?", gazelle_user_id)
    if user:
        return user.id

    # 2. Créer un placeholder
    placeholder = db.insert("users", {
        'id': gazelle_user_id,
        'first_name': 'Inconnu',
        'last_name': f'({gazelle_user_id})',
        'is_placeholder': True  # Flag pour admin
    })

    # 3. Notifier admin
    notify_admin(f"Nouveau technicien détecté: {gazelle_user_id}")

    return placeholder.id
```

**Résultat:** Aucune FK violation possible, l'import ne peut jamais échouer.

---

### Pilier 4: OBSERVABILITÉ (Monitoring)

**Responsabilité:** Répondre aux 3 questions critiques

```sql
CREATE TABLE sync_status (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sync_type TEXT NOT NULL,              -- 'timeline', 'clients', etc.
    started_at TIMESTAMPTZ NOT NULL,
    completed_at TIMESTAMPTZ,
    status TEXT NOT NULL,                 -- 'running', 'success', 'failed'

    -- Métriques
    records_fetched INT DEFAULT 0,
    records_processed INT DEFAULT 0,
    records_skipped INT DEFAULT 0,
    records_failed INT DEFAULT 0,

    -- Santé
    error_rate FLOAT,                     -- % d'erreurs
    data_freshness_score FLOAT,           -- 0-100%

    -- Debug
    error_summary JSONB,
    performance_metrics JSONB,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Dashboard query
SELECT
    sync_type,
    MAX(completed_at) as last_success,
    COUNT(*) FILTER (WHERE status='failed') as failures_24h,
    AVG(data_freshness_score) as avg_freshness
FROM sync_status
WHERE created_at > NOW() - INTERVAL '24 hours'
GROUP BY sync_type;
```

**Dashboard Simple (API Endpoint):**
```json
GET /api/v6/health

{
  "timeline": {
    "last_sync": "2025-12-28T15:30:00Z",
    "freshness": 98.5,
    "status": "healthy",
    "records_pending": 3
  },
  "clients": {
    "last_sync": "2025-12-28T12:00:00Z",
    "freshness": 100,
    "status": "healthy",
    "records_pending": 0
  }
}
```

---

## 🔄 Pipeline de Données V6

```
┌─────────────────────────────────────────────────────────────┐
│  ÉTAPE 1: EXTRACTION                                        │
│  gazelle-fetcher → raw_data/*.json                          │
│  • Aucune transformation                                    │
│  • Rate limiting automatique                                │
│  • Reprise sur échec                                        │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  ÉTAPE 2: STAGING                                           │
│  raw_data/*.json → stg_* tables                             │
│  • Accepte tout (même invalide)                             │
│  • Détection de doublons                                    │
│  • Flag processed=false                                     │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  ÉTAPE 3: RÉCONCILIATION                                    │
│  stg_* → production tables (clients, pianos, etc.)          │
│  • Matching intelligent (fuzzy, levenshtein)                │
│  • Création de placeholders si besoin                       │
│  • Jamais d'échec (fallback toujours)                       │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  ÉTAPE 4: MONITORING                                        │
│  sync_status table + dashboard                              │
│  • Métriques temps réel                                     │
│  • Alertes automatiques (Slack, Email)                      │
│  • Rapports quotidiens                                      │
└─────────────────────────────────────────────────────────────┘
```

---

## 📊 Tables de Production (Schéma Unifié)

### Principes de Design
1. **IDs Gazelle partout** - Fini les UUIDs, on utilise les IDs natifs de Gazelle
2. **Soft deletes** - Jamais de DELETE, toujours `deleted_at`
3. **Audit trail** - Toutes les tables ont `created_at`, `updated_at`, `synced_at`
4. **Versioning** - Champ `version` pour détecter les changements

```sql
-- Exemple: Table users (techniciens)
CREATE TABLE users (
    id TEXT PRIMARY KEY,                  -- usr_ofYggsCDt2JAVeNP
    external_id TEXT,
    first_name TEXT,
    last_name TEXT,
    email TEXT,
    phone TEXT,
    role TEXT,
    is_placeholder BOOLEAN DEFAULT FALSE, -- Créé par réconciliation?

    -- Audit
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    synced_at TIMESTAMPTZ,                -- Dernière sync Gazelle
    deleted_at TIMESTAMPTZ,               -- Soft delete

    -- Métadata
    version INT DEFAULT 1,
    raw_data JSONB                        -- Backup des données Gazelle brutes
);

-- Trigger auto-update
CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
```

---

## 🚀 Stratégie de Synchronisation

### Mode Incrémental (Par Défaut)
```python
# Au lieu de "fenêtre glissante de 30 jours"
last_sync = get_last_successful_sync('timeline')
entries = fetcher.get_timeline_entries(since=last_sync)

# Avantages:
# ✅ Charge minimale API
# ✅ Sync rapide (secondes au lieu de minutes)
# ✅ Temps réel possible (toutes les 5 minutes)
```

### Mode Full Sync (Rare, Planifié)
```python
# 1x par semaine, la nuit
entries = fetcher.get_timeline_entries(full=True)

# Use case:
# - Détecter suppressions Gazelle
# - Corriger inconsistances
# - Audit de santé
```

### Mode Réparation (Manuel)
```python
# Admin trigger pour ressync une période spécifique
entries = fetcher.get_timeline_entries(
    start='2025-12-01',
    end='2025-12-31'
)
```

---

## 🧩 Extensibilité: Ajouter un Nouveau Volet

**Exemple: Ajouter module "Facturation"**

### Étape 1: Créer le Fetcher (5 minutes)
```python
# v6/gazelle-fetcher/fetchers/invoice_fetcher.py
class InvoiceFetcher(BaseFetcher):
    def fetch(self):
        query = "query { allInvoices { ... } }"
        return self.graphql_client.query(query)
```

### Étape 2: Créer Table Staging (2 minutes)
```sql
CREATE TABLE stg_invoices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    raw_data JSONB NOT NULL,
    processed BOOLEAN DEFAULT FALSE
);
```

### Étape 3: Créer Table Production (10 minutes)
```sql
CREATE TABLE invoices (
    id TEXT PRIMARY KEY,  -- inv_XXX
    client_id TEXT REFERENCES clients(id),
    amount DECIMAL(10,2),
    -- ... autres champs
);
```

### Étape 4: Créer Reconciler (20 minutes)
```python
# v6/reconciler/transformers/invoice_transformer.py
def transform(raw_invoice):
    return {
        'id': raw_invoice['id'],
        'client_id': match_client(raw_invoice['client']),
        'amount': raw_invoice['total']
    }
```

### Étape 5: Ajouter au Pipeline (2 minutes)
```python
# v6/pipeline/main.py
SYNC_MODULES = [
    'clients',
    'pianos',
    'timeline',
    'invoices',  # ← Nouveau module
]
```

**Total: ~40 minutes pour ajouter un volet complet**

---

## 🛡️ Gestion des Erreurs (Zero Trust)

### Principe: "Jamais faire confiance, toujours vérifier"

```python
class SafeReconciler:
    def process_entry(self, raw_data):
        try:
            # Validation
            if not self.validate(raw_data):
                self.log_and_skip(raw_data, "Invalid schema")
                return

            # Transformation
            transformed = self.transform(raw_data)

            # Matching
            matched = self.match_references(transformed)

            # Insertion (avec retry)
            self.insert_with_retry(matched, max_retries=3)

        except ValidationError as e:
            # Erreur attendue: on skip, on log
            self.mark_as_skipped(raw_data, str(e))

        except DatabaseError as e:
            # Erreur DB: on retry plus tard
            self.mark_for_retry(raw_data, str(e))

        except Exception as e:
            # Erreur inattendue: on alerte
            self.alert_admin(raw_data, str(e))
            self.mark_as_failed(raw_data, str(e))
```

**Résultat:** Une erreur ne bloque JAMAIS tout le pipeline.

---

## 📈 Métriques de Succès

### KPIs V6
1. **Uptime:** 99.9% des syncs réussissent
2. **Latence:** Données Gazelle → Supabase < 5 minutes
3. **Fraîcheur:** 98%+ des données < 1h de retard
4. **Fiabilité:** 0 perte de données
5. **Observabilité:** Tout problème détectable en < 30 secondes

### Dashboard Admin
```
┌─────────────────────────────────────────────┐
│  Assistant Gazelle V6 - Santé Système      │
├─────────────────────────────────────────────┤
│  Timeline Entries    ✓ 98.5%  (5 min ago)  │
│  Clients             ✓ 100%   (1h ago)     │
│  Pianos              ✓ 99.2%  (10 min ago) │
│  Users               ⚠ 95.1%  (2h ago)     │
│                                             │
│  📊 Dernières 24h:                          │
│    • 1,847 entrées synchronisées           │
│    • 3 erreurs (0.16%)                     │
│    • 2 nouveaux techniciens détectés       │
│                                             │
│  ⚠️ Actions requises:                       │
│    • Vérifier placeholder: usr_ABC123      │
│    • Résoudre 3 timeline orphelines        │
└─────────────────────────────────────────────┘
```

---

## 🔧 Stack Technologique

### Backend
- **Python 3.11+** (async/await pour performance)
- **FastAPI** (API V6 moderne)
- **SQLAlchemy 2.0** (ORM avec type safety)
- **Pydantic V2** (Validation données)
- **Celery + Redis** (Tasks async, scheduling)

### Base de Données
- **Supabase PostgreSQL** (Production)
- **Triggers PostgreSQL** (Auto-updates, audit)
- **Partitioning** (Timeline entries par mois)

### Monitoring
- **Sentry** (Error tracking)
- **Prometheus + Grafana** (Métriques)
- **OU Simple: Table sync_status** (Commencer petit)

### CI/CD
- **GitHub Actions** (Tests automatiques)
- **Docker** (Déploiement consistant)
- **Pre-commit hooks** (Quality gates)

---

## 📅 Plan de Migration V5 → V6

### Phase 1: Fondations (Semaine 1)
- [x] Créer structure v6/
- [ ] Migrer table users (FAIT dans V5)
- [ ] Créer tables staging (stg_*)
- [ ] Créer table sync_status
- [ ] Écrire BaseFetcher (classe abstraite)

### Phase 2: Premier Module (Semaine 2)
- [ ] Timeline Fetcher complet
- [ ] Timeline Reconciler
- [ ] Tests end-to-end timeline
- [ ] Migration données V5 → V6

### Phase 3: Modules Restants (Semaine 3-4)
- [ ] Clients, Pianos, Users
- [ ] Dashboard monitoring basique
- [ ] Documentation API

### Phase 4: Production (Semaine 5)
- [ ] Tests de charge
- [ ] Déploiement staging
- [ ] Migration finale
- [ ] Rollback plan

---

## 🎓 Leçons Apprises (V5)

### ❌ Ce qui n'a PAS marché
1. **Fenêtres temporelles fixes** (15/30 jours) - Arbitraire et inefficace
2. **FK violations bloquantes** - 1 user manquant = tout casse
3. **Logs print()** - Impossible de debug en production
4. **Logique monolithique** - Sync + Transform dans 1 fichier de 800 lignes
5. **Pas de tests** - Chaque changement = roulette russe

### ✅ Ce qui a BIEN marché
1. **Gazelle IDs natifs** - Plus simple que UUIDs
2. **GraphQL pagination** - Gère bien les gros volumes
3. **Supabase RLS** - Sécurité native
4. **Structure modulaire** (core/, modules/) - Bonne base

### 🎯 Principes V6 (Non Négociables)
1. **Séparation stricte des responsabilités**
2. **Fail gracefully, jamais tout casser**
3. **Observable depuis le jour 1**
4. **Tests automatiques obligatoires**
5. **Documentation = Code (pas un PDF Word)**

---

## 🚦 Critères de Succès V6

Avant de dire "V6 est prête", on doit pouvoir répondre OUI à:

- [ ] Pipeline peut tourner 1000x sans supervision?
- [ ] Une erreur dans Timeline n'affecte pas Clients?
- [ ] Admin sait en < 1 minute si sync a échoué?
- [ ] Ajouter un nouveau module prend < 1 jour?
- [ ] Données fraîches en < 5 minutes après changement Gazelle?
- [ ] 0 perte de données même si Supabase down 1h?
- [ ] Nouveau dev comprend l'architecture en < 30 minutes?

---

## 📖 Prochaines Étapes

1. **Valider cette stratégie** avec l'équipe
2. **Créer POC** (Timeline Fetcher + Staging + Reconciler)
3. **Mesurer performance** (1000 entries en combien de temps?)
4. **Itérer** sur base de résultats réels

---

**Document vivant** - Mis à jour au fur et à mesure de l'implémentation.
