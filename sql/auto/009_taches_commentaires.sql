-- Commentaires sur une tâche : [{auteur, texte, quand}] (fil simple, le plus ancien d'abord).
ALTER TABLE public.taches ADD COLUMN IF NOT EXISTS commentaires jsonb NOT NULL DEFAULT '[]'::jsonb;
NOTIFY pgrst, 'reload schema'
