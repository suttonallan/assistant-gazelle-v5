import { useState, useEffect } from 'react'
import { API_URL } from '../utils/apiConfig'

const CATEGORY_CONFIG = {
  humidity: { icon: '💧', badge: 'bg-orange-100 text-orange-800' },
  urgence_rv: { icon: '📅', badge: 'bg-red-100 text-red-800' },
  pda_oublis: { icon: '📬', badge: 'bg-purple-100 text-purple-800' },
  late_assignment: { icon: '⏰', badge: 'bg-yellow-100 text-yellow-800' },
  validation: { icon: '📋', badge: 'bg-blue-100 text-blue-800' },
}

export default function AlertesSummaryCard() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadResume()
    const interval = setInterval(loadResume, 60000)
    return () => clearInterval(interval)
  }, [])

  const loadResume = async () => {
    try {
      const resp = await fetch(`${API_URL}/api/alertes-resume`)
      if (resp.ok) {
        setData(await resp.json())
      }
    } catch (err) {
      console.warn('Alertes résumé non disponible:', err)
    } finally {
      setLoading(false)
    }
  }

  if (loading || !data) return null

  const total = data.total_alertes || 0
  if (total === 0) {
    return (
      <div className="bg-green-50 border border-green-200 rounded-lg px-4 py-3 mb-4 flex items-center gap-2">
        <span className="text-green-600 font-medium text-sm">Aucune alerte active</span>
      </div>
    )
  }

  const categories = data.categories || {}
  const active = Object.entries(categories).filter(([, v]) => v.count > 0)

  return (
    <div className="bg-white border border-red-200 rounded-lg shadow-sm mb-4 px-4 py-3">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className="relative flex h-3 w-3">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75" />
            <span className="relative inline-flex rounded-full h-3 w-3 bg-red-500" />
          </span>
          <span className="font-semibold text-gray-800 text-sm">
            {total} alerte{total > 1 ? 's' : ''} active{total > 1 ? 's' : ''}
          </span>
        </div>
        <button
          onClick={loadResume}
          className="text-xs text-gray-400 hover:text-gray-600"
        >
          Actualiser
        </button>
      </div>
      <div className="flex flex-wrap gap-2">
        {active.map(([key, val]) => {
          const cfg = CATEGORY_CONFIG[key] || { icon: '⚠️', badge: 'bg-gray-100 text-gray-800' }
          return (
            <span
              key={key}
              className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium ${cfg.badge}`}
            >
              {cfg.icon} {val.count} {val.label}
            </span>
          )
        })}
      </div>
    </div>
  )
}
