-- Sécurité (avis Supabase du 31 oct. 2026 : rls_disabled_in_public, sensitive_columns_exposed).
-- Active la sécurité par ligne (RLS) sur TOUTES les tables du schéma public qui ne l'ont pas.
-- Sans politique, la clé publique (anon, visible dans le frontend) ne lit ni n'écrit plus rien ;
-- la clé service (API Render, GitHub Actions) contourne la RLS : rien ne change pour l'assistant.
-- Une seule instruction (le script découpe sur les points-virgules) ; idempotent ; couvre aussi
-- les tables créées plus tard, à chaque exécution du workflow.
SELECT public.exec_sql(format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY', tablename)) FROM pg_tables WHERE schemaname = 'public' AND NOT rowsecurity;
NOTIFY pgrst, 'reload schema'
