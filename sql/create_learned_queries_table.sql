-- ═══════════════════════════════════════════════════════════════════
-- Table: learned_queries
-- Stocke les "recettes" apprises par le Smart Query Engine.
-- Quand l'IA répond à une nouvelle question, elle sauvegarde la
-- requête Supabase générée pour la réutiliser sans LLM la prochaine fois.
-- ═══════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS learned_queries (
    id SERIAL PRIMARY KEY,

    -- La question originale qui a déclenché l'apprentissage
    original_question TEXT NOT NULL,

    -- Mots-clés normalisés pour matcher des questions similaires
    -- Ex: ["église", "accordé", "dernier"]
    normalized_keywords TEXT[] NOT NULL,

    -- La requête Supabase REST à exécuter (template JSON)
    -- Ex: {"steps": [{"table": "gazelle_clients", "filters": {...}, "select": "..."}]}
    query_template JSONB NOT NULL,

    -- Template de formatage de la réponse
    -- Ex: "Voici les {count} dernières églises accordées:\n{results}"
    response_template TEXT,

    -- Catégorie pour organisation
    -- Ex: "clients", "appointments", "invoices", "pianos", "stats"
    category TEXT DEFAULT 'general',

    -- Compteur d'utilisation (pour prioriser les recettes populaires)
    times_used INTEGER DEFAULT 1,

    -- Tracking
    last_used_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by TEXT  -- Email de la personne qui a posé la question
);

-- Index pour recherche rapide par mots-clés
CREATE INDEX IF NOT EXISTS idx_learned_queries_keywords
    ON learned_queries USING GIN (normalized_keywords);

-- Index pour catégorie
CREATE INDEX IF NOT EXISTS idx_learned_queries_category
    ON learned_queries(category);
