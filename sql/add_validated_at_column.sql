-- Add validated_at column to track when Nicolas validates a piano's technician work
ALTER TABLE public.vincent_dindy_piano_updates
ADD COLUMN IF NOT EXISTS validated_at TIMESTAMPTZ DEFAULT NULL;
