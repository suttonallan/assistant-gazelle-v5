-- Migration: Ajouter change_type à late_assignment_queue
-- Permet de différencier les types d'alerte:
--   'new'         — nouveau rendez-vous créé
--   'reassigned'  — technicien changé
--   'rescheduled' — date/heure modifiée
--   'cancelled'   — rendez-vous annulé (plage libérée)

ALTER TABLE late_assignment_queue
ADD COLUMN IF NOT EXISTS change_type VARCHAR(50) DEFAULT 'new';

-- Ajouter aussi last_notified_schedule pour détecter les changements d'horaire
-- Format: "YYYY-MM-DD HH:MM" — snapshot de la dernière date/heure notifiée
ALTER TABLE gazelle_appointments
ADD COLUMN IF NOT EXISTS last_notified_schedule VARCHAR(50);

COMMENT ON COLUMN late_assignment_queue.change_type IS
    'Type de changement: new, reassigned, rescheduled, cancelled';

COMMENT ON COLUMN gazelle_appointments.last_notified_schedule IS
    'Snapshot date+heure du RV lors de la dernière notification (anti-doublon horaire)';
