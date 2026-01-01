-- ==========================================
-- Table: vincent_dindy_piano_updates
-- ==========================================
-- Stocke les modifications dynamiques des pianos
-- (status, aFaire, travail, observations, etc.)
--
-- Architecture:
-- - piano_id = PRIMARY KEY (gazelleId depuis Gazelle API)
-- - Upserts pour merge optimiste
-- - Tracking updated_by + updated_at

-- Drop existing table if needed (ATTENTION: perte de données!)
-- DROP TABLE IF EXISTS public.vincent_dindy_piano_updates CASCADE;

CREATE TABLE IF NOT EXISTS public.vincent_dindy_piano_updates (
  -- Primary Key
  piano_id TEXT PRIMARY KEY,  -- gazelleId du piano (ex: "ins_wbXNVWqrqwwf1UZ9")

  -- Modifications dynamiques
  status TEXT CHECK (status IN ('normal', 'proposed', 'top', 'completed')),
  usage TEXT,
  a_faire TEXT,  -- "À faire"
  travail TEXT,
  observations TEXT,

  -- Tracking
  is_in_csv BOOLEAN DEFAULT true,  -- Visible dans inventaire CSV
  completed_in_tournee_id TEXT,  -- ID de la tournée où le piano a été complété

  -- Métadonnées
  updated_by TEXT,  -- Email de l'utilisateur
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ==========================================
-- INDEXES
-- ==========================================

CREATE INDEX IF NOT EXISTS idx_piano_updates_status
  ON public.vincent_dindy_piano_updates(status);

CREATE INDEX IF NOT EXISTS idx_piano_updates_tournee
  ON public.vincent_dindy_piano_updates(completed_in_tournee_id);

CREATE INDEX IF NOT EXISTS idx_piano_updates_updated_at
  ON public.vincent_dindy_piano_updates(updated_at DESC);

-- ==========================================
-- ROW LEVEL SECURITY (RLS)
-- ==========================================

ALTER TABLE public.vincent_dindy_piano_updates ENABLE ROW LEVEL SECURITY;

-- Policy: Tout le monde peut lire
CREATE POLICY "Enable read access for all users"
  ON public.vincent_dindy_piano_updates
  FOR SELECT
  USING (true);

-- Policy: Tout le monde peut insérer/modifier (pour dev)
-- TODO: Restreindre en production avec auth
CREATE POLICY "Enable insert/update for all users"
  ON public.vincent_dindy_piano_updates
  FOR ALL
  USING (true)
  WITH CHECK (true);

-- ==========================================
-- TRIGGER: Auto-update updated_at
-- ==========================================

CREATE OR REPLACE FUNCTION update_vincent_dindy_piano_updates_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_update_vincent_dindy_piano_updates_updated_at
  ON public.vincent_dindy_piano_updates;

CREATE TRIGGER trigger_update_vincent_dindy_piano_updates_updated_at
  BEFORE UPDATE ON public.vincent_dindy_piano_updates
  FOR EACH ROW
  EXECUTE FUNCTION update_vincent_dindy_piano_updates_updated_at();

-- ==========================================
-- ENABLE REALTIME
-- ==========================================

-- Enable realtime for this table
ALTER PUBLICATION supabase_realtime ADD TABLE public.vincent_dindy_piano_updates;

-- ==========================================
-- COMMENTAIRES
-- ==========================================

COMMENT ON TABLE public.vincent_dindy_piano_updates IS
  'Modifications dynamiques des pianos Vincent d''Indy (status, notes, etc.)';

COMMENT ON COLUMN public.vincent_dindy_piano_updates.piano_id IS
  'gazelleId du piano (clé primaire)';

COMMENT ON COLUMN public.vincent_dindy_piano_updates.status IS
  'Statut du piano: normal, proposed (jaune), top (ambre), completed (vert)';

COMMENT ON COLUMN public.vincent_dindy_piano_updates.completed_in_tournee_id IS
  'ID de la tournée où ce piano a été marqué completed (pour logique couleur verte)';
