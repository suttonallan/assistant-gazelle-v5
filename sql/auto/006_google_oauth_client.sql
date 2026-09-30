-- Connexion Google : identifiant PUBLIC de l'app (projet Google Cloud « Assistant Gazelle Connexion »,
-- client « Assistant Gazelle - site web », origine https://suttonallan.github.io).
-- Ce n'est pas un secret : il est visible dans la page de connexion de n'importe quel site Google.
-- DO NOTHING : si on change de client plus tard, on modifie system_settings sans être écrasé ici.
INSERT INTO public.system_settings (key, value) VALUES ('google_oauth_client_id', '"662756227753-4bjgu28imgk3i5sgbu8ac2s50ct34e3v.apps.googleusercontent.com"') ON CONFLICT (key) DO NOTHING
