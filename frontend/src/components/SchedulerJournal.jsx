import React, { useState, useEffect } from 'react'
import { TECHNICIENS_LISTE } from '../../../config/techniciens.config'

import { API_URL } from '../utils/apiConfig'

/**
 * Journal des Tâches Planifiées
 *
 * Affiche les logs des exécutions du scheduler avec:
 * - Historique des 20 dernières exécutions
 * - Boutons pour lancer manuellement chaque tâche
 * - Statut (Succès/Erreur) avec détails
 * - Support "Nick" au lieu de "Nicolas" dans les logs
 */
const SchedulerJournal = ({ currentUser }) => {
  const [logs, setLogs] = useState([])
  const [loading, setLoading] = useState(true)
  const [runningTasks, setRunningTasks] = useState(new Set())

  // Charger les logs au montage et toutes les 30 secondes
  useEffect(() => {
    loadLogs()
    const interval = setInterval(loadLogs, 30000) // Refresh toutes les 30s
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
      label: 'Sync RV & Alertes',
      icon: '📧',
      description: 'Import RV et envoi alertes RV non confirmés',
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

  return (
    <div className="space-y-6">
      {/* Boutons d'exécution manuelle - Tâches Planifiées */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">
          ⚡ Tâches Planifiées - Exécution Manuelle
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {availableTasks.map(task => (
            <div key={task.name} className="border rounded-lg p-4 hover:border-blue-500 transition-colors">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-2xl">{task.icon}</span>
                    <h4 className="font-semibold text-gray-900">{task.label}</h4>
                  </div>
                  <p className="text-sm text-gray-600 mb-3">{task.description}</p>
                </div>
              </div>

              <button
                onClick={() => runTask(task.name, task.label)}
                disabled={runningTasks.has(task.name)}
                className={`w-full px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                  runningTasks.has(task.name)
                    ? 'bg-gray-200 text-gray-500 cursor-not-allowed'
                    : 'bg-blue-600 text-white hover:bg-blue-700'
                }`}
              >
                {runningTasks.has(task.name) ? '⏳ En cours...' : '▶️ Lancer maintenant'}
              </button>
            </div>
          ))}
        </div>
      </div>

      {/* Imports Individuels */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">
          📥 Imports Gazelle Individuels
        </h3>
        <p className="text-sm text-gray-600 mb-4">
          Lancez des imports spécifiques depuis l'API Gazelle vers Supabase
        </p>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          {availableImports.map(imp => (
            <div key={imp.name} className="border rounded-lg p-3 hover:border-green-500 transition-colors">
              <div className="flex items-center gap-2 mb-2">
                <span className="text-xl">{imp.icon}</span>
                <h4 className="font-semibold text-gray-900 text-sm">{imp.label}</h4>
              </div>
              <p className="text-xs text-gray-600 mb-3">{imp.description}</p>
              <button
                onClick={() => runImport(imp.name, imp.label)}
                disabled={runningTasks.has(`import_${imp.name}`)}
                className={`w-full px-3 py-1.5 rounded text-xs font-medium transition-colors ${
                  runningTasks.has(`import_${imp.name}`)
                    ? 'bg-gray-200 text-gray-500 cursor-not-allowed'
                    : 'bg-green-600 text-white hover:bg-green-700'
                }`}
              >
                {runningTasks.has(`import_${imp.name}`) ? '⏳ Import...' : '▶️ Lancer'}
              </button>
            </div>
          ))}
        </div>
      </div>

      {/* Journal des exécutions */}
      <div className="bg-white rounded-lg shadow">
        <div className="p-6 border-b border-gray-200">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-semibold text-gray-900">
              📜 Journal des Exécutions
            </h3>
            <button
              onClick={loadLogs}
              className="px-3 py-1 text-sm text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
            >
              🔄 Actualiser
            </button>
          </div>
          <p className="text-sm text-gray-500 mt-1">
            Historique des 20 dernières exécutions
          </p>
        </div>

        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Heure
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Tâche
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Statut
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Durée
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Message
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Déclencheur
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {logs.length === 0 ? (
                <tr>
                  <td colSpan="6" className="px-6 py-4 text-center text-sm text-gray-500">
                    Aucune exécution enregistrée
                  </td>
                </tr>
              ) : (
                logs.map(log => (
                  <tr key={log.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {formatDate(log.started_at)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm font-medium text-gray-900">
                        {log.task_label}
                      </div>
                      {formatStats(log.stats)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {getStatusBadge(log.status)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                      {formatDuration(log.duration_seconds)}
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-600">
                      <div className="max-w-xs truncate" title={log.message}>
                        {formatMessage(log.message)}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                      {log.triggered_by === 'scheduler' ? '⏰ Auto' :
                       log.triggered_by === 'manual' ? '👤 Manuel' :
                       log.triggered_by}
                      {log.triggered_by_user && (
                        <div className="text-xs text-gray-400 mt-1">
                          {log.triggered_by_user}
                        </div>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

export default SchedulerJournal
