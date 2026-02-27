/**
 * VDI_NotesView — Mode VDI : Saisie rapide + Admin buffer
 *
 * Fonctionnalités :
 * - Auto-save debounce 500ms vers le buffer Supabase
 * - Feedback visuel universel : Modifié → En cours → ✅ Sauvegardé
 * - localStorage de secours (rien ne se perd si l'onglet est fermé)
 * - Identification par nom réel du technicien connecté (via PIN)
 * - Admin : buffer review, validation, Bundle Push, toggle priorité
 */

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { getUserRole } from '../../config/roles';
import { TECHNICIENS_LISTE } from '../../config/techniciens.config';

const API_URL = import.meta.env.VITE_API_URL || (import.meta.env.DEV ? '' : 'https://assistant-gazelle-v5-api.onrender.com');

// ========== localStorage helpers ==========
const LS_PREFIX = 'vdi_note_';
function lsSave(pianoId, value) {
  try { localStorage.setItem(LS_PREFIX + pianoId, value); } catch {}
}
function lsLoad(pianoId) {
  try { return localStorage.getItem(LS_PREFIX + pianoId) || ''; } catch { return ''; }
}
function lsRemove(pianoId) {
  try { localStorage.removeItem(LS_PREFIX + pianoId); } catch {}
}

// ========== Resolve tech display name from currentUser ==========
function resolveTechName(currentUser) {
  // Try to match by email in the technicien config
  if (currentUser?.email) {
    const match = TECHNICIENS_LISTE.find(
      t => t.email.toLowerCase() === currentUser.email.toLowerCase()
    );
    if (match) return match.prenom; // "Nicolas", "Jean-Philippe", "Allan"
  }
  // Fallback to currentUser.name or email prefix
  return currentUser?.name || currentUser?.email?.split('@')[0] || 'Inconnu';
}

export default function VDI_NotesView({ currentUser }) {
  // Auth & token
  const [techToken, setTechToken] = useState(null);
  const [techName, setTechName] = useState('');

  // Pianos & notes
  const [pianos, setPianos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [expandedId, setExpandedId] = useState(null);
  // Status per piano: 'idle' | 'modified' | 'saving' | 'saved' | 'error'
  const [saveStatus, setSaveStatus] = useState({});

  // Admin buffer
  const [bufferNotes, setBufferNotes] = useState([]);
  const [selectedNoteIds, setSelectedNoteIds] = useState(new Set());
  const [bundlePushing, setBundlePushing] = useState(false);
  const [showAdmin, setShowAdmin] = useState(false);

  // Admin inline editing
  const [editingNoteId, setEditingNoteId] = useState(null);
  const [editingText, setEditingText] = useState('');
  const [editSaving, setEditSaving] = useState(false);

  // Admin identity switcher — enter notes as a guest tech
  const [guestTechnicians, setGuestTechnicians] = useState([]);
  const [impersonating, setImpersonating] = useState(null); // null = self, or { tech_token, tech_name }
  const [showAddGuest, setShowAddGuest] = useState(false);
  const [newGuestName, setNewGuestName] = useState('');
  const [addingGuest, setAddingGuest] = useState(false);

  // Debounce timers
  const debounceTimers = useRef({});
  // Local note values (controlled textareas)
  const localNotes = useRef({});
  // Track which pianos have been initialized from localStorage
  const lsRestored = useRef(new Set());

  const userRole = getUserRole(currentUser?.email);
  const isAdmin = userRole === 'admin' || userRole === 'nick';

  // ========== 1. Auto-provision token on mount ==========
  useEffect(() => {
    // Skip if impersonating — token is set by switchIdentity
    if (impersonating) return;
    const ensureToken = async () => {
      const name = resolveTechName(currentUser);
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
  }, [currentUser, impersonating]);

  // ========== 1b. Load guest technicians for identity switcher (admin) ==========
  // Permanent staff names to exclude from the guest list
  const permanentStaff = TECHNICIENS_LISTE.map(t => t.prenom.toLowerCase());

  const loadGuests = useCallback(async () => {
    if (!isAdmin) return;
    try {
      const r = await fetch(`${API_URL}/api/vdi/admin/guest-technicians`);
      if (!r.ok) return;
      const data = await r.json();
      // Filter: active AND not permanent staff
      setGuestTechnicians(data.filter(g =>
        g.active && !permanentStaff.includes(g.tech_name.toLowerCase())
      ));
    } catch (e) {
      console.error('Erreur chargement invités:', e);
    }
  }, [isAdmin]);

  useEffect(() => { loadGuests(); }, [loadGuests]);

  // ========== 1c. Switch identity to a guest tech ==========
  const switchIdentity = (guest) => {
    // Reset note state
    localNotes.current = {};
    lsRestored.current = new Set();
    setSaveStatus({});
    setExpandedId(null);
    setPianos([]);

    if (guest) {
      setImpersonating(guest);
      setTechToken(guest.tech_token);
      setTechName(guest.tech_name);
    } else {
      // Back to self — useEffect will re-provision own token
      setImpersonating(null);
      setTechToken(null);
    }
  };

  // ========== 1d. Create a new guest technician ==========
  const createGuestTech = async () => {
    const name = newGuestName.trim();
    if (!name) return;
    setAddingGuest(true);
    try {
      const r = await fetch(`${API_URL}/api/vdi/admin/guest-technicians`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tech_name: name }),
      });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const created = await r.json();
      setNewGuestName('');
      setShowAddGuest(false);
      await loadGuests();
      // Auto-switch to the new tech
      switchIdentity({ tech_token: created.tech_token, tech_name: created.tech_name });
    } catch (e) {
      console.error('Erreur création invité:', e);
      alert('Erreur: ' + e.message);
    } finally {
      setAddingGuest(false);
    }
  };

  // ========== 2. Load pianos when token is ready ==========
  const loadPianos = useCallback(async () => {
    if (!techToken) return;
    setLoading(true);
    try {
      const r = await fetch(`${API_URL}/api/vdi/guest/${techToken}/pianos`);
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const data = await r.json();
      const loadedPianos = data.pianos || [];
      setPianos(loadedPianos);

      // Initialize local notes: server buffer first, then localStorage fallback
      loadedPianos.forEach(p => {
        const serverNote = p.buffer_note?.note || '';
        const lsNote = lsLoad(p.id);

        if (lsNote && lsNote.length > serverNote.length && !lsRestored.current.has(p.id)) {
          // localStorage has more content → user probably closed before save finished
          localNotes.current[p.id] = lsNote;
          lsRestored.current.add(p.id);
          setSaveStatus(prev => ({ ...prev, [p.id]: 'modified' }));
        } else if (serverNote) {
          localNotes.current[p.id] = serverNote;
          // Clear localStorage since server is up to date
          lsRemove(p.id);
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

  // ========== 4. Auto-save with debounce + localStorage ==========
  const handleNoteChange = (pianoId, value) => {
    localNotes.current[pianoId] = value;
    // Persist immediately in localStorage (crash-safe)
    lsSave(pianoId, value);
    // Force re-render for textarea
    setPianos(prev => [...prev]);

    clearTimeout(debounceTimers.current[pianoId]);
    setSaveStatus(prev => ({ ...prev, [pianoId]: 'modified' }));

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
        // Server is now up to date → remove localStorage backup
        lsRemove(pianoId);
        // Refresh admin buffer silently
        if (isAdmin) loadBuffer();
      } catch {
        setSaveStatus(prev => ({ ...prev, [pianoId]: 'error' }));
        // Keep localStorage so nothing is lost
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
        alert(`Envoyé! ${data.notes_count} note(s) pour ${data.pianos_count} piano(s).\nEvent: ${data.event_id}`);
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

  const startEditNote = (note) => {
    setEditingNoteId(note.id);
    setEditingText(note.note);
  };

  const cancelEditNote = () => {
    setEditingNoteId(null);
    setEditingText('');
  };

  const saveEditNote = async () => {
    if (!editingNoteId) return;
    setEditSaving(true);
    try {
      const r = await fetch(`${API_URL}/api/vdi/admin/buffer/${editingNoteId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ note: editingText }),
      });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      setEditingNoteId(null);
      setEditingText('');
      await loadBuffer();
    } catch (e) {
      alert('Erreur sauvegarde: ' + e.message);
    } finally {
      setEditSaving(false);
    }
  };

  // ========== 6. Save Status Badge (prominent, universal) ==========
  const SaveBadge = ({ pianoId }) => {
    const s = saveStatus[pianoId];
    if (!s || s === 'idle') return null;

    const config = {
      modified: { bg: 'bg-amber-100', text: 'text-amber-700', border: 'border-amber-300', label: 'Modifié', icon: '●' },
      saving:   { bg: 'bg-blue-100',  text: 'text-blue-700',  border: 'border-blue-300',  label: 'En cours...', icon: '↻' },
      saved:    { bg: 'bg-green-100', text: 'text-green-700', border: 'border-green-300', label: 'Sauvegardé', icon: '✓' },
      error:    { bg: 'bg-red-100',   text: 'text-red-700',   border: 'border-red-300',   label: 'Erreur — réessai auto', icon: '✕' },
    };
    const c = config[s];

    return (
      <div className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold border ${c.bg} ${c.text} ${c.border} ${s === 'saving' ? 'animate-pulse' : ''}`}>
        <span>{c.icon}</span>
        <span>{c.label}</span>
      </div>
    );
  };

  // ========== RENDER ==========
  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-center">
          <div className="w-8 h-8 border-3 border-gray-300 border-t-blue-500 rounded-full animate-spin mx-auto mb-3" />
          <div className="text-gray-500">Chargement Mode VDI...</div>
        </div>
      </div>
    );
  }

  const draftCount = bufferNotes.filter(n => n.status === 'draft').length;
  const validatedCount = bufferNotes.filter(n => n.status === 'validated').length;

  // ========== NoteRow — reusable per-note rendering ==========
  const NoteRow = ({ note }) => (
    <div
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
        </div>
        {editingNoteId === note.id ? (
          <div className="mt-1 space-y-1.5">
            <textarea
              value={editingText}
              onChange={(e) => setEditingText(e.target.value)}
              className="w-full border border-blue-300 rounded p-2 text-sm h-24 resize-y focus:outline-none focus:ring-2 focus:ring-blue-300"
              autoFocus
            />
            <div className="flex gap-1.5">
              <button
                onClick={saveEditNote}
                disabled={editSaving}
                className="px-2.5 py-1 text-xs font-medium rounded bg-blue-500 text-white hover:bg-blue-600 disabled:opacity-50"
              >
                {editSaving ? 'Sauvegarde...' : 'Sauvegarder'}
              </button>
              <button
                onClick={cancelEditNote}
                disabled={editSaving}
                className="px-2.5 py-1 text-xs font-medium rounded bg-gray-200 text-gray-700 hover:bg-gray-300 disabled:opacity-50"
              >
                Annuler
              </button>
            </div>
          </div>
        ) : (
          <div
            onClick={(e) => { e.stopPropagation(); if (note.status !== 'pushed') startEditNote(note); }}
            className={`text-gray-600 mt-0.5 ${note.status !== 'pushed' ? 'cursor-pointer hover:bg-blue-50 hover:text-blue-700 rounded px-1 -mx-1 transition-colors' : ''}`}
            title={note.status !== 'pushed' ? 'Cliquer pour modifier' : ''}
          >
            {note.note}
          </div>
        )}
      </div>
    </div>
  );

  return (
    <div className="space-y-4">
      {/* ===== IDENTITY SWITCHER (Admin only) ===== */}
      {isAdmin && (
        <div className={`rounded-lg shadow border overflow-hidden ${impersonating ? 'bg-purple-50 border-purple-300' : 'bg-white border-gray-200'}`}>
          <div className="px-4 py-3">
            <div className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
              Entrer les notes au nom de :
            </div>
            <div className="flex flex-wrap gap-2">
              <button
                onClick={() => switchIdentity(null)}
                className={`px-3 py-1.5 text-sm font-medium rounded-full transition-colors ${
                  !impersonating
                    ? 'bg-blue-500 text-white shadow-sm'
                    : 'bg-white text-gray-600 border border-gray-300 hover:bg-gray-50'
                }`}
              >
                Moi (Allan)
              </button>
              {guestTechnicians.map(g => (
                <button
                  key={g.tech_token}
                  onClick={() => switchIdentity(g)}
                  className={`px-3 py-1.5 text-sm font-medium rounded-full transition-colors ${
                    impersonating?.tech_token === g.tech_token
                      ? 'bg-purple-600 text-white shadow-sm'
                      : 'bg-white text-gray-600 border border-gray-300 hover:bg-gray-50'
                  }`}
                >
                  {g.tech_name}
                </button>
              ))}
              {/* Add new guest tech */}
              {!showAddGuest ? (
                <button
                  onClick={() => setShowAddGuest(true)}
                  className="px-3 py-1.5 text-sm font-medium rounded-full border-2 border-dashed border-gray-300 text-gray-400 hover:border-purple-400 hover:text-purple-500 transition-colors"
                >
                  + Ajouter
                </button>
              ) : (
                <div className="flex items-center gap-1.5">
                  <input
                    type="text"
                    value={newGuestName}
                    onChange={(e) => setNewGuestName(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && createGuestTech()}
                    placeholder="Prénom du tech"
                    className="px-2.5 py-1 text-sm border border-purple-300 rounded-full w-36 focus:outline-none focus:ring-2 focus:ring-purple-300"
                    autoFocus
                    disabled={addingGuest}
                  />
                  <button
                    onClick={createGuestTech}
                    disabled={!newGuestName.trim() || addingGuest}
                    className="px-2.5 py-1 text-sm font-medium rounded-full bg-purple-600 text-white hover:bg-purple-700 disabled:opacity-50"
                  >
                    {addingGuest ? '...' : 'OK'}
                  </button>
                  <button
                    onClick={() => { setShowAddGuest(false); setNewGuestName(''); }}
                    className="px-2 py-1 text-sm text-gray-400 hover:text-gray-600"
                  >
                    x
                  </button>
                </div>
              )}
            </div>
            {impersonating && (
              <div className="mt-2 text-sm text-purple-700 font-medium">
                Les notes seront enregistrées sous le nom de <strong>{impersonating.tech_name}</strong>
              </div>
            )}
          </div>
        </div>
      )}

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
                <div className="space-y-3 max-h-96 overflow-y-auto">
                  {/* --- Section Brouillons --- */}
                  {(() => { const drafts = bufferNotes.filter(n => n.status === 'draft'); return drafts.length > 0 && (
                    <div>
                      <div className="flex items-center gap-2 mb-1.5">
                        <span className="text-xs font-bold text-blue-700 uppercase tracking-wide">Brouillons</span>
                        <span className="text-xs text-blue-500">({drafts.length})</span>
                        {drafts.length > 1 && (
                          <button
                            onClick={() => {
                              const allSelected = drafts.every(n => selectedNoteIds.has(n.id));
                              setSelectedNoteIds(prev => {
                                const next = new Set(prev);
                                drafts.forEach(n => allSelected ? next.delete(n.id) : next.add(n.id));
                                return next;
                              });
                            }}
                            className="text-xs text-blue-500 hover:text-blue-700 underline"
                          >
                            {drafts.every(n => selectedNoteIds.has(n.id)) ? 'Tout desélectionner' : 'Tout sélectionner'}
                          </button>
                        )}
                      </div>
                      <div className="space-y-1.5">
                        {drafts.map(note => (
                          <NoteRow key={note.id} note={note} />
                        ))}
                      </div>
                    </div>
                  ); })()}

                  {/* --- Section Validées --- */}
                  {(() => { const validated = bufferNotes.filter(n => n.status === 'validated'); return validated.length > 0 && (
                    <div>
                      <div className="flex items-center gap-2 mb-1.5">
                        <span className="text-xs font-bold text-green-700 uppercase tracking-wide">Validées — prêtes à pousser</span>
                        <span className="text-xs text-green-500">({validated.length})</span>
                      </div>
                      <div className="space-y-1.5">
                        {validated.map(note => (
                          <NoteRow key={note.id} note={note} />
                        ))}
                      </div>
                    </div>
                  ); })()}

                  {/* --- Section Poussées (collapsed) --- */}
                  {(() => { const pushed = bufferNotes.filter(n => n.status === 'pushed'); return pushed.length > 0 && (
                    <details className="group">
                      <summary className="flex items-center gap-2 mb-1.5 cursor-pointer text-xs text-gray-400 hover:text-gray-600">
                        <span className="font-bold uppercase tracking-wide">Déjà poussées</span>
                        <span>({pushed.length})</span>
                        <span className="group-open:rotate-90 transition-transform">▶</span>
                      </summary>
                      <div className="space-y-1.5">
                        {pushed.map(note => (
                          <NoteRow key={note.id} note={note} />
                        ))}
                      </div>
                    </details>
                  ); })()}
                </div>
              )}

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
      <div className={`rounded-lg shadow border ${impersonating ? 'border-purple-300' : 'border-gray-200'} bg-white`}>
        <div className={`px-4 py-3 border-b flex items-center justify-between ${impersonating ? 'bg-purple-50 border-purple-200' : ''}`}>
          <div className="flex items-center gap-2">
            <span className="text-lg">🎹</span>
            <span className="font-semibold text-gray-800">Saisie rapide</span>
            <span className={`text-sm font-medium ${impersonating ? 'text-purple-700' : 'text-gray-500'}`}>
              — {techName}{impersonating ? ' (proxy)' : ''}
            </span>
          </div>
          <span className="text-xs text-gray-400">{pianos.length} pianos</span>
        </div>

        <div className="divide-y">
          {pianos.map(piano => {
            const isExpanded = expandedId === piano.id;
            const noteValue = localNotes.current[piano.id] || '';

            return (
              <div key={piano.id}>
                {/* Piano header */}
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
                    {piano.buffer_note?.note && !isExpanded && (
                      <span className="text-xs bg-blue-100 text-blue-700 px-1.5 py-0.5 rounded">
                        {piano.buffer_note.status === 'draft' ? '📝' : '✓'}
                      </span>
                    )}
                    {/* Save status visible even when collapsed */}
                    {!isExpanded && saveStatus[piano.id] === 'modified' && (
                      <span className="w-2 h-2 rounded-full bg-amber-400" title="Modifié (non sauvegardé)" />
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
                      <div className="flex justify-between items-center mt-2">
                        <div className="text-xs text-gray-400">
                          {techName} — auto-save 0.5s
                        </div>
                        <SaveBadge pianoId={piano.id} />
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
