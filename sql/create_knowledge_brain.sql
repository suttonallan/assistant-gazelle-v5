-- ============================================================
-- LE CERVEAU PTM — Knowledge base pour le Compagnon d'entreprise
-- Created: 2026-04-30
-- ============================================================

-- Unité atomique de connaissance
CREATE TABLE IF NOT EXISTS knowledge_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Classification
    category TEXT NOT NULL CHECK (category IN (
        'regle_metier',    -- Ce qu'on fait et ne fait pas
        'savoir_faire',    -- Comment on le fait (procédures, techniques)
        'jugement',        -- Pourquoi on le fait comme ça
        'vocabulaire',     -- Notre langue à nous
        'relation',        -- Clients, fournisseurs, particularités
        'erreur',          -- Ce qui n'a pas marché
        'procedure'        -- Workflows étape par étape
    )),
    domain TEXT NOT NULL CHECK (domain IN (
        'soumissions',     -- Création et gestion des soumissions
        'marketing',       -- Newsletter, blog, réseaux, branding
        'operations',      -- RV, PDA, VDI, Orford, briefings
        'technique',       -- Bundles, MSL, templates, réglage
        'clients',         -- Relations client, suivi, PLS
        'formation',       -- AEC, onboarding, documentation
        'admin',           -- Compta, facturation, gestion
        'general'          -- Règles transversales
    )),

    -- Contenu
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    why TEXT,                          -- Pourquoi cette règle existe
    how_to_apply TEXT,                 -- Comment/quand l'appliquer

    -- Provenance
    source TEXT DEFAULT 'manual' CHECK (source IN (
        'conversation_claude',         -- Extrait d'une session Claude Code
        'correction_allan',            -- Allan a corrigé quelque chose
        'observation_auto',            -- Détecté automatiquement
        'document_drive',              -- Extrait d'un document Drive
        'migration_memory',            -- Migré depuis les mémoires Claude Code
        'manual'                       -- Créé manuellement
    )),
    source_ref TEXT,                   -- Session ID, doc ID, commit, etc.

    -- Confiance et validation
    confidence FLOAT DEFAULT 1.0,     -- 1.0=confirmé, 0.5=inféré, 0.0=à valider
    validated_by TEXT,                 -- Qui a confirmé
    validated_at TIMESTAMPTZ,

    -- Accès par rôle
    applicable_roles TEXT[] DEFAULT '{direction}',  -- tech, admin, marketing, direction

    -- Lifecycle
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by TEXT DEFAULT 'allan',
    is_active BOOLEAN DEFAULT TRUE,
    superseded_by UUID REFERENCES knowledge_entries(id),

    -- Recherche
    tags TEXT[] DEFAULT '{}',
    search_vector TSVECTOR
);

-- Index pour la recherche full-text
CREATE INDEX IF NOT EXISTS idx_knowledge_search ON knowledge_entries USING gin(search_vector);
CREATE INDEX IF NOT EXISTS idx_knowledge_category ON knowledge_entries(category);
CREATE INDEX IF NOT EXISTS idx_knowledge_domain ON knowledge_entries(domain);
CREATE INDEX IF NOT EXISTS idx_knowledge_active ON knowledge_entries(is_active);
CREATE INDEX IF NOT EXISTS idx_knowledge_roles ON knowledge_entries USING gin(applicable_roles);

-- Trigger pour mettre à jour le search_vector automatiquement
CREATE OR REPLACE FUNCTION knowledge_search_update() RETURNS TRIGGER AS $$
BEGIN
    NEW.search_vector :=
        setweight(to_tsvector('french', COALESCE(NEW.title, '')), 'A') ||
        setweight(to_tsvector('french', COALESCE(NEW.content, '')), 'B') ||
        setweight(to_tsvector('french', COALESCE(NEW.why, '')), 'C') ||
        setweight(to_tsvector('french', COALESCE(array_to_string(NEW.tags, ' '), '')), 'B');
    NEW.updated_at := NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE TRIGGER knowledge_search_trigger
    BEFORE INSERT OR UPDATE ON knowledge_entries
    FOR EACH ROW EXECUTE FUNCTION knowledge_search_update();

-- Liens entre connaissances
CREATE TABLE IF NOT EXISTS knowledge_links (
    from_id UUID REFERENCES knowledge_entries(id) ON DELETE CASCADE,
    to_id UUID REFERENCES knowledge_entries(id) ON DELETE CASCADE,
    link_type TEXT NOT NULL CHECK (link_type IN (
        'depends_on',    -- Cette règle dépend de celle-là
        'contradicts',   -- Ces deux règles sont en tension
        'refines',       -- Précise ou nuance une autre règle
        'example_of',    -- Exemple concret d'une règle générale
        'replaces'       -- Remplace une ancienne règle
    )),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (from_id, to_id)
);

-- Documents Drive indexés
CREATE TABLE IF NOT EXISTS knowledge_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    drive_file_id TEXT NOT NULL UNIQUE,
    drive_name TEXT,
    drive_path TEXT,
    domain TEXT,
    summary TEXT,
    doc_type TEXT,                -- 'procedure', 'template', 'soumission', 'formulaire'
    applicable_roles TEXT[] DEFAULT '{direction}',
    indexed_at TIMESTAMPTZ DEFAULT NOW(),
    last_checked TIMESTAMPTZ,
    is_active BOOLEAN DEFAULT TRUE
);

CREATE INDEX IF NOT EXISTS idx_knowledge_docs_domain ON knowledge_documents(domain);
CREATE INDEX IF NOT EXISTS idx_knowledge_docs_drive ON knowledge_documents(drive_file_id);

-- Log d'apprentissage
CREATE TABLE IF NOT EXISTS knowledge_learning_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entry_id UUID REFERENCES knowledge_entries(id) ON DELETE SET NULL,
    event_type TEXT NOT NULL CHECK (event_type IN (
        'created', 'corrected', 'validated', 'deprecated', 'queried', 'feedback_positive', 'feedback_negative'
    )),
    before_value TEXT,
    after_value TEXT,
    context TEXT,
    actor TEXT DEFAULT 'allan',    -- Qui a fait l'action
    occurred_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_knowledge_log_entry ON knowledge_learning_log(entry_id);
CREATE INDEX IF NOT EXISTS idx_knowledge_log_time ON knowledge_learning_log(occurred_at);

-- Fonction de recherche dans le Cerveau
CREATE OR REPLACE FUNCTION search_knowledge(
    query_text TEXT,
    filter_domain TEXT DEFAULT NULL,
    filter_role TEXT DEFAULT NULL,
    max_results INT DEFAULT 10
) RETURNS TABLE (
    id UUID,
    title TEXT,
    content TEXT,
    category TEXT,
    domain TEXT,
    why TEXT,
    confidence FLOAT,
    rank REAL
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        ke.id,
        ke.title,
        ke.content,
        ke.category,
        ke.domain,
        ke.why,
        ke.confidence,
        ts_rank(ke.search_vector, plainto_tsquery('french', query_text)) AS rank
    FROM knowledge_entries ke
    WHERE ke.is_active = TRUE
      AND ke.search_vector @@ plainto_tsquery('french', query_text)
      AND (filter_domain IS NULL OR ke.domain = filter_domain)
      AND (filter_role IS NULL OR filter_role = ANY(ke.applicable_roles))
    ORDER BY rank DESC
    LIMIT max_results;
END;
$$ LANGUAGE plpgsql;

-- Enable RLS
ALTER TABLE knowledge_entries ENABLE ROW LEVEL SECURITY;
ALTER TABLE knowledge_documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE knowledge_learning_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE knowledge_links ENABLE ROW LEVEL SECURITY;

-- Policy: service role can do everything
CREATE POLICY "Service role full access" ON knowledge_entries FOR ALL USING (TRUE) WITH CHECK (TRUE);
CREATE POLICY "Service role full access" ON knowledge_documents FOR ALL USING (TRUE) WITH CHECK (TRUE);
CREATE POLICY "Service role full access" ON knowledge_learning_log FOR ALL USING (TRUE) WITH CHECK (TRUE);
CREATE POLICY "Service role full access" ON knowledge_links FOR ALL USING (TRUE) WITH CHECK (TRUE);
