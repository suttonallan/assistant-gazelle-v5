-- Une seule discussion Front par tâche : commentaires et avis s'y retrouvent (source unique : Front).
ALTER TABLE public.taches ADD COLUMN IF NOT EXISTS front_discussion text;
NOTIFY pgrst, 'reload schema'
