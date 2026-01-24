-- Script SQL pour le système d'alerte "Late Assignment"
-- Alerte les techniciens lorsqu'un RV leur est assigné/réassigné moins de 24h avant
--
-- IMPORTANT - PRÉREQUIS:
-- Assurez-vous que tous les techniciens ont leur ID Gazelle dans la colonne
-- external_id de la table users. Ce lien est essentiel pour:
-- 1. Récupérer l'email du technicien lors de l'envoi de l'alerte
-- 2. Afficher le nom du technicien dans la vue late_assignment_alerts
--
-- Vérification: SELECT external_id, email, first_name, last_name FROM users;
-- Tous les techniciens doivent avoir un external_id non NULL correspondant à leur ID Gazelle.

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
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Index unique partiel: un seul pending par appointment+technician
-- (Doit être créé après la table, pas comme contrainte inline)
CREATE UNIQUE INDEX IF NOT EXISTS idx_late_assignment_queue_unique_pending 
    ON late_assignment_queue(appointment_external_id, technician_id) 
    WHERE status = 'pending';

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
-- 3. Index sur users.external_id (si pas déjà existant)
-- ============================================================

-- IMPORTANT: Assurez-vous que tous les techniciens ont leur ID Gazelle
-- dans la colonne external_id de la table users.
-- Ce lien est essentiel pour récupérer l'email du technicien.

CREATE INDEX IF NOT EXISTS idx_users_external_id ON users(external_id);

COMMENT ON INDEX idx_users_external_id IS 
    'Index pour optimiser la recherche de techniciens par ID Gazelle (technician_id)';


-- ============================================================
-- 4. Vue pour les alertes dernière minute (pour le frontend)
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
    -- Lien avec users via external_id = technician_id (ID Gazelle)
    u.first_name || ' ' || u.last_name AS technician_name,
    u.email AS technician_email,
    a.title AS appointment_title,
    a.description AS appointment_description
FROM late_assignment_queue q
-- JOIN avec users: technician_id (Gazelle) = external_id (Supabase)
LEFT JOIN users u ON u.external_id = q.technician_id
LEFT JOIN gazelle_appointments a ON a.external_id = q.appointment_external_id
WHERE q.status IN ('pending', 'sent')
ORDER BY q.created_at DESC;

COMMENT ON VIEW late_assignment_alerts IS 
    'Vue enrichie des alertes dernière minute pour affichage frontend. '
    'Fait le lien entre technician_id (Gazelle) et users.external_id pour récupérer email/nom.';
