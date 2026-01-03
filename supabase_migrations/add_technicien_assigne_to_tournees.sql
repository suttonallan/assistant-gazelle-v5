-- Migration: Ajouter colonne technicien_assigne à la table tournees
-- Date: 2026-01-02
-- Description: Permet d'assigner un technicien spécifique à une tournée

-- Ajouter la colonne technicien_assigne
ALTER TABLE tournees ADD COLUMN IF NOT EXISTS technicien_assigne TEXT;

-- Ajouter un commentaire pour documentation
COMMENT ON COLUMN tournees.technicien_assigne IS 'Technicien assigné pour exécuter le travail sur le terrain (Nicolas, Isabelle, JP, etc.)';

-- Vérification
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'tournees' AND column_name = 'technicien_assigne';
