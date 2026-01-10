import React, { useState, useEffect } from 'react'
import { TECHNICIENS_LISTE } from '../../../config/techniciens.config'

import { API_URL } from '../utils/apiConfig'

/**
 * Journal des Tâches Planifiées & Importations
 *
 * Affiche:
 * - Importations récentes depuis sync_logs (Supabase)
 * - Logs des exécutions du scheduler
 * - Boutons pour lancer manuellement chaque tâche
 * - Statut (Succès/Erreur) avec détails
 */
const SchedulerJournal = ({ currentUser }) => {
  const [logs, setLogs] = useState([])
  const [syncLogs, setSyncLogs] = useState([])
  const [loading, setLoading] = useState(true)
  const [runningTasks, setRunningTasks] = useState(new Set())

  // Charger les logs au montage et toutes les 30 secondes
  useEffect(() => {
    loadLogs()
    loadSyncLogs()
    const interval = setInterval(() => {
      loadLogs()
      loadSyncLogs()
    }, 30000) // Refresh toutes les 30s
    return () => clearInterval(interval)
  }, [])

  const loadLogs = async () => {
    try {
      const response = await fetch(`${API_URL}/api/scheduler/logs?limit=20`)
      if (!response.ok) throw new Error('Erreur chargement logs')
      const data = await response.json()
      setLogs(data)
    } catch (err) {
      console.error('Erreur chargement logs:', err)
    } finally {
      setLoading(false)
    }
  }

  const loadSyncLogs = async () => {
    try {
      const response = await fetch(`${API_URL}/api/sync-logs/recent?limit=50`)
      if (!response.ok) throw new Error('Erreur chargement sync logs')
      const data = await response.json()
      setSyncLogs(data.logs || [])
    } catch (err) {
      console.error('Erreur chargement sync logs:', err)
    }
  }

  const runTask = async (taskName, taskLabel) => {
    if (runningTasks.has(taskName)) {
      alert(`La tâche "${taskLabel}" est déjà en cours d'exécution`)
      return
    }

    try {
      setRunningTasks(prev => new Set([...prev, taskName]))

      const response = await fetch(`${API_URL}/api/scheduler/run/${taskName}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_email: currentUser?.email
        })
      })

      if (!response.ok) throw new Error('Erreur lancement tâche')

      const result = await response.json()
      alert(`✅ ${result.message}`)

      // Recharger les logs après 2 secondes
      setTimeout(loadLogs, 2000)

    } catch (err) {
      console.error('Erreur lancement tâche:', err)
      alert(`❌ Erreur: ${err.message}`)
    } finally {
      // Retirer de la liste des tâches en cours après 5 secondes
      setTimeout(() => {
        setRunningTasks(prev => {
          const newSet = new Set(prev)
          newSet.delete(taskName)
          return newSet
        })
      }, 5000)
    }
  }

  const formatDate = (isoString) => {
    if (!isoString) return '-'
    const date = new Date(isoString)
    return date.toLocaleString('fr-CA', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    })
  }

  const formatDuration = (seconds) => {
    if (!seconds) return '-'
    if (seconds < 60) return `${seconds}s`
    const minutes = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${minutes}m ${secs}s`
  }

  // Remplacer "Nicolas" par "Nick" dans les messages
  const formatMessage = (message) => {
    if (!message) return '-'
    return message.replace(/Nicolas/g, 'Nick')
  }

  // Définition des tâches disponibles
  const availableTasks = [
    {
      name: 'sync',
      label: 'Sync Gazelle Totale',
      icon: '🔄',
      description: 'Synchronise Clients, Pianos, Timeline depuis Gazelle API',
      category: 'scheduler'
    },
    {
      name: 'rapport',
      label: 'Rapport Timeline',
      icon: '📊',
      description: 'Génère le Google Sheets avec UQAM, Vincent, PDA, Alertes',
      category: 'scheduler'
    },
    {
      name: 'backup',
      label: 'Backup SQL',
      icon: '💾',
      description: 'Sauvegarde la base de données SQLite',
      category: 'scheduler'
    },
    {
      name: 'alerts',
      label: 'Sync RV + Scan Notifications',
      icon: '📧',
      description: 'Import RV et scan alertes RV non confirmés (16h00)',
      category: 'scheduler'
    }
  ]

  // Imports individuels disponibles
  const availableImports = [
    {
      name: 'clients',
      label: 'Import Clients',
      icon: '👥',
      description: 'Importe les clients depuis Gazelle API vers Supabase'
    },
    {
      name: 'contacts',
      label: 'Import Contacts',
      icon: '📇',
      description: 'Importe les contacts depuis Gazelle API vers Supabase'
    },
    {
      name: 'pianos',
      label: 'Import Pianos',
      icon: '🎹',
      description: 'Importe les pianos depuis Gazelle API vers Supabase'
    },
    {
      name: 'timeline',
      label: 'Import Timeline',
      icon: '📅',
      description: 'Importe les entrées timeline depuis Gazelle API'
    },
    {
      name: 'appointments',
      label: 'Import Rendez-vous',
      icon: '📆',
      description: 'Importe les rendez-vous depuis Gazelle API'
    }
  ]

  const runImport = async (importName, importLabel) => {
    if (runningTasks.has(`import_${importName}`)) {
      alert(`L'import "${importLabel}" est déjà en cours`)
      return
    }

    try {
      setRunningTasks(prev => new Set([...prev, `import_${importName}`]))

      const response = await fetch(`${API_URL}/api/scheduler/run/import/${importName}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_email: currentUser?.email
        })
      })

      if (!response.ok) throw new Error('Erreur lancement import')

      const result = await response.json()
      alert(`✅ ${result.message}`)

      // Recharger les logs après 2 secondes
      setTimeout(loadLogs, 2000)

    } catch (err) {
      console.error('Erreur lancement import:', err)
      alert(`❌ Erreur: ${err.message}`)
    } finally {
      // Retirer de la liste après 5 secondes
      setTimeout(() => {
        setRunningTasks(prev => {
          const newSet = new Set(prev)
          newSet.delete(`import_${importName}`)
          return newSet
        })
      }, 5000)
    }
  }

  const getStatusBadge = (status) => {
    if (status === 'success') {
      return <span className="px-2 py-1 bg-green-100 text-green-800 text-xs rounded-full font-medium">✅ Succès</span>
    } else if (status === 'error') {
      return <span className="px-2 py-1 bg-red-100 text-red-800 text-xs rounded-full font-medium">❌ Erreur</span>
    } else if (status === 'running') {
      return <span className="px-2 py-1 bg-blue-100 text-blue-800 text-xs rounded-full font-medium">⏳ En cours</span>
    }
    return <span className="px-2 py-1 bg-gray-100 text-gray-800 text-xs rounded-full">{status}</span>
  }

  const formatStats = (stats) => {
    if (!stats || Object.keys(stats).length === 0) return null
    return (
      <div className="text-xs text-gray-600 mt-1">
        {Object.entries(stats).map(([key, value]) => (
          <span key={key} className="mr-3">
            {key}: <strong>{value}</strong>
          </span>
        ))}
      </div>
    )
  }

  if (loading) {
    return (
      <div className="p-8 text-center text-gray-500">
        Chargement du journal...
      </div>
    )
  }

  // Fonction pour recharger tous les logs
  const refreshAll = () => {
    loadLogs()
    loadSyncLogs()
  }

  return (
    <div className="space-y-4">
      {/* En-tête avec actualisation globale */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold text-gray-900">Tâches & Imports</h2>
          <p className="text-sm text-gray-500 mt-1">
            Gérez vos synchronisations et consultez l'historique
          </p>
        </div>
        <button
          onClick={refreshAll}
          className="px-4 py-2 text-sm text-white bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors flex items-center gap-2"
        >
          🔄 Actualiser tout
        </button>
      </div>

      {/* Section compacte: Exécution manuelle */}
      <div className="bg-white rounded-lg shadow">
        <div className="px-4 py-3 border-b border-gray-200">
          <h3 className="text-base font-semibold text-gray-900">
            ⚡ Exécution manuelle
          </h3>
        </div>
        <div className="p-4">
          {/* Tâches principales en ligne compacte */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-2 mb-3">
            {availableTasks.map(task => (
              <button
                key={task.name}
                onClick={() => runTask(task.name, task.label)}
                disabled={runningTasks.has(task.name)}
                className={`px-3 py-2 rounded text-sm font-medium transition-colors ${
                  runningTasks.has(task.name)
                    ? 'bg-gray-200 text-gray-500 cursor-not-allowed'
                    : 'bg-blue-600 text-white hover:bg-blue-700'
                }`}
                title={task.description}
              >
                <div className="text-base">{task.icon}</div>
                <div className="text-xs mt-1">{task.label.split(' ')[0]}</div>
              </button>
            ))}
          </div>

          {/* Imports individuels en grille compacte */}
          <div className="pt-3 border-t border-gray-200">
            <p className="text-xs text-gray-600 mb-2">Imports spécifiques:</p>
            <div className="grid grid-cols-3 md:grid-cols-5 gap-2">
              {availableImports.map(imp => (
                <button
                  key={imp.name}
                  onClick={() => runImport(imp.name, imp.label)}
                  disabled={runningTasks.has(`import_${imp.name}`)}
                  className={`px-2 py-2 rounded text-xs font-medium transition-colors ${
                    runningTasks.has(`import_${imp.name}`)
                      ? 'bg-gray-200 text-gray-500 cursor-not-allowed'
                      : 'bg-green-600 text-white hover:bg-green-700'
                  }`}
                  title={imp.description}
                >
                  <div className="text-lg">{imp.icon}</div>
                  <div className="text-xs mt-1">{imp.label.replace('Import ', '')}</div>
                </button>
              ))}
            </div>
          </div>

          {/* Indicateur de tâches en cours */}
          {runningTasks.size > 0 && (
            <div className="mt-3 px-3 py-2 bg-blue-50 border border-blue-200 rounded text-xs text-blue-800 flex items-center gap-2">
              <span className="animate-pulse">⏳</span>
              <span>{runningTasks.size} tâche(s) en cours d'exécution...</span>
            </div>
          )}
        </div>
      </div>

      {/* Historique des synchronisations (GitHub Actions + Manuelles) */}
      <div className="bg-white rounded-lg shadow">
        <div className="px-4 py-3 border-b border-gray-200">
          <h3 className="text-base font-semibold text-gray-900">
            📊 Historique des synchronisations
          </h3>
          <p className="text-xs text-gray-500 mt-1">
            Sync automatiques (1h00, 16h00) et manuelles
          </p>
        </div>

        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200 text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Date</th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Source</th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Statut</th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Tables modifiées</th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Durée</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {syncLogs.length === 0 ? (
                <tr>
                  <td colSpan="5" className="px-4 py-8 text-center text-sm text-gray-500">
                    <div className="text-3xl mb-2">📭</div>
                    <div className="font-medium">Aucune synchronisation récente</div>
                    <div className="text-xs text-gray-400 mt-1">
                      Les logs apparaîtront ici après la première sync automatique (1h00 ou 16h00) ou manuelle
                    </div>
                  </td>
                </tr>
              ) : (
                syncLogs.slice(0, 15).map(log => {
                  const tablesUpdated = log.tables_updated
                    ? (typeof log.tables_updated === 'string' ? JSON.parse(log.tables_updated) : log.tables_updated)
                    : {}

                  return (
                    <tr key={log.id} className="hover:bg-gray-50">
                      <td className="px-4 py-2 whitespace-nowrap text-xs text-gray-900">
                        {new Date(log.created_at).toLocaleString('fr-CA', {
                          month: '2-digit',
                          day: '2-digit',
                          hour: '2-digit',
                          minute: '2-digit'
                        })}
                      </td>
                      <td className="px-4 py-2 whitespace-nowrap text-xs">
                        {log.script_name === 'sync_appointments_and_alerts.py' ? '📧 RV + Alertes' :
                         log.script_name === 'GitHub_Full_Sync' ? '🤖 GitHub Actions' :
                         log.script_name.replace('sync_', '').replace('.py', '')}
                      </td>
                      <td className="px-4 py-2 whitespace-nowrap">
                        {log.status === 'success' && (
                          <span className="px-2 py-0.5 bg-green-100 text-green-800 text-xs rounded-full">✅</span>
                        )}
                        {log.status === 'error' && (
                          <span className="px-2 py-0.5 bg-red-100 text-red-800 text-xs rounded-full">❌</span>
                        )}
                        {log.status === 'warning' && (
                          <span className="px-2 py-0.5 bg-yellow-100 text-yellow-800 text-xs rounded-full">⚠️</span>
                        )}
                      </td>
                      <td className="px-4 py-2 text-xs text-gray-600">
                        {Object.keys(tablesUpdated).length > 0 ? (
                          <div className="flex flex-wrap gap-1">
                            {Object.entries(tablesUpdated).map(([table, count]) => (
                              <span key={table} className="inline-flex items-center">
                                {table}: <strong className="ml-0.5">{count}</strong>
                                {Object.keys(tablesUpdated).length > 1 && <span className="mx-1">•</span>}
                              </span>
                            ))}
                          </div>
                        ) : (
                          <span className="text-gray-400">-</span>
                        )}
                      </td>
                      <td className="px-4 py-2 whitespace-nowrap text-xs text-gray-600">
                        {log.execution_time_seconds ? `${log.execution_time_seconds}s` : '-'}
                      </td>
                    </tr>
                  )
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

export default SchedulerJournal
