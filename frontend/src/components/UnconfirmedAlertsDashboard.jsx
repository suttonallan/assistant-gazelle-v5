import React, { useState, useEffect } from 'react';
import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000';

/**
 * Dashboard des Alertes RV Non Confirmés
 * 
 * Affiche :
 * - Les alertes envoyées (historique)
 * - Les RV non confirmés actuels
 * - Statistiques par technicien
 */
function UnconfirmedAlertsDashboard() {
  const [alerts, setAlerts] = useState([]);
  const [unconfirmed, setUnconfirmed] = useState(null);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('current'); // 'current' ou 'history'

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      setLoading(true);
      setError(null);

      // Récupérer les RV non confirmés actuels
      const unconfirmedRes = await axios.get(`${API_BASE}/api/alertes-rv/check`);
      setUnconfirmed(unconfirmedRes.data);

      // Récupérer l'historique des alertes
      const historyRes = await axios.get(`${API_BASE}/api/alertes-rv/history?limit=50`);
      setAlerts(historyRes.data.alerts || []);

      // Récupérer les stats
      const statsRes = await axios.get(`${API_BASE}/api/alertes-rv/stats`);
      setStats(statsRes.data);

    } catch (err) {
      setError(err.message);
      console.error('Erreur:', err);
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleDateString('fr-CA', { 
      year: 'numeric', 
      month: 'short', 
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const getStatusBadge = (status) => {
    const badges = {
      'sent': { text: '✅ Envoyé', color: 'bg-green-100 text-green-800' },
      'failed': { text: '❌ Échec', color: 'bg-red-100 text-red-800' },
      'acknowledged': { text: '✓ Lu', color: 'bg-blue-100 text-blue-800' }
    };
    const badge = badges[status] || { text: status, color: 'bg-gray-100 text-gray-800' };
    return (
      <span className={`px-2 py-1 text-xs font-medium rounded ${badge.color}`}>
        {badge.text}
      </span>
    );
  };

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto p-6">
        <div className="text-center py-12">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
          <p className="mt-4 text-gray-600">Chargement...</p>
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
            onClick={fetchData}
            className="mt-4 px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700"
          >
            Réessayer
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto p-6">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">
          📧 Alertes RV Non Confirmés
        </h1>
        <p className="text-gray-600">
          Gestion des alertes envoyées aux techniciens pour les rendez-vous non confirmés
        </p>
      </div>

      {/* Stats Cards */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
          <div className="bg-white border border-gray-200 rounded-lg p-4">
            <div className="text-sm text-gray-500 mb-1">Total Alertes</div>
            <div className="text-2xl font-bold text-gray-900">{stats.total_alerts || 0}</div>
          </div>
          <div className="bg-white border border-gray-200 rounded-lg p-4">
            <div className="text-sm text-gray-500 mb-1">RV Alertés</div>
            <div className="text-2xl font-bold text-gray-900">{stats.total_appointments || 0}</div>
          </div>
          <div className="bg-white border border-gray-200 rounded-lg p-4">
            <div className="text-sm text-gray-500 mb-1">Techniciens</div>
            <div className="text-2xl font-bold text-gray-900">{stats.unique_technicians || 0}</div>
          </div>
          <div className="bg-white border border-gray-200 rounded-lg p-4">
            <div className="text-sm text-gray-500 mb-1">Taux Succès</div>
            <div className="text-2xl font-bold text-gray-900">
              {stats.success_rate ? `${Math.round(stats.success_rate * 100)}%` : 'N/A'}
            </div>
          </div>
        </div>
      )}

      {/* Tabs */}
      <div className="mb-4 border-b border-gray-200">
        <nav className="flex space-x-8">
          <button
            onClick={() => setActiveTab('current')}
            className={`py-4 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'current'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            📋 RV Non Confirmés Actuels
            {unconfirmed && unconfirmed.total_appointments > 0 && (
              <span className="ml-2 bg-red-100 text-red-800 text-xs px-2 py-1 rounded">
                {unconfirmed.total_appointments}
              </span>
            )}
          </button>
          <button
            onClick={() => setActiveTab('history')}
            className={`py-4 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'history'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            📜 Historique des Alertes ({alerts.length})
          </button>
        </nav>
      </div>

      {/* Current Unconfirmed */}
      {activeTab === 'current' && (
        <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
          {unconfirmed && unconfirmed.technicians && unconfirmed.technicians.length > 0 ? (
            <div className="divide-y divide-gray-200">
              {unconfirmed.technicians.map((tech, idx) => (
                <div key={idx} className="p-4 hover:bg-gray-50">
                  <div className="flex justify-between items-start mb-2">
                    <div>
                      <h3 className="font-semibold text-gray-900">{tech.name}</h3>
                      <p className="text-sm text-gray-500">{tech.email}</p>
                    </div>
                    <span className="bg-red-100 text-red-800 text-sm px-3 py-1 rounded">
                      {tech.unconfirmed_count} RV non confirmé(s)
                    </span>
                  </div>
                  <div className="mt-3 space-y-2">
                    {tech.appointments && tech.appointments.map((apt, aptIdx) => (
                      <div key={aptIdx} className="bg-gray-50 p-3 rounded text-sm">
                        <div className="flex justify-between">
                          <span className="font-medium">{apt.appointment_time || 'N/A'}</span>
                          <span className="text-gray-600">{apt.client_name || apt.title || 'N/A'}</span>
                        </div>
                        {apt.title && apt.title !== apt.client_name && (
                          <p className="text-gray-500 mt-1">{apt.title}</p>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-12 text-gray-500">
              ✅ Aucun RV non confirmé pour le moment
            </div>
          )}
        </div>
      )}

      {/* History */}
      {activeTab === 'history' && (
        <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Date</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Technicien</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">RV</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Client</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Statut</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Envoyé le</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {alerts.map((alert, idx) => (
                <tr key={idx} className="hover:bg-gray-50">
                  <td className="px-4 py-3 text-sm text-gray-900">
                    {formatDate(alert.appointment_date)}
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-900">
                    {alert.technician_name || 'N/A'}
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-500">
                    {alert.appointment_time || 'N/A'}
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-500">
                    {alert.client_name || alert.title || 'N/A'}
                  </td>
                  <td className="px-4 py-3">
                    {getStatusBadge(alert.status)}
                    {alert.acknowledged && (
                      <span className="ml-2 text-xs text-gray-500">✓ Lu</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-500">
                    {formatDate(alert.sent_at)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {alerts.length === 0 && (
            <div className="text-center py-12 text-gray-500">
              Aucune alerte envoyée pour le moment
            </div>
          )}
        </div>
      )}

      {/* Actions */}
      <div className="mt-6 flex justify-end">
        <button 
          onClick={fetchData}
          className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 flex items-center gap-2"
        >
          🔄 Actualiser
        </button>
      </div>

      {/* Info Box */}
      <div className="mt-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
        <h3 className="text-sm font-semibold text-blue-900 mb-2">ℹ️ Comment ça marche ?</h3>
        <ul className="text-sm text-blue-800 space-y-1">
          <li>• <strong>Automatique</strong> : Les alertes sont envoyées chaque jour à 16:00 aux techniciens avec des RV non confirmés pour le lendemain</li>
          <li>• <strong>Destinataires</strong> : Chaque technicien reçoit un email avec ses propres RV non confirmés</li>
          <li>• <strong>Méthode</strong> : SendGrid (si configuré) ou SMTP Gmail (fallback)</li>
          <li>• <strong>Logs</strong> : Toutes les alertes sont enregistrées dans la table <code>alert_logs</code> de Supabase</li>
        </ul>
      </div>
    </div>
  );
}

export default UnconfirmedAlertsDashboard;
