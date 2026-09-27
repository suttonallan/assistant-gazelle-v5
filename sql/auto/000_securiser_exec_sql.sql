-- Fonction exec_sql : permet au workflow GitHub « Migrations SQL » d'appliquer
-- les migrations sans intervention. RÉSERVÉE au rôle service_role (clé secrète
-- stockée dans GitHub/Render) : ni la clé publique (anon) ni les utilisateurs
-- connectés ne peuvent l'appeler.
CREATE OR REPLACE FUNCTION public.exec_sql(sql_query text)
RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path = public
AS $fn$ BEGIN EXECUTE sql_query; END; $fn$;
REVOKE ALL ON FUNCTION public.exec_sql(text) FROM PUBLIC;
REVOKE ALL ON FUNCTION public.exec_sql(text) FROM anon;
REVOKE ALL ON FUNCTION public.exec_sql(text) FROM authenticated;
GRANT EXECUTE ON FUNCTION public.exec_sql(text) TO service_role
