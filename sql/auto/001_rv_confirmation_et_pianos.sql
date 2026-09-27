-- Rendez-vous : conserver la confirmation du client et TOUS les pianos du RV
-- (avant : seul le premier piano était gardé -> fausses alertes de stationnement
-- quand un RV couvre plusieurs salles à Place des Arts).
ALTER TABLE public.gazelle_appointments ADD COLUMN IF NOT EXISTS confirmed_by_client boolean;
ALTER TABLE public.gazelle_appointments ADD COLUMN IF NOT EXISTS piano_ids text[];
NOTIFY pgrst, 'reload schema'
