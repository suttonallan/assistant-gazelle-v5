-- ============================================================================
-- NETTOYAGE COMPLET: Supprimer le trigger et réinitialiser la table
-- ============================================================================
--
-- Ce script supprime le trigger SQL qui causait la soustraction automatique
-- des heures, vide la table gazelle_appointments, et la prépare pour un
-- import propre avec des données UTC pures.
--
-- Date: 2026-12-26
-- Problème résolu: Le trigger soustrayait 10h de toutes les heures importées
--

-- Étape 1: Supprimer le trigger et sa fonction
-- ============================================================================
DROP TRIGGER IF EXISTS tr_fix_api_import ON public.gazelle_appointments;
DROP FUNCTION IF EXISTS public.fn_fix_gazelle_api_time();

-- Vérifier que le trigger a été supprimé
SELECT
    trigger_name,
    event_manipulation,
    action_statement
FROM information_schema.triggers
WHERE event_object_table = 'gazelle_appointments';

-- Devrait retourner: aucune ligne (0 résultats)


-- Étape 2: Vider complètement la table
-- ============================================================================
TRUNCATE TABLE public.gazelle_appointments RESTART IDENTITY CASCADE;

-- Vérifier que la table est vide
SELECT COUNT(*) as total_appointments FROM public.gazelle_appointments;
-- Devrait retourner: 0


-- Étape 3: Vérifier la structure de la table
-- ============================================================================
SELECT
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE table_name = 'gazelle_appointments'
ORDER BY ordinal_position;

-- Devrait afficher les colonnes:
-- - id (integer)
-- - external_id (text)
-- - client_external_id (text)
-- - title (text)
-- - description (text)
-- - appointment_date (date)
-- - appointment_time (time without time zone) ← Stockera UTC pur
-- - duration_minutes (integer)
-- - status (text)
-- - technicien (text)
-- - location (text)
-- - notes (text)
-- - created_at (timestamp)
-- - updated_at (timestamp)


-- ============================================================================
-- PROCHAINES ÉTAPES (à exécuter APRÈS ce script):
-- ============================================================================
--
-- 1. Exécuter ce script SQL dans Supabase SQL Editor
--
-- 2. Relancer l'import Python:
--    python3 scripts/import_appointments_fixed.py
--
-- 3. Vérifier que les heures sont stockées en UTC pur:
--    SELECT
--      external_id,
--      title,
--      appointment_date,
--      appointment_time as time_utc
--    FROM gazelle_appointments
--    WHERE title ILIKE '%Tire le coyote%'
--    ORDER BY appointment_date, appointment_time;
--
--    Résultat attendu pour "Tire le coyote avant 8h":
--    - appointment_date: 2026-01-09
--    - appointment_time: 12:00:00 (UTC pur, pas 07:00:00!)
--
-- 4. Vérifier que les vues SQL convertissent correctement:
--    SELECT
--      external_id,
--      title,
--      appointment_date,
--      appointment_time AT TIME ZONE 'UTC' AT TIME ZONE 'America/Toronto' as time_montreal
--    FROM gazelle_appointments
--    WHERE title ILIKE '%Tire le coyote%'
--    ORDER BY appointment_date, appointment_time;
--
--    Résultat attendu pour "Tire le coyote avant 8h":
--    - time_montreal: 07:00:00 (7h AM Montréal)
--
-- ============================================================================
