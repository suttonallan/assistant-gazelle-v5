-- ==========================================
-- Migration: Ajouter colonnes d'incertitude
-- ==========================================
-- Ajoute les colonnes is_uncertain et uncertainty_note
-- à la table pda_piano_mappings existante
-- ==========================================

-- Ajouter colonne is_uncertain
ALTER TABLE pda_piano_mappings
ADD COLUMN IF NOT EXISTS is_uncertain BOOLEAN DEFAULT false;

-- Ajouter colonne uncertainty_note
ALTER TABLE pda_piano_mappings
ADD COLUMN IF NOT EXISTS uncertainty_note TEXT;

-- Commentaires
COMMENT ON COLUMN pda_piano_mappings.is_uncertain IS 'Flag indiquant si le mapping nécessite vérification par le gestionnaire';
COMMENT ON COLUMN pda_piano_mappings.uncertainty_note IS 'Note du gestionnaire expliquant l''incertitude';

