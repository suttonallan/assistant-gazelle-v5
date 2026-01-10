-- Fix: Remplir start_datetime NULL avec appointment_date + appointment_time
-- Date: 2026-01-09
-- Problème: 11194 RV (97.7%) ont start_datetime = NULL
-- Cause: Migration SQL exécutée après import initial

-- Étape 1: Vérifier combien de RV sont concernés
SELECT
    COUNT(*) as total_null,
    COUNT(*) FILTER (WHERE appointment_date IS NOT NULL AND appointment_time IS NOT NULL) as fixable
FROM gazelle_appointments
WHERE start_datetime IS NULL;

-- Étape 2: Mettre à jour start_datetime depuis appointment_date + appointment_time
UPDATE gazelle_appointments
SET start_datetime = (
    CASE
        -- Combiner date + time en timestamptz
        WHEN appointment_date IS NOT NULL AND appointment_time IS NOT NULL
        THEN (appointment_date::text || ' ' || appointment_time::text)::timestamptz
        ELSE NULL
    END
)
WHERE start_datetime IS NULL
  AND appointment_date IS NOT NULL
  AND appointment_time IS NOT NULL;

-- Étape 3: Vérifier le résultat
SELECT
    COUNT(*) as total_appointments,
    COUNT(*) FILTER (WHERE start_datetime IS NOT NULL) as filled,
    COUNT(*) FILTER (WHERE start_datetime IS NULL) as still_null,
    ROUND(COUNT(*) FILTER (WHERE start_datetime IS NOT NULL)::numeric / COUNT(*)::numeric * 100, 1) as pct_filled
FROM gazelle_appointments;

-- Résultat attendu:
-- total_appointments: 11460
-- filled: ~11260 (98%)
-- still_null: ~200 (2% - RV sans date/heure)
-- pct_filled: 98.3%

-- Commentaire
COMMENT ON COLUMN gazelle_appointments.start_datetime IS
'CoreDateTime complet avec timezone (UTC). Source de vérité pour toutes les opérations timezone-aware. Calculé depuis appointment_date + appointment_time si manquant.';
