-- Migration: Unifier les techniciens avec Gazelle IDs
-- Date: 2025-12-28
-- Description: Convertir la table users pour utiliser les IDs Gazelle au lieu des UUIDs

-- 1. Créer une nouvelle table temporaire avec la nouvelle structure
CREATE TABLE users_new (
    id TEXT PRIMARY KEY,  -- Gazelle ID (ex: usr_ofYggsCDt2JAVeNP)
    external_id TEXT,
    first_name TEXT,
    last_name TEXT,
    email TEXT,
    phone TEXT,
    role TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. Copier les données existantes si elles existent
-- (Skip si la table est vide ou n'a que des données test)
-- INSERT INTO users_new (id, first_name, last_name, email, created_at, updated_at)
-- SELECT id::TEXT, first_name, last_name, email, created_at, updated_at
-- FROM users;

-- 3. Supprimer l'ancienne table (attention: ceci va échouer si des FK existent)
-- DROP TABLE IF EXISTS users CASCADE;

-- 4. Renommer la nouvelle table
-- ALTER TABLE users_new RENAME TO users;

-- 5. Créer les index
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_external_id ON users(external_id);

-- 6. Activer RLS (Row Level Security)
ALTER TABLE users ENABLE ROW LEVEL SECURITY;

-- 7. Créer une politique pour permettre la lecture/écriture avec service_role
CREATE POLICY "Enable all access for service role"
ON users
FOR ALL
USING (true)
WITH CHECK (true);

-- Note: Cette migration doit être exécutée manuellement dans Supabase SQL Editor
-- car elle modifie la structure de la table users qui pourrait avoir des dépendances.
