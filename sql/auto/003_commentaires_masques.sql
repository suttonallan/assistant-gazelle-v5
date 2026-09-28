-- Commentaires Front masqués des cartes campagne du module Tâches (le commentaire reste dans Front).
CREATE TABLE IF NOT EXISTS public.commentaires_masques (
    comment_id text PRIMARY KEY,
    masque_par text,
    created_at timestamptz NOT NULL DEFAULT now()
);
ALTER TABLE public.commentaires_masques ENABLE ROW LEVEL SECURITY;
NOTIFY pgrst, 'reload schema'
