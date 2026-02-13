-- ================================================================
-- TABLE: follow_up_items
-- Suivi persistant des éléments "à faire" entre visites
--
-- Exemples:
--   "rondelle manquante" → persiste jusqu'à résolution
--   "prochaine fois: harmonisation" → affiché au prochain RV
--   "PLS: entretien annuel dû" → auto-détecté par le scanner
-- ================================================================

CREATE TABLE IF NOT EXISTS follow_up_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Liens vers les données Gazelle
    client_external_id TEXT NOT NULL,
    piano_external_id TEXT,                    -- Optionnel (peut être lié au client seul)
    source_timeline_entry_id TEXT,             -- Note Gazelle d'où l'item a été extrait

    -- Description de l'item
    category TEXT NOT NULL CHECK (category IN (
        'action',        -- "à faire", "prochaine fois"
        'missing_part',  -- "rondelle manquante", "vis manquante"
        'maintenance',   -- "PLS entretien annuel dû"
        'observation',   -- "bruit inhabituel", "touche colle"
        'bring_item'     -- "apporter buvards", "apporter cordes"
    )),
    description TEXT NOT NULL,                 -- Description lisible
    source_citation TEXT,                      -- Citation exacte de la note Gazelle

    -- Statut et résolution
    status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'resolved', 'dismissed')),
    detected_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    detected_by TEXT,                          -- 'ai_extraction' ou 'manual' ou user_id
    resolved_at TIMESTAMPTZ,
    resolved_by TEXT,                          -- user_id du tech qui a résolu
    resolution_note TEXT,                      -- Citation de la note de résolution
    resolution_timeline_entry_id TEXT,         -- Note Gazelle qui confirme la résolution

    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index pour requêtes fréquentes
CREATE INDEX IF NOT EXISTS idx_followup_client ON follow_up_items(client_external_id);
CREATE INDEX IF NOT EXISTS idx_followup_piano ON follow_up_items(piano_external_id);
CREATE INDEX IF NOT EXISTS idx_followup_status ON follow_up_items(status);
CREATE INDEX IF NOT EXISTS idx_followup_client_open ON follow_up_items(client_external_id, status) WHERE status = 'open';

-- Pas de doublon: même client + même description + encore ouvert
CREATE UNIQUE INDEX IF NOT EXISTS idx_followup_unique_open
ON follow_up_items(client_external_id, description) WHERE status = 'open';

-- Fonction pour résoudre un item
CREATE OR REPLACE FUNCTION resolve_follow_up_item(
    item_id UUID,
    resolver TEXT DEFAULT NULL,
    note TEXT DEFAULT NULL
)
RETURNS VOID AS $$
BEGIN
    UPDATE follow_up_items
    SET status = 'resolved',
        resolved_at = NOW(),
        resolved_by = resolver,
        resolution_note = note,
        updated_at = NOW()
    WHERE id = item_id;
END;
$$ LANGUAGE plpgsql;
