// 🔒 Jeton de connexion à l'API (remis par le serveur après vérification du PIN).
// Ajouté automatiquement à tous les appels vers l'API (fetch et axios).
import axios from 'axios'
import { API_URL } from './apiConfig'

const CLE = 'jetonApi'

export const lireJeton = () => { try { return localStorage.getItem(CLE) } catch { return null } }
export const ecrireJeton = (j) => { try { localStorage.setItem(CLE, j) } catch {} }
export const effacerJeton = () => { try { localStorage.removeItem(CLE) } catch {} }

const versApi = (url) => {
  if (!url) return false
  const u = String(url)
  if (u.startsWith('/api') || u.startsWith('api/')) return true
  if (API_URL && u.startsWith(API_URL)) return true
  return u.includes('assistant-gazelle-v5-api.onrender.com')
}

const deconnecter = () => {
  effacerJeton()
  try { localStorage.removeItem('currentUser') } catch {}
  window.location.reload()
}

export function installerJetonApi() {
  if (window.__jetonApiInstalle) return
  window.__jetonApiInstalle = true

  const fetchOriginal = window.fetch.bind(window)
  window.fetch = async (entree, options = {}) => {
    const url = typeof entree === 'string' ? entree : entree?.url
    const jeton = lireJeton()
    if (versApi(url) && jeton) {
      const entetes = new Headers(options.headers || (typeof entree !== 'string' ? entree.headers : undefined) || {})
      if (!entetes.has('Authorization')) entetes.set('Authorization', `Bearer ${jeton}`)
      options = { ...options, headers: entetes }
    }
    const rep = await fetchOriginal(entree, options)
    // Jeton expiré ou refusé → retour à l'écran PIN (jamais sans jeton : évite une boucle sur l'écran PIN)
    if (rep.status === 401 && jeton && versApi(url) && !String(url).includes('/auth/connexion')) {
      try {
        const d = await rep.clone().json()
        if (d?.detail === 'Connexion requise') deconnecter()
      } catch {}
    }
    return rep
  }

  axios.interceptors.request.use((config) => {
    const jeton = lireJeton()
    const url = (config.baseURL || '') + (config.url || '')
    if (jeton && versApi(url)) {
      config.headers = config.headers || {}
      if (!config.headers.Authorization) config.headers.Authorization = `Bearer ${jeton}`
    }
    return config
  })
  axios.interceptors.response.use((r) => r, (err) => {
    if (err?.response?.status === 401 && lireJeton() && err?.response?.data?.detail === 'Connexion requise') deconnecter()
    return Promise.reject(err)
  })
}
