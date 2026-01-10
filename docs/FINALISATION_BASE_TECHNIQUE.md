# Finalisation Base Technique - Checklist

## 🎯 Objectif

Finaliser les 3 actions techniques critiques pour garantir:
1. Stockage CoreDateTime complet (UTC)
2. Sync avec `allEventsBatched` et conversion timezone
3. UPSERT activé partout (zéro doublon)

## ✅ Status des Actions

### 1️⃣ Migration SQL: Ajouter start_datetime

**Fichier:** `scripts/migrations/add_start_datetime_to_appointments.sql`

**Status:** ⏳ **À EXÉCUTER MANUELLEMENT**

**Instructions:**
1. Va sur: https://supabase.com/dashboard/project/beblgzvmjqkcillmcavk/sql/new
2. Copie le SQL ci-dessous
3. Clique "Run"

```sql
-- Migration: Ajouter colonne start_datetime (CoreDateTime) à gazelle_appointments
-- Date: 2026-01-09
-- Objectif: Stocker le CoreDateTime complet avec timezone pour précision maximale

-- Ajouter la nouvelle colonne
ALTER TABLE gazelle_appointments
ADD COLUMN IF NOT EXISTS start_datetime TIMESTAMPTZ;

-- Créer un index pour les requêtes par date
CREATE INDEX IF NOT EXISTS idx_gazelle_appointments_start_datetime
ON gazelle_appointments(start_datetime);

-- Mettre à jour les valeurs existantes depuis created_at (si disponible)
UPDATE gazelle_appointments
SET start_datetime = created_at
WHERE start_datetime IS NULL AND created_at IS NOT NULL;

-- Commentaires
COMMENT ON COLUMN gazelle_appointments.start_datetime IS 'CoreDateTime complet avec timezone (UTC) - plus précis que appointment_date + appointment_time séparés';

-- Note: Les colonnes appointment_date et appointment_time sont conservées pour compatibilité
-- mais start_datetime est la source de vérité pour toutes les opérations timezone-aware
```

**Validation:**
```bash
python3 scripts/validate_appointments_table.py
```

**Résultat attendu:**
```
✅ UPSERT avec external_id: OUI
✅ Colonne start_datetime:  OUI  ← Doit passer de NON à OUI
```

---

### 2️⃣ Update sync_to_supabase.py

**Fichier:** `modules/sync_gazelle/sync_to_supabase.py`

**Status:** ✅ **DÉJÀ FAIT**

**Vérifications effectuées:**

✅ **Import des fonctions timezone:**
```python
from core.timezone_utils import (
    format_for_gazelle_filter,      # Conversion Montreal → UTC
    parse_gazelle_datetime,          # Parser CoreDateTime Gazelle
    format_for_supabase,             # Formater pour stockage UTC
    extract_date_time                # Extraire date/heure Montreal
)
```

✅ **Conversion dates pour filtres API (ligne 397, 402):**
```python
# Conversion Montreal → UTC pour filtre API
start_dt = datetime.now() - timedelta(days=7)
effective_start_date = format_for_gazelle_filter(start_dt)
# Résultat: "2026-01-09T05:00:00Z" (00:00 EST = 05:00 UTC)
```

✅ **Parsing CoreDateTime Gazelle (ligne 442-447):**
```python
dt_parsed = parse_gazelle_datetime(start_time)
if dt_parsed:
    appointment_date, appointment_time = extract_date_time(dt_parsed)
    start_time_utc = format_for_supabase(dt_parsed)
```

✅ **Stockage avec start_datetime (ligne 494):**
```python
appointment_record = {
    'start_datetime': start_time_utc,  # CoreDateTime complet (UTC)
    'appointment_date': appointment_date,
    'appointment_time': appointment_time,
    'created_at': start_time_utc,
    'updated_at': format_for_supabase(datetime.now())
}
```

✅ **Utilisation allEventsBatched (commentaire ligne 787):**
```python
# 4. Appointments (utilise maintenant allEventsBatched de V4)
self.sync_appointments()
```

**Query GraphQL confirmée dans `core/gazelle_api_client.py` (ligne 449):**
```graphql
allEventsBatched(first: $first, after: $after, filters: $filters) {
    nodes {
        id
        title
        start
        duration
        ...
    }
}
```

---

### 3️⃣ UPSERT Activé Partout

**Fichier:** `modules/sync_gazelle/sync_to_supabase.py`

**Status:** ✅ **DÉJÀ FAIT**

**Tables avec UPSERT:**

| Table | Ligne | Clé Unique | Status |
|-------|-------|------------|--------|
| `gazelle_clients` | 151 | `external_id` | ✅ Activé |
| `gazelle_contacts` | 248 | `external_id` | ✅ Activé |
| `gazelle_pianos` | 328 | `external_id` | ✅ Activé |
| `gazelle_appointments` | 505 | `external_id` | ✅ Activé |
| `gazelle_timeline_entries` | 661 | `external_id` | ✅ Activé |
| `users` | 738 | `gazelle_user_id` | ✅ Activé |

**Pattern UPSERT utilisé:**
```python
url = f"{self.storage.api_url}/gazelle_appointments?on_conflict=external_id"
headers = self.storage._get_headers()
headers["Prefer"] = "resolution=merge-duplicates"

response = requests.post(url, headers=headers, json=appointment_record)
```

**Comportement:**
- Si `external_id` existe → **UPDATE** (écrase)
- Si `external_id` n'existe pas → **INSERT** (crée)
- **Aucun doublon possible**

---

## 🧪 Tests Complets

### Test Automatisé

```bash
python3 scripts/test_complete_system.py
```

**Tests effectués:**
1. ✅ Migration SQL exécutée (colonne start_datetime existe)
2. ✅ UPSERT fonctionne (aucun doublon)
3. ✅ Conversion timezone correcte
4. ℹ️  Instructions sync complète

**Résultat attendu si tout OK:**
```
🎉 TOUS LES TESTS PASSENT!

✅ Le système est prêt:
   • Migration SQL exécutée
   • UPSERT activé (aucun doublon)
   • Conversions timezone correctes

🚀 Prochaine étape:
   Lancer une sync complète:
   python3 modules/sync_gazelle/sync_to_supabase.py
```

---

## 🚀 Sync Complète de Test

Après validation des tests:

```bash
python3 modules/sync_gazelle/sync_to_supabase.py
```

**Ce qui sera synchronisé:**
- Users/Techniciens
- Clients
- Contacts
- Pianos
- **Appointments (7 derniers jours)** avec `start_datetime` UTC
- **Timeline (30 derniers jours)** avec `occurred_at` UTC

**Durée estimée:** 2-5 minutes

**Logs en temps réel:**
```
🔄 SYNCHRONISATION GAZELLE → SUPABASE
======================================================================
📅 Date: 2026-01-09 14:30:00
======================================================================

👥 Synchronisation des techniciens (users)...
📥 5 utilisateurs récupérés depuis l'API
✅ 5 techniciens synchronisés

📋 Synchronisation des clients...
📥 850 clients récupérés depuis l'API
✅ 850 clients synchronisés

📆 Synchronisation des rendez-vous...
🔄 Sync incrémental SÉCURISÉE: derniers 7 jours
   📍 Depuis: 2026-01-02 Montreal → 2026-01-02T05:00:00Z UTC
📥 45 rendez-vous récupérés depuis l'API
✅ 45 rendez-vous synchronisés

📖 Synchronisation timeline (fenêtre glissante 30 jours)...
   📍 Cutoff: 2025-12-10 Montreal → 2025-12-10T05:00:00Z UTC
📥 123 timeline entries reçues de l'API
✅ 123 timeline entries synchronisées

======================================================================
✅ SYNCHRONISATION TERMINÉE
======================================================================
⏱️  Durée: 180.45s

📊 Résumé:
   • Clients:      850 synchronisés, 0 erreurs
   • Contacts:     1200 synchronisés, 0 erreurs
   • Pianos:       2100 synchronisés, 0 erreurs
   • RV:           45 synchronisés, 0 erreurs
   • Timeline:     123 synchronisés, 0 erreurs
======================================================================
```

---

## 📊 Vérification Post-Sync

### Dans Dashboard Supabase

1. **Notifications → Tâches & Imports:**
   - Vérifier log de sync
   - Status: ✅ Succès
   - Tables modifiées: appointments (45), timeline (123), etc.

2. **SQL Editor - Vérifier données:**

```sql
-- Vérifier start_datetime est rempli
SELECT
    external_id,
    title,
    start_datetime,
    appointment_date,
    appointment_time
FROM gazelle_appointments
WHERE start_datetime IS NOT NULL
ORDER BY start_datetime DESC
LIMIT 10;
```

**Résultat attendu:**
- `start_datetime` format: `2026-01-09 19:30:00+00`
- Timezone: `+00` (UTC)

3. **Vérifier conversion timezone:**

```sql
SELECT
    external_id,
    start_datetime,
    start_datetime AT TIME ZONE 'America/Montreal' as montreal_time,
    appointment_date,
    appointment_time
FROM gazelle_appointments
WHERE start_datetime IS NOT NULL
LIMIT 5;
```

**Validation:**
- `start_datetime`: 19:30:00+00 (UTC)
- `montreal_time`: 14:30:00 (EST)
- `appointment_date`: 2026-01-09
- `appointment_time`: 14:30:00

Si tout correspond → ✅ **Conversion timezone correcte**

4. **Vérifier aucun doublon:**

```sql
SELECT
    external_id,
    COUNT(*) as count
FROM gazelle_appointments
GROUP BY external_id
HAVING COUNT(*) > 1;
```

**Résultat attendu:** `0 rows` (aucun doublon)

---

## ✅ Checklist Finale

Avant de considérer la base technique finalisée:

- [ ] **Migration SQL exécutée** (Dashboard Supabase)
  - [ ] Colonne `start_datetime TIMESTAMPTZ` créée
  - [ ] Index `idx_gazelle_appointments_start_datetime` créé

- [ ] **Tests passés**
  - [ ] `python3 scripts/test_complete_system.py` → ✅ Tous PASSÉS

- [ ] **Sync complète réussie**
  - [ ] `python3 modules/sync_gazelle/sync_to_supabase.py` → ✅ Succès
  - [ ] Log dans Dashboard → Status ✅
  - [ ] Données visibles dans tables Supabase

- [ ] **Validations post-sync**
  - [ ] `start_datetime` rempli pour tous les appointments
  - [ ] Format UTC correct (`+00` timezone)
  - [ ] Conversion Montreal ↔ UTC correcte
  - [ ] Aucun doublon (`GROUP BY external_id HAVING COUNT(*) > 1` → 0 rows)

---

## 🎉 Résultat Final

Une fois toutes les cases cochées:

✅ **Base technique finalisée:**
- CoreDateTime complet avec timezone (UTC)
- UPSERT activé partout (zéro doublon)
- Conversions timezone automatiques
- Sync avec `allEventsBatched`
- Logging complet dans Dashboard

🚀 **Prêt pour:**
- Alertes maintenance Timeline (prochaine étape)
- Workflows automatisés (GitHub Actions)
- Production stable

---

## 📚 Références

- [TIMEZONE_AND_DEDUPLICATION.md](TIMEZONE_AND_DEDUPLICATION.md) - Doc complète optimisations
- [MIGRATION_START_DATETIME.md](MIGRATION_START_DATETIME.md) - Guide migration SQL
- [core/timezone_utils.py](../core/timezone_utils.py) - Utilitaires timezone
- [modules/sync_gazelle/sync_to_supabase.py](../modules/sync_gazelle/sync_to_supabase.py) - Script sync
