# ⚠️ Ordre d'Exécution des Migrations

**IMPORTANT:** Les migrations doivent être exécutées dans l'ordre!

---

## 🔴 Erreur Actuelle

```
ERROR: 42P01: relation "produits_catalogue" does not exist
```

**Cause:** La migration 001 (qui crée la table) n'a pas été exécutée avant la migration 002.

---

## ✅ Solution: Exécuter les Migrations dans l'Ordre

### ÉTAPE 1: Migration 001 - Créer les Tables (5 min)

1. **Ouvrir Supabase Dashboard:**
   - https://app.supabase.com
   - Votre projet → **SQL Editor**

2. **Copier le script:**
   - Ouvrir: `modules/inventaire/migrations/001_create_inventory_tables.sql`
   - **Copier tout le contenu**

3. **Exécuter:**
   - Dans SQL Editor → **New Query**
   - **Coller** le contenu
   - Cliquer **Run** (ou `Cmd+Enter`)

4. **Vérifier que les tables sont créées:**
   ```sql
   SELECT table_name 
   FROM information_schema.tables 
   WHERE table_schema = 'public' 
   AND table_name IN ('produits_catalogue', 'inventaire_techniciens', 'transactions_inventaire');
   ```
   Devrait retourner **3 lignes**.

5. **Vérifier la structure de `produits_catalogue`:**
   ```sql
   SELECT column_name, data_type 
   FROM information_schema.columns 
   WHERE table_name = 'produits_catalogue'
   ORDER BY ordinal_position;
   ```
   Devrait montrer les colonnes de base (code_produit, nom, categorie, etc.)

✅ **Migration 001 terminée!** Passez à l'étape 2.

---

### ÉTAPE 2: Migration 002 - Ajouter les Colonnes de Classification (5 min)

1. **Dans Supabase SQL Editor:**
   - Créer une **New Query**

2. **Copier le script:**
   - Ouvrir: `modules/inventaire/migrations/002_add_product_classifications.sql`
   - **Copier tout le contenu**

3. **Exécuter:**
   - **Coller** dans SQL Editor
   - Cliquer **Run**

4. **Vérifier que les nouvelles colonnes existent:**
   ```sql
   SELECT column_name, data_type 
   FROM information_schema.columns 
   WHERE table_name = 'produits_catalogue' 
   AND column_name IN (
       'has_commission',
       'commission_rate',
       'display_order',
       'variant_group',
       'variant_label',
       'is_active',
       'gazelle_product_id',
       'last_sync_at'
   )
   ORDER BY column_name;
   ```
   Devrait retourner **8 lignes** (une par colonne).

✅ **Migration 002 terminée!** Toutes les colonnes sont maintenant présentes.

---

## 📋 Checklist Complète

- [ ] Migration 001 exécutée
- [ ] Table `produits_catalogue` créée
- [ ] Table `inventaire_techniciens` créée
- [ ] Table `transactions_inventaire` créée
- [ ] Migration 002 exécutée
- [ ] Colonnes de classification ajoutées (8 colonnes)
- [ ] Vérification finale réussie

---

## 🐛 Si Erreur "relation already exists"

Si vous obtenez une erreur lors de la migration 001:
```
ERROR: relation "produits_catalogue" already exists
```

**C'est normal!** Cela signifie que la table existe déjà. Vous pouvez:
1. **Option A:** Ignorer l'erreur et passer directement à la migration 002
2. **Option B:** Vérifier d'abord si la table existe:
   ```sql
   SELECT EXISTS (
       SELECT FROM information_schema.tables 
       WHERE table_name = 'produits_catalogue'
   );
   ```

---

## 🎯 Prochaines Étapes

Une fois les deux migrations exécutées:

1. ✅ Vérifier que toutes les colonnes existent
2. ⏭️ Importer les données depuis Gazelle (voir `GUIDE_IMPORT_COMPLET.md`)
3. ⏭️ Tester l'interface React

---

## 📝 Résumé

**Ordre d'exécution:**
1. **Migration 001** → Crée les tables de base
2. **Migration 002** → Ajoute les colonnes de classification

**Temps total:** ~10 minutes

**Fichiers:**
- `modules/inventaire/migrations/001_create_inventory_tables.sql`
- `modules/inventaire/migrations/002_add_product_classifications.sql`
