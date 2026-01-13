-- Ajouter la colonne 'description' à la table technician_reports si elle n'existe pas
ALTER TABLE technician_reports 
ADD COLUMN IF NOT EXISTS description TEXT;

-- S'assurer que description est NOT NULL pour les nouvelles insertions
-- (mais on ne peut pas changer en NOT NULL si des lignes existent déjà avec NULL)
-- On fait juste un comment pour documenter que c'est requis
COMMENT ON COLUMN technician_reports.description IS 'Description du travail effectué (requis)';
