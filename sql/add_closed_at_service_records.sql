-- ============================================================
-- piano_service_records — colonne closed_at
--
-- Permet de consigner PLUSIEURS services distincts le même jour sur un même
-- piano sans devoir valider manuellement entre les deux.
--
-- Principe :
--   closed_at IS NULL      → LA fiche active/éditable du piano (une seule).
--   closed_at IS NOT NULL  → fiche « figée » par le technicien via le bouton
--                            « Nouveau service ». Reste en 'completed' et suit
--                            le cycle normal (validation Nicolas → push Gazelle),
--                            mais sort du périmètre d'unicité pour laisser place
--                            à une nouvelle fiche.
--
-- L'invariant « une seule fiche active par piano » est donc redéfini comme
-- « une seule fiche NON figée par piano ».
-- ============================================================

ALTER TABLE public.piano_service_records
    ADD COLUMN IF NOT EXISTS closed_at TIMESTAMPTZ;

COMMENT ON COLUMN public.piano_service_records.closed_at IS
    'Non-NULL = fiche figée par le technicien (bouton « Nouveau service »). '
    'Sort du périmètre d''unicité pour permettre plusieurs services le même jour. '
    'La fiche reste completed et suit le cycle validation → push.';

-- Redéfinir l'unicité : une seule fiche NON figée (closed_at IS NULL) par piano.
-- Strictement plus permissif que l'ancien index (mêmes statuts + filtre closed_at),
-- donc ne peut pas introduire de nouvelle violation.
DROP INDEX IF EXISTS idx_psr_one_active_per_piano;
CREATE UNIQUE INDEX IF NOT EXISTS idx_psr_one_active_per_piano
    ON public.piano_service_records (piano_id, institution_slug)
    WHERE status IN ('draft', 'completed', 'validated') AND closed_at IS NULL;

-- Index pour retrouver rapidement la fiche active éditable d'un piano.
DROP INDEX IF EXISTS idx_psr_active_record;
CREATE INDEX IF NOT EXISTS idx_psr_active_record
    ON public.piano_service_records (piano_id, institution_slug, status)
    WHERE status IN ('draft', 'completed') AND closed_at IS NULL;
