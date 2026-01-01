/**
 * LastTunedBadge Component
 *
 * Badge compact affichant le délai depuis dernier accord
 * Format VDV7: +Xs (X semaines)
 *
 * @example
 * ```tsx
 * <LastTunedBadge
 *   lastTuned={piano.lastTuned}
 *   showTooltip
 *   size="sm"
 * />
 * // Affiche: "+6s" avec tooltip "15 jan 2024 (il y a 42 jours)"
 * ```
 */

import React from 'react';
import { formatDelay, formatDelayWithTooltip } from '@lib/utils';
import { getLastTunedBadgeColor } from '@hooks/usePianoColors';

// ==========================================
// TYPES
// ==========================================

interface LastTunedBadgeProps {
  /** Date dernier accord */
  lastTuned: Date | string | null;

  /** Afficher tooltip avec détails */
  showTooltip?: boolean;

  /** Taille du badge */
  size?: 'xs' | 'sm' | 'md';

  /** Classe CSS additionnelle */
  className?: string;
}

// ==========================================
// COMPONENT
// ==========================================

export function LastTunedBadge({
  lastTuned,
  showTooltip = true,
  size = 'sm',
  className = ''
}: LastTunedBadgeProps) {
  // Format délai
  const { display, tooltip } = showTooltip
    ? formatDelayWithTooltip(lastTuned)
    : { display: formatDelay(lastTuned), tooltip: '' };

  // Get color basé sur âge
  const colorClass = getLastTunedBadgeColor(
    lastTuned ? (typeof lastTuned === 'string' ? new Date(lastTuned) : lastTuned) : null
  );

  // Size classes
  const sizeClasses = {
    xs: 'text-xs px-1 py-0.5',
    sm: 'text-sm px-1.5 py-0.5',
    md: 'text-base px-2 py-1'
  };

  return (
    <span
      className={`
        inline-flex items-center justify-center
        font-mono font-medium
        rounded
        ${sizeClasses[size]}
        ${colorClass}
        ${className}
      `}
      title={showTooltip ? tooltip : undefined}
    >
      {display}
    </span>
  );
}

export default LastTunedBadge;
