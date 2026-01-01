-- ==========================================
-- Migration: Corriger contrainte CHECK pour status
-- Date: 2025-12-31
-- Description: Ajouter 'top' aux valeurs permises pour status
-- ==========================================

-- Drop l'ancienne contrainte
ALTER TABLE public.vincent_dindy_piano_updates
DROP CONSTRAINT IF EXISTS vincent_dindy_piano_updates_status_check;

-- Créer nouvelle contrainte avec TOUTES les valeurs
ALTER TABLE public.vincent_dindy_piano_updates
ADD CONSTRAINT vincent_dindy_piano_updates_status_check
CHECK (status IN ('normal', 'proposed', 'top', 'completed'));

-- Validation
DO $$
BEGIN
  -- Vérifier que la contrainte existe
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conname = 'vincent_dindy_piano_updates_status_check'
  ) THEN
    RAISE EXCEPTION 'Migration échouée: contrainte status_check manquante!';
  END IF;

  RAISE NOTICE 'Migration OK: Contrainte status_check mise à jour avec "top"';
END $$;

-- Test: Insérer un piano avec status='top'
INSERT INTO public.vincent_dindy_piano_updates (gazelle_id, status, updated_by)
VALUES ('TEST_MIGRATION_TOP', 'top', 'migration@system.com')
ON CONFLICT (gazelle_id) DO UPDATE SET status = 'top';

-- Cleanup test
DELETE FROM public.vincent_dindy_piano_updates WHERE gazelle_id = 'TEST_MIGRATION_TOP';

-- Succès
SELECT 'Migration 005 terminée avec succès ✅' AS result;
