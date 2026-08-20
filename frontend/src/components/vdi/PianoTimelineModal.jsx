/**
 * PianoTimelineModal — historique d'entretien d'un piano.
 *
 * Extrait de VDI_ManagementView le 2026-08-19 pour que la vue TECHNICIEN puisse
 * l'ouvrir avec la même icône horloge, sans dupliquer 157 lignes de tableau.
 * Le composant est autonome : il gère son propre chargement, tri et filtres.
 *
 * Props:
 *   piano       — objet piano ({ id, local, piano, modele, serie }). null = fermé.
 *   institution — slug (défaut 'vincent-dindy')
 *   onClose     — appelé à la fermeture
 */

import React, { useState, useEffect } from 'react';

const API_URL = import.meta.env.VITE_API_URL || (import.meta.env.DEV ? '' : 'https://assistant-gazelle-v5-api.onrender.com');

const TYPE_LABELS = {
  SERVICE_ENTRY_MANUAL: 'Service',
  SERVICE_ENTRY_AUTOMATED: 'Facture/Service',
  SERVICE: 'Service (local)',
  PIANO_MEASUREMENT: 'Mesure',
  USER_COMMENT: 'Note',
  APPOINTMENT: 'RDV',
  INVOICE: 'Facture',
  INVOICE_LOG: 'Facture',
  ESTIMATE: 'Devis',
  ESTIMATE_LOG: 'Devis',
};

export function TimelineTypeBadge({ type, source }) {
  const cfg = {
    APPOINTMENT:             { bg: 'bg-blue-100',   text: 'text-blue-700',   label: 'RDV' },
    SERVICE:                 { bg: 'bg-green-100',  text: 'text-green-700',  label: source === 'local' ? 'Service (local)' : 'Service' },
    SERVICE_ENTRY_MANUAL:    { bg: 'bg-green-100',  text: 'text-green-700',  label: 'Service' },
    SERVICE_ENTRY_AUTOMATED: { bg: 'bg-green-100',  text: 'text-green-700',  label: 'Facture/Service' },
    USER_COMMENT:            { bg: 'bg-yellow-100', text: 'text-yellow-700', label: 'Note' },
    PIANO_MEASUREMENT:       { bg: 'bg-cyan-100',   text: 'text-cyan-700',   label: 'Mesure' },
    INVOICE:                 { bg: 'bg-purple-100', text: 'text-purple-700', label: 'Facture' },
    INVOICE_LOG:             { bg: 'bg-purple-100', text: 'text-purple-700', label: 'Facture' },
    ESTIMATE:                { bg: 'bg-orange-100', text: 'text-orange-700', label: 'Devis' },
    ESTIMATE_LOG:            { bg: 'bg-orange-100', text: 'text-orange-700', label: 'Devis' },
  };
  const c = cfg[type] || { bg: 'bg-gray-100', text: 'text-gray-600', label: type || '?' };
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold ${c.bg} ${c.text}`}>
      {c.label}
    </span>
  );
}

/** Icône horloge — la même dans les deux vues. */
export function ClockIcon({ className = 'w-4 h-4 inline' }) {
  return (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  );
}

export default function PianoTimelineModal({ piano, institution = 'vincent-dindy', onClose }) {
  const [entries, setEntries] = useState([]);
  const [loading, setLoading] = useState(false);
  const [sort, setSort] = useState({ key: 'date', dir: 'desc' });
  const [filter, setFilter] = useState('');
  const [typeFilter, setTypeFilter] = useState('all');

  useEffect(() => {
    if (!piano) return;
    let annule = false;
    setEntries([]);
    setFilter('');
    setTypeFilter('all');
    setLoading(true);
    (async () => {
      try {
        const r = await fetch(`${API_URL}/api/${institution}/pianos/${piano.id}/timeline?limit=200`);
        if (r.ok) {
          const data = await r.json();
          if (!annule) setEntries(data.entries || []);
        }
      } catch (e) {
        console.error('Erreur chargement timeline:', e);
      } finally {
        if (!annule) setLoading(false);
      }
    })();
    return () => { annule = true; };
  }, [piano, institution]);

  if (!piano) return null;

  const uniqueTypes = [...new Set(entries.map(e => e.type))];
  const getText = (e) => [e.summary, e.comment, e.user, e.invoice_number].filter(Boolean).join(' ').toLowerCase();

  const filtered = entries.filter(e => {
    if (typeFilter !== 'all' && e.type !== typeFilter) return false;
    if (filter && !getText(e).includes(filter.toLowerCase())) return false;
    return true;
  });

  const sorted = [...filtered].sort((a, b) => {
    let va, vb;
    switch (sort.key) {
      case 'date': va = a.date || ''; vb = b.date || ''; break;
      case 'type': va = TYPE_LABELS[a.type] || a.type || ''; vb = TYPE_LABELS[b.type] || b.type || ''; break;
      case 'user': va = a.user || ''; vb = b.user || ''; break;
      default: va = ''; vb = '';
    }
    const cmp = typeof va === 'string' ? va.localeCompare(vb) : va - vb;
    return sort.dir === 'asc' ? cmp : -cmp;
  });

  const toggleSort = (key) => {
    setSort(prev => prev.key === key
      ? { key, dir: prev.dir === 'asc' ? 'desc' : 'asc' }
      : { key, dir: key === 'date' ? 'desc' : 'asc' }
    );
  };

  const SortArrow = ({ col }) => {
    if (sort.key !== col) return <span className="text-gray-300 ml-0.5">⇅</span>;
    return <span className="text-blue-600 ml-0.5">{sort.dir === 'asc' ? '▲' : '▼'}</span>;
  };

  // Les dates de l'API sont en UTC : toLocaleDateString convertit vers l'heure
  // locale. Ne PAS trancher la chaîne — voir CLAUDE.md § Horodatages.
  const formatDate = (d) => d ? new Date(d).toLocaleDateString('fr-CA', { year: 'numeric', month: 'short', day: 'numeric' }) : '-';

  return (
    <div className="fixed inset-0 bg-black/40 z-50 flex items-start justify-center pt-8 px-4">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-5xl max-h-[85vh] flex flex-col">
        <div className="flex items-center justify-between px-5 py-3 border-b bg-gray-50 rounded-t-xl">
          <div>
            <h3 className="text-base font-bold text-gray-900">Historique — {piano.local}</h3>
            <p className="text-xs text-gray-500">
              {piano.piano}{piano.modele ? ` ${piano.modele}` : ''} — {piano.serie}
              <span className="ml-2 text-gray-400">({filtered.length} entrée{filtered.length > 1 ? 's' : ''})</span>
            </p>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-700 text-xl leading-none px-2">
            &times;
          </button>
        </div>

        <div className="flex items-center gap-3 px-5 py-2 border-b bg-white">
          <input
            type="text"
            placeholder="Rechercher..."
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            className="border border-gray-300 rounded px-2.5 py-1.5 text-xs w-56 focus:outline-none focus:ring-1 focus:ring-blue-400"
          />
          <select
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
            className="border border-gray-300 rounded px-2 py-1.5 text-xs bg-white focus:outline-none focus:ring-1 focus:ring-blue-400"
          >
            <option value="all">Tous les types</option>
            {uniqueTypes.map(t => (
              <option key={t} value={t}>{TYPE_LABELS[t] || t}</option>
            ))}
          </select>
        </div>

        <div className="flex-1 overflow-auto">
          {loading ? (
            <div className="text-center py-8 text-gray-500">Chargement...</div>
          ) : sorted.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              {entries.length === 0 ? 'Aucun historique.' : 'Aucun résultat pour ce filtre.'}
            </div>
          ) : (
            <table className="w-full text-xs">
              <thead className="sticky top-0 bg-gray-50 z-10">
                <tr className="border-b text-left text-[10px] font-semibold text-gray-500 uppercase">
                  <th className="px-3 py-2 w-28 cursor-pointer select-none" onClick={() => toggleSort('date')}>
                    Date <SortArrow col="date" />
                  </th>
                  <th className="px-3 py-2 w-28 cursor-pointer select-none" onClick={() => toggleSort('type')}>
                    Type <SortArrow col="type" />
                  </th>
                  <th className="px-3 py-2 w-32 cursor-pointer select-none" onClick={() => toggleSort('user')}>
                    Technicien <SortArrow col="user" />
                  </th>
                  <th className="px-3 py-2">Description</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {sorted.map((entry, idx) => (
                  <tr key={entry.id || idx} className={`hover:bg-blue-50/50 ${entry.source === 'local' ? 'bg-green-50/30' : ''}`}>
                    <td className="px-3 py-2 text-gray-600 whitespace-nowrap align-top">{formatDate(entry.date)}</td>
                    <td className="px-3 py-2 align-top">
                      <TimelineTypeBadge type={entry.type} source={entry.source} />
                    </td>
                    <td className="px-3 py-2 text-gray-700 align-top">{entry.user || '-'}</td>
                    <td className="px-3 py-2 text-gray-800 align-top">
                      {entry.summary && entry.comment ? (
                        <>
                          <span className="font-medium">{entry.summary}</span>
                          <p className="whitespace-pre-wrap mt-0.5 text-gray-600">{entry.comment}</p>
                        </>
                      ) : (
                        <span className="whitespace-pre-wrap">{entry.comment || entry.summary || '-'}</span>
                      )}
                      {entry.invoice_number && (
                        <span className="ml-2 text-purple-500">#{entry.invoice_number}</span>
                      )}
                      {entry.source === 'local' && entry.status && (
                        <span className={`ml-2 text-[10px] px-1.5 py-0.5 rounded-full font-medium ${
                          entry.status === 'pushed' ? 'bg-gray-200 text-gray-600' : 'bg-green-100 text-green-700'
                        }`}>
                          {entry.status === 'pushed' ? 'Poussé' : entry.status === 'imported' ? 'Sheet' : 'Validé'}
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}
