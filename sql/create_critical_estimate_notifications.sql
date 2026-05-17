-- Table de déduplication pour les digests quotidiens envoyés par le système
-- de briefings. Partagée entre plusieurs workflows via la colonne `kind` :
--   - 'critical_louise'  — digest 7h de soumissions critiques à Louise
--                          (voir modules/briefing/critical_estimate_digest.py)
--   - 'info_followup'    — digest 8h de soumissions sans relance à info@
--                          (voir modules/briefing/follow_up_digest.py)
--
-- Un enregistrement par (kind, client, estimate_number, sent_at). La
-- déduplication évite de re-notifier le même couple pendant DEDUP_WINDOW_DAYS.
--
-- Contexte : demandé par Allan 2026-04-15.

CREATE TABLE IF NOT EXISTS critical_estimate_notifications (
    id SERIAL PRIMARY KEY,
    kind TEXT NOT NULL DEFAULT 'critical_louise',
    client_external_id TEXT NOT NULL,
    estimate_number INTEGER NOT NULL,
    appointment_external_id TEXT,
    estimate_total_cents INTEGER,
    estimate_date TEXT,
    estimate_is_archived BOOLEAN DEFAULT FALSE,
    sent_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index pour accélérer la vérification de déduplication par kind
CREATE INDEX IF NOT EXISTS idx_critical_est_notif_dedup
ON critical_estimate_notifications (kind, client_external_id, estimate_number, sent_at DESC);

-- Reload PostgREST schema cache
NOTIFY pgrst, 'reload schema';
