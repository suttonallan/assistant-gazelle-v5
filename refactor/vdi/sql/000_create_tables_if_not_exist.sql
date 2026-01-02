-- ==========================================
-- Migration 000: Créer toutes les tables nécessaires si elles n'existent pas
-- Date: 2026-01-02
-- Description: Script de setup initial pour système tournées Vincent d'Indy
-- ==========================================

-- ==========================================
-- 1. TABLE: tournees
-- ==========================================

CREATE TABLE IF NOT EXISTS public.tournees (
  id TEXT PRIMARY KEY,
  nom TEXT NOT NULL,
  date_debut DATE NOT NULL,
  date_fin DATE NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('planifiee', 'en_cours', 'terminee')),
  etablissement TEXT NOT NULL CHECK (etablissement IN ('vincent-dindy', 'orford', 'place-des-arts')),
  technicien_responsable TEXT NOT NULL,
  techniciens_assistants TEXT[] DEFAULT '{}',
  piano_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
  notes TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  created_by TEXT NOT NULL,

  CONSTRAINT valid_date_range CHECK (date_fin >= date_debut),
  CONSTRAINT valid_piano_ids CHECK (jsonb_typeof(piano_ids) = 'array')
);

-- Index pour performance
CREATE INDEX IF NOT EXISTS idx_tournees_etablissement ON public.tournees(etablissement);
CREATE INDEX IF NOT EXISTS idx_tournees_status ON public.tournees(status);
CREATE INDEX IF NOT EXISTS idx_tournees_technicien ON public.tournees(technicien_responsable);
CREATE INDEX IF NOT EXISTS idx_tournees_dates ON public.tournees(date_debut, date_fin);
CREATE INDEX IF NOT EXISTS idx_tournees_piano_ids ON public.tournees USING GIN(piano_ids);

-- Trigger pour updated_at automatique
CREATE OR REPLACE FUNCTION update_tournees_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS tournees_updated_at ON public.tournees;
CREATE TRIGGER tournees_updated_at
  BEFORE UPDATE ON public.tournees
  FOR EACH ROW
  EXECUTE FUNCTION update_tournees_updated_at();

-- Enable Row Level Security
ALTER TABLE public.tournees ENABLE ROW LEVEL SECURITY;

-- Policies
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'tournees' AND policyname = 'Enable read access for all users') THEN
    EXECUTE 'CREATE POLICY "Enable read access for all users" ON public.tournees FOR SELECT USING (true)';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'tournees' AND policyname = 'Enable insert for authenticated users') THEN
    EXECUTE 'CREATE POLICY "Enable insert for authenticated users" ON public.tournees FOR INSERT WITH CHECK (true)';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'tournees' AND policyname = 'Enable update for creator and admins') THEN
    EXECUTE 'CREATE POLICY "Enable update for creator and admins" ON public.tournees FOR UPDATE USING (true)';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'tournees' AND policyname = 'Enable delete for admins') THEN
    EXECUTE 'CREATE POLICY "Enable delete for admins" ON public.tournees FOR DELETE USING (true)';
  END IF;
END $$;

-- ==========================================
-- 2. TABLE: tournee_pianos (junction table)
-- ==========================================

CREATE TABLE IF NOT EXISTS public.tournee_pianos (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tournee_id TEXT NOT NULL REFERENCES public.tournees(id) ON DELETE CASCADE,
  gazelle_id TEXT NOT NULL,
  ordre INTEGER,
  is_top BOOLEAN DEFAULT false,
  ajoute_le TIMESTAMPTZ NOT NULL DEFAULT now(),
  ajoute_par TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

  CONSTRAINT unique_tournee_piano UNIQUE(tournee_id, gazelle_id)
);

CREATE INDEX IF NOT EXISTS idx_tournee_pianos_tournee ON public.tournee_pianos(tournee_id);
CREATE INDEX IF NOT EXISTS idx_tournee_pianos_gazelle ON public.tournee_pianos(gazelle_id);
CREATE INDEX IF NOT EXISTS idx_tournee_pianos_ordre ON public.tournee_pianos(tournee_id, ordre);
CREATE INDEX IF NOT EXISTS idx_tournee_pianos_is_top ON public.tournee_pianos(is_top);

-- Trigger
CREATE OR REPLACE FUNCTION update_tournee_pianos_timestamp()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_update_tournee_pianos_timestamp ON public.tournee_pianos;
CREATE TRIGGER trigger_update_tournee_pianos_timestamp
  BEFORE UPDATE ON public.tournee_pianos
  FOR EACH ROW
  EXECUTE FUNCTION update_tournee_pianos_timestamp();

-- RLS
ALTER TABLE public.tournee_pianos ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'tournee_pianos' AND policyname = 'Users can view tournee pianos') THEN
    EXECUTE 'CREATE POLICY "Users can view tournee pianos" ON public.tournee_pianos FOR SELECT TO authenticated USING (true)';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'tournee_pianos' AND policyname = 'Users can add pianos to tournees') THEN
    EXECUTE 'CREATE POLICY "Users can add pianos to tournees" ON public.tournee_pianos FOR INSERT TO authenticated WITH CHECK (true)';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'tournee_pianos' AND policyname = 'Users can update tournee pianos') THEN
    EXECUTE 'CREATE POLICY "Users can update tournee pianos" ON public.tournee_pianos FOR UPDATE TO authenticated USING (true)';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'tournee_pianos' AND policyname = 'Users can remove pianos from tournees') THEN
    EXECUTE 'CREATE POLICY "Users can remove pianos from tournees" ON public.tournee_pianos FOR DELETE TO authenticated USING (true)';
  END IF;
END $$;

-- ==========================================
-- 3. TABLE: vincent_dindy_piano_updates
-- ==========================================

CREATE TABLE IF NOT EXISTS public.vincent_dindy_piano_updates (
  piano_id TEXT PRIMARY KEY,
  status TEXT CHECK (status IN ('normal', 'proposed', 'top', 'completed')),
  usage TEXT,
  a_faire TEXT,
  travail TEXT,
  observations TEXT,
  is_in_csv BOOLEAN DEFAULT true,
  is_hidden BOOLEAN DEFAULT false,
  completed_in_tournee_id TEXT,
  updated_by TEXT,
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Si la table existe déjà, ajouter les colonnes manquantes
DO $$
BEGIN
  -- Ajouter is_hidden si manquante
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public'
    AND table_name = 'vincent_dindy_piano_updates'
    AND column_name = 'is_hidden'
  ) THEN
    ALTER TABLE public.vincent_dindy_piano_updates
    ADD COLUMN is_hidden BOOLEAN DEFAULT false;
  END IF;

  -- Ajouter completed_in_tournee_id si manquante
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public'
    AND table_name = 'vincent_dindy_piano_updates'
    AND column_name = 'completed_in_tournee_id'
  ) THEN
    ALTER TABLE public.vincent_dindy_piano_updates
    ADD COLUMN completed_in_tournee_id TEXT;
  END IF;

  -- Ajouter travail si manquante
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public'
    AND table_name = 'vincent_dindy_piano_updates'
    AND column_name = 'travail'
  ) THEN
    ALTER TABLE public.vincent_dindy_piano_updates
    ADD COLUMN travail TEXT;
  END IF;

  -- Ajouter observations si manquante
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public'
    AND table_name = 'vincent_dindy_piano_updates'
    AND column_name = 'observations'
  ) THEN
    ALTER TABLE public.vincent_dindy_piano_updates
    ADD COLUMN observations TEXT;
  END IF;

  -- Ajouter a_faire si manquante
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public'
    AND table_name = 'vincent_dindy_piano_updates'
    AND column_name = 'a_faire'
  ) THEN
    ALTER TABLE public.vincent_dindy_piano_updates
    ADD COLUMN a_faire TEXT;
  END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_piano_updates_status
  ON public.vincent_dindy_piano_updates(status);

CREATE INDEX IF NOT EXISTS idx_piano_updates_tournee
  ON public.vincent_dindy_piano_updates(completed_in_tournee_id);

CREATE INDEX IF NOT EXISTS idx_piano_updates_updated_at
  ON public.vincent_dindy_piano_updates(updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_piano_updates_is_hidden
  ON public.vincent_dindy_piano_updates(is_hidden)
  WHERE is_hidden = true;

-- Trigger
CREATE OR REPLACE FUNCTION update_vincent_dindy_piano_updates_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_update_vincent_dindy_piano_updates_updated_at
  ON public.vincent_dindy_piano_updates;

CREATE TRIGGER trigger_update_vincent_dindy_piano_updates_updated_at
  BEFORE UPDATE ON public.vincent_dindy_piano_updates
  FOR EACH ROW
  EXECUTE FUNCTION update_vincent_dindy_piano_updates_updated_at();

-- RLS
ALTER TABLE public.vincent_dindy_piano_updates ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'vincent_dindy_piano_updates' AND policyname = 'Enable read access for all users') THEN
    EXECUTE 'CREATE POLICY "Enable read access for all users" ON public.vincent_dindy_piano_updates FOR SELECT USING (true)';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'vincent_dindy_piano_updates' AND policyname = 'Enable insert/update for all users') THEN
    EXECUTE 'CREATE POLICY "Enable insert/update for all users" ON public.vincent_dindy_piano_updates FOR ALL USING (true) WITH CHECK (true)';
  END IF;
END $$;

-- Enable realtime
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_publication_tables
    WHERE pubname = 'supabase_realtime'
    AND schemaname = 'public'
    AND tablename = 'vincent_dindy_piano_updates'
  ) THEN
    ALTER PUBLICATION supabase_realtime ADD TABLE public.vincent_dindy_piano_updates;
  END IF;
END $$;

-- ==========================================
-- VALIDATION
-- ==========================================

DO $$
DECLARE
  table_count INTEGER;
BEGIN
  SELECT COUNT(*) INTO table_count
  FROM pg_tables
  WHERE schemaname = 'public'
  AND tablename IN ('tournees', 'tournee_pianos', 'vincent_dindy_piano_updates');

  RAISE NOTICE '✅ Migration 000 terminée:';
  RAISE NOTICE '   - % tables créées/vérifiées', table_count;
  RAISE NOTICE '   - tournees: structure tournées';
  RAISE NOTICE '   - tournee_pianos: relation many-to-many';
  RAISE NOTICE '   - vincent_dindy_piano_updates: états et notes pianos';
  RAISE NOTICE '';
  RAISE NOTICE '📝 Prochaine étape: Exécuter 011_add_sync_tracking.sql';
END $$;
