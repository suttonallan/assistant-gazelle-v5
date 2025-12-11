# 🚀 Guide: Exécuter les Migrations Inventaire dans Supabase

**Date:** 2025-12-10
**Statut:** ⚠️ URGENT - Les migrations SQL doivent être exécutées pour que l'admin inventaire fonctionne

---

## Problème Actuel

L'interface admin de l'inventaire affiche "Aucun produit dans le catalogue" car:

1. ✅ La table `produits_catalogue` existe dans Supabase
2. ❌ MAIS les colonnes de classification (`has_commission`, `commission_rate`, etc.) n'existent **pas encore**
3. ❌ La table est vide (pas de produits de test)

**Erreur technique:**
```
Could not find the 'commission_rate' column of 'produits_catalogue' in the schema cache
```

---

## Solution: Exécuter les Migrations SQL

### Étape 1: Ouvrir Supabase SQL Editor

1. Va sur: https://supabase.com/dashboard
2. Connecte-toi avec ton compte
3. Sélectionne le projet **Assistant Gazelle V5**
4. Dans le menu de gauche, clique sur **"SQL Editor"**

### Étape 2: Exécuter Migration 001 (Créer les Tables)

1. Dans SQL Editor, clique sur **"New query"**
2. Copie le contenu du fichier:
   ```
   /Users/allansutton/Documents/assistant-gazelle-v5/modules/inventaire/migrations/001_create_inventory_tables.sql
   ```
3. Colle dans l'éditeur SQL
4. Clique sur **"Run"** (ou Cmd+Enter)
5. Tu devrais voir un message de succès (vert)

**Ce que cette migration fait:**
- Crée la table `produits_catalogue` (si elle n'existe pas)
- Crée la table `inventaire_techniciens`
- Crée la table `transactions_inventaire`
- Ajoute 5 produits de test (CORD-001, CORD-002, FELT-001, TOOL-001, CLEAN-001)
- Ajoute du stock pour Allan

### Étape 3: Exécuter Migration 002 (Ajouter les Classifications)

1. Dans SQL Editor, clique sur **"New query"** à nouveau
2. Copie le contenu du fichier:
   ```
   /Users/allansutton/Documents/assistant-gazelle-v5/modules/inventaire/migrations/002_add_product_classifications.sql
   ```
3. Colle dans l'éditeur SQL
4. Clique sur **"Run"** (ou Cmd+Enter)
5. Tu devrais voir un message de succès (vert)

**Ce que cette migration fait:**
- Ajoute 8 nouvelles colonnes à `produits_catalogue`:
  - `has_commission` (BOOLEAN)
  - `commission_rate` (DECIMAL)
  - `variant_group` (TEXT)
  - `variant_label` (TEXT)
  - `display_order` (INTEGER)
  - `is_active` (BOOLEAN)
  - `gazelle_product_id` (INTEGER)
  - `last_sync_at` (TIMESTAMPTZ)
- Crée des index pour la performance
- Configure les commissions sur les produits de test

### Étape 4: Vérifier que ça a fonctionné

Dans SQL Editor, exécute cette requête de vérification:

```sql
-- Vérifier les colonnes de la table
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'produits_catalogue'
ORDER BY ordinal_position;
```

Tu devrais voir **toutes** ces colonnes:
- id
- code_produit
- nom
- categorie
- description
- unite_mesure
- prix_unitaire
- fournisseur
- created_at
- updated_at
- **has_commission** ← Nouvelle
- **commission_rate** ← Nouvelle
- **variant_group** ← Nouvelle
- **variant_label** ← Nouvelle
- **display_order** ← Nouvelle
- **is_active** ← Nouvelle
- **gazelle_product_id** ← Nouvelle
- **last_sync_at** ← Nouvelle

Puis, vérifie les produits:

```sql
-- Voir les produits de test
SELECT code_produit, nom, has_commission, commission_rate, display_order
FROM produits_catalogue
ORDER BY display_order;
```

Tu devrais voir:
```
code_produit | nom                    | has_commission | commission_rate | display_order
-------------|------------------------|----------------|-----------------|---------------
CORD-001     | Corde #1 (Do)         | true           | 15.00           | 1
CORD-002     | Corde #2 (Ré)         | true           | 15.00           | 2
FELT-001     | Feutre tête de marteau| false          | 0.00            | 3
TOOL-001     | Clé d'accord          | true           | 20.00           | 4
CLEAN-001    | Nettoyant touches     | false          | 0.00            | 5
```

---

## Étape 5: Tester l'Interface Admin

1. Va sur http://localhost:5173 (frontend local)
2. Connecte-toi avec ton compte admin
3. Clique sur l'onglet **"Inventaire"**
4. Clique sur l'onglet **"Admin"** (visible seulement pour role=admin)
5. Tu devrais maintenant voir **5 produits** dans le tableau
6. Teste les fonctionnalités:
   - ✏️ Modifier un produit (clic sur l'icône crayon)
   - ↑↓ Changer l'ordre d'affichage
   - 💾 Sauvegarder l'ordre

---

## Problèmes Possibles

### Erreur: "permission denied"

Si tu vois une erreur de permission, c'est que Row Level Security (RLS) est activé.

**Solution temporaire pour le développement:**

```sql
-- Désactiver RLS temporairement (DEV seulement!)
ALTER TABLE produits_catalogue DISABLE ROW LEVEL SECURITY;
ALTER TABLE inventaire_techniciens DISABLE ROW LEVEL SECURITY;
ALTER TABLE transactions_inventaire DISABLE ROW LEVEL SECURITY;
```

**Solution permanente (PROD):**

Créer des policies RLS:

```sql
-- Policy pour lecture publique du catalogue
CREATE POLICY "Public can read catalogue"
ON produits_catalogue
FOR SELECT
USING (true);

-- Policy pour update admin seulement
CREATE POLICY "Admin can update catalogue"
ON produits_catalogue
FOR ALL
USING (auth.jwt() ->> 'role' = 'admin');
```

### Erreur: "relation already exists"

Si une table existe déjà, tu verras cette erreur. C'est **NORMAL** et pas grave.

La migration utilise `CREATE TABLE IF NOT EXISTS`, donc elle ne recrée pas les tables existantes.

Continue avec la migration 002.

### Erreur: "column already exists"

Si une colonne existe déjà, tu verras cette erreur. C'est **NORMAL** et pas grave.

La migration utilise `ADD COLUMN IF NOT EXISTS`, donc elle n'ajoute pas les colonnes déjà existantes.

---

## Vérification Finale

Après avoir exécuté les 2 migrations, exécute ce script:

```bash
curl -s http://localhost:8000/inventaire/catalogue | python3 -m json.tool
```

Tu devrais voir:

```json
{
  "produits": [
    {
      "code_produit": "CORD-001",
      "nom": "Corde #1 (Do)",
      "categorie": "Cordes",
      "has_commission": true,
      "commission_rate": 15.0,
      "display_order": 1,
      ...
    },
    ...
  ],
  "count": 5
}
```

**Si tu vois `"count": 5` → ✅ SUCCESS!**

---

## Prochaines Étapes (Après les Migrations)

1. ✅ L'interface admin fonctionne
2. Tester toutes les fonctionnalités (modifier ordre, éditer produits)
3. Implémenter l'import depuis Gazelle (Cursor PC)
4. Synchroniser les vraies données depuis SQL Server

---

**Besoin d'aide?** Copie-colle les erreurs que tu vois dans Supabase SQL Editor et je t'aiderai à les résoudre.
