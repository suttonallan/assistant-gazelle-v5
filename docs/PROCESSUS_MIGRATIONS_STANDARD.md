# 📋 Processus Standardisé pour les Migrations

**Pour éviter les problèmes à l'avenir!**

---

## 🚀 Processus Automatique

### 1. Vérifier les Migrations

**Double-cliquez sur:** `VERIFIER_TOUTES_MIGRATIONS.bat`

Le script:
- ✅ Vérifie automatiquement toutes les migrations
- ✅ Liste celles qui manquent
- ✅ Donne les instructions exactes pour chaque migration

### 2. Exécuter les Migrations Manquantes

Le script vous dira exactement quoi faire. En général:
1. Supabase Dashboard → SQL Editor
2. Ouvrir le fichier indiqué
3. Copier-coller dans Supabase
4. Run
5. Attendre 10 secondes

### 3. Relancer la Vérification

Double-cliquez à nouveau sur `VERIFIER_TOUTES_MIGRATIONS.bat` pour confirmer.

---

## 📁 Structure des Migrations

```
modules/
  └── inventaire/
      └── migrations/
          ├── 001_create_inventory_tables.sql
          ├── 002_add_product_classifications.sql
          └── 003_xxx.sql (futures migrations)
```

**Règle:** Numérotation séquentielle (001, 002, 003...)

---

## ✅ Avantages

- ✅ Vérification automatique
- ✅ Instructions claires
- ✅ Pas besoin de se souvenir quoi faire
- ✅ Fonctionne pour toutes les migrations futures

---

## 🔄 Pour les Nouvelles Migrations

1. Créer le fichier SQL dans `modules/inventaire/migrations/003_xxx.sql`
2. Ajouter la vérification dans `scripts/gestion_migrations.py`
3. C'est tout! Le système gère le reste.

---

**Plus besoin de se casser la tête!** 🎉
