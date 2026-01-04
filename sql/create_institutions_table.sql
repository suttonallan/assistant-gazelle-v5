-- Table centralisée pour TOUTES les institutions
-- Plus de hardcoded credentials, tout est dans Supabase
CREATE TABLE IF NOT EXISTS institutions (
  slug TEXT PRIMARY KEY,                    -- Identifiant URL (vincent-dindy, orford, place-des-arts)
  name TEXT NOT NULL,                       -- Nom affiché (Vincent d'Indy, Orford, Place des Arts)
  gazelle_client_id TEXT NOT NULL,          -- Client ID Gazelle pour cette institution
  active BOOLEAN DEFAULT true,              -- Actif ou désactivé
  options JSONB DEFAULT '{}'::jsonb,        -- Options spéciales (ex: {"has_requests": true} pour PDA)
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index pour performance
CREATE INDEX IF NOT EXISTS idx_institutions_active ON institutions(active);

-- Fonction pour auto-update updated_at
CREATE OR REPLACE FUNCTION update_institutions_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger pour auto-update
DROP TRIGGER IF EXISTS institutions_updated_at ON institutions;
CREATE TRIGGER institutions_updated_at
  BEFORE UPDATE ON institutions
  FOR EACH ROW
  EXECUTE FUNCTION update_institutions_updated_at();

-- Insérer les institutions existantes
INSERT INTO institutions (slug, name, gazelle_client_id, options) VALUES
  ('vincent-dindy', 'Vincent d''Indy', 'cli_9UMLkteep8EsISbG', '{}'),
  ('place-des-arts', 'Place des Arts', 'cli_HbEwl9rN11pSuDEU', '{"has_requests": true, "has_email_parser": true}')
ON CONFLICT (slug) DO UPDATE SET
  name = EXCLUDED.name,
  gazelle_client_id = EXCLUDED.gazelle_client_id,
  options = EXCLUDED.options;

-- Enable Row Level Security
ALTER TABLE institutions ENABLE ROW LEVEL SECURITY;

-- Policy: Tout le monde peut lire les institutions actives
CREATE POLICY "Institutions actives sont lisibles par tous"
  ON institutions FOR SELECT
  USING (active = true);

-- Policy: Seuls les admins peuvent modifier (service_role)
CREATE POLICY "Seuls admins peuvent modifier institutions"
  ON institutions FOR ALL
  USING (auth.role() = 'service_role');

COMMENT ON TABLE institutions IS 'Configuration centralisée des institutions - Plus de hardcoded credentials!';
COMMENT ON COLUMN institutions.slug IS 'Identifiant URL utilisé dans /api/{slug}/pianos';
COMMENT ON COLUMN institutions.gazelle_client_id IS 'Client ID Gazelle - UNIQUE source de vérité';
COMMENT ON COLUMN institutions.options IS 'Options spéciales par institution (ex: has_requests pour Place des Arts)';
