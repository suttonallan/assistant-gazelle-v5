import { useState } from 'react'

import { API_URL } from '../../utils/apiConfig'

/**
 * Composant pour afficher/éditer un item de prévisualisation
 * Si confidence < 1.0, affiche un formulaire éditable
 * Sinon, affiche juste la prévisualisation en lecture seule
 */
export default function EditablePreviewItem({ item, index, rawText, currentUser, onCorrect }) {
  const [isEditing, setIsEditing] = useState(item.confidence < 1.0)
  const [editedFields, setEditedFields] = useState({
    appointment_date: item.appointment_date || '',
    room: item.room || '',
    for_who: item.for_who || '',
    diapason: item.diapason || '',
    piano: item.piano || '',
    time: item.time || '',
    requester: item.requester || ''
  })
  const [saving, setSaving] = useState(false)

  const handleFieldChange = (field, value) => {
    setEditedFields(prev => ({ ...prev, [field]: value }))
  }

  const handleSaveCorrection = async () => {
    setSaving(true)
    try {
      // Enregistrer la correction pour apprentissage
      await fetch(`${API_URL}/api/place-des-arts/learn`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          original_text: rawText,
          // Champs parsés
          parsed_date: item.appointment_date,
          parsed_room: item.room,
          parsed_for_who: item.for_who,
          parsed_diapason: item.diapason,
          parsed_piano: item.piano,
          parsed_time: item.time,
          parsed_requester: item.requester,
          parsed_confidence: item.confidence,
          // Champs corrigés
          corrected_date: editedFields.appointment_date,
          corrected_room: editedFields.room,
          corrected_for_who: editedFields.for_who,
          corrected_diapason: editedFields.diapason,
          corrected_piano: editedFields.piano,
          corrected_time: editedFields.time,
          corrected_requester: editedFields.requester,
          corrected_by: currentUser?.email || 'admin'
        })
      })

      setIsEditing(false)
      if (onCorrect) {
        onCorrect(index, editedFields)
      }
    } catch (err) {
      console.error('Erreur sauvegarde correction:', err)
      alert('Erreur lors de l\'enregistrement de la correction')
    } finally {
      setSaving(false)
    }
  }

  const confidenceColor = item.confidence >= 0.8
    ? 'text-green-600 bg-green-50'
    : item.confidence >= 0.6
      ? 'text-yellow-600 bg-yellow-50'
      : 'text-red-600 bg-red-50'

  const confidenceLabel = item.confidence >= 0.8
    ? '✓ Haute confiance'
    : item.confidence >= 0.6
      ? '⚠ Moyenne confiance'
      : '⚠ Faible confiance - Vérification requise'

  if (!isEditing) {
    // Mode lecture seule
    return (
      <div className="px-3 py-3 text-sm space-y-2 bg-white hover:bg-gray-50">
        <div className="flex items-center justify-between mb-2">
          <span className={`text-xs px-2 py-1 rounded ${confidenceColor}`}>
            {confidenceLabel} ({Math.round(item.confidence * 100)}%)
          </span>
          {item.confidence < 1.0 && (
            <button
              onClick={() => setIsEditing(true)}
              className="text-xs text-blue-600 hover:text-blue-800"
            >
              ✎ Modifier
            </button>
          )}
        </div>

        <div className="grid grid-cols-2 gap-2">
          <div>
            <span className="font-medium text-gray-600">Date RDV:</span>
            <span className="ml-2">{item.appointment_date || '—'}</span>
            {item.time && <span className="ml-2 text-gray-600">{item.time}</span>}
          </div>
          <div>
            <span className="font-medium text-gray-600">Salle:</span>
            <span className="ml-2">{item.room || '—'}</span>
          </div>
          <div>
            <span className="font-medium text-gray-600">Pour qui:</span>
            <span className="ml-2">{item.for_who || '—'}</span>
          </div>
          <div>
            <span className="font-medium text-gray-600">Diapason:</span>
            <span className="ml-2">{item.diapason || '—'}</span>
          </div>
          <div className="col-span-2">
            <span className="font-medium text-gray-600">Piano:</span>
            <span className="ml-2">{item.piano || '—'}</span>
          </div>
          <div>
            <span className="font-medium text-gray-600">Demandeur:</span>
            <span className="ml-2">{item.requester || '—'}</span>
          </div>
        </div>

        {item.warnings && item.warnings.length > 0 && (
          <div className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded px-2 py-1">
            Avertissements: {item.warnings.join(' | ')}
          </div>
        )}
        {item.duplicate_of && item.duplicate_of.length > 0 && (
          <div className="text-xs text-red-700 bg-red-50 border border-red-200 rounded px-2 py-1">
            Doublon potentiel : {item.duplicate_of.join(', ')}
          </div>
        )}
      </div>
    )
  }

  // Mode édition
  return (
    <div className="px-3 py-3 text-sm space-y-3 bg-blue-50 border-l-4 border-blue-400">
      <div className="flex items-center justify-between mb-2">
        <span className={`text-xs px-2 py-1 rounded ${confidenceColor}`}>
          {confidenceLabel} ({Math.round(item.confidence * 100)}%) - Mode édition
        </span>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-xs font-medium text-gray-700 mb-1">Date RDV</label>
          <input
            type="date"
            value={editedFields.appointment_date}
            onChange={(e) => handleFieldChange('appointment_date', e.target.value)}
            className="w-full px-2 py-1 text-sm border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          />
        </div>

        <div>
          <label className="block text-xs font-medium text-gray-700 mb-1">Heure</label>
          <input
            type="text"
            value={editedFields.time}
            onChange={(e) => handleFieldChange('time', e.target.value)}
            placeholder="Ex: 13h00"
            className="w-full px-2 py-1 text-sm border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          />
        </div>

        <div>
          <label className="block text-xs font-medium text-gray-700 mb-1">Salle</label>
          <select
            value={editedFields.room}
            onChange={(e) => handleFieldChange('room', e.target.value)}
            className="w-full px-2 py-1 text-sm border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          >
            <option value="">-- Sélectionner --</option>
            <option value="WP">WP - Wilfrid-Pelletier</option>
            <option value="TM">TM - Théâtre Maisonneuve</option>
            <option value="MS">MS - Salle MS</option>
            <option value="SD">SD - Salle D</option>
            <option value="C5">C5 - Cinquième Salle</option>
            <option value="SCL">SCL - Studio Claude-Léveillée</option>
            <option value="ODM">ODM - Opera de Montreal</option>
          </select>
        </div>

        <div>
          <label className="block text-xs font-medium text-gray-700 mb-1">Diapason</label>
          <input
            type="text"
            value={editedFields.diapason}
            onChange={(e) => handleFieldChange('diapason', e.target.value)}
            placeholder="Ex: 440"
            className="w-full px-2 py-1 text-sm border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          />
        </div>

        <div>
          <label className="block text-xs font-medium text-gray-700 mb-1">Pour qui (artiste/événement)</label>
          <input
            type="text"
            value={editedFields.for_who}
            onChange={(e) => handleFieldChange('for_who', e.target.value)}
            placeholder="Ex: Clémence"
            className="w-full px-2 py-1 text-sm border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          />
        </div>

        <div>
          <label className="block text-xs font-medium text-gray-700 mb-1">Demandeur</label>
          <input
            type="text"
            value={editedFields.requester}
            onChange={(e) => handleFieldChange('requester', e.target.value)}
            placeholder="Ex: Isabelle"
            className="w-full px-2 py-1 text-sm border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          />
        </div>

        <div className="col-span-2">
          <label className="block text-xs font-medium text-gray-700 mb-1">Piano</label>
          <input
            type="text"
            value={editedFields.piano}
            onChange={(e) => handleFieldChange('piano', e.target.value)}
            placeholder="Ex: Piano Baldwin (9')"
            className="w-full px-2 py-1 text-sm border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          />
        </div>
      </div>

      <div className="flex gap-2 pt-2 border-t border-blue-200">
        <button
          onClick={handleSaveCorrection}
          disabled={saving}
          className="px-3 py-1.5 text-sm bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50"
        >
          {saving ? 'Enregistrement...' : '✓ Valider et apprendre'}
        </button>
        <button
          onClick={() => setIsEditing(false)}
          disabled={saving}
          className="px-3 py-1.5 text-sm bg-gray-100 text-gray-700 rounded hover:bg-gray-200 disabled:opacity-50"
        >
          Annuler
        </button>
      </div>

      {item.warnings && item.warnings.length > 0 && (
        <div className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded px-2 py-1">
          Avertissements: {item.warnings.join(' | ')}
        </div>
      )}
    </div>
  )
}
