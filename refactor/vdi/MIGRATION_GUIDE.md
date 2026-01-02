# Guide de Migration: Système Tournées Vincent d'Indy

## 🚀 Installation Complète (Fresh Install)

Si les tables n'existent pas encore dans votre base Supabase, suivez ces étapes:

### Étape 1: Exécuter Migration Initiale

Dans **Supabase SQL Editor**:

1. Ouvrir [`sql/000_create_tables_if_not_exist.sql`](sql/000_create_tables_if_not_exist.sql)
2. Copier tout le contenu
3. Coller dans SQL Editor
4. Cliquer **Run**

**Ce que ça fait:**
- Crée table `tournees` (si n'existe pas)
- Crée table `tournee_pianos` (si n'existe pas)
- Crée table `vincent_dindy_piano_updates` (si n'existe pas)
- Configure RLS, triggers, indexes
- Affiche message de confirmation

### Étape 2: Ajouter Sync Tracking

Dans **Supabase SQL Editor**:

1. Ouvrir [`sql/011_add_sync_tracking.sql`](sql/011_add_sync_tracking.sql)
2. Copier tout le contenu
3. Coller dans SQL Editor
4. Cliquer **Run**

**Ce que ça fait:**
- Vérifie que `vincent_dindy_piano_updates` existe
- Ajoute colonnes: `is_work_completed`, `sync_status`, `last_sync_at`, `sync_error`, `gazelle_event_id`
- Met à jour contrainte `status` (ajoute `work_in_progress`)
- Crée fonctions PostgreSQL pour push
- Crée trigger auto-mark modified
- Affiche résumé de migration

**Résultat attendu:**
```
✅ Migration 011 terminée:
   - X pianos avec updates
   - Y pianos prêts pour push initial

📋 Nouveaux champs ajoutés:
   - is_work_completed (BOOLEAN)
   - sync_status (TEXT)
   - last_sync_at (TIMESTAMPTZ)
   - sync_error (TEXT)
   - gazelle_event_id (TEXT)
```

## 🔄 Mise à Jour (Tables Existantes)

Si les tables existent déjà mais sans les nouveaux champs:

### Option A: Exécuter uniquement Migration 011

```sql
-- Dans Supabase SQL Editor
-- Copier/coller le contenu de sql/011_add_sync_tracking.sql
```

Si erreur "table n'existe pas":
1. Vérifier nom table: `SELECT * FROM pg_tables WHERE tablename LIKE '%piano%';`
2. Si table a un autre nom, adapter la migration
3. Ou exécuter Migration 000 d'abord

### Option B: Forcer Recréation

**⚠️ ATTENTION: Perte de données!**

```sql
-- Sauvegarder données existantes
CREATE TABLE vincent_dindy_piano_updates_backup AS
SELECT * FROM vincent_dindy_piano_updates;

-- Supprimer table
DROP TABLE vincent_dindy_piano_updates CASCADE;

-- Exécuter Migration 000
-- Puis Migration 011

-- Restaurer données
INSERT INTO vincent_dindy_piano_updates
SELECT * FROM vincent_dindy_piano_updates_backup;
```

## ✅ Vérification Post-Migration

### 1. Vérifier Tables Créées

```sql
SELECT tablename
FROM pg_tables
WHERE schemaname = 'public'
AND tablename IN ('tournees', 'tournee_pianos', 'vincent_dindy_piano_updates');
```

**Résultat attendu:** 3 rows

### 2. Vérifier Colonnes Ajoutées

```sql
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_schema = 'public'
AND table_name = 'vincent_dindy_piano_updates'
AND column_name IN ('is_work_completed', 'sync_status', 'last_sync_at', 'sync_error', 'gazelle_event_id');
```

**Résultat attendu:** 5 rows

### 3. Vérifier Fonctions Créées

```sql
SELECT routine_name
FROM information_schema.routines
WHERE routine_schema = 'public'
AND routine_name LIKE '%piano%push%';
```

**Résultat attendu:**
- `get_pianos_ready_for_push`
- `mark_piano_as_pushed`
- `mark_piano_push_error`
- `auto_mark_sync_modified`

### 4. Test Fonction get_pianos_ready_for_push

```sql
SELECT * FROM get_pianos_ready_for_push(NULL, 10);
```

**Résultat:** Liste des pianos prêts pour push (peut être vide au début)

### 5. Test Trigger auto_mark_sync_modified

```sql
-- Créer piano test
INSERT INTO vincent_dindy_piano_updates (piano_id, status, travail, is_work_completed, sync_status)
VALUES ('test_piano_123', 'completed', 'Piano accordé', true, 'pushed');

-- Modifier piano
UPDATE vincent_dindy_piano_updates
SET travail = 'Piano accordé et réglé'
WHERE piano_id = 'test_piano_123';

-- Vérifier sync_status changé
SELECT piano_id, sync_status
FROM vincent_dindy_piano_updates
WHERE piano_id = 'test_piano_123';
-- sync_status devrait être 'modified'

-- Nettoyer
DELETE FROM vincent_dindy_piano_updates WHERE piano_id = 'test_piano_123';
```

## 🐛 Dépannage

### Erreur: "column travail does not exist"

**Cause:** Table `vincent_dindy_piano_updates` n'existe pas ou a structure différente

**Solution:**
1. Exécuter Migration 000 d'abord
2. Puis Migration 011

### Erreur: "relation tournees does not exist"

**Cause:** Tables tournées pas encore créées

**Solution:** Exécuter Migration 000

### Erreur: "constraint already exists"

**Cause:** Migration déjà partiellement exécutée

**Solution:**
1. Vérifier colonnes existantes: `\d vincent_dindy_piano_updates`
2. Commenter lignes déjà exécutées dans migration
3. Re-exécuter

### Erreur: "permission denied"

**Cause:** Utilisateur n'a pas les droits

**Solution:** Utiliser SERVICE_ROLE_KEY dans Supabase, pas ANON_KEY

## 📋 Checklist Déploiement

- [ ] Migration 000 exécutée (tables créées)
- [ ] Migration 011 exécutée (sync tracking ajouté)
- [ ] Vérifications post-migration passées
- [ ] Test fonction `get_pianos_ready_for_push` OK
- [ ] Test trigger `auto_mark_sync_modified` OK
- [ ] Backend API redémarré (pour charger nouvelles fonctions)
- [ ] Frontend déployé avec nouveaux champs
- [ ] Tests end-to-end réussis
- [ ] Cron job configuré pour push automatique

## 🔗 Prochaines Étapes

Après migration réussie:

1. **Tester API Backend**
   ```bash
   # Vérifier endpoint pianos-ready-for-push
   curl http://localhost:8000/vincent-dindy/pianos-ready-for-push
   ```

2. **Tester Push Service**
   ```bash
   python3 core/gazelle_push_service.py --dry-run
   ```

3. **Implémenter Frontend** (code fourni dans [`IMPLEMENTATION_TOURNEES_STATUS.md`](../../IMPLEMENTATION_TOURNEES_STATUS.md))

4. **Setup Cron Job**
   ```bash
   crontab -e
   # Ajouter: 0 1 * * * /usr/bin/python3 /path/to/scripts/scheduled_push_to_gazelle.py
   ```

---

**Support:** Si problèmes persistent, vérifier logs Supabase et contacter Allan Sutton
