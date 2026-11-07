-- Relais Ivo → Claude : quand Ivo ne peut pas faire une demande avec ses outils, il la
-- transmet ici ; une tâche planifiée Claude (accès complet : code, API, Front, Gazelle)
-- la reprend et répond dans le même fil Front. Idempotent.
CREATE TABLE IF NOT EXISTS public.ivo_relais (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    cree_le timestamptz NOT NULL DEFAULT now(),
    conversation_id text,
    qui text,
    demande text NOT NULL,
    contexte text,
    statut text NOT NULL DEFAULT 'ouvert',
    reponse text,
    traite_le timestamptz
);
CREATE INDEX IF NOT EXISTS ivo_relais_statut_idx ON public.ivo_relais (statut, cree_le);
ALTER TABLE public.ivo_relais ENABLE ROW LEVEL SECURITY;
NOTIFY pgrst, 'reload schema'
