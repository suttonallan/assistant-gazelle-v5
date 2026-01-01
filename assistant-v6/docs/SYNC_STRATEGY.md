# Sync Strategy - Assistant Gazelle V6

## 📋 Document "Source de Vérité"

**Objectif:** Définir la stratégie de synchronisation Gazelle → Supabase avec garanties de cohérence

**Date création:** 2025-12-29
**Dernière mise à jour:** 2025-12-29

---

## 🎯 Principe Fondamental

**Architecture 2-Stages:**
```
Gazelle API (source externe)
    ↓ Stage 1: Fetch & Store Raw
Staging Tables (backup données brutes)
    ↓ Stage 2: Reconcile & Transform
Production Tables (données normalisées)
```

**Avantages:**
- ✅ **Audit trail complet** - Toutes les données brutes préservées
- ✅ **Récupération possible** - Si Reconciler bug, on peut rejouer depuis staging
- ✅ **Débogage facile** - Comparer données brutes vs transformées
- ✅ **Rollback sécurisé** - Revenir en arrière sans re-fetch

---

## ⏰ Solution Timezone UTC (CRITIQUE)

### 🚨 Problème Résolu

**Date résolution:** 2025-12-26
**Statut:** ✅ SOLUTION VALIDÉE

Les rendez-vous de l'API Gazelle arrivent en **UTC** mais doivent s'afficher en heure de **Montréal** (America/Toronto).

**Exemple:**
- API Gazelle: `2026-01-09T12:00:00Z` (midi UTC)
- Affichage utilisateur: `07:00` (7h AM Montréal)

### ✅ Solution Finale: Stockage UTC Pur

**Règle d'or:**
> Stocker en UTC, convertir pour l'affichage.

**Architecture:**
```
API Gazelle (UTC)  →  Stockage Supabase (UTC)  →  Affichage (Montréal)
   12:00:00Z       →       12:00:00            →       07:00
```

### Code Python - Import (Stage 1)

**Fichier de référence:** `scripts/import_appointments_fixed.py`

```python
from datetime import datetime

# ✅ BON - Stockage UTC pur, AUCUNE conversion
dt_utc = datetime.fromisoformat(start_time.replace('Z', '+00:00'))

# Stocker tel quel (UTC)
appointment_date = dt_utc.date().isoformat()  # "2026-01-09"
appointment_time = dt_utc.time().isoformat()  # "12:00:00"

# IMPORTANT: Aucune compensation, aucune conversion
```

**Ce qu'on NE fait PAS:**
- ❌ Pas de `astimezone()` lors de l'import
- ❌ Pas de compensation `+ timedelta(hours=5)` ou `+ timedelta(hours=10)`
- ❌ Pas de `replace(tzinfo=...)`

### Code Python - Affichage (Frontend/API)

```python
from datetime import datetime
from zoneinfo import ZoneInfo

# Lire depuis DB (UTC)
time_utc = "12:00:00"
date = "2026-01-09"

# Convertir pour affichage Montréal
dt_utc = datetime.fromisoformat(f"{date} {time_utc}").replace(
    tzinfo=ZoneInfo('UTC')
)
dt_mtl = dt_utc.astimezone(ZoneInfo('America/Toronto'))
time_montreal = dt_mtl.strftime('%H:%M')  # "07:00"
```

### SQL - Vues avec Conversion Automatique

```sql
-- Vue pour affichage frontend
CREATE OR REPLACE VIEW v_appointments_montreal AS
SELECT
    external_id,
    appointment_date,
    appointment_time AT TIME ZONE 'UTC' AT TIME ZONE 'America/Toronto' as time_montreal,
    title,
    client_external_id
FROM gazelle_appointments;
```

### ⚠️ RÈGLES CRITIQUES

**À LIRE À CHAQUE IMPORT:**

1. **JAMAIS de trigger SQL** qui modifie les heures automatiquement
   ```sql
   -- ❌ NE JAMAIS FAIRE
   DROP TRIGGER IF EXISTS tr_fix_api_import ON public.gazelle_appointments;
   DROP FUNCTION IF EXISTS public.fn_fix_gazelle_api_time();
   ```

2. **TOUJOURS stocker UTC** dans les colonnes `TIME` ou `TIMESTAMP`
   - ✅ `appointment_time TIME` → stocke `12:00:00` (UTC)
   - ❌ Pas de colonne `appointment_time_montreal`

3. **TOUJOURS utiliser `zoneinfo`** (Python 3.9+) au lieu de `pytz`
   ```python
   # ✅ BON (moderne)
   from zoneinfo import ZoneInfo
   tz = ZoneInfo('America/Toronto')

   # ❌ ÉVITER (legacy)
   import pytz
   tz = pytz.timezone('America/Montreal')
   ```

4. **TOUJOURS tester avec "Tire le Coyote"**
   - RV test: "Tire le Coyote avant 8h" → doit afficher 07:00 Montréal
   - RV test: "Tire le Coyote à 18h" → doit afficher 18:00 Montréal

### 🧪 Validation

**Script de test:**
```python
from core.supabase_storage import SupabaseStorage
from supabase import create_client
from datetime import datetime
from zoneinfo import ZoneInfo

storage = SupabaseStorage()
supabase = create_client(storage.supabase_url, storage.supabase_key)

# Récupérer un RV de test
result = supabase.table('gazelle_appointments')\
    .select('appointment_date, appointment_time, title')\
    .ilike('title', '%Tire le Coyote%')\
    .limit(1)\
    .execute()

if result.data:
    appt = result.data[0]

    # Conversion UTC → Montréal
    dt_utc = datetime.fromisoformat(
        f"{appt['appointment_date']} {appt['appointment_time']}"
    ).replace(tzinfo=ZoneInfo('UTC'))

    dt_mtl = dt_utc.astimezone(ZoneInfo('America/Toronto'))

    print(f"Titre: {appt['title']}")
    print(f"Stocké (UTC): {appt['appointment_time']}")
    print(f"Affiché (MTL): {dt_mtl.strftime('%H:%M')}")
    # Doit afficher 07:00 ou 18:00
```

### 📚 Références

- **Document V5:** `/docs/TIMEZONE_SOLUTION_FINALE.md`
- **Script d'import:** `scripts/import_appointments_fixed.py`
- **Validation PDA:** `assistant-v6/modules/assistant/services/pda_validation.py`

---

## 🗂️ Architecture 2-Stages Détaillée

### Stage 1: Gazelle → Staging

**Responsabilité:**
Récupérer les données brutes de l'API Gazelle et les stocker telles quelles.

**Fichier:** `sync/gazelle_to_staging.py`

```python
# sync/gazelle_to_staging.py
from core.fetcher.gazelle_fetcher import GazelleFetcher
from datetime import datetime

class GazelleToStagingSync:
    """
    Stage 1: Fetch données brutes depuis Gazelle API.

    RÈGLE: Aucune transformation, stockage JSON pur.
    """

    def sync_appointments(self, since: datetime):
        """Sync rendez-vous depuis last_sync."""
        fetcher = GazelleFetcher()

        # Fetch raw data
        raw_appointments = fetcher.fetch_appointments(since)

        # Store in staging (JSON brut)
        for raw_appt in raw_appointments:
            self.staging_storage.insert('staging_appointments', {
                'external_id': raw_appt['id'],
                'raw_data': raw_appt,  # JSON complet
                'fetched_at': datetime.utcnow(),
                'sync_status': 'pending'
            })

        # ❌ PAS de transformation ici!
        return len(raw_appointments)
```

**Tables Staging:**

```sql
-- Staging table pour appointments
CREATE TABLE staging_appointments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    external_id TEXT NOT NULL,
    raw_data JSONB NOT NULL,  -- Données brutes Gazelle
    fetched_at TIMESTAMPTZ NOT NULL,
    sync_status TEXT NOT NULL,  -- 'pending' | 'processed' | 'error'
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Index pour éviter doublons
CREATE UNIQUE INDEX idx_staging_appt_external
ON staging_appointments(external_id, fetched_at);
```

### Stage 2: Staging → Production (via Reconciler)

**Responsabilité:**
Transformer les données staging en données normalisées via le Reconciler.

**Fichier:** `sync/staging_to_production.py`

```python
# sync/staging_to_production.py
from core.reconciler.appointment_reconciler import AppointmentReconciler
from core.reconciler.client_reconciler import ClientReconciler

class StagingToProductionSync:
    """
    Stage 2: Reconcile données staging → production.

    RÈGLE: Toute transformation passe par le Reconciler.
    """

    def __init__(self):
        self.client_reconciler = ClientReconciler()
        self.appt_reconciler = AppointmentReconciler()

    def process_pending_appointments(self):
        """Process tous les appointments staging en attente."""

        # Récupérer staging pending
        pending = self.staging_storage.fetch(
            'staging_appointments',
            filters={'sync_status': 'pending'}
        )

        for staging_record in pending:
            try:
                raw_data = staging_record['raw_data']

                # 1. Reconcile client (crée Client + Contact + Location)
                if raw_data.get('client_id'):
                    client_result = self.client_reconciler.reconcile_client(
                        raw_data['client']
                    )

                # 2. Reconcile appointment
                appt_result = self.appt_reconciler.reconcile_appointment(
                    raw_data,
                    client_external_id=raw_data.get('client_id')
                )

                # 3. Mark staging as processed
                self.staging_storage.update(
                    'staging_appointments',
                    staging_record['id'],
                    {'sync_status': 'processed'}
                )

            except Exception as e:
                # Log error, garde staging pour debug
                self.staging_storage.update(
                    'staging_appointments',
                    staging_record['id'],
                    {
                        'sync_status': 'error',
                        'error_message': str(e)
                    }
                )
```

**Flux Complet:**

```
1. Gazelle API
   ↓ GazelleFetcher.fetch_appointments()
2. Staging Table (raw JSONB)
   ↓ AppointmentReconciler.reconcile_appointment()
3. Production Tables
   - gazelle_appointments (normalisé)
   - gazelle_clients (si nouveau)
   - gazelle_contacts (si nouveau - V6)
   - gazelle_locations (si nouveau - V6)
```

---

## 🔄 Stratégie de Synchronisation

### Modes de Sync

#### 1. Sync Incrémental (Normal)

**Fréquence:** Toutes les 15 minutes

**Logique:**
```python
# Sync seulement les changements depuis last_sync
last_sync = get_last_sync_timestamp()
new_data = fetcher.fetch_appointments(since=last_sync)
```

**Use case:**
- Opération quotidienne
- Faible charge réseau
- Mise à jour en temps quasi-réel

#### 2. Full Sync (Initial ou Recovery)

**Fréquence:** Manuel ou 1x/jour (3h AM)

**Logique:**
```python
# Sync toutes les données (pas de since)
all_data = fetcher.fetch_appointments(since=None)
```

**Use case:**
- Premier import
- Récupération après bug
- Vérification cohérence

#### 3. Rollback & Replay

**Scénario:** Reconciler a bugé, production corrompue

**Procédure:**
```sql
-- 1. Vider production
TRUNCATE TABLE gazelle_appointments CASCADE;

-- 2. Reset staging status
UPDATE staging_appointments
SET sync_status = 'pending'
WHERE sync_status = 'processed';

-- 3. Rejouer stage 2
-- (via staging_to_production.py)
```

**Avantage:** Pas besoin de re-fetch depuis Gazelle!

---

## 🛡️ Gestion des Erreurs

### Erreurs Stage 1 (Fetch)

**Scénarios:**
- API Gazelle down
- Rate limiting
- Timeout réseau

**Stratégie:**
```python
class GazelleFetcher:
    MAX_RETRIES = 3
    RETRY_DELAY = 5  # secondes

    def fetch_with_retry(self, endpoint: str):
        for attempt in range(self.MAX_RETRIES):
            try:
                response = self.client.get(endpoint, timeout=10)
                response.raise_for_status()
                return response.json()
            except requests.exceptions.RequestException as e:
                if attempt == self.MAX_RETRIES - 1:
                    raise
                time.sleep(self.RETRY_DELAY * (attempt + 1))
```

### Erreurs Stage 2 (Reconcile)

**Scénarios:**
- Données invalides (champs manquants)
- Relations incohérentes (client_id inexistant)
- Erreurs DB (contraintes)

**Stratégie:**
```python
# Staging garde l'erreur pour inspection
{
    'sync_status': 'error',
    'error_message': 'Missing required field: client_id',
    'error_stack': traceback.format_exc()
}

# Email/Slack alert si > 10 erreurs/heure
if error_count > 10:
    send_alert("Sync errors spike detected")
```

---

## 📊 Monitoring & Observabilité

### Métriques à Tracker

```python
# sync/metrics.py
class SyncMetrics:
    """Métriques de synchronisation."""

    metrics = {
        'stage1_fetch_duration': Histogram,
        'stage1_records_fetched': Counter,
        'stage2_reconcile_duration': Histogram,
        'stage2_records_processed': Counter,
        'stage2_errors': Counter,
        'staging_backlog_size': Gauge,  # pending records
    }
```

### Dashboard Supabase

**Vue SQL:**
```sql
-- Dashboard sync status
CREATE OR REPLACE VIEW v_sync_dashboard AS
SELECT
    sync_status,
    COUNT(*) as count,
    MIN(fetched_at) as oldest_record,
    MAX(fetched_at) as newest_record
FROM staging_appointments
GROUP BY sync_status;

-- Résultat:
-- sync_status | count | oldest_record       | newest_record
-- pending     | 12    | 2025-12-29 10:00:00 | 2025-12-29 10:15:00
-- processed   | 4580  | 2025-12-01 00:00:00 | 2025-12-29 10:00:00
-- error       | 3     | 2025-12-28 14:30:00 | 2025-12-29 09:00:00
```

---

## 🚀 Migration V5 → V6

### V5 Actuel (Direct)

```python
# modules/sync_gazelle/sync_to_supabase.py (V5)
# Problème: Fetch + Transform dans même fonction
def sync_appointments():
    raw_appointments = gazelle_api.get_appointments()  # Fetch

    for raw_appt in raw_appointments:
        # Transform inline (pas réutilisable!)
        normalized = {
            'external_id': raw_appt['id'],
            'appointment_time': parse_time(raw_appt['start_time']),  # Transform
            # ... etc
        }

        supabase.insert('gazelle_appointments', normalized)  # Store
```

**Problèmes:**
- ❌ Pas de backup données brutes
- ❌ Transformation non testable seule
- ❌ Impossible de rejouer si bug

### V6 Target (2-Stages)

```python
# sync/orchestrator.py (V6)
class SyncOrchestrator:
    """Orchestre les 2 stages de sync."""

    def run_full_sync(self):
        # Stage 1: Fetch & Store Raw
        stage1 = GazelleToStagingSync()
        fetched_count = stage1.sync_appointments(since=None)

        # Stage 2: Reconcile & Transform
        stage2 = StagingToProductionSync()
        processed_count = stage2.process_pending_appointments()

        return {
            'fetched': fetched_count,
            'processed': processed_count
        }
```

**Avantages:**
- ✅ Backup automatique (staging)
- ✅ Reconciler testable isolément
- ✅ Rollback possible
- ✅ Audit trail complet

---

## 🧪 Tests de Synchronisation

### Test Stage 1 (Fetch)

```python
# tests/unit/test_gazelle_fetcher.py
def test_fetch_appointments_returns_raw_json():
    """Test que le fetcher retourne JSON brut sans transformation."""
    fetcher = GazelleFetcher()

    # Mock API response
    with patch('requests.get') as mock_get:
        mock_get.return_value.json.return_value = [
            {
                'id': 'ABC123',
                'start_time': '2026-01-09T12:00:00Z',
                'client': {'id': 'CLI456'}
            }
        ]

        result = fetcher.fetch_appointments(since=None)

        # Vérifie que c'est identique à l'API
        assert result[0]['id'] == 'ABC123'
        assert result[0]['start_time'] == '2026-01-09T12:00:00Z'  # UTC pur
```

### Test Stage 2 (Reconcile)

```python
# tests/unit/test_appointment_reconciler.py
def test_reconcile_converts_utc_time():
    """Test que le Reconciler parse correctement UTC."""
    reconciler = AppointmentReconciler()

    raw_data = {
        'id': 'ABC123',
        'start_time': '2026-01-09T12:00:00Z',
        'client_id': 'CLI456'
    }

    result = reconciler.reconcile_appointment(raw_data)

    # Vérifie stockage UTC (pas de conversion)
    assert result.appointment_time == time(12, 0, 0)  # 12:00 UTC
    assert result.appointment_date == date(2026, 1, 9)
```

### Test End-to-End

```python
# tests/integration/test_sync_e2e.py
def test_full_sync_flow():
    """Test du flux complet staging → production."""
    # 1. Insérer dans staging
    staging_storage.insert('staging_appointments', {
        'external_id': 'TEST123',
        'raw_data': {'id': 'TEST123', 'start_time': '2026-01-09T12:00:00Z'},
        'sync_status': 'pending'
    })

    # 2. Run stage 2
    sync = StagingToProductionSync()
    sync.process_pending_appointments()

    # 3. Vérifie production
    result = production_storage.fetch_one(
        'gazelle_appointments',
        {'external_id': 'TEST123'}
    )
    assert result is not None
    assert result['appointment_time'] == '12:00:00'
```

---

## 📝 Checklist Déploiement

### Avant Premier Sync V6

- [ ] Tables staging créées (`staging_appointments`, etc.)
- [ ] Trigger SQL V5 supprimé (timezone fix)
- [ ] Reconcilers testés unitairement
- [ ] Tests E2E passent
- [ ] Monitoring dashboard configuré
- [ ] Alertes Slack/Email configurées
- [ ] Backup DB pris
- [ ] Rollback plan documenté

### Premier Full Sync

```bash
# 1. Vider les anciennes données V5
TRUNCATE TABLE gazelle_appointments CASCADE;

# 2. Run sync V6
python3 sync/orchestrator.py --mode=full

# 3. Vérifier dashboard
SELECT * FROM v_sync_dashboard;

# 4. Test spot check
SELECT * FROM gazelle_appointments
WHERE appointment_date = '2026-01-09'
LIMIT 5;
```

---

## 🔗 Documents Liés

- [ARCHITECTURE_MAP.md](ARCHITECTURE_MAP.md) - Structure modules Reconciler
- [DATA_DICTIONARY.md](DATA_DICTIONARY.md) - Schéma tables staging/production
- [TIMEZONE_SOLUTION_FINALE.md](/docs/TIMEZONE_SOLUTION_FINALE.md) - Détails timezone (V5)

---

## 📐 Principes de Design

### ✅ DO (À FAIRE)

1. **Toujours passer par staging**
   - Même pour les full sync
   - Backup automatique

2. **Aucune transformation en Stage 1**
   - Fetcher retourne JSON pur
   - Staging stocke JSONB brut

3. **Toute transformation en Stage 2**
   - Via Reconciler
   - Testable isolément

4. **Stocker UTC pur**
   - Pas de conversion à l'import
   - Conversion seulement pour affichage

5. **Logger chaque erreur**
   - Garder staging pour debug
   - Alerter si spike d'erreurs

### ❌ DON'T (À ÉVITER)

1. **Pas de transformation dans le Fetcher**
   ```python
   # ❌ MAUVAIS
   def fetch_appointments(self):
       raw = api.get()
       return [self._transform(r) for r in raw]  # NON!

   # ✅ BON
   def fetch_appointments(self):
       return api.get()  # Retourne tel quel
   ```

2. **Pas de skip staging**
   ```python
   # ❌ MAUVAIS
   raw = fetcher.fetch()
   supabase.insert('gazelle_appointments', raw)  # Direct!

   # ✅ BON
   raw = fetcher.fetch()
   staging.insert('staging_appointments', raw)  # Staging d'abord
   reconciler.process_staging()  # Puis reconcile
   ```

3. **Pas de modification des heures à l'import**
   ```python
   # ❌ MAUVAIS
   dt_utc = datetime.fromisoformat(raw['start_time'])
   dt_mtl = dt_utc.astimezone(ZoneInfo('America/Toronto'))  # NON!

   # ✅ BON
   dt_utc = datetime.fromisoformat(raw['start_time'])
   # Stocker tel quel (UTC)
   ```

---

**Version:** 1.0
**Auteur:** Assistant Gazelle Team
**Prochaine révision:** Après implémentation Stage 1

**RAPPEL CRITIQUE:** Toujours lire la section "Solution Timezone UTC" avant tout import!
