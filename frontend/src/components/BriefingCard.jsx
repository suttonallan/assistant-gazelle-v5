import React, { useState } from 'react'
import { API_URL } from '../utils/apiConfig'

/**
 * BriefingCard V3 - Carte de briefing intelligent à deux niveaux
 *
 * NIVEAU 1 (coup d'oeil, 10 secondes):
 *   Heure + client + ancienneté + icônes + piano + warnings + paiement
 *
 * NIVEAU 2 (clic "Voir plus"):
 *   Profil détaillé + historique technique + PLS + follow-ups + courtoisies
 *
 * Anti-hallucination: chaque donnée vient de Gazelle via extraction validée.
 */
export default function BriefingCard({ briefing, currentUser, onFeedbackSaved }) {
  const [expanded, setExpanded] = useState(false)
  const [showFeedback, setShowFeedback] = useState(false)
  const [feedbackValue, setFeedbackValue] = useState('')
  const [saving, setSaving] = useState(false)
  const [resolvingId, setResolvingId] = useState(null)

  const isAllan = currentUser?.email === 'asutton@piano-tek.com'

  const {
    appointment,
    profile,
    piano,
    technical_history,
    estimate_items,
    client_name,
    client_since,
    confidence_score,
    follow_ups,
    extraction_mode,
  } = briefing

  // ── NIVEAU 1: Icônes rapides ──
  const profileIcons = []
  if (profile?.language === 'EN') profileIcons.push({ icon: '🇬🇧', label: 'Anglophone' })
  if (profile?.language === 'BI') profileIcons.push({ icon: '🇬🇧🇫🇷', label: 'Bilingue' })
  if (profile?.pets?.length > 0) profileIcons.push({ icon: '🐕', label: profile.pets.join(', ') })
  if (profile?.courtesies?.includes('enlever chaussures')) profileIcons.push({ icon: '👟', label: 'Enlever chaussures' })
  if (profile?.courtesies?.includes('appeler avant')) profileIcons.push({ icon: '📞', label: 'Appeler avant' })
  if (profile?.payment_method) profileIcons.push({ icon: '💳', label: profile.payment_method })

  // Collaboration : autres techniciens au même RV
  const collaboration = appointment?.collaboration || []

  // Dernière visite (Niveau 1 résumé)
  const lastVisit = technical_history?.[0]
  const hasWarnings = piano?.warnings?.length > 0
  const hasFollowUps = follow_ups?.length > 0

  // PLS status pour Niveau 2
  const plsStatus = piano?.pls_status || {}

  // ── Handlers ──
  const saveFeedback = async () => {
    if (!feedbackValue.trim()) return
    setSaving(true)
    try {
      const response = await fetch(`${API_URL}/api/briefing/feedback`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          client_id: briefing.client_id,
          note: feedbackValue.trim(),
          created_by: currentUser?.email || 'asutton@piano-tek.com'
        })
      })
      if (response.ok) {
        setShowFeedback(false)
        setFeedbackValue('')
        onFeedbackSaved?.()
      }
    } catch (err) {
      console.error('Erreur feedback:', err)
    } finally {
      setSaving(false)
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
        onFeedbackSaved?.() // Refresh
      }
    } catch (err) {
      console.error('Erreur résolution:', err)
    } finally {
      setResolvingId(null)
    }
  }

  return (
    <div className="bg-white rounded-xl shadow-lg overflow-hidden mb-4 border border-gray-100">

      {/* ══════════ NIVEAU 1: COUP D'OEIL (toujours visible) ══════════ */}

      {/* Header */}
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
            {confidence_score < 0.5 && (
              <span className="bg-yellow-400 text-yellow-900 text-xs px-2 py-1 rounded-full">
                Donnees limitees
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Body Niveau 1 */}
      <div className="p-4 space-y-3">

        {/* Icones rapides */}
        {profileIcons.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {profileIcons.map((item, idx) => (
              <span
                key={idx}
                className="bg-gray-100 px-3 py-1 rounded-full text-sm flex items-center gap-1"
                title={item.label}
              >
                <span className="text-lg">{item.icon}</span>
                <span className="text-gray-600 hidden sm:inline">{item.label}</span>
              </span>
            ))}
          </div>
        )}

        {/* Piano */}
        {piano?.make && (
          <div className="flex items-start gap-2">
            <span className="text-xl">🎹</span>
            <div>
              <div className="font-medium text-gray-900">
                {piano.make} {piano.model}
                {piano.year > 0 && <span className="text-gray-500 ml-1">({piano.year})</span>}
              </div>
              {piano.age_years > 0 && (
                <div className="text-sm text-gray-500">
                  {piano.age_years} ans {piano.type && `\u00B7 ${piano.type}`}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Warnings (toujours visibles) */}
        {hasWarnings && (
          <div className="space-y-1">
            {piano.warnings.map((warning, idx) => (
              <div
                key={idx}
                className="bg-orange-50 border-l-4 border-orange-400 px-3 py-2 text-sm text-orange-800"
              >
                {warning}
              </div>
            ))}
          </div>
        )}

        {/* Collaboration : autre(s) technicien(s) au même client */}
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

        {/* Dernier tech + date (Niveau 1 résumé) */}
        {lastVisit && (
          <div className="text-sm text-gray-600">
            Dernier: <span className="font-medium">{lastVisit.technician}</span>, {lastVisit.date}
          </div>
        )}

        {/* Follow-ups badge (Niveau 1 résumé) */}
        {hasFollowUps && !expanded && (
          <div className="bg-amber-50 border-l-4 border-amber-400 px-3 py-2 text-sm text-amber-800">
            🔔 {follow_ups.length} suivi(s) en attente
            {follow_ups.length <= 2 && follow_ups.map((fu, idx) => (
              <div key={idx} className="ml-4 mt-1 text-amber-700">
                → {fu.description}
              </div>
            ))}
          </div>
        )}

        {/* Bouton Voir plus / Voir moins */}
        <button
          onClick={() => setExpanded(!expanded)}
          className="w-full text-center text-sm text-blue-600 hover:text-blue-800 font-medium py-1 border-t border-gray-100 mt-2"
        >
          {expanded ? 'Voir moins ▲' : 'Voir plus ▼'}
        </button>
      </div>

      {/* ══════════ NIVEAU 2: DETAILS (expandable) ══════════ */}

      {expanded && (
        <div className="border-t border-gray-200 p-4 space-y-4 bg-gray-50">

          {/* Profil detaille */}
          <div>
            <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
              Profil client
            </h4>
            <div className="space-y-1 text-sm">
              {profile?.language && (
                <div>Langue: <span className="font-medium">{
                  profile.language === 'FR' ? 'Francais' :
                  profile.language === 'EN' ? 'Anglais' : 'Bilingue'
                }</span></div>
              )}
              {profile?.pets?.length > 0 && (
                <div>Animaux: <span className="font-medium">{profile.pets.join(', ')}</span></div>
              )}
              {profile?.courtesies?.length > 0 && (() => {
                // Filtrer les courtoisies déjà affichées dans Stationnement ou Accès
                const parkingLower = (profile.parking_info || '').toLowerCase().trim()
                const accessLower = (profile.access_notes || '').toLowerCase().trim()
                const filtered = profile.courtesies.filter(c => {
                  const cLower = c.toLowerCase().trim()
                  return cLower !== parkingLower && cLower !== accessLower
                })
                return filtered.length > 0 ? (
                  <div>
                    Courtoisies:
                    {filtered.map((c, idx) => (
                      <span key={idx} className="ml-1 inline-block bg-blue-100 text-blue-800 text-xs px-2 py-0.5 rounded-full">
                        {c}
                      </span>
                    ))}
                  </div>
                ) : null
              })()}
              {profile?.personality && (
                <div>Temperament: <span className="font-medium">{profile.personality}</span></div>
              )}
              {profile?.payment_method && (
                <div>Paiement habituel: <span className="font-medium">{profile.payment_method}</span></div>
              )}
              {profile?.parking_info && (
                <div>Stationnement: <span className="font-medium">{profile.parking_info}</span></div>
              )}
              {profile?.access_code && (
                <div>Code: <span className="font-medium">{profile.access_code}</span></div>
              )}
              {profile?.access_notes && (
                <div>Acces: <span className="font-medium">{profile.access_notes}</span></div>
              )}
            </div>
          </div>

          {/* Historique technique */}
          {technical_history?.length > 0 && (
            <div>
              <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
                Historique technique
              </h4>
              <div className="space-y-2">
                {technical_history.map((visit, idx) => (
                  <div key={idx} className="text-sm border-l-2 border-gray-300 pl-3">
                    <div className="font-medium text-gray-800">
                      {visit.date} — {visit.technician || 'Tech inconnu'}
                    </div>
                    {visit.summary && (
                      <div className="text-gray-600 mt-0.5 text-xs leading-relaxed">
                        {visit.summary.length > 150
                          ? visit.summary.substring(0, 150) + '...'
                          : visit.summary}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Soumission / Estimate */}
          {estimate_items?.length > 0 && (
            <div>
              <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
                Soumission
              </h4>
              <div className="space-y-2">
                {estimate_items.map((item, idx) => (
                  <div key={idx} className="text-sm border-l-2 border-green-400 pl-3 bg-green-50 rounded-r py-1.5 pr-2">
                    {item.date && (
                      <div className="text-xs text-gray-500 mb-0.5">{item.date}</div>
                    )}
                    <div className="text-gray-800 whitespace-pre-wrap">{item.text}</div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* PLS Status detaille */}
          {piano?.dampp_chaser && (
            <div>
              <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
                Piano Life Saver (PLS)
              </h4>
              <div className="text-sm space-y-1">
                {plsStatus.last_service && (
                  <div>
                    Dernier service: <span className="font-medium">{plsStatus.last_service.date}</span>
                    {' '}({plsStatus.last_service.type === 'basic' ? 'test + buvards' :
                      plsStatus.last_service.type === 'annual' ? 'entretien annuel' : 'type inconnu'})
                    {plsStatus.last_service.source && (
                      <div className="text-xs text-gray-400 mt-0.5 italic">
                        📎 {plsStatus.last_service.source}
                      </div>
                    )}
                  </div>
                )}
                {plsStatus.last_annual && plsStatus.last_annual !== plsStatus.last_service && (
                  <div>
                    Dernier entretien annuel: <span className="font-medium">{plsStatus.last_annual.date}</span>
                    {plsStatus.months_since_annual && (
                      <span className="text-gray-500 ml-1">({plsStatus.months_since_annual} mois)</span>
                    )}
                  </div>
                )}
                {plsStatus.reason && (
                  <div className={`text-xs mt-1 ${plsStatus.needs_annual ? 'text-orange-700 font-medium' : 'text-gray-500'}`}>
                    {plsStatus.reason}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Follow-ups detailles avec bouton resolution */}
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
                      {fu.source_citation && (
                        <div className="text-xs text-amber-500 italic mt-0.5">
                          📎 {fu.source_citation}
                        </div>
                      )}
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

          {/* Mode extraction (debug info pour Allan) */}
          {isAllan && extraction_mode && (
            <div className="text-xs text-gray-400 text-right">
              Mode: {extraction_mode === 'ai' ? 'IA' : 'Regex'} | {briefing.notes_analyzed || 0} notes
            </div>
          )}
        </div>
      )}

      {/* ══════════ FOOTER: Feedback Allan ══════════ */}

      {isAllan && (
        <div className="border-t border-gray-100 px-4 py-2 bg-gray-50">
          {!showFeedback ? (
            <button
              onClick={() => setShowFeedback(true)}
              className="text-sm text-purple-600 hover:text-purple-800 font-medium flex items-center gap-1"
            >
              <span>🧠</span> Ajuster l'Intelligence
            </button>
          ) : (
            <div className="space-y-2">
              <textarea
                value={feedbackValue}
                onChange={(e) => setFeedbackValue(e.target.value)}
                placeholder="Ex: Le client parle anglais, il a un chien nomme Rex, stationnement a l'arriere..."
                className="w-full text-sm border border-gray-300 rounded px-3 py-2 resize-none"
                rows={3}
              />
              <div className="flex gap-2">
                <button
                  onClick={saveFeedback}
                  disabled={saving || !feedbackValue.trim()}
                  className="bg-purple-600 text-white text-sm px-3 py-1 rounded hover:bg-purple-700 disabled:opacity-50"
                >
                  {saving ? '...' : 'Enregistrer'}
                </button>
                <button
                  onClick={() => setShowFeedback(false)}
                  className="text-gray-600 text-sm px-3 py-1"
                >
                  Annuler
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
