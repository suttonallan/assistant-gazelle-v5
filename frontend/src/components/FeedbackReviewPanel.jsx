import React, { useState, useEffect } from 'react'
import { API_URL } from '../utils/apiConfig'

/**
 * FeedbackReviewPanel — Panneau de revue des notes "Ajuster l'Intelligence"
 *
 * Affiché dans MaJournée pour Allan quand il y a des notes brutes
 * en attente d'analyse. Permet de revoir, analyser et agir sur chaque note.
 */
export default function FeedbackReviewPanel({ currentUser, onUpdated }) {
  const [notes, setNotes] = useState([])
  const [globalRules, setGlobalRules] = useState([])
  const [loading, setLoading] = useState(true)
  const [expanded, setExpanded] = useState(false)
  const [analyzingId, setAnalyzingId] = useState(null)
  const [suggestions, setSuggestions] = useState({})
  const [actionStates, setActionStates] = useState({})
  const [applyingId, setApplyingId] = useState(null)
  const [deletingId, setDeletingId] = useState(null)

  useEffect(() => {
    loadFeedback()
  }, [])

  const loadFeedback = async () => {
    try {
      const resp = await fetch(`${API_URL}/api/briefing/feedback`)
      if (resp.ok) {
        const data = await resp.json()
        setNotes(data.client_notes || [])
        setGlobalRules(data.global_rules || [])
      }
    } catch (err) {
      console.error('Erreur chargement feedback:', err)
    } finally {
      setLoading(false)
    }
  }

  const analyzeNote = async (note) => {
    setAnalyzingId(note.id)
    try {
      const resp = await fetch(`${API_URL}/api/briefing/feedback/analyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          client_id: note.client_id,
          client_name: '',
          note: note.note,
          narrative: '',
        })
      })
      if (resp.ok) {
        const data = await resp.json()
        const actions = data.suggested_actions || []
        setSuggestions(prev => ({ ...prev, [note.id]: actions }))
        const states = {}
        actions.forEach((_, idx) => { states[idx] = true })
        setActionStates(prev => ({ ...prev, [note.id]: states }))
      }
    } catch (err) {
      console.error('Erreur analyse:', err)
    } finally {
      setAnalyzingId(null)
    }
  }

  const applyActions = async (noteId) => {
    const actions = (suggestions[noteId] || []).filter((_, idx) => actionStates[noteId]?.[idx])
    if (actions.length === 0) return
    setApplyingId(noteId)
    try {
      const resp = await fetch(`${API_URL}/api/briefing/feedback/apply`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          actions,
          created_by: currentUser?.email || 'asutton@piano-tek.com',
        })
      })
      if (resp.ok) {
        await deleteNote(noteId, true)
        setSuggestions(prev => { const n = { ...prev }; delete n[noteId]; return n })
        onUpdated?.()
      }
    } catch (err) {
      console.error('Erreur application:', err)
    } finally {
      setApplyingId(null)
    }
  }

  const deleteNote = async (noteId, silent = false) => {
    if (!silent) setDeletingId(noteId)
    try {
      await fetch(`${API_URL}/api/briefing/feedback/${noteId}`, { method: 'DELETE' })
      setNotes(prev => prev.filter(n => n.id !== noteId))
      setGlobalRules(prev => prev.filter(n => n.id !== noteId))
      if (!silent) onUpdated?.()
    } catch (err) {
      console.error('Erreur suppression:', err)
    } finally {
      if (!silent) setDeletingId(null)
    }
  }

  const totalCount = notes.length + globalRules.length
  if (loading || totalCount === 0) return null

  return (
    <div className="mb-6 bg-purple-50 border border-purple-200 rounded-xl overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full px-4 py-3 flex items-center justify-between hover:bg-purple-100 transition-colors"
      >
        <div className="flex items-center gap-2">
          <span className="text-xl">🧠</span>
          <span className="font-semibold text-purple-800">
            {totalCount} note{totalCount > 1 ? 's' : ''} d'intelligence active{totalCount > 1 ? 's' : ''}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs bg-purple-200 text-purple-800 px-2 py-0.5 rounded-full">
            Revoir
          </span>
          <span className="text-purple-600">{expanded ? '▲' : '▼'}</span>
        </div>
      </button>

      {expanded && (
        <div className="px-4 pb-4 space-y-3">
          <p className="text-xs text-purple-600">
            Ces notes influencent les briefings de l'IA. Analysez-les pour les affiner ou supprimez celles qui ne sont plus pertinentes.
          </p>

          {/* Global rules */}
          {globalRules.map(rule => (
            <NoteCard
              key={rule.id}
              note={rule}
              scope="global"
              analyzing={analyzingId === rule.id}
              applying={applyingId === rule.id}
              deleting={deletingId === rule.id}
              suggestions={suggestions[rule.id]}
              actionStates={actionStates[rule.id]}
              onAnalyze={() => analyzeNote({ ...rule, client_id: '__GLOBAL__' })}
              onApply={() => applyActions(rule.id)}
              onDelete={() => deleteNote(rule.id)}
              onToggleAction={(idx) => setActionStates(prev => ({
                ...prev,
                [rule.id]: { ...prev[rule.id], [idx]: !prev[rule.id]?.[idx] }
              }))}
              onDismissSuggestions={() => setSuggestions(prev => { const n = { ...prev }; delete n[rule.id]; return n })}
            />
          ))}

          {/* Client notes */}
          {notes.map(note => (
            <NoteCard
              key={note.id}
              note={note}
              scope="client"
              analyzing={analyzingId === note.id}
              applying={applyingId === note.id}
              deleting={deletingId === note.id}
              suggestions={suggestions[note.id]}
              actionStates={actionStates[note.id]}
              onAnalyze={() => analyzeNote(note)}
              onApply={() => applyActions(note.id)}
              onDelete={() => deleteNote(note.id)}
              onToggleAction={(idx) => setActionStates(prev => ({
                ...prev,
                [note.id]: { ...prev[note.id], [idx]: !prev[note.id]?.[idx] }
              }))}
              onDismissSuggestions={() => setSuggestions(prev => { const n = { ...prev }; delete n[note.id]; return n })}
            />
          ))}
        </div>
      )}
    </div>
  )
}

function NoteCard({
  note, scope, analyzing, applying, deleting,
  suggestions, actionStates,
  onAnalyze, onApply, onDelete, onToggleAction, onDismissSuggestions
}) {
  const scopeLabel = scope === 'global'
    ? '🌐 Règle globale'
    : `👤 ${note.client_id}`
  const scopeColor = scope === 'global'
    ? 'bg-blue-100 text-blue-800'
    : 'bg-purple-100 text-purple-800'
  const date = note.created_at ? new Date(note.created_at).toLocaleDateString('fr-CA') : ''

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-3 space-y-2">
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${scopeColor}`}>
              {scopeLabel}
            </span>
            {date && <span className="text-xs text-gray-400">{date}</span>}
          </div>
          <div className="text-sm text-gray-800">{note.note}</div>
        </div>
      </div>

      {/* Actions si pas de suggestions affichées */}
      {!suggestions && (
        <div className="flex gap-2 pt-1">
          <button
            onClick={onAnalyze}
            disabled={analyzing}
            className="text-xs bg-purple-600 text-white px-3 py-1.5 rounded-lg hover:bg-purple-700 disabled:opacity-50 flex items-center gap-1"
          >
            {analyzing ? <><span className="animate-spin">⏳</span> Analyse...</> : <><span>🧠</span> Analyser</>}
          </button>
          <button
            onClick={onDelete}
            disabled={deleting}
            className="text-xs text-red-500 hover:text-red-700 px-2 py-1.5 border border-red-200 rounded-lg hover:bg-red-50 disabled:opacity-50"
          >
            {deleting ? '...' : 'Supprimer'}
          </button>
        </div>
      )}

      {/* Suggestions d'actions */}
      {suggestions && suggestions.length > 0 && (
        <div className="space-y-2 pt-1">
          <div className="text-xs font-semibold text-gray-500 uppercase tracking-wider">
            Actions suggérées
          </div>
          {suggestions.map((action, idx) => (
            <label
              key={idx}
              className={`flex items-start gap-3 p-2 rounded-lg border cursor-pointer transition-colors ${
                actionStates?.[idx]
                  ? action.scope === 'global'
                    ? 'bg-blue-50 border-blue-300'
                    : 'bg-purple-50 border-purple-300'
                  : 'bg-gray-50 border-gray-200 opacity-60'
              }`}
            >
              <input
                type="checkbox"
                checked={!!actionStates?.[idx]}
                onChange={() => onToggleAction(idx)}
                className="mt-0.5 rounded"
              />
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-0.5">
                  <span className={`text-xs font-bold px-1.5 py-0.5 rounded-full ${
                    action.scope === 'global' ? 'bg-blue-100 text-blue-800' : 'bg-purple-100 text-purple-800'
                  }`}>
                    {action.scope === 'global' ? '🌐 Global' : `👤 Client`}
                  </span>
                </div>
                <div className="text-sm text-gray-800">{action.note}</div>
                {action.reason && <div className="text-xs text-gray-500 mt-0.5">{action.reason}</div>}
              </div>
            </label>
          ))}
          <div className="flex gap-2">
            <button
              onClick={onApply}
              disabled={applying || !Object.values(actionStates || {}).some(v => v)}
              className="text-xs bg-green-600 text-white px-3 py-1.5 rounded-lg hover:bg-green-700 disabled:opacity-50"
            >
              {applying ? 'Enregistrement...' : 'Appliquer et remplacer la note'}
            </button>
            <button
              onClick={onDismissSuggestions}
              className="text-xs text-gray-500 px-2 py-1.5 hover:text-gray-700"
            >
              Annuler
            </button>
          </div>
        </div>
      )}

      {suggestions && suggestions.length === 0 && (
        <div className="text-xs text-gray-500 italic">
          Aucune suggestion. Cette note est déjà bien formulée.
          <button onClick={onDismissSuggestions} className="ml-2 text-purple-600 hover:underline">OK</button>
        </div>
      )}
    </div>
  )
}
