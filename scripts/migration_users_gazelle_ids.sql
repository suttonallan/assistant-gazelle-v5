-- Migration: Recréer table users avec Gazelle IDs
-- Date: 2025-12-28
-- Description: Convertir la table users pour utiliser les IDs Gazelle (TEXT) au lieu des UUIDs
--
-- IMPORTANT: Exécuter ce script dans Supabase SQL Editor
-- URL: https://supabase.com/dashboard/project/[PROJECT_ID]/sql/new

-- ============================================================
-- ÉTAPE 1: Supprimer FK constraint sur gazelle_timeline_entries
-- ============================================================
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'fk_timeline_user'
        AND table_name = 'gazelle_timeline_entries'
    ) THEN
        ALTER TABLE gazelle_timeline_entries DROP CONSTRAINT fk_timeline_user;
        RAISE NOTICE '✓ FK constraint fk_timeline_user supprimée';
    ELSE
        RAISE NOTICE 'ℹ FK constraint fk_timeline_user n''existe pas';
    END IF;
END $$;

-- ============================================================
-- ÉTAPE 2: Supprimer l'ancienne table users
-- ============================================================
DROP TABLE IF EXISTS users CASCADE;
-- Note: CASCADE va aussi supprimer les policies RLS associées

-- ============================================================
-- ÉTAPE 3: Créer nouvelle table users avec Gazelle IDs
-- ============================================================
CREATE TABLE users (
    id TEXT PRIMARY KEY,              -- Gazelle ID (ex: usr_ofYggsCDt2JAVeNP)
    external_id TEXT,                 -- ID externe si différent
    first_name TEXT,
    last_name TEXT,
    email TEXT,
    phone TEXT,
    role TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE users IS 'Techniciens synchronisés depuis Gazelle API';
COMMENT ON COLUMN users.id IS 'Gazelle User ID (format: usr_XXXXX)';

-- ============================================================
-- ÉTAPE 4: Créer index pour performance
-- ============================================================
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_external_id ON users(external_id);

-- ============================================================
-- ÉTAPE 5: Activer Row Level Security (RLS)
-- ============================================================
ALTER TABLE users ENABLE ROW LEVEL SECURITY;

-- Policy: Accès complet pour service_role
CREATE POLICY "Enable all access for service role"
ON users
FOR ALL
USING (true)
WITH CHECK (true);

-- ============================================================
-- ÉTAPE 6: Recréer FK constraint sur gazelle_timeline_entries
-- ============================================================
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_name = 'gazelle_timeline_entries'
    ) THEN
        ALTER TABLE gazelle_timeline_entries
        ADD CONSTRAINT fk_timeline_user
        FOREIGN KEY (user_id) REFERENCES users(id)
        ON DELETE SET NULL;

        RAISE NOTICE '✓ FK constraint fk_timeline_user recréée';
    ELSE
        RAISE NOTICE '⚠ Table gazelle_timeline_entries n''existe pas';
    END IF;
END $$;

-- ============================================================
-- VÉRIFICATION
-- ============================================================
DO $$
DECLARE
    v_count INT;
BEGIN
    -- Vérifier que la table existe
    SELECT COUNT(*) INTO v_count
    FROM information_schema.tables
    WHERE table_name = 'users';

    IF v_count > 0 THEN
        RAISE NOTICE '✓ Table users créée avec succès';

        -- Afficher le type de la colonne id
        SELECT COUNT(*) INTO v_count
        FROM information_schema.columns
        WHERE table_name = 'users'
        AND column_name = 'id'
        AND data_type = 'text';

        IF v_count > 0 THEN
            RAISE NOTICE '✓ Colonne id est de type TEXT (Gazelle IDs)';
        END IF;

        -- Vérifier RLS
        SELECT COUNT(*) INTO v_count
        FROM pg_tables
        WHERE tablename = 'users'
        AND rowsecurity = true;

        IF v_count > 0 THEN
            RAISE NOTICE '✓ RLS activé sur table users';
        END IF;
    END IF;
END $$;

-- ============================================================
-- FIN DE LA MIGRATION
-- ============================================================
-- Prochaines étapes:
-- 1. Exécuter: python3 test_sync_users.py
-- 2. Vérifier que les users sont synchronisés depuis Gazelle
-- 3. Exécuter: python3 sync_timeline_recent.py
-- 4. Vérifier que les timeline entries ont le bon user_id
