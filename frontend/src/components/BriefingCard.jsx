import React, { useState } from 'react'
import { API_URL } from '../utils/apiConfig'

/**
 * BriefingCard - Carte de briefing intelligent pour technicien
 *
 * Affichage optimisé mobile (10 secondes de lecture):
 * - Icônes pour scan rapide
 * - Info piano condensée
 * - Alertes visuelles
 * - Bouton "Ajuster" pour Allan (super-utilisateur)
 */
export default function BriefingCard({ briefing, currentUser, onFeedbackSaved }) {
  const [showFeedback, setShowFeedback] = useState(false)
  const [feedbackValue, setFeedbackValue] = useState('')
  const [saving, setSaving] = useState(false)

  const isAllan = currentUser?.email === 'asutton@piano-tek.com'

  const { appointment, profile, piano, technical_history, client_name, confidence_score } = briefing

  // Générer les icônes de profil
  const profileIcons = []
  if (profile?.language === 'EN') profileIcons.push({ icon: '🇬🇧', label: 'Anglophone' })
  if (profile?.language === 'BI') profileIcons.push({ icon: '🇬🇧🇫🇷', label: 'Bilingue' })
  if (profile?.pets?.length > 0) profileIcons.push({ icon: '🐕', label: profile.pets.join(', ') })
  if (profile?.courtesies?.includes('enlever chaussures')) profileIcons.push({ icon: '👟❌', label: 'Enlever chaussures' })
  if (profile?.courtesies?.includes('offre café')) profileIcons.push({ icon: '☕', label: 'Offre café' })
  if (profile?.courtesies?.includes('appeler avant')) profileIcons.push({ icon: '📞', label: 'Appeler avant' })

  // Dernière recommandation
  const lastRec = technical_history?.[0]?.recommendations?.[0]

  // Sauvegarder une note libre (Allan only)
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

  return (
    <div className="bg-white rounded-xl shadow-lg overflow-hidden mb-4 border border-gray-100">
      {/* Header avec heure et client */}
      <div className="bg-gradient-to-r from-blue-600 to-blue-700 px-4 py-3 text-white">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="text-2xl font-bold font-mono">
              {appointment?.time || '--:--'}
            </span>
            <div>
              <div className="font-semibold text-lg">{client_name || 'Client'}</div>
              {appointment?.title && appointment.title !== client_name && (
                <div className="text-blue-100 text-sm">{appointment.title}</div>
              )}
            </div>
          </div>

          {/* Score de confiance */}
          {confidence_score < 0.5 && (
            <span className="bg-yellow-400 text-yellow-900 text-xs px-2 py-1 rounded-full">
              ⚠️ Données limitées
            </span>
          )}
        </div>
      </div>

      {/* Corps de la carte */}
      <div className="p-4 space-y-3">
        {/* Icônes de profil */}
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
                  {piano.age_years} ans • {piano.type}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Avertissements piano */}
        {piano?.warnings?.length > 0 && (
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

        {/* Dernière recommandation */}
        {lastRec && (
          <div className="bg-blue-50 border-l-4 border-blue-400 px-3 py-2">
            <div className="text-xs text-blue-600 font-medium mb-1">Dernière recommandation</div>
            <div className="text-sm text-blue-900">{lastRec}</div>
          </div>
        )}

        {/* Dampp-Chaser */}
        {piano?.dampp_chaser && (
          <div className="bg-cyan-50 border border-cyan-200 rounded px-3 py-2 text-sm text-cyan-800 flex items-center gap-2">
            <span>💧</span>
            <span>Dampp-Chaser installé - Vérifier niveau d'eau</span>
          </div>
        )}
      </div>

      {/* Footer - Bouton Allan */}
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
                placeholder="Ex: Le client parle anglais, il a un chien nommé Rex, stationnement à l'arrière..."
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
