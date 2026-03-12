-- Migration 029: Table pour tracker les emails PDA traités automatiquement
-- Évite les doublons lors du scan Gmail

CREATE TABLE IF NOT EXISTS processed_emails (
    id BIGSERIAL PRIMARY KEY,
    gmail_message_id TEXT NOT NULL UNIQUE,       -- ID unique du message Gmail
    gmail_thread_id TEXT,                         -- ID du thread Gmail
    sender_email TEXT NOT NULL,                   -- Expéditeur
    sender_name TEXT,                             -- Nom de l'expéditeur
    subject TEXT,                                 -- Objet du mail
    received_at TIMESTAMPTZ NOT NULL,             -- Date de réception
    processed_at TIMESTAMPTZ DEFAULT NOW(),       -- Date de traitement
    requests_created INTEGER DEFAULT 0,           -- Nombre de demandes créées
    requests_ids TEXT[],                           -- IDs des demandes créées dans place_des_arts_requests
    status TEXT DEFAULT 'processed' CHECK (status IN ('processed', 'failed', 'skipped', 'no_requests')),
    error_message TEXT,                           -- Message d'erreur si échec
    confirmation_sent BOOLEAN DEFAULT FALSE,      -- Email de confirmation envoyé ?
    raw_body_preview TEXT                          -- Premiers 500 chars du body (pour debug)
);

-- Index pour la recherche rapide par message ID
CREATE INDEX IF NOT EXISTS idx_processed_emails_gmail_id ON processed_emails(gmail_message_id);

-- Index pour le filtrage par date
CREATE INDEX IF NOT EXISTS idx_processed_emails_received ON processed_emails(received_at DESC);

-- Index pour le statut
CREATE INDEX IF NOT EXISTS idx_processed_emails_status ON processed_emails(status);
