-- Réservation en ligne (reserver.pianotechniquemontreal.com) : journal des événements,
-- conservé même quand le service de réservation redémarre.
--   type = 'etape'        : étape atteinte par un visiteur (anonyme, aucune donnée personnelle)
--   type = 'reservation'  : demande de RV envoyée à Gazelle par la nouvelle page
--   type = 'abandon'      : coordonnées remplies à la dernière étape, page quittée sans envoyer
--   type = 'hors_zone'    : demande hors zone transmise à la coordonnatrice
--   type = 'refus'        : demande refusée par Gazelle (plage prise entre-temps, etc.)
-- Idempotent : rejouable sans effet.
CREATE TABLE IF NOT EXISTS public.reservation_en_ligne_evenements (
    id bigserial PRIMARY KEY,
    cree_le timestamptz NOT NULL DEFAULT now(),
    jour date NOT NULL,
    type text NOT NULL,
    cle text,
    client_id text,
    details jsonb NOT NULL DEFAULT '{}'::jsonb
);
CREATE INDEX IF NOT EXISTS reservation_en_ligne_evenements_jour_idx
    ON public.reservation_en_ligne_evenements (jour, type);
-- Accès uniquement via l'API (clé service) : la clé publique du frontend ne lit rien.
ALTER TABLE public.reservation_en_ligne_evenements ENABLE ROW LEVEL SECURITY;
NOTIFY pgrst, 'reload schema'
