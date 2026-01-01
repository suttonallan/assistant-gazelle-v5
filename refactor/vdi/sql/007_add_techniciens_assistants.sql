-- ==========================================
-- Migration: Ajouter support pour plusieurs techniciens par tournée
-- Date: 2025-12-31
-- Description: Ajouter colonne techniciens_assistants pour assigner plusieurs techniciens
-- ==========================================

-- Ajouter colonne pour techniciens assistants (array d'emails)
ALTER TABLE public.tournees
ADD COLUMN IF NOT EXISTS techniciens_assistants text[] DEFAULT '{}';

-- Commentaire explicatif
COMMENT ON COLUMN public.tournees.techniciens_assistants IS
  'Liste des techniciens assistants assignés à cette tournée (en plus du technicien_responsable)';

-- Index pour recherche par technicien assistant
CREATE INDEX IF NOT EXISTS idx_tournees_techniciens_assistants
  ON public.tournees USING GIN(techniciens_assistants);

-- Validation
DO $$
BEGIN
  -- Vérifier que la colonne existe
  IF NOT EXISTS (
    SELECT 1
    FROM information_schema.columns
    WHERE table_schema = 'public'
      AND table_name = 'tournees'
      AND column_name = 'techniciens_assistants'
  ) THEN
    RAISE EXCEPTION 'Migration échouée: colonne techniciens_assistants manquante!';
  END IF;

  RAISE NOTICE 'Migration OK: Colonne techniciens_assistants créée';
END $$;

-- Succès
SELECT 'Migration 007 terminée avec succès ✅' AS result;
