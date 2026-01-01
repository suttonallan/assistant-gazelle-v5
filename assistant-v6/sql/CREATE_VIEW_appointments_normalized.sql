-- ============================================================================
-- VUE: v_appointments_normalized
-- ============================================================================
--
-- OBJECTIF: Corriger l'erreur de timezone dans gazelle_appointments
--
-- PROBLÈME:
-- - Gazelle API retourne des heures en UTC (ex: 14:15Z)
-- - Le code de sync interprète à tort comme Eastern et ajoute 5h
-- - Résultat: DB contient 19:15 au lieu de 14:15
--
-- SOLUTION:
-- - Soustraire 5 heures pour retrouver l'heure UTC correcte
-- - Le code Python de service.py convertit ensuite UTC → Montreal correctement
--
-- VALIDATION:
-- - Caroline Lessard (evt_xMjKE8YJCDQmRg7K):
--   * Gazelle: 09:15 Toronto
--   * API: 14:15Z (UTC)
--   * DB actuelle: 19:15 UTC ❌
--   * Vue corrigée: 14:15 UTC ✅
--   * Affichage final: 09:15 Montreal ✅
--
-- DOCUMENTATION: docs/TIMEZONE_BUG_GAZELLE.md
-- ============================================================================

DROP VIEW IF EXISTS v_appointments_normalized CASCADE;

CREATE VIEW v_appointments_normalized AS
SELECT
    id,
    external_id,
    client_external_id,
    title,
    description,
    appointment_date,

    -- CORRECTION TIMEZONE: Soustraire 5 heures
    -- (Compense la double conversion dans sync_to_supabase.py)
    (appointment_time::time - interval '5 hours')::time as appointment_time,

    duration_minutes,
    status,
    technicien,
    location,
    notes,
    created_at,
    updated_at
FROM gazelle_appointments;

-- Index (hérités de la table sous-jacente, pas besoin de recréer)

-- ============================================================================
-- TEST DE VALIDATION
-- ============================================================================

-- Caroline Lessard devrait afficher 09:15 (14:15 UTC - 5h correction = 09:15)
-- Note: service.py convertit ensuite 09:15 UTC → Montreal (pas de changement en hiver)
SELECT
    external_id,
    title,
    appointment_date,
    appointment_time as heure_corrigee,
    '09:15:00'::time as heure_attendue,
    CASE
        WHEN appointment_time = '09:15:00'::time THEN '✅ CORRECT'
        ELSE '❌ ERREUR: décalage de ' ||
             EXTRACT(HOUR FROM (appointment_time - '09:15:00'::time)) || 'h'
    END as validation
FROM v_appointments_normalized
WHERE external_id = 'evt_xMjKE8YJCDQmRg7K';

-- Devrait retourner:
-- external_id              | title | appointment_date | heure_corrigee | heure_attendue | validation
-- evt_xMjKE8YJCDQmRg7K     | vd    | 2026-01-03       | 09:15:00       | 09:15:00       | ✅ CORRECT
