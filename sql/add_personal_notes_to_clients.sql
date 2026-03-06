-- Ajouter les colonnes personal_notes et preference_notes à gazelle_clients
-- Ces champs proviennent de l'API Gazelle (personalNotes, preferenceNotes)

ALTER TABLE gazelle_clients
ADD COLUMN IF NOT EXISTS personal_notes TEXT,
ADD COLUMN IF NOT EXISTS preference_notes TEXT;

-- Index pour recherche dans les notes (optionnel, utile pour l'assistant)
COMMENT ON COLUMN gazelle_clients.personal_notes IS 'Notes personnelles du client (depuis Gazelle)';
COMMENT ON COLUMN gazelle_clients.preference_notes IS 'Notes de préférences du client (depuis Gazelle)';
