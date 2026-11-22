-- Suivi des outils et de l'équipement partagés : qui a pris quoi.
-- Chaque outil porte une étiquette QR (gravée au laser ou collée) qui ouvre
-- l'appli sur cet outil ; le technicien touche « Je le prends » / « Je le rapporte ».
--   detenteur : 'atelier' ou la personne (allan, nicolas, jean-philippe, margot, louise)
-- Idempotent : rejouable sans effet.
CREATE TABLE IF NOT EXISTS public.outils (
    id bigserial PRIMARY KEY,
    nom text NOT NULL,
    categorie text NOT NULL DEFAULT 'Général',
    description text,
    valeur numeric,
    detenteur text NOT NULL DEFAULT 'atelier',
    depuis timestamptz NOT NULL DEFAULT now(),
    actif boolean NOT NULL DEFAULT true,
    cree_le timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.outils_mouvements (
    id bigserial PRIMARY KEY,
    outil_id bigint NOT NULL REFERENCES public.outils(id) ON DELETE CASCADE,
    action text NOT NULL,
    qui text,
    detenteur_avant text,
    detenteur_apres text,
    note text,
    le timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS outils_mouvements_outil_idx ON public.outils_mouvements (outil_id, le DESC);

ALTER TABLE public.outils ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.outils_mouvements ENABLE ROW LEVEL SECURITY;
NOTIFY pgrst, 'reload schema'
