-- Script SQL pour ajouter les colonnes manquantes à la table alert_logs
-- Ces colonnes sont utilisées par le code Python mais n'existent pas encore dans Supabase

-- Colonnes principales demandées
ALTER TABLE alert_logs
ADD COLUMN IF NOT EXISTS sent_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS technician_name VARCHAR(255),
ADD COLUMN IF NOT EXISTS appointment_count INTEGER DEFAULT 1,
ADD COLUMN IF NOT EXISTS triggered_by VARCHAR(255);

-- Colonnes supplémentaires utilisées dans le payload (pour synchronisation complète)
ALTER TABLE alert_logs
ADD COLUMN IF NOT EXISTS technician_id VARCHAR(255),
ADD COLUMN IF NOT EXISTS technician_email VARCHAR(255),
ADD COLUMN IF NOT EXISTS appointment_time TIME,
ADD COLUMN IF NOT EXISTS client_name VARCHAR(255),
ADD COLUMN IF NOT EXISTS client_phone VARCHAR(255),
ADD COLUMN IF NOT EXISTS service_type VARCHAR(255),
ADD COLUMN IF NOT EXISTS title VARCHAR(255),
ADD COLUMN IF NOT EXISTS description TEXT,
ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();

-- Index pour améliorer les performances des requêtes
CREATE INDEX IF NOT EXISTS idx_alert_logs_sent_at ON alert_logs(sent_at DESC);
CREATE INDEX IF NOT EXISTS idx_alert_logs_technician_id ON alert_logs(technician_id);
CREATE INDEX IF NOT EXISTS idx_alert_logs_triggered_by ON alert_logs(triggered_by);
CREATE INDEX IF NOT EXISTS idx_alert_logs_appointment_date ON alert_logs(appointment_date);

-- Commentaires pour documentation
COMMENT ON COLUMN alert_logs.sent_at IS 'Date et heure d''envoi de l''alerte (utilisé pour tri dans /history)';
COMMENT ON COLUMN alert_logs.technician_name IS 'Nom du technicien concerné par l''alerte';
COMMENT ON COLUMN alert_logs.appointment_count IS 'Nombre de rendez-vous dans cette alerte';
COMMENT ON COLUMN alert_logs.triggered_by IS 'Identifiant de l''utilisateur/système qui a déclenché l''alerte';
COMMENT ON COLUMN alert_logs.technician_id IS 'ID externe du technicien (Gazelle)';
COMMENT ON COLUMN alert_logs.technician_email IS 'Email du technicien';
COMMENT ON COLUMN alert_logs.appointment_time IS 'Heure du rendez-vous';
COMMENT ON COLUMN alert_logs.client_name IS 'Nom du client';
COMMENT ON COLUMN alert_logs.client_phone IS 'Téléphone du client';
COMMENT ON COLUMN alert_logs.service_type IS 'Type de service du rendez-vous';
COMMENT ON COLUMN alert_logs.title IS 'Titre du rendez-vous';
COMMENT ON COLUMN alert_logs.description IS 'Description du rendez-vous';
COMMENT ON COLUMN alert_logs.updated_at IS 'Date de dernière mise à jour';

-- Mettre à jour appointment_count pour les enregistrements existants (si count existe)
UPDATE alert_logs
SET appointment_count = COALESCE(count, 1)
WHERE appointment_count IS NULL AND count IS NOT NULL;

-- Mettre à jour sent_at avec created_at pour les enregistrements existants
UPDATE alert_logs
SET sent_at = created_at
WHERE sent_at IS NULL AND created_at IS NOT NULL;
