import { useState, useEffect } from 'react'
import { API_URL } from '../utils/apiConfig'

/**
 * SyncDashboard — Tableau de bord compact
 *
 * Sections:
 * 1. Statut système (une ligne)
 * 2. Timeline syncs (compact)
 * 3. Alertes dernière minute
 * 4. RV non confirmés (J-1)
 * 5. Surveillance PDA (watchlist)
 */
export default function SyncDashboard({ currentUser }) {
  const [syncLogs, setSyncLogs] = useState([])
  const [syncStats, setSyncStats] = useState(null)
  const [lateAlerts, setLateAlerts] = useState([])
  const [unconfirmedRV, setUnconfirmedRV] = useState([])
  const [j1AlertsHistory, setJ1AlertsHistory] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    loadAllData()
    const interval = setInterval(loadAllData, 60000)
    return () => clearInterval(interval)
  }, [])

  const loadAllData = async () => {
    setLoading(true)
    await Promise.all([
      loadSyncLogs(),
      loadSyncStats(),
      loadLateAlerts(),
      loadUnconfirmedRV(),
      loadJ1AlertsHistory(),
    ])
    setLoading(false)
  }

  const loadSyncLogs = async () => {
    try {
      const r = await fetch(`${API_URL}/api/sync-logs/recent?limit=10`)
      if (r.ok) { const d = await r.json(); setSyncLogs(d.logs || []) }
    } catch (e) { console.error('sync logs:', e) }
  }

  const loadSyncStats = async () => {
    try {
      const r = await fetch(`${API_URL}/api/sync-logs/stats`)
      if (r.ok) setSyncStats(await r.json())
    } catch (e) { console.error('sync stats:', e) }
  }

  const loadLateAlerts = async () => {
    try {
      const r = await fetch(`${API_URL}/api/alertes-rv/late-assignment?limit=20`)
      if (r.ok) { const d = await r.json(); setLateAlerts(d.alerts || []) }
    } catch (e) { console.error('late alerts:', e) }
  }

  const loadUnconfirmedRV = async () => {
    try {
      const r = await fetch(`${API_URL}/api/alertes-rv/check`)
      if (r.ok) {
        const d = await r.json()
        setUnconfirmedRV(d.unconfirmed || d.appointments || [])
      }
    } catch (e) { console.error('unconfirmed:', e) }
  }

  // Historique des alertes J-1 envoyees aux techniciens (16h quotidien).
  // Dedoublonne les anciens doublons causes par l'ex-scheduler duplique
  // (fix deploye 2026-04-21, commit 3f98d6b) en gardant le premier par
  // (appointment_id, technician_id, date-jour).
  const loadJ1AlertsHistory = async () => {
    try {
      const r = await fetch(`${API_URL}/api/alertes-rv/history?limit=30`)
      if (r.ok) {
        const d = await r.json()
        const raw = d.alerts || []
        const seen = new Set()
        const deduped = []
        for (const a of raw) {
          const key = `${a.appointment_id || a.id}_${a.technician_id || ''}_${(a.sent_at || '').slice(0, 10)}`
          if (seen.has(key)) continue
          seen.add(key)
          deduped.push(a)
        }
        setJ1AlertsHistory(deduped)
      }
    } catch (e) { console.error('j1 alerts history:', e) }
  }

  const rel = (iso) => {
    if (!iso) return '--'
    const m = Math.floor((Date.now() - new Date(iso).getTime()) / 60000)
    if (m < 1) return 'maintenant'
    if (m < 60) return `${m}min`
    const h = Math.floor(m / 60)
    if (h < 24) return `${h}h`
    const d = Math.floor(h / 24)
    return `${d}j`
  }

  const time = (iso) => {
    if (!iso) return '--:--'
    try { return new Date(iso).toLocaleTimeString('fr-CA', { hour: '2-digit', minute: '2-digit' }) }
    catch { return '--:--' }
  }

  const date = (iso) => {
    if (!iso) return ''
    try { return new Date(iso).toLocaleDateString('fr-CA', { day: '2-digit', month: 'short' }) }
    catch { return iso?.slice(0, 10) || '' }
  }

  // Statut système
  const lastLog = syncLogs[0]
  const hoursSince = lastLog ? (Date.now() - new Date(lastLog.created_at).getTime()) / 3600000 : 99
  const sysOk = lastLog?.status === 'success' && hoursSince < 3

  const pendingAlerts = lateAlerts.filter(a => a.status === 'pending')
  const sentAlerts = lateAlerts.filter(a => a.status === 'sent')

  const techNames = {
    'usr_HcCiFk7o0vZ9xAI0': 'Nicolas',
    'usr_ofYggsCDt2JAVeNP': 'Allan',
    'usr_ReUSmIJmBF86ilY1': 'JP',
    'usr_bbt59aCUqUaDWA8n': 'Margot',
    'usr_HihJsEgkmpTEziJo': 'À attribuer',
  }
  const techName = (id) => techNames[id] || id?.slice(0, 8) || ''

  const extractStats = (log) => {
    const s = log.stats || log.tables_updated || {}
    if (typeof s === 'string') { try { return JSON.parse(s) } catch { return {} } }
    return s
  }

  return (
    <div className="max-w-4xl mx-auto px-3 py-4 space-y-3">

      {/* ── Statut système (une ligne) ── */}
      <div className={`flex items-center justify-between px-3 py-2 rounded-lg text-xs ${
        sysOk ? 'bg-green-50 border border-green-200' : 'bg-yellow-50 border border-yellow-200'
      }`}>
        <div className="flex items-center gap-2">
          <div className={`w-2 h-2 rounded-full ${sysOk ? 'bg-green-500' : 'bg-yellow-500'}`} />
          <span className="font-medium text-gray-700">
            Dernière sync: {rel(lastLog?.created_at)}
            {lastLog && ` (${lastLog.script_name || 'Gazelle'})`}
          </span>
        </div>
        <button
          onClick={loadAllData}
          disabled={loading}
          className="text-gray-500 hover:text-gray-700 text-xs"
        >
          {loading ? '...' : 'Actualiser'}
        </button>
      </div>

      {error && <div className="text-xs text-red-600 px-3">{error}</div>}

      {/* ── RV non confirmés (J-1) ── */}
      {unconfirmedRV.length > 0 && (
        <Section title={`RV non confirmés demain (${unconfirmedRV.length})`} color="orange">
          {unconfirmedRV.slice(0, 8).map((rv, i) => (
            <Row key={i}>
              <span className="font-medium">{rv.appointment_time?.slice(0, 5) || '--:--'}</span>
              <span className="flex-1 truncate">{rv.client_name || 'Client'}</span>
              <span className="text-gray-400">{rv.technician_name || techName(rv.technician_id)}</span>
            </Row>
          ))}
          {unconfirmedRV.length > 8 && (
            <div className="text-xs text-gray-400 px-2 pt-1">+{unconfirmedRV.length - 8} autres</div>
          )}
        </Section>
      )}

      {/* ── Alertes J-1 envoyees aux techniciens (16h quotidien) ── */}
      <Section
        title="Alertes J-1 envoyees (16h)"
        color={j1AlertsHistory.some(a => a.status === 'failed') ? 'orange' : 'gray'}
        badge={j1AlertsHistory.length > 0 ? `${j1AlertsHistory.length}` : null}
      >
        {j1AlertsHistory.length === 0 ? (
          <div className="text-xs text-gray-400 py-2 px-2">Aucune alerte envoyee</div>
        ) : (
          j1AlertsHistory.slice(0, 12).map((a, i) => (
            <Row
              key={a.id || i}
              className={a.status === 'failed' ? 'bg-red-50' : ''}
              title={a.subject || a.alert_type || ''}
            >
              <span className="w-4 text-center">
                {a.status === 'sent' ? '✓' : a.status === 'failed' ? '✗' : '·'}
              </span>
              <span className="font-mono w-12 text-gray-500">{time(a.sent_at)}</span>
              <span className="w-12 text-gray-400">{date(a.sent_at)}</span>
              <span className="flex-1 truncate">
                {a.client_name || '—'}
                {a.appointment_date && (
                  <span className="text-gray-400 ml-1">({a.appointment_date.slice(5)})</span>
                )}
              </span>
              <span className="text-gray-400 truncate w-16 text-right">
                {a.technician_name || techName(a.technician_id)}
              </span>
            </Row>
          ))
        )}
      </Section>

      {/* ── Alertes dernière minute ── */}
      <Section title={`Alertes RV dernière minute`} color="gray"
        badge={pendingAlerts.length > 0 ? `${pendingAlerts.length} en attente` : null}
      >
        {lateAlerts.length === 0 ? (
          <div className="text-xs text-gray-400 py-2 px-2">Aucune alerte</div>
        ) : (
          lateAlerts.slice(0, 10).map((a, i) => (
            <Row key={a.id || i} className={a.status === 'pending' ? 'bg-yellow-50' : a.status === 'failed' ? 'bg-red-50' : ''}>
              <span className="w-4 text-center">
                {a.status === 'sent' ? '✓' : a.status === 'pending' ? '⏳' : '✗'}
              </span>
              <span className="font-medium w-20">{a.appointment_date?.slice(5) || ''} {a.appointment_time?.slice(0, 5) || ''}</span>
              <span className="flex-1 truncate">{a.client_name || a.location || '--'}</span>
              <span className="text-gray-400 truncate">{a.technician_first_name || techName(a.technician_id)}</span>
              <span className="text-gray-400 w-12 text-right">
                {a.status === 'sent' ? rel(a.sent_at) : a.status === 'pending' ? time(a.scheduled_send_at) : 'err'}
              </span>
            </Row>
          ))
        )}
      </Section>

      {/* ── Timeline syncs ── */}
      <Section title="Synchronisations" color="gray">
        {syncLogs.length === 0 ? (
          <div className="text-xs text-gray-400 py-2 px-2">Aucune sync</div>
        ) : (
          syncLogs.slice(0, 8).map((log, i) => {
            const s = extractStats(log)
            // Statut "success" (vert), "warning" (jaune — non critique), "error" (rouge — critique)
            const isSuccess = log.status === 'success'
            const isWarning = log.status === 'warning'
            const isError = log.status === 'error'
            const dotColor = isSuccess ? 'bg-green-400' : isWarning ? 'bg-yellow-400' : 'bg-red-400'
            const rowBg = isError ? 'bg-red-50' : isWarning ? 'bg-yellow-50' : ''
            // Libellé de nature — visible en hover + texte court inline
            const natureLabel = isWarning
              ? 'non critique'
              : isError
              ? 'critique'
              : null
            const errMsg = log.error_message || ''
            // Tooltip complet avec le message d'erreur si disponible
            const tooltip = isSuccess
              ? ''
              : `${natureLabel?.toUpperCase() || 'ERREUR'} — ${errMsg || 'voir les logs GitHub Actions'}`
            return (
              <Row key={log.id || i} className={rowBg} title={tooltip || undefined}>
                <span className={`w-2 h-2 rounded-full flex-shrink-0 ${dotColor}`} />
                <span className="font-mono w-12">{time(log.created_at)}</span>
                <span className="w-16 text-gray-500">{date(log.created_at)}</span>
                <span className="flex-1 truncate">
                  {log.script_name || 'Sync'}
                  {natureLabel && (
                    <span
                      className={`ml-1.5 text-xs ${
                        isWarning ? 'text-yellow-700' : 'text-red-700'
                      }`}
                    >
                      ({natureLabel})
                    </span>
                  )}
                </span>
                <span className="text-gray-400 w-10 text-right">
                  {log.execution_time_seconds ? `${log.execution_time_seconds}s` : ''}
                </span>
                {s.appointments !== undefined && (
                  <span className="bg-blue-50 text-blue-600 text-xs px-1.5 rounded">{s.appointments} RV</span>
                )}
              </Row>
            )
          })
        )}
      </Section>

      {/* ── Footer ── */}
      <div className="text-center text-xs text-gray-300 pt-1">
        Sync horaire 7h-21h
      </div>
    </div>
  )
}


function Section({ title, color = 'gray', badge, children }) {
  return (
    <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
      <div className={`px-3 py-1.5 border-b border-gray-100 flex items-center justify-between ${
        color === 'orange' ? 'bg-orange-50' : 'bg-gray-50'
      }`}>
        <span className="text-xs font-semibold text-gray-600 uppercase tracking-wide">{title}</span>
        {badge && (
          <span className="text-xs bg-yellow-100 text-yellow-700 px-1.5 py-0.5 rounded">{badge}</span>
        )}
      </div>
      <div className="divide-y divide-gray-50 text-xs">
        {children}
      </div>
    </div>
  )
}


function Row({ children, className = '' }) {
  return (
    <div className={`px-3 py-1.5 flex items-center gap-2 hover:bg-gray-50 ${className}`}>
      {children}
    </div>
  )
}
