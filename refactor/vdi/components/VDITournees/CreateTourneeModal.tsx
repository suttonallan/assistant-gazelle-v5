/**
 * CreateTourneeModal - Modal de création d'une tournée
 *
 * Formulaire avec:
 * - Nom de la tournée
 * - Dates début/fin
 * - Technicien responsable
 * - Notes optionnelles
 */

import React, { useState } from 'react';
import type { Etablissement } from '@types/tournee.types';

interface CreateTourneeModalProps {
  etablissement: Etablissement;
  onClose: () => void;
  onCreate: (data: CreateTourneeData) => Promise<void>;
}

interface CreateTourneeFormData {
  nom: string;
  dateDebut: string;
  dateFin: string;
  technicienResponsable?: string;
  techniciensAssistants: string[];
  notes?: string;
}

export interface CreateTourneeData {
  nom: string;
  dateDebut: Date;
  dateFin: Date;
  etablissement: string;
  technicienResponsable?: string;
  techniciensAssistants?: string[];
  notes?: string;
}

export function CreateTourneeModal({ etablissement, onClose, onCreate }: CreateTourneeModalProps) {
  const [formData, setFormData] = useState<CreateTourneeFormData>({
    nom: '',
    dateDebut: getTodayString(),
    dateFin: getDateString(30), // +30 jours par défaut
    technicienResponsable: '',
    techniciensAssistants: [],
    notes: ''
  });

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    // Validation
    if (!formData.nom.trim()) {
      setError('Le nom de la tournée est requis');
      return;
    }

    if (new Date(formData.dateFin) <= new Date(formData.dateDebut)) {
      setError('La date de fin doit être après la date de début');
      return;
    }

    setLoading(true);

    try {
      // Convert form data (strings) to CreateTourneeData (Dates)
      const tourneeData: CreateTourneeData = {
        nom: formData.nom,
        dateDebut: new Date(formData.dateDebut),
        dateFin: new Date(formData.dateFin),
        etablissement,
        technicienResponsable: formData.technicienResponsable || undefined,
        techniciensAssistants: formData.techniciensAssistants.length > 0 ? formData.techniciensAssistants : undefined,
        notes: formData.notes || undefined
      };

      await onCreate(tourneeData);
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erreur lors de la création');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50 p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-md w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <h2 className="text-xl font-semibold text-gray-900">Nouvelle tournée</h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition-colors"
          >
            ✕
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {/* Nom */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Nom de la tournée *
            </label>
            <input
              type="text"
              value={formData.nom}
              onChange={(e) => setFormData({ ...formData, nom: e.target.value })}
              placeholder="Ex: Tournée Hiver 2025"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              autoFocus
            />
          </div>

          {/* Dates */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Date début *
              </label>
              <input
                type="date"
                value={formData.dateDebut}
                onChange={(e) => setFormData({ ...formData, dateDebut: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Date fin *
              </label>
              <input
                type="date"
                value={formData.dateFin}
                onChange={(e) => setFormData({ ...formData, dateFin: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
          </div>

          {/* Technicien */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Technicien responsable
            </label>
            <select
              value={formData.technicienResponsable}
              onChange={(e) =>
                setFormData({ ...formData, technicienResponsable: e.target.value })
              }
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="">-- Sélectionner --</option>
              <option value="allan@pianosmtl.com">Allan</option>
              <option value="nicolas@pianosmtl.com">Nicolas</option>
              <option value="nick@pianosmtl.com">Nick</option>
              <option value="michelle@pianosmtl.com">Michelle</option>
            </select>
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
                        setFormData({ ...formData, techniciensAssistants: newAssistants });
                      }}
                      disabled={loading}
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

          {/* Notes */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Notes (optionnel)
            </label>
            <textarea
              value={formData.notes}
              onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
              placeholder="Notes ou instructions pour cette tournée..."
              rows={3}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 resize-none"
            />
          </div>

          {/* Error */}
          {error && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-3 text-sm text-red-800">
              ❌ {error}
            </div>
          )}

          {/* Actions */}
          <div className="flex gap-3 pt-4">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 font-medium rounded-lg hover:bg-gray-50 transition-colors"
              disabled={loading}
            >
              Annuler
            </button>
            <button
              type="submit"
              className="flex-1 px-4 py-2 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              disabled={loading}
            >
              {loading ? 'Création...' : 'Créer la tournée'}
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

function getTodayString(): string {
  return new Date().toISOString().split('T')[0];
}

function getDateString(daysFromNow: number): string {
  const date = new Date();
  date.setDate(date.getDate() + daysFromNow);
  return date.toISOString().split('T')[0];
}
