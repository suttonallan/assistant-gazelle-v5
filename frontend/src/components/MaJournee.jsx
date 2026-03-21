import React, { useState, useEffect } from 'react'
import { API_URL } from '../utils/apiConfig'
import BriefingCard from './BriefingCard'
import ClientAccessPanel from './ClientAccessPanel'

/**
 * MaJournee - Briefings Intelligents pour Techniciens
 *
 * Affiche les RV du jour avec intelligence contextuelle:
 * - Profil client (langue, animaux, courtoisies)
 * - Historique technique (dernières recommandations)
 * - Fiche piano (âge, avertissements)
 *
 * Mode Super-Utilisateur (Allan):
 * - Bouton "Ajuster l'Intelligence" sur chaque carte
 * - Sauvegarde dans ai_training_feedback
 */
export default function MaJournee({ currentUser }) {
  const [briefings, setBriefings] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  // Calculer la date d'aujourd'hui en heure locale (pas UTC) pour éviter les décalages
  const getTodayLocal = () => {
    const now = new Date()
    const year = now.getFullYear()
    const month = String(now.getMonth() + 1).padStart(2, '0')
    const day = String(now.getDate()).padStart(2, '0')
    return `${year}-${month}-${day}`
  }
  const [selectedDate, setSelectedDate] = useState(getTodayLocal())

  const technicianId = currentUser?.gazelleId || currentUser?.id || null
  const isAllan = currentUser?.email === 'asutton@piano-tek.com'
  const isLouise = currentUser?.email === 'info@piano-tek.com' || currentUser?.role === 'louise'
  const [showAllTechs, setShowAllTechs] = useState(false) // Mode admin: voir tous les RV

  // Debug: voir quel technicianId est utilisé
  console.log('[MaJournee] currentUser:', currentUser?.email, 'gazelleId:', currentUser?.gazelleId, 'id:', currentUser?.id, '→ technicianId:', technicianId)

  useEffect(() => {
    loadBriefings()
  }, [selectedDate, technicianId, showAllTechs])

  const loadBriefings = async (retryCount = 0) => {
    setLoading(true)
    if (retryCount === 0) setError(null)

    try {
      let url = `${API_URL}/api/briefing/daily?date=${selectedDate}`
      // Louise: voir tous les RV (elle est assistante, pas technicienne)
      // Allan: filtrer par ses RV ou les autres
      // Autres: filtrer par leur ID
      if (isLouise) {
        // Pas de filtre — Louise voit tous les RV du jour
      } else if (technicianId) {
        if (isAllan && showAllTechs) {
          url += `&exclude_technician_id=${technicianId}`
        } else {
          url += `&technician_id=${technicianId}`
        }
      }

      const response = await fetch(url)
      if (!response.ok) {
        throw new Error(`Erreur ${response.status}`)
      }

      const data = await response.json()
      setBriefings(data.briefings || [])
      setError(null)
      setLoading(false)
    } catch (err) {
      console.error('Erreur chargement briefings:', err)
      // Retry automatique (cold start Render) — max 2 essais
      if (retryCount < 2) {
        setError('Serveur en démarrage... nouvelle tentative')
        setTimeout(() => loadBriefings(retryCount + 1), 3000)
      } else {
        setError(err.message)
        setLoading(false)
      }
    }
  }

  // Navigation entre les jours
  const changeDate = (delta) => {
    const current = new Date(selectedDate + 'T00:00:00') // Ajouter l'heure pour éviter les problèmes de timezone
    current.setDate(current.getDate() + delta)
    const year = current.getFullYear()
    const month = String(current.getMonth() + 1).padStart(2, '0')
    const day = String(current.getDate()).padStart(2, '0')
    setSelectedDate(`${year}-${month}-${day}`)
  }

  // Utiliser la même fonction pour comparer
  const isToday = selectedDate === getTodayLocal()

  const formatDateDisplay = (dateStr) => {
    // Ajouter T00:00:00 pour forcer l'interprétation en heure locale (pas UTC)
    const date = new Date(dateStr + 'T00:00:00')
    const options = { weekday: 'long', day: 'numeric', month: 'long' }
    return date.toLocaleDateString('fr-CA', options)
  }

  return (
    <div className="max-w-2xl mx-auto px-4 py-6">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-800 mb-1">
          {isLouise ? '📋 Ma Journée' : '📅 Ma Journée'}
        </h1>
        <p className="text-gray-600 text-sm">
          {isLouise
            ? 'Consultez la fiche d\'un client ou les rendez-vous du jour'
            : 'Briefings intelligents pour vos rendez-vous'}
        </p>
      </div>

      {/* Accès rapide client — Louise */}
      {isLouise && (
        <ClientAccessPanel currentUser={currentUser} />
      )}

      {/* Navigation date */}
      <div className="flex items-center justify-between mb-6 bg-white rounded-xl shadow px-4 py-3">
        <button
          onClick={() => changeDate(-1)}
          className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
        >
          ◀️
        </button>

        <div className="text-center">
          <div className="font-semibold text-gray-800 capitalize">
            {formatDateDisplay(selectedDate)}
          </div>
          {isToday && (
            <span className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded-full">
              Aujourd'hui
            </span>
          )}
        </div>

        <button
          onClick={() => changeDate(1)}
          className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
        >
          ▶️
        </button>
      </div>

      {/* Stats rapides + Toggle admin */}
      {!loading && (
        <div className="bg-gradient-to-r from-blue-50 to-indigo-50 rounded-xl px-4 py-3 mb-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="text-2xl font-bold text-blue-600">{briefings.length}</span>
              <span className="text-gray-600">rendez-vous</span>
            </div>
            <button
              onClick={loadBriefings}
              disabled={loading}
              className="text-blue-600 hover:text-blue-800 text-sm font-medium"
            >
              🔄 Actualiser
            </button>
          </div>

          {/* Toggle pour Allan: Mes RV / Tous les RV */}
          {isAllan && (
            <div className="mt-3 flex items-center gap-2">
              <button
                onClick={() => setShowAllTechs(false)}
                className={`px-3 py-1 text-sm rounded-full transition-colors ${
                  !showAllTechs
                    ? 'bg-blue-600 text-white'
                    : 'bg-white text-gray-600 hover:bg-gray-100'
                }`}
              >
                Mes RV
              </button>
              <button
                onClick={() => setShowAllTechs(true)}
                className={`px-3 py-1 text-sm rounded-full transition-colors ${
                  showAllTechs
                    ? 'bg-blue-600 text-white'
                    : 'bg-white text-gray-600 hover:bg-gray-100'
                }`}
              >
                Autres techs
              </button>
            </div>
          )}
        </div>
      )}

      {/* États */}
      {loading && (
        <div className="flex items-center justify-center py-12">
          <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-600"></div>
        </div>
      )}

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-xl mb-4">
          ⚠️ {error}
        </div>
      )}

      {!loading && !error && briefings.length === 0 && (
        <div className="text-center py-12">
          <div className="text-6xl mb-4">📭</div>
          <div className="text-gray-600">
            Aucun rendez-vous pour cette date
          </div>
          {!isToday && (
            <button
              onClick={() => setSelectedDate(getTodayLocal())}
              className="mt-4 text-blue-600 hover:text-blue-800 font-medium"
            >
              Retour à aujourd'hui
            </button>
          )}
        </div>
      )}

      {/* Liste des briefings */}
      {!loading && !error && briefings.length > 0 && (
        <div className="space-y-4">
          {briefings.map((briefing, idx) => (
            <BriefingCard
              key={briefing.appointment?.id || `${briefing.client_id}-${idx}`}
              briefing={briefing}
              currentUser={currentUser}
              onFeedbackSaved={loadBriefings}
            />
          ))}
        </div>
      )}

      {/* Mode Super-Utilisateur info */}
      {isAllan && (
        <div className="mt-8 bg-purple-50 border border-purple-200 rounded-xl px-4 py-3">
          <div className="flex items-center gap-2 text-purple-800">
            <span className="text-xl">🧠</span>
            <span className="font-medium">Mode Super-Utilisateur</span>
          </div>
          <p className="text-sm text-purple-700 mt-1">
            Cliquez sur "Ajuster l'Intelligence" sur une carte pour corriger les données.
            Vos corrections entraînent l'IA pour les prochaines analyses.
          </p>
        </div>
      )}
    </div>
  )
}
