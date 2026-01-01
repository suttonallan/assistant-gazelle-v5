-- ==========================================
-- Migration: Corriger contraintes table tournees
-- Date: 2025-12-31
-- Description:
--   1. Rendre technicien_responsable nullable
--   2. Ajouter status 'archivee'
-- ==========================================

-- 1. Rendre technicien_responsable nullable
ALTER TABLE public.tournees
  ALTER COLUMN technicien_responsable DROP NOT NULL;

-- 2. Supprimer ancienne contrainte status
ALTER TABLE public.tournees
  DROP CONSTRAINT IF EXISTS tournees_status_check;

-- 3. Ajouter nouvelle contrainte avec 'archivee'
ALTER TABLE public.tournees
  ADD CONSTRAINT tournees_status_check
  CHECK (status IN ('planifiee', 'en_cours', 'terminee', 'archivee'));

-- Commentaire
COMMENT ON COLUMN public.tournees.status IS 'Statut: planifiee | en_cours | terminee | archivee';
COMMENT ON COLUMN public.tournees.technicien_responsable IS 'Email du technicien responsable (optionnel)';
