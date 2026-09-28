-- Module Tâches v2 : tâche urgente + client (couleur par client dans l'échéancier).
ALTER TABLE public.taches ADD COLUMN IF NOT EXISTS urgent boolean NOT NULL DEFAULT false;
ALTER TABLE public.taches ADD COLUMN IF NOT EXISTS client text;
NOTIFY pgrst, 'reload schema'
