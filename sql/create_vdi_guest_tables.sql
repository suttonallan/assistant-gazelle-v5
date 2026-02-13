-- =====================================================
-- VDI Guest System — Tables Buffer & Invités
-- À exécuter manuellement dans Supabase SQL Editor
-- =====================================================

-- 1. Table des techniciens invités (liens uniques)
CREATE TABLE IF NOT EXISTS vdi_guest_technicians (
    tech_token UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tech_name  TEXT NOT NULL,
    active     BOOLEAN DEFAULT TRUE,
    created_by TEXT DEFAULT 'nicolas',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE vdi_guest_technicians IS 'Liens uniques pour techniciens invités VDI';

-- 2. Table buffer des notes (auto-save)
CREATE TABLE IF NOT EXISTS vdi_notes_buffer (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tech_token  UUID NOT NULL REFERENCES vdi_guest_technicians(tech_token),
    tech_name   TEXT NOT NULL,
    piano_id    TEXT NOT NULL,
    note        TEXT NOT NULL DEFAULT '',
    status      TEXT NOT NULL DEFAULT 'draft'
                CHECK (status IN ('draft', 'validated', 'pushed')),
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);

-- Contrainte d'unicité pour l'upsert (une note par invité par piano)
ALTER TABLE vdi_notes_buffer
    ADD CONSTRAINT vdi_notes_buffer_unique_tech_piano
    UNIQUE (tech_token, piano_id);

CREATE INDEX idx_vdi_notes_status ON vdi_notes_buffer(status);
CREATE INDEX idx_vdi_notes_tech   ON vdi_notes_buffer(tech_token);

COMMENT ON TABLE vdi_notes_buffer IS 'Buffer auto-save des notes techniciens invités VDI';

-- 3. Table des pianos prioritaires (marqués par Nicolas)
CREATE TABLE IF NOT EXISTS vdi_priority_pianos (
    piano_id   TEXT PRIMARY KEY,
    set_by     TEXT DEFAULT 'nicolas',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE vdi_priority_pianos IS 'Pianos marqués prioritaires par Nicolas pour la visite VDI';

-- 4. RLS — Désactiver pour le service role (backend uniquement)
ALTER TABLE vdi_guest_technicians ENABLE ROW LEVEL SECURITY;
ALTER TABLE vdi_notes_buffer ENABLE ROW LEVEL SECURITY;
ALTER TABLE vdi_priority_pianos ENABLE ROW LEVEL SECURITY;

-- Policy : le service_role a accès complet (utilisé par le backend FastAPI)
CREATE POLICY "service_role_full_access" ON vdi_guest_technicians
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "service_role_full_access" ON vdi_notes_buffer
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "service_role_full_access" ON vdi_priority_pianos
    FOR ALL USING (auth.role() = 'service_role');

-- =====================================================
-- FIN — 3 tables créées :
--   vdi_guest_technicians  (liens invités)
--   vdi_notes_buffer       (notes auto-save)
--   vdi_priority_pianos    (marqueurs priorité)
-- =====================================================
