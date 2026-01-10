-- Migration: Ajouter colonne start_datetime (CoreDateTime) à gazelle_appointments
-- Date: 2026-01-09
-- Objectif: Stocker le CoreDateTime complet avec timezone pour précision maximale

-- Ajouter la nouvelle colonne
ALTER TABLE gazelle_appointments
ADD COLUMN IF NOT EXISTS start_datetime TIMESTAMPTZ;

-- Créer un index pour les requêtes par date
CREATE INDEX IF NOT EXISTS idx_gazelle_appointments_start_datetime
ON gazelle_appointments(start_datetime);

-- Mettre à jour les valeurs existantes depuis created_at (si disponible)
UPDATE gazelle_appointments
SET start_datetime = created_at
WHERE start_datetime IS NULL AND created_at IS NOT NULL;

-- Commentaires
COMMENT ON COLUMN gazelle_appointments.start_datetime IS 'CoreDateTime complet avec timezone (UTC) - plus précis que appointment_date + appointment_time séparés';

-- Note: Les colonnes appointment_date et appointment_time sont conservées pour compatibilité
-- mais start_datetime est la source de vérité pour toutes les opérations timezone-aware
