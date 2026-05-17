import { useState } from 'react'

import { API_URL } from '../../utils/apiConfig'

/**
 * Calculateur de Kilomètres Parcourus
 * 
 * Calcule les kilomètres parcourus par un technicien pour une journée complète.
 * Trajet: Maison → RV1 → RV2 → ... → Maison
 */
export default function KilometersCalculator() {
  const [technicianId, setTechnicianId] = useState('usr_HcCiFk7o0vZ9xAI0') // Nicolas par défaut
  const [date, setDate] = useState(new Date().toISOString().split('T')[0])
  const [dateEnd, setDateEnd] = useState('')
  const [quarter, setQuarter] = useState('')
  const [travelMode, setTravelMode] = useState('DRIVING')
  const [loading, setLoading] = useState(false)
  const [results, setResults] = useState(null)
  const [error, setError] = useState(null)

  const technicians = [
    { id: 'usr_HcCiFk7o0vZ9xAI0', name: 'Nicolas' },
    { id: 'usr_ofYggsCDt2JAVeNP', name: 'Allan' },
    { id: 'usr_ReUSmIJmBF86ilY1', name: 'Jean-Philippe' }
  ]

  const handleCalculate = async () => {
    if (!technicianId) {
      alert('Veuillez sélectionner un technicien')
      return
    }
    if (!date && !quarter) {
      alert('Choisissez soit une date, soit une plage (date de fin), soit un trimestre')
      return
    }

    setLoading(true)
    setError(null)
    setResults(null)

    try {
      const response = await fetch(`${API_URL}/api/admin/kilometers/calculate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          technician_id: technicianId,
          date: date,
          date_end: dateEnd || null,
          quarter: quarter || null,
          travel_mode: travelMode,
        })
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Erreur de calcul')
      }

      const data = await response.json()
      setResults(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <h2 className="text-3xl font-bold mb-6 text-gray-800">
        {travelMode === 'BICYCLING' ? '🚲' : '🚗'} Calculateur de Kilomètres Parcourus
      </h2>

      {/* Formulaire */}
      <div className="bg-white rounded-lg shadow-lg p-6 mb-6">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              👤 Technicien
            </label>
            <select
              value={technicianId}
              onChange={(e) => setTechnicianId(e.target.value)}
              className="w-full border border-gray-300 rounded-lg px-4 py-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              {technicians.map(tech => (
                <option key={tech.id} value={tech.id}>{tech.name}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              🚗 Mode de transport
            </label>
            <div className="flex gap-2">
              <button
                onClick={() => setTravelMode('DRIVING')}
                className={`flex-1 py-2 px-4 text-sm font-medium rounded-lg transition-colors ${
                  travelMode === 'DRIVING'
                    ? 'bg-blue-600 text-white shadow'
                    : 'bg-white text-gray-700 border border-gray-300 hover:bg-gray-50'
                }`}
              >
                🚗 Auto
              </button>
              <button
                onClick={() => setTravelMode('BICYCLING')}
                className={`flex-1 py-2 px-4 text-sm font-medium rounded-lg transition-colors ${
                  travelMode === 'BICYCLING'
                    ? 'bg-green-600 text-white shadow'
                    : 'bg-white text-gray-700 border border-gray-300 hover:bg-gray-50'
                }`}
              >
                🚲 Vélo
              </button>
            </div>
          </div>

          <div className="space-y-2">
            <label className="block text-sm font-medium text-gray-700">
              📅 Dates (jour ou plage) / Trimestre
            </label>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              <input
                type="date"
                value={date}
                onChange={(e) => setDate(e.target.value)}
                className="w-full border border-gray-300 rounded-lg px-4 py-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
              <input
                type="date"
                value={dateEnd}
                onChange={(e) => setDateEnd(e.target.value)}
                placeholder="Date de fin (optionnel)"
                className="w-full border border-gray-300 rounded-lg px-4 py-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
            <div className="flex gap-2 flex-wrap">
              {['Q1','Q2','Q3','Q4'].map(q => (
                <button
                  key={q}
                  onClick={() => setQuarter(q)}
                  className={`px-3 py-1 text-sm rounded border ${
                    quarter === q ? 'bg-blue-600 text-white border-blue-600' : 'bg-white text-gray-700 border-gray-300'
                  }`}
                >
                  {q}
                </button>
              ))}
              {quarter && (
                <button
                  onClick={() => setQuarter('')}
                  className="px-3 py-1 text-sm rounded border bg-gray-100 text-gray-700 border-gray-300"
                >
                  Effacer trimestre
                </button>
              )}
            </div>
            <p className="text-xs text-gray-500">
              - Renseignez une date unique OU une plage (date début + fin) OU un trimestre (Q1=jan-mars, Q2=avr-juin, Q3=jul-sep, Q4=oct-déc).<br/>
              - Le trimestre écrase la plage de dates si sélectionné.
            </p>
          </div>
        </div>

        <button
          onClick={handleCalculate}
          disabled={loading}
          className="w-full md:w-auto px-8 py-3 bg-blue-600 text-white rounded-lg font-semibold hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
        >
          {loading ? '⏳ Calcul en cours...' : '🚀 Calculer les Kilomètres'}
        </button>
      </div>

      {/* Erreur */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
          <p className="text-red-800">❌ {error}</p>
        </div>
      )}

      {/* Résultats */}
      {results && (
        <div className="space-y-6">
          {/* Résumé principal */}
          <div className={`text-white rounded-lg shadow-lg p-6 ${
            results.travel_mode === 'BICYCLING'
              ? 'bg-gradient-to-r from-green-500 to-emerald-600'
              : 'bg-gradient-to-r from-blue-500 to-purple-500'
          }`}>
            <h3 className="text-2xl font-bold mb-4">
              {results.travel_mode === 'BICYCLING' ? '🚲' : '📊'} Résumé - {results.technician_name}
              {results.travel_mode === 'BICYCLING' && <span className="text-sm font-normal ml-2 opacity-80">(vélo)</span>}
            </h3>
            <div className={`grid grid-cols-2 ${results.travel_mode === 'BICYCLING' ? 'md:grid-cols-3' : 'md:grid-cols-4'} gap-4`}>
              <div>
                <p className="text-sm opacity-90">Distance Totale</p>
                <p className="text-3xl font-bold">{results.total_km} km</p>
              </div>
              <div>
                <p className="text-sm opacity-90">Temps Total</p>
                <p className="text-3xl font-bold">{results.total_duration_minutes} min</p>
              </div>
              {results.travel_mode !== 'BICYCLING' && (
                <div>
                  <p className="text-sm opacity-90">Remboursement</p>
                  <p className="text-3xl font-bold">{results.reimbursement.toFixed(2)}$</p>
                  <p className="text-xs opacity-75">(0.72$/km)</p>
                </div>
              )}
              <div>
                <p className="text-sm opacity-90">Période</p>
                <p className="text-lg font-semibold">
                  {results.date_start === results.date_end
                    ? new Date(results.date_start).toLocaleDateString('fr-FR')
                    : `${new Date(results.date_start).toLocaleDateString('fr-FR')} - ${new Date(results.date_end).toLocaleDateString('fr-FR')}`
                  }
                </p>
              </div>
            </div>
          </div>

          {/* Segments détaillés */}
          {results.segments && results.segments.length > 0 && (
            <div className="bg-white rounded-lg shadow-lg p-6">
              <h4 className="text-xl font-bold mb-4 text-gray-800">📍 Segments Détaillés</h4>
              <div className="space-y-3">
                {results.segments.map((segment, idx) => (
                  <div key={idx} className={`border-l-4 ${results.travel_mode === 'BICYCLING' ? 'border-green-500' : 'border-blue-500'} pl-4 py-2 bg-gray-50 rounded`}>
                    <div className="flex justify-between items-start">
                      <div className="flex-1">
                        <p className="font-semibold text-gray-800">
                          {idx + 1}. {segment.from} → {segment.to}
                        </p>
                      </div>
                      <div className="text-right text-sm text-gray-600">
                        <p><strong>{segment.distance_km} km</strong></p>
                        <p>{segment.duration_text}</p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

