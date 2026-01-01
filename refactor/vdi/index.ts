/**
 * VDI - Exports Centralisés
 *
 * Point d'entrée unique pour utilisation externe
 *
 * @example
 * ```tsx
 * import { usePianos, useTournees, PianosTable } from '@/refactor/vdi';
 * ```
 */

// ==========================================
// TYPES
// ==========================================

export * from './types/piano.types';
export * from './types/tournee.types';
export * from './types/institution.types';
export * from './types/supabase.types';

// ==========================================
// CONFIGURATION
// ==========================================

export {
  getInstitutionConfig,
  hasFeature,
  getColorRules,
  isAdmin,
  isTechnician,
  getUserRole,
  listInstitutions,
  INSTITUTION_REGISTRY
} from './config/institutions';

// ==========================================
// LIB / UTILITIES
// ==========================================

export {
  supabase,
  subscribeToPianos,
  subscribeToTournees,
  subscribeToTournee,
  isConnected,
  getCurrentUserEmail,
  formatSupabaseError,
  withRetry,
  batchUpsert,
  enableRealtimeDebug,
  logRealtimeStatus
} from './lib/supabase.client';

export {
  formatDate,
  formatDateShort,
  formatDateForInput,
  formatDelay,
  formatDelayWithTooltip,
  formatRelativeTime,
  parseDate,
  isFuture,
  isPast,
  generateTourneeId,
  generateUniqueId,
  isValidTourneeId,
  truncate,
  capitalize,
  toSnakeCase,
  toCamelCase,
  keysToSnakeCase,
  keysToCamelCase,
  unique,
  groupBy,
  sortBy,
  chunk,
  clamp,
  formatNumber,
  percentage,
  deepClone,
  isEmpty,
  pick,
  omit,
  isEmail,
  isNonEmpty,
  sanitizeHtml,
  debounce,
  throttle,
  cn
} from './lib/utils';

export * from './lib/validators';

// ==========================================
// HOOKS
// ==========================================

export { usePianos } from './hooks/usePianos';
export { useTournees } from './hooks/useTournees';
export {
  usePianoColors,
  getLastTunedBadgeColor,
  getPianoStatusIcon,
  getColorDescription
} from './hooks/usePianoColors';
export { useRangeSelection, getSelectAllState } from './hooks/useRangeSelection';
export { useBatchOperations } from './hooks/useBatchOperations';

// ==========================================
// COMPONENTS - SHARED
// ==========================================

export { LastTunedBadge } from './components/shared/LastTunedBadge';
export { PianoStatusPill } from './components/shared/PianoStatusPill';

// ==========================================
// COMPONENTS - INVENTORY
// ==========================================

export { VDIInventory } from './components/VDIInventory';
export { InventoryTable } from './components/VDIInventory/InventoryTable';

// ==========================================
// COMPONENTS - TOURNEES DASHBOARD
// ==========================================

export { PianosTable } from './components/VDITournees/PianosTable';
export { BatchToolbar } from './components/VDITournees/BatchToolbar';

// Note: TourneesSidebar sera exporté quand implémenté
