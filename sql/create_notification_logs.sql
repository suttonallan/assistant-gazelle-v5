-- ============================================================
-- NOTIFICATION_LOGS - Traçabilité des notifications (v5→v6 Bridge)
-- ============================================================
-- Cette table est créée en v5 pour que la v6 hérite des données.
-- Chaque email envoyé génère une entrée pour audit/debug.

CREATE TABLE IF NOT EXISTS notification_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Référence au RV
    appointment_external_id VARCHAR NOT NULL,
    appointment_date DATE,
    appointment_time TIME,

    -- Technicien notifié
    technician_id VARCHAR NOT NULL,
    technician_name VARCHAR,
    technician_email VARCHAR,

    -- Détails notification
    notification_type VARCHAR NOT NULL, -- 'new_assignment', 'time_change', 'reminder', 'late_assignment'
    email_subject VARCHAR,
    email_body TEXT,

    -- État
    status VARCHAR DEFAULT 'pending', -- 'pending', 'sent', 'failed'
    sent_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT,

    -- Contexte (pour debug)
    trigger_source VARCHAR, -- 'sync_hourly', 'manual', 'api'
    previous_tech_id VARCHAR, -- Pour tracer le changement
    previous_time TIME,

    -- Métadonnées
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Index pour recherches fréquentes
    CONSTRAINT fk_appointment FOREIGN KEY (appointment_external_id)
        REFERENCES gazelle_appointments(external_id) ON DELETE SET NULL
);

-- Index pour performance
CREATE INDEX IF NOT EXISTS idx_notification_logs_tech ON notification_logs(technician_id);
CREATE INDEX IF NOT EXISTS idx_notification_logs_date ON notification_logs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_notification_logs_status ON notification_logs(status);
CREATE INDEX IF NOT EXISTS idx_notification_logs_appt ON notification_logs(appointment_external_id);

-- ============================================================
-- COLONNES DE MÉMOIRE sur gazelle_appointments (v6 Ready)
-- ============================================================
-- Ces colonnes permettent la "Règle d'Or" de comparaison simple

ALTER TABLE gazelle_appointments
ADD COLUMN IF NOT EXISTS last_notified_tech_id VARCHAR;

ALTER TABLE gazelle_appointments
ADD COLUMN IF NOT EXISTS last_notified_time TIME;

ALTER TABLE gazelle_appointments
ADD COLUMN IF NOT EXISTS last_notified_at TIMESTAMP WITH TIME ZONE;

-- Commentaires pour documentation
COMMENT ON TABLE notification_logs IS 'Historique de toutes les notifications envoyées aux techniciens (v5→v6 bridge)';
COMMENT ON COLUMN gazelle_appointments.last_notified_tech_id IS 'Dernier technicien notifié pour ce RV';
COMMENT ON COLUMN gazelle_appointments.last_notified_time IS 'Dernière heure notifiée (pour détecter changements)';
COMMENT ON COLUMN gazelle_appointments.last_notified_at IS 'Timestamp de la dernière notification';
