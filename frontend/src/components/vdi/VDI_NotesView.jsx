/**
 * VDI_NotesView — Mode VDI : Saisie rapide + Admin buffer
 *
 * - Tout technicien (Nick, JP) : voit la liste des pianos, saisit ses notes avec auto-save
 * - Admin (Nicolas) : voit en plus le buffer des notes + bouton Bundle Push + toggle priorité
 */

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { getUserRole } from '../../config/roles';

const API_URL = import.meta.env.VITE_API_URL || (import.meta.env.DEV ? '' : 'https://assistant-gazelle-v5-api.onrender.com');

export default function VDI_NotesView({ currentUser }) {
  // Auth & token
  const [techToken, setTechToken] = useState(null);
  const [techName, setTechName] = useState('');

  // Pianos & notes
  const [pianos, setPianos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [expandedId, setExpandedId] = useState(null);
  const [saveStatus, setSaveStatus] = useState({}); // {pianoId: 'saving'|'saved'|'error'}

  // Admin buffer
  const [bufferNotes, setBufferNotes] = useState([]);
  const [selectedNoteIds, setSelectedNoteIds] = useState(new Set());
  const [bundlePushing, setBundlePushing] = useState(false);
  const [showAdmin, setShowAdmin] = useState(false);

  // Debounce timers
  const debounceTimers = useRef({});
  // Local note values (for controlled textareas)
  const localNotes = useRef({});

  const userRole = getUserRole(currentUser?.email);
  const isAdmin = userRole === 'admin' || userRole === 'nick';

  // ========== 1. Auto-provision token on mount ==========
  useEffect(() => {
    const ensureToken = async () => {
      const name = currentUser?.name || currentUser?.email?.split('@')[0] || 'Inconnu';
      try {
        const r = await fetch(`${API_URL}/api/vdi/internal/ensure-token`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ tech_name: name }),
        });
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        const data = await r.json();
        setTechToken(data.tech_token);
        setTechName(data.tech_name);
      } catch (e) {
        console.error('Erreur ensure-token:', e);
        setLoading(false);
      }
    };
    ensureToken();
  }, [currentUser]);

  // ========== 2. Load pianos when token is ready ==========
  const loadPianos = useCallback(async () => {
    if (!techToken) return;
    setLoading(true);
    try {
      const r = await fetch(`${API_URL}/api/vdi/guest/${techToken}/pianos`);
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const data = await r.json();
      setPianos(data.pianos || []);
      // Initialize local notes from buffer data
      (data.pianos || []).forEach(p => {
        if (p.buffer_note?.note) {
          localNotes.current[p.id] = p.buffer_note.note;
        }
      });
    } catch (e) {
      console.error('Erreur chargement pianos:', e);
    } finally {
      setLoading(false);
    }
  }, [techToken]);

  useEffect(() => { loadPianos(); }, [loadPianos]);

  // ========== 3. Load admin buffer ==========
  const loadBuffer = useCallback(async () => {
    if (!isAdmin) return;
    try {
      const r = await fetch(`${API_URL}/api/vdi/admin/buffer`);
      if (!r.ok) return;
      setBufferNotes(await r.json());
    } catch (e) {
      console.error('Erreur buffer:', e);
    }
  }, [isAdmin]);

  useEffect(() => { if (isAdmin) loadBuffer(); }, [loadBuffer, isAdmin]);

  // ========== 4. Auto-save with debounce ==========
  const handleNoteChange = (pianoId, value) => {
    localNotes.current[pianoId] = value;
    // Force re-render for the textarea
    setPianos(prev => [...prev]);

    clearTimeout(debounceTimers.current[pianoId]);
    setSaveStatus(prev => ({ ...prev, [pianoId]: 'typing' }));

    debounceTimers.current[pianoId] = setTimeout(async () => {
      if (!value.trim()) return;
      setSaveStatus(prev => ({ ...prev, [pianoId]: 'saving' }));
      try {
        const r = await fetch(`${API_URL}/api/vdi/guest/${techToken}/pianos/${pianoId}/note`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ note: value }),
        });
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        setSaveStatus(prev => ({ ...prev, [pianoId]: 'saved' }));
        // Refresh admin buffer silently
        if (isAdmin) loadBuffer();
      } catch {
        setSaveStatus(prev => ({ ...prev, [pianoId]: 'error' }));
      }
    }, 500);
  };

  // ========== 5. Admin actions ==========
  const togglePriority = async (pianoId, currentlyPriority) => {
    try {
      await fetch(`${API_URL}/api/vdi/admin/priority/${pianoId}`, {
        method: currentlyPriority ? 'DELETE' : 'POST',
      });
      await loadPianos();
    } catch (e) {
      console.error('Erreur toggle priorité:', e);
    }
  };

  const validateSelected = async () => {
    if (selectedNoteIds.size === 0) return;
    try {
      await fetch(`${API_URL}/api/vdi/admin/buffer/validate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ note_ids: Array.from(selectedNoteIds) }),
      });
      setSelectedNoteIds(new Set());
      await loadBuffer();
    } catch (e) {
      alert('Erreur validation: ' + e.message);
    }
  };

  const bundlePush = async () => {
    const validatedNotes = bufferNotes.filter(n => n.status === 'validated');
    if (validatedNotes.length === 0) {
      alert('Aucune note validée à envoyer.');
      return;
    }
    if (!confirm(`Envoyer ${validatedNotes.length} note(s) vers Gazelle en un seul rendez-vous?`)) return;

    setBundlePushing(true);
    try {
      const r = await fetch(`${API_URL}/api/vdi/admin/bundle-push`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
      });
      const data = await r.json();
      if (data.success) {
        alert(`Envoyé! ${data.notes_count} note(s) pour ${data.pianos_count} piano(s). Event: ${data.event_id}`);
        await loadBuffer();
      } else {
        alert('Erreur: ' + JSON.stringify(data));
      }
    } catch (e) {
      alert('Erreur Bundle Push: ' + e.message);
    } finally {
      setBundlePushing(false);
    }
  };

  const toggleNoteSelection = (noteId) => {
    setSelectedNoteIds(prev => {
      const next = new Set(prev);
      next.has(noteId) ? next.delete(noteId) : next.add(noteId);
      return next;
    });
  };

  // ========== 6. Render helpers ==========
  const SaveIndicator = ({ pianoId }) => {
    const s = saveStatus[pianoId];
    if (!s) return null;
    const styles = {
      typing: 'text-gray-400',
      saving: 'text-blue-500',
      saved: 'text-green-600',
      error: 'text-red-500',
    };
    const labels = { typing: '...', saving: 'Sauvegarde...', saved: 'Sauvegardé', error: 'Erreur!' };
    return <span className={`text-xs ${styles[s]}`}>{labels[s]}</span>;
  };

  // ========== RENDER ==========
  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-gray-500">Chargement Mode VDI...</div>
      </div>
    );
  }

  const draftCount = bufferNotes.filter(n => n.status === 'draft').length;
  const validatedCount = bufferNotes.filter(n => n.status === 'validated').length;

  return (
    <div className="space-y-4">
      {/* ===== ADMIN PANEL ===== */}
      {isAdmin && (
        <div className="bg-white rounded-lg shadow border border-gray-200">
          <button
            onClick={() => setShowAdmin(!showAdmin)}
            className="w-full px-4 py-3 flex justify-between items-center text-left hover:bg-gray-50"
          >
            <div className="flex items-center gap-2">
              <span className="text-lg">📋</span>
              <span className="font-semibold text-gray-800">Admin Buffer</span>
              {draftCount > 0 && (
                <span className="bg-blue-100 text-blue-700 text-xs font-bold px-2 py-0.5 rounded-full">
                  {draftCount} brouillon{draftCount > 1 ? 's' : ''}
                </span>
              )}
              {validatedCount > 0 && (
                <span className="bg-green-100 text-green-700 text-xs font-bold px-2 py-0.5 rounded-full">
                  {validatedCount} validée{validatedCount > 1 ? 's' : ''}
                </span>
              )}
            </div>
            <span className="text-gray-400">{showAdmin ? '▲' : '▼'}</span>
          </button>

          {showAdmin && (
            <div className="border-t px-4 py-3 space-y-3">
              {bufferNotes.length === 0 ? (
                <div className="text-sm text-gray-500 text-center py-2">Aucune note dans le buffer.</div>
              ) : (
                <div className="space-y-2 max-h-64 overflow-y-auto">
                  {bufferNotes.map(note => (
                    <div
                      key={note.id}
                      className={`flex items-start gap-2 p-2 rounded border text-sm ${
                        note.status === 'validated' ? 'bg-green-50 border-green-200' :
                        note.status === 'pushed' ? 'bg-gray-50 border-gray-200 opacity-60' :
                        'bg-white border-gray-200'
                      }`}
                    >
                      {note.status === 'draft' && (
                        <input
                          type="checkbox"
                          checked={selectedNoteIds.has(note.id)}
                          onChange={() => toggleNoteSelection(note.id)}
                          className="mt-1 w-4 h-4"
                        />
                      )}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="font-medium text-gray-800">{note.tech_name}</span>
                          <span className="text-gray-400">—</span>
                          <span className="text-gray-600 truncate">{note.piano_id?.slice(-8)}</span>
                          <span className={`text-xs px-1.5 py-0.5 rounded ${
                            note.status === 'draft' ? 'bg-blue-100 text-blue-700' :
                            note.status === 'validated' ? 'bg-green-100 text-green-700' :
                            'bg-gray-100 text-gray-500'
                          }`}>
                            {note.status}
                          </span>
                        </div>
                        <div className="text-gray-600 mt-0.5 line-clamp-2">{note.note}</div>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* Admin action buttons */}
              <div className="flex gap-2 pt-2 border-t">
                <button
                  onClick={validateSelected}
                  disabled={selectedNoteIds.size === 0}
                  className="flex-1 py-2 px-3 text-sm font-medium rounded-lg bg-blue-500 text-white hover:bg-blue-600 disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  Valider ({selectedNoteIds.size})
                </button>
                <button
                  onClick={bundlePush}
                  disabled={validatedCount === 0 || bundlePushing}
                  className="flex-1 py-2 px-3 text-sm font-medium rounded-lg bg-green-600 text-white hover:bg-green-700 disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  {bundlePushing ? 'Envoi...' : `Bundle Push (${validatedCount})`}
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ===== PIANO LIST — SAISIE RAPIDE ===== */}
      <div className="bg-white rounded-lg shadow border border-gray-200">
        <div className="px-4 py-3 border-b flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-lg">🎹</span>
            <span className="font-semibold text-gray-800">Saisie rapide</span>
            <span className="text-sm text-gray-500">— {techName}</span>
          </div>
          <span className="text-xs text-gray-400">{pianos.length} pianos</span>
        </div>

        <div className="divide-y">
          {pianos.map(piano => {
            const isExpanded = expandedId === piano.id;
            const noteValue = localNotes.current[piano.id] || '';

            return (
              <div key={piano.id}>
                {/* Piano header — clickable */}
                <div
                  onClick={() => setExpandedId(isExpanded ? null : piano.id)}
                  className={`px-4 py-3 flex items-center justify-between cursor-pointer hover:bg-gray-50 active:bg-gray-100 ${
                    piano.is_priority ? 'border-l-4 border-green-500' : ''
                  }`}
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <span className="font-bold text-gray-700 whitespace-nowrap">
                      {piano.location || '?'}
                    </span>
                    <span className="text-gray-500 text-sm truncate">
                      {piano.make} {piano.model}
                    </span>
                  </div>
                  <div className="flex items-center gap-2 flex-shrink-0">
                    {piano.is_priority && (
                      <span className="text-xs bg-green-100 text-green-700 font-bold px-2 py-0.5 rounded-full">
                        Prioritaire
                      </span>
                    )}
                    {piano.buffer_note?.note && (
                      <span className="text-xs bg-blue-100 text-blue-700 px-1.5 py-0.5 rounded">
                        {piano.buffer_note.status === 'draft' ? '📝' : '✓'}
                      </span>
                    )}
                    {isAdmin && (
                      <button
                        onClick={(e) => { e.stopPropagation(); togglePriority(piano.id, piano.is_priority); }}
                        className={`w-6 h-6 rounded-full border-2 text-xs flex items-center justify-center ${
                          piano.is_priority
                            ? 'bg-green-500 border-green-500 text-white'
                            : 'border-gray-300 text-gray-400 hover:border-green-400'
                        }`}
                        title={piano.is_priority ? 'Retirer priorité' : 'Marquer prioritaire'}
                      >
                        ★
                      </button>
                    )}
                    <span className="text-gray-400 text-sm">{isExpanded ? '▲' : '▼'}</span>
                  </div>
                </div>

                {/* Expanded note area */}
                {isExpanded && (
                  <div className="px-4 pb-4 bg-gray-50 border-t">
                    <div className="pt-3">
                      {piano.serialNumber && (
                        <div className="text-xs text-gray-500 mb-2">
                          Série: {piano.serialNumber} — {piano.type === 'GRAND' ? 'Queue' : 'Droit'}
                        </div>
                      )}
                      <textarea
                        value={noteValue}
                        onChange={(e) => handleNoteChange(piano.id, e.target.value)}
                        placeholder="Notes d'accord, observations..."
                        className="w-full border border-gray-300 rounded-lg p-3 text-sm h-28 resize-y focus:outline-none focus:ring-2 focus:ring-blue-300 focus:border-blue-400"
                        autoFocus
                      />
                      <div className="flex justify-end mt-1">
                        <SaveIndicator pianoId={piano.id} />
                      </div>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
