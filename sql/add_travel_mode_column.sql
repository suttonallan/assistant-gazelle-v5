-- Add travel_mode column to gazelle_appointments
-- Stores the Gazelle travelMode field (DRIVING, BICYCLING, WALKING, etc.)
ALTER TABLE gazelle_appointments ADD COLUMN IF NOT EXISTS travel_mode TEXT DEFAULT '';
