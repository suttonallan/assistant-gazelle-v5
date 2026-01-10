# Migration: Ajouter start_datetime à gazelle_appointments

## 🎯 Objectif

Ajouter la colonne `start_datetime TIMESTAMPTZ` à la table `gazelle_appointments` pour stocker le CoreDateTime complet avec timezone (UTC).

## ✅ Validation Pré-Migration

**Status:** ✅ UPSERT fonctionne | ❌ Colonne start_datetime manquante

```bash
python3 scripts/validate_appointments_table.py
```

**Résultats actuels:**
- ✅ UPSERT avec `external_id`: **OUI** (clé unique confirmée)
- ❌ Colonne `start_datetime`: **NON** (doit être créée)
- 📦 Enregistrements: 0 (table vide, normal avant première sync)

## 🔧 Exécution de la Migration

### Option 1: Via Dashboard Supabase (RECOMMANDÉ)

1. **Ouvrir le Dashboard Supabase:**
   - URL: https://supabase.com/dashboard/project/beblgzvmjqkcillmcavk/sql

2. **Créer une nouvelle query:**
   - Cliquer sur "New Query" en haut à droite
   - Ou utiliser le raccourci: Ctrl/Cmd + Enter

3. **Copier le SQL:**
   - Ouvrir: `scripts/migrations/add_start_datetime_to_appointments.sql`
   - Copier tout le contenu (lignes 1-23)

4. **Exécuter:**
   - Coller dans l'éditeur SQL
   - Cliquer sur "Run" (ou Ctrl/Cmd + Enter)
   - Attendre la confirmation "Success"

### Option 2: Via psql (Si accès direct)

```bash
# Se connecter à Supabase
psql "postgresql://postgres:[PASSWORD]@db.beblgzvmjqkcillmcavk.supabase.co:5432/postgres"

# Exécuter la migration
\i scripts/migrations/add_start_datetime_to_apartments.sql
```

## 📋 Contenu de la Migration

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
```

## ✅ Validation Post-Migration

Après exécution, re-valider la structure:

```bash
python3 scripts/validate_appointments_table.py
```

**Résultats attendus:**
```
✅ UPSERT avec external_id: OUI
✅ Colonne start_datetime:  OUI  ← Doit passer à OUI
📦 Enregistrements:         0
```

**Message de succès attendu:**
```
🎉 LA TABLE EST PRÊTE À RECEVOIR DES DONNÉES UTC!
```

## 🧪 Test Après Migration

### Test 1: Insérer un enregistrement test

```sql
INSERT INTO gazelle_appointments (
    external_id,
    title,
    start_datetime,
    status,
    created_at
) VALUES (
    'evt_test_utc_2026',
    'Test CoreDateTime UTC',
    '2026-01-09T19:30:00Z',  -- 19:30 UTC = 14:30 EST
    'scheduled',
    NOW()
);
```

### Test 2: Vérifier le timezone

```sql
SELECT
    external_id,
    start_datetime,
    start_datetime AT TIME ZONE 'America/Montreal' as montreal_time,
    EXTRACT(TIMEZONE FROM start_datetime) as tz_offset
FROM gazelle_appointments
WHERE external_id = 'evt_test_utc_2026';
```

**Résultat attendu:**
```
external_id          | start_datetime           | montreal_time            | tz_offset
---------------------|--------------------------|--------------------------|----------
evt_test_utc_2026   | 2026-01-09 19:30:00+00   | 2026-01-09 14:30:00      | 0
```

- `tz_offset = 0` confirme stockage en UTC
- `montreal_time = 14:30` confirme conversion correcte (19:30 UTC - 5h = 14:30 EST)

### Test 3: Nettoyer

```sql
DELETE FROM gazelle_appointments WHERE external_id = 'evt_test_utc_2026';
```

## 🚀 Prochaines Étapes

Après validation post-migration:

1. **Lancer une synchronisation complète:**
   ```bash
   python3 modules/sync_gazelle/sync_to_supabase.py
   ```

2. **Vérifier les données dans Dashboard:**
   - Notifications → Tâches & Imports → Historique
   - Vérifier statut "✅ Succès"

3. **Inspecter les données synchronisées:**
   ```sql
   SELECT
       external_id,
       title,
       start_datetime,
       appointment_date,
       appointment_time
   FROM gazelle_appointments
   ORDER BY start_datetime DESC
   LIMIT 10;
   ```

4. **Valider conversions timezone:**
   ```sql
   SELECT
       COUNT(*) as total,
       COUNT(start_datetime) as with_start_datetime,
       COUNT(appointment_date) as with_appointment_date
   FROM gazelle_appointments;
   ```

   **Résultat attendu:**
   - `with_start_datetime` doit égaler `total` (tous remplis)
   - Format: `2026-01-09T19:30:00Z` (UTC avec 'Z')

## ⚠️ Troubleshooting

### Erreur: "relation gazelle_appointments does not exist"

**Cause:** Table pas encore créée
**Solution:** Vérifier schéma Supabase, créer table d'abord

### Erreur: "column start_datetime already exists"

**Cause:** Migration déjà exécutée
**Solution:** Normal si re-exécution, utiliser `IF NOT EXISTS` (déjà inclus)

### Erreur: "permission denied"

**Cause:** Clé API insuffisante
**Solution:** Utiliser Dashboard Supabase ou `service_role_key`

## 📊 Impact

### Avant Migration
- Stockage: `appointment_date` (date) + `appointment_time` (time) séparés
- Timezone: Ambiguë (assumée Montreal mais non explicite)
- Précision: Limitée

### Après Migration
- Stockage: `start_datetime` (timestamptz) complet
- Timezone: Explicite UTC avec 'Z'
- Précision: Maximale (microseconde + timezone)
- Compatibilité: Colonnes legacy conservées

## 📚 Références

- Migration SQL: [scripts/migrations/add_start_datetime_to_appointments.sql](../scripts/migrations/add_start_datetime_to_appointments.sql)
- Validation: [scripts/validate_appointments_table.py](../scripts/validate_appointments_table.py)
- Documentation: [TIMEZONE_AND_DEDUPLICATION.md](TIMEZONE_AND_DEDUPLICATION.md)
- Module timezone: [core/timezone_utils.py](../core/timezone_utils.py)
