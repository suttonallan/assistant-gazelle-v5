-- Ouvre le module Tâches à toute l'équipe (bouton ✅ Tâches pour Nicolas, Louise, Margot, JP).
-- DO NOTHING : une fois posé, le réglage se change dans system_settings sans être écrasé ici.
INSERT INTO public.system_settings (key, value) VALUES ('flag_taches_equipe', '"true"') ON CONFLICT (key) DO NOTHING
