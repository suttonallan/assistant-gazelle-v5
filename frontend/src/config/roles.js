/**
 * Configuration des rôles utilisateurs
 * Version simplifiée pour démarrage rapide (ce soir)
 */

export const ROLES = {
  admin: {
    name: 'Administrateur',
    email: 'asutton@piano-tek.com',
    gazelleId: 'usr_ofYggsCDt2JAVeNP', // Allan Sutton dans Gazelle
    permissions: ['*'], // Tout
    dashboards: ['inventaire', 'commissions', 'stats', 'admin', 'sync_gazelle', 'tournees'],
    technicianName: 'allan' // Allan est aussi technicien
  },

  nick: {
    name: 'Nick (Gestionnaire)',
    email: 'nlessard@piano-tek.com',
    gazelleId: 'usr_HcCiFk7o0vZ9xAI0', // Nicolas Lessard dans Gazelle
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
    gazelleId: 'usr_tndhXmnT0iakT4HF', // Louise Paradis dans Gazelle
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
    gazelleId: 'usr_ReUSmIJmBF86ilY1', // Jean-Philippe Reny dans Gazelle
    permissions: [
      'view_inventory',
      'edit_inventory', // Peut modifier toutes les colonnes
      'view_tours', // Peut voir les tournées et les pianos à accorder
      'use_assistant' // Jean-Philippe peut utiliser l'assistant
    ],
    dashboards: ['inventaire', 'tournees']
  },

  margot: {
    name: 'Margot (Assistante)',
    email: 'margotcharignon@gmail.com',
    gazelleId: 'usr_bbt59aCUqUaDWA8n', // Margot Charignon dans Gazelle
    permissions: [
      'view_inventory',
      'edit_inventory', // Peut modifier les quantités
      'view_tours', // Peut voir les tournées
      'use_assistant' // Margot peut utiliser l'assistant
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

/**
 * Retourne les permissions détaillées pour l'utilisateur
 * Permet de gérer l'affichage conditionnel des boutons Admin, etc.
 *
 * IMPORTANT pour l'impersonation:
 * - Si l'utilisateur RÉEL est Allan (admin), il garde toujours accès au sélecteur de rôle
 * - Le rôle simulé (currentUser.role) affecte uniquement les permissions d'interface
 *
 * @param {Object} currentUser - Objet utilisateur avec { email, role? }
 * @returns {Object} Permissions détaillées: { canAccessAdmin, canEditAll, role, isRealAdmin, ... }
 */
export function getUserPermissions(currentUser) {
  if (!currentUser) {
    return {
      canAccessAdmin: false,
      canEditAll: false,
      canViewAll: false,
      role: null,
      isRealAdmin: false
    }
  }

  // Déterminer le rôle réel (basé sur email) vs rôle simulé
  const realRole = getUserRole(currentUser.email)
  const effectiveRole = currentUser.role || realRole
  const roleConfig = ROLES[effectiveRole]

  // Permissions générales basées sur le rôle EFFECTIF (simulé ou réel)
  const hasWildcard = roleConfig?.permissions?.includes('*')

  return {
    role: effectiveRole,
    realRole,
    isRealAdmin: realRole === 'admin', // ⭐ Toujours vrai pour Allan, même s'il impersonne Louise
    canAccessAdmin: hasWildcard || effectiveRole === 'admin',
    canEditAll: hasWildcard || roleConfig?.permissions?.includes('edit_inventory'),
    canViewAll: hasWildcard || roleConfig?.permissions?.includes('view_inventory'),
    canManageTours: hasWildcard || roleConfig?.permissions?.includes('create_tours') || roleConfig?.permissions?.includes('view_tours'),
    canUseAssistant: hasWildcard || roleConfig?.permissions?.includes('use_assistant'),
    permissions: roleConfig?.permissions || []
  }
}
