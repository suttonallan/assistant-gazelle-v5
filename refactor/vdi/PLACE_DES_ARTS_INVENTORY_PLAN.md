# Plan: Inventaire Pianos Place des Arts

## Objectif
Créer un inventaire de pianos pour Place des Arts similaire à celui de Vincent d'Indy, avec fonctionnalité de mapping entre les abréviations/locations Place des Arts et les vrais pianos de Gazelle.

## Structure

### 1. Table de Mapping (Supabase)
Table `pda_piano_mappings` pour associer:
- `piano_abbreviation` (ex: "SALLE1", "GRAND", "PETIT") - Abréviation dans les demandes PDA
- `gazelle_piano_id` (ex: "ins_9H7Mh59SXwEs2JxL") - ID du piano dans Gazelle
- `location` - Localisation complète (ex: "Salle Wilfrid-Pelletier")
- `created_at`, `updated_at`, `created_by`

### 2. Composant PDAInventoryTable
Basé sur `InventoryTable.tsx` mais adapté pour:
- Afficher les pianos de Gazelle pour le client Place des Arts
- Colonne "Abréviation PDA" avec possibilité de mapper
- Colonne "Demandes associées" (nombre de demandes utilisant cette abréviation)
- Interface de mapping: dropdown pour sélectionner un piano Gazelle

### 3. Interface de Mapping
- Vue côte à côte:
  - Gauche: Liste des abréviations uniques trouvées dans les demandes PDA
  - Droite: Liste des pianos Gazelle disponibles
  - Action: Bouton "Mapper" pour associer abréviation ↔ piano

### 4. Confrontation Demandes ↔ Pianos
- Afficher pour chaque piano:
  - Nombre de demandes utilisant l'abréviation mappée
  - Dernière demande associée
  - Statut des demandes (ASSIGN_OK, COMPLETED, etc.)

## Fichiers créés ✅

1. ✅ `refactor/vdi/components/PDAInventory/PDAInventoryTable.tsx` - Inventaire avec mapping
2. ✅ `refactor/vdi/components/PDAInventory/PianoMappingModal.tsx` - Modal de jumelage
3. ✅ `refactor/vdi/components/PDAInventory/index.tsx` - Export
4. ✅ `refactor/vdi/sql/009_create_pda_piano_mappings.sql` - Table de mapping
5. ✅ `refactor/vdi/hooks/usePDAPianoMappings.ts` - Hook de gestion
6. ✅ `refactor/vdi/types/pda.types.ts` - Types TypeScript

## Intégration
- Ajouter onglet "Inventaire Pianos" dans le dashboard Place des Arts (frontend V5)
- OU créer une vue séparée dans VDI V7 pour Place des Arts

