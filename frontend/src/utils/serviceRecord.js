/**
 * Helpers pour les fiches de service VDI.
 */

/**
 * Retourne true si le piano a été poussé vers Gazelle dans les `days` derniers jours.
 * Lit `piano.last_pushed_at` (ISO-8601) exposé par l'API VDI.
 *
 * 21 jours depuis le 2026-08-20 (auparavant 7). Le vert dit « c'est fait,
 * n'y retourne pas » ; trois semaines correspondent au rythme réel des tournées.
 *
 * ⚠️ Le compteur part de `last_pushed_at`, c'est-à-dire du moment où la fiche part
 * vers Gazelle — PAS du moment où le piano a été accordé. Sur VD501 : travail le
 * 5 août, poussée le 7, donc vert du 7 au 28.
 *
 * Le vert ne s'impose plus à un statut posé volontairement : un clic qui remet le
 * piano en « à faire » (jaune) ou « top » (orange) l'emporte sur le vert. C'est
 * possible parce que la poussée remet désormais `status` à 'normal'
 * (api/service_records.py), donc un 'proposed'/'top' est forcément délibéré.
 */
export function isPushedRecently(piano, days = 21) {
  const pushedAt = piano?.last_pushed_at;
  if (!pushedAt) return false;
  const ageMs = Date.now() - new Date(pushedAt).getTime();
  return ageMs >= 0 && ageMs < days * 24 * 60 * 60 * 1000;
}
