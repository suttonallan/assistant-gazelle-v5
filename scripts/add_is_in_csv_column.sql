-- Ajouter la colonne is_in_csv à la table vincent_dindy_piano_updates
-- Cette colonne permet de distinguer les pianos du CSV officiel vs ceux trouvés uniquement dans Gazelle

ALTER TABLE vincent_dindy_piano_updates
ADD COLUMN IF NOT EXISTS is_in_csv BOOLEAN DEFAULT TRUE;

-- Commentaire sur la colonne
COMMENT ON COLUMN vincent_dindy_piano_updates.is_in_csv IS
'Indique si le piano fait partie du CSV officiel Vincent d''Indy. TRUE = dans CSV, FALSE = trouvé uniquement dans Gazelle';

-- Index pour les requêtes filtrées
CREATE INDEX IF NOT EXISTS idx_vincent_dindy_is_in_csv
ON vincent_dindy_piano_updates(is_in_csv);
