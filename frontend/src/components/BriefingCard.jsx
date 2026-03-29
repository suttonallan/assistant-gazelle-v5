import React, { useState } from 'react'
import { API_URL } from '../utils/apiConfig'

/**
 * BriefingCard V4 — Narrative-First Card
 *
 * LEVEL 1 (always visible):
 *   Header (time + name + client_since) + badges + piano + narrative + action items
 *
 * LEVEL 2 (expand):
 *   Follow-ups, estimates, Allan's feedback
 */
export default function BriefingCard({ briefing, currentUser, onFeedbackSaved }) {
  const [expanded, setExpanded] = useState(false)
  const [showFeedback, setShowFeedback] = useState(false)
  const [feedbackValue, setFeedbackValue] = useState('')
  const [saving, setSaving] = useState(false)
  const [resolvingId, setResolvingId] = useState(null)
  const [suggestedActions, setSuggestedActions] = useState(null)
  const [analyzing, setAnalyzing] = useState(false)
  const [applying, setApplying] = useState(false)
  const [actionStates, setActionStates] = useState({})
  const [feedbackDone, setFeedbackDone] = useState(false)

  const isAllan = currentUser?.email === 'asutton@piano-tek.com'

  const {
    appointment,
    narrative,
    action_items,
    flags,
    piano,
    client_name,
    client_since,
    follow_ups,
    estimate_items,
  } = briefing

  // ── Badges ──
  const badges = []
  if (flags?.language === 'EN') badges.push({ icon: '🇬🇧', label: 'Anglophone', color: 'bg-red-100 text-red-800' })
  if (flags?.language === 'BI') badges.push({ icon: '🇬🇧', label: 'Anglophone', color: 'bg-red-100 text-red-800' })
  if (flags?.pls) badges.push({ icon: '💧', label: 'PLS', color: 'bg-blue-100 text-blue-800' })
  if (flags?.dog_name) badges.push({ icon: '🐕', label: flags.dog_name, color: 'bg-amber-100 text-amber-800' })
  if (flags?.children_names) badges.push({ icon: '👧', label: flags.children_names, color: 'bg-pink-100 text-pink-800' })

  // Collaboration
  const collaboration = appointment?.collaboration || []
  const hasFollowUps = follow_ups?.length > 0
  const hasEstimates = estimate_items?.length > 0
  const hasExpandableContent = hasFollowUps || hasEstimates || isAllan

  // ── Handlers ──
  const analyzeFeedback = async () => {
    if (!feedbackValue.trim()) return
    setAnalyzing(true)
    setSuggestedActions(null)
    try {
      const response = await fetch(`${API_URL}/api/briefing/feedback/analyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          client_id: briefing.client_id,
          client_name: client_name || '',
          note: feedbackValue.trim(),
          narrative: narrative || '',
        })
      })
      if (response.ok) {
        const data = await response.json()
        const actions = data.suggested_actions || []
        setSuggestedActions(actions)
        const states = {}
        actions.forEach((_, idx) => { states[idx] = true })
        setActionStates(states)
      }
    } catch (err) {
      console.error('Erreur analyse:', err)
    } finally {
      setAnalyzing(false)
    }
  }

  const applyActions = async () => {
    const selected = (suggestedActions || []).filter((_, idx) => actionStates[idx])
    if (selected.length === 0) return
    setApplying(true)
    try {
      const response = await fetch(`${API_URL}/api/briefing/feedback/apply`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          actions: selected,
          created_by: currentUser?.email || 'asutton@piano-tek.com',
        })
      })
      if (response.ok) {
        setFeedbackDone(true)
        setSuggestedActions(null)
        setFeedbackValue('')
        setTimeout(() => {
          setShowFeedback(false)
          setFeedbackDone(false)
          onFeedbackSaved?.()
        }, 2000)
      }
    } catch (err) {
      console.error('Erreur application:', err)
    } finally {
      setApplying(false)
    }
  }

  const resolveFollowUp = async (itemId) => {
    setResolvingId(itemId)
    try {
      const response = await fetch(`${API_URL}/api/briefing/follow-up/resolve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          item_id: itemId,
          resolved_by: currentUser?.gazelleId || currentUser?.email,
        })
      })
      if (response.ok) {
        onFeedbackSaved?.()
      }
    } catch (err) {
      console.error('Erreur resolution:', err)
    } finally {
      setResolvingId(null)
    }
  }

  return (
    <div className="bg-white rounded-xl shadow-lg overflow-hidden mb-4 border border-gray-100">

      {/* ══════════ HEADER ══════════ */}
      <div className="bg-gradient-to-r from-blue-600 to-blue-700 px-4 py-3 text-white">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="text-2xl font-bold font-mono">
              {appointment?.time || '--:--'}
            </span>
            <div>
              <div className="font-semibold text-lg">
                {client_name || 'Client'}
                {client_since && (
                  <span className="text-blue-200 text-sm font-normal ml-2">
                    {client_since}
                  </span>
                )}
              </div>
              {appointment?.title && appointment.title !== client_name && (
                <div className="text-blue-100 text-sm">{appointment.title}</div>
              )}
            </div>
          </div>
          <div className="flex items-center gap-2">
            {appointment?.technician_name && (
              <span
                className="bg-white/20 text-white text-xs font-bold px-2 py-1 rounded-full"
                title={appointment.technician_name}
              >
                {appointment.technician_name.charAt(0).toUpperCase()}
              </span>
            )}
            {!client_since && (
              <span className="bg-green-400 text-green-900 text-xs px-2 py-1 rounded-full font-medium">
                Premier RV
              </span>
            )}
          </div>
        </div>
      </div>

      {/* ══════════ BODY — LEVEL 1 ══════════ */}
      <div className="p-4 space-y-3">

        {/* Badges + Piano (compact row) */}
        <div className="flex flex-wrap items-center gap-2">
          {badges.map((badge, idx) => (
            <span
              key={idx}
              className={`px-2.5 py-0.5 rounded-full text-xs font-semibold flex items-center gap-1 ${badge.color}`}
            >
              <span>{badge.icon}</span>
              <span>{badge.label}</span>
            </span>
          ))}
          {flags?.piano_label && (
            <span className="text-sm text-gray-600 flex items-center gap-1">
              🎹 {flags.piano_label}
            </span>
          )}
        </div>

        {/* Collaboration */}
        {collaboration.length > 0 && (
          <div className="bg-indigo-50 border-l-4 border-indigo-400 px-3 py-2 text-sm text-indigo-800">
            En collaboration avec {collaboration.map((c, idx) => (
              <span key={idx} className="font-semibold">
                {c.technician_name}{c.time ? ` (${c.time})` : ''}
                {idx < collaboration.length - 1 ? ', ' : ''}
              </span>
            ))}
          </div>
        )}

        {/* ── NARRATIVE (the heart of V4) ── */}
        {narrative && (
          <div className="text-gray-800 text-sm leading-relaxed">
            {narrative}
          </div>
        )}

        {/* Action items */}
        {action_items?.length > 0 && (
          <div className="space-y-1">
            {action_items.map((item, idx) => (
              <div
                key={idx}
                className="flex items-start gap-2 text-sm bg-amber-50 border-l-4 border-amber-400 px-3 py-1.5 text-amber-900"
              >
                <span className="font-bold mt-0.5">→</span>
                <span>{item}</span>
              </div>
            ))}
          </div>
        )}

        {/* Follow-ups badge (summary when collapsed) */}
        {hasFollowUps && !expanded && (
          <div className="text-xs text-amber-700 font-medium">
            🔔 {follow_ups.length} suivi(s) en attente
          </div>
        )}

        {/* Expand button */}
        {hasExpandableContent && (
          <button
            onClick={() => setExpanded(!expanded)}
            className="w-full text-center text-sm text-blue-600 hover:text-blue-800 font-medium py-1 border-t border-gray-100 mt-2"
          >
            {expanded ? 'Voir moins ▲' : 'Voir plus ▼'}
          </button>
        )}
      </div>

      {/* ══════════ LEVEL 2: EXPANDED DETAILS ══════════ */}
      {expanded && (
        <div className="border-t border-gray-200 p-4 space-y-4 bg-gray-50">

          {/* Follow-ups with resolve button */}
          {hasFollowUps && (
            <div>
              <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
                Suivis en attente
              </h4>
              <div className="space-y-2">
                {follow_ups.map((fu, idx) => (
                  <div key={fu.id || idx} className="flex items-start justify-between bg-amber-50 rounded-lg px-3 py-2">
                    <div className="flex-1">
                      <div className="text-sm font-medium text-amber-900">{fu.description}</div>
                      <div className="text-xs text-amber-600 mt-0.5">
                        {fu.category && <span className="capitalize">{fu.category}</span>}
                        {fu.detected_at && <span> — {fu.detected_at.substring(0, 10)}</span>}
                      </div>
                    </div>
                    {fu.id && (
                      <button
                        onClick={() => resolveFollowUp(fu.id)}
                        disabled={resolvingId === fu.id}
                        className="ml-2 text-green-600 hover:text-green-800 text-xs font-medium px-2 py-1 rounded border border-green-300 hover:bg-green-50 disabled:opacity-50 flex-shrink-0"
                      >
                        {resolvingId === fu.id ? '...' : 'Fait ✓'}
                      </button>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Estimates */}
          {hasEstimates && (
            <div>
              <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
                Soumissions
              </h4>
              <div className="space-y-2">
                {estimate_items.map((item, idx) => (
                  <div key={idx} className="text-sm border-l-2 border-green-400 pl-3 bg-green-50 rounded-r py-1.5 pr-2">
                    {item.date && (
                      <div className="text-xs text-gray-500 mb-0.5">{item.date}</div>
                    )}
                    <div className="text-gray-800">{item.text}</div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Allan feedback */}
          {isAllan && (
            <div className="border-t border-gray-200 pt-3">
              {!showFeedback ? (
                <button
                  onClick={() => setShowFeedback(true)}
                  className="text-sm text-purple-600 hover:text-purple-800 font-medium flex items-center gap-1"
                >
                  <span>🧠</span> Ajuster l'Intelligence
                </button>
              ) : feedbackDone ? (
                <div className="bg-green-50 border border-green-200 rounded-lg px-4 py-3 text-green-800 text-sm font-medium">
                  Actions enregistrées — l'IA en tiendra compte aux prochains briefings
                </div>
              ) : (
                <div className="space-y-3">
                  <textarea
                    value={feedbackValue}
                    onChange={(e) => setFeedbackValue(e.target.value)}
                    placeholder="Ex: Ce client ne parle pas anglais, l'IA s'est trompée..."
                    className="w-full text-sm border border-gray-300 rounded-lg px-3 py-2 resize-none focus:ring-2 focus:ring-purple-300 focus:border-purple-400"
                    rows={3}
                    disabled={analyzing || !!suggestedActions}
                  />

                  {/* Boutons avant analyse */}
                  {!suggestedActions && (
                    <div className="flex gap-2">
                      <button
                        onClick={analyzeFeedback}
                        disabled={analyzing || !feedbackValue.trim()}
                        className="bg-purple-600 text-white text-sm px-4 py-2 rounded-lg hover:bg-purple-700 disabled:opacity-50 flex items-center gap-2"
                      >
                        {analyzing ? (
                          <><span className="animate-spin">⏳</span> Analyse en cours...</>
                        ) : (
                          <><span>🧠</span> Analyser</>
                        )}
                      </button>
                      <button
                        onClick={() => { setShowFeedback(false); setFeedbackValue('') }}
                        className="text-gray-500 text-sm px-3 py-2 hover:text-gray-700"
                      >
                        Annuler
                      </button>
                    </div>
                  )}

                  {/* Suggestions d'actions */}
                  {suggestedActions && suggestedActions.length > 0 && (
                    <div className="space-y-2">
                      <div className="text-xs font-semibold text-gray-500 uppercase tracking-wider">
                        Actions suggérées
                      </div>
                      {suggestedActions.map((action, idx) => (
                        <label
                          key={idx}
                          className={`flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-colors ${
                            actionStates[idx]
                              ? action.scope === 'global'
                                ? 'bg-blue-50 border-blue-300'
                                : 'bg-purple-50 border-purple-300'
                              : 'bg-gray-50 border-gray-200 opacity-60'
                          }`}
                        >
                          <input
                            type="checkbox"
                            checked={!!actionStates[idx]}
                            onChange={() => setActionStates(prev => ({ ...prev, [idx]: !prev[idx] }))}
                            className="mt-0.5 rounded"
                          />
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 mb-1">
                              <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${
                                action.scope === 'global'
                                  ? 'bg-blue-100 text-blue-800'
                                  : 'bg-purple-100 text-purple-800'
                              }`}>
                                {action.scope === 'global' ? '🌐 Tous les clients' : `👤 ${action.client_name || client_name}`}
                              </span>
                            </div>
                            <div className="text-sm text-gray-800 font-medium">{action.note}</div>
                            {action.reason && (
                              <div className="text-xs text-gray-500 mt-1">{action.reason}</div>
                            )}
                          </div>
                        </label>
                      ))}
                      <div className="flex gap-2 pt-1">
                        <button
                          onClick={applyActions}
                          disabled={applying || !Object.values(actionStates).some(v => v)}
                          className="bg-green-600 text-white text-sm px-4 py-2 rounded-lg hover:bg-green-700 disabled:opacity-50 flex items-center gap-2"
                        >
                          {applying ? 'Enregistrement...' : 'Appliquer'}
                        </button>
                        <button
                          onClick={() => { setSuggestedActions(null); setFeedbackValue('') }}
                          className="text-gray-500 text-sm px-3 py-2 hover:text-gray-700"
                        >
                          Recommencer
                        </button>
                        <button
                          onClick={() => { setShowFeedback(false); setSuggestedActions(null); setFeedbackValue('') }}
                          className="text-gray-500 text-sm px-3 py-2 hover:text-gray-700"
                        >
                          Annuler
                        </button>
                      </div>
                    </div>
                  )}

                  {/* Aucune suggestion */}
                  {suggestedActions && suggestedActions.length === 0 && (
                    <div className="text-sm text-gray-500 italic">
                      Aucune action suggérée. Reformule ton commentaire ou annule.
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
