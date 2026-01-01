-- ==========================================
-- Migration: Ajouter colonne is_top à tournee_pianos
-- Date: 2025-12-31
-- Description: Permettre de marquer des pianos comme "Top" (priorité haute) par tournée
-- ==========================================

-- Ajouter colonne is_top (flag booléen pour priorité haute)
ALTER TABLE public.tournee_pianos
ADD COLUMN IF NOT EXISTS is_top BOOLEAN DEFAULT false;

-- Index pour performance (filtrage fréquent)
CREATE INDEX IF NOT EXISTS idx_tournee_pianos_is_top
  ON public.tournee_pianos(is_top) WHERE is_top = true;

-- Commentaire
COMMENT ON COLUMN public.tournee_pianos.is_top IS
  'Indique si ce piano est marqué comme priorité haute (Top/Ambre) dans cette tournée';

-- ==========================================
-- Migration des données existantes (optionnel)
-- ==========================================

-- Migrer les pianos avec status='top' depuis vincent_dindy_piano_updates
-- vers is_top=true dans tournee_pianos (pour TOUTES les tournées où ils sont présents)
UPDATE public.tournee_pianos tp
SET is_top = true
FROM public.vincent_dindy_piano_updates vdu
WHERE tp.gazelle_id = vdu.gazelle_id
  AND vdu.status = 'top';

-- Log résultat
DO $$
DECLARE
  v_count INT;
BEGIN
  SELECT COUNT(*) INTO v_count
  FROM public.tournee_pianos
  WHERE is_top = true;

  RAISE NOTICE 'Migration terminée: % piano(s) marqué(s) comme Top dans des tournées', v_count;
END $$;

-- Validation
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'tournee_pianos'
    AND column_name = 'is_top'
  ) THEN
    RAISE EXCEPTION 'Migration échouée: colonne is_top manquante!';
  END IF;

  RAISE NOTICE 'Migration OK: colonne is_top ajoutée à tournee_pianos ✅';
END $$;
