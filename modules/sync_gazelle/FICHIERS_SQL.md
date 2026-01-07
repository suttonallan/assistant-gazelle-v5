# 📁 Fichiers SQL - Guide de Nettoyage

## ✅ Fichiers à GARDER (utilisés en production)

### 1. `create_appointments_table.sql`
- **Usage :** Création de la table `gazelle_appointments`
- **Script Python :** `scripts/create_appointments_table.py`
- **Statut :** ✅ **À GARDER**

### 2. `create_contacts_table.sql`
- **Usage :** Création de la table `gazelle_contacts`
- **Statut :** ✅ **À GARDER**

### 3. `create_timeline_entries_table_safe.sql`
- **Usage :** Création/modification sécurisée de `gazelle_timeline_entries`
- **Note :** Version "safe" qui utilise `ALTER TABLE ADD COLUMN IF NOT EXISTS`
- **Statut :** ✅ **À GARDER** (version recommandée)

## ⚠️ Fichiers OBSOLÈTES (à supprimer ou archiver)

### 4. `create_timeline_entries_table.sql`
- **Version :** Ancienne version (remplacée par `_safe.sql`)
- **Statut :** ❌ **À SUPPRIMER**

### 5. `create_timeline_entries_table_fixed.sql`
- **Version :** Version "drop and recreate" (non recommandée si données existent)
- **Statut :** ❌ **À SUPPRIMER** (ou archiver si nécessaire)

### 6. `create_all_missing_tables.sql`
- **Usage :** Script consolidé (probablement temporaire)
- **Note :** Contient contacts + timeline
- **Statut :** ⚠️ **À ARCHIVER** (garder comme référence)

### 7. `create_tables_public.sql`
- **Usage :** Script général pour clients + pianos (probablement obsolète)
- **Note :** Les tables clients/pianos sont déjà créées
- **Statut :** ⚠️ **À ARCHIVER**

### 8. `create_tables.sql`
- **Usage :** Script très ancien
- **Statut :** ❌ **À SUPPRIMER**

### 9. `create_tables_simple.sql`
- **Usage :** Version simplifiée (probablement obsolète)
- **Statut :** ❌ **À SUPPRIMER**

### 10. `create_tables_contacts_appointments.sql`
- **Usage :** Version consolidée temporaire
- **Statut :** ⚠️ **À ARCHIVER**

## 📋 Recommandation

**Actions suggérées :**
1. ✅ Garder : `create_appointments_table.sql`, `create_contacts_table.sql`, `create_timeline_entries_table_safe.sql`
2. ❌ Supprimer : Les versions obsolètes (`create_timeline_entries_table.sql`, `_fixed.sql`, `create_tables.sql`, `create_tables_simple.sql`)
3. 📦 Archiver : Les scripts consolidés temporaires (`create_all_missing_tables.sql`, `create_tables_public.sql`, `create_tables_contacts_appointments.sql`)

---

**Date de création :** 2025-12-16
**Dernière mise à jour :** 2025-12-16




