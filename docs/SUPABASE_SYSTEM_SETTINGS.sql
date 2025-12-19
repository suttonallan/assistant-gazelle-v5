-- Table pour stocker les paramètres système (tokens OAuth, config, etc.)
CREATE TABLE IF NOT EXISTS public.system_settings (
    key TEXT PRIMARY KEY,
    value JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index pour améliorer les performances
CREATE INDEX IF NOT EXISTS idx_system_settings_updated_at ON public.system_settings(updated_at DESC);

-- RLS: Désactiver pour permettre l'écriture depuis le backend (service_role)
ALTER TABLE public.system_settings ENABLE ROW LEVEL SECURITY;

-- Policy: Autoriser lecture/écriture avec service_role key
CREATE POLICY "Service role can do anything" ON public.system_settings
    FOR ALL USING (true) WITH CHECK (true);

-- Commentaire pour documentation
COMMENT ON TABLE public.system_settings IS 'Stockage clé-valeur pour paramètres système (tokens OAuth, configurations)';
COMMENT ON COLUMN public.system_settings.key IS 'Identifiant unique du paramètre (ex: gazelle_oauth_token)';
COMMENT ON COLUMN public.system_settings.value IS 'Valeur JSON du paramètre';

-- Trigger pour auto-update du updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_system_settings_updated_at
    BEFORE UPDATE ON public.system_settings
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
