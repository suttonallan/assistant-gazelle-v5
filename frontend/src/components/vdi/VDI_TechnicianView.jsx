/**
 * VDI_TechnicianView v2 — Vue accordéon mobile pour les techniciens
 *
 * Auto-save avec debounce 500ms + indicateur lumineux.
 * Le technicien tape ses notes, ça s'enregistre tout seul.
 * Il clique sur un autre piano pour passer au suivant.
 * Pas de push Gazelle — Nick review et décide dans sa vue gestionnaire.
 *
 * Changements v2: retrait checkbox Gazelle, retrait bouton Sauvegarder
 */

import React, { useState, useRef, useCallback } from 'react';

// Save status badge (same pattern as VDI_NotesView)
function SaveBadge({ status }) {
  if (!status || status === 'idle') return null;

  const config = {
    modified: { bg: 'bg-amber-100', text: 'text-amber-700', border: 'border-amber-300', label: 'Modifié', icon: '●' },
    saving:   { bg: 'bg-blue-100',  text: 'text-blue-700',  border: 'border-blue-300',  label: 'En cours...', icon: '↻' },
    saved:    { bg: 'bg-green-100', text: 'text-green-700', border: 'border-green-300', label: 'Sauvegardé', icon: '✓' },
    error:    { bg: 'bg-red-100',   text: 'text-red-700',   border: 'border-red-300',   label: 'Erreur', icon: '✕' },
  };
  const c = config[status];

  return (
    <div className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold border ${c.bg} ${c.text} ${c.border} ${status === 'saving' ? 'animate-pulse' : ''}`}>
      <span>{c.icon}</span>
      <span>{c.label}</span>
    </div>
  );
}

export default function VDI_TechnicianView({
  pianos,
  stats,
  showOnlyProposed,
  setShowOnlyProposed,
  searchLocal,
  setSearchLocal,
  expandedPianoId,
  setExpandedPianoId,
  travailInput,
  setTravailInput,

  // Actions — saveTravail is used for auto-save now
  saveTravail,

  // Utilitaires
  moisDepuisAccord,
  formatDateRelative,
  pianosFiltres,

  // Tournées (sélection institution)
  selectedInstitution,
  setSelectedInstitution,
  onInstitutionChange
}) {
  // Auto-save state
  const [saveStatus, setSaveStatus] = useState({});
  const debounceTimers = useRef({});

  const toggleExpand = (piano) => {
    if (expandedPianoId === piano.id) {
      setExpandedPianoId(null);
      setTravailInput('');
    } else {
      setExpandedPianoId(piano.id);
      setTravailInput(piano.travail || '');
    }
  };

  // Auto-save handler with debounce
  const handleTravailChange = useCallback((pianoId, value) => {
    setTravailInput(value);

    clearTimeout(debounceTimers.current[pianoId]);
    setSaveStatus(prev => ({ ...prev, [pianoId]: 'modified' }));

    debounceTimers.current[pianoId] = setTimeout(async () => {
      if (!value.trim()) return;
      setSaveStatus(prev => ({ ...prev, [pianoId]: 'saving' }));
      try {
        await saveTravail(pianoId, value);
        setSaveStatus(prev => ({ ...prev, [pianoId]: 'saved' }));
      } catch {
        setSaveStatus(prev => ({ ...prev, [pianoId]: 'error' }));
      }
    }, 500);
  }, [saveTravail, setTravailInput]);

  const institutions = [
    { slug: 'vincent-dindy', name: "Vincent-d'Indy" },
    { slug: 'orford', name: 'Orford Musique' },
    { slug: 'place-des-arts', name: 'Place des Arts' }
  ];

  const handleInstitutionChange = (institutionSlug) => {
    if (setSelectedInstitution) setSelectedInstitution(institutionSlug);
    if (onInstitutionChange) onInstitutionChange(institutionSlug);
  };

  const currentInstitution = selectedInstitution || 'vincent-dindy';

  return (
    <div className="bg-gray-50">
      {/* Sélection institution */}
      <div className="bg-gradient-to-r from-blue-50 to-white p-4 mb-3 border border-blue-200 rounded-lg">
        <div className="text-sm font-semibold text-gray-700 mb-2 flex items-center gap-2">
          <span>🏛️</span>
          <span>Institution</span>
        </div>
        <div className="flex gap-2">
          {institutions.map(inst => {
            const isActive = currentInstitution === inst.slug;
            return (
              <button
                key={inst.slug}
                onClick={() => handleInstitutionChange(inst.slug)}
                className={`flex-1 py-2 px-3 text-sm rounded-lg font-medium transition-all ${
                  isActive
                    ? 'bg-blue-600 text-white shadow'
                    : 'bg-white text-gray-700 hover:bg-blue-50 border border-gray-300'
                }`}
              >
                {inst.name}
              </button>
            );
          })}
        </div>
      </div>

      {/* Filtres */}
      <div className="bg-white p-3 mb-4 border-b border-gray-200">
        <div className="flex gap-2 mb-2">
          <button
            onClick={() => setShowOnlyProposed(false)}
            className={`flex-1 py-1 px-2 text-xs rounded ${!showOnlyProposed ? 'bg-blue-500 text-white' : 'bg-gray-100'}`}
          >
            Tous ({stats.total})
          </button>
          <button
            onClick={() => setShowOnlyProposed(true)}
            className={`flex-1 py-1 px-2 text-xs rounded ${showOnlyProposed ? 'bg-blue-500 text-white' : 'bg-gray-100'}`}
          >
            À faire ({stats.proposed})
          </button>
        </div>

        <input
          type="text"
          placeholder="Rechercher par local (ex: 301)"
          value={searchLocal}
          onChange={(e) => setSearchLocal(e.target.value)}
          className="w-full px-3 py-2 border rounded text-sm"
        />
      </div>

      {/* Liste accordéon */}
      <div className="p-2 space-y-2">
        {pianosFiltres.length === 0 ? (
          <div className="bg-white rounded-lg p-6 text-center text-gray-500">
            {showOnlyProposed ? 'Aucun piano à faire.' : 'Aucun piano trouvé.'}
          </div>
        ) : (
          pianosFiltres.map(piano => {
            const isExpanded = expandedPianoId === piano.id;
            const mois = moisDepuisAccord(piano.dernierAccord);
            const hasTravail = piano.travail && piano.travail.trim() !== '';

            return (
              <div key={piano.id} className={`rounded-lg shadow overflow-hidden ${
                piano.status === 'top' ? 'bg-amber-100' :
                piano.status === 'proposed' ? 'bg-yellow-100' :
                'bg-white'
              }`}>
                {/* Ligne principale - cliquable */}
                <div
                  onClick={() => toggleExpand(piano)}
                  className="p-3 flex justify-between items-center cursor-pointer active:bg-gray-100"
                >
                  <div className="flex items-center gap-3">
                    <span className="text-lg font-bold text-gray-700">{piano.local}</span>
                    <span className="text-gray-600">{piano.piano}{piano.modele ? ` ${piano.modele}` : ''}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    {piano.service_status ? (
                      <span className="text-green-500 text-sm font-bold" title={
                        piano.service_status === 'pushed' ? 'Poussé vers Gazelle' : 'Validé par Nicolas'
                      }>{piano.service_status === 'pushed' ? '✓✓' : '✓'}</span>
                    ) : hasTravail ? (
                      <span className="text-blue-500 text-xs">📝</span>
                    ) : piano.last_validated_at ? (
                      <span className="text-green-500 text-sm font-bold" title="Validé">✓</span>
                    ) : null}
                    {/* Save status dot when collapsed */}
                    {!isExpanded && saveStatus[piano.id] === 'modified' && (
                      <span className="w-2 h-2 rounded-full bg-amber-400" title="Non sauvegardé" />
                    )}
                    <span className={`text-sm ${mois >= 6 ? 'text-orange-500' : 'text-gray-400'}`}>
                      {formatDateRelative(piano.dernierAccord)}
                    </span>
                    <span className="text-gray-400">{isExpanded ? '▲' : '▼'}</span>
                  </div>
                </div>

                {/* Détails - développé */}
                {isExpanded && (
                  <div className="border-t bg-gray-50 p-3 space-y-3">
                    {/* Infos */}
                    <div className="grid grid-cols-2 gap-2 text-sm">
                      <div><span className="text-gray-500">Série:</span> {piano.serie}</div>
                      <div><span className="text-gray-500">Type:</span> {piano.type === 'D' ? 'Droit' : 'Queue'}</div>
                      <div><span className="text-gray-500">Dernier:</span> {formatDateRelative(piano.dernierAccord)}</div>
                      <div><span className="text-gray-500">Usage:</span> {piano.usage || '-'}</div>
                    </div>

                    {/* Note "à faire" de Nick */}
                    {piano.aFaire && (
                      <div className="bg-yellow-100 p-2 rounded text-sm">
                        <span className="font-medium">À faire:</span> {piano.aFaire}
                      </div>
                    )}

                    {/* Bannière lecture seule si validé/poussé */}
                    {piano.service_status && (
                      <div className={`text-xs font-medium rounded px-2 py-1.5 ${
                        piano.service_status === 'pushed'
                          ? 'bg-gray-100 text-gray-600'
                          : 'bg-green-100 text-green-700'
                      }`}>
                        {piano.service_status === 'pushed'
                          ? 'Poussé vers Gazelle — lecture seule'
                          : 'Validé par Nicolas — lecture seule'}
                      </div>
                    )}

                    {/* Textarea auto-save */}
                    <div>
                      <textarea
                        value={travailInput}
                        onChange={(e) => handleTravailChange(piano.id, e.target.value)}
                        className={`w-full border rounded-lg p-3 text-sm h-24 resize-y focus:outline-none ${
                          piano.service_status
                            ? 'bg-gray-100 border-gray-200 cursor-not-allowed text-gray-500'
                            : 'border-gray-300 focus:ring-2 focus:ring-blue-300 focus:border-blue-400'
                        }`}
                        placeholder="Notes d'accord, observations..."
                        autoFocus={!piano.service_status}
                        disabled={!!piano.service_status}
                        readOnly={!!piano.service_status}
                      />
                      {!piano.service_status && (
                        <div className="flex justify-between items-center mt-1">
                          <div className="text-xs text-gray-400">auto-save</div>
                          <SaveBadge status={saveStatus[piano.id]} />
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
