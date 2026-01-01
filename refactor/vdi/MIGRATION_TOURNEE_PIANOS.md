# Migration: Table de Jonction tournee_pianos

## 📋 Résumé

Cette migration refactore le système de gestion des pianos dans les tournées pour passer d'un tableau JSONB à une vraie table relationnelle.

## 🎯 Problème Résolu

### Avant (Problématique)
```sql
tournees
--------
id          | nom        | piano_ids
"t1"        | "Hiver"    | ["piano1", "piano2", "piano3"]  -- JSONB array
"t2"        | "Été"      | ["piano4", "piano5"]
```

**Problèmes**:
- ❌ Difficile de savoir dans quelle tournée est un piano
- ❌ Pas d'ordre des pianos
- ❌ Pas de métadonnées (qui a ajouté, quand)
- ❌ Requêtes SQL complexes pour chercher dans JSON
- ❌ Performance médiocre avec beaucoup de pianos

### Après (Solution)
```sql
tournees
--------
id   | nom        | (piano_ids conservé pour rollback)
"t1" | "Hiver"    | null
"t2" | "Été"      | null

tournee_pianos (nouvelle table)
--------------
id  | tournee_id | gazelle_id | ordre | ajoute_le           | ajoute_par
1   | "t1"       | "piano1"   | 1     | 2025-01-15 10:00    | tech@example.com
2   | "t1"       | "piano2"   | 2     | 2025-01-15 10:05    | tech@example.com
3   | "t1"       | "piano3"   | 3     | 2025-01-15 10:10    | tech@example.com
4   | "t2"       | "piano4"   | 1     | 2025-01-16 09:00    | tech@example.com
5   | "t2"       | "piano5"   | 2     | 2025-01-16 09:15    | tech@example.com
```

**Avantages**:
- ✅ Requêtes SQL simples: `SELECT * FROM tournee_pianos WHERE tournee_id = 'x'`
- ✅ Recherche inverse facile: `SELECT tournee_id FROM tournee_pianos WHERE gazelle_id = 'y'`
- ✅ Ordre des pianos préservé
- ✅ Métadonnées complètes (qui, quand)
- ✅ Performance avec index
- ✅ Historique et audit trail

## 📦 Fichiers Modifiés

### 1. SQL Migration
- **`sql/003_create_tournee_pianos_junction.sql`**
  - Crée table `tournee_pianos`
  - Migre données depuis `piano_ids` JSONB
  - Ajoute index pour performance
  - Configure RLS policies
  - Fonctions helper: `count_tournee_pianos()`, `get_tournee_piano_ids()`

### 2. Types TypeScript
- **`types/supabase.types.ts`**
  - Ajout table `tournee_pianos` avec types complets
  - Fix `piano_id` → `gazelle_id` dans `vincent_dindy_piano_updates`
  - Marque `piano_ids` comme deprecated
  - Ajout types pour fonctions SQL helpers

### 3. Hooks
- **`hooks/useTournees.ts`**
  - `fetchTournees()`: Fetch pianos depuis `tournee_pianos` table
  - `addPianoToTournee()`: INSERT dans `tournee_pianos`
  - `removePianoFromTournee()`: DELETE depuis `tournee_pianos`

- **`hooks/useBatchOperations.ts`**
  - `batchAddToTournee()`: Batch UPSERT dans `tournee_pianos`

## 🚀 Exécution de la Migration

### Option 1: Via Supabase Dashboard (Recommandé)
1. Ouvrir [Supabase SQL Editor](https://supabase.com/dashboard)
2. Copier le contenu de [sql/003_create_tournee_pianos_junction.sql](sql/003_create_tournee_pianos_junction.sql)
3. Coller dans l'éditeur
4. Cliquer "Run"

### Option 2: Via Script Bash
```bash
cd refactor/vdi/sql
./run_003_migration.sh
```

## ✅ Validation Post-Migration

### 1. Vérifier la migration des données
```sql
-- Compter les tournées
SELECT COUNT(*) FROM tournees;

-- Compter les relations migrées
SELECT COUNT(*) FROM tournee_pianos;

-- Vérifier qu'une tournée spécifique a ses pianos
SELECT tp.gazelle_id, tp.ordre, tp.ajoute_le
FROM tournee_pianos tp
WHERE tp.tournee_id = 'votre_tournee_id'
ORDER BY tp.ordre;
```

### 2. Tester dans l'application
1. Créer une nouvelle tournée
2. Sélectionner des pianos et les ajouter à la tournée
3. Vérifier qu'ils apparaissent correctement
4. Retirer un piano de la tournée
5. Vérifier que le retrait fonctionne

### 3. Tester le Realtime Sync
1. Ouvrir l'app sur Mac
2. Ouvrir l'app sur iPad
3. Ajouter un piano à une tournée sur Mac
4. Vérifier qu'il apparaît instantanément sur iPad

## 🔄 Rollback (si problème)

Si vous rencontrez des problèmes, la colonne `piano_ids` est conservée:

```sql
-- Restaurer l'ancienne logique (temporaire)
-- Les données JSONB sont toujours là

-- Supprimer la nouvelle table
DROP TABLE IF EXISTS tournee_pianos CASCADE;

-- Note: Il faudra aussi reverter le code TypeScript
```

## 🗑️ Nettoyage Final (après validation)

Une fois que tout fonctionne parfaitement pendant quelques jours:

```sql
-- Supprimer l'ancienne colonne piano_ids
ALTER TABLE public.tournees DROP COLUMN piano_ids;
```

Décommenter cette ligne dans `003_create_tournee_pianos_junction.sql` (ligne 124).

## 🎨 Schéma de la Table

```
tournee_pianos
--------------
┌─────────────────────────┬──────────────┬──────────────┬────────────────────┐
│ Colonne                 │ Type         │ Null?        │ Description        │
├─────────────────────────┼──────────────┼──────────────┼────────────────────┤
│ id                      │ UUID         │ NOT NULL PK  │ Unique ID          │
│ tournee_id              │ TEXT         │ NOT NULL FK  │ → tournees.id      │
│ gazelle_id              │ TEXT         │ NOT NULL     │ ID piano Gazelle   │
│ ordre                   │ INTEGER      │ NULL         │ Ordre d'affichage  │
│ ajoute_le               │ TIMESTAMPTZ  │ NOT NULL     │ Date d'ajout       │
│ ajoute_par              │ TEXT         │ NULL         │ Email utilisateur  │
│ created_at              │ TIMESTAMPTZ  │ NOT NULL     │ Audit              │
│ updated_at              │ TIMESTAMPTZ  │ NOT NULL     │ Audit              │
└─────────────────────────┴──────────────┴──────────────┴────────────────────┘

Contraintes:
- UNIQUE(tournee_id, gazelle_id)  -- Un piano ne peut être qu'une fois par tournée
- FK tournee_id → tournees(id) ON DELETE CASCADE

Index:
- idx_tournee_pianos_tournee   (tournee_id)
- idx_tournee_pianos_gazelle   (gazelle_id)
- idx_tournee_pianos_ordre     (tournee_id, ordre)
```

## 📝 Notes Techniques

### Performances
- **AVANT**: Chercher si piano dans tournée = Full table scan + JSON parse
- **APRÈS**: Chercher si piano dans tournée = Index seek (microseconds)

### Exemple Requêtes SQL

```sql
-- Tous les pianos d'une tournée (ordonné)
SELECT gazelle_id
FROM tournee_pianos
WHERE tournee_id = 'x'
ORDER BY ordre NULLS LAST, ajoute_le;

-- Dans quelle(s) tournée(s) est un piano?
SELECT t.nom, tp.ajoute_le
FROM tournee_pianos tp
JOIN tournees t ON t.id = tp.tournee_id
WHERE tp.gazelle_id = 'piano123';

-- Compter pianos par tournée
SELECT tournee_id, COUNT(*) as nb_pianos
FROM tournee_pianos
GROUP BY tournee_id;

-- Pianos ajoutés aujourd'hui
SELECT *
FROM tournee_pianos
WHERE DATE(ajoute_le) = CURRENT_DATE;
```

## 🔐 Sécurité (RLS)

Les policies permettent à tous les utilisateurs authentifiés de:
- ✅ Voir les relations (SELECT)
- ✅ Ajouter des pianos (INSERT)
- ✅ Modifier l'ordre (UPDATE)
- ✅ Retirer des pianos (DELETE)

Pour restreindre par rôle (futur):
```sql
-- Exemple: Seuls les admins peuvent supprimer
DROP POLICY "Users can remove pianos from tournees" ON tournee_pianos;

CREATE POLICY "Only admins can remove pianos"
  ON tournee_pianos FOR DELETE
  TO authenticated
  USING (auth.jwt() ->> 'role' = 'admin');
```

## 📚 Références

- [Supabase Foreign Keys](https://supabase.com/docs/guides/database/tables#foreign-keys)
- [Supabase Junction Tables](https://supabase.com/docs/guides/database/joins-and-nesting)
- [PostgreSQL UPSERT](https://www.postgresql.org/docs/current/sql-insert.html#SQL-ON-CONFLICT)
