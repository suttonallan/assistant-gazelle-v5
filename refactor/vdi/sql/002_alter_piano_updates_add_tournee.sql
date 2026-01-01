-- ==========================================
-- Migration: Ajouter colonne completed_in_tournee_id
-- Date: 2025-01-01
-- Description: Tracker quelle tournée a complété chaque piano (pour couleur Vert)
-- ==========================================

-- Ajouter colonne completed_in_tournee_id
ALTER TABLE public.vincent_dindy_piano_updates
ADD COLUMN IF NOT EXISTS completed_in_tournee_id TEXT REFERENCES public.tournees(id) ON DELETE SET NULL;

-- Index pour performance (joins fréquents)
CREATE INDEX IF NOT EXISTS idx_piano_updates_completed_tournee
  ON public.vincent_dindy_piano_updates(completed_in_tournee_id);

-- Commentaire pour documentation
COMMENT ON COLUMN public.vincent_dindy_piano_updates.completed_in_tournee_id IS
  'ID de la tournée où ce piano a été marqué "completed". Utilisé pour déterminer couleur Vert.';

-- ==========================================
-- Logique métier: Reset automatique
-- ==========================================

-- Fonction pour reset pianos Vert quand tournée désactivée
CREATE OR REPLACE FUNCTION reset_completed_pianos_on_tournee_status_change()
RETURNS TRIGGER AS $$
BEGIN
  -- Si tournée passe de 'en_cours' à autre chose
  IF OLD.status = 'en_cours' AND NEW.status != 'en_cours' THEN
    -- Reset tous les pianos qui étaient Vert dans cette tournée
    UPDATE public.vincent_dindy_piano_updates
    SET
      completed_in_tournee_id = NULL,
      status = CASE
        WHEN status = 'completed' THEN 'normal'
        ELSE status
      END,
      updated_at = NOW()
    WHERE completed_in_tournee_id = OLD.id;

    RAISE NOTICE 'Reset % pianos de la tournée %',
      (SELECT COUNT(*) FROM public.vincent_dindy_piano_updates WHERE completed_in_tournee_id = OLD.id),
      OLD.id;
  END IF;

  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger sur changement statut tournée
CREATE TRIGGER tournee_status_change_reset_pianos
  AFTER UPDATE OF status ON public.tournees
  FOR EACH ROW
  WHEN (OLD.status IS DISTINCT FROM NEW.status)
  EXECUTE FUNCTION reset_completed_pianos_on_tournee_status_change();

-- ==========================================
-- Fonction helper: Activer une tournée
-- ==========================================

-- Cette fonction désactive toutes les autres tournées du même établissement
-- et reset leurs pianos Vert
CREATE OR REPLACE FUNCTION activate_tournee(p_tournee_id TEXT)
RETURNS BOOLEAN AS $$
DECLARE
  v_etablissement TEXT;
  v_count INT;
BEGIN
  -- Récupérer établissement de la tournée cible
  SELECT etablissement INTO v_etablissement
  FROM public.tournees
  WHERE id = p_tournee_id;

  IF v_etablissement IS NULL THEN
    RAISE EXCEPTION 'Tournée % introuvable', p_tournee_id;
  END IF;

  -- Désactiver toutes les autres tournées actives du même établissement
  UPDATE public.tournees
  SET status = 'planifiee', updated_at = NOW()
  WHERE etablissement = v_etablissement
    AND status = 'en_cours'
    AND id != p_tournee_id;

  GET DIAGNOSTICS v_count = ROW_COUNT;
  RAISE NOTICE 'Désactivé % tournée(s) active(s)', v_count;

  -- Activer la tournée cible
  UPDATE public.tournees
  SET status = 'en_cours', updated_at = NOW()
  WHERE id = p_tournee_id;

  -- Reset pianos Vert des anciennes tournées (via trigger automatique)

  RETURN TRUE;
EXCEPTION
  WHEN OTHERS THEN
    RAISE EXCEPTION 'Erreur activation tournée: %', SQLERRM;
    RETURN FALSE;
END;
$$ LANGUAGE plpgsql;

-- Commentaire
COMMENT ON FUNCTION activate_tournee IS
  'Active une tournée et désactive les autres actives du même établissement. Reset automatique des pianos Vert.';

-- ==========================================
-- Tests de validation
-- ==========================================

-- Test 1: Colonne ajoutée correctement
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'vincent_dindy_piano_updates'
    AND column_name = 'completed_in_tournee_id'
  ) THEN
    RAISE EXCEPTION 'Colonne completed_in_tournee_id manquante!';
  END IF;
  RAISE NOTICE 'Test 1 OK: Colonne completed_in_tournee_id existe';
END $$;

-- Test 2: Fonction activate_tournee existe
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_proc
    WHERE proname = 'activate_tournee'
  ) THEN
    RAISE EXCEPTION 'Fonction activate_tournee manquante!';
  END IF;
  RAISE NOTICE 'Test 2 OK: Fonction activate_tournee existe';
END $$;
