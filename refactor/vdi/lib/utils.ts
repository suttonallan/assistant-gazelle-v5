/**
 * Utility Functions
 *
 * Helpers réutilisables pour:
 * - Date formatting
 * - ID generation
 * - String manipulation
 * - Array operations
 */

import { format, formatDistanceToNow, differenceInDays, differenceInWeeks } from 'date-fns';
import { fr } from 'date-fns/locale';

// ==========================================
// DATE UTILITIES
// ==========================================

/**
 * Format date pour affichage (format français)
 *
 * @example
 * formatDate(new Date('2025-01-15')) // "15 janvier 2025"
 */
export function formatDate(date: Date | string | null): string {
  if (!date) return 'N/A';

  const d = typeof date === 'string' ? new Date(date) : date;
  if (isNaN(d.getTime())) return 'Date invalide';

  return format(d, 'dd MMMM yyyy', { locale: fr });
}

/**
 * Format date courte (pour UI compacte)
 *
 * @example
 * formatDateShort(new Date('2025-01-15')) // "15 jan 2025"
 */
export function formatDateShort(date: Date | string | null): string {
  if (!date) return 'N/A';

  const d = typeof date === 'string' ? new Date(date) : date;
  if (isNaN(d.getTime())) return 'N/A';

  return format(d, 'dd MMM yyyy', { locale: fr });
}

/**
 * Format date pour input type="date" (YYYY-MM-DD)
 *
 * @example
 * formatDateForInput(new Date()) // "2025-01-15"
 */
export function formatDateForInput(date: Date | string | null): string {
  if (!date) return '';

  const d = typeof date === 'string' ? new Date(date) : date;
  if (isNaN(d.getTime())) return '';

  return format(d, 'yyyy-MM-dd');
}

/**
 * Format délai depuis dernière action (compact)
 *
 * Format VDV7: Xs (X semaines)
 *
 * @example
 * formatDelay(new Date('2024-11-15')) // "6s" (6 semaines ago)
 * formatDelay(new Date()) // "0s"
 */
export function formatDelay(date: Date | string | null): string {
  if (!date) return 'N/A';

  const d = typeof date === 'string' ? new Date(date) : date;
  if (isNaN(d.getTime())) return 'N/A';

  const weeks = differenceInWeeks(new Date(), d);

  return `${weeks}s`;
}

/**
 * Format délai avec tooltip (pour affichage riche)
 *
 * @returns { display: string, tooltip: string }
 *
 * @example
 * const { display, tooltip } = formatDelayWithTooltip(lastTuned);
 * <span title={tooltip}>{display}</span>
 */
export function formatDelayWithTooltip(date: Date | string | null): {
  display: string;
  tooltip: string;
} {
  if (!date) {
    return { display: 'N/A', tooltip: 'Pas de date enregistrée' };
  }

  const d = typeof date === 'string' ? new Date(date) : date;
  if (isNaN(d.getTime())) {
    return { display: 'N/A', tooltip: 'Date invalide' };
  }

  const weeks = differenceInWeeks(new Date(), d);
  const days = differenceInDays(new Date(), d);

  return {
    display: `${weeks}s`,
    tooltip: `${formatDateShort(d)} (il y a ${days} jours)`
  };
}

/**
 * Format distance relative (humaine)
 *
 * @example
 * formatRelativeTime(new Date('2025-01-10')) // "il y a 5 jours"
 */
export function formatRelativeTime(date: Date | string | null): string {
  if (!date) return 'N/A';

  const d = typeof date === 'string' ? new Date(date) : date;
  if (isNaN(d.getTime())) return 'N/A';

  return formatDistanceToNow(d, { locale: fr, addSuffix: true });
}

/**
 * Parse date ISO string → Date object (safe)
 */
export function parseDate(dateStr: string | null): Date | null {
  if (!dateStr) return null;

  try {
    const date = new Date(dateStr);
    return isNaN(date.getTime()) ? null : date;
  } catch {
    return null;
  }
}

/**
 * Check si date est dans le futur
 */
export function isFuture(date: Date | string): boolean {
  const d = typeof date === 'string' ? new Date(date) : date;
  return d > new Date();
}

/**
 * Check si date est dans le passé
 */
export function isPast(date: Date | string): boolean {
  const d = typeof date === 'string' ? new Date(date) : date;
  return d < new Date();
}

// ==========================================
// ID GENERATION
// ==========================================

/**
 * Générer ID tournée (format: tournee_{timestamp})
 *
 * @example
 * generateTourneeId() // "tournee_1704447600000"
 */
export function generateTourneeId(): string {
  return `tournee_${Date.now()}`;
}

/**
 * Générer ID unique (UUID simple sans dépendance)
 */
export function generateUniqueId(): string {
  return `${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;
}

/**
 * Valider format ID tournée
 */
export function isValidTourneeId(id: string): boolean {
  return /^tournee_\d+$/.test(id);
}

// ==========================================
// STRING UTILITIES
// ==========================================

/**
 * Truncate texte avec ellipsis
 *
 * @example
 * truncate("Long text here", 10) // "Long text..."
 */
export function truncate(text: string, maxLength: number): string {
  if (text.length <= maxLength) return text;
  return `${text.slice(0, maxLength)}...`;
}

/**
 * Capitalize première lettre
 *
 * @example
 * capitalize("hello") // "Hello"
 */
export function capitalize(text: string): string {
  if (!text) return '';
  return text.charAt(0).toUpperCase() + text.slice(1).toLowerCase();
}

/**
 * Convert camelCase → snake_case (pour API Python)
 *
 * @example
 * toSnakeCase("aFaire") // "a_faire"
 */
export function toSnakeCase(str: string): string {
  return str.replace(/[A-Z]/g, (letter) => `_${letter.toLowerCase()}`);
}

/**
 * Convert snake_case → camelCase (depuis API Python)
 *
 * @example
 * toCamelCase("a_faire") // "aFaire"
 */
export function toCamelCase(str: string): string {
  return str.replace(/_([a-z])/g, (_, letter) => letter.toUpperCase());
}

/**
 * Convert object keys camelCase → snake_case
 */
export function keysToSnakeCase<T extends Record<string, unknown>>(
  obj: T
): Record<string, unknown> {
  return Object.fromEntries(
    Object.entries(obj).map(([key, value]) => [toSnakeCase(key), value])
  );
}

/**
 * Convert object keys snake_case → camelCase
 */
export function keysToCamelCase<T extends Record<string, unknown>>(
  obj: T
): Record<string, unknown> {
  return Object.fromEntries(
    Object.entries(obj).map(([key, value]) => [toCamelCase(key), value])
  );
}

// ==========================================
// ARRAY UTILITIES
// ==========================================

/**
 * Remove duplicates from array
 */
export function unique<T>(array: T[]): T[] {
  return [...new Set(array)];
}

/**
 * Group array by key
 *
 * @example
 * groupBy(pianos, 'location')
 * // { "Studio A": [...], "Studio B": [...] }
 */
export function groupBy<T>(array: T[], key: keyof T): Record<string, T[]> {
  return array.reduce(
    (groups, item) => {
      const groupKey = String(item[key]);
      return {
        ...groups,
        [groupKey]: [...(groups[groupKey] || []), item]
      };
    },
    {} as Record<string, T[]>
  );
}

/**
 * Sort array by key (immutable)
 */
export function sortBy<T>(
  array: T[],
  key: keyof T,
  order: 'asc' | 'desc' = 'asc'
): T[] {
  return [...array].sort((a, b) => {
    const aVal = a[key];
    const bVal = b[key];

    if (aVal === bVal) return 0;

    const comparison = aVal < bVal ? -1 : 1;
    return order === 'asc' ? comparison : -comparison;
  });
}

/**
 * Chunk array into smaller arrays
 *
 * @example
 * chunk([1,2,3,4,5], 2) // [[1,2], [3,4], [5]]
 */
export function chunk<T>(array: T[], size: number): T[][] {
  const chunks: T[][] = [];
  for (let i = 0; i < array.length; i += size) {
    chunks.push(array.slice(i, i + size));
  }
  return chunks;
}

// ==========================================
// NUMBER UTILITIES
// ==========================================

/**
 * Clamp number between min and max
 */
export function clamp(value: number, min: number, max: number): number {
  return Math.min(Math.max(value, min), max);
}

/**
 * Format number avec séparateurs milliers
 *
 * @example
 * formatNumber(1234567) // "1 234 567"
 */
export function formatNumber(num: number): string {
  return num.toLocaleString('fr-FR');
}

/**
 * Calculate percentage
 *
 * @example
 * percentage(30, 100) // 30
 * percentage(1, 3) // 33.33
 */
export function percentage(value: number, total: number, decimals = 2): number {
  if (total === 0) return 0;
  return Number(((value / total) * 100).toFixed(decimals));
}

// ==========================================
// OBJECT UTILITIES
// ==========================================

/**
 * Deep clone object (simple, pas de fonctions)
 */
export function deepClone<T>(obj: T): T {
  return JSON.parse(JSON.stringify(obj));
}

/**
 * Check si object vide
 */
export function isEmpty(obj: Record<string, unknown>): boolean {
  return Object.keys(obj).length === 0;
}

/**
 * Pick keys from object
 *
 * @example
 * pick({ a: 1, b: 2, c: 3 }, ['a', 'c']) // { a: 1, c: 3 }
 */
export function pick<T extends Record<string, unknown>, K extends keyof T>(
  obj: T,
  keys: K[]
): Pick<T, K> {
  return keys.reduce(
    (result, key) => {
      if (key in obj) {
        result[key] = obj[key];
      }
      return result;
    },
    {} as Pick<T, K>
  );
}

/**
 * Omit keys from object
 *
 * @example
 * omit({ a: 1, b: 2, c: 3 }, ['b']) // { a: 1, c: 3 }
 */
export function omit<T extends Record<string, unknown>, K extends keyof T>(
  obj: T,
  keys: K[]
): Omit<T, K> {
  const result = { ...obj };
  keys.forEach((key) => delete result[key]);
  return result as Omit<T, K>;
}

// ==========================================
// VALIDATION UTILITIES
// ==========================================

/**
 * Check si string est email valide (simple)
 */
export function isEmail(str: string): boolean {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(str);
}

/**
 * Check si string non vide (après trim)
 */
export function isNonEmpty(str: string | null | undefined): boolean {
  return Boolean(str && str.trim().length > 0);
}

/**
 * Sanitize HTML (prévention XSS basique)
 */
export function sanitizeHtml(html: string): string {
  const div = document.createElement('div');
  div.textContent = html;
  return div.innerHTML;
}

// ==========================================
// DEBOUNCE & THROTTLE
// ==========================================

/**
 * Debounce function (pour search inputs)
 *
 * @example
 * const debouncedSearch = debounce((query) => search(query), 300);
 */
export function debounce<T extends (...args: unknown[]) => unknown>(
  fn: T,
  delayMs: number
): (...args: Parameters<T>) => void {
  let timeoutId: ReturnType<typeof setTimeout>;

  return (...args: Parameters<T>) => {
    clearTimeout(timeoutId);
    timeoutId = setTimeout(() => fn(...args), delayMs);
  };
}

/**
 * Throttle function (pour scroll handlers)
 */
export function throttle<T extends (...args: unknown[]) => unknown>(
  fn: T,
  delayMs: number
): (...args: Parameters<T>) => void {
  let lastCall = 0;

  return (...args: Parameters<T>) => {
    const now = Date.now();
    if (now - lastCall >= delayMs) {
      lastCall = now;
      fn(...args);
    }
  };
}

// ==========================================
// CLASS NAME UTILITIES
// ==========================================

/**
 * Conditional className builder (minimal clsx alternative)
 *
 * @example
 * cn('base', isActive && 'active', { 'disabled': !enabled })
 * // "base active" si isActive=true, enabled=true
 */
export function cn(
  ...inputs: Array<string | boolean | undefined | null | Record<string, boolean>>
): string {
  return inputs
    .flat()
    .filter(Boolean)
    .map((input) => {
      if (typeof input === 'string') return input;
      if (typeof input === 'object') {
        return Object.entries(input)
          .filter(([, value]) => value)
          .map(([key]) => key)
          .join(' ');
      }
      return '';
    })
    .join(' ')
    .trim();
}
