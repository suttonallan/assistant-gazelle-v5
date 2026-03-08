-- Add completed_at column to track when a technician marks a piano as "Terminé"
ALTER TABLE public.vincent_dindy_piano_updates
ADD COLUMN IF NOT EXISTS completed_at TIMESTAMPTZ DEFAULT NULL;
