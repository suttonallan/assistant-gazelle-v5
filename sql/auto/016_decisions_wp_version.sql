-- Volet « Décisions » : empreinte (« version ») de la révision WordPress au moment où
-- l'avant/après a été déposé. Au clic Approuver/Refuser, l'API la renvoie à WordPress :
-- si l'agent a modifié la proposition entre-temps, WordPress refuse (409) et rien n'est fait.
-- Idempotent.
ALTER TABLE public.decisions ADD COLUMN IF NOT EXISTS wp_version text;
NOTIFY pgrst, 'reload schema'
