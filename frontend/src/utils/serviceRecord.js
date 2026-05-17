/**
 * Helpers pour les fiches de service VDI.
 */

/**
 * Retourne true si le piano a été poussé vers Gazelle dans les `days` derniers jours.
 * Lit `piano.last_pushed_at` (ISO-8601) exposé par l'API VDI.
 */
export function isPushedRecently(piano, days = 7) {
  const pushedAt = piano?.last_pushed_at;
  if (!pushedAt) return false;
  const ageMs = Date.now() - new Date(pushedAt).getTime();
  return ageMs >= 0 && ageMs < days * 24 * 60 * 60 * 1000;
}
