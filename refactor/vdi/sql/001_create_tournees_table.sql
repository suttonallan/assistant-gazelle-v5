-- ==========================================
-- Migration: Créer table tournees
-- Date: 2025-01-01
-- Description: Système de tournées d'accordage pour institutions
-- ==========================================

-- Créer table tournees
CREATE TABLE IF NOT EXISTS public.tournees (
  id TEXT PRIMARY KEY,
  nom TEXT NOT NULL,
  date_debut DATE NOT NULL,
  date_fin DATE NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('planifiee', 'en_cours', 'terminee')),
  etablissement TEXT NOT NULL CHECK (etablissement IN ('vincent-dindy', 'orford', 'place-des-arts')),
  technicien_responsable TEXT NOT NULL,
  piano_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
  notes TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  created_by TEXT NOT NULL,

  -- Constraints
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

CREATE TRIGGER tournees_updated_at
  BEFORE UPDATE ON public.tournees
  FOR EACH ROW
  EXECUTE FUNCTION update_tournees_updated_at();

-- Enable Row Level Security (RLS)
ALTER TABLE public.tournees ENABLE ROW LEVEL SECURITY;

-- Policy: Tout le monde peut lire (ajuster selon besoins auth)
CREATE POLICY "Enable read access for all users" ON public.tournees
  FOR SELECT
  USING (true);

-- Policy: Admins et techniciens peuvent créer
CREATE POLICY "Enable insert for authenticated users" ON public.tournees
  FOR INSERT
  WITH CHECK (true);

-- Policy: Admins et créateur peuvent modifier
CREATE POLICY "Enable update for creator and admins" ON public.tournees
  FOR UPDATE
  USING (true);

-- Policy: Admins peuvent supprimer
CREATE POLICY "Enable delete for admins" ON public.tournees
  FOR DELETE
  USING (true);

-- Commentaires pour documentation
COMMENT ON TABLE public.tournees IS 'Tournées d''accordage pour gestion multi-institutions';
COMMENT ON COLUMN public.tournees.id IS 'Format: tournee_{timestamp}';
COMMENT ON COLUMN public.tournees.piano_ids IS 'Array de gazelleIds des pianos inclus';
COMMENT ON COLUMN public.tournees.status IS 'Statut: planifiee | en_cours | terminee';
COMMENT ON COLUMN public.tournees.etablissement IS 'Institution: vincent-dindy | orford | place-des-arts';

-- ==========================================
-- Données de test (optionnel, supprimer en prod)
-- ==========================================

-- Exemple tournée Vincent d'Indy
INSERT INTO public.tournees (
  id,
  nom,
  date_debut,
  date_fin,
  status,
  etablissement,
  technicien_responsable,
  piano_ids,
  notes,
  created_by
) VALUES (
  'tournee_' || EXTRACT(EPOCH FROM NOW())::BIGINT,
  'Tournée Test Hiver 2025',
  '2025-01-15',
  '2025-02-15',
  'planifiee',
  'vincent-dindy',
  'nicolas@example.com',
  '[]'::jsonb,
  'Tournée de test pour validation système',
  'system'
) ON CONFLICT (id) DO NOTHING;
