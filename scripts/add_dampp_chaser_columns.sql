-- Ajouter les colonnes Dampp-Chaser à la table gazelle_pianos
-- Date: 2025-12-27

ALTER TABLE gazelle_pianos
ADD COLUMN IF NOT EXISTS dampp_chaser_installed BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS dampp_chaser_humidistat_model TEXT,
ADD COLUMN IF NOT EXISTS dampp_chaser_mfg_date DATE;

-- Créer un index pour rechercher rapidement les pianos avec Dampp-Chaser
CREATE INDEX IF NOT EXISTS idx_pianos_dampp_chaser 
ON gazelle_pianos(dampp_chaser_installed) 
WHERE dampp_chaser_installed = TRUE;

-- Vérifier les colonnes ajoutées
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'gazelle_pianos'
  AND column_name LIKE 'dampp%'
ORDER BY column_name;
