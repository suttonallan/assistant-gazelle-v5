/**
 * useRangeSelection Hook - Shift+Click Range Selection
 *
 * Implémente sélection par plage avec Shift+Clic
 * (comme Excel, Finder, Gmail)
 *
 * @example
 * ```tsx
 * function PianosTable({ pianos }) {
 *   const { selectedIds, handleClick, selectAll, clearAll } = useRangeSelection(
 *     pianos.map(p => p.gazelleId)
 *   );
 *
 *   return pianos.map(piano => (
 *     <Checkbox
 *       checked={selectedIds.has(piano.gazelleId)}
 *       onClick={(e) => handleClick(piano.gazelleId, e.shiftKey)}
 *     />
 *   ));
 * }
 * ```
 */

import { useState, useCallback, useMemo } from 'react';

// ==========================================
// TYPES
// ==========================================

interface UseRangeSelectionOptions {
  /** IDs initialement sélectionnés */
  initialSelected?: Set<string>;

  /** Callback appelé quand sélection change */
  onChange?: (selectedIds: Set<string>) => void;

  /** Mode multi-select (désactiver Shift+Clic) */
  disableRangeSelection?: boolean;
}

interface UseRangeSelectionReturn {
  /** IDs actuellement sélectionnés */
  selectedIds: Set<string>;

  /** Handler pour click sur item (avec Shift support) */
  handleClick: (id: string, shiftKey: boolean) => void;

  /** Toggle un ID */
  toggle: (id: string) => void;

  /** Sélectionner tous */
  selectAll: () => void;

  /** Désélectionner tous */
  clearAll: () => void;

  /** Check si ID sélectionné */
  isSelected: (id: string) => boolean;

  /** Nombre d'items sélectionnés */
  count: number;

  /** Sélectionner plage (programmati cally) */
  selectRange: (startId: string, endId: string) => void;
}

// ==========================================
// HOOK
// ==========================================

export function useRangeSelection(
  /** Liste complète des IDs (dans l'ordre affiché) */
  allIds: string[],
  options: UseRangeSelectionOptions = {}
): UseRangeSelectionReturn {
  const { initialSelected = new Set(), onChange, disableRangeSelection = false } = options;

  // State
  const [selectedIds, setSelectedIds] = useState<Set<string>>(initialSelected);
  const [lastClickedId, setLastClickedId] = useState<string | null>(null);

  // ==========================================
  // HELPERS
  // ==========================================

  /**
   * Trigger onChange callback
   */
  const triggerChange = useCallback(
    (newSelection: Set<string>) => {
      if (onChange) {
        onChange(newSelection);
      }
    },
    [onChange]
  );

  /**
   * Get range between two IDs
   */
  const getRangeBetween = useCallback(
    (startId: string, endId: string): string[] => {
      const startIndex = allIds.indexOf(startId);
      const endIndex = allIds.indexOf(endId);

      if (startIndex === -1 || endIndex === -1) {
        return [];
      }

      const [min, max] = [Math.min(startIndex, endIndex), Math.max(startIndex, endIndex)];

      return allIds.slice(min, max + 1);
    },
    [allIds]
  );

  // ==========================================
  // ACTIONS
  // ==========================================

  /**
   * Handle click avec Shift support
   */
  const handleClick = useCallback(
    (id: string, shiftKey: boolean) => {
      setSelectedIds((prev) => {
        const next = new Set(prev);

        // Cas 1: Shift+Clic ET lastClickedId existe
        if (shiftKey && lastClickedId && !disableRangeSelection) {
          // Sélectionner plage
          const range = getRangeBetween(lastClickedId, id);

          // Comportement standard: Shift+Clic = TOUJOURS sélectionner le range
          // (comme Excel, Finder, Gmail)
          range.forEach((rangeId) => {
            next.add(rangeId);
          });
        }
        // Cas 2: Click normal
        else {
          if (next.has(id)) {
            next.delete(id);
          } else {
            next.add(id);
          }
        }

        triggerChange(next);
        return next;
      });

      // Update lastClickedId (sauf si Shift, pour permettre range multiple)
      if (!shiftKey) {
        setLastClickedId(id);
      }
    },
    [lastClickedId, getRangeBetween, triggerChange, disableRangeSelection]
  );

  /**
   * Toggle un ID (programmactically)
   */
  const toggle = useCallback(
    (id: string) => {
      setSelectedIds((prev) => {
        const next = new Set(prev);
        if (next.has(id)) {
          next.delete(id);
        } else {
          next.add(id);
        }
        triggerChange(next);
        return next;
      });
    },
    [triggerChange]
  );

  /**
   * Sélectionner tous
   */
  const selectAll = useCallback(() => {
    const next = new Set(allIds);
    setSelectedIds(next);
    triggerChange(next);
  }, [allIds, triggerChange]);

  /**
   * Désélectionner tous
   */
  const clearAll = useCallback(() => {
    const next = new Set<string>();
    setSelectedIds(next);
    triggerChange(next);
    setLastClickedId(null);
  }, [triggerChange]);

  /**
   * Check si ID sélectionné
   */
  const isSelected = useCallback(
    (id: string): boolean => {
      return selectedIds.has(id);
    },
    [selectedIds]
  );

  /**
   * Sélectionner plage (programmactically)
   */
  const selectRange = useCallback(
    (startId: string, endId: string) => {
      const range = getRangeBetween(startId, endId);

      setSelectedIds((prev) => {
        const next = new Set(prev);
        range.forEach((id) => next.add(id));
        triggerChange(next);
        return next;
      });

      setLastClickedId(endId);
    },
    [getRangeBetween, triggerChange]
  );

  // ==========================================
  // COMPUTED
  // ==========================================

  const count = useMemo(() => selectedIds.size, [selectedIds]);

  // ==========================================
  // RETURN
  // ==========================================

  return {
    selectedIds,
    handleClick,
    toggle,
    selectAll,
    clearAll,
    isSelected,
    count,
    selectRange
  };
}

/**
 * Helper: Get indeterminate state pour "Select All" checkbox
 *
 * @returns { checked, indeterminate }
 */
export function getSelectAllState(selectedCount: number, totalCount: number) {
  return {
    checked: selectedCount > 0 && selectedCount === totalCount,
    indeterminate: selectedCount > 0 && selectedCount < totalCount
  };
}

export default useRangeSelection;
