-- Le scanner PDA écrit « detected », « already_reported » et « out_of_scope » depuis août 2026,
-- mais la contrainte d'origine (sql/029) ne les acceptait pas : ces courriels n'étaient jamais
-- marqués traités et repassaient à chaque scan horaire. On élargit la liste (idempotent).
ALTER TABLE public.processed_emails DROP CONSTRAINT IF EXISTS processed_emails_status_check;
ALTER TABLE public.processed_emails ADD CONSTRAINT processed_emails_status_check CHECK (status IN ('processed', 'failed', 'skipped', 'no_requests', 'detected', 'already_reported', 'out_of_scope', 'empty', 'reply', 'no_demands', 'watched'));
NOTIFY pgrst, 'reload schema'
