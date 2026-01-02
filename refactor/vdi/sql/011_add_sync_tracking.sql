-- ==========================================
-- Migration 011: Sync Tracking & Work Completion
-- Date: 2026-01-02
-- Description: Ajouter tracking de synchronisation Gazelle et checkbox "Travail complété"
--
-- PRÉREQUIS: La table vincent_dindy_piano_updates doit exister
-- Si elle n'existe pas, exécuter d'abord refactor/vdi/sql/003_create_piano_updates_table.sql
-- ==========================================

-- ==========================================
-- 0. VÉRIFICATION TABLE EXISTE ET DIAGNOSTIC
-- ==========================================

DO $$
DECLARE
  table_exists BOOLEAN;
  column_list TEXT;
BEGIN
  -- Vérifier si table existe
  SELECT EXISTS (
    SELECT FROM pg_tables
    WHERE schemaname = 'public'
    AND tablename = 'vincent_dindy_piano_updates'
  ) INTO table_exists;

  IF NOT table_exists THEN
    RAISE EXCEPTION 'Table vincent_dindy_piano_updates n''existe pas. Exécutez d''abord la migration 000_create_tables_if_not_exist.sql';
  END IF;

  -- Afficher toutes les colonnes pour diagnostic
  SELECT string_agg(column_name, ', ' ORDER BY ordinal_position)
  INTO column_list
  FROM information_schema.columns
  WHERE table_schema = 'public'
  AND table_name = 'vincent_dindy_piano_updates';

  RAISE NOTICE 'Colonnes trouvées dans vincent_dindy_piano_updates: %', column_list;
END $$;

-- ==========================================
-- 1. VÉRIFIER ET AJOUTER COLONNES REQUISES
-- ==========================================

-- S'assurer que travail et observations existent (requis pour les fonctions)
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public'
    AND table_name = 'vincent_dindy_piano_updates'
    AND column_name = 'travail'
  ) THEN
    ALTER TABLE public.vincent_dindy_piano_updates
    ADD COLUMN travail TEXT;
    RAISE NOTICE 'Colonne travail ajoutée';
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public'
    AND table_name = 'vincent_dindy_piano_updates'
    AND column_name = 'observations'
  ) THEN
    ALTER TABLE public.vincent_dindy_piano_updates
    ADD COLUMN observations TEXT;
    RAISE NOTICE 'Colonne observations ajoutée';
  END IF;
END $$;

-- ==========================================
-- 2. AJOUTER NOUVEAUX CHAMPS
-- ==========================================

ALTER TABLE public.vincent_dindy_piano_updates
ADD COLUMN IF NOT EXISTS is_work_completed BOOLEAN DEFAULT false,
ADD COLUMN IF NOT EXISTS sync_status TEXT CHECK (sync_status IN ('pending', 'pushed', 'modified', 'error')) DEFAULT 'pending',
ADD COLUMN IF NOT EXISTS last_sync_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS sync_error TEXT,
ADD COLUMN IF NOT EXISTS gazelle_event_id TEXT,
ADD COLUMN IF NOT EXISTS completed_at TIMESTAMPTZ;  -- Date/heure de complétion (pour push Gazelle)

-- ==========================================
-- 2. COMMENTAIRES
-- ==========================================

COMMENT ON COLUMN public.vincent_dindy_piano_updates.is_work_completed IS
  'Checkbox "Travail complété" cochée par le technicien';

COMMENT ON COLUMN public.vincent_dindy_piano_updates.sync_status IS
  'État de synchronisation avec Gazelle: pending, pushed, modified, error';

COMMENT ON COLUMN public.vincent_dindy_piano_updates.last_sync_at IS
  'Timestamp du dernier push réussi vers Gazelle';

COMMENT ON COLUMN public.vincent_dindy_piano_updates.sync_error IS
  'Message d''erreur si le dernier push a échoué';

COMMENT ON COLUMN public.vincent_dindy_piano_updates.gazelle_event_id IS
  'ID de l''événement Gazelle créé lors du push (pour traçabilité)';

COMMENT ON COLUMN public.vincent_dindy_piano_updates.completed_at IS
  'Date/heure où le piano a été marqué comme complété (utilisée pour push Gazelle)';

-- ==========================================
-- 3. METTRE À JOUR CONTRAINTE STATUS
-- ==========================================

-- Supprimer ancienne contrainte
ALTER TABLE public.vincent_dindy_piano_updates
DROP CONSTRAINT IF EXISTS vincent_dindy_piano_updates_status_check;

-- Ajouter nouvelle contrainte avec 'work_in_progress'
ALTER TABLE public.vincent_dindy_piano_updates
ADD CONSTRAINT vincent_dindy_piano_updates_status_check
  CHECK (status IN ('normal', 'proposed', 'top', 'work_in_progress', 'completed'));

-- ==========================================
-- 4. INDEX POUR PERFORMANCE
-- ==========================================

CREATE INDEX IF NOT EXISTS idx_piano_updates_sync_status
  ON public.vincent_dindy_piano_updates(sync_status)
  WHERE sync_status IN ('pending', 'modified', 'error');

CREATE INDEX IF NOT EXISTS idx_piano_updates_work_completed
  ON public.vincent_dindy_piano_updates(is_work_completed)
  WHERE is_work_completed = true;

CREATE INDEX IF NOT EXISTS idx_piano_updates_completed_ready_for_push
  ON public.vincent_dindy_piano_updates(status, is_work_completed, sync_status)
  WHERE status = 'completed' AND is_work_completed = true AND sync_status IN ('pending', 'modified', 'error');

-- ==========================================
-- 5. VÉRIFIER ET CORRIGER STRUCTURE TABLE
-- ==========================================

-- Vérifier que la colonne piano_id existe, sinon la créer ou renommer
DO $$
DECLARE
  has_piano_id BOOLEAN;
  pk_column_name TEXT;
  all_columns TEXT;
BEGIN
  -- Vérifier si piano_id existe
  SELECT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public'
    AND table_name = 'vincent_dindy_piano_updates'
    AND column_name = 'piano_id'
  ) INTO has_piano_id;

  IF NOT has_piano_id THEN
    -- Chercher la colonne primaire existante
    SELECT a.attname INTO pk_column_name
    FROM pg_index i
    JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
    WHERE i.indrelid = 'public.vincent_dindy_piano_updates'::regclass
    AND i.indisprimary
    LIMIT 1;

    -- Afficher toutes les colonnes pour debug
    SELECT string_agg(column_name, ', ' ORDER BY ordinal_position)
    INTO all_columns
    FROM information_schema.columns
    WHERE table_schema = 'public'
    AND table_name = 'vincent_dindy_piano_updates';

    RAISE NOTICE 'Colonnes actuelles: %', all_columns;

    IF pk_column_name IS NOT NULL AND pk_column_name != 'piano_id' THEN
      -- Renommer la colonne primaire existante en piano_id
      EXECUTE format('ALTER TABLE public.vincent_dindy_piano_updates RENAME COLUMN %I TO piano_id', pk_column_name);
      RAISE NOTICE 'Colonne % renommée en piano_id', pk_column_name;
    ELSIF pk_column_name IS NULL THEN
      -- Pas de clé primaire, ajouter piano_id
      -- Mais d'abord, vérifier s'il y a des colonnes qui pourraient être l'ID
      IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public'
        AND table_name = 'vincent_dindy_piano_updates'
        AND column_name IN ('id', 'gazelle_id', 'piano_gazelle_id')
      ) THEN
        -- Renommer la colonne ID trouvée
        SELECT column_name INTO pk_column_name
        FROM information_schema.columns
        WHERE table_schema = 'public'
        AND table_name = 'vincent_dindy_piano_updates'
        AND column_name IN ('id', 'gazelle_id', 'piano_gazelle_id')
        LIMIT 1;
        
        EXECUTE format('ALTER TABLE public.vincent_dindy_piano_updates RENAME COLUMN %I TO piano_id', pk_column_name);
        RAISE NOTICE 'Colonne % renommée en piano_id', pk_column_name;
      ELSE
        -- Ajouter la colonne piano_id
        ALTER TABLE public.vincent_dindy_piano_updates
        ADD COLUMN piano_id TEXT;
        
        -- Essayer de créer une clé primaire (peut échouer si données existent)
        BEGIN
          ALTER TABLE public.vincent_dindy_piano_updates
          ADD PRIMARY KEY (piano_id);
          RAISE NOTICE 'Colonne piano_id ajoutée avec clé primaire';
        EXCEPTION WHEN OTHERS THEN
          RAISE NOTICE 'Colonne piano_id ajoutée (clé primaire non créée: %)', SQLERRM;
        END;
      END IF;
    END IF;
  ELSE
    RAISE NOTICE 'Colonne piano_id existe déjà';
  END IF;
END $$;

-- ==========================================
-- 6. FONCTION: Get Pianos Ready for Push
-- ==========================================

CREATE OR REPLACE FUNCTION get_pianos_ready_for_push(
  p_tournee_id TEXT DEFAULT NULL,
  p_limit INTEGER DEFAULT 100
)
RETURNS TABLE (
  piano_id TEXT,
  travail TEXT,
  observations TEXT,
  completed_in_tournee_id TEXT,
  sync_status TEXT,
  updated_at TIMESTAMPTZ,
  a_faire TEXT,
  completed_at TIMESTAMPTZ
) AS $$
BEGIN
  RETURN QUERY
  SELECT
    vdpu.piano_id,
    vdpu.travail,
    vdpu.observations,
    vdpu.completed_in_tournee_id,
    vdpu.sync_status,
    vdpu.updated_at,
    vdpu.a_faire,
    vdpu.completed_at
  FROM public.vincent_dindy_piano_updates vdpu
  WHERE
    -- Piano doit être completed et work_completed cochée
    vdpu.status = 'completed'
    AND vdpu.is_work_completed = true
    -- Sync doit être en attente, modifié ou erreur
    AND vdpu.sync_status IN ('pending', 'modified', 'error')
    -- Piano doit avoir du contenu à envoyer
    AND (vdpu.travail IS NOT NULL OR vdpu.observations IS NOT NULL)
    -- Filtre optionnel par tournée
    AND (p_tournee_id IS NULL OR vdpu.completed_in_tournee_id = p_tournee_id)
  ORDER BY
    -- Priorité: erreurs d'abord, puis modifiés, puis pending
    CASE vdpu.sync_status
      WHEN 'error' THEN 1
      WHEN 'modified' THEN 2
      WHEN 'pending' THEN 3
    END,
    vdpu.updated_at DESC
  LIMIT p_limit;
END;
$$ LANGUAGE plpgsql STABLE;

COMMENT ON FUNCTION get_pianos_ready_for_push IS
  'Retourne les pianos prêts à être envoyés vers Gazelle (completed + work_completed + sync pending/modified/error)';

-- ==========================================
-- 7. FONCTION: Mark Piano as Pushed
-- ==========================================

CREATE OR REPLACE FUNCTION mark_piano_as_pushed(
  p_piano_id TEXT,
  p_gazelle_event_id TEXT
)
RETURNS VOID AS $$
BEGIN
  UPDATE public.vincent_dindy_piano_updates
  SET
    sync_status = 'pushed',
    last_sync_at = NOW(),
    sync_error = NULL,
    gazelle_event_id = p_gazelle_event_id,
    updated_at = NOW()
  WHERE piano_id = p_piano_id;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION mark_piano_as_pushed IS
  'Marque un piano comme pushé avec succès vers Gazelle';

-- ==========================================
-- 8. FONCTION: Mark Piano as Push Error
-- ==========================================

CREATE OR REPLACE FUNCTION mark_piano_push_error(
  p_piano_id TEXT,
  p_error_message TEXT
)
RETURNS VOID AS $$
BEGIN
  UPDATE public.vincent_dindy_piano_updates
  SET
    sync_status = 'error',
    sync_error = p_error_message,
    updated_at = NOW()
  WHERE piano_id = p_piano_id;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION mark_piano_push_error IS
  'Marque un piano avec une erreur de push vers Gazelle';

-- ==========================================
-- 9. TRIGGER: Auto-mark as Modified on Update
-- ==========================================

CREATE OR REPLACE FUNCTION auto_mark_sync_modified()
RETURNS TRIGGER AS $$
BEGIN
  -- Si le piano était 'pushed' et on modifie travail/observations
  IF OLD.sync_status = 'pushed' AND (
    OLD.travail IS DISTINCT FROM NEW.travail OR
    OLD.observations IS DISTINCT FROM NEW.observations OR
    OLD.is_work_completed IS DISTINCT FROM NEW.is_work_completed
  ) THEN
    NEW.sync_status := 'modified';
  END IF;

  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_auto_mark_sync_modified
  ON public.vincent_dindy_piano_updates;

CREATE TRIGGER trigger_auto_mark_sync_modified
  BEFORE UPDATE ON public.vincent_dindy_piano_updates
  FOR EACH ROW
  EXECUTE FUNCTION auto_mark_sync_modified();

COMMENT ON FUNCTION auto_mark_sync_modified IS
  'Auto-marque sync_status = modified si piano pushé est modifié';

-- ==========================================
-- 10. MIGRATION DONNÉES EXISTANTES
-- ==========================================

-- Marquer tous les pianos completed existants comme 'pending' pour push
-- Seulement si la table a déjà des données ET les colonnes existent
DO $$
DECLARE
  has_travail BOOLEAN;
  has_observations BOOLEAN;
  row_count INTEGER;
BEGIN
  -- Vérifier si colonnes travail et observations existent
  SELECT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public'
    AND table_name = 'vincent_dindy_piano_updates'
    AND column_name = 'travail'
  ) INTO has_travail;

  SELECT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public'
    AND table_name = 'vincent_dindy_piano_updates'
    AND column_name = 'observations'
  ) INTO has_observations;

  -- Si les colonnes existent ET table non vide, faire migration
  IF has_travail AND has_observations THEN
    SELECT COUNT(*) INTO row_count FROM public.vincent_dindy_piano_updates;

    IF row_count > 0 THEN
      UPDATE public.vincent_dindy_piano_updates
      SET
        sync_status = 'pending',
        is_work_completed = true  -- Assume completed = work_completed si déjà completed
      WHERE
        status = 'completed'
        AND (travail IS NOT NULL OR observations IS NOT NULL);

      GET DIAGNOSTICS row_count = ROW_COUNT;
      RAISE NOTICE 'Migration données existantes: % pianos mis à jour', row_count;
    ELSE
      RAISE NOTICE 'Table vide, skip migration données';
    END IF;
  ELSE
    RAISE NOTICE 'Colonnes travail/observations manquantes, skip migration';
  END IF;
END $$;

-- ==========================================
-- 11. VALIDATION
-- ==========================================

DO $$
DECLARE
  total_pianos INTEGER;
  ready_for_push INTEGER;
  has_piano_id BOOLEAN;
BEGIN
  -- Vérifier que piano_id existe avant d'utiliser la fonction
  SELECT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public'
    AND table_name = 'vincent_dindy_piano_updates'
    AND column_name = 'piano_id'
  ) INTO has_piano_id;

  IF NOT has_piano_id THEN
    RAISE WARNING 'Colonne piano_id n''existe toujours pas après correction. Vérifiez la structure de la table.';
    RETURN;
  END IF;

  -- Compter total pianos avec updates
  SELECT COUNT(*) INTO total_pianos
  FROM public.vincent_dindy_piano_updates;

  -- Compter pianos prêts pour push (seulement si colonnes requises existent)
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public'
    AND table_name = 'vincent_dindy_piano_updates'
    AND column_name IN ('status', 'is_work_completed', 'sync_status')
  ) THEN
    SELECT COUNT(*) INTO ready_for_push
    FROM get_pianos_ready_for_push();
  ELSE
    ready_for_push := 0;
    RAISE WARNING 'Colonnes requises manquantes pour get_pianos_ready_for_push';
  END IF;

  RAISE NOTICE '✅ Migration 011 terminée:';
  RAISE NOTICE '   - % pianos avec updates', total_pianos;
  RAISE NOTICE '   - % pianos prêts pour push initial', ready_for_push;
  RAISE NOTICE '';
  RAISE NOTICE '📋 Nouveaux champs ajoutés:';
  RAISE NOTICE '   - is_work_completed (BOOLEAN)';
  RAISE NOTICE '   - sync_status (TEXT)';
  RAISE NOTICE '   - last_sync_at (TIMESTAMPTZ)';
  RAISE NOTICE '   - sync_error (TEXT)';
  RAISE NOTICE '   - gazelle_event_id (TEXT)';
  RAISE NOTICE '';
  RAISE NOTICE '🔧 Fonctions créées:';
  RAISE NOTICE '   - get_pianos_ready_for_push(tournee_id, limit)';
  RAISE NOTICE '   - mark_piano_as_pushed(piano_id, event_id)';
  RAISE NOTICE '   - mark_piano_push_error(piano_id, error)';
  RAISE NOTICE '   - auto_mark_sync_modified() TRIGGER';
END $$;
