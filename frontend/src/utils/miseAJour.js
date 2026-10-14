// Recharge automatiquement l'app quand une nouvelle version est déployée.
// Sur téléphone (surtout l'icône sur l'écran d'accueil de l'iPhone), l'app
// reste en mémoire des jours et n'affiche jamais les nouveautés : on vérifie
// au démarrage, à chaque retour au premier plan, et toutes les 10 minutes.

/* global __BUILD_ID__ */
const BUILD_ACTUEL = typeof __BUILD_ID__ !== 'undefined' ? __BUILD_ID__ : null

async function verifier() {
  if (!BUILD_ACTUEL || import.meta.env.DEV) return
  try {
    const url = `${import.meta.env.BASE_URL}version.json?t=${Date.now()}`
    const rep = await fetch(url, { cache: 'no-store' })
    if (!rep.ok) return
    const { build } = await rep.json()
    if (!build || build === BUILD_ACTUEL) return
    // Garde-fou : une seule tentative de rechargement par version
    const cle = 'ptm-recharge-' + build
    try {
      if (sessionStorage.getItem(cle)) return
      sessionStorage.setItem(cle, '1')
    } catch { /* stockage bloqué : on recharge quand même */ }
    window.location.reload()
  } catch { /* hors ligne : on réessaiera plus tard */ }
}

export function surveillerMiseAJour() {
  verifier()
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible') verifier()
  })
  window.addEventListener('pageshow', (e) => { if (e.persisted) verifier() })
  setInterval(verifier, 10 * 60 * 1000)
}
