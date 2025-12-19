import { useState } from 'react'

const API_URL = import.meta.env.VITE_API_URL || 'https://assistant-gazelle-v5-api.onrender.com'

/**
 * Calculateur de Frais de Déplacement
 * 
 * Permet de calculer les frais de déplacement pour tous les techniciens
 * en fonction d'une adresse ou code postal (partiel ou complet).
 * 
 * Accepte:
 * - Code postal: "H3B 4W8" ou "H3B"
 * - Adresse partielle: "123 Rue Example"
 * - Adresse complète: "123 Rue Example, Montréal, QC H3B 4W8"
 * - Nom de client: recherche automatique de l'adresse
 */
export default function TravelFeeCalculator() {
  const [destination, setDestination] = useState('')
  const [clientName, setClientName] = useState('')
  const [loading, setLoading] = useState(false)
  const [results, setResults] = useState(null)
  const [error, setError] = useState(null)
  const [searchResults, setSearchResults] = useState([])
  const [searching, setSearching] = useState(false)
  const [selectedClient, setSelectedClient] = useState(null)

  const handleSearchClient = async () => {
    if (!clientName.trim()) {
      setSearchResults([])
      setSelectedClient(null)
      return
    }
    
    setSearching(true)
    setSearchResults([])
    setSelectedClient(null)
    
    try {
      const response = await fetch(`${API_URL}/api/admin/travel-fees/search-client?client_name=${encodeURIComponent(clientName)}`)
      const data = await response.json()
      
      if (data.results && data.results.length > 0) {
        setSearchResults(data.results)
        // Si un seul résultat, le sélectionner automatiquement
        if (data.results.length === 1) {
          handleSelectClient(data.results[0])
        }
      } else {
        setSearchResults([])
        alert('Aucun client trouvé')
      }
    } catch (err) {
      setSearchResults([])
      alert('Erreur recherche client: ' + err.message)
    } finally {
      setSearching(false)
    }
  }

  const handleSelectClient = (client) => {
    setSelectedClient(client)
    setClientName(client.client_name)
    if (client.address) {
      setDestination(client.address)
      // Auto-calcul dès qu'un client avec adresse est sélectionné
      setTimeout(() => handleCalculate(client.address, client.client_name), 0)
    }
    setSearchResults([])
  }

  const handleCalculate = async (destinationOverride = null, clientNameOverride = null) => {
    const dest = (destinationOverride ?? destination).trim()
    if (!dest) {
      alert('Veuillez entrer une adresse ou code postal')
      return
    }

    setLoading(true)
    setError(null)
    setResults(null)

    try {
      const response = await fetch(`${API_URL}/api/admin/travel-fees/calculate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          destination: dest,
          client_name: selectedClient ? selectedClient.client_name : (clientNameOverride || clientName.trim() || null)
        })
      })

      if (!response.ok) {
        let msg = 'Erreur de calcul'
        try {
          const errorData = await response.json()
          msg = errorData.detail || msg
        } catch (_) {
          msg = await response.text()
        }
        throw new Error(msg)
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
      <h2 className="text-2xl font-bold mb-6 text-gray-800">
        💰 Calculateur de frais de déplacement
      </h2>

      {/* Formulaire */}
      <div className="bg-white rounded-lg shadow-lg p-6 mb-6">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
          {/* Recherche par nom de client */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              🔍 Rechercher un client
            </label>
            <div className="flex gap-2 relative">
              <input
                type="text"
                value={clientName}
                onChange={(e) => {
                  setClientName(e.target.value)
                  setSelectedClient(null)
                  setSearchResults([])
                }}
                placeholder="Ex: Carretta ou Michelle"
                className="flex-1 border border-gray-300 rounded-lg px-4 py-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                onKeyPress={(e) => e.key === 'Enter' && handleSearchClient()}
              />
              <button
                onClick={handleSearchClient}
                disabled={searching}
                className="px-4 py-2 bg-gray-500 text-white rounded-lg hover:bg-gray-600 disabled:bg-gray-400 transition-colors"
              >
                {searching ? '⏳' : 'Chercher'}
              </button>
              
              {/* Liste déroulante des résultats */}
              {searchResults.length > 0 && (
                <div className="absolute top-full left-0 right-0 mt-1 bg-white border border-gray-300 rounded-lg shadow-lg z-10 max-h-96 overflow-y-auto">
                  {searchResults.map((client, idx) => (
                    <button
                      key={idx}
                      onClick={() => handleSelectClient(client)}
                      className={`w-full text-left px-4 py-3 hover:bg-blue-50 transition-colors border-b border-gray-100 last:border-b-0 ${
                        selectedClient?.client_id === client.client_id ? 'bg-blue-100' : ''
                      }`}
                    >
                      <div className="font-semibold text-gray-800 mb-1">
                        {client.client_name}
                        {client.type === 'contact' && (
                          <span className="ml-2 text-xs bg-purple-100 text-purple-700 px-2 py-0.5 rounded">Contact</span>
                        )}
                      </div>
                      {client.address_full && (
                        <div className="text-sm text-gray-600 mb-1">📍 {client.address_full}</div>
                      )}
                      <div className="flex flex-wrap gap-3 text-xs text-gray-500">
                        {client.phone && (
                          <span>📞 {client.phone}</span>
                        )}
                        {client.email && (
                          <span>✉️ {client.email}</span>
                        )}
                        {client.postal_code && (
                          <span>📮 {client.postal_code}</span>
                        )}
                      </div>
                      {client.notes && (
                        <div className="text-xs text-gray-400 mt-1 italic truncate">
                          {client.notes}
                        </div>
                      )}
                    </button>
                  ))}
                </div>
              )}
            </div>
            {selectedClient && (
              <div className="mt-2 p-3 bg-green-50 border border-green-200 rounded-lg text-sm text-green-800 space-y-1">
                <p className="font-semibold">Client : {selectedClient.client_name}</p>
                {selectedClient.address_full && <p>📍 {selectedClient.address_full}</p>}
                {selectedClient.phone && <p>📞 {selectedClient.phone}</p>}
                {selectedClient.email && <p>✉️ {selectedClient.email}</p>}
              </div>
            )}
          </div>

          {/* Adresse ou code postal */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              📍 Adresse ou code postal
            </label>
            <input
              type="text"
              value={destination}
              onChange={(e) => setDestination(e.target.value)}
              placeholder="Ex: H3B 4W8 ou 123 rue Example, Montréal"
              className="w-full border border-gray-300 rounded-lg px-4 py-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              onKeyPress={(e) => e.key === 'Enter' && handleCalculate()}
            />
            <p className="text-xs text-gray-500 mt-1">
              Accepte : code postal, adresse partielle ou complète
            </p>
          </div>
        </div>

        <button
          onClick={handleCalculate}
          disabled={loading || !destination.trim()}
          className="w-full md:w-auto px-8 py-3 bg-blue-600 text-white rounded-lg font-semibold hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
        >
          {loading ? '⏳ Calcul en cours...' : '🚀 Calculer les Frais'}
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
        <div className="space-y-4">
          {/* Recommandation */}
          {results.recommendation && (
            <div className="bg-green-50 border border-green-200 rounded-lg p-4">
              <p className="text-green-800 font-semibold">{results.recommendation}</p>
            </div>
          )}

          {/* Cards techniciens */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {results.results.map((tech, idx) => {
              const isCheapest = tech.technician_name === results.cheapest_technician
              const isFree = tech.is_free

              return (
                <div
                  key={tech.technician_name}
                  className={`bg-white rounded-lg shadow-lg p-6 border-2 ${
                    isCheapest
                      ? 'border-green-500 ring-2 ring-green-200'
                      : isFree
                      ? 'border-green-300'
                      : 'border-gray-200'
                  }`}
                >
                  {/* Badge recommandé */}
                  {isCheapest && (
                    <div className="mb-3">
                      <span className="inline-block bg-green-500 text-white text-xs font-bold px-3 py-1 rounded-full">
                        ⭐ Recommandé
                      </span>
                    </div>
                  )}

                  {/* Nom technicien */}
                  <h3 className="text-xl font-bold mb-4 text-gray-800">
                    👤 {tech.technician_name}
                  </h3>

                  {/* Coût */}
                  <div className="mb-4">
                    {isFree ? (
                      <div className="text-3xl font-bold text-green-600">GRATUIT</div>
                    ) : (
                      <div className="text-3xl font-bold text-orange-600">
                        {tech.total_fee.toFixed(2)}$
                      </div>
                    )}
                  </div>

                  {/* Détails */}
                  <div className="space-y-2 text-sm text-gray-600">
                    <div className="flex justify-between">
                      <span>📏 Distance:</span>
                      <span className="font-semibold">{tech.distance_km} km</span>
                    </div>
                    <div className="flex justify-between">
                      <span>⏱️ Temps:</span>
                      <span className="font-semibold">{tech.duration_minutes.toFixed(0)} min</span>
                    </div>

                    {/* Breakdown */}
                    {!isFree && (
                      <div className="mt-3 pt-3 border-t border-gray-200">
                        <p className="text-xs text-gray-500 mb-1">Détail:</p>
                        {tech.breakdown.distance_fee > 0 && (
                          <div className="flex justify-between text-xs">
                            <span>Distance:</span>
                            <span>{tech.breakdown.distance_fee.toFixed(2)}$</span>
                          </div>
                        )}
                        {tech.breakdown.time_fee > 0 && (
                          <div className="flex justify-between text-xs">
                            <span>Temps:</span>
                            <span>{tech.breakdown.time_fee.toFixed(2)}$</span>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              )
            })}
          </div>

          {/* Destination calculée */}
          <div className="bg-gray-50 rounded-lg p-4 text-sm text-gray-600">
            <p><strong>Destination:</strong> {results.destination}</p>
            {selectedClient && (
              <p><strong>Client:</strong> {selectedClient.client_name}</p>
            )}
            {results.client_name && !selectedClient && (
              <p><strong>Client:</strong> {results.client_name}</p>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

