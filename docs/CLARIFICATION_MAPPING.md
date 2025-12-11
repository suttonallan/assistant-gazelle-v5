# Clarification: Ce qui est "Mixte" dans le Mapping

## 🔍 Problèmes Identifiés (Points Confus)

### 1. **Deux Sources de Données Différentes** ⚠️

**Problème:** Actuellement, il y a confusion entre:
- **SQL Server Gazelle (V4)** - Utilisé pour l'import initial (`import_gazelle_product_display.py`)
- **API Gazelle GraphQL (CRM)** - La vraie source pour les imports futurs

**Solution:**
- ✅ **Migration initiale:** Continue d'utiliser SQL Server (déjà fait)
- ✅ **Imports futurs:** Utilise l'API GraphQL Gazelle (`GazelleAPIClient.get_products()`)
- ✅ **Mapping:** Se fait avec les produits de l'API GraphQL (pas SQL Server)

### 2. **Identifiants Différents** ⚠️

**Problème:**
- SQL Server utilise `ProductId` (INTEGER)
- API GraphQL utilise `id` (STRING, ex: "prod_123abc")
- Supabase utilise `code_produit` (TEXT, ex: "PROD-123" ou "CORD-001")

**Solution:**
- Le mapping utilise `gazelle_product_id` = `id` de l'API GraphQL (pas `ProductId` de SQL Server)
- Lors du premier import depuis SQL Server, on ne crée PAS de mapping (c'est une migration unique)
- Les mappings sont créés uniquement pour les produits importés depuis l'API GraphQL

### 3. **Quand Créer les Mappings?** ⚠️

**Scénarios:**

#### Scénario A: Premier Import (Migration SQL Server → Supabase)
- ❌ **NE PAS** créer de mapping (c'est une migration unique)
- ✅ Les produits sont créés directement dans Supabase
- ✅ Les mappings seront créés plus tard, manuellement ou lors du premier import depuis l'API

#### Scénario B: Import depuis API Gazelle (Futur)
- ✅ Vérifier si `gazelle_product_id` existe dans `produits_mapping`
- ✅ Si OUI: Utiliser le `code_produit` mappé → UPDATE
- ✅ Si NON: Créer nouveau produit → Proposer mapping dans l'interface

### 4. **Code Produit: Auto-généré vs Manuel** ⚠️

**Problème:**
- Certains produits ont un `code_produit` auto-généré: `PROD-{ProductId}`
- D'autres ont un vrai SKU: `CORD-001`, `DOUILLE-BOIS`, etc.

**Solution:**
- Le mapping doit fonctionner avec les deux types
- L'interface permet de mapper n'importe quel produit Gazelle vers n'importe quel produit Supabase
- Suggestion automatique: Si SKU Gazelle = code_produit Supabase → mapping suggéré

## ✅ Ce qui est CLAIR maintenant

1. **Table `produits_mapping`:**
   - Stocke: `gazelle_product_id` (ID de l'API GraphQL) → `code_produit` (Supabase)
   - UN mapping par produit Gazelle

2. **Interface Admin:**
   - Onglet "Mapping Gazelle" visible seulement pour les admins
   - Vue côte à côte: Produits Gazelle (non mappés) ↔ Produits Supabase (sans mapping)
   - Sélection + bouton "Créer Mapping"

3. **Workflow:**
   ```
   Import API Gazelle → Vérifier mapping → Si existe: UPDATE | Si non: Créer + Proposer mapping
   ```

## 🎯 Actions à Faire

1. ✅ Migration SQL exécutée
2. ✅ API endpoints créés
3. ✅ Interface React créée
4. ⏳ **Modifier script d'import pour utiliser l'API GraphQL** (pas SQL Server)
5. ⏳ **Tester le workflow complet**

## 📝 Notes Importantes

- **Ne pas mélanger** SQL Server (migration unique) et API GraphQL (imports futurs)
- **Le mapping est pour l'API GraphQL uniquement**
- **Les produits importés depuis SQL Server n'ont PAS de mapping** (c'est normal)
