# 📦 Module Inventaire - Assistant Gazelle Web

Module complet pour la gestion de l'inventaire dans la version web déployable sur Render.

## 📋 Contenu

### Scripts Python
- **`scripts/inventory_checker.py`** : Vérification des stocks bas et alertes
- **`scripts/export_inventory_data.py`** : Export des données (CSV/JSON)

### Routes Flask
- **`app/inventory_routes.py`** : Endpoints API pour l'inventaire

## 🚀 Installation

1. Installer les dépendances :
```bash
pip install -r requirements.txt
```

2. Configurer les variables d'environnement (`.env`) :
```env
# Supabase (PostgreSQL) - PRIORITÉ
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_PASSWORD=votre_mot_de_passe
SUPABASE_DATABASE=postgres
SUPABASE_USER=postgres
SUPABASE_PORT=5432

# OU SQLite (développement local)
USE_SQLITE=true

# CORS
ALLOWED_ORIGINS=http://localhost:3000,https://votre-app.onrender.com
```

## 📡 Endpoints API

### 1. Vérifier les stocks bas
```http
GET /api/inventory/check-stock
GET /api/inventory/check-stock?technician_id=usr_xxxxx
```

**Réponse :**
```json
{
  "success": true,
  "data": {
    "low_stock": [...],
    "zero_stock": [...],
    "summary": {
      "total_low_stock": 5,
      "total_zero_stock": 2,
      "total_alerts": 7,
      "checked_at": "2025-01-15T10:30:00"
    }
  }
}
```

### 2. Obtenir les alertes
```http
GET /api/inventory/alerts
GET /api/inventory/alerts?type=low
GET /api/inventory/alerts?type=zero
GET /api/inventory/alerts?technician_id=usr_xxxxx
```

### 3. Exporter les données (admin)
```http
GET /api/inventory/export
GET /api/inventory/export?format=csv&table=products
GET /api/inventory/export?format=json&table=all
```

### 4. Télécharger un fichier CSV
```http
GET /api/inventory/download/products
GET /api/inventory/download/inventory
GET /api/inventory/download/product_display
```

### 5. Vérification de santé
```http
GET /api/inventory/health
```

## 🔧 Intégration dans votre app Flask

### Option 1 : Utiliser le blueprint directement

```python
from app.inventory_routes import inventory_bp

app = Flask(__name__)
app.register_blueprint(inventory_bp)
```

### Option 2 : Utiliser la factory function

```python
from app import create_app

app = create_app()
```

## 📊 Utilisation des scripts directement

### Vérifier les stocks
```bash
python scripts/inventory_checker.py
```

### Exporter les données
```bash
python scripts/export_inventory_data.py
```

Les fichiers seront créés dans `data/export_inventory/`.

## 🔄 Déploiement sur Render

1. **Variables d'environnement** : Configurez toutes les variables Supabase dans Render Dashboard
2. **Build Command** : `pip install -r requirements.txt`
3. **Start Command** : `gunicorn run_web:app` ou `python run_web.py`
4. **Health Check** : `/health` ou `/api/inventory/health`

## ⚠️ Notes importantes

- **Priorité DB** : Supabase > SQLite > SQL Server
- **Authentification** : Le décorateur `@require_auth` doit être adapté à votre système d'auth
- **CORS** : Configurez `ALLOWED_ORIGINS` selon vos besoins
- **Logs** : Les scripts utilisent `logging` - vérifiez les logs Render pour le débogage

## 📚 Structure des données

### Products
- `ProductId`, `Name`, `Sku`, `UnitCost`, `RetailPrice`, `Active`, `CreatedAt`

### Inventory
- `InventoryId`, `ProductId`, `TechnicianId`, `Quantity`, `ReorderThreshold`, `UpdatedAt`

### ProductDisplay (optionnel)
- `DisplayId`, `ProductId`, `DisplayOrder`, `DisplayNameFr`, `DisplayNameEn`, `Category`, etc.

## 🔍 Dépannage

### Erreur de connexion
- Vérifiez que `SUPABASE_PASSWORD` est bien défini
- Vérifiez que les variables d'environnement sont chargées (`.env` ou Render)

### Scripts ne trouvent pas les modules
- Assurez-vous d'être dans le répertoire `assistant-gazelle-web/`
- Vérifiez que `sys.path` est correctement configuré dans les scripts

### Endpoints retournent 401
- Adaptez le décorateur `@require_auth` à votre système d'authentification
- Pour le développement, le décorateur accepte toutes les requêtes par défaut

