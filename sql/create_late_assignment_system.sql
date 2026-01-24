-- Script SQL pour le système d'alerte "Late Assignment"
-- Alerte les techniciens lorsqu'un RV leur est assigné/réassigné moins de 24h avant

-- ============================================================
-- 1. Table de file d'attente pour les alertes
-- ============================================================

CREATE TABLE IF NOT EXISTS late_assignment_queue (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    appointment_external_id VARCHAR(255) NOT NULL,
    technician_id VARCHAR(255) NOT NULL,
    appointment_date DATE NOT NULL,
    appointment_time TIME,
    client_name VARCHAR(255),
    location VARCHAR(255),
    scheduled_send_at TIMESTAMPTZ NOT NULL,
    sent_at TIMESTAMPTZ,
    status VARCHAR(50) DEFAULT 'pending', -- 'pending', 'sent', 'failed'
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Contrainte: un seul pending par appointment+technician
    CONSTRAINT unique_pending_appointment_tech UNIQUE (appointment_external_id, technician_id, status)
        WHERE status = 'pending'
);

-- Index pour les requêtes fréquentes
CREATE INDEX IF NOT EXISTS idx_late_assignment_queue_scheduled_send 
    ON late_assignment_queue(scheduled_send_at) 
    WHERE status = 'pending';

CREATE INDEX IF NOT EXISTS idx_late_assignment_queue_appointment 
    ON late_assignment_queue(appointment_external_id);

CREATE INDEX IF NOT EXISTS idx_late_assignment_queue_status 
    ON late_assignment_queue(status, scheduled_send_at);

-- Commentaires
COMMENT ON TABLE late_assignment_queue IS 'File d''attente pour les alertes de réassignation tardive (< 24h)';
COMMENT ON COLUMN late_assignment_queue.scheduled_send_at IS 'Heure prévue d''envoi (now + 5min ou 07h05 si nuit)';
COMMENT ON COLUMN late_assignment_queue.status IS 'pending: en attente, sent: envoyé, failed: échec';


-- ============================================================
-- 2. Ajouter colonne last_notified_tech_id à gazelle_appointments
-- ============================================================

ALTER TABLE gazelle_appointments
ADD COLUMN IF NOT EXISTS last_notified_tech_id VARCHAR(255);

-- Index pour les requêtes de comparaison
CREATE INDEX IF NOT EXISTS idx_gazelle_appointments_last_notified 
    ON gazelle_appointments(last_notified_tech_id);

COMMENT ON COLUMN gazelle_appointments.last_notified_tech_id IS 
    'ID du dernier technicien à qui une alerte a été envoyée (anti-doublon)';


-- ============================================================
-- 3. Vue pour les alertes dernière minute (pour le frontend)
-- ============================================================

CREATE OR REPLACE VIEW late_assignment_alerts AS
SELECT 
    q.id,
    q.appointment_external_id,
    q.technician_id,
    q.appointment_date,
    q.appointment_time,
    q.client_name,
    q.location,
    q.scheduled_send_at,
    q.sent_at,
    q.status,
    q.created_at,
    u.first_name || ' ' || u.last_name AS technician_name,
    u.email AS technician_email,
    a.title AS appointment_title,
    a.description AS appointment_description
FROM late_assignment_queue q
LEFT JOIN users u ON u.external_id = q.technician_id
LEFT JOIN gazelle_appointments a ON a.external_id = q.appointment_external_id
WHERE q.status IN ('pending', 'sent')
ORDER BY q.created_at DESC;

COMMENT ON VIEW late_assignment_alerts IS 
    'Vue enrichie des alertes dernière minute pour affichage frontend';
