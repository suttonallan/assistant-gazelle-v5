-- ==========================================
-- Migration: Renommer piano_id → gazelle_id
-- Date: 2025-01-01
-- Description: Standardiser sur gazelle_id comme identifiant principal
-- ==========================================

-- Renommer la colonne PRIMARY KEY
ALTER TABLE public.vincent_dindy_piano_updates
RENAME COLUMN piano_id TO gazelle_id;

-- Mettre à jour les commentaires
COMMENT ON COLUMN public.vincent_dindy_piano_updates.gazelle_id IS
  'ID unique du piano depuis Gazelle API (ex: ins_wbXNVWqrqwwf1UZ9)';

-- Validation
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'vincent_dindy_piano_updates'
    AND column_name = 'gazelle_id'
  ) THEN
    RAISE EXCEPTION 'Migration échouée: colonne gazelle_id manquante!';
  END IF;

  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'vincent_dindy_piano_updates'
    AND column_name = 'piano_id'
  ) THEN
    RAISE EXCEPTION 'Migration échouée: colonne piano_id existe encore!';
  END IF;

  RAISE NOTICE 'Migration OK: piano_id renommé en gazelle_id';
END $$;
