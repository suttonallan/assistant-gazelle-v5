/**
 * PianoStatusPill Component
 *
 * Badge affichant le statut d'un piano avec icône
 *
 * @example
 * ```tsx
 * <PianoStatusPill status="top" />
 * // Affiche: "⭐ Top"
 * ```
 */

import React from 'react';
import { PianoStatus } from '@types/piano.types';
import { getPianoStatusIcon } from '@hooks/usePianoColors';

// ==========================================
// TYPES
// ==========================================

interface PianoStatusPillProps {
  /** Statut du piano */
  status: PianoStatus;

  /** Afficher icône */
  showIcon?: boolean;

  /** Taille */
  size?: 'sm' | 'md' | 'lg';

  /** Classe CSS additionnelle */
  className?: string;
}

// ==========================================
// CONFIG
// ==========================================

const STATUS_CONFIG: Record<
  PianoStatus,
  { label: string; bgClass: string; textClass: string }
> = {
  [PianoStatus.Normal]: {
    label: 'Normal',
    bgClass: 'bg-gray-100',
    textClass: 'text-gray-700'
  },
  [PianoStatus.Proposed]: {
    label: 'À faire',
    bgClass: 'bg-yellow-100',
    textClass: 'text-yellow-800'
  },
  [PianoStatus.Top]: {
    label: 'Top',
    bgClass: 'bg-amber-100',
    textClass: 'text-amber-800'
  },
  [PianoStatus.Completed]: {
    label: 'Complété',
    bgClass: 'bg-green-100',
    textClass: 'text-green-800'
  }
};

// ==========================================
// COMPONENT
// ==========================================

export function PianoStatusPill({
  status,
  showIcon = true,
  size = 'md',
  className = ''
}: PianoStatusPillProps) {
  const config = STATUS_CONFIG[status];
  const icon = showIcon ? getPianoStatusIcon(status) : null;

  const sizeClasses = {
    sm: 'text-xs px-2 py-0.5',
    md: 'text-sm px-2.5 py-1',
    lg: 'text-base px-3 py-1.5'
  };

  return (
    <span
      className={`
        inline-flex items-center gap-1
        font-medium rounded-full
        ${config.bgClass}
        ${config.textClass}
        ${sizeClasses[size]}
        ${className}
      `}
    >
      {icon && <span className="leading-none">{icon}</span>}
      <span>{config.label}</span>
    </span>
  );
}

export default PianoStatusPill;
