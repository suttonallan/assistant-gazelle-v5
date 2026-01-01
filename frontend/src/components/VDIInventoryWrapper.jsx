/**
 * VDIInventoryWrapper - Wrapper pour charger le Master Template V7
 *
 * Ce composant charge dynamiquement le VDIInventory de 527 lignes
 * depuis le module refactor/vdi via un iframe pour isolation complète.
 *
 * Isolation complète = pas de conflits CSS/JS avec V5
 */

import React from 'react'

export default function VDIInventoryWrapper() {
  // URL du serveur V7 (port dynamique, essaie 5175 puis 5174)
  const v7Url = 'http://localhost:5175'

  return (
    <div className="w-full h-screen bg-gray-50">
      <iframe
        src={v7Url}
        title="Vincent d'Indy - Gestion Pianos V7"
        className="w-full h-full border-0"
        style={{
          minHeight: 'calc(100vh - 60px)', // Hauteur totale moins le header V5
        }}
      />
    </div>
  )
}
