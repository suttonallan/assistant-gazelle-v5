-- ==========================================
-- Table: pda_piano_mappings
-- ==========================================
-- Mapping entre les abréviations/locations Place des Arts
-- et les vrais pianos de Gazelle
--
-- Exemple:
--   piano_abbreviation: "SALLE1" ou "GRAND" ou "PETIT"
--   gazelle_piano_id: "ins_9H7Mh59SXwEs2JxL"
--   location: "Salle Wilfrid-Pelletier - Scène principale"
-- ==========================================

CREATE TABLE IF NOT EXISTS pda_piano_mappings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  
  -- Abréviation utilisée dans les demandes Place des Arts
  piano_abbreviation TEXT NOT NULL,
  
  -- ID du piano dans Gazelle
  gazelle_piano_id TEXT NOT NULL,
  
  -- Localisation complète (optionnel, pour référence)
  location TEXT,
  
  -- Flag d'incertitude: true si le mapping nécessite vérification
  is_uncertain BOOLEAN DEFAULT false,
  
  -- Note du gestionnaire en cas d'incertitude
  uncertainty_note TEXT,
  
  -- Métadonnées
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  created_by TEXT,
  
  -- Contraintes
  CONSTRAINT unique_abbreviation UNIQUE (piano_abbreviation),
  CONSTRAINT unique_gazelle_piano UNIQUE (gazelle_piano_id)
);

-- Index pour recherche rapide
CREATE INDEX IF NOT EXISTS idx_pda_mappings_abbreviation ON pda_piano_mappings(piano_abbreviation);
CREATE INDEX IF NOT EXISTS idx_pda_mappings_gazelle_id ON pda_piano_mappings(gazelle_piano_id);

-- Trigger pour updated_at
CREATE OR REPLACE FUNCTION update_pda_piano_mappings_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_pda_piano_mappings_updated_at
  BEFORE UPDATE ON pda_piano_mappings
  FOR EACH ROW
  EXECUTE FUNCTION update_pda_piano_mappings_updated_at();

-- RLS (Row Level Security)
ALTER TABLE pda_piano_mappings ENABLE ROW LEVEL SECURITY;

-- Policy: Tous les utilisateurs authentifiés peuvent lire
CREATE POLICY "pda_piano_mappings_select" ON pda_piano_mappings
  FOR SELECT
  USING (true);

-- Policy: Seuls les admins peuvent modifier
CREATE POLICY "pda_piano_mappings_modify" ON pda_piano_mappings
  FOR ALL
  USING (
    -- TODO: Vérifier le rôle admin depuis auth.users
    -- Pour l'instant, permettre à tous (à restreindre plus tard)
    true
  );

-- Commentaires
COMMENT ON TABLE pda_piano_mappings IS 'Mapping entre abréviations Place des Arts et pianos Gazelle';
COMMENT ON COLUMN pda_piano_mappings.piano_abbreviation IS 'Abréviation utilisée dans les demandes PDA (ex: SALLE1, GRAND)';
COMMENT ON COLUMN pda_piano_mappings.gazelle_piano_id IS 'ID du piano dans Gazelle (ex: ins_9H7Mh59SXwEs2JxL)';
COMMENT ON COLUMN pda_piano_mappings.location IS 'Localisation complète du piano (ex: Salle Wilfrid-Pelletier)';
COMMENT ON COLUMN pda_piano_mappings.is_uncertain IS 'Flag indiquant si le mapping nécessite vérification par le gestionnaire';
COMMENT ON COLUMN pda_piano_mappings.uncertainty_note IS 'Note du gestionnaire expliquant l''incertitude';

