-- exec_sql(text) exécute du SQL arbitraire (SECURITY DEFINER). Par défaut Postgres
-- accorde EXECUTE à PUBLIC : la clé anon, publiée dans le frontend, pouvait donc
-- l'appeler. On la réserve au rôle service_role (GitHub Actions / Render).
GRANT EXECUTE ON FUNCTION public.exec_sql(text) TO service_role;
REVOKE ALL ON FUNCTION public.exec_sql(text) FROM PUBLIC;
REVOKE ALL ON FUNCTION public.exec_sql(text) FROM anon;
REVOKE ALL ON FUNCTION public.exec_sql(text) FROM authenticated
