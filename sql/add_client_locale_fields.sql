-- Ajout des champs manquants depuis Gazelle API (découverts par introspection 2026-03-29)

-- Langue du client (le plus important!)
ALTER TABLE gazelle_clients ADD COLUMN IF NOT EXISTS locale VARCHAR(10);
COMMENT ON COLUMN gazelle_clients.locale IS 'Langue du client depuis Gazelle (fr_CA, en_US, etc.)';

-- Technicien préféré
ALTER TABLE gazelle_clients ADD COLUMN IF NOT EXISTS preferred_technician_id VARCHAR(50);

-- Type de client
ALTER TABLE gazelle_clients ADD COLUMN IF NOT EXISTS client_type VARCHAR(50);

-- État du cycle de vie
ALTER TABLE gazelle_clients ADD COLUMN IF NOT EXISTS lifecycle_state VARCHAR(50);

-- Référé par
ALTER TABLE gazelle_clients ADD COLUMN IF NOT EXISTS referred_by VARCHAR(200);

-- Ne pas contacter
ALTER TABLE gazelle_clients ADD COLUMN IF NOT EXISTS no_contact_until DATE;
ALTER TABLE gazelle_clients ADD COLUMN IF NOT EXISTS no_contact_reason VARCHAR(200);

-- Préférences de communication du contact
ALTER TABLE gazelle_clients ADD COLUMN IF NOT EXISTS wants_email BOOLEAN;
ALTER TABLE gazelle_clients ADD COLUMN IF NOT EXISTS wants_phone BOOLEAN;
ALTER TABLE gazelle_clients ADD COLUMN IF NOT EXISTS wants_text BOOLEAN;

-- Mobile confirmé (pour SMS)
ALTER TABLE gazelle_clients ADD COLUMN IF NOT EXISTS mobile_phone VARCHAR(30);

-- Index sur locale pour requêtes rapides
CREATE INDEX IF NOT EXISTS idx_clients_locale ON gazelle_clients(locale);
