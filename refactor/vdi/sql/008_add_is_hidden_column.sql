-- ==========================================
-- Migration: Ajouter colonne is_hidden pour masquer pianos
-- Date: 2025-12-31
-- Description: Permet de masquer des pianos de l'inventaire (n'apparaissent plus dans Tournées ni Technicien)
-- ==========================================

-- Ajouter colonne is_hidden
ALTER TABLE public.vincent_dindy_piano_updates
ADD COLUMN IF NOT EXISTS is_hidden boolean DEFAULT false;

-- Commentaire explicatif
COMMENT ON COLUMN public.vincent_dindy_piano_updates.is_hidden IS
  'Si true, le piano est masqué de l''inventaire (n''apparaît plus dans Tournées ni Technicien, seulement dans Inventaire avec filtre)';

-- Index pour recherche rapide des pianos masqués
CREATE INDEX IF NOT EXISTS idx_vincent_dindy_piano_updates_is_hidden
  ON public.vincent_dindy_piano_updates(is_hidden)
  WHERE is_hidden = true;

-- Validation
DO $$
BEGIN
  -- Vérifier que la colonne existe
  IF NOT EXISTS (
    SELECT 1
    FROM information_schema.columns
    WHERE table_schema = 'public'
      AND table_name = 'vincent_dindy_piano_updates'
      AND column_name = 'is_hidden'
  ) THEN
    RAISE EXCEPTION 'Migration échouée: colonne is_hidden manquante!';
  END IF;

  RAISE NOTICE 'Migration OK: Colonne is_hidden créée';
END $$;

-- Succès
SELECT 'Migration 008 terminée avec succès ✅' AS result;
