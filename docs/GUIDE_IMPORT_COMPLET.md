# 🚀 Guide Complet: Import des Données ProductDisplay

**Objectif:** Importer les données de classification de produits depuis Gazelle SQL Server vers Supabase.

**Temps estimé:** 30 minutes

---

## 📋 Checklist Préalable

- [ ] Migration SQL 002 exécutée dans Supabase
- [ ] Accès à SQL Server Gazelle (Cursor PC)
- [ ] Variables d'environnement Supabase configurées (Cursor Mac)

---

## 🖥️ ÉTAPE 1: Cursor PC (Windows) - Extraction des Données

### 1.1 Préparer l'environnement

```bash
# Installer pyodbc si nécessaire
pip install pyodbc
```

### 1.2 Configurer le script

Ouvrez `scripts/fetch_gazelle_products.py` et modifiez la section `SQL_SERVER_CONFIG`:

```python
SQL_SERVER_CONFIG = {
    'server': 'pianotek.database.windows.net',  # Votre serveur
    'database': 'PianoTek',
    'username': 'votre_username',
    'password': 'votre_password',
    'driver': '{ODBC Driver 17 for SQL Server}',
}
```

### 1.3 Exécuter le script

```bash
cd /chemin/vers/assistant-gazelle-v5
python scripts/fetch_gazelle_products.py
```

### 1.4 Résultat

Le script génère 2 fichiers à la racine du projet:

- ✅ `gazelle_products_export.json` - Backup JSON complet
- ✅ `supabase_insert.sql` - Script SQL pour Supabase

### 1.5 Transférer vers Mac

- **Option 1:** USB / Disque externe
- **Option 2:** Google Drive / Dropbox
- **Option 3:** Email (si fichiers < 25MB)
- **Option 4:** Git (commiter les fichiers)

---

## 🍎 ÉTAPE 2: Cursor Mac - Migration SQL 002

### 2.1 Ouvrir Supabase Dashboard

1. Allez sur https://app.supabase.com
2. Sélectionnez votre projet
3. Cliquez sur **SQL Editor** dans le menu gauche

### 2.2 Exécuter la migration

1. Cliquez sur **New Query**
2. Ouvrez le fichier: `modules/inventaire/migrations/002_add_product_classifications.sql`
3. **Copiez tout le contenu**
4. **Collez** dans SQL Editor
5. Cliquez sur **Run** (ou `Cmd+Enter`)

### 2.3 Vérifier la migration

Exécutez cette requête pour vérifier:

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

Vous devriez voir **8 lignes** (une par colonne).

---

## 🍎 ÉTAPE 3: Cursor Mac - Import des Données

### 3.1 Préparer le fichier SQL

1. Transférez `supabase_insert.sql` depuis Cursor PC vers votre Mac
2. Placez-le dans le projet (ex: à la racine)

### 3.2 Exécuter dans Supabase

1. Dans Supabase SQL Editor, créez une **New Query**
2. Ouvrez le fichier `supabase_insert.sql`
3. **Copiez tout le contenu**
4. **Collez** dans SQL Editor
5. Cliquez sur **Run**

⚠️ **Note:** Si vous avez beaucoup de produits (>1000), l'exécution peut prendre 1-2 minutes.

### 3.3 Vérifier l'import

Exécutez:

```sql
-- Compter les produits importés
SELECT COUNT(*) as total_produits FROM produits_catalogue;

-- Voir quelques exemples
SELECT 
    code_produit,
    nom,
    categorie,
    has_commission,
    commission_rate,
    display_order
FROM produits_catalogue
ORDER BY display_order, code_produit
LIMIT 10;
```

---

## 🍎 ÉTAPE 4: Cursor Mac - Ajouter Export CSV

### 4.1 Vérifier que le composant existe

Le fichier `frontend/src/components/ExportButton.jsx` devrait déjà exister (créé par Cursor Mac).

### 4.2 Vérifier l'intégration

Le composant `InventaireDashboard.jsx` devrait déjà avoir:
- Import de `ExportButton`
- Bouton d'export dans l'onglet "Catalogue"
- Bouton d'export dans l'onglet "Admin"

Si ce n'est pas le cas, vérifiez les modifications dans `InventaireDashboard.jsx`.

### 4.3 Tester le frontend

```bash
cd frontend
npm run dev
```

Ouvrez http://localhost:5173 et vérifiez:
- ✅ Le bouton "📥 Exporter CSV" apparaît
- ✅ Cliquer dessus télécharge un fichier CSV
- ✅ Le CSV contient les colonnes attendues

---

## ✅ Vérification Finale

### Checklist de succès

- [ ] Migration 002 exécutée (8 colonnes présentes)
- [ ] Données importées (produits visibles dans Supabase)
- [ ] Frontend affiche les produits
- [ ] Export CSV fonctionne
- [ ] Commissions affichées correctement
- [ ] Ordre d'affichage fonctionne

### Test complet

1. **Backend:**
   ```bash
   curl http://localhost:8000/inventaire/catalogue | jq '.count'
   ```
   Devrait retourner le nombre de produits.

2. **Frontend:**
   - Ouvrir http://localhost:5173
   - Se connecter (admin)
   - Aller dans "Inventaire"
   - Vérifier que les produits s'affichent
   - Cliquer sur "📥 Exporter CSV"
   - Vérifier le fichier téléchargé

---

## 🐛 Dépannage

### Erreur: "column already exists"

✅ **Normal!** La migration utilise `IF NOT EXISTS`. Les colonnes existent déjà.

### Erreur: "relation produits_catalogue does not exist"

❌ Exécutez d'abord la migration 001:
- `modules/inventaire/migrations/001_create_inventory_tables.sql`

### Erreur: "duplicate key value violates unique constraint"

✅ **Normal!** Le script utilise `ON CONFLICT DO UPDATE`, donc les produits existants sont mis à jour.

### Erreur: "connection timeout" lors de l'import

⚠️ Si vous avez >1000 produits, divisez le script SQL en plusieurs parties (ex: 500 produits par batch).

### Export CSV ne fonctionne pas

1. Vérifiez la console du navigateur (F12)
2. Vérifiez que `ExportButton.jsx` est bien importé
3. Vérifiez que `data` n'est pas vide

---

## 📊 Statistiques Attendues

Après import réussi:

- **Produits:** ~100-500 produits (selon votre catalogue Gazelle)
- **Avec commission:** ~30-50% des produits
- **Variantes:** ~20-30 groupes de variantes
- **Taille CSV:** ~50-200 KB

---

## 🎯 Prochaines Étapes

Une fois l'import terminé:

1. ✅ Tester l'interface React
2. ✅ Vérifier les commissions
3. ✅ Réorganiser l'ordre d'affichage
4. ✅ Exporter les données
5. ⏭️ Configurer la synchronisation automatique (optionnel)

---

## 📞 Support

Si vous rencontrez des problèmes:

1. **Vérifiez les logs:**
   - Supabase Dashboard → Logs
   - Console navigateur (F12)

2. **Scripts de diagnostic:**
   ```bash
   python3 scripts/check_migration_002.py
   ```

3. **Documentation:**
   - `docs/INTEGRATION_PRODUCT_DISPLAY_V5.md`
   - `docs/GUIDE_MIGRATION_002.md`

---

**🎉 Félicitations!** Une fois ces étapes terminées, vous verrez vos données dans l'interface React!
