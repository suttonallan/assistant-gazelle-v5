/**
 * Configuration des rôles utilisateurs
 * Version simplifiée pour démarrage rapide (ce soir)
 */

export const ROLES = {
  admin: {
    name: 'Administrateur',
    email: 'asutton@piano-tek.com',
    permissions: ['*'], // Tout
    dashboards: ['inventaire', 'commissions', 'stats', 'admin', 'sync_gazelle', 'tournees'],
    technicianName: 'allan' // Allan est aussi technicien
  },

  nick: {
    name: 'Nick (Gestionnaire)',
    email: 'nlessard@piano-tek.com',
    permissions: [
      'view_inventory',
      'manage_own_inventory',
      'create_tours',
      'view_tours',
      'use_assistant' // Nick peut utiliser l'assistant
    ],
    dashboards: ['inventaire', 'tournees', 'vincent-dindy']
  },

  louise: {
    name: 'Louise (Assistante)',
    email: 'info@piano-tek.com',
    permissions: [
      'view_inventory',
      'edit_inventory', // Louise peut modifier les quantités
      'view_tours', // Louise peut voir les tournées
      'use_assistant' // Louise peut utiliser l'assistant
    ],
    dashboards: ['inventaire', 'tournees']
  },

  jeanphilippe: {
    name: 'Jean-Philippe (Technicien)',
    email: 'jpreny@gmail.com',
    permissions: [
      'view_inventory',
      'edit_inventory', // Peut modifier toutes les colonnes
      'view_tours', // Peut voir les tournées et les pianos à accorder
      'use_assistant' // Jean-Philippe peut utiliser l'assistant
    ],
    dashboards: ['inventaire', 'tournees']
  }
}

/**
 * Détecte le rôle selon l'email de l'utilisateur
 */
export function getUserRole(userEmail) {
  if (!userEmail) return 'admin' // Par défaut

  const email = userEmail.toLowerCase()

  // Chercher le rôle correspondant
  for (const [roleName, roleConfig] of Object.entries(ROLES)) {
    if (roleConfig.email.toLowerCase() === email) {
      return roleName
    }
  }

  return 'admin' // Par défaut si non trouvé
}

/**
 * Vérifie si l'utilisateur a une permission
 */
export function hasPermission(userEmail, permission) {
  const role = getUserRole(userEmail)
  const roleConfig = ROLES[role]

  if (!roleConfig) return false
  if (roleConfig.permissions.includes('*')) return true

  return roleConfig.permissions.includes(permission)
}

/**
 * Retourne les dashboards accessibles par l'utilisateur
 */
export function getAvailableDashboards(userEmail) {
  const role = getUserRole(userEmail)
  const roleConfig = ROLES[role]

  return roleConfig?.dashboards || ['inventaire']
}
