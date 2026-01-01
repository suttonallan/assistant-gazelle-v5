/**
 * Migration 003: Table de jonction tournee_pianos
 *
 * Remplace le JSONB piano_ids par une vraie table relationnelle
 * pour gérer la relation Many-to-Many entre tournées et pianos
 */

-- ==========================================
-- 1. CRÉER TABLE DE JONCTION
-- ==========================================

CREATE TABLE IF NOT EXISTS public.tournee_pianos (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

  -- Relations
  tournee_id TEXT NOT NULL REFERENCES public.tournees(id) ON DELETE CASCADE,
  gazelle_id TEXT NOT NULL,  -- ID du piano (pas de FK car pianos sont dans Gazelle API)

  -- Métadonnées
  ordre INTEGER,  -- Ordre d'affichage dans la tournée
  ajoute_le TIMESTAMPTZ NOT NULL DEFAULT now(),
  ajoute_par TEXT,  -- Email de l'utilisateur qui a ajouté

  -- Audit
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

  -- Contraintes
  CONSTRAINT unique_tournee_piano UNIQUE(tournee_id, gazelle_id)
);

-- ==========================================
-- 2. INDEX POUR PERFORMANCE
-- ==========================================

-- Recherche rapide: tous les pianos d'une tournée
CREATE INDEX idx_tournee_pianos_tournee ON public.tournee_pianos(tournee_id);

-- Recherche rapide: dans quelle(s) tournée(s) est un piano
CREATE INDEX idx_tournee_pianos_gazelle ON public.tournee_pianos(gazelle_id);

-- Tri par ordre
CREATE INDEX idx_tournee_pianos_ordre ON public.tournee_pianos(tournee_id, ordre);

-- ==========================================
-- 3. TRIGGER AUTO-UPDATE
-- ==========================================

CREATE OR REPLACE FUNCTION update_tournee_pianos_timestamp()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_tournee_pianos_timestamp
  BEFORE UPDATE ON public.tournee_pianos
  FOR EACH ROW
  EXECUTE FUNCTION update_tournee_pianos_timestamp();

-- ==========================================
-- 4. RLS (Row Level Security)
-- ==========================================

ALTER TABLE public.tournee_pianos ENABLE ROW LEVEL SECURITY;

-- Policy: Lecture publique authentifiée
CREATE POLICY "Users can view tournee pianos"
  ON public.tournee_pianos
  FOR SELECT
  TO authenticated
  USING (true);

-- Policy: Insertion authentifiée
CREATE POLICY "Users can add pianos to tournees"
  ON public.tournee_pianos
  FOR INSERT
  TO authenticated
  WITH CHECK (true);

-- Policy: Mise à jour authentifiée
CREATE POLICY "Users can update tournee pianos"
  ON public.tournee_pianos
  FOR UPDATE
  TO authenticated
  USING (true);

-- Policy: Suppression authentifiée
CREATE POLICY "Users can remove pianos from tournees"
  ON public.tournee_pianos
  FOR DELETE
  TO authenticated
  USING (true);

-- ==========================================
-- 5. MIGRATION DONNÉES EXISTANTES
-- ==========================================

-- Migrer piano_ids JSONB → tournee_pianos table
DO $$
DECLARE
  tournee_record RECORD;
  piano_id TEXT;
  piano_ordre INTEGER;
BEGIN
  -- Pour chaque tournée
  FOR tournee_record IN
    SELECT id, piano_ids, created_by
    FROM public.tournees
    WHERE piano_ids IS NOT NULL
      AND jsonb_array_length(piano_ids) > 0
  LOOP
    piano_ordre := 1;

    -- Pour chaque piano dans le tableau JSONB
    FOR piano_id IN
      SELECT jsonb_array_elements_text(tournee_record.piano_ids)
    LOOP
      -- Insérer dans table de jonction
      INSERT INTO public.tournee_pianos (
        tournee_id,
        gazelle_id,
        ordre,
        ajoute_par
      ) VALUES (
        tournee_record.id,
        piano_id,
        piano_ordre,
        tournee_record.created_by
      )
      ON CONFLICT (tournee_id, gazelle_id) DO NOTHING;  -- Skip doublons

      piano_ordre := piano_ordre + 1;
    END LOOP;
  END LOOP;

  RAISE NOTICE 'Migration des pianos vers tournee_pianos terminée';
END $$;

-- ==========================================
-- 6. OPTIONNEL: SUPPRIMER ANCIENNE COLONNE
-- ==========================================

-- NOTE: On garde piano_ids pour l'instant pour rollback facile
-- Décommenter après validation que tout fonctionne:
-- ALTER TABLE public.tournees DROP COLUMN piano_ids;

-- ==========================================
-- 7. FONCTION HELPER: Compter pianos
-- ==========================================

CREATE OR REPLACE FUNCTION count_tournee_pianos(p_tournee_id TEXT)
RETURNS INTEGER AS $$
  SELECT COUNT(*)::INTEGER
  FROM public.tournee_pianos
  WHERE tournee_id = p_tournee_id;
$$ LANGUAGE sql STABLE;

-- ==========================================
-- 8. FONCTION HELPER: Get piano IDs array
-- ==========================================

CREATE OR REPLACE FUNCTION get_tournee_piano_ids(p_tournee_id TEXT)
RETURNS TEXT[] AS $$
  SELECT ARRAY_AGG(gazelle_id ORDER BY ordre NULLS LAST, ajoute_le)
  FROM public.tournee_pianos
  WHERE tournee_id = p_tournee_id;
$$ LANGUAGE sql STABLE;

-- ==========================================
-- VALIDATION
-- ==========================================

-- Vérifier que la migration a fonctionné
DO $$
DECLARE
  total_tournees INTEGER;
  total_relations INTEGER;
BEGIN
  SELECT COUNT(*) INTO total_tournees FROM public.tournees;
  SELECT COUNT(*) INTO total_relations FROM public.tournee_pianos;

  RAISE NOTICE '✅ Migration terminée:';
  RAISE NOTICE '   - % tournées existantes', total_tournees;
  RAISE NOTICE '   - % relations piano-tournée créées', total_relations;
END $$;
