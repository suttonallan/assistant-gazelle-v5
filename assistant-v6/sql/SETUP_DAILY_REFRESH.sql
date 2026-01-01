-- ============================================================================
-- Configuration: Rafraîchissement quotidien de la vue (optionnel)
-- ============================================================================
-- Si pg_cron est disponible dans Supabase, vous pouvez automatiser le refresh
-- ============================================================================

-- Option 1: Vérifier si pg_cron est disponible
SELECT * FROM pg_extension WHERE extname = 'pg_cron';

-- Option 2: Activer pg_cron (si pas déjà activé)
-- CREATE EXTENSION IF NOT EXISTS pg_cron;

-- Option 3: Planifier le refresh quotidien à 2h du matin
-- SELECT cron.schedule(
--     'refresh-gazelle-timeline',  -- nom du job
--     '0 2 * * *',                  -- cron: tous les jours à 2h
--     'SELECT refresh_gazelle_views();'
-- );

-- Option 4: Lister les jobs cron planifiés
-- SELECT * FROM cron.job;

-- Option 5: Supprimer un job (si besoin)
-- SELECT cron.unschedule('refresh-gazelle-timeline');


-- ============================================================================
-- Alternative: Refresh manuel après import
-- ============================================================================
-- Si pg_cron n'est pas disponible, appelez manuellement après chaque import:

-- SELECT refresh_gazelle_views();
