-- Volet « Décisions » : un point « mineur » (coquille, espace, trait d'union, majuscule)
-- n'est montré qu'aux personnes qui le tranchent ; les autres l'apprennent par le rapport
-- hebdomadaire des améliorations. Idempotent.
ALTER TABLE public.decisions ADD COLUMN IF NOT EXISTS mineur boolean NOT NULL DEFAULT false;
NOTIFY pgrst, 'reload schema'
