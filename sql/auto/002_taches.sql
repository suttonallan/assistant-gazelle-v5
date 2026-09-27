-- Module Tâches (maquette Tâches Gazelle v7) : tâches d'équipe + éléments de campagne.
-- Une tâche avec « campagne » renseignée apparaît sur la carte de la campagne ;
-- sans campagne, elle apparaît dans le tableau À faire / En cours / Fait.
-- Idempotent : rejouable sans effet.
CREATE TABLE IF NOT EXISTS public.taches (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    titre text NOT NULL,
    contexte text,
    statut text NOT NULL DEFAULT 'a_faire',
    assigne text,
    echeance date,
    campagne text,
    note text,
    etapes jsonb NOT NULL DEFAULT '[]'::jsonb,
    liens jsonb NOT NULL DEFAULT '[]'::jsonb,
    source text NOT NULL DEFAULT 'manuel',
    cree_par text,
    fait_le timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS taches_statut_idx ON public.taches (statut);
CREATE INDEX IF NOT EXISTS taches_campagne_idx ON public.taches (campagne);
-- Accès uniquement via l'API (clé service) : la clé publique du frontend ne lit rien.
ALTER TABLE public.taches ENABLE ROW LEVEL SECURITY;
NOTIFY pgrst, 'reload schema'
