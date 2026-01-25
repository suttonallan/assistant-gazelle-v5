import React, { useState, useEffect } from 'react'
import { API_URL } from '../utils/apiConfig'
import BriefingCard from './BriefingCard'

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
  const [selectedDate, setSelectedDate] = useState(new Date().toISOString().split('T')[0])

  const technicianId = currentUser?.gazelleId || currentUser?.id || null
  const isAllan = currentUser?.email === 'asutton@piano-tek.com'

  useEffect(() => {
    loadBriefings()
  }, [selectedDate, technicianId])

  const loadBriefings = async () => {
    setLoading(true)
    setError(null)

    try {
      let url = `${API_URL}/api/briefing/daily?date=${selectedDate}`
      // Pour les techniciens (non-admin), filtrer par leur ID
      if (technicianId && !isAllan) {
        url += `&technician_id=${technicianId}`
      }

      const response = await fetch(url)
      if (!response.ok) {
        throw new Error(`Erreur ${response.status}`)
      }

      const data = await response.json()
      setBriefings(data.briefings || [])
    } catch (err) {
      console.error('Erreur chargement briefings:', err)
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  // Navigation entre les jours
  const changeDate = (delta) => {
    const current = new Date(selectedDate)
    current.setDate(current.getDate() + delta)
    setSelectedDate(current.toISOString().split('T')[0])
  }

  const isToday = selectedDate === new Date().toISOString().split('T')[0]

  const formatDateDisplay = (dateStr) => {
    const date = new Date(dateStr)
    const options = { weekday: 'long', day: 'numeric', month: 'long' }
    return date.toLocaleDateString('fr-CA', options)
  }

  return (
    <div className="max-w-2xl mx-auto px-4 py-6">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-800 mb-1">
          📅 Ma Journée
        </h1>
        <p className="text-gray-600 text-sm">
          Briefings intelligents pour vos rendez-vous
        </p>
      </div>

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

      {/* Stats rapides */}
      {!loading && briefings.length > 0 && (
        <div className="bg-gradient-to-r from-blue-50 to-indigo-50 rounded-xl px-4 py-3 mb-6 flex items-center justify-between">
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
              onClick={() => setSelectedDate(new Date().toISOString().split('T')[0])}
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
              key={briefing.client_id || idx}
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
