-- Volet « Décisions » : points à trancher par Allan et Nicolas (remplace les panneaux
-- de décisions publiés à part). Chaque personne vote Approuver / À discuter / Refuser,
-- avec une note. Unanimes → décision prise ; divergence → à discuter.
--   votes    : {"allan": {"s": "ok|talk|no", "note": "...", "at": "..."}, "nicolas": {...}}
--   votants  : qui doit voter pour que la décision soit prise (par défaut les deux)
--   type     : 'point' ou 'revision_wp' (révision WordPress en attente, avec avant/après)
-- Idempotent : rejouable sans effet.
CREATE TABLE IF NOT EXISTS public.decisions (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    sujet text NOT NULL DEFAULT 'Général',
    groupe text,
    type text NOT NULL DEFAULT 'point',
    titre text NOT NULL,
    avant text,
    apres text,
    changements jsonb,
    info text,
    consigne text,
    question text,
    recommandation text,
    page text,
    lien text,
    lien_wp text,
    rid integer,
    ordre integer NOT NULL DEFAULT 0,
    votants jsonb NOT NULL DEFAULT '["allan", "nicolas"]'::jsonb,
    votes jsonb NOT NULL DEFAULT '{}'::jsonb,
    statut text NOT NULL DEFAULT 'en_attente',
    decidee_le timestamptz,
    suite text,
    realisee_le timestamptz,
    archive boolean NOT NULL DEFAULT false,
    source text,
    cle_source text,
    depuis date,
    cree_par text,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS decisions_statut_idx ON public.decisions (statut, archive);
CREATE UNIQUE INDEX IF NOT EXISTS decisions_cle_source_idx ON public.decisions (cle_source) WHERE cle_source IS NOT NULL;
-- Accès uniquement via l'API (clé service) : la clé publique du frontend ne lit rien.
ALTER TABLE public.decisions ENABLE ROW LEVEL SECURITY;
NOTIFY pgrst, 'reload schema'
