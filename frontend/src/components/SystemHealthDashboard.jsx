import React, { useState, useEffect } from 'react';

/**
 * Dashboard de Santé Système
 * 
 * Affiche les logs de synchronisation (sync_logs) et d'exécution des tâches (scheduler_logs).
 * Permet de voir d'un coup d'œil si toutes les syncs nocturnes ont bien tourné.
 */
function SystemHealthDashboard() {
  const [schedulerLogs, setSchedulerLogs] = useState([]);
  const [syncLogs, setSyncLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('scheduler'); // 'scheduler' ou 'sync'

  useEffect(() => {
    fetchLogs();
  }, []);

  const fetchLogs = async () => {
    try {
      setLoading(true);
      setError(null);

      // Récupérer les logs du scheduler
      const schedulerResponse = await fetch('/api/scheduler-logs/recent?limit=30');
      if (!schedulerResponse.ok) throw new Error('Erreur récupération scheduler logs');
      const schedulerData = await schedulerResponse.json();
      setSchedulerLogs(schedulerData.logs || []);

      // Récupérer les logs de sync
      const syncResponse = await fetch('/api/sync-logs/recent?limit=30');
      if (!syncResponse.ok) throw new Error('Erreur récupération sync logs');
      const syncData = await syncResponse.json();
      setSyncLogs(syncData.logs || []);

    } catch (err) {
      setError(err.message);
      console.error('Erreur:', err);
    } finally {
      setLoading(false);
    }
  };

  const getStatusEmoji = (status) => {
    const emojis = {
      'success': '✅',
      'error': '❌',
      'warning': '⚠️',
      'running': '⏳'
    };
    return emojis[status] || '❓';
  };

  const getStatusColor = (status) => {
    const colors = {
      'success': 'text-green-600',
      'error': 'text-red-600',
      'warning': 'text-yellow-600',
      'running': 'text-blue-600'
    };
    return colors[status] || 'text-gray-600';
  };

  const formatDuration = (seconds) => {
    if (!seconds) return 'N/A';
    if (seconds < 60) return `${seconds}s`;
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes}m ${remainingSeconds}s`;
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    
    if (diffMins < 60) return `Il y a ${diffMins}min`;
    if (diffMins < 1440) return `Il y a ${Math.floor(diffMins / 60)}h`;
    return date.toLocaleDateString('fr-CA') + ' ' + date.toLocaleTimeString('fr-CA', { hour: '2-digit', minute: '2-digit' });
  };

  const renderSchedulerLogs = () => (
    <div className="overflow-x-auto">
      <table className="min-w-full bg-white border border-gray-200">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Statut</th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Tâche</th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Date</th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Durée</th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Déclencheur</th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Message</th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Stats</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-200">
          {schedulerLogs.map((log) => (
            <tr key={log.id} className="hover:bg-gray-50">
              <td className="px-4 py-3">
                <span className={`text-2xl ${getStatusColor(log.status)}`}>
                  {getStatusEmoji(log.status)}
                </span>
              </td>
              <td className="px-4 py-3 text-sm font-medium text-gray-900">
                {log.task_label || log.task_name}
              </td>
              <td className="px-4 py-3 text-sm text-gray-500">
                {formatDate(log.started_at)}
              </td>
              <td className="px-4 py-3 text-sm text-gray-500">
                {formatDuration(log.duration_seconds)}
              </td>
              <td className="px-4 py-3 text-sm text-gray-500">
                {log.triggered_by === 'scheduler' ? '⏰ Auto' : 
                 log.triggered_by === 'manual' ? '👤 Manuel' : 
                 '🔌 API'}
              </td>
              <td className="px-4 py-3 text-sm text-gray-500">
                {log.message || '-'}
              </td>
              <td className="px-4 py-3 text-sm text-gray-500">
                {log.stats && Object.keys(log.stats).length > 0 ? (
                  <details className="cursor-pointer">
                    <summary className="text-blue-600 hover:underline">Voir stats</summary>
                    <pre className="text-xs mt-2 p-2 bg-gray-50 rounded">
                      {JSON.stringify(log.stats, null, 2)}
                    </pre>
                  </details>
                ) : '-'}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      
      {schedulerLogs.length === 0 && (
        <div className="text-center py-8 text-gray-500">
          Aucun log de tâche planifiée
        </div>
      )}
    </div>
  );

  const renderSyncLogs = () => (
    <div className="overflow-x-auto">
      <table className="min-w-full bg-white border border-gray-200">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Statut</th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Script</th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Type</th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Date</th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Durée</th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Message</th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Stats</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-200">
          {syncLogs.map((log) => (
            <tr key={log.id} className="hover:bg-gray-50">
              <td className="px-4 py-3">
                <span className={`text-2xl ${getStatusColor(log.status)}`}>
                  {getStatusEmoji(log.status)}
                </span>
              </td>
              <td className="px-4 py-3 text-sm font-medium text-gray-900">
                {log.script_name}
              </td>
              <td className="px-4 py-3">
                <span className={`px-2 py-1 text-xs font-medium rounded ${
                  log.task_type === 'sync' ? 'bg-blue-100 text-blue-800' :
                  log.task_type === 'report' ? 'bg-purple-100 text-purple-800' :
                  log.task_type === 'chain' ? 'bg-green-100 text-green-800' :
                  'bg-gray-100 text-gray-800'
                }`}>
                  {log.task_type}
                </span>
              </td>
              <td className="px-4 py-3 text-sm text-gray-500">
                {formatDate(log.created_at)}
              </td>
              <td className="px-4 py-3 text-sm text-gray-500">
                {formatDuration(log.execution_time_seconds)}
              </td>
              <td className="px-4 py-3 text-sm text-gray-500">
                {log.message || log.error_details || '-'}
              </td>
              <td className="px-4 py-3 text-sm text-gray-500">
                {log.stats && Object.keys(log.stats).length > 0 ? (
                  <details className="cursor-pointer">
                    <summary className="text-blue-600 hover:underline">Voir stats</summary>
                    <pre className="text-xs mt-2 p-2 bg-gray-50 rounded">
                      {JSON.stringify(log.stats, null, 2)}
                    </pre>
                  </details>
                ) : '-'}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      
      {syncLogs.length === 0 && (
        <div className="text-center py-8 text-gray-500">
          Aucun log de synchronisation
        </div>
      )}
    </div>
  );

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto p-6">
        <div className="text-center py-12">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
          <p className="mt-4 text-gray-600">Chargement des logs...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-7xl mx-auto p-6">
        <div className="bg-red-50 border border-red-200 rounded-lg p-6">
          <h3 className="text-red-800 font-semibold mb-2">Erreur</h3>
          <p className="text-red-600">{error}</p>
          <button 
            onClick={fetchLogs}
            className="mt-4 px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700"
          >
            Réessayer
          </button>
        </div>
      </div>
    );
  }

  // Compter les succès/erreurs récents
  const recentScheduler = schedulerLogs.slice(0, 10);
  const schedulerSuccess = recentScheduler.filter(l => l.status === 'success').length;
  const schedulerError = recentScheduler.filter(l => l.status === 'error').length;

  const recentSync = syncLogs.slice(0, 10);
  const syncSuccess = recentSync.filter(l => l.status === 'success').length;
  const syncError = recentSync.filter(l => l.status === 'error').length;

  return (
    <div className="max-w-7xl mx-auto p-6">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">
          🏥 Santé du Système
        </h1>
        <p className="text-gray-600">
          Logs des synchronisations et tâches planifiées (chaînes Gazelle → Timeline)
        </p>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <div className="text-sm text-gray-500 mb-1">Tâches Planifiées</div>
          <div className="text-2xl font-bold text-gray-900">{schedulerLogs.length}</div>
          <div className="text-xs text-gray-500 mt-1">
            {schedulerSuccess} ✅ / {schedulerError} ❌ (10 derniers)
          </div>
        </div>

        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <div className="text-sm text-gray-500 mb-1">Synchronisations</div>
          <div className="text-2xl font-bold text-gray-900">{syncLogs.length}</div>
          <div className="text-xs text-gray-500 mt-1">
            {syncSuccess} ✅ / {syncError} ❌ (10 derniers)
          </div>
        </div>

        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <div className="text-sm text-gray-500 mb-1">Dernière Tâche</div>
          <div className="text-lg font-bold text-gray-900">
            {schedulerLogs.length > 0 ? getStatusEmoji(schedulerLogs[0].status) : '-'}
          </div>
          <div className="text-xs text-gray-500 mt-1">
            {schedulerLogs.length > 0 ? formatDate(schedulerLogs[0].started_at) : 'Aucune'}
          </div>
        </div>

        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <div className="text-sm text-gray-500 mb-1">Dernière Sync</div>
          <div className="text-lg font-bold text-gray-900">
            {syncLogs.length > 0 ? getStatusEmoji(syncLogs[0].status) : '-'}
          </div>
          <div className="text-xs text-gray-500 mt-1">
            {syncLogs.length > 0 ? formatDate(syncLogs[0].created_at) : 'Aucune'}
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="mb-4 border-b border-gray-200">
        <nav className="flex space-x-8">
          <button
            onClick={() => setActiveTab('scheduler')}
            className={`py-4 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'scheduler'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            ⏰ Tâches Planifiées ({schedulerLogs.length})
          </button>
          <button
            onClick={() => setActiveTab('sync')}
            className={`py-4 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'sync'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            🔄 Synchronisations ({syncLogs.length})
          </button>
        </nav>
      </div>

      {/* Actions */}
      <div className="mb-4 flex justify-end">
        <button 
          onClick={fetchLogs}
          className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 flex items-center gap-2"
        >
          🔄 Actualiser
        </button>
      </div>

      {/* Logs Table */}
      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
        {activeTab === 'scheduler' ? renderSchedulerLogs() : renderSyncLogs()}
      </div>

      {/* Footer Info */}
      <div className="mt-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
        <h3 className="text-sm font-semibold text-blue-900 mb-2">ℹ️ Comment ça marche ?</h3>
        <ul className="text-sm text-blue-800 space-y-1">
          <li>• <strong>Tâches Planifiées</strong> : Logs du scheduler (01:00 Gazelle → Timeline, 16:00 Alertes RV, etc.)</li>
          <li>• <strong>Synchronisations</strong> : Logs détaillés des syncs manuelles et automatiques</li>
          <li>• <strong>Chaînage</strong> : Quand Gazelle réussit, le Rapport Timeline se génère automatiquement</li>
          <li>• <strong>Notifications</strong> : Les erreurs sont envoyées automatiquement sur Slack</li>
        </ul>
      </div>
    </div>
  );
}

export default SystemHealthDashboard;
