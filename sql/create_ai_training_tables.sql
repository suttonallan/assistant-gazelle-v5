-- ============================================================
-- TABLES POUR LE SYSTÈME DE BRIEFING INTELLIGENT
-- "Ma Journée" - Intelligence Client pour Techniciens
-- ============================================================

-- 1. Table de feedback pour l'apprentissage (corrections d'Allan)
CREATE TABLE IF NOT EXISTS ai_training_feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Référence client
    client_external_id VARCHAR(50) NOT NULL,

    -- Catégorie de l'intelligence
    category VARCHAR(20) NOT NULL CHECK (category IN ('profile', 'technical', 'piano', 'general')),

    -- Champ spécifique corrigé
    field_name VARCHAR(100) NOT NULL,

    -- Valeurs
    original_value TEXT,           -- Ce que l'IA avait détecté
    corrected_value TEXT NOT NULL, -- Correction d'Allan

    -- Contexte
    source_note_id VARCHAR(50),    -- ID de la note source (timeline ou appointment)
    reasoning TEXT,                -- Explication de la correction (optionnel)

    -- Métadonnées
    created_by VARCHAR(100) NOT NULL DEFAULT 'asutton@piano-tek.com',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE
);

-- Index pour recherche rapide par client
CREATE INDEX IF NOT EXISTS idx_ai_feedback_client ON ai_training_feedback(client_external_id);
CREATE INDEX IF NOT EXISTS idx_ai_feedback_category ON ai_training_feedback(category);

-- 2. Table cache pour l'intelligence client générée
CREATE TABLE IF NOT EXISTS client_intelligence (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Référence client
    client_external_id VARCHAR(50) NOT NULL UNIQUE,

    -- ═══════════════════════════════════════════════════════════
    -- PILIER 1: PROFIL HUMAIN (Permanent)
    -- ═══════════════════════════════════════════════════════════
    profile_data JSONB DEFAULT '{}'::jsonb,
    -- Structure attendue:
    -- {
    --   "language": "FR" | "EN" | "BI",
    --   "family_members": ["Marie (épouse)", "Thomas (fils)"],
    --   "pets": ["Bella (chat)", "Max (chien)"],
    --   "courtesies": ["enlève chaussures", "offre café"],
    --   "personality": "bavard" | "discret" | "pressé",
    --   "parking_info": "stationnement arrière",
    --   "access_notes": "code 1234, 3e étage"
    -- }

    -- ═══════════════════════════════════════════════════════════
    -- PILIER 2: HISTORIQUE TECHNIQUE
    -- ═══════════════════════════════════════════════════════════
    technical_history JSONB DEFAULT '[]'::jsonb,
    -- Structure attendue (array des dernières visites):
    -- [
    --   {
    --     "date": "2026-01-15",
    --     "technician": "Nick",
    --     "recommendations": ["lubrification mécanique", "vérifier humidité"],
    --     "work_done": ["accord standard", "nettoyage clavier"],
    --     "next_action": "harmonisation recommandée"
    --   }
    -- ]

    -- ═══════════════════════════════════════════════════════════
    -- PILIER 3: FICHE PIANO
    -- ═══════════════════════════════════════════════════════════
    piano_info JSONB DEFAULT '{}'::jsonb,
    -- Structure attendue:
    -- {
    --   "piano_id": "pia_xxx",
    --   "make": "Steinway",
    --   "model": "B",
    --   "year": 1985,
    --   "type": "grand",
    --   "age_years": 41,
    --   "warnings": ["piano > 40 ans - disclaimer fragilité"],
    --   "dampp_chaser": true,
    --   "special_notes": "touches ivoire d'origine"
    -- }

    -- Métadonnées
    last_generated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    confidence_score DECIMAL(3,2) DEFAULT 0.5,  -- 0.00 à 1.00
    notes_analyzed_count INTEGER DEFAULT 0,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Index
CREATE INDEX IF NOT EXISTS idx_client_intel_updated ON client_intelligence(updated_at DESC);

-- 3. Vue pour les briefings du jour (jointure avec appointments)
CREATE OR REPLACE VIEW daily_briefings AS
SELECT
    a.id as appointment_id,
    a.external_id as appointment_external_id,
    a.appointment_date,
    a.appointment_time,
    a.title as appointment_title,
    a.technicien as technician_id,
    u.first_name as technician_first_name,
    u.last_name as technician_last_name,

    -- Client info
    c.external_id as client_external_id,
    c.company_name as client_name,
    c.first_name as client_first_name,
    c.last_name as client_last_name,

    -- Intelligence (si disponible)
    ci.profile_data,
    ci.technical_history,
    ci.piano_info,
    ci.confidence_score,
    ci.last_generated_at as intelligence_updated_at

FROM gazelle_appointments a
LEFT JOIN gazelle_clients c ON c.external_id = a.client_external_id
LEFT JOIN users u ON u.external_id = a.technicien
LEFT JOIN client_intelligence ci ON ci.client_external_id = a.client_external_id
WHERE a.appointment_date >= CURRENT_DATE
ORDER BY a.appointment_date, a.appointment_time;

-- ============================================================
-- COMMENTAIRES
-- ============================================================
COMMENT ON TABLE ai_training_feedback IS 'Corrections manuelles d''Allan pour entraîner l''IA';
COMMENT ON TABLE client_intelligence IS 'Cache des briefings générés pour chaque client';
COMMENT ON VIEW daily_briefings IS 'Vue des briefings pour les RV du jour et à venir';
