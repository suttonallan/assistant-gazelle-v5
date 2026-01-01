import React from 'react'
import TechniciensInventaireTable from '../TechniciensInventaireTable'

/**
 * Dashboard pour Nick (Gestionnaire)
 *
 * SIMPLIFIÉ: Affiche SEULEMENT l'inventaire des techniciens.
 * La navigation est gérée par le bandeau supérieur dans App.jsx.
 *
 * Ancienne version avec onglets secondaires → SUPPRIMÉE
 * Nouveau comportement: Composant minimal sans navigation redondante
 */
const NickDashboard = ({ currentUser }) => {
  return (
    <div className="p-6">
      {/* Inventaire techniciens - Vue principale pour Nick */}
      <TechniciensInventaireTable
        currentUser={currentUser}
        allowComment={true}
      />
    </div>
  )
}

export default NickDashboard
