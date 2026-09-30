-- Ordre manuel des tâches (flèches ↑↓ dans le module Tâches).
-- Vide = pas d'ordre choisi : la tâche est classée par urgence/échéance comme avant.
ALTER TABLE public.taches ADD COLUMN IF NOT EXISTS ordre double precision;
NOTIFY pgrst, 'reload schema'
