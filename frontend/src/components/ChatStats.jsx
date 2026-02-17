import { useState, useEffect } from 'react'
import { API_URL } from '../utils/apiConfig'

/**
 * ChatStats - Statistiques du Chat Public (Piano Concierge)
 *
 * Admin only. Affiche:
 * - Stats globales (sessions, clients, analyses)
 * - Derniers clients identifiés
 * - Analyses photo récentes
 * - Activité par région
 * - Activité par jour (30 jours)
 */
export default function ChatStats() {
  const [summary, setSummary] = useState(null)
  const [clients, setClients] = useState([])
  const [analyses, setAnalyses] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [activeTab, setActiveTab] = useState('overview')

  useEffect(() => {
    loadData()
    const interval = setInterval(loadData, 120000) // Refresh 2min
    return () => clearInterval(interval)
  }, [])

  const loadData = async () => {
    setLoading(true)
    try {
      const [sumRes, cliRes, anaRes] = await Promise.all([
        fetch(`${API_URL}/api/chat-stats/summary`),
        fetch(`${API_URL}/api/chat-stats/clients?limit=30`),
        fetch(`${API_URL}/api/chat-stats/analyses?limit=20`)
      ])

      if (sumRes.ok) setSummary(await sumRes.json())
      if (cliRes.ok) {
        const cliData = await cliRes.json()
        setClients(cliData.clients || [])
      }
      if (anaRes.ok) {
        const anaData = await anaRes.json()
        setAnalyses(anaData.analyses || [])
      }
    } catch (err) {
      console.error('Erreur chat stats:', err)
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const formatDate = (iso) => {
    if (!iso) return '--'
    try {
      return new Date(iso).toLocaleDateString('fr-CA', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
    } catch { return '--' }
  }

  const stats = summary?.stats || {}

  return (
    <div className="max-w-7xl mx-auto px-4 py-6">
      {/* Header */}
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Chat Public - Piano Concierge</h1>
          <p className="text-sm text-gray-500">Prospects via le widget chat sur piano-tek.com</p>
        </div>
        <button
          onClick={loadData}
          className="px-4 py-2 text-sm bg-blue-50 text-blue-600 rounded-lg hover:bg-blue-100 transition-colors"
        >
          Rafraichir
        </button>
      </div>

      {error && (
        <div className="bg-red-50 text-red-700 px-4 py-3 rounded-lg mb-4 text-sm">
          Erreur: {error}
        </div>
      )}

      {/* Stats Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <StatCard label="Sessions" value={stats.total_sessions || 0} icon="💬" />
        <StatCard label="Clients identifiés" value={stats.total_clients_identified || 0} icon="👤" />
        <StatCard label="Analyses photo" value={stats.total_photo_analyses || 0} icon="📸" />
        <StatCard label="Contacts collectés" value={stats.contacts_collected || 0} icon="📧" />
      </div>

      {/* Tabs */}
      <div className="flex gap-2 mb-4 border-b border-gray-200">
        {[
          { id: 'overview', label: 'Vue globale' },
          { id: 'clients', label: 'Clients' },
          { id: 'analyses', label: 'Analyses photo' }
        ].map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors -mb-px ${
              activeTab === tab.id
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {loading && !summary ? (
        <div className="text-center py-12 text-gray-400">Chargement...</div>
      ) : (
        <>
          {/* Overview tab */}
          {activeTab === 'overview' && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Par région */}
              <div className="bg-white rounded-lg border border-gray-200 p-4">
                <h3 className="font-semibold text-gray-700 mb-3">Par région</h3>
                {(summary?.by_region || []).length === 0 ? (
                  <p className="text-sm text-gray-400">Aucune donnée</p>
                ) : (
                  <div className="space-y-2">
                    {summary.by_region.map((r, i) => (
                      <div key={i} className="flex justify-between items-center text-sm">
                        <span className="text-gray-700">{r.region}</span>
                        <div className="flex gap-3 text-gray-500">
                          <span>{r.sessions} sess.</span>
                          <span>{r.clients} cli.</span>
                          <span>{r.photo_analyses} photos</span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Intérêts */}
              <div className="bg-white rounded-lg border border-gray-200 p-4">
                <h3 className="font-semibold text-gray-700 mb-3">Types d'intérêt</h3>
                {(summary?.interests || []).length === 0 ? (
                  <p className="text-sm text-gray-400">Aucune donnée</p>
                ) : (
                  <div className="space-y-2">
                    {summary.interests.map((interest, i) => (
                      <div key={i} className="flex justify-between items-center text-sm">
                        <span className="text-gray-700 capitalize">{interest.interet.replace('_', ' ')}</span>
                        <span className="text-gray-500">{interest.sessions} sessions</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Activité 30 jours */}
              <div className="bg-white rounded-lg border border-gray-200 p-4 md:col-span-2">
                <h3 className="font-semibold text-gray-700 mb-3">Activité (30 derniers jours)</h3>
                {(summary?.daily_activity || []).length === 0 ? (
                  <p className="text-sm text-gray-400">Aucune donnée</p>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="text-left text-gray-500 border-b">
                          <th className="pb-2">Jour</th>
                          <th className="pb-2">Sessions</th>
                          <th className="pb-2">Clients uniques</th>
                          <th className="pb-2">Analyses</th>
                          <th className="pb-2">Contacts</th>
                        </tr>
                      </thead>
                      <tbody>
                        {summary.daily_activity.map((day, i) => (
                          <tr key={i} className="border-b border-gray-50">
                            <td className="py-2 text-gray-700">{day.jour}</td>
                            <td className="py-2">{day.sessions}</td>
                            <td className="py-2">{day.clients_uniques}</td>
                            <td className="py-2">{day.analyses_photo}</td>
                            <td className="py-2">{day.contacts}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Clients tab */}
          {activeTab === 'clients' && (
            <div className="bg-white rounded-lg border border-gray-200">
              {clients.length === 0 ? (
                <p className="text-sm text-gray-400 p-4">Aucun client identifié</p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="text-left text-gray-500 border-b bg-gray-50">
                        <th className="px-4 py-3">Email</th>
                        <th className="px-4 py-3">Région</th>
                        <th className="px-4 py-3">Intérêt</th>
                        <th className="px-4 py-3">Analyses</th>
                        <th className="px-4 py-3">Sessions</th>
                        <th className="px-4 py-3">Dernier contact</th>
                      </tr>
                    </thead>
                    <tbody>
                      {clients.map((c, i) => (
                        <tr key={i} className="border-b border-gray-50 hover:bg-gray-50">
                          <td className="px-4 py-3 text-gray-800 font-medium">
                            {c.email || '(anonyme)'}
                            {c.first_name && <span className="ml-2 text-gray-400">{c.first_name}</span>}
                          </td>
                          <td className="px-4 py-3 text-gray-600">{c.region || '--'}</td>
                          <td className="px-4 py-3">
                            <span className="px-2 py-0.5 bg-blue-50 text-blue-600 rounded text-xs">
                              {c.interest_type || '--'}
                            </span>
                          </td>
                          <td className="px-4 py-3">{c.photo_analyses_count || 0}</td>
                          <td className="px-4 py-3">{c.total_sessions || 0}</td>
                          <td className="px-4 py-3 text-gray-500">{formatDate(c.last_contact_at)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}

          {/* Analyses tab */}
          {activeTab === 'analyses' && (
            <div className="bg-white rounded-lg border border-gray-200">
              {analyses.length === 0 ? (
                <p className="text-sm text-gray-400 p-4">Aucune analyse</p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="text-left text-gray-500 border-b bg-gray-50">
                        <th className="px-4 py-3">Date</th>
                        <th className="px-4 py-3">Client</th>
                        <th className="px-4 py-3">Marque</th>
                        <th className="px-4 py-3">Score</th>
                        <th className="px-4 py-3">Verdict</th>
                        <th className="px-4 py-3">Type</th>
                      </tr>
                    </thead>
                    <tbody>
                      {analyses.map((a, i) => (
                        <tr key={i} className="border-b border-gray-50 hover:bg-gray-50">
                          <td className="px-4 py-3 text-gray-500">{formatDate(a.created_at)}</td>
                          <td className="px-4 py-3 text-gray-700">
                            {a.chat_clients?.email || a.chat_clients?.first_name || '(anonyme)'}
                          </td>
                          <td className="px-4 py-3 font-medium">{a.piano_brand || '--'}</td>
                          <td className="px-4 py-3">
                            {a.score != null ? (
                              <span className={`font-bold ${a.score >= 7 ? 'text-green-600' : a.score >= 4 ? 'text-yellow-600' : 'text-red-600'}`}>
                                {a.score}/10
                              </span>
                            ) : '--'}
                          </td>
                          <td className="px-4 py-3 text-gray-600">{a.verdict || '--'}</td>
                          <td className="px-4 py-3">
                            <span className="px-2 py-0.5 bg-purple-50 text-purple-600 rounded text-xs">
                              {a.analysis_type || 'general'}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}
        </>
      )}
    </div>
  )
}

function StatCard({ label, value, icon }) {
  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4">
      <div className="flex items-center gap-2 mb-1">
        <span className="text-lg">{icon}</span>
        <span className="text-xs text-gray-500 uppercase tracking-wide">{label}</span>
      </div>
      <div className="text-2xl font-bold text-gray-800">{value}</div>
    </div>
  )
}
