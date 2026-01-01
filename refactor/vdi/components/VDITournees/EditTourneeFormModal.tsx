/**
 * EditTourneeFormModal - Modal d'édition d'une tournée existante
 *
 * Permet de modifier:
 * - Nom de la tournée
 * - Dates (début, fin)
 * - Technicien responsable
 * - Notes
 * - Statut
 */

import React, { useState } from 'react';
import type { Tournee, TourneeStatus } from '@types/tournee.types';

// ==========================================
// TYPES
// ==========================================

interface EditTourneeFormModalProps {
  tournee: Tournee;
  onClose: () => void;
  onSave: (tourneeId: string, updates: Partial<TourneeUpdateData>) => Promise<void>;
}

export interface TourneeUpdateData {
  nom?: string;
  dateDebut?: Date;
  dateFin?: Date;
  technicienResponsable?: string | null;
  techniciensAssistants?: string[];
  notes?: string | null;
  status?: TourneeStatus;
}

interface TourneeFormData {
  nom: string;
  dateDebut: string;
  dateFin: string;
  technicienResponsable: string;
  techniciensAssistants: string[];
  notes: string;
  status: TourneeStatus;
}

// ==========================================
// COMPONENT
// ==========================================

export function EditTourneeFormModal({ tournee, onClose, onSave }: EditTourneeFormModalProps) {
  // Form state - initialiser avec données existantes
  const [formData, setFormData] = useState<TourneeFormData>({
    nom: tournee.nom,
    dateDebut: formatDateForInput(tournee.dateDebut),
    dateFin: formatDateForInput(tournee.dateFin),
    technicienResponsable: tournee.technicienResponsable || '',
    techniciensAssistants: tournee.techniciensAssistants || [],
    notes: tournee.notes || '',
    status: tournee.status
  });

  const [errors, setErrors] = useState<Partial<Record<keyof TourneeFormData, string>>>({});
  const [saving, setSaving] = useState(false);

  // ==========================================
  // VALIDATION
  // ==========================================

  const validate = (): boolean => {
    const newErrors: Partial<Record<keyof TourneeFormData, string>> = {};

    if (!formData.nom.trim()) {
      newErrors.nom = 'Le nom est requis';
    }

    if (!formData.dateDebut) {
      newErrors.dateDebut = 'La date de début est requise';
    }

    if (!formData.dateFin) {
      newErrors.dateFin = 'La date de fin est requise';
    }

    if (formData.dateDebut && formData.dateFin) {
      const debut = new Date(formData.dateDebut);
      const fin = new Date(formData.dateFin);

      if (fin < debut) {
        newErrors.dateFin = 'La date de fin doit être après la date de début';
      }
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  // ==========================================
  // HANDLERS
  // ==========================================

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!validate()) return;

    setSaving(true);

    try {
      // Construire objet updates avec seulement les champs modifiés
      const updates: TourneeUpdateData = {};

      if (formData.nom !== tournee.nom) {
        updates.nom = formData.nom.trim();
      }

      const newDateDebut = new Date(formData.dateDebut);
      if (newDateDebut.getTime() !== tournee.dateDebut.getTime()) {
        updates.dateDebut = newDateDebut;
      }

      const newDateFin = new Date(formData.dateFin);
      if (newDateFin.getTime() !== tournee.dateFin.getTime()) {
        updates.dateFin = newDateFin;
      }

      if (formData.technicienResponsable !== (tournee.technicienResponsable || '')) {
        updates.technicienResponsable = formData.technicienResponsable.trim() || null;
      }

      // Vérifier si assistants ont changé
      const currentAssistants = tournee.techniciensAssistants || [];
      const newAssistants = formData.techniciensAssistants;
      const assistantsChanged =
        currentAssistants.length !== newAssistants.length ||
        !currentAssistants.every((a) => newAssistants.includes(a));

      if (assistantsChanged) {
        updates.techniciensAssistants = newAssistants;
      }

      if (formData.notes !== (tournee.notes || '')) {
        updates.notes = formData.notes.trim() || null;
      }

      if (formData.status !== tournee.status) {
        updates.status = formData.status;
      }

      // Si aucun changement
      if (Object.keys(updates).length === 0) {
        alert('ℹ️ Aucune modification détectée');
        onClose();
        return;
      }

      await onSave(tournee.id, updates);

      alert(`✅ Tournée "${formData.nom}" mise à jour`);
      onClose();
    } catch (err) {
      console.error('Error saving tournee:', err);
      alert(`❌ Erreur: ${err}`);
    } finally {
      setSaving(false);
    }
  };

  const handleChange = (field: keyof TourneeFormData, value: string | TourneeStatus) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
    // Clear error for this field
    if (errors[field]) {
      setErrors((prev) => {
        const newErrors = { ...prev };
        delete newErrors[field];
        return newErrors;
      });
    }
  };

  // ==========================================
  // RENDER
  // ==========================================

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <div className="bg-white rounded-xl shadow-2xl max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="sticky top-0 bg-white border-b border-gray-200 px-6 py-4 rounded-t-xl">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-bold text-gray-900">
              ✏️ Éditer la tournée
            </h2>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600 transition-colors"
            >
              <span className="text-2xl">×</span>
            </button>
          </div>
          <p className="text-sm text-gray-500 mt-1">
            Modifiez les informations de la tournée "{tournee.nom}"
          </p>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="p-6 space-y-6">
          {/* Nom */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Nom de la tournée *
            </label>
            <input
              type="text"
              value={formData.nom}
              onChange={(e) => handleChange('nom', e.target.value)}
              className={`
                w-full px-4 py-2 border rounded-lg
                focus:ring-2 focus:ring-blue-500 focus:border-blue-500
                ${errors.nom ? 'border-red-500' : 'border-gray-300'}
              `}
              placeholder="Ex: Tournée Hiver 2025"
              disabled={saving}
            />
            {errors.nom && (
              <p className="mt-1 text-sm text-red-600">{errors.nom}</p>
            )}
          </div>

          {/* Dates */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Date de début *
              </label>
              <input
                type="date"
                value={formData.dateDebut}
                onChange={(e) => handleChange('dateDebut', e.target.value)}
                className={`
                  w-full px-4 py-2 border rounded-lg
                  focus:ring-2 focus:ring-blue-500 focus:border-blue-500
                  ${errors.dateDebut ? 'border-red-500' : 'border-gray-300'}
                `}
                disabled={saving}
              />
              {errors.dateDebut && (
                <p className="mt-1 text-sm text-red-600">{errors.dateDebut}</p>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Date de fin *
              </label>
              <input
                type="date"
                value={formData.dateFin}
                onChange={(e) => handleChange('dateFin', e.target.value)}
                className={`
                  w-full px-4 py-2 border rounded-lg
                  focus:ring-2 focus:ring-blue-500 focus:border-blue-500
                  ${errors.dateFin ? 'border-red-500' : 'border-gray-300'}
                `}
                disabled={saving}
              />
              {errors.dateFin && (
                <p className="mt-1 text-sm text-red-600">{errors.dateFin}</p>
              )}
            </div>
          </div>

          {/* Technicien */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Technicien responsable
            </label>
            <select
              value={formData.technicienResponsable}
              onChange={(e) => handleChange('technicienResponsable', e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              disabled={saving}
            >
              <option value="">Aucun technicien assigné</option>
              <option value="allan@pianosmtl.com">Allan</option>
              <option value="nicolas@pianosmtl.com">Nicolas</option>
              <option value="nick@pianosmtl.com">Nick</option>
              <option value="michelle@pianosmtl.com">Michelle</option>

              {/* Afficher ancienne valeur si elle n'est pas dans la liste */}
              {formData.technicienResponsable &&
               !['', 'allan@pianosmtl.com', 'nicolas@pianosmtl.com', 'nick@pianosmtl.com', 'michelle@pianosmtl.com'].includes(formData.technicienResponsable) && (
                <option value={formData.technicienResponsable}>
                  {formData.technicienResponsable} (ancien)
                </option>
              )}
            </select>
            {formData.technicienResponsable &&
             !['', 'allan@pianosmtl.com', 'nicolas@pianosmtl.com', 'nick@pianosmtl.com', 'michelle@pianosmtl.com'].includes(formData.technicienResponsable) && (
              <p className="mt-1 text-xs text-amber-600">
                ⚠️ Cet email ne correspond pas aux techniciens actuels. Sélectionnez un nouveau technicien pour mettre à jour.
              </p>
            )}
          </div>

          {/* Techniciens Assistants */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Techniciens assistants (optionnel)
            </label>
            <div className="space-y-2">
              {['allan@pianosmtl.com', 'nicolas@pianosmtl.com', 'nick@pianosmtl.com', 'michelle@pianosmtl.com'].map((email) => {
                const name = email.split('@')[0];
                const displayName = name.charAt(0).toUpperCase() + name.slice(1);
                const isChecked = formData.techniciensAssistants.includes(email);

                return (
                  <label
                    key={email}
                    className="flex items-center gap-2 p-2 rounded hover:bg-gray-50 cursor-pointer"
                  >
                    <input
                      type="checkbox"
                      checked={isChecked}
                      onChange={(e) => {
                        const newAssistants = e.target.checked
                          ? [...formData.techniciensAssistants, email]
                          : formData.techniciensAssistants.filter((a) => a !== email);
                        handleChange('techniciensAssistants', newAssistants as any);
                      }}
                      disabled={saving}
                      className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                    />
                    <span className="text-sm text-gray-700">{displayName}</span>
                  </label>
                );
              })}
            </div>
            {formData.techniciensAssistants.length > 0 && (
              <p className="mt-2 text-xs text-gray-500">
                {formData.techniciensAssistants.length} assistant(s) sélectionné(s)
              </p>
            )}
          </div>

          {/* Statut */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Statut
            </label>
            <select
              value={formData.status}
              onChange={(e) => handleChange('status', e.target.value as TourneeStatus)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              disabled={saving}
            >
              <option value="planifiee">📅 Planifiée</option>
              <option value="en_cours">✓ Active</option>
              <option value="terminee">✅ Terminée</option>
              <option value="archivee">📦 Archivée</option>
            </select>
            <p className="mt-1 text-xs text-gray-500">
              Note: Une seule tournée peut être "Active" à la fois
            </p>
          </div>

          {/* Notes */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Notes
            </label>
            <textarea
              value={formData.notes}
              onChange={(e) => handleChange('notes', e.target.value)}
              rows={4}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              placeholder="Notes additionnelles..."
              disabled={saving}
            />
          </div>

          {/* Info Box */}
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <div className="flex items-start gap-3">
              <span className="text-blue-600 text-lg">ℹ️</span>
              <div className="text-sm text-blue-800">
                <p className="font-medium mb-1">Informations:</p>
                <ul className="space-y-1 text-xs">
                  <li>• {tournee.pianoIds.length} piano(s) dans cette tournée</li>
                  <li>• {tournee.topPianoIds.size} piano(s) marqué(s) comme Top</li>
                  <li>• Créée le {formatDateFull(tournee.createdAt)} par {tournee.createdBy}</li>
                  <li>• Dernière modification: {formatDateFull(tournee.updatedAt)}</li>
                </ul>
              </div>
            </div>
          </div>

          {/* Actions */}
          <div className="flex gap-3 pt-4 border-t border-gray-200">
            <button
              type="button"
              onClick={onClose}
              disabled={saving}
              className="
                flex-1 px-4 py-2 border border-gray-300 rounded-lg
                text-gray-700 font-medium
                hover:bg-gray-50 transition-colors
                disabled:opacity-50 disabled:cursor-not-allowed
              "
            >
              Annuler
            </button>
            <button
              type="submit"
              disabled={saving}
              className="
                flex-1 px-4 py-2 bg-blue-600 rounded-lg
                text-white font-medium
                hover:bg-blue-700 transition-colors
                disabled:opacity-50 disabled:cursor-not-allowed
                flex items-center justify-center gap-2
              "
            >
              {saving ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent" />
                  Enregistrement...
                </>
              ) : (
                <>
                  💾 Enregistrer les modifications
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ==========================================
// HELPERS
// ==========================================

/**
 * Format Date pour input[type="date"] (YYYY-MM-DD)
 */
function formatDateForInput(date: Date): string {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

/**
 * Format Date complet (affichage)
 */
function formatDateFull(date: Date): string {
  return new Intl.DateTimeFormat('fr-CA', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  }).format(date);
}

export default EditTourneeFormModal;
