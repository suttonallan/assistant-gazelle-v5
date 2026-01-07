-- ==========================================
-- Script de diagnostic: Structure de la table vincent_dindy_piano_updates
-- ==========================================
-- Exécutez ce script dans Supabase SQL Editor pour voir la structure réelle de votre table
-- ==========================================

-- 1. Vérifier si la table existe
SELECT 
  CASE 
    WHEN EXISTS (
      SELECT FROM pg_tables
      WHERE schemaname = 'public'
      AND tablename = 'vincent_dindy_piano_updates'
    ) THEN '✅ Table existe'
    ELSE '❌ Table n''existe pas'
  END as table_status;

-- 2. Lister toutes les colonnes
SELECT 
  column_name,
  data_type,
  is_nullable,
  column_default,
  CASE 
    WHEN EXISTS (
      SELECT 1 FROM pg_constraint c
      JOIN pg_attribute a ON a.attrelid = c.conrelid AND a.attnum = ANY(c.conkey)
      WHERE c.contype = 'p'
      AND a.attname = column_name
      AND c.conrelid = 'public.vincent_dindy_piano_updates'::regclass
    ) THEN 'PRIMARY KEY'
    ELSE ''
  END as key_type
FROM information_schema.columns
WHERE table_schema = 'public'
AND table_name = 'vincent_dindy_piano_updates'
ORDER BY ordinal_position;

-- 3. Vérifier la clé primaire
SELECT 
  a.attname as primary_key_column
FROM pg_index i
JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
WHERE i.indrelid = 'public.vincent_dindy_piano_updates'::regclass
AND i.indisprimary;

-- 4. Compter les lignes
SELECT COUNT(*) as total_rows
FROM public.vincent_dindy_piano_updates;




