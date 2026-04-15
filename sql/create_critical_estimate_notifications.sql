-- Table de déduplication pour les digests quotidiens de soumissions critiques
-- envoyés à Louise. Un enregistrement par (client, soumission) notifié, avec
-- timestamp → on ne re-notifie pas le même couple avant 7 jours.
--
-- Contexte : demandé par Allan 2026-04-15. Voir
-- modules/briefing/critical_estimate_digest.py

CREATE TABLE IF NOT EXISTS critical_estimate_notifications (
    id SERIAL PRIMARY KEY,
    client_external_id TEXT NOT NULL,
    estimate_number INTEGER NOT NULL,
    appointment_external_id TEXT,
    estimate_total_cents INTEGER,
    estimate_date TEXT,
    estimate_is_archived BOOLEAN DEFAULT FALSE,
    sent_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index pour accélérer la vérification de déduplication
CREATE INDEX IF NOT EXISTS idx_critical_est_notif_dedup
ON critical_estimate_notifications (client_external_id, estimate_number, sent_at DESC);

-- Reload PostgREST schema cache
NOTIFY pgrst, 'reload schema';
