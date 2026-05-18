-- Ajout du status 'deleted' pour permettre le soft-delete des fiches de service
-- via le bouton admin dans la vue À valider (commit ed26a48).
-- Sans cette migration, l'UPDATE en 'deleted' viole le CHECK constraint et le backend
-- répond 500 (vu en prod 2026-05-18, fiche 0eb8e7b1-... que JP voulait retirer pour
-- VD401 Yamaha C2x).

ALTER TABLE public.piano_service_records
    DROP CONSTRAINT IF EXISTS piano_service_records_status_check;

ALTER TABLE public.piano_service_records
    ADD CONSTRAINT piano_service_records_status_check
    CHECK (status IN ('draft', 'completed', 'validated', 'pushed', 'error', 'deleted'));

-- Vérification
COMMENT ON COLUMN public.piano_service_records.status IS
    'draft → completed → validated → pushed. error si push échoué. deleted si admin retire la note avant push (soft delete).';
