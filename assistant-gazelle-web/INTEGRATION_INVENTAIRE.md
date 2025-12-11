# ✅ Intégration Inventaire - Résumé

## 📦 Ce qui a été créé

### 1. Scripts Python (`scripts/`)
- ✅ **`inventory_checker.py`** : Vérification des stocks bas et alertes
  - Compatible Supabase (PostgreSQL), SQLite et SQL Server
  - Fonctions : `check_low_stock()`, `check_zero_stock()`, `generate_alerts()`
  
- ✅ **`export_inventory_data.py`** : Export des données d'inventaire
  - Exporte Products, Inventory, ProductDisplay
  - Formats CSV et JSON
  - Compatible avec toutes les bases de données

### 2. Routes Flask (`app/`)
- ✅ **`inventory_routes.py`** : Blueprint Flask avec endpoints API
  - `GET /api/inventory/check-stock` : Vérifier les stocks
  - `GET /api/inventory/alerts` : Obtenir les alertes
  - `GET /api/inventory/export` : Exporter les données (admin)
  - `GET /api/inventory/download/<table>` : Télécharger CSV
  - `GET /api/inventory/health` : Vérification de santé

- ✅ **`__init__.py`** : Factory function pour créer l'app Flask
  - Enregistre automatiquement le blueprint inventaire
  - Configure CORS

### 3. Point d'entrée
- ✅ **`run_web.py`** : Script pour lancer l'application
  - Compatible Render (utilise variable PORT)
  - Configuration via variables d'environnement

### 4. Configuration
- ✅ **`requirements.txt`** : Toutes les dépendances nécessaires
  - Flask, psycopg2-binary, python-dotenv, etc.

### 5. Documentation
- ✅ **`README_INVENTAIRE.md`** : Guide complet d'utilisation

## 🚀 Utilisation

### Développement local

1. **Installer les dépendances** :
```bash
cd assistant-gazelle-web
pip install -r requirements.txt
```

2. **Configurer `.env`** :
```env
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_PASSWORD=votre_mot_de_passe
# OU pour SQLite local
USE_SQLITE=true
```

3. **Lancer l'application** :
```bash
python run_web.py
```

4. **Tester les endpoints** :
```bash
curl http://localhost:5000/api/inventory/health
curl http://localhost:5000/api/inventory/check-stock
```

### Déploiement sur Render

1. **Variables d'environnement** (Render Dashboard) :
   - `SUPABASE_URL` ou `SUPABASE_HOST`
   - `SUPABASE_PASSWORD`
   - `SUPABASE_DATABASE` (défaut: postgres)
   - `SUPABASE_USER` (défaut: postgres)
   - `SUPABASE_PORT` (défaut: 5432)
   - `ALLOWED_ORIGINS` (pour CORS)

2. **Build Command** :
```bash
pip install -r requirements.txt
```

3. **Start Command** :
```bash
gunicorn run_web:app
# OU
python run_web.py
```

4. **Health Check Path** :
```
/health
# OU
/api/inventory/health
```

## 📊 Exemples d'utilisation

### Via API (recommandé)

```javascript
// Vérifier les stocks bas
fetch('https://votre-app.onrender.com/api/inventory/check-stock')
  .then(res => res.json())
  .then(data => console.log(data));

// Obtenir les alertes pour un technicien
fetch('https://votre-app.onrender.com/api/inventory/alerts?technician_id=usr_xxxxx')
  .then(res => res.json())
  .then(data => console.log(data));
```

### Via scripts Python

```bash
# Vérifier les stocks
python scripts/inventory_checker.py

# Exporter les données
python scripts/export_inventory_data.py
```

## 🔧 Intégration dans votre app existante

Si vous avez déjà une app Flask, vous pouvez simplement enregistrer le blueprint :

```python
from app.inventory_routes import inventory_bp

# Dans votre app Flask existante
app.register_blueprint(inventory_bp)
```

## ⚠️ Notes importantes

1. **Authentification** : Le décorateur `@require_auth` dans `inventory_routes.py` doit être adapté à votre système d'authentification actuel.

2. **Priorité des bases de données** :
   - Si `SUPABASE_HOST` ou `SUPABASE_URL` est défini → Supabase
   - Sinon si `USE_SQLITE=true` → SQLite
   - Sinon → SQL Server (fallback)

3. **Schémas SQL** :
   - Supabase : `"inv"."Products"` (avec guillemets)
   - SQLite : `Products` (sans schéma)
   - SQL Server : `inv.Products` (avec schéma)

## 📚 Prochaines étapes

1. ✅ Scripts créés et testés
2. ✅ Endpoints API créés
3. ⏳ Adapter l'authentification à votre système
4. ⏳ Tester sur Render
5. ⏳ Intégrer dans l'interface frontend

## 🔍 Dépannage

### Erreur "Module not found"
- Vérifiez que vous êtes dans `assistant-gazelle-web/`
- Vérifiez que `sys.path` est correct dans les scripts

### Erreur de connexion Supabase
- Vérifiez toutes les variables d'environnement
- Testez la connexion avec `psql` ou un client PostgreSQL

### Endpoints retournent 500
- Vérifiez les logs Render
- Vérifiez que les tables existent dans Supabase
- Testez les scripts directement : `python scripts/inventory_checker.py`

---

**Tout est prêt pour la migration vers Render ! 🚀**

