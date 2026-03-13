-- ============================================================
-- piano_service_records — Fiches de service individuelles
--
-- Remplace la fragmentation entre 3 tables :
--   vincent_dindy_piano_updates.travail
--   vdi_service_history
--   vdi_notes_buffer
--
-- Une fiche = un piano, une visite, un cycle de vie complet.
-- Plusieurs techniciens peuvent contribuer à la même fiche.
-- ============================================================

CREATE TABLE IF NOT EXISTS public.piano_service_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Identité
    piano_id TEXT NOT NULL,
    institution_slug TEXT NOT NULL DEFAULT 'vincent-dindy',
    tournee_id UUID,  -- lien optionnel vers tournees.id

    -- Contenu du travail
    travail TEXT DEFAULT '',           -- notes du/des technicien(s)
    observations TEXT DEFAULT '',      -- observations additionnelles
    a_faire TEXT DEFAULT '',           -- copié depuis l'overlay au début de la fiche

    -- Cycle de vie : draft → completed → validated → pushed
    status TEXT NOT NULL DEFAULT 'draft'
        CHECK (status IN ('draft', 'completed', 'validated', 'pushed', 'error')),

    -- Timestamps du cycle
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    started_at TIMESTAMPTZ,           -- première note écrite
    completed_at TIMESTAMPTZ,         -- technicien clique Terminé
    validated_at TIMESTAMPTZ,         -- Nicolas valide
    pushed_at TIMESTAMPTZ,            -- poussé vers Gazelle

    -- Qui
    technician_email TEXT,            -- qui a commencé
    completed_by TEXT,                -- qui a cliqué Terminé (peut être un 2e tech)
    validated_by TEXT,                -- qui a validé (Nicolas)

    -- Référence Gazelle après push
    gazelle_event_id TEXT,
    push_error TEXT,                  -- message d'erreur si push échoué

    -- Metadata
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index pour les requêtes fréquentes
CREATE INDEX IF NOT EXISTS idx_psr_piano_institution
    ON public.piano_service_records (piano_id, institution_slug);

CREATE INDEX IF NOT EXISTS idx_psr_status
    ON public.piano_service_records (status);

CREATE INDEX IF NOT EXISTS idx_psr_institution_status
    ON public.piano_service_records (institution_slug, status);

-- Index pour trouver la fiche active d'un piano (draft ou completed, pas encore pushed)
CREATE INDEX IF NOT EXISTS idx_psr_active_record
    ON public.piano_service_records (piano_id, institution_slug, status)
    WHERE status IN ('draft', 'completed');

-- Index pour le push en lot : toutes les fiches validées
CREATE INDEX IF NOT EXISTS idx_psr_ready_for_push
    ON public.piano_service_records (institution_slug, status)
    WHERE status = 'validated';

-- Index pour "dernier service" : dernière fiche poussée par piano
CREATE INDEX IF NOT EXISTS idx_psr_last_pushed
    ON public.piano_service_records (piano_id, institution_slug, pushed_at DESC)
    WHERE status = 'pushed';

-- Trigger auto-update updated_at
CREATE OR REPLACE FUNCTION update_psr_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_psr_updated_at ON public.piano_service_records;
CREATE TRIGGER trg_psr_updated_at
    BEFORE UPDATE ON public.piano_service_records
    FOR EACH ROW
    EXECUTE FUNCTION update_psr_updated_at();

-- Contrainte : un seul draft ou completed par piano/institution à la fois
-- (on ne peut pas avoir 2 fiches actives pour le même piano)
CREATE UNIQUE INDEX IF NOT EXISTS idx_psr_one_active_per_piano
    ON public.piano_service_records (piano_id, institution_slug)
    WHERE status IN ('draft', 'completed', 'validated');

-- Enable RLS
ALTER TABLE public.piano_service_records ENABLE ROW LEVEL SECURITY;

-- Policy : service role a accès total
CREATE POLICY psr_service_role ON public.piano_service_records
    FOR ALL
    USING (true)
    WITH CHECK (true);

-- Commentaires
COMMENT ON TABLE public.piano_service_records IS
    'Fiches de service individuelles : une par piano, par visite. Cycle: draft → completed → validated → pushed';
COMMENT ON COLUMN public.piano_service_records.status IS
    'draft=en cours, completed=tech a fini, validated=Nicolas approuve, pushed=dans Gazelle';
COMMENT ON COLUMN public.piano_service_records.completed_at IS
    'Date utilisée comme date de service lors du push vers Gazelle';
