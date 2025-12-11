# 🚀 Déploiement sur Render - Scripts Inventaire

Ce document explique comment intégrer les scripts d'inventaire dans votre déploiement Render.

## 📋 Prérequis

1. Repository GitHub configuré
2. Projet Render créé
3. Base de données Supabase configurée

## 🔧 Configuration Render

### Variables d'environnement à configurer dans Render

Dans votre dashboard Render → Environment Variables, ajoutez :

```env
# Supabase Configuration
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_HOST=xxxxx.supabase.co
SUPABASE_PORT=5432
SUPABASE_DATABASE=postgres
SUPABASE_USER=postgres
SUPABASE_PASSWORD=votre_mot_de_passe

# Optionnel : SQL Server (si migration progressive)
# DB_CONN_STR=DRIVER={ODBC Driver 17 for SQL Server};SERVER=...
```

### Structure recommandée dans votre repo

```
assistant-gazelle/
├── scripts/
│   ├── inventory_checker.py
│   └── export_inventory_data.py
├── export_inventaire/          # Dossier d'export (optionnel)
│   ├── requirements.txt
│   └── README.md
└── render.yaml                  # Configuration Render
```

## 📦 Intégration dans Render

### Option 1 : Scripts autonomes (recommandé)

Les scripts peuvent être exécutés via :
- **Cron Jobs Render** (tâches planifiées)
- **Webhooks** (déclenchement manuel)
- **API Endpoints** (intégration dans votre app Flask)

### Option 2 : Endpoints API Flask

Ajoutez dans votre `app/assistant_web.py` :

```python
from scripts.inventory_checker import check_low_stock, generate_alerts
from scripts.export_inventory_data import export_products, export_inventory

@app.route('/api/inventory/check-stock')
@require_auth('read_client')
def check_stock_api(user):
    """API endpoint pour vérifier les stocks bas"""
    alerts = generate_alerts()
    return jsonify(alerts)

@app.route('/api/inventory/export')
@require_auth('admin')
def export_inventory_api(user):
    """API endpoint pour exporter les données"""
    # Exécuter l'export
    # Retourner les fichiers ou un lien de téléchargement
    pass
```

## 🔄 Workflow de migration

### Étape 1 : Export initial (Windows/SQL Server)

```bash
# Sur votre machine Windows actuelle
python export_inventaire/export_inventory_data.py
```

Cela génère les fichiers CSV dans `export_data/`.

### Étape 2 : Import dans Supabase

Suivez `INSTRUCTIONS_IMPORT.md` pour importer les données.

### Étape 3 : Vérification sur Render

Une fois déployé sur Render, testez :

```bash
# Via l'API (si endpoints créés)
curl https://votre-app.onrender.com/api/inventory/check-stock

# Ou via script direct (SSH dans Render)
python scripts/inventory_checker.py
```

## 📝 Notes importantes

1. **Variables d'environnement** : Render injecte automatiquement les variables d'env dans les scripts
2. **Dépendances** : Ajoutez `psycopg2-binary` et `python-dotenv` dans votre `requirements.txt` principal
3. **Logs** : Les scripts utilisent `logging` - vérifiez les logs Render pour le débogage
4. **Sécurité** : Ne commitez jamais les fichiers `.env` - utilisez les secrets Render

## 🔍 Vérification post-déploiement

1. Connectez-vous à votre app Render
2. Vérifiez que les variables d'environnement Supabase sont bien configurées
3. Testez la connexion :
   ```python
   # Dans la console Python Render
   from scripts.inventory_checker import get_db_connection
   conn = get_db_connection()
   print("✅ Connexion OK")
   ```

## 📚 Ressources

- [Documentation Render](https://render.com/docs)
- [Supabase Python Client](https://supabase.com/docs/reference/python)
- `README.md` : Guide d'utilisation des scripts
- `INSTRUCTIONS_IMPORT.md` : Instructions d'import Supabase

