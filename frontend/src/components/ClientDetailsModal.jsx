import { useState, useEffect } from 'react'

const API_URL = import.meta.env.VITE_API_URL || 'https://assistant-gazelle-v5-api.onrender.com'

export default function ClientDetailsModal({ clientId, onClose, onAskQuestion }) {
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [details, setDetails] = useState(null)

  useEffect(() => {
    const fetchDetails = async () => {
      try {
        setLoading(true)
        setError(null)
        // Encoder l'ID pour éviter les 404 si l'ID contient des caractères spéciaux
        const safeId = encodeURIComponent(clientId)
        const response = await fetch(`${API_URL}/assistant/client/${safeId}`)

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`)
        }

        const data = await response.json()
        setDetails(data)
      } catch (err) {
        console.error('Erreur chargement détails client:', err)
        setError(err.message)
      } finally {
        setLoading(false)
      }
    }

    if (clientId) {
      fetchDetails()
    }
  }, [clientId])

  return (
    <div 
      className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4"
      onClick={(e) => {
        if (e.target === e.currentTarget) {
          onClose()
        }
      }}
    >
      <div className="bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="sticky top-0 bg-white border-b px-6 py-4 flex justify-between items-center z-10">
          <h2 className="text-xl font-bold">Détails Client</h2>
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-gray-700 text-2xl font-bold"
          >
            ×
          </button>
        </div>

        {/* Content */}
        <div className="p-6">
          {loading && (
            <div className="text-center py-8">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
              <p className="mt-4 text-gray-600">Chargement des détails...</p>
            </div>
          )}

          {error && (
            <div className="bg-red-50 border border-red-200 rounded p-4 text-red-800">
              ❌ Erreur: {error}
            </div>
          )}

          {details && (
            <div className="space-y-6">
              {/* Informations principales */}
              <div>
                <h3 className="text-lg font-semibold mb-2">Informations</h3>
                <div className="bg-gray-50 p-4 rounded space-y-2">
                  <p><span className="font-medium">Nom:</span> {details.name}</p>
                  {details.address && <p><span className="font-medium">Adresse:</span> {details.address}</p>}
                  {details.city && <p><span className="font-medium">Ville:</span> {details.city}</p>}
                  {details.postal_code && <p><span className="font-medium">Code postal:</span> {details.postal_code}</p>}
                  {details.phone && <p><span className="font-medium">Téléphone:</span> {details.phone}</p>}
                  {details.email && <p><span className="font-medium">Email:</span> {details.email}</p>}
                  {details.type && (
                    <p>
                      <span className="font-medium">Type:</span>{' '}
                      <span className={`px-2 py-1 rounded text-xs ${
                        details.type === 'client' 
                          ? 'bg-blue-100 text-blue-800' 
                          : 'bg-green-100 text-green-800'
                      }`}>
                        {details.type === 'client' ? 'Client' : 'Contact'}
                      </span>
                    </p>
                  )}
                </div>
              </div>

              {/* Notes client */}
              {details.client_notes && (
                <div>
                  <h3 className="text-lg font-semibold mb-2">Notes Client</h3>
                  <div className="bg-yellow-50 p-4 rounded border-l-4 border-yellow-400">
                    <p className="text-sm text-gray-700 whitespace-pre-wrap">{details.client_notes}</p>
                  </div>
                </div>
              )}

              {/* Contacts associés */}
              {details.associated_contacts && details.associated_contacts.length > 0 && (
                <div>
                  <h3 className="text-lg font-semibold mb-2">Contacts Associés ({details.associated_contacts.length})</h3>
                  <div className="space-y-2">
                    {details.associated_contacts.map((contact, idx) => (
                      <div key={idx} className="bg-gray-50 p-3 rounded">
                        <p className="font-medium">{contact.name || 'N/A'}</p>
                        {contact.role && <p className="text-sm text-gray-600">{contact.role}</p>}
                        {contact.phone && <p className="text-sm">📞 {contact.phone}</p>}
                        {contact.email && <p className="text-sm">✉️ {contact.email}</p>}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Pianos */}
              {details.pianos && details.pianos.length > 0 && (
                <div>
                  <h3 className="text-lg font-semibold mb-2">🎹 Pianos ({details.pianos.length})</h3>
                  <div className="space-y-3">
                    {details.pianos.map((piano, idx) => (
                      <div key={idx} className="bg-gray-50 p-4 rounded border-l-4 border-blue-400">
                        <p className="font-medium">
                          {piano.make || ''} {piano.model || ''}
                          {piano.serial_number && <span className="text-gray-600 text-sm ml-2">(S/N: {piano.serial_number})</span>}
                        </p>
                        <div className="mt-2 space-y-1 text-sm">
                          {piano.year && <p className="text-gray-600">Année: {piano.year}</p>}
                          {piano.type && <p className="text-gray-600">Type: {piano.type}</p>}
                          {piano.location && <p className="text-gray-600">📍 {piano.location}</p>}
                          {piano.notes && (
                            <div className="mt-2 p-2 bg-blue-50 rounded">
                              <p className="text-xs text-gray-700 whitespace-pre-wrap">{piano.notes}</p>
                            </div>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Historique de service */}
              {details.service_history && details.service_history.length > 0 && (
                <div>
                  <h3 className="text-lg font-semibold mb-2">📝 Historique de Service ({details.service_history.length})</h3>
                  <div className="space-y-3 max-h-96 overflow-y-auto">
                    {details.service_history.map((note, idx) => (
                      <div key={idx} className="bg-blue-50 p-3 rounded border-l-4 border-blue-400">
                        <p className="text-sm text-gray-700 whitespace-pre-wrap">{note}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Prochains RV */}
              {details.upcoming_appointments && details.upcoming_appointments.length > 0 && (
                <div>
                  <h3 className="text-lg font-semibold mb-2">📅 Prochains Rendez-vous ({details.upcoming_appointments.length})</h3>
                  <div className="space-y-2">
                    {details.upcoming_appointments.map((appt, idx) => (
                      <div key={idx} className="bg-green-50 p-3 rounded border-l-4 border-green-400">
                        <p className="font-medium">{appt.date} à {appt.time}</p>
                        {appt.title && <p className="text-sm text-gray-600">{appt.title}</p>}
                        {appt.description && <p className="text-sm text-gray-600">{appt.description}</p>}
                        {appt.assigned_to && <p className="text-sm">Technicien: {appt.assigned_to}</p>}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Questions rapides */}
              {onAskQuestion && (
                <div className="mt-6 pt-4 border-t border-gray-200">
                  <h3 className="text-sm font-semibold text-gray-700 mb-3">💬 Questions rapides</h3>
                  <div className="flex flex-wrap gap-2">
                    <button
                      onClick={() => {
                        onAskQuestion(`frais de déplacement pour ${details.name}`)
                        onClose()
                      }}
                      className="px-3 py-1.5 text-sm bg-blue-50 text-blue-700 border border-blue-200 rounded hover:bg-blue-100 transition-colors"
                    >
                      💰 Frais de déplacement
                    </button>
                    <button
                      onClick={() => {
                        onAskQuestion(`prochains rendez-vous pour ${details.name}`)
                        onClose()
                      }}
                      className="px-3 py-1.5 text-sm bg-green-50 text-green-700 border border-green-200 rounded hover:bg-green-100 transition-colors"
                    >
                      📅 Prochains RV
                    </button>
                    <button
                      onClick={() => {
                        onAskQuestion(`résumé historique service pour ${details.name}`)
                        onClose()
                      }}
                      className="px-3 py-1.5 text-sm bg-purple-50 text-purple-700 border border-purple-200 rounded hover:bg-purple-100 transition-colors"
                    >
                      📝 Résumé historique
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
