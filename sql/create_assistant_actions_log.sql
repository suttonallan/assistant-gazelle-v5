-- Audit log pour les actions exécutées par l'assistant via chat
-- (création/amélioration de soumissions, etc.)

CREATE TABLE IF NOT EXISTS assistant_actions_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Qui
    user_id VARCHAR(255),                  -- email ou Gazelle user id du tech
    user_role VARCHAR(50),                 -- admin|technicien|coordinator

    -- Quoi
    action_type VARCHAR(100) NOT NULL,     -- 'estimate.create'|'estimate.improve'|'estimate.preview'
    intent_text TEXT,                      -- la phrase originale du user
    target_resource VARCHAR(255),          -- numéro de soumission, ID client, etc.

    -- Contenu
    payload JSONB,                         -- payload envoyé à Gazelle (pour audit)
    response JSONB,                        -- réponse de Gazelle

    -- Statut
    status VARCHAR(50) NOT NULL,           -- 'preview'|'confirmed'|'executed'|'rejected'|'failed'
    error_message TEXT,

    -- Confirmation
    preview_token VARCHAR(255),            -- lien preview → execute
    confirmed_at TIMESTAMPTZ,

    -- Timing
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_assistant_actions_user
    ON assistant_actions_log(user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_assistant_actions_type
    ON assistant_actions_log(action_type, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_assistant_actions_token
    ON assistant_actions_log(preview_token)
    WHERE preview_token IS NOT NULL;

COMMENT ON TABLE assistant_actions_log IS
    'Journal d''audit pour les actions exécutées par l''assistant chat (création/amélioration de soumissions, etc.)';
